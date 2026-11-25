"""Two recap figures of the 2026-10-24 protocol run: retrieval (R, CR, P) and SQL (EX).

  .venv/bin/python experiments/plot_protocol.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "experiments" / "results" / "protocol_2026-10-24"
SQL = ROOT / "experiments" / "results" / "sqleval_2026-10-24"
LAKES = {"bird_dev": "BIRD", "spider_dev": "Spider", "mmqa": "MMQA"}
LABELS = {"gold": "gold label", "multi": "multi-valid label"}
WRITERS = {"qwen": "Qwen3.8 27B", "gemma": "Gemma 4 E4B", "granite": "Granite 4.2 8B"}
# bar order and color: the reference categorical palette, slots 1-7 in order
METHODS = {"AMIGO": "#2a78d6", "AMIGO top-1": "#eb6834", "AMIGO with hints": "#1baf7a",
           "CORE-T": "#eda100", "Route+SQL": "#e87ba4", "MURRE k3": "#008300", "Dense k3": "#6250d6"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def bars(ax, groups: list[str], values: dict[str, list], width: float = 0.8):
    """Grouped bars, one color per method; AMIGO's bars carry their value."""
    names = [m for m in METHODS if m in values]
    w = width / len(names)
    for i, m in enumerate(names):
        xs = [g + (i - (len(names) - 1) / 2) * w for g in range(len(groups))]
        for x, v in zip(xs, values[m]):
            if v is None:
                continue
            ax.bar(x, v, w * 0.85, color=METHODS[m], label=m, zorder=2)
            if m == "AMIGO":
                ax.text(x, v + 1.5, f"{v:.0f}", ha="center", va="bottom", fontsize=7.5, color=INK, fontweight="bold",
                        bbox={"fc": "white", "ec": "none", "pad": 0.6}, zorder=4)
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylim(0, 105)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(length=0)


def legend(fig, names, extra=()):
    handles = [plt.Rectangle((0, 0), 1, 1, color=METHODS[m]) for m in names] + [h for h, _ in extra]
    fig.legend(handles, list(names) + [t for _, t in extra], loc="lower center", ncol=len(handles),
               frameon=False, fontsize=8.5)


def retrieval():
    rows = [r for r in json.loads((RETRIEVAL / "retrieval.json").read_text()) if r["size"] == "all"]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4), sharey=True)
    names = [m for m in METHODS if m != "AMIGO with hints"]
    for i, label in enumerate(LABELS):
        for j, lake in enumerate(LAKES):
            got = {r["method"]: [r["R"], r["CR"], r["P"]] for r in rows if r["label"] == label and r["lake"] == lake}
            bars(axes[i, j], ["Recall", "Complete recall", "Precision"],
                 {m: got.get(m, [None] * 3) for m in names})
            axes[i, j].set_title(f"{LAKES[lake]}, {LABELS[label]}", fontsize=10, color=INK)
            if lake == "mmqa":
                axes[i, j].text(0.99, 0.98, "Route+SQL did not run on MMQA", transform=axes[i, j].transAxes,
                                ha="right", va="top", fontsize=7.5, color=MUTED)
        axes[i, 0].set_ylabel("score out of 100")
    fig.suptitle("Retrieval: did each method return the tables the question needs?", fontsize=12, color=INK)
    legend(fig, names)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(RETRIEVAL / "retrieval.png", dpi=180)


def sql():
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), sharey=True)
    for i, writer in enumerate(WRITERS):
        rows = json.loads((SQL / f"sql_{writer}.json").read_text())
        for j, lake in enumerate(LAKES):
            ex = {(r["label"], r["method"]): r["all"] for r in rows if r["lake"] == lake}
            ax = axes[i, j]
            bars(ax, list(LABELS.values()), {m: [ex.get((lb, m)) for lb in LABELS] for m in METHODS})
            for g, lb in enumerate(LABELS):  # the same writer handed the label's own tables
                ax.hlines(ex[lb, "Gold-table oracle"], g - 0.45, g + 0.45, colors=INK, linestyles="--", lw=1.2, zorder=3)
            ax.set_title(f"{LAKES[lake]}, writer {WRITERS[writer]}", fontsize=10, color=INK)
        axes[i, 0].set_ylabel("questions answered right, out of 100")
    fig.suptitle("SQL: does the SQL written from each method's tables return the right answer?", fontsize=12, color=INK)
    legend(fig, list(METHODS), [(plt.Line2D([], [], color=INK, ls="--", lw=1.2), "same writer, given the right tables")])
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(SQL / "sql.png", dpi=180)


if __name__ == "__main__":
    retrieval()
    sql()
    print(f"wrote {RETRIEVAL / 'retrieval.png'} and {SQL / 'sql.png'}")
