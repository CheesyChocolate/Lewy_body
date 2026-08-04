#!/usr/bin/env python3
"""Build the ADNI RID list for the DLB radiomics cohort.

Selects SAA-positive subjects (AMPRION_ASYN_SAA.Result == "Detected-1") and
pairs each with the closest FDG-PET scan (UCBERKELEYFDG_8mm) and closest
structural MRI scan (UCSFFSX51) to the SAA draw date, keeping only pairs
within MAX_DAYS of the draw. Per docs/advisor_notes/1.md.
"""

import argparse
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "adni"
MAX_DAYS = 365


def closest_scan(
    rid: int, saa_date: pd.Timestamp, scans: pd.DataFrame
) -> pd.Series | None:
    subj_scans = scans[scans["RID"] == rid]
    if subj_scans.empty:
        return None
    deltas = (subj_scans["EXAMDATE"] - saa_date).abs()
    best_idx = deltas.idxmin()
    if deltas.loc[best_idx].days > MAX_DAYS:
        return None
    row = subj_scans.loc[best_idx].copy()
    row["DAYS_FROM_SAA"] = deltas.loc[best_idx].days
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-days", type=int, default=MAX_DAYS)
    parser.add_argument(
        "--out", type=Path, default=DATA_DIR / "dlb_cohort_candidates.csv"
    )
    args = parser.parse_args()

    saa = pd.read_csv(DATA_DIR / "biospecimen" / "AMPRION_ASYN_SAA_04Aug2026.csv")
    saa["EXAMDATE"] = pd.to_datetime(saa["EXAMDATE"])
    saa_pos = saa[saa["Result"] == "Detected-1"].copy()

    fdg = pd.read_csv(DATA_DIR / "tables" / "UCBERKELEYFDG_8mm.csv")
    fdg["EXAMDATE"] = pd.to_datetime(fdg["EXAMDATE"])
    fdg_wide = fdg[fdg["ROINAME"] == "MetaROI"][["RID", "EXAMDATE"]].drop_duplicates()

    mri = pd.read_csv(DATA_DIR / "tables" / "UCSFFSX51.csv", low_memory=False)
    mri["EXAMDATE"] = pd.to_datetime(mri["EXAMDATE"])
    mri_dates = mri[["RID", "EXAMDATE"]].drop_duplicates()

    rows = []
    for _, subj in saa_pos.iterrows():
        rid = subj["RID"]
        saa_date = subj["EXAMDATE"]

        pet_match = closest_scan(rid, saa_date, fdg_wide)
        mri_match = closest_scan(rid, saa_date, mri_dates)

        rows.append(
            {
                "RID": rid,
                "SAA_EXAMDATE": saa_date.date(),
                "SAA_RESULT": subj["Result"],
                "FDG_PET_EXAMDATE": (
                    pet_match["EXAMDATE"].date() if pet_match is not None else None
                ),
                "FDG_PET_DAYS_FROM_SAA": (
                    pet_match["DAYS_FROM_SAA"] if pet_match is not None else None
                ),
                "MRI_EXAMDATE": (
                    mri_match["EXAMDATE"].date() if mri_match is not None else None
                ),
                "MRI_DAYS_FROM_SAA": (
                    mri_match["DAYS_FROM_SAA"] if mri_match is not None else None
                ),
            }
        )

    cohort = pd.DataFrame(rows)
    cohort["has_fdg_pet"] = cohort["FDG_PET_EXAMDATE"].notna()
    cohort["has_mri"] = cohort["MRI_EXAMDATE"].notna()

    cohort.to_csv(args.out, index=False)

    n = len(cohort)
    n_pet = cohort["has_fdg_pet"].sum()
    n_mri = cohort["has_mri"].sum()
    n_both = (cohort["has_fdg_pet"] & cohort["has_mri"]).sum()
    print(f"SAA-positive (Detected-1) subjects: {n}")
    print(f"  with FDG-PET within {args.max_days}d of SAA draw: {n_pet}")
    print(f"  with sMRI within {args.max_days}d of SAA draw:    {n_mri}")
    print(f"  with both:                                        {n_both}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
