"""Live view of a labeling run: progress, quality per lake, and the latest accepted answers.

  .venv/bin/python -m labeler.watch

Reads runs/labeler/labels.jsonl (finished questions) and the servers' counters every
REFRESH seconds. Read-only: it never touches the run.
"""

import time
import urllib.request

from labeler import read
from labeler.label import summary
from labeler.llm import URLS

REFRESH = 10
LATEST = 12
DIM, BOLD, GREEN, YELLOW, RED, CYAN, END = "\033[2m", "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m"
COLOUR = {"different rows": GREEN, "same rows": CYAN, "empty": YELLOW, "failed": RED, "not answerable": YELLOW}


def server() -> dict[str, float]:
    """The servers' counters, added up over all of them; a server that does not answer adds nothing."""
    out = {}
    for url in URLS:
        try:
            text = urllib.request.urlopen(url.removesuffix("/v1") + "/metrics", timeout=3).read().decode()
        except OSError:
            continue
        for line in text.splitlines():
            for name in ("num_requests_running", "num_requests_waiting", "generation_tokens_total"):
                if line.startswith(f"vllm:{name}{{"):
                    out[name] = out.get(name, 0.0) + float(line.rsplit(" ", 1)[1])
    return out


def main() -> None:
    total = len(read("questions"))
    last = server().get("generation_tokens_total", 0.0)
    while True:
        labels = read("labels")
        now = server()
        speed = (now.get("generation_tokens_total", last) - last) / REFRESH
        last = now.get("generation_tokens_total", last)
        times = sorted(x["finished"] for x in labels if "finished" in x)
        rate = (len(times) - 1) / (times[-1] - times[0]) if len(times) >= 2 and times[-1] > times[0] else 0
        eta = f"~{(total - len(labels)) / rate / 60:.0f} min left" if rate else "time left: after 2 questions"
        out = [f"{BOLD}labeling run{END}  {len(labels)}/{total} questions done  {eta}   "
               f"{DIM}server: {now.get('num_requests_running', 0):.0f} calls running, "
               f"{now.get('num_requests_waiting', 0):.0f} waiting, {speed:.0f} tokens/s{END}", ""]
        out += [f"{BOLD}{line}{END}" if i == 0 else line for i, line in enumerate(summary(labels))]
        out += ["", f"{DIM}decoys in = planted wrong columns the judge accepted; unsure = votes split or failed; "
                    f"revoted = options that got 3 votes{END}", "", f"{BOLD}latest accepted answers{END}"]
        recent = [(x, a) for x in sorted(labels, key=lambda x: x.get("finished", 0)) for a in x["accepted"]][-LATEST:]
        for x, a in recent:
            words = next((i.get("words") for i in x["judged"] if i["item"] == a["item"]), "")
            colour = COLOUR.get(a["answer"], "")
            out.append(f"{x['id']:14} \"{(words or '')[:30]}\" {DIM}{a['item'][:28]}{END} -> {a['name'][:40]:40} "
                       f"{DIM}{a['kind']:14} {a['by'] or '':4}{END} {colour}{a['answer']}{END}")
        if not recent:
            out.append(f"{DIM}none yet{END}")
        print("\033[2J\033[H" + "\n".join(out), flush=True)
        time.sleep(REFRESH)


if __name__ == "__main__":
    main()
