"""Stage 5: SUVR normalization + pyradiomics feature extraction per ROI.

Ties together Stage 4's registration.py (DKT labeling, PET-to-MRI registration) with a
PET reference region for SUVR normalization and pyradiomics texture-feature extraction.

Reference region: DKT (registration.segment_t1_dkt) is a cortical-only parcellation, with
no pons/vermis/brainstem/cerebellum labels, so it cannot supply ADNI's own
"Top50PonsVermis" reference convention directly. antspynet.deep_atropos's six-tissue
segmentation gives whole brain-stem (label 5) and whole cerebellum (label 6) in the same
native space as DKT -- the closest available substitute. See docs/DECISIONS.md "Stage 5"
for this tradeoff.

Resolution handling: params/pyradiomics_params.yaml sets resampledPixelSpacing to 2mm
isotropic, so pyradiomics itself resamples both the SUVR image and each ROI mask onto a
common grid at extraction time -- this is what avoids raw-voxel-size/scanner acting as a
texture-feature confound (IBSI's own recommendation), without needing a separate
manually-resampled image.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import ants
import antspynet
import numpy as np
import SimpleITK as sitk
import tensorflow as tf
from radiomics import featureextractor

from dlb_radiomics.registration import (
    ROI_LABELS,
    mask_for_roi,
    register_pet_to_t1,
    segment_t1_dkt,
)

PARAMS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "params" / "pyradiomics_params.yaml"
)

# antspynet.deep_atropos's six-tissue labeling: 5 = brain stem, 6 = cerebellum.
REFERENCE_TISSUE_LABELS = (5, 6)

_extractor: featureextractor.RadiomicsFeatureExtractor | None = None


def compute_reference_mask(t1_path: Path) -> ants.core.ants_image.ANTsImage:
    """Whole brain-stem + cerebellum mask, used as the PET SUVR reference region.

    Forced onto CPU: deep_atropos's batched (8-way reorientation ensemble) prediction
    needs more contiguous VRAM than segment_t1_dkt's single-batch call, and exceeds this
    project's 4GB GPU even with memory growth enabled (see docs/DECISIONS.md "Stage 5").
    Slower, but system RAM + swap comfortably absorb it and this only runs once per
    subject.
    """
    t1 = ants.image_read(str(t1_path))
    with tf.device("/CPU:0"):
        atropos = antspynet.deep_atropos(t1)
    seg = atropos["segmentation_image"]
    arr = seg.numpy()
    mask_arr = np.isin(arr, REFERENCE_TISSUE_LABELS).astype(np.float32)
    return seg.new_image_like(mask_arr)


def compute_suvr(
    pet_native: ants.core.ants_image.ANTsImage,
    reference_mask: ants.core.ants_image.ANTsImage,
) -> ants.core.ants_image.ANTsImage:
    """Normalize a registered PET image by its mean uptake in the reference region."""
    pet_arr = pet_native.numpy()
    ref_arr = reference_mask.numpy() > 0
    if not ref_arr.any():
        raise ValueError("Reference region mask is empty -- cannot compute SUVR")

    ref_mean = pet_arr[ref_arr].mean()
    if ref_mean <= 0:
        raise ValueError(
            f"Non-positive reference-region mean uptake ({ref_mean}); cannot compute SUVR"
        )

    suvr_arr = (pet_arr / ref_mean).astype(np.float32)
    return pet_native.new_image_like(suvr_arr)


def _ants_to_sitk(img: ants.core.ants_image.ANTsImage) -> sitk.Image:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "img.nii.gz"
        ants.image_write(img, str(tmp_path))
        return sitk.ReadImage(str(tmp_path))


def _get_extractor() -> featureextractor.RadiomicsFeatureExtractor:
    global _extractor
    if _extractor is None:
        _extractor = featureextractor.RadiomicsFeatureExtractor(str(PARAMS_PATH))
    return _extractor


def extract_roi_features(
    suvr_image: ants.core.ants_image.ANTsImage,
    roi_mask: ants.core.ants_image.ANTsImage,
    roi_name: str,
) -> dict:
    """Run pyradiomics on one ROI mask against the SUVR image.

    Feature names are prefixed with `roi_name` so per-ROI results can be flattened into
    one row per subject.
    """
    sitk_image = _ants_to_sitk(suvr_image)
    sitk_mask = sitk.Cast(_ants_to_sitk(roi_mask), sitk.sitkUInt8)

    result = _get_extractor().execute(sitk_image, sitk_mask)
    return {
        f"{roi_name}__{k}": v
        for k, v in result.items()
        if not k.startswith("diagnostics_")
    }


def extract_subject_features(t1_path: Path, pet_path: Path) -> dict:
    """Full Stage 4+5 pipeline for one subject: segment, register, normalize, extract.

    ROIs with an empty mask (label not present, e.g. due to a segmentation edge case)
    are skipped rather than raising, since pyradiomics itself requires a non-empty mask.
    """
    label_image = segment_t1_dkt(t1_path)
    pet_native = register_pet_to_t1(pet_path, t1_path)
    reference_mask = compute_reference_mask(t1_path)
    suvr_image = compute_suvr(pet_native, reference_mask)

    features: dict = {}
    for roi_name in ROI_LABELS:
        roi_mask = mask_for_roi(label_image, roi_name)
        if roi_mask.numpy().sum() == 0:
            continue
        features.update(extract_roi_features(suvr_image, roi_mask, roi_name))
    return features
