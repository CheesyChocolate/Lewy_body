"""Data loading and preprocessing for DLB CSF proteomics datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "del_campo_2023"

DISCOVERY_FILE = DATA_DIR / "DataSet_PRIDE_DLBstudy.csv"
VALIDATION_FILES = {
    1: DATA_DIR / "DataSet_PRIDE_DLBstudy_clinical_validation1.csv",
    2: DATA_DIR / "DataSet_PRIDE_DLBstudy_clinical_validation2.csv",
    "autopsy": DATA_DIR / "DataSet_PRIDE_DLBstudy_autopsy.csv",
}

META_COLS_DISCOVERY = [
    "Dx_group",
    "Age",
    "Sex",
    "CSFAD_profile",
    "Park_med",
    "CSF_Abeta42",
    "CSF_tTau",
    "CSF_pTau181",
    "CSF_tTau_Abeta_ratio",
]

PANEL_PROTEINS = ["DDC", "FCER2", "CRH", "MMP3", "ABL1", "MMP10", "THOP1"]


def _harmonise_labels(series: pd.Series) -> pd.Series:
    """Map 'Control' → 'CN' for consistency across cohorts."""
    return series.replace({"Control": "CN"})


def load_discovery() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load discovery cohort, return (X_proteins, meta).

    Returns
    -------
    X : DataFrame of shape (534, 664) — protein NPX values
    meta : DataFrame of shape (534, 9) — demographic/clinical metadata
    """
    df = pd.read_csv(DISCOVERY_FILE, index_col=0)
    df = df.drop(columns=["filter_"], errors="ignore")
    df["Dx_group"] = _harmonise_labels(df["Dx_group"])
    meta = df[META_COLS_DISCOVERY].copy()
    protein_cols = [c for c in df.columns if c not in META_COLS_DISCOVERY]
    X = df[protein_cols].copy()
    return X, meta


def load_validation(
    cohort: Literal[1, 2, "autopsy"],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load a validation cohort, return (X_proteins, meta).

    Validation cohorts have only 6 panel proteins (FCER2 absent).
    """
    path = VALIDATION_FILES[cohort]
    df = pd.read_csv(path, index_col=0)
    df["Dx_group"] = _harmonise_labels(df["Dx_group"])

    known_meta = ["Dx_group", "Age", "Sex", "CSFAD_profile"]
    if cohort == "autopsy":
        known_meta = ["Dx_group", "Age", "Sex"]

    protein_cols = [c for c in df.columns if c not in known_meta]
    meta = df[[c for c in known_meta if c in df.columns]].copy()
    X = df[protein_cols].copy()
    return X, meta


def encode_labels(
    dx_group: pd.Series,
    positive: str,
    negative: str,
) -> pd.Series:
    """Binary encode labels: positive=1, negative=0, others NaN."""
    mapping = {positive: 1, negative: 0}
    return dx_group.map(mapping)


def get_protein_columns(df: pd.DataFrame) -> list[str]:
    """Return protein NPX column names (excludes metadata and filter_ artifact)."""
    exclude = set(META_COLS_DISCOVERY) | {"filter_"}
    return [c for c in df.columns if c not in exclude]


def split_features_meta(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a full DataFrame into (X_proteins, meta) based on known meta column names."""
    meta_present = [c for c in META_COLS_DISCOVERY if c in df.columns]
    protein_cols = get_protein_columns(df)
    return df[protein_cols].copy(), df[meta_present].copy()
