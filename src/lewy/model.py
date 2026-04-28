"""Elastic net classifier and repeated stratified cross-validation."""

from __future__ import annotations

import json
from pathlib import Path

import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")


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
    desc: str = "CV",
) -> np.ndarray:
    """Run repeated stratified k-fold CV and return per-fold AUROC array.

    Results are cached to cache_path (JSON) to avoid recomputation.
    """
    if cache_path is not None and cache_path.exists():
        with open(cache_path) as f:
            aucs = np.array(json.load(f))
        tqdm.write(f"  {desc}: loaded {len(aucs)} cached fold AUCs")
        return aucs

    X_arr = X.values
    y_arr = y.values
    aucs = []

    with tqdm(total=n_repeats, desc=f"  {desc}", unit="repeat") as pbar:
        for repeat in range(n_repeats):
            cv = StratifiedKFold(
                n_splits=n_splits, shuffle=True, random_state=random_state + repeat
            )
            for train_idx, test_idx in cv.split(X_arr, y_arr):
                clf_fold = clone(clf)
                clf_fold.fit(X_arr[train_idx], y_arr[train_idx])
                proba = clf_fold.predict_proba(X_arr[test_idx])[:, 1]
                aucs.append(roc_auc_score(y_arr[test_idx], proba))
            pbar.update(1)
            pbar.set_postfix(auc=f"{np.mean(aucs):.3f}")

    result = np.array(aucs)
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(result.tolist(), f)

    return result


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
