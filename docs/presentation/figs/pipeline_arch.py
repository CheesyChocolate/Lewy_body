"""Generate pipeline architecture figure for the presentation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "pipeline_arch.png"

STAGES = [
    ("Raw CSF Data", "534 samples\n664 proteins"),
    ("Differential\nAnalysis", "OLS per protein\nBH FDR q<0.05"),
    ("Elastic Net\nClassifier", "5-fold × 100 CV\nAge + Sex covariates"),
    ("AUC\nEvaluation", "Mean ± 95% CI\n500 held-out folds"),
    ("Figures &\nMetrics", "ROC, volcano\nranked proteins"),
]

ARROWS = ["X, meta", "sig. proteins", "clf, AUCs", "fpr / tpr"]

BOX_W = 1.55
BOX_H = 1.05
GAP = 0.42
START_X = 0.2
Y = 1.3
TOTAL_W = len(STAGES) * BOX_W + (len(STAGES) - 1) * GAP + 2 * START_X

fig, ax = plt.subplots(figsize=(TOTAL_W, 2.9))
ax.set_xlim(0, TOTAL_W)
ax.set_ylim(0, 2.6)
ax.axis("off")

BOX_COLOR = "#2c3e50"
TEXT_COLOR = "white"
SUB_COLOR = "#bdc3c7"
ARROW_COLOR = "#7f8c8d"
LABEL_COLOR = "#2980b9"

for i, (title, subtitle) in enumerate(STAGES):
    x = START_X + i * (BOX_W + GAP)
    box = FancyBboxPatch(
        (x, Y - BOX_H / 2),
        BOX_W,
        BOX_H,
        boxstyle="round,pad=0.07",
        facecolor=BOX_COLOR,
        edgecolor="none",
        zorder=3,
    )
    ax.add_patch(box)
    ax.text(
        x + BOX_W / 2,
        Y + 0.18,
        title,
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=TEXT_COLOR,
        zorder=4,
        linespacing=1.3,
    )
    ax.text(
        x + BOX_W / 2,
        Y - 0.28,
        subtitle,
        ha="center",
        va="center",
        fontsize=9,
        color=SUB_COLOR,
        zorder=4,
        linespacing=1.3,
    )

for i, label in enumerate(ARROWS):
    x_start = START_X + (i + 1) * BOX_W + i * GAP
    x_end = x_start + GAP
    ax.annotate(
        "",
        xy=(x_end, Y),
        xytext=(x_start, Y),
        arrowprops=dict(
            arrowstyle="->,head_width=0.22,head_length=0.10",
            color=ARROW_COLOR,
            lw=1.6,
        ),
        zorder=2,
    )
    ax.text(
        (x_start + x_end) / 2,
        Y + 0.42,
        label,
        ha="center",
        va="center",
        fontsize=8,
        color=LABEL_COLOR,
        style="italic",
    )

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
