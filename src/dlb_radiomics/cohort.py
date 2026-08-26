"""Cohort assembly and one-scan-per-subject selection.

Combines the SAA-positive and SAA-negative cohort CSVs into a single labeled cohort,
maps RID -> PTID (needed to locate each subject's image directory under
data/adni/images/), and picks the single scan per subject/modality closest to each
subject's target exam date. See docs/DECISIONS.md and docs/TODO.md ("Stage 3") for
context.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydicom

from dlb_radiomics.ingest import detect_format

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "adni"

# select_closest_series rejects any candidate farther than this from the target date --
# a defensive guard, not load-bearing against current data (every currently-resolved PET
# series matches its target exam date exactly, see docs/DECISIONS.md "Modality mismatch
# bug"), but stops a future/edge-case subject with no real scan on disk from silently
# resolving to an unrelated, distant series instead of None.
MAX_SERIES_DATE_OFFSET_DAYS = 90


def load_cohort(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load and concatenate the SAA-positive and SAA-negative cohort CSVs.

    Adds a `label` column derived from `SAA_RESULT` (1 for "Detected-1", 0 for
    "Not_Detected"; other SAA_RESULT values, e.g. "Indeterminate"/"Detected-2", are
    dropped since this project's target is strictly Detected-1 vs Not_Detected).
    """
    positive = pd.read_csv(data_dir / "dlb_cohort_candidates.csv")
    negative = pd.read_csv(data_dir / "saa_negative_controls.csv")
    cohort = pd.concat([positive, negative], ignore_index=True)

    cohort = cohort[cohort["SAA_RESULT"].isin(["Detected-1", "Not_Detected"])].copy()
    cohort["label"] = (cohort["SAA_RESULT"] == "Detected-1").astype(int)

    roster = pd.read_csv(data_dir / "tables" / "ROSTER.csv")[["RID", "PTID"]]
    roster = roster.drop_duplicates(subset="RID")
    cohort = cohort.merge(roster, on="RID", how="left")

    missing_ptid = cohort["PTID"].isna().sum()
    if missing_ptid:
        raise ValueError(
            f"{missing_ptid} cohort RIDs have no PTID in ROSTER.csv (cannot locate "
            "their image directories)"
        )

    return cohort


def find_series_dirs(ptid_dir: Path) -> list[Path]:
    """List every `<datetime>/<image_id>` scan-series leaf directory for a subject."""
    if not ptid_dir.is_dir():
        return []
    return sorted(
        p
        for series_desc_dir in ptid_dir.iterdir()
        if series_desc_dir.is_dir()
        for datetime_dir in series_desc_dir.iterdir()
        if datetime_dir.is_dir()
        for p in datetime_dir.iterdir()
        if p.is_dir()
    )


def _parse_series_datetime(series_dir: Path) -> pd.Timestamp | None:
    # series_dir is .../<series_description>/<acquisition_datetime>/<image_id>
    datetime_str = series_dir.parent.name.split("_")[0]
    try:
        return pd.Timestamp(datetime_str)
    except ValueError:
        return None


def series_modality(series_dir: Path) -> str | None:
    """DICOM Modality-tag equivalent for a scan-series directory: "MR" or "PT".

    ECAT7 (.v) and Interfile (.hdr) are exclusively FDG-PET formats in this dataset
    (every ECAT7/Interfile series description contains "FDG", confirmed across the whole
    tree, see docs/DECISIONS.md) -- for those, format alone determines modality. DICOM
    series carry the tag directly (0008,0060), read from a single file since it's
    constant across a series.
    """
    fmt = detect_format(series_dir)
    if fmt in ("interfile", "ecat7"):
        return "PT"

    dcm_path = next(series_dir.glob("*.dcm"), None)
    if dcm_path is None:
        return None
    ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
    return ds.get("Modality")


def select_closest_series(
    ptid_dir: Path, target_date: pd.Timestamp, modality: str
) -> Path | None:
    """Pick the `modality` ("MR" or "PT") series directory closest to `target_date`.

    Ties (multiple series of the same modality on the same closest date) are broken
    deterministically by image_id (the leaf directory name, e.g. "I123456") in ascending
    order, since no principled tie-break criterion exists in the available metadata.
    Candidates farther than MAX_SERIES_DATE_OFFSET_DAYS are rejected -- see its docstring.
    """
    candidates = []
    for series_dir in find_series_dirs(ptid_dir):
        acq_date = _parse_series_datetime(series_dir)
        if acq_date is None:
            continue
        offset_days = abs((acq_date - target_date).days)
        if offset_days > MAX_SERIES_DATE_OFFSET_DAYS:
            continue
        if series_modality(series_dir) != modality:
            continue
        candidates.append((offset_days, series_dir.name, series_dir))

    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def build_final_manifest(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Build the one-scan-per-subject manifest: cohort + resolved PET/MRI series dirs.

    Reads FDG-PET series from `data/adni/images/ADNI/<PTID>/` (the only PET source
    currently on disk; Stage 1's processed-FDG-PET download will add a second source
    under `ADNI_processed_fdg/` once available -- this function will need extending to
    prefer that source once it exists, see docs/TODO.md).
    """
    cohort = load_cohort(data_dir)
    images_dir = data_dir / "images" / "ADNI"

    rows = []
    for _, subj in cohort.iterrows():
        ptid_dir = images_dir / subj["PTID"]

        pet_series = None
        if pd.notna(subj["FDG_PET_EXAMDATE"]):
            pet_series = select_closest_series(
                ptid_dir, pd.Timestamp(subj["FDG_PET_EXAMDATE"]), modality="PT"
            )

        mri_series = None
        if pd.notna(subj["MRI_EXAMDATE"]):
            mri_series = select_closest_series(
                ptid_dir, pd.Timestamp(subj["MRI_EXAMDATE"]), modality="MR"
            )

        rows.append(
            {
                "RID": subj["RID"],
                "PTID": subj["PTID"],
                "label": subj["label"],
                "SAA_RESULT": subj["SAA_RESULT"],
                "FDG_PET_EXAMDATE": subj["FDG_PET_EXAMDATE"],
                "fdg_pet_series_dir": str(pet_series) if pet_series else None,
                "MRI_EXAMDATE": subj["MRI_EXAMDATE"],
                "mri_series_dir": str(mri_series) if mri_series else None,
            }
        )

    return pd.DataFrame(rows)
