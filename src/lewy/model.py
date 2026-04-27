"""Elastic net classifier and repeated stratified cross-validation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_classifier(l1_ratios: list[float] | None = None) -> Pipeline:
    """Return sklearn Pipeline: StandardScaler → ElasticNet LogisticRegressionCV.

    l1_ratios=0 is pure ridge; l1_ratios=1 is pure lasso.
    Cross-validated over C (inverse regularisation) and l1_ratio.
    """
    if l1_ratios is None:
        l1_ratios = [0.0, 0.1, 0.5, 0.9, 1.0]
    clf = LogisticRegressionCV(
        solver="saga",
        cv=5,
        Cs=20,
        l1_ratios=l1_ratios,
        scoring="neg_log_loss",
        max_iter=2000,
        random_state=42,
        n_jobs=-1,
        use_legacy_attributes=False,
    )
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def repeated_stratified_cv(
    clf: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    n_repeats: int = 100,
    random_state: int = 42,
    cache_path: Path | None = None,
) -> np.ndarray:
    """Run repeated stratified k-fold CV and return per-fold AUROC array.

    Results are cached to cache_path (JSON) to avoid recomputation.
    """
    if cache_path is not None and cache_path.exists():
        with open(cache_path) as f:
            return np.array(json.load(f))

    cv = RepeatedStratifiedKFold(
        n_splits=n_splits, n_repeats=n_repeats, random_state=random_state
    )
    aucs = cross_val_score(
        clf,
        X.values,
        y.values,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
    )

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(aucs.tolist(), f)

    return aucs


def compute_auc_ci(aucs: np.ndarray, ci: float = 0.95) -> tuple[float, float, float]:
    """Return (mean_auc, lower_ci, upper_ci) by percentile method."""
    alpha = (1 - ci) / 2
    lower = float(np.percentile(aucs, 100 * alpha))
    upper = float(np.percentile(aucs, 100 * (1 - alpha)))
    return float(np.mean(aucs)), lower, upper


def select_panel(
    clf: Pipeline,
    feature_names: list[str],
    max_features: int = 7,
) -> list[str]:
    """Return top proteins by absolute coefficient magnitude from a fitted clf."""
    coefs = clf.named_steps["clf"].coef_[0]
    indices = np.argsort(np.abs(coefs))[::-1][:max_features]
    return [feature_names[i] for i in indices]
