"""Visual re-check of the ECAT7/Interfile orientation-fix, across two subjects from
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

Produces two figures:
  - figs/pet_fov_variant_recheck_overlay.png: PET (hot colormap, alpha) overlaid on the
    T1 MRI, one row per variant, one column per subject -- same style as the original
    evidence figures.
  - figs/pet_fov_variant_recheck_sidebyside.png: T1 and registered-PET shown as
    separate, non-overlapping panels side by side (no alpha blending) -- makes any
    clipped/missing PET coverage at the top of the brain visible without relying on
    overlay transparency to see it.

Both figures use an axial slice near the top of each subject's brain (90% of the T1
brain's z-extent) -- the region where the original clipping (paracentral/postcentral/
superior_parietal ROIs) was found.

Usage: uv run python3 scripts/plot_pet_variant_checks.py
"""

from __future__ import annotations

from pathlib import Path

import ants
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import ingest_series
from dlb_radiomics.registration import register_pet_to_t1

NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_variant_recheck")
FIGS_DIR = Path("figs")

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


def top_axial_slice(t1_arr: np.ndarray, frac: float = 0.90) -> int:
    """Pick a near-vertex axial slice using the largest connected component of a
    coarse intensity threshold, not the raw threshold alone -- a plain percentile
    cutoff (v1 of this function) misidentified low-level background/scanner noise as
    "brain" for several subjects (whole-panel static noise, no head visible at all),
    because a percentile of nonzero voxels doesn't exclude a noisy-but-nonzero
    background floor. Restricting to the largest connected component after
    thresholding reliably isolates the actual head.
    """
    nonzero = t1_arr[t1_arr > 0]
    threshold = np.percentile(nonzero, 70)
    coarse_mask = t1_arr > threshold
    labeled, n = ndimage.label(coarse_mask)
    if n == 0:
        raise ValueError("no foreground component found in T1 volume")
    sizes = ndimage.sum(coarse_mask, labeled, range(1, n + 1))
    largest_label = 1 + int(np.argmax(sizes))
    brain_mask = labeled == largest_label

    z_idx = np.where(brain_mask.any(axis=(0, 1)))[0]
    z_lo, z_hi = z_idx.min(), z_idx.max()
    return int(z_lo + frac * (z_hi - z_lo))


def load_pair(ptid: str, manifest: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, int]:
    row = manifest[manifest["PTID"] == ptid].iloc[0]
    subj_dir = NIFTI_TMP_DIR / ptid
    subj_dir.mkdir(parents=True, exist_ok=True)

    t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)
    pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)

    t1_img = ants.image_read(str(t1_nii))
    t1_arr = t1_img.numpy()
    pet_arr = register_pet_to_t1(pet_nii, t1_nii).numpy()

    z = top_axial_slice(t1_arr)
    return t1_arr, pet_arr, z


def main() -> None:
    manifest = build_final_manifest()
    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    slices: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
    for variant, ptids in VARIANT_SUBJECTS.items():
        slices[variant] = []
        for ptid in ptids:
            print(f"{variant}: {ptid}", flush=True)
            t1_arr, pet_arr, z = load_pair(ptid, manifest)
            slices[variant].append((t1_arr[:, :, z], pet_arr[:, :, z]))

    n_rows = len(VARIANT_SUBJECTS)

    # Overlay figure: 1 column per subject.
    fig, axes = plt.subplots(n_rows, 2, figsize=(8, 4 * n_rows))
    for row_i, (variant, pairs) in enumerate(slices.items()):
        for col_i, (t1_slice, pet_slice) in enumerate(pairs):
            ax = axes[row_i, col_i]
            ax.imshow(np.rot90(t1_slice), cmap="gray")
            pet_masked = np.ma.masked_where(pet_slice <= 0, pet_slice)
            ax.imshow(np.rot90(pet_masked), cmap="hot", alpha=0.5)
            ptid = VARIANT_SUBJECTS[variant][col_i]
            ax.set_title(f"{ptid}", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        axes[row_i, 0].set_ylabel(variant, fontsize=8)
    fig.suptitle("PET (hot) overlaid on T1 -- top-of-brain axial slice, fixed pipeline")
    fig.tight_layout()
    out1 = FIGS_DIR / "pet_fov_variant_recheck_overlay.png"
    fig.savefig(out1, dpi=130)
    print(f"wrote {out1}", flush=True)

    # Side-by-side figure: T1 | PET per subject, no overlay -- 4 columns.
    fig2, axes2 = plt.subplots(n_rows, 4, figsize=(14, 3.5 * n_rows))
    for row_i, (variant, pairs) in enumerate(slices.items()):
        for col_i, (t1_slice, pet_slice) in enumerate(pairs):
            ptid = VARIANT_SUBJECTS[variant][col_i]
            ax_t1 = axes2[row_i, col_i * 2]
            ax_t1.imshow(np.rot90(t1_slice), cmap="gray")
            ax_t1.set_title(f"{ptid} T1", fontsize=8)
            ax_t1.set_xticks([])
            ax_t1.set_yticks([])

            ax_pet = axes2[row_i, col_i * 2 + 1]
            ax_pet.imshow(np.rot90(pet_slice), cmap="hot")
            ax_pet.set_title(f"{ptid} PET", fontsize=8)
            ax_pet.set_xticks([])
            ax_pet.set_yticks([])
        axes2[row_i, 0].set_ylabel(variant, fontsize=7)
    fig2.suptitle(
        "T1 and registered PET shown separately (no overlay) -- top-of-brain axial slice"
    )
    fig2.tight_layout()
    out2 = FIGS_DIR / "pet_fov_variant_recheck_sidebyside.png"
    fig2.savefig(out2, dpi=130)
    print(f"wrote {out2}", flush=True)


if __name__ == "__main__":
    main()
