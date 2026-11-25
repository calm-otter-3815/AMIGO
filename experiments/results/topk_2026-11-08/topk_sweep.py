"""Top-k ablation of the place judge: on each part keep the k places of lowest cost (ties by
similarity) in place of the place judge's yes, then run the search with a cap of CAP candidates
and the relaxed fallback, as abl_nojudge does. Also the place judge's own answers under the same
cap. No LLM call: places, stage and judge answers come from the saved answers of the 2026-11-08 run.
Run from the worktree root (campaign-1108). Args: lake [limit]. Writes topk_<lake>.jsonl here:
one line per question and setting with the table sets in order, whether the cap was hit,
whether the answer is relaxed, and the seconds spent."""
import json, os, pickle, sys, time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, "experiments"); sys.path.insert(0, ".")
import paper_results as P
from amigo import candidates, judge
from amigo.probe import Probe

CAP = 2000
KS = (1, 2, 3, 5, 10, 15, 20)
lake = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
HERE = Path(__file__).parent
import protocol
SRC = protocol.JOINCHOICE / lake / "amigo"  # the 2026-11-08 run
probe = Probe(lake)
graph = candidates.Graph(probe)


def search(stage, places):
    found = candidates.candidates(probe, graph, stage, CAP, graded=places)
    relaxed = not found
    if relaxed:
        found = judge.relaxed(probe, graph, stage, places, CAP, None)
    sets = [sorted(probe.path("table", t) for t in c.tables) for c in found]
    return sets, len(found) >= CAP, relaxed


def one(q):
    saved = pickle.loads((SRC / f"{q}.amigo.pkl").read_bytes())
    if saved["error"]:
        return [{"q": q, "setting": s, "error": saved["error"]} for s in ["judge", *map(str, KS)]]
    shown = [sorted(part, key=candidates.tie_order) for part in saved["shown"]]
    out = []
    settings = [("judge", judge.graded(saved["shown"], saved["grades"]))]
    settings += [(str(k), [part[:k] if k else part for part in shown]) for k in KS]
    for name, places in settings:
        started = time.monotonic()
        sets, capped, relaxed = search(saved["stage"], places)
        out.append({"q": q, "setting": name, "sets": sets, "capped": capped, "relaxed": relaxed,
                    "places": sum(map(len, places)), "seconds": round(time.monotonic() - started, 2)})
    return out


if __name__ == "__main__":
    ids = sorted(p.name.removesuffix(".amigo.pkl") for p in SRC.glob("*.amigo.pkl"))[:limit]
    path = HERE / f"topk_{lake}{'_try' if limit else ''}.jsonl"
    done = {json.loads(l)["q"] for l in path.open()} if path.exists() else set()
    todo = [q for q in ids if q not in done]
    with Pool(int(os.environ.get("WORKERS", "7"))) as pool, path.open("a") as f:
        for n, rows in enumerate(pool.imap_unordered(one, todo), 1):
            f.write("".join(json.dumps(r) + "\n" for r in rows)); f.flush()
            if n % 50 == 0:
                print(lake, n, "of", len(todo), flush=True)
    print(lake, "done", len(todo), flush=True)
