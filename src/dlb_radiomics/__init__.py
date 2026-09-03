"""dlb_radiomics: DLB FDG-PET radiomics pipeline.

Sets process-wide determinism flags before ANTs gets imported elsewhere in the process,
so repeated runs on the same input produce identical features -- see docs/KNOWLEDGE.md
"Feature reproducibility" for the bug this fixes (duplicate-subject re-extractions
diverged on ~99% of feature columns, confirmed still present after only setting
aff_random_sampling_rate=1.0 -- that alone doesn't fix it, ants.config.set_ants_deterministic
below is the real switch: it forces single-threaded ITK, which avoids nondeterministic
floating-point reduction order across threads, and passes a real --random-seed through to
the underlying antsRegistration CLI call).

The TF/cuDNN determinism setup this module used to also set here (before tensorflow's
first import) is gone: antspynet/tensorflow are no longer imported in-process anywhere in
this package (segmentation now runs via a containerized FastSurfer call, see
docs/KNOWLEDGE.md "Superseded: switched from antspynet to FastSurfer") -- FastSurfer's own
container process determinism is a separate, unverified question (see that same
KNOWLEDGE.md section for what was and wasn't checked).
"""

import random

import numpy as np

random.seed(0)
np.random.seed(0)

import ants

ants.config.set_ants_deterministic(on=True, seed_value=123)
