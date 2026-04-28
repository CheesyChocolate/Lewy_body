"""Generate a presentation-sized protein AUC figure (top 20) from cached JSON."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

METRICS = Path(__file__).parents[3] / "results" / "metrics"
OUT = Path(__file__).parent / "protein_aucs_pres.png"
TOP_N = 20

PANEL_COLOR = "#e74c3c"
DEFAULT_COLOR = "#95a5a6"
STYLE = {
    "figure.dpi": 150,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def load(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text())
    key = "proteins" if "proteins" in data else list(data.keys())[0]
    records = data[key] if isinstance(data[key], list) else data[key]
    return (
        pd.DataFrame(records).sort_values("auc", ascending=False).reset_index(drop=True)
    )


auc_cn = load(METRICS / "protein_aucs_DLB_vs_CN.json")
auc_ad = load(METRICS / "protein_aucs_DLB_vs_AD.json")

with plt.rc_context(STYLE):
    fig, axes = plt.subplots(1, 2, figsize=(13, TOP_N * 0.28 + 2), sharey=False)

    for ax, auc_df, title in zip(axes, [auc_cn, auc_ad], ["DLB vs CN", "DLB vs AD"]):
        top = auc_df.head(TOP_N).copy()
        colors = [PANEL_COLOR if f else DEFAULT_COLOR for f in top["in_panel"]]

        ax.barh(
            range(len(top)), top["auc"], color=colors, edgecolor="none", height=0.72
        )
        ax.axvline(0.5, color="#bdc3c7", lw=1.2, ls="--", label="0.5 (chance)")
        ax.axvline(0.8, color="#e67e22", lw=1.2, ls="--", label="0.8 (good)")

        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top["protein"], fontsize=9)
        ax.invert_yaxis()
        ax.set_xlim(0.4, 1.02)
        ax.set_xlabel("AUROC", fontsize=10)
        ax.set_title(title, fontweight="bold", fontsize=11)
        ax.legend(fontsize=8, loc="lower right")

        for i, (_, row) in enumerate(top.iterrows()):
            if row["in_panel"]:
                ax.get_yticklabels()[i].set_color(PANEL_COLOR)
                ax.get_yticklabels()[i].set_fontweight("bold")

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=PANEL_COLOR, label="Panel protein"),
        Patch(facecolor=DEFAULT_COLOR, label="Other protein"),
    ]
    fig.legend(
        handles=legend_elements,
        loc="lower center",
        ncol=2,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

print(f"Saved: {OUT}")
