"""Batch-run Stage 4+5 (registration + feature extraction) across the full cohort.

534 subjects at ~360s/subject is roughly 53 hours -- this runs sequentially rather than
parallelizing across GPU/CPU workers (user decision, 2026-08-26, given the current 4GB-GPU
resource constraints documented in docs/DECISIONS.md), so it's designed to be safely
interruptible and resumable: each subject's feature row is appended to the output CSV
immediately after extraction, and PTIDs already present in the output are skipped on
restart. A failing subject is logged and skipped rather than stopping the whole batch.

Intended to run for days inside a detached tmux session (see docs/TODO.md / project
convention): `uv run python3 scripts/extract_all_features.py`.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import pandas as pd

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.features import extract_subject_features
from dlb_radiomics.ingest import ingest_series

OUT_PATH = Path("data/adni/features.csv")
NIFTI_TMP_DIR = Path("data/adni/nifti_tmp")
FAILURE_LOG_PATH = Path("data/adni/feature_extraction_failures.log")


def _already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    return set(pd.read_csv(OUT_PATH, usecols=["PTID"])["PTID"])


def main() -> None:
    manifest = build_final_manifest()
    manifest = manifest[
        manifest["fdg_pet_series_dir"].notna() & manifest["mri_series_dir"].notna()
    ]

    done = _already_done()
    remaining = manifest[~manifest["PTID"].isin(done)]
    print(f"{len(done)} subjects already done, {len(remaining)} remaining", flush=True)

    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)

    for i, (_, row) in enumerate(remaining.iterrows(), start=1):
        ptid = row["PTID"]
        t0 = time.time()
        subj_dir = NIFTI_TMP_DIR / ptid
        try:
            subj_dir.mkdir(exist_ok=True)
            t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)
            pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)
            features = extract_subject_features(t1_nii, pet_nii)

            row_out = {
                "PTID": ptid,
                "RID": row["RID"],
                "label": row["label"],
                **features,
            }
            pd.DataFrame([row_out]).to_csv(
                OUT_PATH, mode="a", header=not OUT_PATH.exists(), index=False
            )

            elapsed = time.time() - t0
            print(f"[{i}/{len(remaining)}] {ptid} done in {elapsed:.0f}s", flush=True)
        except Exception as exc:  # noqa: BLE001
            with open(FAILURE_LOG_PATH, "a") as f:
                f.write(f"{ptid}\t{exc}\n{traceback.format_exc()}\n---\n")
            print(f"[{i}/{len(remaining)}] {ptid} FAILED: {exc}", flush=True)
        finally:
            # Only the feature row needs to persist -- clean up intermediate NIfTIs so a
            # multi-day run doesn't accumulate disk usage.
            if subj_dir.exists():
                for f in subj_dir.glob("*"):
                    f.unlink()
                subj_dir.rmdir()


if __name__ == "__main__":
    main()
