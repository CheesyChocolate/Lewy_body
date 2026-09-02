"""Run Stage 6 nested CV on the full extracted feature set and report results.

Usage: uv run python3 scripts/run_nested_cv.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dlb_radiomics.classify import nested_cv

FEATURES_PATH = Path("data/adni/features.csv")
RESULTS_PATH = Path("data/adni/nested_cv_results.csv")


def main() -> None:
    df = pd.read_csv(FEATURES_PATH)
    y = df["label"]
    X = df.drop(columns=["PTID", "RID", "label"])

    print(f"{len(df)} subjects, {X.shape[1]} features, {y.sum()} positive", flush=True)

    results = nested_cv(X, y)
    results.to_csv(RESULTS_PATH, index=False)

    print(results.to_string(index=False), flush=True)
    print(
        f"\nmean AUC-ROC: {results['auc_roc'].mean():.3f} "
        f"+/- {results['auc_roc'].std():.3f}",
        flush=True,
    )
    print(
        f"mean accuracy: {results['accuracy'].mean():.3f} "
        f"+/- {results['accuracy'].std():.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
