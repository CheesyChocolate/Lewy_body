"""Reader for ADNI's ECAT7-format raw FDG-PET exports (Siemens HR/HR+/EXACT/ACCEL scanners).

179 series in the cohort are ECAT7 (`.v` files, magic bytes `MATRIX72`) -- dynamic PET
frames from standard Siemens ECAT scanners (not the HRRT scanners that produce Interfile
exports, see interfile.py). `dcm2niix` converts these but collapses them into a plain
multi-frame NIfTI with no access to each frame's own `decay_corr_fctr` subheader field, so
this module reads the format directly via `nibabel.ecat` instead, mirroring the fix already
applied to the Interfile subset.

Per-frame decay correction: unlike Interfile's raw HRRT export (which has an explicit,
unambiguous `applied decay correction factor` header field confirming the correction is
computed but not applied), ECAT7's `corrections_applied` subheader bitmask has no
documented meaning we could confirm authoritatively (checked nibabel, TPCCLIB, Turku PET
Centre docs, general web search -- see docs/ecat7_decay_correction_question.md, sent to a
PET-physics specialist for confirmation). Applying `decay_corr_fctr` here anyway, based on
strong indirect evidence from ADNI's own PET Technical Procedures Manual
(adni.loni.usc.edu): both the "Siemens ECAT Exact HR+ (BGO) 63-slice scanners" protocol
(matches this format) and the "Siemens HRRT 207-slice scanners" protocol (produces the
Interfile files, where we have *definitive* proof the equivalent factor is NOT pre-applied
despite the manual saying the same "All corrections 'On'") are described identically in
that manual, and both use the same 6-frame/300s FDG acquisition protocol. If that analogy
turns out to be wrong once the specialist responds, this needs revisiting -- see
docs/KNOWLEDGE.md "Feature reproducibility" / ECAT7 for the full reasoning trail.

Orientation (fixed 2026-09-02, see docs/KNOWLEDGE.md "PET field-of-view coverage"):
`nibabel.ecat`'s `EcatImage.affine` is computed purely from header zooms/offsets and never
accounts for the per-file `patient_orientation`-driven data reorientation that
`img.get_fdata()` silently applies (`raw_data[::-1,::-1,::-1]` for codes 1/3/5/7,
`raw_data[::,::-1,::-1]` for 0/2/4/6, no flip at all for any other/unmatched code) --
meaning `img.get_fdata()` + `img.affine` together produce a self-consistent (data, affine)
pair only for a subset of files, by accident of which `patient_orientation` code happens to
combine with the raw storage layout to net out to a proper rotation. Confirmed on this
cohort's 101 ECAT7 subjects: only codes 3 (71 subjects, gets the correct triple-axis flip
already) and 8 (30 subjects, gets no flip and is genuinely wrong -- verified via real
per-ROI PET/T1 registration coverage, 0-62% instead of 100%, and visually) appear at all.
Fix: always request the triple-axis ("neurological") reorientation explicitly, regardless
of what each file's own header says, rather than trusting the per-file default.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel import ecat
from nibabel.ecat import get_frame_order


def _load_oriented_frames(subheader) -> np.ndarray:
    """Read every frame's data, always in the "neurological" (triple-axis-flipped)
    orientation regardless of the file's own `patient_orientation` header value -- see
    module docstring. Mirrors `EcatImageArrayProxy.__array__`'s frame-order handling.
    """
    nframes = subheader.get_nframes()
    shape = subheader.get_shape()
    frame_mapping = get_frame_order(subheader._mlist)
    data = np.empty(shape + (nframes,))
    for i in sorted(frame_mapping):
        data[:, :, :, i] = subheader.data_from_fileobj(
            frame_mapping[i][0], orientation="neurological"
        )
    return data


def load_ecat_series(
    v_path: Path, *, combine: str = "sum", decay_correct: bool = True
) -> nib.Nifti1Image:
    """Load a dynamic ECAT7 PET series (one `.v` file, multiple frame subheaders) as a
    single static NIfTI image.

    `combine`: "sum" (default) or "mean" across frames.
    `decay_correct`: if True (default), each frame is scaled by its own subheader
    `decay_corr_fctr` value before combining -- see module docstring for the (currently
    unconfirmed-by-an-authoritative-source, but well-evidenced) reasoning. Pass False to
    reproduce the old, uncorrected behavior.
    """
    v_path = Path(v_path)
    img = ecat.load(str(v_path))
    subheader = img.get_subheaders()
    data = _load_oriented_frames(subheader)

    subheaders = subheader.subheaders
    if len(subheaders) != data.shape[-1]:
        raise ValueError(
            f"{v_path}: {len(subheaders)} subheaders but {data.shape[-1]} frames"
        )

    frames = data
    if decay_correct:
        factors = np.array(
            [sh["decay_corr_fctr"] for sh in subheaders], dtype=np.float64
        )
        frames = frames * factors[np.newaxis, np.newaxis, np.newaxis, :]

    if combine == "sum":
        combined = frames.sum(axis=-1)
    elif combine == "mean":
        combined = frames.mean(axis=-1)
    else:
        raise ValueError(f"Unknown combine mode: {combine!r}")

    return nib.Nifti1Image(combined.astype(np.float32), img.affine)
