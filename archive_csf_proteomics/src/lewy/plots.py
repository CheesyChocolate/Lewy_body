"""Figures replicating del Campo et al. (2023) visualisations."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from adjustText import adjust_text

FIGURE_DIR = Path(__file__).parent.parent.parent / "results" / "figures"
STYLE = {
    "figure.dpi": 150,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def _save(fig: plt.Figure, name: str, out_dir: Path | None = None) -> None:
    d = out_dir or FIGURE_DIR
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_volcano(
    diff_results: pd.DataFrame,
    title: str = "Differential proteins",
    label_top_n: int = 10,
    out_dir: Path | None = None,
) -> None:
    """Volcano plot: log2FC vs -log10(q-value). Replicates Fig 1b."""
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(6, 5))
        sig = diff_results["qval"] < 0.05
        colors = np.where(sig, "#e74c3c", "#95a5a6")
        ax.scatter(
            diff_results["log2fc"],
            -np.log10(diff_results["qval"]),
            c=colors,
            s=12,
            alpha=0.7,
        )
        ax.axhline(-np.log10(0.05), color="gray", lw=0.8, ls="--")
        ax.set_xlabel("log2 fold change")
        ax.set_ylabel("-log10(q-value)")
        ax.set_title(title)

        top = diff_results.nsmallest(label_top_n, "qval")
        texts = [
            ax.text(row["log2fc"], -np.log10(row["qval"]), row["protein"], fontsize=7)
            for _, row in top.iterrows()
        ]
        adjust_text(
            texts, ax=ax, arrowprops={"arrowstyle": "-", "color": "gray", "lw": 0.5}
        )
        _save(fig, f"volcano_{title.replace(' ', '_')}", out_dir)


def plot_roc(
    roc_data: dict[str, tuple[np.ndarray, np.ndarray, float]],
    title: str = "ROC curves",
    out_dir: Path | None = None,
) -> None:
    """ROC curves for one or more classifiers. Replicates Fig 2b."""
    palette = sns.color_palette("tab10", len(roc_data))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(5, 5))
        for (label, (fpr, tpr, auc)), color in zip(roc_data.items(), palette):
            ax.plot(fpr, tpr, lw=1.8, color=color, label=f"{label} (AUC={auc:.3f})")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_xlabel("1 – Specificity")
        ax.set_ylabel("Sensitivity")
        ax.set_title(title)
        ax.legend(fontsize=8)
        _save(fig, f"roc_{title.replace(' ', '_')}", out_dir)


def plot_forest(
    auc_ci: dict[str, tuple[float, float, float]],
    title: str = "Validation AUCs",
    out_dir: Path | None = None,
) -> None:
    """Forest plot of AUC ± 95% CI across cohorts. Replicates Fig 3b summary."""
    labels = list(auc_ci.keys())
    means = [v[0] for v in auc_ci.values()]
    lowers = [v[1] for v in auc_ci.values()]
    uppers = [v[2] for v in auc_ci.values()]
    y = np.arange(len(labels))

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(5, 0.8 * len(labels) + 1))
        ax.errorbar(
            means,
            y,
            xerr=[
                np.array(means) - np.array(lowers),
                np.array(uppers) - np.array(means),
            ],
            fmt="o",
            color="#2980b9",
            capsize=4,
            lw=1.5,
        )
        ax.axvline(0.5, color="gray", lw=0.8, ls="--")
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_xlim(0.4, 1.05)
        ax.set_xlabel("AUROC")
        ax.set_title(title)
        _save(fig, f"forest_{title.replace(' ', '_')}", out_dir)


def plot_violin(
    X: pd.DataFrame,
    meta: pd.DataFrame,
    proteins: list[str],
    out_dir: Path | None = None,
) -> None:
    """Violin plots of NPX abundance per diagnosis group. Replicates Fig 2c."""
    order = ["CN", "AD", "DLB"]
    palette = {"CN": "#3498db", "AD": "#e67e22", "DLB": "#e74c3c"}
    n = len(proteins)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(nrows, ncols, figsize=(3.5 * ncols, 3.5 * nrows))
        axes = np.array(axes).flatten() if n > 1 else [axes]

        for ax, prot in zip(axes, proteins):
            data = meta[["Dx_group"]].copy()
            data["NPX"] = X[prot].values if prot in X.columns else np.nan
            data = data[data["Dx_group"].isin(order)]
            sns.violinplot(
                data=data,
                x="Dx_group",
                y="NPX",
                order=order,
                palette=palette,
                ax=ax,
                inner="box",
            )
            ax.set_title(prot, fontsize=9)
            ax.set_xlabel("")
            ax.set_ylabel("NPX")

        for ax in axes[n:]:
            ax.set_visible(False)

        fig.tight_layout()
        _save(fig, "violin_panel_proteins", out_dir)


def plot_protein_aucs(
    auc_cn: pd.DataFrame,
    auc_ad: pd.DataFrame,
    out_dir: Path | None = None,
    top_n: int = 40,
) -> None:
    """Ranked bar chart of per-protein AUROCs for DLB vs CN and DLB vs AD.

    Shows the top_n proteins by AUC in each comparison. Panel proteins are
    highlighted in a distinct colour. Reference lines at AUC=0.5 and AUC=0.8.
    Saves as protein_aucs.png.
    """
    PANEL_COLOR = "#e74c3c"
    DEFAULT_COLOR = "#95a5a6"
    REF_COLORS = {"0.5 (chance)": "#bdc3c7", "0.8 (good)": "#e67e22"}

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(14, top_n * 0.22 + 2), sharey=False)

        for ax, auc_df, title in zip(
            axes,
            [auc_cn, auc_ad],
            ["DLB vs CN", "DLB vs AD"],
        ):
            top = auc_df.head(top_n).copy()
            colors = [
                PANEL_COLOR if flag else DEFAULT_COLOR for flag in top["in_panel"]
            ]

            ax.barh(
                range(len(top)),
                top["auc"],
                color=colors,
                edgecolor="none",
                height=0.75,
            )
            ax.axvline(
                0.5,
                color=REF_COLORS["0.5 (chance)"],
                lw=1.2,
                ls="--",
                label="0.5 (chance)",
            )
            ax.axvline(
                0.8, color=REF_COLORS["0.8 (good)"], lw=1.2, ls="--", label="0.8 (good)"
            )

            ax.set_yticks(range(len(top)))
            ax.set_yticklabels(top["protein"], fontsize=7)
            ax.invert_yaxis()
            ax.set_xlim(0.4, 1.02)
            ax.set_xlabel("AUROC")
            ax.set_title(title, fontweight="bold")
            ax.legend(fontsize=7, loc="lower right")

            # Highlight panel protein labels
            for i, (_, row) in enumerate(top.iterrows()):
                if row["in_panel"]:
                    ax.get_yticklabels()[i].set_color(PANEL_COLOR)
                    ax.get_yticklabels()[i].set_fontweight("bold")

        # Shared legend for bar colours
        from matplotlib.patches import Patch

        legend_elements = [
            Patch(facecolor=PANEL_COLOR, label="Panel protein"),
            Patch(facecolor=DEFAULT_COLOR, label="Other protein"),
        ]
        fig.legend(
            handles=legend_elements,
            loc="lower center",
            ncol=2,
            fontsize=8,
            bbox_to_anchor=(0.5, -0.01),
        )
        fig.tight_layout(rect=[0, 0.03, 1, 1])
        _save(fig, "protein_aucs", out_dir)
