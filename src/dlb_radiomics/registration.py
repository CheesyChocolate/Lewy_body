"""Native-space ROI extraction: FastSurfer DKT+aseg segmentation + PET-to-MRI registration.

For the majority of the cohort, ADNI never processed a coregistered/normalized FDG-PET
image or a FreeSurfer segmentation (verified this session, see docs/DECISIONS.md "Pivot:
ADNI processed-image download is not viable as the primary path") -- so both have to be
built from the raw DICOM/ECAT7/Interfile images already on disk:

1. Segment each subject's own raw T1 MRI into FastSurfer's DKT+aseg labels via a
   containerized FastSurfer run (--seg_only, partial-GPU: --device cuda
   --viewagg_device cpu, fits Olympus's 4GB GPU). FastSurfer's own conform step
   resamples the T1 onto a canonical 256^3 1mm grid internally; the result is
   resampled back onto the *original* T1 grid here (nearest-neighbor, to preserve
   integer labels) so it lines up with register_pet_to_t1's output below, which
   stays on that same native grid. Replaces the previous antspynet
   desikan_killiany_tourville_labeling + deep_atropos hybrid -- see
   docs/KNOWLEDGE.md "Superseded: switched from antspynet to FastSurfer" for the full
   rationale (accuracy, one segmentation call covering both cortical ROIs and the
   brain-stem/cerebellum reference region, GPU fit).
2. Rigidly register the subject's raw FDG-PET onto that same native MRI grid via antspyx,
   so PET voxels and DKT+aseg labels line up.

ROI_LABELS below covers the regions needed for the DLB cingulate island sign (posterior
cingulate vs. surrounding occipital/parietal cortex, McKeith et al. 2017, Lim et al. 2009)
plus enough of the Desikan-Killiany-Tourville set for general radiomics. Label codes
confirmed directly against FastSurfer's own FreeSurferColorLUT.txt (same IDs as the old
antspynet labeling used -- both follow the standard FreeSurfer/DKT numbering, so no
remapping was needed when switching segmentation tools).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import ants
import numpy as np

# name -> (left_label, right_label), FreeSurfer/DKT atlas label IDs.
ROI_LABELS: dict[str, tuple[int, int]] = {
    "posterior_cingulate": (1023, 2023),
    "caudal_anterior_cingulate": (1002, 2002),
    "rostral_anterior_cingulate": (1026, 2026),
    "precuneus": (1025, 2025),
    "lateral_occipital": (1011, 2011),
    "inferior_parietal": (1008, 2008),
    "superior_parietal": (1029, 2029),
    "supramarginal": (1031, 2031),
    "postcentral": (1022, 2022),
    "paracentral": (1017, 2017),
    "lingual": (1013, 2013),
    "pericalcarine": (1021, 2021),
    "cuneus": (1005, 2005),
}

FASTSURFER_IMAGE = "deepmi/fastsurfer:latest"
FASTSURFER_OUT_DIR = Path("data/adni/fastsurfer_out")


def run_fastsurfer(t1_path: Path, sid: str) -> Path:
    """Run FastSurfer --seg_only (partial-GPU) on a subject's T1, returning the path
    to the resulting DKT+aseg label volume (still on FastSurfer's own conformed grid).

    CerebNet cerebellum sub-segmentation is left on (near-free once on GPU, per
    docs/KNOWLEDGE.md, kept for possible future use); HypVINN hypothalamus is left off
    (unrelated to this project's ROIs). Resumable: skips the docker run entirely if
    the subject's output already exists, since segmentation only needs to run once per
    subject regardless of how many times feature extraction itself is re-run. On
    failure, see <sid>/scripts/deep-seg.log under FASTSURFER_OUT_DIR for FastSurfer's
    own error detail -- the subprocess's own stderr is not verbose enough alone.
    """
    sd = FASTSURFER_OUT_DIR.resolve()
    sd.mkdir(parents=True, exist_ok=True)
    out_seg = sd / sid / "mri" / "aparc.DKTatlas+aseg.deep.mgz"
    if out_seg.exists():
        return out_seg

    t1_abs = Path(t1_path).resolve()
    subprocess.run(
        [
            "sudo", "docker", "run", "--rm", "--gpus", "all",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{t1_abs.parent}:/t1in",
            "-v", f"{sd}:/data",
            FASTSURFER_IMAGE,
            "--t1", f"/t1in/{t1_abs.name}",
            "--sid", sid, "--sd", "/data",
            "--seg_only", "--device", "cuda", "--viewagg_device", "cpu", "--no_hypothal",
        ],
        check=True,
    )
    return out_seg


def segment_t1_fastsurfer(t1_path: Path, sid: str) -> ants.core.ants_image.ANTsImage:
    """Segment a raw T1 MRI into FastSurfer's DKT+aseg labels, resampled onto that
    MRI's own native grid (see module docstring point 1)."""
    seg_mgz = run_fastsurfer(t1_path, sid)
    seg_img = ants.image_read(str(seg_mgz))
    t1_img = ants.image_read(str(t1_path))
    return ants.resample_image_to_target(seg_img, t1_img, interp_type="genericLabel")


def register_pet_to_t1(pet_path: Path, t1_path: Path) -> ants.core.ants_image.ANTsImage:
    """Rigidly register a raw FDG-PET image onto its subject's native T1 MRI grid.

    Determinism comes from ants.config.set_ants_deterministic (package
    __init__), not from anything here -- see docs/KNOWLEDGE.md "Feature
    reproducibility".
    """
    t1 = ants.image_read(str(t1_path))
    pet = ants.image_read(str(pet_path))
    result = ants.registration(fixed=t1, moving=pet, type_of_transform="Rigid")
    return result["warpedmovout"]


def mask_for_roi(
    label_image: ants.core.ants_image.ANTsImage,
    roi_name: str,
    *,
    hemisphere: str = "both",
) -> ants.core.ants_image.ANTsImage:
    """Binary mask for one ROI (both hemispheres, or "left"/"right" only)."""
    left, right = ROI_LABELS[roi_name]
    codes = {"both": (left, right), "left": (left,), "right": (right,)}[hemisphere]

    arr = label_image.numpy()
    mask_arr = np.isin(arr, codes).astype(np.float32)
    return label_image.new_image_like(mask_arr)
