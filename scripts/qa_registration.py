"""Spot-check PET->T1 registration + reference-mask quality on a few subjects.

Reruns Stage 4/5 up through compute_reference_mask/compute_suvr for a handful of
subjects (mix of SAA-positive/negative, mix of source PET format), and dumps
mid-slice overlay PNGs (T1 gray + PET-in-T1-space edges + reference-mask outline) to
data/adni/qa_registration/ for visual review. Does not run pyradiomics.

Usage: uv run python3 scripts/qa_registration.py PTID [PTID ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.features import compute_reference_mask, compute_suvr
from dlb_radiomics.ingest import ingest_series
from dlb_radiomics.registration import register_pet_to_t1, segment_t1_dkt

NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_qa")
OUT_DIR = Path("data/adni/qa_registration")


def mid_slices(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z, y, x = (s // 2 for s in arr.shape)
    return arr[z, :, :], arr[:, y, :], arr[:, :, x]


def make_overlay(t1_arr, suvr_arr, ref_arr, dkt_arr, ptid, label):
    fig, axes = plt.subplots(3, 3, figsize=(12, 12))
    views = ["axial", "coronal", "sagittal"]
    t1_slices = mid_slices(t1_arr)
    suvr_slices = mid_slices(suvr_arr)
    ref_slices = mid_slices(ref_arr)
    dkt_slices = mid_slices(dkt_arr)

    for i, view in enumerate(views):
        t1_s = np.rot90(t1_slices[i])
        suvr_s = np.rot90(suvr_slices[i])
        ref_s = np.rot90(ref_slices[i]) > 0
        dkt_s = np.rot90(dkt_slices[i]) > 0

        axes[0, i].imshow(t1_s, cmap="gray")
        axes[0, i].set_title(f"{view}: T1")
        axes[0, i].axis("off")

        axes[1, i].imshow(t1_s, cmap="gray")
        axes[1, i].imshow(suvr_s, cmap="hot", alpha=0.5)
        axes[1, i].set_title(f"{view}: PET(SUVR) on T1")
        axes[1, i].axis("off")

        axes[2, i].imshow(t1_s, cmap="gray")
        axes[2, i].contour(ref_s, colors="cyan", linewidths=0.8)
        axes[2, i].contour(dkt_s, colors="yellow", linewidths=0.5)
        axes[2, i].set_title(f"{view}: ref mask (cyan) + DKT ROIs (yellow)")
        axes[2, i].axis("off")

    fig.suptitle(f"{ptid}  (label={label})")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{ptid}_overlay.png"
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    print(f"wrote {out_path}", flush=True)


def main() -> None:
    ptids = sys.argv[1:]
    if not ptids:
        raise SystemExit("usage: qa_registration.py PTID [PTID ...]")

    manifest = build_final_manifest().set_index("PTID")
    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)

    for ptid in ptids:
        if ptid not in manifest.index:
            print(f"{ptid}: not in manifest, skipping", flush=True)
            continue
        row = manifest.loc[ptid]
        subj_dir = NIFTI_TMP_DIR / ptid
        subj_dir.mkdir(exist_ok=True)

        print(f"{ptid}: ingesting...", flush=True)
        t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)
        pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)

        print(f"{ptid}: segmenting DKT...", flush=True)
        label_image = segment_t1_dkt(t1_nii)

        print(f"{ptid}: registering PET->T1...", flush=True)
        pet_native = register_pet_to_t1(pet_nii, t1_nii)

        print(f"{ptid}: computing reference mask...", flush=True)
        reference_mask = compute_reference_mask(t1_nii)
        suvr_image = compute_suvr(pet_native, reference_mask)

        import ants

        t1_arr = ants.image_read(str(t1_nii)).numpy()
        suvr_arr = suvr_image.numpy()
        ref_arr = reference_mask.numpy()
        dkt_arr = (label_image.numpy() > 1000).astype(np.float32)

        make_overlay(t1_arr, suvr_arr, ref_arr, dkt_arr, ptid, row["label"])

        for f in subj_dir.glob("*"):
            f.unlink()


if __name__ == "__main__":
    main()
