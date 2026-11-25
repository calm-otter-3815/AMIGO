"""Paths, keys, constants and lake definitions."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LAKES_DIR = ROOT / "lakes"
RUNS_DIR = ROOT / "runs"
PROMPTS_DIR = ROOT / "prompts"
ENV_FILE = ROOT / ".env"
LAKE_DEFS = ROOT / "lakes.json"
# explicit path: auto-discovery walks up from cwd and misses when run through stdin. Loaded
# before the flags below are read, so a flag set in .env counts.
load_dotenv(ENV_FILE)

EMBEDDING_MODEL = "ibm-granite/granite-embedding-english-r2"
# a new commit to the model's repo would change the query vectors but not a built lake's
EMBEDDING_REVISION = "47ea694b257b703fee9253d75c2b1f2985180498"
# every default LLM step runs on the local Qwen since the OpenAI credits ran out on
# 2026-10-14; LLM_MODEL=<an OpenAI model> goes back to OpenAI
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.8-27b-fp8")
LLM_REASONING_EFFORT = "medium"
# the thinking levels each model takes, lowest first; "none" is thinking off. Qwen's were
# read from its server's replies, OpenAI's from each model page on developers.openai.com,
# both on 2026-10-20. A model left out (its page lists none) gets each level as asked.
EFFORTS = {
    "qwen3.8-27b-fp8": ("none", "low", "medium", "xhigh"),
    "gpt-6-astra": ("low", "medium", "high", "xhigh", "max"),
    "gpt-6.1-sol": ("low", "medium", "high", "xhigh", "max"),
    "gpt-6-sol": ("none", "low", "medium", "high", "xhigh", "max"),
    "gpt-6-luna": ("none", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.6-sol": ("none", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.6-terra": ("none", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.6-luna": ("none", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.5": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.4": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.4-mini": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.4-nano": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.2": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.1": ("none", "low", "medium", "high"),
    "gpt-5": ("minimal", "low", "medium", "high"),
}
# the page's thinking choice for every call: None keeps each step's own level
THINKING: str | None = None
# the judge's two calls; JUDGE_EFFORT=none turns thinking off, for a fast run
JUDGE_REASONING_EFFORT = os.environ.get("JUDGE_EFFORT", LLM_REASONING_EFFORT)
# the judge's place grades asked this many times at once, their odds averaged (judge.py):
# samples in parallel in place of thinking in series
JUDGE_SAMPLES = int(os.environ.get("JUDGE_SAMPLES", "1"))
# the judge's thinking stopped after this many tokens, then it answers (budget forcing,
# Muennighoff et al. 2025); local models only, unset thinks as long as it likes
JUDGE_BUDGET = int(os.environ["JUDGE_BUDGET"]) if os.environ.get("JUDGE_BUDGET") else None
# splitting the question feeds every later step; at medium it often skipped thinking and
# folded a bare name into an attribute ("Batman's colour")
DECOMPOSE_REASONING_EFFORT = os.environ.get("DECOMPOSE_EFFORT", "high")
# the answer in words only reads rows already there, so it needs little thinking
SAY_REASONING_EFFORT = "low"
# flex unless a run sets LLM_SERVICE_TIER=default (the standard lane): a timing run does,
# as flex waits vary too much to time a method by
LLM_SERVICE_TIER = os.environ.get("LLM_SERVICE_TIER", "flex")
if LLM_SERVICE_TIER not in ("flex", "default"):
    raise ValueError(f"LLM_SERVICE_TIER is {LLM_SERVICE_TIER!r}, and it must be 'flex' or 'default'")
LLM_ATTEMPTS = 3
# models served by vLLM on this machine behind its OpenAI-style API: no lane, no price
# (labeler/llm.py has the start command; QWEN_URL when the server runs elsewhere, several
# comma-separated when several servers share the calls)
LOCAL_MODELS = {"qwen3.8-27b-fp8": os.environ.get("QWEN_URL", "http://localhost:8000/v1")}
# the answer window in bits: AMIGO_WINDOW=none (default) keeps every
# interpretation the judge says yes to, up to judge.MOST; a number keeps only those at most
# that many bits above the best (1: at least half as likely; chosen by hand, for ablations)
WINDOW = None if os.environ.get("AMIGO_WINDOW", "none") == "none" else float(os.environ["AMIGO_WINDOW"])
# the longest prompt one judge call is sent, in tokens; a longer list is split over several
# calls. Half the local Qwen server's 32,768-token window (labeler/llm.py), which prompt and
# reply share: the smallest window of the models run here
PROMPT_TOKENS = int(os.environ.get("PROMPT_TOKENS", "16384"))
# the second judge call's model, when not LLM_MODEL: the OpenAI credits ran out on
# 2026-10-14, while its run was half done
WHOLES_MODEL = os.environ.get("WHOLES_MODEL") or None

# US dollars per million tokens (input, cached input, output) for each model and lane:
# "flex", "default" (the standard lane) and "fast" (called "priority" before 2026-07-30).
# The GUI offers only these models: a call to any other could not be priced. They all take
# a reasoning effort and a JSON schema. Source: https://developers.openai.com/api/docs/pricing,
# checked 2026-10-06.
LLM_PRICES = {
    "gpt-6-astra": {"flex": (5, 0.5, 25), "default": (10, 1, 50), "fast": (20, 2, 100)},
    "gpt-6.1-sol": {"flex": (1, 0.05, 5), "default": (2, 0.10, 10), "fast": (4, 0.20, 20)},
    "gpt-6-sol": {"flex": (1, 0.10, 5), "default": (2, 0.20, 10), "fast": (4, 0.40, 20)},
    "gpt-6-luna": {"flex": (0.05, 0.005, 0.25), "default": (0.10, 0.01, 0.50), "fast": (0.20, 0.02, 1.00)},
    "gpt-5.6-sol": {"flex": (2, 0.20, 10), "default": (4, 0.40, 20), "fast": (8, 0.80, 40)},
    "gpt-5.6-terra": {"flex": (1, 0.10, 6), "default": (2, 0.20, 12), "fast": (4, 0.40, 24)},
    "gpt-5.6-luna": {"flex": (0.10, 0.01, 0.60), "default": (0.20, 0.02, 1.20), "fast": (0.40, 0.04, 2.40)},
    "gpt-5.5": {"flex": (2.5, 0.25, 15), "default": (5, 0.50, 30), "fast": (12.5, 1.25, 75)},
    "gpt-5.4": {"flex": (1.25, 0.13, 7.5), "default": (2.5, 0.25, 15), "fast": (5, 0.5, 30)},
    "gpt-5.4-mini": {"flex": (0.375, 0.0375, 2.25), "default": (0.75, 0.075, 4.5), "fast": (1.5, 0.15, 9)},
    "gpt-5.4-nano": {"flex": (0.10, 0.01, 0.625), "default": (0.20, 0.02, 1.25)},
    "gpt-5.2": {"flex": (0.875, 0.0875, 7), "default": (1.75, 0.175, 14), "fast": (3.5, 0.35, 28)},
    "gpt-5.1": {"flex": (0.625, 0.0625, 5), "default": (1.25, 0.125, 10), "fast": (2.5, 0.25, 20)},
    "gpt-5": {"flex": (0.625, 0.0625, 5), "default": (1.25, 0.125, 10), "fast": (2.5, 0.25, 20)},
    "gpt-5-mini": {"flex": (0.125, 0.0125, 1), "default": (0.25, 0.025, 2), "fast": (0.45, 0.045, 3.6)},
    "gpt-5-nano": {"flex": (0.025, 0.0025, 0.20), "default": (0.05, 0.005, 0.40)},
    "o3": {"flex": (1, 0.25, 4), "default": (2, 0.5, 8), "fast": (3.5, 0.875, 14)},
    "o4-mini": {"flex": (0.55, 0.138, 2.2), "default": (1.1, 0.275, 4.4), "fast": (2, 0.5, 8)},
}

EXACT_VALUE_LIMIT = 1000
# a column with at most this many values holds codes: a column the person chose that does
# not store their word offers each of its values instead (design: allowed values)
CODE_VALUE_LIMIT = 30
# a value may also sit split over up to this many columns of one row:
# "Juan Pablo Montoya" as forename and surname, or a first, a middle and a last name
SPLIT_PARTS = 3
# 20 bits per value, 14 hashes: about 1 false positive in 15000 (maintainer decision 2026-09-10, a false hit adds a table to the bundle)
BLOOM_BITS_PER_VALUE = 20
BLOOM_HASHES = 14
# Top-k cutoff for lookups 1 and 2, PLAN.md 3.3.
TOP_TABLES = 20
TOP_COLUMNS = 20
# hyperparameter, chosen by hand, for ablations: the columns (AMIGO_COLUMNS) kept per
# question part by name meaning; a number is looked for in these columns
COLUMNS_PER_PART = int(os.environ.get("AMIGO_COLUMNS", "30"))
# Lookup 2: the slots for columns of empty tables, kept apart from the main list.
TOP_EMPTY_COLUMNS = 3

# Step 5: soft cap. More interpretations than this and fan-out logs a warning, but the
# UI already lets the user pick which ones to run, so it never stops the run.
MAX_INTERPRETATIONS = 12

# Step 5: hard safety cap on the column choices tried and the interpretations kept, so a
# pathological question cannot hang the process; past it the first choices are kept.
MAX_COMBINATIONS = 2000

# Step 5 fan-out: the least join quality (containment x cardinality proportion) a link
# needs before fan-out will join on it; below it the overlap is coincidence, not a key.
MIN_EDGE_QUALITY = 0.5

# bundle.minimal_sets: a solution's table set may add at most this many join tables
# beyond the bound ones; a real SQL join across more than three pass-through tables
# is not an interpretation worth running blind.
MAX_JOIN_TABLES = 3

# Step 5 fan-out: two equally good join paths are compared on the rows they join; past
# this many thousand SQLite steps the check stops and keeps them apart. A step count,
# not a clock, so the same question folds the same way on every run and machine.
SAME_ROWS_STEPS = 50_000

# every model reply kept by what was asked (cache.py); "off" to measure run-to-run change
CACHE = os.environ.get("AMIGO_CACHE", "on") != "off"
# AMIGO_CACHE_DIR gives a run its own replies, so none comes from an earlier run
CACHE_DIR = Path(os.environ.get("AMIGO_CACHE_DIR", RUNS_DIR / "cache"))
# an ablation of the evaluation: novalues finds no stored value, so parts are placed by names only
ABLATE = os.environ.get("AMIGO_ABLATE", "none")
if ABLATE not in ("none", "novalues"):
    raise ValueError(f"AMIGO_ABLATE is {ABLATE!r}, and it must be 'none' or 'novalues'")

# Stage 3: how much of a result is kept, how many repair tries, how long one query may run.
SQL_MAX_ROWS = 50
SQL_MAX_TRIES = 5
# counted in SQLite steps, not seconds, so a query stops at the same point on a busy
# machine as on an idle one; 10 billion steps take about 30 s on a laptop
SQL_MAX_STEPS = 10_000_000_000


def openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(f"OPENAI_API_KEY not set in {ENV_FILE}")
    return key


def lake(name: str) -> dict:
    defs = json.loads(LAKE_DEFS.read_text())
    if name not in defs:
        raise KeyError(f"unknown lake {name!r} in {LAKE_DEFS}; known: {sorted(defs)}")
    spec = defs[name]
    databases = sorted(ROOT.glob(spec["databases"]))
    if not databases:
        raise FileNotFoundError(
            f"lake {name!r}: no database matches {spec['databases']!r} under {ROOT}"
        )
    questions = ROOT / spec["questions"]
    if not questions.exists():
        raise FileNotFoundError(f"lake {name!r}: no questions file at {questions}")
    return {
        "name": name,
        "databases": databases,
        "questions": questions,
    }


def questions(name: str) -> list[dict]:
    """The question records of a lake, each labelled with SQL, evidence and question_id."""
    records = json.loads(lake(name)["questions"].read_text())
    for number, record in enumerate(records, 1):
        # the benchmarks spell the gold query SQL, query or sql; spider's `sql` is a parsed dict
        written = record.get("SQL") or record.get("query") or record.get("sql")
        record["SQL"] = written if isinstance(written, str) else ""
        record.setdefault("evidence", "")
        record.setdefault("question_id", number)
    return records
