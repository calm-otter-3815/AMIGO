"""Full schema in one prompt: every table of the lake, one line each (its columns and the
first sentence of its description), and one LLM call names the tables that answer the
question. No retrieval step. No size cap: a lake whose schema does not fit the model's
context fails on each question, kept as an error and scored as an empty answer.
The question goes last, so the questions of a lake share the schema prefix.
"""

import re
import string
import threading

from pydantic import BaseModel

from amigo import llm

from .lake import lap, record

PROMPT = string.Template("""You choose the tables of a data lake that answer a question. A question may need one table or several tables joined together.

Data lake (each line is database.table(column, column, ...): what the table holds):
$schema

Example, over a made-up data lake that is not the one above:
harbour.vessel(vessel_id, name, home_port_id, tonnage): ships and the port each is based in
harbour.port(port_id, port_name, country): ports
weather.station(station_id, port_id, name): weather stations near ports
weather.reading(station_id, taken_on, wind_kmh): wind readings of each station
Question: How many vessels of more than 500 tonnes are based in Saltmere?
Answer: {"tables": ["harbour.vessel", "harbour.port"]}

Rules:
- Name only tables listed in the data lake above, written exactly as database.table.
- Name every table the answer needs, including a table needed only to join two others.

Question: $question

Output Format: a JSON object with exactly the key "tables", whose value is the list of the chosen tables, each a string database.table written as in the data lake above. No other text.
Return an answer only in this exact Output Format.""")

_SCHEMA: dict[str, str] = {}
_LOCK = threading.Lock()


class Chosen(BaseModel):
    tables: list[str]


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]


def schema(lake) -> str:
    with _LOCK:
        if lake.name not in _SCHEMA:
            _SCHEMA[lake.name] = "\n".join(
                f"{t.path}({', '.join(c.name for c in t.columns)}): {_first_sentence(t.description)}"
                for t in lake.tables)
        return _SCHEMA[lake.name]


def known(lake):
    def check(reply: Chosen) -> None:
        if not reply.tables:
            raise llm.ModelError("name at least one table")
        unknown = [t for t in reply.tables if t not in lake.table]
        if unknown:
            raise llm.ModelError(f"not tables of the data lake: {unknown}")
    return check


def run(lake, question, log_path):
    text = schema(lake)
    lap("setup")
    reply = llm.call(PROMPT.substitute(schema=text, question=question), Chosen, log_path, "full schema",
                     check=known(lake))
    lap("llm choose")
    return record(list(dict.fromkeys(reply.tables)))
