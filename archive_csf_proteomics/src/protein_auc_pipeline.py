"""Standalone CLI for per-protein AUC analysis.

Runs independently of pipeline.py — the original pipeline is untouched.
Computes a covariate-adjusted AUROC for each of the 664 discovery proteins
individually, for both DLB vs CN and DLB vs AD comparisons.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
import pandas as pd

from lewy.data import load_discovery
from lewy.evaluate import format_metrics
from lewy.features import filter_by_lod
from lewy.plots import plot_protein_aucs
from lewy.protein_auc import compute_protein_aucs


@click.command()
@click.option(
    "--output-dir",
    default="results",
    show_default=True,
    type=click.Path(),
    help="Root directory for figures and metrics output.",
)
@click.option(
    "--top-n",
    default=40,
    show_default=True,
    help="Number of top proteins to show in the figure.",
)
def main(output_dir: str, top_n: int) -> None:
    """Compute per-protein AUROCs for DLB vs CN and DLB vs AD."""
    out = Path(output_dir)
    fig_dir = out / "figures"
    met_dir = out / "metrics"
    fig_dir.mkdir(parents=True, exist_ok=True)
    met_dir.mkdir(parents=True, exist_ok=True)

    click.echo("[1/3] Loading discovery cohort...")
    X, meta = load_discovery()
    X = filter_by_lod(X, lod_frac=0.85)
    click.echo(f"  Samples: {X.shape[0]}  Proteins: {X.shape[1]}")

    click.echo("\n[2/3] Computing per-protein AUROCs...")
    auc_cn = compute_protein_aucs(X, meta, "CN", "DLB")
    auc_ad = compute_protein_aucs(X, meta, "AD", "DLB")

    met_dir.joinpath("protein_aucs_DLB_vs_CN.json").write_text(
        json.dumps(
            format_metrics({"proteins": auc_cn.to_dict(orient="records")}), indent=2
        )
    )
    met_dir.joinpath("protein_aucs_DLB_vs_AD.json").write_text(
        json.dumps(
            format_metrics({"proteins": auc_ad.to_dict(orient="records")}), indent=2
        )
    )

    click.echo("\n[3/3] Generating figure...")
    plot_protein_aucs(auc_cn, auc_ad, out_dir=fig_dir, top_n=top_n)

    click.echo("\n" + "=" * 60)
    click.echo("TOP 10 PROTEINS — DLB vs CN")
    click.echo("=" * 60)
    _print_top(auc_cn)

    click.echo("\n" + "=" * 60)
    click.echo("TOP 10 PROTEINS — DLB vs AD")
    click.echo("=" * 60)
    _print_top(auc_ad)

    click.echo(f"\nFigure : {fig_dir / 'protein_aucs.png'}")
    click.echo(f"Metrics: {met_dir / 'protein_aucs_DLB_vs_CN.json'}")


def _print_top(df: pd.DataFrame, n: int = 10) -> None:
    for i, row in df.head(n).iterrows():
        panel_marker = " *" if row["in_panel"] else ""
        click.echo(
            f"  {i+1:2d}. {row['protein']:12s}  AUC={row['auc']:.3f}{panel_marker}"
        )
    click.echo("  (* = panel protein)")


if __name__ == "__main__":
    main()
