"""Generate pipeline architecture figure for the presentation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "pipeline_arch.png"

MODULES = [
    ("data.py", "Load & harmonise\nCSF samples"),
    ("features.py", "Differential\nanalysis + LOD"),
    ("model.py", "Elastic net\nclassifier + CV"),
    ("evaluate.py", "ROC / AUC\nvalidation"),
    ("plots.py", "Figures\n& reports"),
]

ARROWS = [
    "X, meta",
    "diff results",
    "clf, AUCs",
    "fpr/tpr",
]

BOX_W = 1.6
BOX_H = 0.8
GAP = 0.55
START_X = 0.3
Y = 1.2

fig, ax = plt.subplots(figsize=(12, 3))
ax.set_xlim(0, 12)
ax.set_ylim(0, 2.4)
ax.axis("off")

BOX_COLOR = "#2c3e50"
TEXT_COLOR = "white"
ARROW_COLOR = "#7f8c8d"
LABEL_COLOR = "#2980b9"

for i, (name, role) in enumerate(MODULES):
    x = START_X + i * (BOX_W + GAP)
    box = FancyBboxPatch(
        (x, Y - BOX_H / 2),
        BOX_W,
        BOX_H,
        boxstyle="round,pad=0.08",
        facecolor=BOX_COLOR,
        edgecolor="none",
        zorder=3,
    )
    ax.add_patch(box)
    ax.text(
        x + BOX_W / 2,
        Y + 0.1,
        name,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=TEXT_COLOR,
        zorder=4,
    )
    ax.text(
        x + BOX_W / 2,
        Y - 0.22,
        role,
        ha="center",
        va="center",
        fontsize=7.5,
        color="#bdc3c7",
        zorder=4,
    )

for i, label in enumerate(ARROWS):
    x_start = START_X + (i + 1) * BOX_W + i * GAP
    x_end = x_start + GAP
    ax.annotate(
        "",
        xy=(x_end, Y),
        xytext=(x_start, Y),
        arrowprops=dict(
            arrowstyle="->,head_width=0.25,head_length=0.12",
            color=ARROW_COLOR,
            lw=1.5,
        ),
        zorder=2,
    )
    ax.text(
        (x_start + x_end) / 2,
        Y + 0.32,
        label,
        ha="center",
        va="center",
        fontsize=7,
        color=LABEL_COLOR,
        style="italic",
    )

ax.text(
    6.0,
    2.18,
    "src/lewy/ — modular Python package",
    ha="center",
    va="center",
    fontsize=10,
    fontweight="bold",
    color="#2c3e50",
)

fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
