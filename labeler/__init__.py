"""Broadened gold labels for the six lakes, built with no human in the loop.

This package never imports `amigo`, so its labels cannot borrow AMIGO's choices.
Output goes to runs/labeler/<run>/ with <run> from the LABEL_RUN variable (pilot,
bird_dev, ...). The LLM cache is one file per run, runs/labeler/cache-<run>.jsonl; the lake
embeddings in runs/labeler/emb/ are shared (gitignored).
"""

import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "labeler"
RUN = OUT / os.environ.get("LABEL_RUN", "pilot")
LAKES = ["bird_dev", "spider_dev", "beaver_dw", "beaver_nw", "fiben", "mmqa"]


def lake_files(lake: str) -> tuple[list[Path], Path]:
    """The database files and the question file of a lake, from lakes.json."""
    entry = json.loads((ROOT / "lakes.json").read_text())[lake]
    return sorted(ROOT.glob(entry["databases"])), ROOT / entry["questions"]


def cross_questions(lake: str) -> list[dict]:
    """The questions whose gold SQL spans several databases (db_ids), kept in their own file
    under "cross_questions" in lakes.json (taco_us); none for the other lakes."""
    entry = json.loads((ROOT / "lakes.json").read_text())[lake]
    return json.loads((ROOT / entry["cross_questions"]).read_text()) if "cross_questions" in entry else []


def dbs(row: dict) -> list[str]:
    """The databases a question's gold SQL reads."""
    return row.get("db_ids") or [row["db_id"]]


def full(row: dict, item: str) -> str:
    """The lake name (db.table or db.table.column) of a gold item of `row`. A question across
    databases already names its items with their database."""
    return item if "db_ids" in row else f"{row['db_id']}.{item}"


def split_item(item: str, cross: bool = False) -> tuple[str, str | None]:
    """(table, column) of a gold item "table.column", or (table, None) for a table; across
    databases the item is "db.table.column" and the table "db.table". No database or table
    name holds a dot; a column name may ("No. of Units" in taco_us)."""
    parts = item.split(".", 2 if cross else 1)
    if len(parts) == (3 if cross else 2):
        return item[:len(item) - len(parts[-1]) - 1], parts[-1]
    return item, None


def table_of(name: str) -> str:
    """db.table of a lake name db.table.column (or of db.table itself)."""
    return ".".join(name.split(".", 2)[:2])


def column_of(name: str) -> str:
    """The column of a lake name db.table.column."""
    return name.split(".", 2)[2]


def databases(lake: str) -> dict[str, Path]:
    """Database name (the file stem) to its path."""
    return {path.stem: path for path in lake_files(lake)[0]}


def read(name: str) -> list[dict]:
    """The records of runs/labeler/<run>/<name>.jsonl, empty when it does not exist yet."""
    path = RUN / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def run(name: str, items: list, work, colour: str = "cyan", threads: int = 96, note=None) -> None:
    """Apply `work` to the items not yet in <name>.jsonl, in parallel, appending each
    result the moment it is ready (open the file in VS Code to watch it grow; a stopped
    run resumes where it was). `note()` gives the live totals shown after the bar."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    path = RUN / f"{name}.jsonl"
    if path.exists():  # a run killed mid-write leaves a half line: drop it
        os.truncate(path, path.read_bytes().rfind(b"\n") + 1)
    done = {r["id"] for r in read(name)}
    todo = [i for i in items if i["id"] not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    bar = tqdm(total=len(items), initial=len(items) - len(todo), desc=f"{name:>6}", colour=colour,
               unit="q", dynamic_ncols=True, smoothing=0.05,
               bar_format="{desc} {bar} {n_fmt}/{total_fmt} q  {elapsed} spent, ~{remaining} left  {postfix}")
    stop = threading.Event()

    def tick():  # the bar moves per finished question; the totals move every few seconds
        while note and not stop.wait(3):
            bar.set_postfix_str(note())

    threading.Thread(target=tick, daemon=True).start()
    errors = RUN / f"{name}-errors.jsonl"
    with ThreadPoolExecutor(threads) as pool, path.open("a") as out:
        futures = {pool.submit(work, i): i["id"] for i in todo}
        for future in as_completed(futures):
            try:
                out.write(json.dumps(future.result()) + "\n")
                out.flush()
            except Exception as error:  # one bad item must not stop the others being saved
                import traceback
                with errors.open("a") as f:
                    f.write(json.dumps({"id": futures[future], "error": repr(error),
                                        "trace": traceback.format_exc()[-2000:]}) + "\n")
                bar.write(f"error on {futures[future]}: {error!r} (logged in {errors.name})")
            bar.update()
    stop.set()
    bar.close()


def questions(lake: str) -> list[dict]:
    """The question records of a lake with one `SQL` string each (spider's `sql` is a dict)."""
    records = json.loads(lake_files(lake)[1].read_text())
    for number, record in enumerate(records, 1):
        written = record.get("SQL") or record.get("query") or record.get("sql")
        record["SQL"] = written if isinstance(written, str) else ""
        record.setdefault("question_id", number)
    return records
