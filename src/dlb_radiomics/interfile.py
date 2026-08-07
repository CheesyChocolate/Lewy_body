"""Reader for ADNI's Interfile-format raw FDG-PET exports.

A small fraction of ADNI's early-phase (HRRT-site) FDG-PET raw exports are dynamic PET
frames encoded as Interfile (a plain-text `.hdr` header plus a raw `.i` binary data
file), one `.hdr`/`.i` pair per frame. Neither `dcm2niix` nor `SimpleITK` can read this
format. `medcon` (xmedcon) parses the header correctly but silently corrupts the pixel
values for this Siemens/HRRT variant -- verified 2026-08-07 by comparing its output
against reading the raw bytes directly: medcon produced float32 values up to ~1e38
(nonsense for PET counts), while reading the same `.i` file as little-endian float32
gives clean values in [0, ~0.5]. Do not use medcon for these files; this module reads
the format directly instead.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def parse_interfile_header(hdr_path: Path) -> dict[str, str]:
    """Parse an Interfile `.hdr` text header into a lowercase-keyed dict."""
    header: dict[str, str] = {}
    for line in Path(hdr_path).read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("!"):
            continue
        if ":=" not in line:
            continue
        key, _, value = line.partition(":=")
        header[key.strip().lower()] = value.strip()
    return header


def _find_data_file(hdr_path: Path, header: dict[str, str]) -> Path:
    """Resolve the `.i` data file referenced by a `.hdr` header.

    ADNI's de-identification process strips a suffix from the filename recorded in the
    header (`name of data file`), so the recorded name usually doesn't match what's
    actually on disk. Fall back to matching by prefix, then to "the only .i file in the
    directory" if that's unambiguous.
    """
    directory = Path(hdr_path).parent
    recorded = header.get("name of data file", "")
    if recorded:
        candidate = directory / recorded
        if candidate.exists():
            return candidate
        prefix = Path(recorded).stem
        matches = [p for p in directory.glob("*.i") if p.name.startswith(prefix)]
        if len(matches) == 1:
            return matches[0]

    matches = list(directory.glob("*.i"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(
        f"Could not uniquely resolve the data file for {hdr_path} "
        f"(recorded name {recorded!r}, candidates in dir: {matches})"
    )


def load_interfile_frame(hdr_path: Path) -> nib.Nifti1Image:
    """Load a single Interfile frame (one `.hdr` + `.i` pair) as a NIfTI image."""
    hdr_path = Path(hdr_path)
    header = parse_interfile_header(hdr_path)

    if header.get("number format", "").lower() != "float":
        raise NotImplementedError(f"Unsupported number format: {header.get('number format')!r}")
    if header.get("number of bytes per pixel") != "4":
        raise NotImplementedError(
            f"Unsupported bytes per pixel: {header.get('number of bytes per pixel')!r}"
        )

    shape = tuple(int(header[f"matrix size [{i}]"]) for i in (1, 2, 3))
    spacing = tuple(float(header[f"scaling factor (mm/pixel) [{i}]"]) for i in (1, 2, 3))

    data_path = _find_data_file(hdr_path, header)
    raw = np.fromfile(data_path, dtype="<f4")
    expected = shape[0] * shape[1] * shape[2]
    if raw.size != expected:
        raise ValueError(
            f"{data_path}: expected {expected} voxels for matrix size {shape}, got {raw.size}"
        )
    # Interfile/Analyze-family convention: matrix size [1] is the fastest-varying axis
    # (column-major / Fortran storage order).
    volume = raw.reshape(shape, order="F")

    dx, dy, dz = spacing
    affine = np.diag([-dx, dy, dz, 1.0])
    affine[:3, 3] = [dx * shape[0] / 2, -dy * shape[1] / 2, -dz * shape[2] / 2]

    return nib.Nifti1Image(volume.astype(np.float32), affine)


def load_interfile_series(series_dir: Path, *, combine: str = "sum") -> nib.Nifti1Image:
    """Load a dynamic Interfile PET series (one `.hdr`/`.i` pair per frame) as a single
    static NIfTI image.

    `combine`: "sum" (raw-count sum across frames, default) or "mean". Neither applies
    per-frame decay correction -- ADNI's raw exports leave `applied decay correction
    factor` blank in the header, so frames are stored as raw, undecayed counts. Whether
    static radiomic features should instead use decay-corrected frame combination is
    still an open pipeline-design question (see docs/TODO.md); this gives a reasonable,
    clearly-labeled default rather than a physics-verified one.
    """
    series_dir = Path(series_dir)
    hdr_paths = sorted(series_dir.glob("*.hdr"))
    if not hdr_paths:
        raise FileNotFoundError(f"No .hdr files in {series_dir}")

    frames = [load_interfile_frame(p) for p in hdr_paths]

    shapes = {f.shape for f in frames}
    if len(shapes) != 1:
        raise ValueError(f"{series_dir}: frames have inconsistent shapes: {shapes}")

    stacked = np.stack([f.get_fdata() for f in frames], axis=-1)
    if combine == "sum":
        combined = stacked.sum(axis=-1)
    elif combine == "mean":
        combined = stacked.mean(axis=-1)
    else:
        raise ValueError(f"Unknown combine mode: {combine!r}")

    return nib.Nifti1Image(combined.astype(np.float32), frames[0].affine)
