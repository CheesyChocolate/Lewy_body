"""DICOM/ECAT7/Interfile -> NIfTI ingestion, dispatched by file type.

A scan-series directory (one leaf under data/adni/images/ADNI/<PTID>/<series>/<datetime>/
<image_id>/) is one of three raw formats: DICOM (.dcm files, the majority), ECAT7 (.v
files), or Interfile (.hdr/.i pairs). This module picks the right converter per series
and returns a single output NIfTI path. See docs/DECISIONS.md "Raw image format mix" for
the format breakdown; ECAT7 and Interfile both get direct-reader conversion (ecat.py,
interfile.py) rather than dcm2niix, so each frame's own decay-correction factor can be
applied before combining frames -- see docs/KNOWLEDGE.md "Feature reproducibility" /
docs/ecat7_decay_correction_question.md for the ECAT7 reasoning.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import dcm2niix
import nibabel as nib

from dlb_radiomics.ecat import load_ecat_series
from dlb_radiomics.interfile import load_interfile_series

DCM2NIIX_BIN = Path(dcm2niix.bin)


def detect_format(series_dir: Path) -> str:
    """Return "dicom", "ecat7", or "interfile" for a scan-series directory."""
    series_dir = Path(series_dir)
    if list(series_dir.glob("*.hdr")):
        return "interfile"
    if list(series_dir.glob("*.v")):
        return "ecat7"
    if list(series_dir.glob("*.dcm")):
        return "dicom"
    raise ValueError(f"{series_dir}: no recognized raw format (.dcm/.v/.hdr) found")


def convert_dicom_series(series_dir: Path, out_dir: Path) -> Path:
    """Convert a DICOM series to NIfTI via dcm2niix."""
    series_dir = Path(series_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            str(DCM2NIIX_BIN),
            "-z",
            "y",
            "-o",
            str(out_dir),
            "-f",
            series_dir.name,
            str(series_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    out_paths = sorted(out_dir.glob(f"{series_dir.name}*.nii.gz"))
    if not out_paths:
        raise RuntimeError(f"dcm2niix produced no output for {series_dir}")
    if len(out_paths) > 1:
        # A handful of ADNI "series" directories genuinely bundle two acquisitions
        # under one image ID (confirmed via dcm2niix -v 2: two full, same-size DICOM
        # sets with different AcquisitionNumber values -- e.g. two reconstruction
        # variants of the same scan, see docs/DECISIONS.md). dcm2niix names the first
        # acquisition it encounters with the bare series name and any later ones with
        # an "a"/"b"/... suffix; deterministically keep the bare (first) one rather
        # than fail the whole subject, since there's no available metadata to say
        # which acquisition is the "right" one.
        return out_paths[0]
    return out_paths[0]


def convert_interfile_series_to(series_dir: Path, out_dir: Path) -> Path:
    """Convert an Interfile series to NIfTI via the direct reader in interfile.py."""
    series_dir = Path(series_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = load_interfile_series(series_dir)
    out_path = out_dir / f"{series_dir.name}.nii.gz"
    img.to_filename(out_path)
    return out_path


def convert_ecat_series_to(series_dir: Path, out_dir: Path) -> Path:
    """Convert an ECAT7 series to NIfTI via the direct reader in ecat.py."""
    series_dir = Path(series_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    v_paths = list(series_dir.glob("*.v"))
    if len(v_paths) != 1:
        raise ValueError(f"{series_dir}: expected exactly one .v file, found {v_paths}")

    img = load_ecat_series(v_paths[0])
    out_path = out_dir / f"{series_dir.name}.nii.gz"
    img.to_filename(out_path)
    return out_path


def _collapse_dynamic_frames(nifti_path: Path) -> Path:
    """Average a 4D dynamic-frame PET volume (e.g. multiple time frames) down to 3D.

    Some raw ADNI FDG-PET series are dynamic (multiple time frames per voxel grid)
    rather than a single static image, which registration.register_pet_to_t1 requires.
    Averaging matches ADNI's own "Coreg, Avg" processed-PET convention. No-op for
    already-3D images (the common case, and all MRI series).
    """
    img = nib.load(nifti_path)
    if img.ndim <= 3:
        return nifti_path

    averaged = img.get_fdata().mean(axis=-1).astype("float32")
    nib.Nifti1Image(averaged, img.affine).to_filename(nifti_path)
    return nifti_path


def ingest_series(series_dir: Path, out_dir: Path) -> Path:
    """Convert any raw scan-series directory to NIfTI, dispatching by detected format."""
    fmt = detect_format(series_dir)
    if fmt == "interfile":
        out_path = convert_interfile_series_to(series_dir, out_dir)
    elif fmt == "ecat7":
        out_path = convert_ecat_series_to(series_dir, out_dir)
    elif fmt == "dicom":
        out_path = convert_dicom_series(series_dir, out_dir)
    else:
        raise ValueError(f"Unhandled format: {fmt}")
    return _collapse_dynamic_frames(out_path)
