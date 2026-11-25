"""Writes the body of Table 4 (paper_v2/sections/results.tex) from extra.json: method@3/@5 on one
line, bold and underline per column. Run after t4.py.
"""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = str(HERE) + '/'
P = str(HERE.parents[2] / 'paper_v2') + '/sections/results.tex'
d = json.load(open(D + 'extra.json'))
src = open(P).read()
a = src.index(r'\label{tab:res-retrieval}'); b0 = src.index(r'\midrule', a) + len(r'\midrule') + 1; b1 = src.index(r'\bottomrule', a)
body = src[b0:b1]
LAKES = [("BIRD", "bird_dev"), ("Spider", "spider_dev"), ("MMQA", "mmqa"), ("Spider~2.0-Lite", "spider2_lite")]
PAIRS = ["Dense", "MURRE", "BM25", "JAR", "Greedy JAR", "CRUSH4SQL"]
SINGLE = ["CORE-T", "Route+SQL", "Full schema"]
K = [("gold", k) for k in ("R", "CR", "P", "CR=")] + [("multi", k) for k in ("IR", "ICR", "IP", "IR=", "ICR=", "IP=")]
def strip(c):
    c = re.sub(r'\\(textbf|underline)\{([^}]*)\}', r'\2', c.strip())
    m = re.match(r'([0-9.]+)(.*)', c); return float(m.group(1)), m.group(2)
def vals(lake, n):
    g, m = d[f"{lake}/gold"].get(n), d[f"{lake}/multi"].get(n)
    if g is None: return None
    out = []
    for lab, k in K:
        v = g if lab == "gold" else m
        mk = ""  # Table 4 has no significance marks; Appendix D.2 (d2.py) has them
        out.append((round(v[k], 1), mk))
    return out, g
blocks = [x for x in body.split(r'\midrule') if x.strip()]
res = []
for (name, lake), blk in zip(LAKES, blocks):
    amigo = []
    for l in blk.strip('\n').split('\n'):
        if '&' not in l: continue
        cells = [c.strip() for c in l.rstrip(' \\').split('&')]
        if r'\sys' in cells[1]:
            amigo.append((cells[1], [[strip(c)] for c in cells[2:12]], cells[12:14]))
    comp = []
    for n in PAIRS:
        a3, g3 = vals(lake, f"{n}@3"); a5, g5 = vals(lake, f"{n}@5")
        comp.append((f"{n}@3/@5", [[x, y] for x, y in zip(a3, a5)], [f"{g3['sets']:.2f}", f"{g3['size']:.0f}/{g5['size']:.0f}"]))
    for n in SINGLE:
        if n == "Full schema" and lake != "bird_dev": continue
        r = vals(lake, n)
        if r is None: continue
        comp.append((n, [[x] for x in r[0]], [f"{r[1]['sets']:.2f}", f"{r[1]['size']:.2f}"]))
    rows = comp + [None] + amigo
    real = [r for r in rows if r]
    fmt = []
    for j in range(10):
        ds = sorted({v for r in real for (v, _) in r[1][j]}, reverse=True)
        fmt.append((ds[0], ds[1] if len(ds) > 1 else None))
    txt, first = [], True
    for r in rows:
        if r is None: txt.append(r'    \cmidrule(l){2-14}'); continue
        cells = []
        for j, parts in enumerate(r[1]):
            out = []
            for v, mk in parts:
                s = f"{v:.1f}"
                if v == fmt[j][0]: s = r'\textbf{' + s + '}'
                elif v == fmt[j][1]: s = r'\underline{' + s + '}'
                out.append(s + mk)
            cells.append("/".join(out))
        lead = f"    {name}" if first else "    "; first = False
        txt.append(f"{lead} & {r[0]} & " + " & ".join(cells) + " & " + " & ".join(r[2]) + r" \\")
    res.append("\n".join(txt) + "\n")
open(P, 'w').write(src[:b0] + "    \\midrule\n".join(res) + src[b1:])
print('ok')
