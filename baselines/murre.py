"""MURRE: beam search over tables in up to three hops. Hop 1 retrieves by the question;
after each hop an LLM call writes, for each of the 5 kept paths, the tables still missing
("removal", in table form), and that text is the next hop's query; a path scores the
product of its (cos + 1) / 2, and a table the score of its best path. zhang2025murre.

Departures from the paper:
1. (medium) The LLM is the default chat model with its reasoning effort, not
   gpt-3.5-turbo; temperature 0.3, max_tokens 256 and the blank-line stop cannot be set.
2. (small) The reply is JSON by schema, {"completing_tables": [...]}, one table per item
   and an empty list for None, instead of free text after "Completing Tables:"; the prompt
   ends with its output format. The next query is the items joined by " \\n ", as the
   paper's text writes them, and the Database line joins tables the same way, as in the
   examples (the code uses a real newline there). A reply that fails after one re-ask
   fails the question (the code's empty-string answer is an error path, not a fallback).
3. (medium) Nine invented out-of-domain examples (three None, one two-table answer) in
   one prompt for every lake; the repo has 10 (Spider) and 9 (BIRD) examples taken from
   the evaluation questions, one prompt per benchmark.
4. (medium) granite-embedding-english-r2 replaces SGPT, without SGPT's "[ ]" and "{ }"
   brackets and position-weighted pooling.
5. (small) A table is "db.table(col, col, ...)" with the stored names, not the
   benchmark's cleaned names (Spider: lower case, spaces for underscores).
6. (small) Hops 2 and 3 search the whole lake, as the paper says; the code searches only
   the hop-1 top 100.
7. (small) Removal always gets the original question, as the paper says; at hop 3 the
   code passes the previous removal text instead.
8. (small) Beams and the final ranking use the paper's product of (cos + 1) / 2; the code
   ranks beams by the sum of log(cos) and tables by the sum of log((cos + 2) / 2).
9. (small) The final ranking applies the paper's table score to every path scored at the
   last hop (each beam extended by every table not on it), as the code does to fill the
   top k; its head is the paper's ranking over the 5 kept paths.
10. (small) Early stop follows the code: one None from any beam stops the question at
   that hop (the paper's text reads per path). None is an empty list, not the code's
   substring test, and calls stop at the first None instead of all running.
"""

import os
import string
import threading
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from amigo import embed, llm

from .lake import lap, record

# BL_CACHE_DIR moves the index caches: they are keyed by lake name only, so a rebuilt lake needs its own
CACHE = Path(os.environ.get("BL_CACHE_DIR", Path(__file__).resolve().parents[1] / "runs" / "eval" / "bl_cache")) / "murre"
BEAM = 5
HOPS = 3

PROMPT = string.Template('''Given the following SQL tables, your job is to complete the possible left SQL tables given a user’s request.
Return None if no left SQL tables according to the user’s request.

Question: Which signals on the Northgate line were inspected after a fault was reported on them?
Database: rail_signals.signal(signal_id, line_id, position_km, aspect_type) \\n rail_signals.inspection(inspection_id, signal_id, inspected_on, inspector_name, result)
Completing Tables: rail_signals.line(line_id, line_name, opened_year) \\n rail_signals.fault_report(report_id, signal_id, reported_on, description)

Question: How many hives produced more than 20 kg of honey in 2023?
Database: apiary.hive(hive_id, apiary_id, installed_on, queen_breed) \\n apiary.harvest(harvest_id, hive_id, harvest_date, honey_kg)
Completing Tables: None

Question: What is the average yearly retreat of the glaciers in the Patagonia region?
Database: glacier_watch.Measurement(MeasurementID, GlacierID, Year, FrontRetreatM)
Completing Tables: glacier_watch.Glacier(GlacierID, Name, Region, AreaKm2, ElevationM)

Question: List the names of the lighting fixtures used in the production 'Winter Lanterns'.
Database: stage_lighting.fixture(fixture_id, name, wattage, beam_angle) \\n stage_lighting.production(production_id, title, opening_night)
Completing Tables: stage_lighting.fixture_use(production_id, fixture_id, cue_count)

Question: Which vessels docked at Port Lyra in March 2024?
Database: harbour.port_call(call_id, vessel_id, port_id, arrival, departure) \\n harbour.vessel(vessel_id, vessel_name, flag, gross_tonnage) \\n harbour.port(port_id, port_name, country)
Completing Tables: None

Question: What was the highest water level recorded at the Ashford gauge?
Database: river_gauges.reading(reading_id, gauge_id, taken_at, level_cm)
Completing Tables: river_gauges.gauge(gauge_id, station_name, river, latitude, longitude)

Question: Which fossils found at the Redcliff quarry are older than 100 million years?
Database: paleo.fossil(fossil_id, species, age_mya, site_id) \\n paleo.dig_site(site_id, site_name, region)
Completing Tables: None

Question: Which grape varieties are grown on plots with clay soil?
Database: vineyard.variety(variety id, variety name, colour) \\n vineyard.planting(plot id, variety id, planted year)
Completing Tables: vineyard.plot(plot id, soil type, area ha, slope)

Question: Which observing sites host a telescope with a mirror wider than 4 metres?
Database: observatory.TELESCOPE(TELESCOPE_ID, NAME, MIRROR_DIAMETER_M, SITE_ID)
Completing Tables: observatory.SITE(SITE_ID, SITE_NAME, ALTITUDE_M, COUNTRY)

Question: $question
Database: $database

Output Format: a JSON object with exactly the key "completing_tables", whose value is the list of the left SQL tables for the last Question and Database above, not for the examples, each one a string written as in the Database line, database.table(column, column, ...). None is an empty list. No other text.
Return an answer only in this exact Output Format.''')


class Removal(BaseModel):
    completing_tables: list[str]


_LOCK = threading.Lock()
_VECTORS: dict[str, np.ndarray] = {}


def _text(table) -> str:
    return f"{table.path}({', '.join(c.name for c in table.columns)})"


def _vectors(lake) -> np.ndarray:
    """One vector per table of its "db.table(col, ...)" text; embedded once per lake,
    kept on disk and in memory."""
    with _LOCK:
        if lake.name not in _VECTORS:
            texts = [_text(t) for t in lake.tables]
            path = CACHE / lake.name / "tables.npz"
            kept = np.load(path) if path.exists() else None
            if kept is not None and kept["texts"].tolist() == texts:
                vectors = kept["vectors"]
            else:
                vectors = embed.embed(texts)
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez(path, texts=np.array(texts), vectors=vectors)
            _VECTORS[lake.name] = vectors
        return _VECTORS[lake.name]


def _left(lake, question, path, log_path) -> list[str]:
    """The tables the LLM call says the path still misses; empty for None."""
    database = " \\n ".join(_text(lake.tables[t]) for t in path)
    reply = llm.call(PROMPT.substitute(question=question, database=database), Removal,
                     log_path, f"murre {question[:50]}")
    return [t.strip() for t in reply.completing_tables if t.strip() not in ("", "None")]


def run(lake, question, log_path, k=3):
    vectors = _vectors(lake)
    lap("setup")
    beams = [((), 1.0, question)]  # (table rows on the path, path score, next hop's query)
    for hop in range(1, HOPS + 1):
        near = (1 + embed.embed([q for *_, q in beams]) @ vectors.T) / 2
        score = np.array([s for _, s, _ in beams])[:, None] * near
        for b, (path, *_) in enumerate(beams):
            score[b, list(path)] = -1  # a path never takes a table twice
        lap("search")
        if hop == HOPS:
            break
        # the 5 best extensions of all beams: the paper's 5 x 5 rule, as each is among its beam's 5 best
        top = [divmod(int(i), len(vectors)) for i in np.argsort(-score, axis=None, kind="stable")[:BEAM]]
        left = []
        for b, t in top:
            left.append(_left(lake, question, beams[b][0] + (t,), log_path))
            if not left[-1]:
                break
        lap("llm removal")
        if not left[-1]:  # None: that path's tables suffice, so the question stops at this hop
            break
        beams = [(beams[b][0] + (t,), float(score[b, t]), " \\n ".join(q)) for (b, t), q in zip(top, left)]

    # a table scores its best path among those of the last hop (Algorithm 1)
    best = score.max(0)
    for b, (path, *_) in enumerate(beams):
        best[list(path)] = np.maximum(best[list(path)], score[b].max())
    order = np.argsort(-best, kind="stable")[:k]
    lap("rank")
    return record([lake.tables[i].path for i in order], hops=hop)
