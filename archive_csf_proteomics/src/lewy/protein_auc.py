"""Per-protein covariate-adjusted AUC analysis.

Computes a standalone AUROC for each protein using a univariate logistic
regression (protein + Age + Sex), extending the paper's DDC spotlight to all
664 proteins systematically.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

from .data import PANEL_PROTEINS, encode_labels


def compute_protein_aucs(
    X: pd.DataFrame,
    meta: pd.DataFrame,
    group_a: str,
    group_b: str,
) -> pd.DataFrame:
    """Compute covariate-adjusted AUROC for each protein individually.

    For each protein fits: LogisticRegression([protein_npx, Age, Sex_num])
    and scores with roc_auc_score. Age and Sex are included as covariates
    to match the differential analysis and classification methodology.

    Parameters
    ----------
    X : protein NPX DataFrame (samples × proteins)
    meta : metadata DataFrame with Dx_group, Age, Sex columns
    group_a : negative group label (e.g. 'CN')
    group_b : positive group label (e.g. 'DLB')

    Returns
    -------
    DataFrame with columns [protein, auc, n_samples, n_positive, in_panel],
    sorted descending by AUC.
    """
    y = encode_labels(meta["Dx_group"], group_b, group_a)
    mask = y.notna()
    X_sub = X.loc[mask]
    y_sub = y.loc[mask].astype(int)
    meta_sub = meta.loc[mask].copy()
    meta_sub["Sex_num"] = (meta_sub["Sex"].str.lower() == "male").astype(float)

    scaler = StandardScaler()
    age_sex = scaler.fit_transform(meta_sub[["Age", "Sex_num"]].fillna(0))

    panel_set = set(PANEL_PROTEINS)
    results = []

    for prot in tqdm(
        X_sub.columns, desc=f"{group_b} vs {group_a}", unit="protein", leave=False
    ):
        npx = X_sub[prot].values
        valid = ~np.isnan(npx)
        if valid.sum() < 10:
            continue

        features = np.column_stack([npx[valid], age_sex[valid]])
        labels = y_sub.values[valid]

        if labels.sum() == 0 or labels.sum() == valid.sum():
            continue

        try:
            clf = LogisticRegression(solver="lbfgs", max_iter=500, random_state=42)
            clf.fit(features, labels)
            proba = clf.predict_proba(features)[:, 1]
            auc = roc_auc_score(labels, proba)
        except Exception:
            continue

        results.append(
            {
                "protein": prot,
                "auc": float(auc),
                "n_samples": int(valid.sum()),
                "n_positive": int(labels.sum()),
                "in_panel": prot in panel_set,
            }
        )

    df = (
        pd.DataFrame(results).sort_values("auc", ascending=False).reset_index(drop=True)
    )
    return df
