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
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel import ecat


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
    data = img.get_fdata()
    if data.ndim != 4:
        # Some ECAT7 exports are already a single static frame; nothing to combine.
        return nib.Nifti1Image(data.astype(np.float32), img.affine)

    subheaders = img.get_subheaders().subheaders
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
