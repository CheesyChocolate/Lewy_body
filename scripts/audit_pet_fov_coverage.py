"""Full-cohort audit: does each subject's PET field-of-view actually cover their brain?

Triggered by a spot-check finding (2026-09-02, docs/KNOWLEDGE.md "PET FOV coverage"):
rigid PET->T1 registration zero-fills any T1 voxel outside the PET's original physical
extent. For subject 041_S_4041 (ECAT7, 63-slice HR+ scanner, ~153mm z-FOV), that zero-fill
clipped into cortical ROIs used for feature extraction -- only 28.3% of the paracentral
ROI and 60-61% of postcentral/superior_parietal were within the PET's actual acquired
volume. A same-scanner, same-FOV-size subject (006_S_4363) had 100% coverage on every
ROI, meaning this is subject-specific (how the PET bed was positioned at scan time), not a
fixed defect of any one file format.

Full DKT segmentation (as features.py/registration.py use for the real per-ROI masks) is
the expensive step in the real pipeline (~300-400s/subject, CPU-forced) and isn't needed
here -- a full 491-subject run with real DKT would cost the same ~60 hours as the original
extraction batch. Instead this script only does ingest + rigid registration (~6-50s) +' a
cheap intensity-threshold brain mask, and reports two proxies per subject:
  - overall_nonzero_frac: fraction of the registered PET volume that is nonzero at all
  - top_slab_coverage: fraction of the brain mask's uppermost 35% (by z, the region
    containing the vertex-near ROIs that were clipped in the spot-check: paracentral,
    postcentral, superior_parietal, precuneus) that falls within the PET's nonzero region

top_slab_coverage is the one that matters for feature validity; overall_nonzero_frac is
context (a PET volume is always smaller than a T1+neck volume, so <100% here is normal and
expected -- the earlier ~59% seen on both ECAT7 spot-check subjects was NOT itself evidence
of a problem, only the per-ROI/per-slab numbers are).

Usage (resumable, like extract_all_features.py): uv run python3 scripts/audit_pet_fov_coverage.py
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import ants
import numpy as np
import pandas as pd

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import detect_format, ingest_series
from dlb_radiomics.registration import register_pet_to_t1

OUT_PATH = Path("data/adni/pet_fov_coverage_audit.csv")
NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_audit")
FAILURE_LOG_PATH = Path("data/adni/pet_fov_coverage_audit_failures.log")

TOP_SLAB_FRACTION = 0.35  # top 35% of brain-mask z-extent


def _already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    return set(pd.read_csv(OUT_PATH, usecols=["PTID"])["PTID"])


def compute_coverage(t1_path: Path, pet_path: Path) -> dict:
    pet_native = register_pet_to_t1(pet_path, t1_path)
    pet_arr = pet_native.numpy()
    nonzero_mask = pet_arr != 0

    t1_arr = ants.image_read(str(t1_path)).numpy()
    brain_mask = t1_arr > np.percentile(t1_arr[t1_arr > 0], 40)

    z_idx = np.where(brain_mask.any(axis=(1, 2)))[0]
    z_lo, z_hi = z_idx.min(), z_idx.max()
    z_span = z_hi - z_lo
    top_slab_start = z_hi - int(z_span * TOP_SLAB_FRACTION)

    top_slab_mask = brain_mask.copy()
    top_slab_mask[:top_slab_start, :, :] = False

    top_slab_total = top_slab_mask.sum()
    top_slab_covered = (top_slab_mask & nonzero_mask).sum()

    return {
        "overall_nonzero_frac": float(nonzero_mask.mean()),
        "top_slab_coverage": (
            float(top_slab_covered / top_slab_total) if top_slab_total else float("nan")
        ),
        "top_slab_voxels": int(top_slab_total),
    }


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
            pet_fmt = detect_format(Path(row["fdg_pet_series_dir"]))

            coverage = compute_coverage(t1_nii, pet_nii)

            row_out = {
                "PTID": ptid,
                "RID": row["RID"],
                "label": row["label"],
                "pet_format": pet_fmt,
                **coverage,
            }
            pd.DataFrame([row_out]).to_csv(
                OUT_PATH, mode="a", header=not OUT_PATH.exists(), index=False
            )

            elapsed = time.time() - t0
            print(
                f"[{i}/{len(remaining)}] {ptid} "
                f"top_slab={coverage['top_slab_coverage']:.3f} "
                f"done in {elapsed:.0f}s",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            with open(FAILURE_LOG_PATH, "a") as f:
                f.write(f"{ptid}\t{exc}\n{traceback.format_exc()}\n---\n")
            print(f"[{i}/{len(remaining)}] {ptid} FAILED: {exc}", flush=True)
        finally:
            if subj_dir.exists():
                for f in subj_dir.glob("*"):
                    f.unlink()


if __name__ == "__main__":
    main()
