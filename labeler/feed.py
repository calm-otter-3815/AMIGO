"""Live feed of LLM calls, one short card per call, sized for a narrow (phone) screen.

  .venv/bin/python -m labeler.feed            new calls only
  .venv/bin/python -m labeler.feed 5          the last 5 calls first, then new ones
  .venv/bin/python -m labeler.feed 5 why      also the end of each call's thinking

A judge card shows the question, the words judged, the gold column, the options the judge
accepted, and how many it rejected. A swap card shows the rewritten SQL. Read-only.
"""

import json
import re
import shutil
import sys
import textwrap
import time

from labeler import OUT
from labeler.llm import CACHE

DIM, BOLD, GREEN, RED, CYAN, YELLOW, END = "\033[2m", "\033[1m", "\033[32m", "\033[31m", "\033[36m", "\033[33m", "\033[0m"


def field(prompt: str, name: str) -> str:
    found = re.findall(rf"^{name}: (.*)$", prompt.split("Now this one.")[-1], re.M)
    return found[0].strip('"') if found else ""


_full: dict[str, dict[str, list[str]]] = {}


def name_of(shown: str, qid: str = "") -> str:
    """db.table.column (or db.table) for the text the judge was shown; the judge itself is
    not shown database names, so same-named tables of different databases look alike."""
    lake = qid.rsplit("-", 1)[0]
    if lake and lake not in _full:
        _full[lake] = {}
        path = OUT / "emb" / f"{lake}-shown.json"
        if path.exists():
            for name, text in json.loads(path.read_text())[1].items():
                _full[lake].setdefault(text, []).append(name)
    names = _full.get(lake, {}).get(shown)
    return " / ".join(names) if names else re.split(r" \(| columns:", shown, maxsplit=1)[0]


def wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width) or [""]


def card(call: dict, why: bool) -> str:
    width = min(shutil.get_terminal_size((60, 20)).columns, 80)
    step, _, rest = call.get("tag", "? ?").partition(" ")
    qid, _, item = rest.partition(" ")
    prompt, reply = call.get("prompt", ""), call.get("reply")
    out = [f"{DIM}{'─' * width}{END}", f"{BOLD}{CYAN}{step.upper()}{END}  {BOLD}{qid}{END}  {DIM}{call.get('tokens', 0)} tokens{END}"]
    question = field(prompt, "Question")
    if question:
        out += wrap(f"Q: {question}", width)
    if reply is None:
        out.append(f"{RED}thinking too long, retrying{END}")
    elif step == "judge":
        out.append(f"{BOLD}\"{field(prompt, 'Words')}\"{END}")
        out.append(f"{DIM}gold: {name_of(field(prompt, 'Reference choice'))}{END}")
        votes = json.loads(reply)
        options = re.findall(r"^(\d+)\. (.*)$", prompt.split("Now this one.")[-1], re.M)
        yes = [name_of(t, qid) for k, t in options if votes.get(k) == "yes"]
        out += [f" {GREEN}✔{END} {n}" for n in yes]
        out.append(f" {RED}✘{END} {DIM}{len(options) - len(yes)} rejected{END}")
    elif step == "swap":
        sql = (json.loads(reply) or {}).get("sql")
        out.append(f"{DIM}uses: {item}{END}")
        out += [f"{YELLOW}{line}{END}" for line in wrap(sql or "not answerable from this database", width)]
    else:
        out += wrap(reply[:300], width)
    think = " ".join((call.get("thinking") or "").split())
    if why and think:
        out += [f"{DIM}{line}{END}" for line in wrap("why: ..." + think[-240:], width)]
    return "\n".join(out)


def main() -> None:
    back = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    why = "why" in sys.argv[2:]
    with CACHE.open() as f:
        f.seek(0, 2)
        if back:  # lines hold whole thinking texts: read only the end of the file
            f.seek(max(0, f.tell() - back * 200_000))
            f.readline()
            for line in f.readlines()[-back:]:
                print(card(json.loads(line), why), flush=True)
        while True:
            line = f.readline()
            if not line.endswith("\n"):
                time.sleep(1)
                f.seek(f.tell() - len(line))
                continue
            print(card(json.loads(line), why), flush=True)


if __name__ == "__main__":
    main()
