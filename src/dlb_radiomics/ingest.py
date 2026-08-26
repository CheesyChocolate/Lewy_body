"""DICOM/ECAT7/Interfile -> NIfTI ingestion, dispatched by file type.

A scan-series directory (one leaf under data/adni/images/ADNI/<PTID>/<series>/<datetime>/
<image_id>/) is one of three raw formats: DICOM (.dcm files, the majority), ECAT7 (.v
files), or Interfile (.hdr/.i pairs). This module picks the right converter per series
and returns a single output NIfTI path. See docs/DECISIONS.md "Raw image format mix" for
the format breakdown and docs/TODO.md for what's in/out of scope (ECAT7 decay correction
is a separate, not-yet-implemented item -- this module passes ECAT7 through dcm2niix as-is).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import dcm2niix
import nibabel as nib

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
    """Convert a DICOM or ECAT7 series to NIfTI via dcm2niix.

    Both formats go through the same dcm2niix CLI path; ECAT7 emits a "VERY
    experimental" warning (spatial transform reliability caveat, see
    docs/DECISIONS.md) but produces valid output.
    """
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

    out_paths = list(out_dir.glob(f"{series_dir.name}*.nii.gz"))
    if not out_paths:
        raise RuntimeError(f"dcm2niix produced no output for {series_dir}")
    if len(out_paths) > 1:
        raise RuntimeError(
            f"dcm2niix produced multiple outputs for {series_dir}: {out_paths} "
            "(series may contain more than one acquisition)"
        )
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
    elif fmt in ("dicom", "ecat7"):
        out_path = convert_dicom_series(series_dir, out_dir)
    else:
        raise ValueError(f"Unhandled format: {fmt}")
    return _collapse_dynamic_frames(out_path)
