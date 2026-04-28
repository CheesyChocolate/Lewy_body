"""Differential protein analysis and LOD filtering."""

from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from tqdm import tqdm


def filter_by_lod(X: pd.DataFrame, lod_frac: float = 0.85) -> pd.DataFrame:
    """Drop proteins detected in fewer than lod_frac of samples.

    Olink NPX values are non-missing when above the LOD; NaN indicates
    below-LOD. Retains proteins with ≥85% non-missing values (paper: 665→664).
    """
    detected = X.notna().mean(axis=0)
    keep = detected[detected >= lod_frac].index
    return X[keep]


def differential_proteins(
    X: pd.DataFrame,
    meta: pd.DataFrame,
    group_a: str,
    group_b: str,
) -> pd.DataFrame:
    """Covariate-adjusted differential analysis for group_a vs group_b.

    Fits: protein ~ C(Dx_group) + Age + Sex  (nested linear model)
    using only samples from group_a and group_b.
    Returns DataFrame with columns: protein, effect, pval, qval, log2fc.

    Parameters
    ----------
    X : protein NPX DataFrame (samples × proteins)
    meta : metadata DataFrame with Dx_group, Age, Sex columns
    group_a : reference group label (e.g. 'CN')
    group_b : test group label (e.g. 'DLB')
    """
    mask = meta["Dx_group"].isin([group_a, group_b])
    X_sub = X.loc[mask]
    meta_sub = meta.loc[mask].copy()
    meta_sub["group"] = (meta_sub["Dx_group"] == group_b).astype(int)
    meta_sub["Sex_num"] = (meta_sub["Sex"].str.lower() == "male").astype(int)

    results = []
    for prot in tqdm(
        X_sub.columns, desc=f"{group_b} vs {group_a}", unit="protein", leave=False
    ):
        data = meta_sub.copy()
        data["y"] = X_sub[prot].values
        data = data.dropna(subset=["y", "Age", "Sex_num"])
        if data.shape[0] < 10:
            continue
        try:
            model = smf.ols("y ~ group + Age + Sex_num", data=data).fit()
            coef = model.params["group"]
            pval = model.pvalues["group"]
            log2fc = (
                X_sub[prot][meta_sub["Dx_group"] == group_b].mean()
                - X_sub[prot][meta_sub["Dx_group"] == group_a].mean()
            )
            results.append(
                {"protein": prot, "effect": coef, "pval": pval, "log2fc": log2fc}
            )
        except Exception:
            continue

    df = pd.DataFrame(results)
    if df.empty:
        return df
    _, qvals, _, _ = multipletests(df["pval"].values, method="fdr_bh")
    df["qval"] = qvals
    df = df.sort_values("qval")
    return df.reset_index(drop=True)
