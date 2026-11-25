"""LaTeX rows of the top-k sweep tables from topk_scores.json (path in argv[1]): the body table
(mean and worst over the three benchmarks) and the appendix table (each benchmark, with stars).
Mean: mean of the per-benchmark values; worst: lowest score, largest number of sets."""
import json, statistics, sys

rows = json.load(open(sys.argv[1]))
LAKES = ["bird_dev", "spider_dev", "mmqa"]
NAMES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA"}
SETTINGS = ["judge", "1", "2", "3", "5", "10", "15", "20"]
by = {(r["lake"], r["label"], r["setting"], r["cut"]): r for r in rows}
lakes = [l for l in LAKES if (l, "gold", "judge", False) in by]


def name(s):
    return "Place judge" if s == "judge" else f"$k={s}$"


def v(lake, label, s, cut, score, star=False):
    r = by[(lake, label, s, cut)]
    x = f"{r[score]:.2f}" if score == "sets" else f"{r[score]:.1f}"
    if star and r.get(f"{score} p", 1) < 0.05:
        x += "$^*$"
    return x


def agg(label, s, cut, score, how):
    xs = [by[(l, label, s, cut)][score] for l in lakes]
    x = statistics.fmean(xs) if how == "mean" else (max(xs) if score == "sets" else min(xs))
    return f"{x:.2f}" if score == "sets" else f"{x:.1f}"


SV, MV = ("R", "CR", "P", "CR="), ("IR", "ICR", "IP", "IR=", "ICR=", "IP=")
print("% body table")
for s in SETTINGS:
    for how in ("mean", "worst"):
        cells = [name(s) if how == "mean" else "", how]
        cells += [agg("gold", s, False, k, how) for k in SV] + [agg("multi", s, False, k, how) for k in MV]
        cells += [" / ".join(v(l, "multi", s, False, "sets") for l in lakes) if how == "mean" else ""]
        cells += ["" if s == "judge" else agg(label, s, True, k, how) for label, k in (("gold", "CR"), ("multi", "IR"))]
        print("    " + " & ".join(cells) + r" \\")

print("% appendix table")
for lake in lakes:
    print(r"    \midrule")
    for i, s in enumerate(SETTINGS):
        cells = [NAMES[lake] if i == 0 else "", name(s)]
        cells += [v(lake, "gold", s, False, k, True) for k in SV] + [v(lake, "multi", s, False, k, True) for k in MV]
        cells += [v(lake, "multi", s, False, "sets")]
        cells += ["" if s == "judge" else v(lake, label, s, True, k, True) for label, k in (("gold", "CR"), ("multi", "IR"))]
        print("    " + " & ".join(cells) + r" \\")

print("% checks: n, capped, sets equal over labels")
for lake in lakes:
    for s in SETTINGS:
        g, m = by[(lake, "gold", s, False)], by[(lake, "multi", s, False)]
        print(lake, s, "n", g["n"], m["n"], "capped", g["capped"], "sets", round(g["sets"], 4), round(m["sets"], 4))
