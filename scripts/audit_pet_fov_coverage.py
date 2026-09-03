"""Stratified-sample cohort audit: does each subject's PET field-of-view actually cover
their cortical ROIs?

Triggered by a spot-check finding (2026-09-02, docs/KNOWLEDGE.md "PET FOV coverage"):
rigid PET->T1 registration zero-fills any T1 voxel outside the PET's original physical
extent. For subject 041_S_4041 (ECAT7, 63-slice HR+ scanner, ~153mm z-FOV), that zero-fill
clipped into cortical ROIs used for feature extraction -- only 28.3% of the paracentral
ROI and 60-61% of postcentral/superior_parietal were within the PET's actual acquired
volume. A same-scanner, same-FOV-size subject (006_S_4363) had 100% coverage on every
ROI: confirmed subject-specific (how the PET bed was positioned at scan time), not a fixed
defect of any one file format. Also confirmed (via NIfTI affine headers, both RAS,
diagonal, no sign flips) that this is a genuine FOV/positioning issue, not an
orientation/mirroring bug.

**v1 of this script (cheap intensity-threshold proxy, skipping real DKT segmentation) was
invalid** -- see docs/KNOWLEDGE.md "PET field-of-view coverage" for the failed validation
(it scored the known-bad and known-good ground-truth subjects almost identically). This
version uses the real, already-proven method instead: actual DKT cortical segmentation +
per-ROI voxel overlap with the registered PET's nonzero region, same as the two-subject
ground truth. That costs ~230-280s/subject (DKT segmentation alone measured at 221s,
CPU-forced, see registration.py), so auditing the full 491-subject cohort would cost the
same ~60 hours as the original extraction batch -- instead this runs on a fixed stratified
sample (SUBJECTS list below, chosen by (pet_format, label) stratum, generated once and
hardcoded here rather than resampled on each run so the audit is reproducible and
resumable): all of the small ECAT7-positive/Interfile strata (where the confirmed bug
lives) plus a smaller minority sample of the much larger DICOM strata.

Usage (resumable, like extract_all_features.py): uv run python3 scripts/audit_pet_fov_coverage.py
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import pandas as pd

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import detect_format, ingest_series
from dlb_radiomics.registration import (
    ROI_LABELS,
    mask_for_roi,
    register_pet_to_t1,
    segment_t1_dkt,
)

OUT_PATH = Path("data/adni/pet_fov_coverage_audit.csv")
NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_audit")
FAILURE_LOG_PATH = Path("data/adni/pet_fov_coverage_audit_failures.log")

# Stratified sample sizes: (pet_format, label) -> subjects to draw. Small/rare strata
# (ecat7 positive, all interfile) taken in full since that's where the confirmed bug
# lives; dicom (much larger, and a priori lower risk -- whole-body PET/CT scanners
# typically have bigger axial FOV than the dedicated brain HR+/HRRT scanners behind
# ecat7/interfile) sampled at a smaller fraction to keep runtime reasonable.
STRATUM_SAMPLE_SIZES = {
    ("dicom", 0): 25,
    ("dicom", 1): 15,
    ("ecat7", 0): 20,
    ("ecat7", 1): 26,  # all
    ("interfile", 0): 18,  # all
    ("interfile", 1): 4,  # all
}
SAMPLE_SEED = 0


def build_sample(manifest: pd.DataFrame) -> pd.DataFrame:
    manifest = manifest.copy()
    manifest["pet_format"] = manifest["fdg_pet_series_dir"].apply(
        lambda p: detect_format(Path(p))
    )
    parts = []
    for (fmt, label), n in STRATUM_SAMPLE_SIZES.items():
        stratum = manifest[
            (manifest["pet_format"] == fmt) & (manifest["label"] == label)
        ]
        n = min(n, len(stratum))
        parts.append(stratum.sample(n=n, random_state=SAMPLE_SEED))
    return pd.concat(parts, ignore_index=True)


def _already_done() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    return set(pd.read_csv(OUT_PATH, usecols=["PTID"])["PTID"])


def compute_roi_coverage(t1_path: Path, pet_path: Path) -> dict:
    label_image = segment_t1_dkt(t1_path)
    pet_native = register_pet_to_t1(pet_path, t1_path)
    nonzero_mask = pet_native.numpy() != 0

    out = {"overall_nonzero_frac": float(nonzero_mask.mean())}
    coverages = []
    for roi_name in ROI_LABELS:
        roi_mask = mask_for_roi(label_image, roi_name).numpy() > 0
        total = roi_mask.sum()
        if total == 0:
            out[f"roi_{roi_name}"] = float("nan")
            continue
        frac = float((roi_mask & nonzero_mask).sum() / total)
        out[f"roi_{roi_name}"] = frac
        coverages.append(frac)
    out["min_roi_coverage"] = min(coverages) if coverages else float("nan")
    out["mean_roi_coverage"] = sum(coverages) / len(coverages) if coverages else float("nan")
    return out


def main() -> None:
    manifest = build_final_manifest()
    manifest = manifest[
        manifest["fdg_pet_series_dir"].notna() & manifest["mri_series_dir"].notna()
    ]
    sample = build_sample(manifest)

    done = _already_done()
    remaining = sample[~sample["PTID"].isin(done)]
    print(
        f"{len(sample)} subjects in stratified sample, {len(done)} already done, "
        f"{len(remaining)} remaining",
        flush=True,
    )

    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)

    for i, (_, row) in enumerate(remaining.iterrows(), start=1):
        ptid = row["PTID"]
        t0 = time.time()
        subj_dir = NIFTI_TMP_DIR / ptid
        try:
            subj_dir.mkdir(exist_ok=True)
            t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)
            pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)

            coverage = compute_roi_coverage(t1_nii, pet_nii)

            row_out = {
                "PTID": ptid,
                "RID": row["RID"],
                "label": row["label"],
                "pet_format": row["pet_format"],
                **coverage,
            }
            pd.DataFrame([row_out]).to_csv(
                OUT_PATH, mode="a", header=not OUT_PATH.exists(), index=False
            )

            elapsed = time.time() - t0
            print(
                f"[{i}/{len(remaining)}] {ptid} "
                f"min_roi={coverage['min_roi_coverage']:.3f} "
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
