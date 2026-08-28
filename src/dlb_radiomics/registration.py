"""Native-space ROI extraction: DKT cortical labeling + PET-to-MRI registration.

For the majority of the cohort, ADNI never processed a coregistered/normalized FDG-PET
image or a FreeSurfer segmentation (verified this session, see docs/DECISIONS.md "Pivot:
ADNI processed-image download is not viable as the primary path") -- so both have to be
built from the raw DICOM/ECAT7/Interfile images already on disk:

1. Segment each subject's own raw T1 MRI into DKT cortical labels, in that MRI's native
   space, via antspynet.desikan_killiany_tourville_labeling. No atlas download or template
   warp needed -- the model does its own preprocessing (N4, brain extraction, HCP-affine)
   internally and inverse-transforms the result back to native space.
2. Rigidly register the subject's raw FDG-PET onto that same native MRI grid via antspyx,
   so PET voxels and DKT labels line up.

ROI_LABELS below covers the regions needed for the DLB cingulate island sign (posterior
cingulate vs. surrounding occipital/parietal cortex, McKeith et al. 2017, Lim et al. 2009)
plus enough of the Desikan-Killiany-Tourville set for general radiomics. Label codes
confirmed against the antspynet source (see docs/DECISIONS.md).
"""

from __future__ import annotations

from pathlib import Path

import ants
import antspynet
import numpy as np

# name -> (left_label, right_label), per the DKT labeling in antspynet.
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


def segment_t1_dkt(t1_path: Path) -> ants.core.ants_image.ANTsImage:
    """Segment a raw T1 MRI into DKT cortical labels, in that MRI's native space."""
    t1 = ants.image_read(str(t1_path))
    return antspynet.desikan_killiany_tourville_labeling(t1)


def register_pet_to_t1(pet_path: Path, t1_path: Path) -> ants.core.ants_image.ANTsImage:
    """Rigidly register a raw FDG-PET image onto its subject's native T1 MRI grid.

    aff_random_sampling_rate=1.0 disables ANTs' default 20% random voxel
    subsampling for the alignment metric -- that subsampling is the confirmed
    source of run-to-run feature non-determinism (see docs/KNOWLEDGE.md
    "Feature reproducibility"); using all voxels is slower but deterministic.
    """
    t1 = ants.image_read(str(t1_path))
    pet = ants.image_read(str(pet_path))
    result = ants.registration(
        fixed=t1, moving=pet, type_of_transform="Rigid", aff_random_sampling_rate=1.0
    )
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
