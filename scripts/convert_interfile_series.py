#!/usr/bin/env python3
"""Convert ADNI's Interfile-format FDG-PET series to NIfTI.

Finds every Interfile series (directories containing `.hdr` files) under
data/adni/images/ADNI/, combines each series' per-frame dynamic acquisition into a
single static volume, and writes it as .nii.gz next to the source series. See
src/dlb_radiomics/interfile.py for why this exists instead of using dcm2niix/medcon.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import click

from dlb_radiomics.interfile import load_interfile_series

IMAGES_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "adni" / "images" / "ADNI"
)


def find_interfile_series_dirs(images_dir: Path) -> list[Path]:
    hdr_dirs = {p.parent for p in images_dir.rglob("*.hdr")}
    return sorted(hdr_dirs)


@click.command()
@click.option(
    "--combine",
    type=click.Choice(["sum", "mean"]),
    default="sum",
    help="How to combine dynamic frames into a static volume.",
)
@click.option(
    "--overwrite", is_flag=True, help="Re-convert series whose output already exists."
)
@click.option(
    "--no-decay-correct",
    is_flag=True,
    help="Skip per-frame decay correction (reproduces the old, uncorrected behavior).",
)
def main(combine: str, overwrite: bool, no_decay_correct: bool) -> None:
    decay_correct = not no_decay_correct
    series_dirs = find_interfile_series_dirs(IMAGES_DIR)
    click.echo(f"Found {len(series_dirs)} Interfile series under {IMAGES_DIR}")

    ok, failed = 0, []
    for series_dir in series_dirs:
        suffix = combine if decay_correct else f"{combine}_nodecay"
        out_path = series_dir / f"{series_dir.name}_{suffix}.nii.gz"
        if out_path.exists() and not overwrite:
            ok += 1
            continue
        try:
            img = load_interfile_series(
                series_dir, combine=combine, decay_correct=decay_correct
            )
            img.to_filename(out_path)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            failed.append((series_dir, exc))
            click.echo(f"FAILED: {series_dir}: {exc}", err=True)

    click.echo(f"Converted {ok}/{len(series_dirs)} series ({len(failed)} failed)")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
