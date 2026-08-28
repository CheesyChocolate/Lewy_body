"""dlb_radiomics: DLB FDG-PET radiomics pipeline.

Sets process-wide determinism flags before any GPU/ANTs library gets imported
elsewhere in the process, so repeated runs on the same input produce identical
features -- see docs/KNOWLEDGE.md "Feature reproducibility" for the bug this
fixes (duplicate-subject re-extractions diverged on ~99.5% of feature columns).
Must live here (not in registration.py/features.py) because TF's determinism
env vars only take effect if set before tensorflow is first imported anywhere,
and antspynet imports tensorflow internally.
"""

import os

os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
os.environ.setdefault("TF_CUDNN_DETERMINISTIC", "1")

import random

import numpy as np

random.seed(0)
np.random.seed(0)

try:
    import tensorflow as tf

    tf.random.set_seed(0)
except ImportError:
    pass
