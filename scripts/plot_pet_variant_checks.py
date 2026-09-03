"""Visual re-check of the ECAT7/Interfile orientation fix, across two subjects from
each distinct geometry/orientation variant (see docs/KNOWLEDGE.md "PET field-of-view
coverage" and scripts/enumerate_pet_variants.py).

User asked (2026-09-03) to double-check the fix visually before trusting it, having
never actually confirmed the original "does this look right?" question
(figs/pet_fov_ecat7_unchecked_variants.png) from the 2026-09-02 session. Covers the 7
variant groups from that investigation's actual scope (5 ECAT7 + 1 Interfile + 1 DICOM
representative pair, the same DICOM subjects already spot-checked as clean) -- not the
full 19-way DICOM geometry breakdown from enumerate_pet_variants.py, which was never
part of the orientation-bug investigation and would ~4x the compute for a format
already confirmed unaffected.

v1 of this script used a single custom-picked "near top of brain" axial slice, which
(a) had its own bug (a percentile-based brain-mask heuristic that mistook background
noise for brain on several subjects), and (b) was the wrong view even when correct: a
top-of-FOV clip is a cut across z, which shows up as a sharp horizontal cutoff line in
a SAGITTAL or CORONAL slice (both span the full head height), not necessarily in any
single flat AXIAL slice. This version instead reuses the exact approach already proven
in scripts/qa_registration.py and figs/pet_fov_clip_041_S_4041.png /
figs/pet_fov_ecat7_unchecked_variants.png: plain mid-array slices along all three axes
(no thresholding/heuristic needed), one PNG per subject, axial+coronal+sagittal side by
side -- since PET is resampled onto T1's exact grid by register_pet_to_t1 (same shape/
spacing/origin/direction, confirmed directly), the same slice index is guaranteed to be
the same physical location in both images, so there's no risk of the two panels showing
different depths.

Produces, per subject, two 1x3 (axial/coronal/sagittal) PNGs under figs/pet_fov_variant_recheck/:
  - <ptid>_overlay.png: PET (hot colormap, alpha) overlaid on the T1 MRI.
  - <ptid>_sidebyside.png: T1 and registered PET as separate, non-overlapping panels
    (T1 | PET per view) -- no alpha blending, so clipped/missing PET coverage is
    visible without relying on overlay transparency.
Plus an index PNG (figs/pet_fov_variant_recheck_index.png) with all 14 subjects'
sagittal overlay slice only, for a quick at-a-glance scan across every variant.

Usage: uv run python3 scripts/plot_pet_variant_checks.py
"""

from __future__ import annotations

from pathlib import Path

import ants
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import ingest_series
from dlb_radiomics.registration import register_pet_to_t1

NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_variant_recheck")
FIGS_DIR = Path("figs/pet_fov_variant_recheck")
INDEX_PATH = Path("figs/pet_fov_variant_recheck_index.png")
# mid_slices()'s 3 outputs, in order -- verified against actual visual content (a
# profile with the nose/jaw visible = sagittal, a symmetric front-on slice = coronal,
# a symmetric top-down ring = axial), NOT assumed from axis position. The original
# investigation's scripts/qa_registration.py (and this script's own first version) had
# axial and sagittal swapped for this dataset's NIfTI axis order -- caught 2026-09-03
# when the "sagittal" index figure came out showing axial-looking slices, useless for
# spotting a top-of-FOV cutoff line.
VIEWS = ["sagittal", "coronal", "axial"]

# variant label -> (subject 1, subject 2). One from each of the 7 groups actually
# investigated for the orientation bug (docs/KNOWLEDGE.md); subject 1 in each pair was
# already spot-checked in that investigation, subject 2 is new.
VARIANT_SUBJECTS: dict[str, tuple[str, str]] = {
    "ecat7 code3 128x63 sp0.2574 (n=62)": ("006_S_4363", "006_S_4515"),
    "ecat7 code8 128x63 sp0.2574 (n=24)": ("041_S_4041", "036_S_5063"),
    "ecat7 code3 128x47 sp0.2059 (n=7)": ("109_S_4531", "109_S_4499"),
    "ecat7 code3 256x63 sp0.2574 (n=2)": ("024_S_4280", "037_S_4770"),
    "ecat7 code8 128x63 sp0.2059 (n=6)": ("031_S_4203", "031_S_4194"),
    "interfile (n=22, single geometry)": ("053_S_5070", "053_S_5272"),
    "dicom (reference, clean)": ("082_S_2307", "130_S_4660"),
}


def mid_slices(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sagittal/coronal/axial mid-slices, matching VIEWS order above. Same axis
    indexing as scripts/qa_registration.py's mid_slices, but with axial/sagittal
    swapped to match this dataset's actual NIfTI axis order (see VIEWS comment)."""
    x, y, z = (s // 2 for s in arr.shape)
    return arr[x, :, :], arr[:, y, :], arr[:, :, z]


def load_pair(ptid: str, manifest: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    row = manifest[manifest["PTID"] == ptid].iloc[0]
    subj_dir = NIFTI_TMP_DIR / ptid
    subj_dir.mkdir(parents=True, exist_ok=True)

    t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)
    pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)

    t1_arr = ants.image_read(str(t1_nii)).numpy()
    pet_arr = register_pet_to_t1(pet_nii, t1_nii).numpy()
    return t1_arr, pet_arr


def make_overlay(ptid: str, variant: str, t1_slices, pet_slices) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for i, view in enumerate(VIEWS):
        t1_s = np.rot90(t1_slices[i])
        pet_s = np.rot90(pet_slices[i])
        axes[i].imshow(t1_s, cmap="gray")
        pet_masked = np.ma.masked_where(pet_s <= 0, pet_s)
        axes[i].imshow(pet_masked, cmap="hot", alpha=0.5)
        axes[i].set_title(view, fontsize=10)
        axes[i].axis("off")
    fig.suptitle(f"{ptid} -- {variant}\nPET (hot) overlaid on T1")
    fig.tight_layout()
    out = FIGS_DIR / f"{ptid}_overlay.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def make_sidebyside(ptid: str, variant: str, t1_slices, pet_slices) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.5))
    for i, view in enumerate(VIEWS):
        t1_s = np.rot90(t1_slices[i])
        pet_s = np.rot90(pet_slices[i])
        axes[0, i].imshow(t1_s, cmap="gray")
        axes[0, i].set_title(f"{view}: T1", fontsize=10)
        axes[0, i].axis("off")
        axes[1, i].imshow(pet_s, cmap="hot")
        axes[1, i].set_title(f"{view}: PET", fontsize=10)
        axes[1, i].axis("off")
    fig.suptitle(f"{ptid} -- {variant}\nT1 and registered PET shown separately (no overlay)")
    fig.tight_layout()
    out = FIGS_DIR / f"{ptid}_sidebyside.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    manifest = build_final_manifest()
    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    index_entries: list[tuple[str, str, np.ndarray, np.ndarray]] = []

    for variant, ptids in VARIANT_SUBJECTS.items():
        for ptid in ptids:
            print(f"{variant}: {ptid}", flush=True)
            t1_arr, pet_arr = load_pair(ptid, manifest)
            t1_slices = mid_slices(t1_arr)
            pet_slices = mid_slices(pet_arr)

            out1 = make_overlay(ptid, variant, t1_slices, pet_slices)
            print(f"  wrote {out1}", flush=True)
            out2 = make_sidebyside(ptid, variant, t1_slices, pet_slices)
            print(f"  wrote {out2}", flush=True)

            # sagittal (index 0) is the most diagnostic view for top-of-FOV clipping
            index_entries.append((ptid, variant, t1_slices[0], pet_slices[0]))

    n = len(index_entries)
    fig, axes = plt.subplots(n, 1, figsize=(5, 4 * n))
    for i, (ptid, variant, t1_s, pet_s) in enumerate(index_entries):
        ax = axes[i]
        t1_r = np.rot90(t1_s)
        pet_r = np.rot90(pet_s)
        ax.imshow(t1_r, cmap="gray")
        pet_masked = np.ma.masked_where(pet_r <= 0, pet_r)
        ax.imshow(pet_masked, cmap="hot", alpha=0.5)
        ax.set_title(f"{ptid} -- {variant}", fontsize=9)
        ax.axis("off")
    fig.suptitle("All 14 subjects, sagittal view (most diagnostic for top-of-FOV clipping)")
    fig.tight_layout()
    fig.savefig(INDEX_PATH, dpi=120)
    print(f"wrote {INDEX_PATH}", flush=True)


if __name__ == "__main__":
    main()
