"""Visual test of FastSurfer segmentation across all 14 subjects from the PET FOV
variant recheck (scripts/plot_pet_variant_checks.py), same style as that script's
_sidebyside.png (T1 | PET per view, no overlay), with a third row added showing the
FastSurfer DKT+aseg segmentation.

Ad hoc check, not part of the pipeline: confirms FastSurfer's partial-GPU --seg_only
output looks anatomically sane across the same 7 raw-format variant groups already
covered by the PET FOV recheck (2 subjects each), not just the FreeSurfer tutorial
subject, before wiring it into the pipeline for real. Written to
figs/pet_fov_variant_recheck/ alongside that script's _overlay.png/_sidebyside.png
outputs, as <ptid>_fastsurfer.png.

Usage (on Olympus): .venv/bin/python3 scripts/plot_fastsurfer_test.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import ants
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dlb_radiomics.cohort import build_final_manifest
from dlb_radiomics.ingest import ingest_series
from dlb_radiomics.registration import register_pet_to_t1

NIFTI_TMP_DIR = Path("data/adni/nifti_tmp_variant_recheck")
FS_TEST_DIR = Path("data/adni/fastsurfer_test")
FIGS_DIR = Path("figs/pet_fov_variant_recheck")
LUT_PATH = Path.home() / "fastsurfer-test" / "FreeSurferColorLUT.txt"
VIEWS = ["sagittal", "coronal", "axial"]

# Same 7 variant groups / 14 subjects as scripts/plot_pet_variant_checks.py.
VARIANT_SUBJECTS: dict[str, tuple[str, str]] = {
    "ecat7 code3 128x63 sp0.2574 (n=62)": ("006_S_4363", "006_S_4515"),
    "ecat7 code8 128x63 sp0.2574 (n=24)": ("041_S_4041", "036_S_5063"),
    "ecat7 code3 128x47 sp0.2059 (n=7)": ("109_S_4531", "109_S_4499"),
    "ecat7 code3 256x63 sp0.2574 (n=2)": ("024_S_4280", "037_S_4770"),
    "ecat7 code8 128x63 sp0.2059 (n=6)": ("031_S_4203", "031_S_4194"),
    "interfile (n=22, single geometry)": ("053_S_5070", "053_S_5272"),
    "dicom (reference, clean)": ("082_S_2307", "130_S_4660"),
}


def load_lut(path: Path) -> dict[int, tuple[float, float, float]]:
    """Parse FreeSurferColorLUT.txt ("id name R G B A" per line) into id -> RGB in
    [0, 1], so the segmentation row shows FastSurfer/FreeSurfer's own anatomical colors
    (e.g. cortex shades of tan/pink, ventricles blue-gray) instead of an arbitrary
    colormap -- a linear colormap over raw label IDs made adjacent DKT cortical labels
    (1002-1035) collapse to near-identical colors, hiding the parcellation entirely."""
    lut: dict[int, tuple[float, float, float]] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        label_id, _name, r, g, b = parts[:5]
        lut[int(label_id)] = (int(r) / 255, int(g) / 255, int(b) / 255)
    return lut


def mid_slices(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y, z = (s // 2 for s in arr.shape)
    return arr[x, :, :], arr[:, y, :], arr[:, :, z]


def run_fastsurfer(t1_nii: Path, sid: str) -> Path:
    """Run --seg_only partial-GPU FastSurfer on a T1 NIfTI, return the DKT+aseg path."""
    sd = FS_TEST_DIR.resolve()
    sd.mkdir(parents=True, exist_ok=True)
    out_seg = sd / sid / "mri" / "aparc.DKTatlas+aseg.deep.mgz"
    if out_seg.exists():
        return out_seg

    t1_abs = t1_nii.resolve()
    subprocess.run(
        [
            "sudo", "docker", "run", "--rm", "--gpus", "all",
            "--user", f"{subprocess.run(['id', '-u'], capture_output=True, text=True).stdout.strip()}:"
                      f"{subprocess.run(['id', '-g'], capture_output=True, text=True).stdout.strip()}",
            "-v", f"{t1_abs.parent}:/t1in",
            "-v", f"{sd}:/data",
            "deepmi/fastsurfer:latest",
            "--t1", f"/t1in/{t1_abs.name}",
            "--sid", sid, "--sd", "/data",
            "--seg_only", "--device", "cuda", "--viewagg_device", "cpu", "--no_hypothal",
        ],
        check=True,
    )
    return out_seg


def load_pair(ptid: str, manifest: pd.DataFrame) -> tuple[Path, np.ndarray, np.ndarray]:
    subj_dir = NIFTI_TMP_DIR / ptid
    subj_dir.mkdir(parents=True, exist_ok=True)
    t1_cache = subj_dir / "t1_arr.npy"
    pet_cache = subj_dir / "pet_arr.npy"

    row = manifest[manifest["PTID"] == ptid].iloc[0]
    t1_nii = ingest_series(Path(row["mri_series_dir"]), subj_dir)

    if t1_cache.exists() and pet_cache.exists():
        return t1_nii, np.load(t1_cache), np.load(pet_cache)

    pet_nii = ingest_series(Path(row["fdg_pet_series_dir"]), subj_dir)
    t1_arr = ants.image_read(str(t1_nii)).numpy()
    pet_arr = register_pet_to_t1(pet_nii, t1_nii).numpy()
    np.save(t1_cache, t1_arr)
    np.save(pet_cache, pet_arr)
    return t1_nii, t1_arr, pet_arr


def load_seg_on_t1_grid(seg_mgz: Path, t1_nii: Path) -> np.ndarray:
    """FastSurfer's own conformed-space output isn't on the same voxel grid as our
    T1 NIfTI (it resamples to a canonical 256^3 1mm grid) -- resample the label map
    (nearest-neighbor, to preserve integer labels) onto the T1's original grid so it
    lines up with the PET, which is already registered to that same T1 grid."""
    seg_img = ants.image_read(str(seg_mgz))
    t1_img = ants.image_read(str(t1_nii))
    seg_on_t1 = ants.resample_image_to_target(seg_img, t1_img, interp_type="genericLabel")
    return seg_on_t1.numpy()


def seg_to_rgb(seg_s: np.ndarray, lut: dict[int, tuple[float, float, float]]) -> np.ma.MaskedArray:
    """Map each label to its real FreeSurferColorLUT RGB, masking background (0)."""
    rgb = np.zeros(seg_s.shape + (3,), dtype=np.float32)
    for label_id in np.unique(seg_s):
        if label_id == 0:
            continue
        rgb[seg_s == label_id] = lut.get(int(label_id), (1.0, 1.0, 1.0))
    mask = np.repeat((seg_s == 0)[..., None], 3, axis=-1)
    return np.ma.masked_array(rgb, mask=mask)


def make_figure(ptid: str, variant: str, t1_slices, pet_slices, seg_slices, lut) -> Path:
    fig, axes = plt.subplots(3, 3, figsize=(12, 11))
    for i, view in enumerate(VIEWS):
        t1_s = np.rot90(t1_slices[i])
        pet_s = np.rot90(pet_slices[i])
        seg_s = np.rot90(seg_slices[i])

        axes[0, i].imshow(t1_s, cmap="gray")
        axes[0, i].set_title(f"{view}: T1", fontsize=10)
        axes[0, i].axis("off")

        axes[1, i].imshow(pet_s, cmap="hot")
        axes[1, i].set_title(f"{view}: PET", fontsize=10)
        axes[1, i].axis("off")

        axes[2, i].imshow(t1_s, cmap="gray")
        axes[2, i].imshow(seg_to_rgb(seg_s, lut), alpha=0.65, interpolation="nearest")
        axes[2, i].set_title(f"{view}: FastSurfer DKT+aseg", fontsize=10)
        axes[2, i].axis("off")

    fig.suptitle(f"{ptid} -- {variant}\nT1 / PET / FastSurfer segmentation (--seg_only, partial-GPU)")
    fig.tight_layout()
    out = FIGS_DIR / f"{ptid}_fastsurfer.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    manifest = build_final_manifest()
    NIFTI_TMP_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    lut = load_lut(LUT_PATH)

    for variant, ptids in VARIANT_SUBJECTS.items():
        for ptid in ptids:
            print(f"{variant}: {ptid}: loading T1/PET", flush=True)
            t1_nii, t1_arr, pet_arr = load_pair(ptid, manifest)

            print(f"{ptid}: running FastSurfer --seg_only", flush=True)
            seg_mgz = run_fastsurfer(t1_nii, ptid)

            print(f"{ptid}: resampling segmentation onto T1 grid", flush=True)
            seg_arr = load_seg_on_t1_grid(seg_mgz, t1_nii)

            t1_slices = mid_slices(t1_arr)
            pet_slices = mid_slices(pet_arr)
            seg_slices = mid_slices(seg_arr)

            out = make_figure(ptid, variant, t1_slices, pet_slices, seg_slices, lut)
            print(f"  wrote {out}", flush=True)


if __name__ == "__main__":
    main()
