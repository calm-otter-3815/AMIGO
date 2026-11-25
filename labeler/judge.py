"""Step 4: could the question's words also mean this candidate? LLM votes, best of three
where it matters.

  .venv/bin/python -m labeler.judge

For each gold item with candidates, the candidates and the planted decoys are mixed,
shuffled (random.Random(SEED)) and cut into calls of at most BATCH options. The judge
sees the question, the words, what the gold SQL took them to mean, and the options.
Every option gets one vote (seed 0). Options voted yes, or found by two signals or more,
get two more votes (seeds 1 and 2, options in reverse and shuffled order) and the
majority decides: on the pilot one vote disagreed with the majority of three on about 2%
of options, so a single "no" stands. Copies are accepted by code and clones take the
verdict of the column they copy. Writes runs/labeler/judge.jsonl.
"""

import os
import random
from concurrent.futures import ThreadPoolExecutor

from labeler import llm, read, run
from labeler.link import note
from labeler.pool import Lake

SEED = 2026
BATCH = 12
CAP = 10_000  # tokens per judge call; the last retry gets the full room
LIMIT = int(os.environ.get("LABEL_JUDGE_LIMIT", CAP)) or None  # 0: full room from the first call

PROMPT = """You check readings of a question asked to a data lake (many databases pooled together). The person who wrote the reference SQL for the question took some of its words to mean one column or table. Other columns or tables may hold the same kind of information, or another reasonable reading of the same words. Your task: for each option, decide whether someone asking exactly this question, with exactly these words, could reasonably mean that option.

Say "yes" when the words, read in this question, can fairly mean what the option holds: the same information kept in another place, or another sensible reading of the words. The option does not need to be as good as the reference choice.
Say "no" when the option holds something the words cannot mean here: a different property, a different role (a seller instead of a buyer, an end date instead of a start date), a narrower or wider group than the words allow, or something unrelated.
Judge each option on its own, from its table, its name and its values.

Example
Question: "Which ferries leave from Brest?"
Words: "leave from Brest"
Reference choice: port_calls.departure_port (TEXT) values: Brest, Roscoff, Cork
Options:
1. sailings.origin (TEXT) values: Brest, Plymouth, Santander
2. port_calls.arrival_port (TEXT) values: Brest, Plymouth, Cork
3. ferries.home_port (TEXT) values: Brest, Santander, Rosslare
4. crew.birth_city (TEXT) values: Brest, Quimper, Lorient
Output Format:
{{"1": "yes", "2": "no", "3": "yes", "4": "no"}}

Now this one.
Question: "{question}"
Words: "{words}"
Reference choice: {gold}
Options:
{options}

Output Format: a JSON object with exactly one key per option number above ("1" to "{n}"), each with the value "yes" or "no". No other text.
Return an answer only in this exact Output Format."""


def schema(n: int) -> dict:
    keys = [str(i) for i in range(1, n + 1)]
    return {"type": "object", "required": keys, "additionalProperties": False,
            "properties": {k: {"enum": ["yes", "no"]} for k in keys}}


def ask(question: str, item: dict, shown: list[str], seed: int, order: list[int], qid: str) -> list[bool | None]:
    """One vote per option, in option order, from one call with the options in `order`.
    A call that runs out of room is retried with another seed, then with the full room."""
    n = len(shown)
    prompt = PROMPT.format(question=question, words=item["words"], gold=item["gold_shown"], n=n,
                           options="\n".join(f"{k}. {shown[i]}" for k, i in enumerate(order, 1)))
    for s, limit in ((seed, LIMIT), (seed + 3, LIMIT), (seed + 3, None)):
        try:
            reply = llm.ask_json(prompt, s, schema(n), tag=f"judge {qid} {item['item']}", limit=limit,
                                 finished_under=CAP if limit is None else None)  # replies saved under the cap
        except (ValueError, KeyError, TypeError):
            continue
        out = [None] * n
        for k, i in enumerate(order, 1):
            out[i] = reply.get(str(k)) == "yes"
        return out
    return [None] * n


def verdict(votes: list[bool | None]) -> str:
    """One vote decides a no; a yes (or a strong candidate) gets three, majority wins."""
    if len(votes) == 1:
        return "no" if votes[0] is False else "failed"
    yes, no = votes.count(True), votes.count(False)
    return "yes" if yes >= 2 else "no" if no >= 2 else "failed" if yes + no == 0 else "unsure"


def batches(options: list[dict]) -> list[list[dict]]:
    return [options[i:i + BATCH] for i in range(0, len(options), BATCH)]


def judge_item(question: str, item: dict, lake: Lake, qid: str) -> dict:
    """Copies are accepted by code; clones take the verdict of the column they copy; the
    rest get one vote, and the options voted yes or found by two signals get two more."""
    options = [{**c, "decoy": False} for c in item["candidates"]] + [{"name": d, "sources": [], "decoy": True} for d in item["decoys"]]
    random.Random(f"{SEED}{question}{item['item']}").shuffle(options)
    asked = [o for o in options if "copy" not in o["sources"] and "clone_of" not in o]

    def first(batch: list[dict]) -> None:
        n = len(batch)
        for o, v in zip(batch, ask(question, item, [lake.shown[o["name"]] for o in batch], 0, list(range(n)), qid)):
            o["votes"] = [v]

    def more(batch: list[dict], seed: int) -> list:
        n, shown = len(batch), [lake.shown[o["name"]] for o in batch]
        order = list(range(n))[::-1] if seed == 1 else random.Random(f"{SEED}{qid}{item['item']}").sample(range(n), n)
        return ask(question, item, shown, seed, order, qid)

    with ThreadPoolExecutor(8) as pool:  # all calls of an item at once keep the server full
        list(pool.map(first, batches(asked)))
        again = batches([o for o in asked if o["votes"][0] or len(o["sources"]) >= 2])
        both = list(pool.map(lambda job: more(*job), [(b, seed) for seed in (1, 2) for b in again]))
        second, third = both[:len(again)], both[len(again):]
    for batch, b2, b3 in zip(again, second, third):
        for o, v2, v3 in zip(batch, b2, b3):
            o["votes"] += [v2, v3]
    for o in asked:
        o["verdict"] = verdict(o["votes"])
    by_name = {o["name"]: o for o in options}
    for o in options:
        if "copy" in o["sources"]:
            o["verdict"] = "copy"
    for o in options:  # after the copies: a clone may copy a copy
        if "clone_of" in o and "copy" not in o["sources"]:
            o["verdict"] = by_name.get(o["clone_of"], {}).get("verdict", "failed")
    return {**item, "options": options, "calls": len(batches(asked)) + 2 * len(again)}


def judge(row: dict, record: dict, lake: Lake) -> dict:
    """All judged items of one question, in parallel."""
    judged = [i for i in record["items"] if i["candidates"]]
    with ThreadPoolExecutor(max(len(judged), 1)) as pool:
        done = list(pool.map(lambda i: judge_item(row["question"], i, lake, row["id"]), judged))
    by_item = {(i["item"], i.get("role")): i for i in done}
    return {"id": record["id"], "items": [by_item.get((i["item"], i.get("role")), i) for i in record["items"]]}


def main() -> None:
    rows = {r["id"]: r for r in read("questions")}
    todo = [r for r in read("pool") if any(i["candidates"] for i in r["items"])]
    lakes = {name: Lake(name) for name in {rows[r["id"]]["lake"] for r in todo}}
    run("judge", todo, lambda r: judge(rows[r["id"]], r, lakes[rows[r["id"]]["lake"]]), colour="yellow", threads=48, note=note)


if __name__ == "__main__":
    main()
