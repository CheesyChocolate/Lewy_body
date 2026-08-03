"""Generate AUC comparison bar chart (our results vs paper) for the presentation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent / "auc_comparison.png"

comparisons = ["DLB vs CN", "DLB vs AD"]
our_aucs = [0.986, 0.937]
paper_aucs = [0.947, 0.929]
our_ci_lo = [0.962, 0.877]
our_ci_hi = [1.000, 0.985]

x = np.arange(len(comparisons))
width = 0.32

STYLE = {
    "figure.dpi": 150,
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
}

with plt.rc_context(STYLE):
    fig, ax = plt.subplots(figsize=(7, 5))

    err_lo = [o - lo for o, lo in zip(our_aucs, our_ci_lo)]
    err_hi = [hi - o for o, hi in zip(our_aucs, our_ci_hi)]

    bars_our = ax.bar(
        x - width / 2,
        our_aucs,
        width,
        label="Our reimplementation",
        color="#2980b9",
        zorder=3,
        yerr=[err_lo, err_hi],
        capsize=6,
        error_kw={"elinewidth": 1.8, "ecolor": "#1a5276"},
    )
    bars_paper = ax.bar(
        x + width / 2,
        paper_aucs,
        width,
        label="del Campo et al. (2023)",
        color="#95a5a6",
        zorder=3,
    )

    ax.axhline(0.9, color="#e67e22", lw=1.2, ls="--", zorder=2, label="AUC = 0.90")

    for bar, val in zip(bars_our, our_aucs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.006,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color="#1a5276",
        )
    for bar, val in zip(bars_paper, paper_aucs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.006,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#5d6d7e",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(comparisons, fontsize=12)
    ax.set_ylabel("AUROC", fontsize=11)
    ax.set_ylim(0.85, 1.04)
    ax.set_title("Discovery Cohort AUC — Recreation vs Paper", fontsize=11)
    ax.legend(fontsize=9, loc="lower right")
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

print(f"Saved: {OUT}")
