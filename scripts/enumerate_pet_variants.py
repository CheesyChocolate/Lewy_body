"""Enumerate the distinct PET geometry/orientation variants across the cohort and pick
two representative subjects per variant, for `scripts/plot_pet_variant_checks.py`.

Mirrors the variant definitions already used in the ECAT7/Interfile orientation-bug
investigation (docs/KNOWLEDGE.md "PET field-of-view coverage"):
  - ECAT7: (patient_orientation code, matrix size, slice count, pixel spacing)
  - Interfile: (shape, spacing) -- known to be a single variant (22/22 subjects identical)
  - DICOM: (rows, columns, n_slices, pixel spacing) -- not previously enumerated in
    that investigation (only spot-checked as a mature/clean format), included here for
    completeness since the user wants every variant the data can have.

Usage: uv run python3 scripts/enumerate_pet_variants.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydicom
from nibabel import ecat

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import detect_format
from dlb_radiomics.interfile import parse_interfile_header

OUT_PATH = Path("data/adni/pet_variant_groups.csv")


def _ecat_key(v_path: Path) -> tuple:
    img = ecat.load(str(v_path))
    sh0 = img.get_subheaders().subheaders[0]
    return (
        "ecat7",
        int(img.header["patient_orientation"]),
        int(sh0["x_dimension"]),
        int(sh0["z_dimension"]),
        round(float(sh0["x_pixel_size"]), 4),
    )


def _interfile_key(hdr_path: Path) -> tuple:
    header = parse_interfile_header(hdr_path)
    matrix = tuple(int(header[f"matrix size [{i}]"]) for i in (1, 2, 3))
    scaling = tuple(
        round(float(header[f"scaling factor (mm/pixel) [{i}]"]), 4) for i in (1, 2, 3)
    )
    return ("interfile", matrix, scaling)


def _dicom_key(series_dir: Path) -> tuple:
    dcm_path = next(series_dir.glob("*.dcm"))
    ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
    n_slices = len(list(series_dir.glob("*.dcm")))
    return (
        "dicom",
        int(ds.Rows),
        int(ds.Columns),
        n_slices,
        round(float(ds.PixelSpacing[0]), 4),
        round(float(getattr(ds, "SliceThickness", 0.0)), 4),
    )


def variant_key(pet_series_dir: Path) -> tuple:
    fmt = detect_format(pet_series_dir)
    if fmt == "ecat7":
        v_path = next(pet_series_dir.glob("*.v"))
        return _ecat_key(v_path)
    if fmt == "interfile":
        hdr_path = next(pet_series_dir.glob("*.hdr"))
        return _interfile_key(hdr_path)
    return _dicom_key(pet_series_dir)


def main() -> None:
    manifest = build_final_manifest()
    manifest = manifest[
        manifest["fdg_pet_series_dir"].notna() & manifest["mri_series_dir"].notna()
    ]

    rows = []
    for _, row in manifest.iterrows():
        try:
            key = variant_key(Path(row["fdg_pet_series_dir"]))
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {row['PTID']}: {exc}")
            continue
        rows.append({"PTID": row["PTID"], "RID": row["RID"], "label": row["label"],
                      "variant_key": str(key)})

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)

    counts = df["variant_key"].value_counts()
    print(f"{len(counts)} distinct variants across {len(df)} subjects:\n")
    for key, n in counts.items():
        example_ptids = df[df["variant_key"] == key]["PTID"].tolist()
        print(f"  n={n:4d}  {key}")
        print(f"           subjects: {example_ptids[:5]}{'...' if n > 5 else ''}")


if __name__ == "__main__":
    main()
