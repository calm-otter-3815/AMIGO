"""Complete recall (y) against precision (x), one panel per benchmark and label set.
Reads points.json {"BENCH|gold|multi": {method: [[tables, R, CR, P], ...]}}, writes an SVG."""
import json, sys

pts = json.load(open(sys.argv[1]))
out = sys.argv[2]
STYLE = {  # color, marker
    "AMIGO": ("#2a78d6", "circle"), "dense": ("#eb6834", "square"), "JAR": ("#1baf7a", "diamond"),
    "CRUSH4SQL": ("#eda100", "tri"), "MURRE": ("#e87ba4", "trid"), "CORE-T": ("#008300", "star"),
    "Route+SQL": ("#6250d6", "plus"), "dense k=3+SQL": ("#e34948", "cross"),
}
BENCH = ["BIRD", "Spider", "MMQA"]
LAB = {"gold": "original labels (one gold query)", "multi": "extended labels (every valid answer)"}
PW, PH, L, T0, GAPX, GAPY = 440, 330, 80, 90, 120, 110
W = L + 2 * PW + GAPX + 40
H = T0 + 3 * PH + 2 * GAPY + 70
s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
     'font-family="Helvetica, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="#ffffff"/>']


def mark(kind, x, y, c, r=6):
    w = 'stroke="#ffffff" stroke-width="2"'
    if kind == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" {w}/>'
    if kind == "square":
        return f'<rect x="{x-r:.1f}" y="{y-r:.1f}" width="{2*r}" height="{2*r}" rx="1.5" fill="{c}" {w}/>'
    if kind == "diamond":
        return f'<polygon points="{x},{y-8} {x+8},{y} {x},{y+8} {x-8},{y}" fill="{c}" {w}/>'
    if kind == "tri":
        return f'<polygon points="{x},{y-8} {x+7},{y+6} {x-7},{y+6}" fill="{c}" {w}/>'
    if kind == "trid":
        return f'<polygon points="{x},{y+8} {x+7},{y-6} {x-7},{y-6}" fill="{c}" {w}/>'
    if kind == "star":
        import math
        p = " ".join(f"{x+(9 if i%2==0 else 4)*math.sin(i*math.pi/5):.1f},{y-(9 if i%2==0 else 4)*math.cos(i*math.pi/5):.1f}" for i in range(10))
        return f'<polygon points="{p}" fill="{c}" {w}/>'
    if kind == "plus":
        return f'<path d="M{x-7},{y}H{x+7}M{x},{y-7}V{y+7}" stroke="{c}" stroke-width="3.5" stroke-linecap="round"/>'
    return f'<path d="M{x-6},{y-6}L{x+6},{y+6}M{x-6},{y+6}L{x+6},{y-6}" stroke="{c}" stroke-width="3.5" stroke-linecap="round"/>'


# legend
x = L + 6
for m, (c, k) in STYLE.items():
    s.append(mark(k, x, 30, c))
    s.append(f'<text x="{x+12}" y="35" font-size="14" fill="#222">{m}</text>')
    x += 12 + 8.6 * len(m) + 30
s.append(f'<text x="{L}" y="60" font-size="12" fill="#555">Each line joins the same method at 1, 3, 5, 10 tables per question; '
         'a single mark is a method with no table budget. Up and right is better.</text>')

for r, b in enumerate(BENCH):
    for col, lab in enumerate(["gold", "multi"]):
        x0, y0 = L + col * (PW + GAPX), T0 + r * (PH + GAPY)
        X = lambda p: x0 + p / 100 * PW
        Y = lambda v: y0 + PH - v / 100 * PH
        s.append(f'<text x="{x0}" y="{y0-14}" font-size="16" font-weight="bold" fill="#111">{b}, {LAB[lab]}</text>')
        for v in range(0, 101, 20):
            s.append(f'<line x1="{X(v)}" y1="{y0}" x2="{X(v)}" y2="{y0+PH}" stroke="#e6e6e6"/>')
            s.append(f'<line x1="{x0}" y1="{Y(v)}" x2="{x0+PW}" y2="{Y(v)}" stroke="#e6e6e6"/>')
            s.append(f'<text x="{X(v)}" y="{y0+PH+18}" font-size="12" fill="#555" text-anchor="middle">{v}%</text>')
            s.append(f'<text x="{x0-8}" y="{Y(v)+4}" font-size="12" fill="#555" text-anchor="end">{v}%</text>')
        s.append(f'<text x="{x0+PW/2}" y="{y0+PH+40}" font-size="13" fill="#333" text-anchor="middle">precision</text>')
        s.append(f'<text x="{x0-52}" y="{y0+PH/2}" font-size="13" fill="#333" text-anchor="middle" '
                 f'transform="rotate(-90 {x0-52} {y0+PH/2})">complete recall</text>')
        panel = pts.get(f"{b}|{lab}", {})
        if not panel:
            s.append(f'<text x="{x0+PW/2}" y="{y0+PH/2}" font-size="14" fill="#888" text-anchor="middle">not scored yet</text>')
        for m, (c, k) in STYLE.items():
            ps = sorted(panel.get(m, []), key=lambda p: p[0])
            if len(ps) > 1:
                d = " ".join(f"{X(p[3]):.1f},{Y(p[2]):.1f}" for p in ps)
                s.append(f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width="2.2"/>')
            s += [mark(k, X(p[3]), Y(p[2]), c) for p in ps]
        notes = pts.get("notes", {}).get(f"{b}|{lab}")
        if notes:
            s.append(f'<text x="{x0+PW}" y="{y0+PH-8}" font-size="12" fill="#888" text-anchor="end">{notes}</text>')
s.append("</svg>")
open(out, "w").write("\n".join(s))
