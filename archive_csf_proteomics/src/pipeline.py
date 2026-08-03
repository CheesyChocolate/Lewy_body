"""CLI entrypoint — runs the full DLB CSF proteomics pipeline unattended."""

from __future__ import annotations

import json
from pathlib import Path

import click
import pandas as pd

from lewy.data import (
    PANEL_PROTEINS,
    encode_labels,
    load_discovery,
    load_validation,
)
from lewy.evaluate import format_metrics, roc_curve_data, validate_on_cohort
from lewy.features import differential_proteins, filter_by_lod
from lewy.model import (
    build_classifier,
    compute_auc_ci,
    repeated_stratified_cv,
    select_panel,
)
from lewy.plots import plot_forest, plot_roc, plot_violin, plot_volcano


@click.command()
@click.option(
    "--output-dir",
    default="results",
    show_default=True,
    type=click.Path(),
    help="Root directory for figures and metrics output.",
)
@click.option(
    "--full",
    is_flag=True,
    default=False,
    help="Run 1000 CV repeats (paper-faithful). Default is 100.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Ignore cached CV results and recompute.",
)
def main(output_dir: str, full: bool, no_cache: bool) -> None:
    """Reproduce DLB vs CN and DLB vs AD classifiers from del Campo et al. 2023."""
    out = Path(output_dir)
    fig_dir = out / "figures"
    met_dir = out / "metrics"
    fig_dir.mkdir(parents=True, exist_ok=True)
    met_dir.mkdir(parents=True, exist_ok=True)

    n_repeats = 1000 if full else 100
    click.echo(f"Output: {out}  |  CV repeats: {n_repeats}")

    # ── Phase 1: Load data ────────────────────────────────────────────────────
    click.echo("\n[1/6] Loading discovery cohort...")
    X, meta = load_discovery()
    X = filter_by_lod(X, lod_frac=0.85)
    click.echo(f"  Samples: {X.shape[0]}  Proteins after LOD filter: {X.shape[1]}")

    # ── Phase 2: Differential analysis ───────────────────────────────────────
    click.echo("\n[2/6] Differential protein analysis...")
    diff_dlb_cn = differential_proteins(X, meta, "CN", "DLB")
    diff_dlb_ad = differential_proteins(X, meta, "AD", "DLB")
    click.echo(
        f"  DLB vs CN: {(diff_dlb_cn['qval'] < 0.05).sum()} significant proteins (q<0.05)"
    )
    click.echo(
        f"  DLB vs AD: {(diff_dlb_ad['qval'] < 0.05).sum()} significant proteins (q<0.05)"
    )

    plot_volcano(diff_dlb_cn, title="DLB vs CN", out_dir=fig_dir)
    plot_volcano(diff_dlb_ad, title="DLB vs AD", out_dir=fig_dir)

    # ── Phase 3: Train classifiers ────────────────────────────────────────────
    click.echo("\n[3/6] Training elastic net classifiers...")
    discovery_aucs: dict = {}

    for pair, (pos, neg) in [
        ("DLB_vs_CN", ("DLB", "CN")),
        ("DLB_vs_AD", ("DLB", "AD")),
    ]:
        y = encode_labels(meta["Dx_group"], pos, neg).dropna()
        X_sub = X.loc[y.index]
        y_sub = y.astype(int)

        # Include age + sex as covariates alongside proteins
        cov = meta.loc[y.index, ["Age", "Sex"]].copy()
        cov["Sex_num"] = (cov["Sex"].str.lower() == "male").astype(float)
        cov = cov[["Age", "Sex_num"]]
        X_with_cov = pd.concat(
            [X_sub.reset_index(drop=True), cov.reset_index(drop=True)], axis=1
        )

        clf = build_classifier()
        cache = None if no_cache else met_dir / f"cv_aucs_{pair}.json"
        aucs = repeated_stratified_cv(
            clf, X_with_cov, y_sub, n_repeats=n_repeats, cache_path=cache, desc=pair
        )
        mean_auc, lo, hi = compute_auc_ci(aucs)
        click.echo(
            f"  {pair}: AUC={mean_auc:.3f} [{lo:.3f}–{hi:.3f}] (n={len(aucs)} folds)"
        )

        # Fit on full data for panel selection and ROC
        clf.fit(X_with_cov.values, y_sub.values)
        fpr, tpr, auc_full = roc_curve_data(clf, X_with_cov, y_sub)
        panel = select_panel(clf, X_with_cov.columns.tolist(), max_features=7)
        click.echo(f"  {pair} panel: {', '.join(panel)}")

        discovery_aucs[pair] = {
            "mean_auc": mean_auc,
            "ci_lower": lo,
            "ci_upper": hi,
            "n_folds": len(aucs),
            "full_fit_auc": auc_full,
            "panel": panel,
            "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        }

        plot_roc(
            {pair: (fpr, tpr, auc_full)},
            title=pair.replace("_", " "),
            out_dir=fig_dir,
        )

    with open(met_dir / "discovery_aucs.json", "w") as f:
        json.dump(format_metrics(discovery_aucs), f, indent=2)

    # ── Phase 4: Violin plots for panel proteins ──────────────────────────────
    click.echo("\n[4/6] Generating violin plots for panel proteins...")
    panel_present = [p for p in PANEL_PROTEINS if p in X.columns]
    plot_violin(X, meta, panel_present, out_dir=fig_dir)

    # ── Phase 5: Validation cohorts ───────────────────────────────────────────
    click.echo("\n[5/6] Validating on external cohorts...")

    # Retrain on 6-protein panel only (what validation cohorts have)
    val_proteins = [p for p in PANEL_PROTEINS if p != "FCER2"]
    val_aucs: dict = {}

    for pair, (pos, neg) in [
        ("DLB_vs_CN", ("DLB", "CN")),
        ("DLB_vs_AD", ("DLB", "AD")),
    ]:
        y = encode_labels(meta["Dx_group"], pos, neg).dropna()
        X_panel = X.loc[y.index, [p for p in val_proteins if p in X.columns]]
        cov = meta.loc[y.index, ["Age", "Sex"]].copy()
        cov["Sex_num"] = (cov["Sex"].str.lower() == "male").astype(float)
        X_train = pd.concat(
            [
                X_panel.reset_index(drop=True),
                cov[["Age", "Sex_num"]].reset_index(drop=True),
            ],
            axis=1,
        )
        clf_panel = build_classifier()
        clf_panel.fit(X_train.values, y.astype(int).values)

        val_aucs[pair] = {}
        for cohort_name, cohort_id in [
            ("validation_1", 1),
            ("validation_2", 2),
            ("autopsy", "autopsy"),
        ]:
            try:
                X_val, meta_val = load_validation(cohort_id)
                result = validate_on_cohort(clf_panel, X_val, meta_val, pos, neg)
                val_aucs[pair][cohort_name] = result
                click.echo(
                    f"  {pair} / {cohort_name}: AUC={result['auc']:.3f} (n={result['n_samples']})"
                )
            except Exception as e:
                click.echo(f"  {pair} / {cohort_name}: SKIPPED ({e})")

    with open(met_dir / "validation_aucs.json", "w") as f:
        json.dump(format_metrics(val_aucs), f, indent=2)

    # ── Phase 6: Forest plot ──────────────────────────────────────────────────
    click.echo("\n[6/6] Generating forest plot...")
    forest_data: dict = {}
    for pair in ("DLB_vs_CN", "DLB_vs_AD"):
        for cohort_name in ("validation_1", "validation_2", "autopsy"):
            entry = val_aucs.get(pair, {}).get(cohort_name)
            if entry:
                label = f"{pair.replace('_', ' ')} / {cohort_name}"
                auc = entry["auc"]
                forest_data[label] = (
                    auc,
                    auc - 0.05,
                    auc + 0.05,
                )  # placeholder CI for external cohorts

    if forest_data:
        plot_forest(forest_data, title="Validation cohort AUCs", out_dir=fig_dir)

    # ── Summary ───────────────────────────────────────────────────────────────
    click.echo("\n" + "=" * 60)
    click.echo("SUMMARY")
    click.echo("=" * 60)
    for pair, vals in discovery_aucs.items():
        click.echo(
            f"  {pair:20s}  AUC={vals['mean_auc']:.3f} "
            f"[{vals['ci_lower']:.3f}–{vals['ci_upper']:.3f}]"
        )
    click.echo(f"\nFigures saved to: {fig_dir}")
    click.echo(f"Metrics saved to: {met_dir}")


if __name__ == "__main__":
    main()
