"""Writes the bodies of the four Appendix D.2 tables (paper_v2/sections/appendix_results.tex) from
full.json, with AMIGO rows, bold, underline and significance marks. Run after full.py and gen2.py.
"""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = str(HERE) + '/'
f = json.load(open(D + 'full.json'))
RES = open(str(HERE.parents[2] / 'paper_v2') + '/sections/results.tex').read()
P = str(HERE.parents[2] / 'paper_v2') + '/sections/appendix_results.tex'
s = open(P).read()
K = [("gold", k) for k in ("R", "CR", "P", "CR=")] + [("multi", k) for k in ("IR", "ICR", "IP", "IR=", "ICR=", "IP=")]
ORDER = [f"{n}@{k}" for n in ("Dense", "BM25", "Hybrid", "JAR", "Greedy JAR", "MURRE", "CRUSH4SQL") for k in (1, 3, 5)] + ["CORE-T", "Route+SQL", "Full schema"]
# AMIGO informed from Table 4 (block of each benchmark)
a = RES.index(r'\label{tab:res-retrieval}'); b = RES.index(r'\bottomrule', a)
inf = [l for l in RES[a:b].split('\n') if r'\sys informed' in l]
def nums(l):
    c = [x.strip() for x in l.rstrip(' \\').split('&')]
    return [float(re.sub(r'\\(textbf|underline)\{([^}]*)\}', r'\2', x)) for x in c[2:12]], c[13]
LAKES = [("tab:app-k-sv", "bird_dev"), ("tab:app-k-mv", "spider_dev"), ("tab:app-k-mmqa", "mmqa"), ("tab:app-k-spider2", "spider2_lite")]
for idx, (lab, lake) in enumerate(LAKES):
    g, m = f[f"{lake}/gold"], f[f"{lake}/multi"]
    rows = []
    def row(name, key):
        cells = []
        for labl, k in K:
            v = (g if labl == "gold" else m)[key]
            t = v.get(k + " test"); mk = ""
            if t: mk = r"$^\circ$" if t[1] >= 0.05 else (r"$^\bullet$" if t[0] < 0 else "")
            cells.append((round(v[k], 1), mk))
        return (name, cells, f"{g[key]['size']:.2f}")
    for n in ORDER:
        rows.append(row(n, n) if n in g else (n, None, "n/a"))
    rows.append(None)
    rows.append(row(r"\sys lazy", "AMIGO"))
    rows.append(row(r"\sys conservative", "AMIGO conservative"))
    iv, isz = nums(inf[idx])
    rows.append((r"\sys informed$^\dagger$", [(x, "") for x in iv], isz))
    real = [r for r in rows if r and r[1]]
    fmt = []
    for j in range(10):
        ds = sorted({r[1][j][0] for r in real}, reverse=True); fmt.append((ds[0], ds[1]))
    out = []
    for r in rows:
        if r is None: out.append(r"    \midrule"); continue
        if r[1] is None: out.append(f"    {r[0]} & " + " & ".join(["n/a"] * 11) + r" \\"); continue
        cs = []
        for j, (v, mk) in enumerate(r[1]):
            x = f"{v:.1f}"
            if v == fmt[j][0]: x = r'\textbf{' + x + '}'
            elif v == fmt[j][1]: x = r'\underline{' + x + '}'
            cs.append(x + mk)
        out.append(f"    {r[0]} & " + " & ".join(cs) + f" & {r[2]}" + r" \\")
    k0 = s.index(r'\label{' + lab + '}'); m0 = s.index(r'\midrule', k0) + len(r'\midrule') + 1; m1 = s.index(r'\bottomrule', k0)
    s = s[:m0] + "\n".join(out) + "\n" + s[m1:]
open(P, 'w').write(s); print('ok')
