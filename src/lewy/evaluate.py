"""Evaluation utilities: ROC curves, AUC, and validation cohort assessment."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline


def roc_curve_data(
    clf: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (fpr, tpr, auc) for a fitted classifier."""
    proba = clf.predict_proba(X.values)[:, 1]
    fpr, tpr, _ = roc_curve(y.values, proba)
    auc = roc_auc_score(y.values, proba)
    return fpr, tpr, float(auc)


def validate_on_cohort(
    clf: Pipeline,
    X_val: pd.DataFrame,
    meta_val: pd.DataFrame,
    positive_label: str,
    negative_label: str,
) -> dict:
    """Evaluate a fitted clf on a validation cohort.

    Mirrors the training feature set: protein columns + Age + Sex_num covariates.
    Returns dict with fpr, tpr, auc, and n_samples.
    """
    from .data import encode_labels

    y_val = encode_labels(meta_val["Dx_group"], positive_label, negative_label)
    mask = y_val.notna()
    X_sub = X_val.loc[mask].copy()
    y_sub = y_val.loc[mask].astype(int)
    meta_sub = meta_val.loc[mask].copy()

    # Append Age + Sex_num covariates to match training feature set
    if "Age" in meta_sub.columns:
        X_sub["Age"] = meta_sub["Age"].values
    if "Sex" in meta_sub.columns:
        X_sub["Sex_num"] = (meta_sub["Sex"] == "Male").astype(float).values

    fpr, tpr, auc = roc_curve_data(clf, X_sub, y_sub)
    return {
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "auc": auc,
        "n_samples": int(mask.sum()),
        "n_positive": int(y_sub.sum()),
    }


def format_metrics(results: dict) -> dict:
    """Recursively convert numpy scalars to plain Python types for JSON serialisation."""
    out = {}
    for k, v in results.items():
        if isinstance(v, dict):
            out[k] = format_metrics(v)
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        elif isinstance(v, (np.integer, np.floating)):
            out[k] = v.item()
        else:
            out[k] = v
    return out
