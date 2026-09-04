# TODO

Living tracker for the DLB radiomics project. Update as items complete or new ones surface —
don't let this drift stale. See `docs/data_acquisition.md` for the full data-acquisition
rationale and `CLAUDE.md` for project orientation.

## Done

- Archived old CSF proteomics project (`archive_csf_proteomics/`, branch `archive/csf-proteomics-v1`).
- Downloaded full ADNI tabular data (`ADNIMERGE2`, 215 tables) + converted to CSV.
- Downloaded `AMPRION_ASYN_SAA` and `CSFALPHASYN` biospecimen tables (not in `ADNIMERGE2`).
- Built SAA-positive cohort: 126 subjects with FDG-PET + MRI within 365 days of SAA draw
  (`data/adni/dlb_cohort_candidates.csv`).
- Built SAA-negative control cohort: 415 subjects, same logic
  (`data/adni/saa_negative_controls.csv`).
- Downloaded raw DICOM images for both cohorts (T1 MRI + FDG-PET) from `Olympus`, pulled to
  this workstation, and extracted into `data/adni/images/ADNI/` (~76 GB decompressed:
  471,034 `.dcm` files + raw-format PET sidecars `.i`/`.hdr`/`.v` + per-image XML metadata).
  Zip files removed after extraction.
- Closed the missing-MRI gap and moved canonical data storage to `Olympus`. Discovered
  376/541 cohort rows (69%) had zero raw MRI on disk because the original search's
  `*SPGR*` wildcard only matched GE-scanner T1 naming, missing Siemens `MPRAGE` sites
  (`docs/data_acquisition.md` section 7). Corrected search downloaded and, since the
  workstation lacks disk space for the full ~190GB image dataset, extracted directly on
  Olympus into `~/Projects/Lewy_body/data/adni/images/ADNI/` along with the SAA-negative
  and SAA-positive-v2 cohort image sets (1,094,206 files total), plus the tabular data
  and 37 Interfile-converted `.nii.gz` PET outputs synced over from the workstation. Full
  detail in `docs/data_acquisition.md` section 8. Olympus (`~/Projects/Lewy_body`,
  remote `git@github-lewy-body:CheesyChocolate/Lewy_body.git`) is now the canonical data
  and pipeline-execution location; this workstation is for code development.
- Wrote a preliminary-research literature review (`docs/preliminary_research/`, IEEE-style,
  compiles via `latexmk conference_paper.tex`) to check the pipeline design against current
  literature. Resolved two of the pipeline's open design questions and surfaced two
  previously-undocumented fixes — see the "Next" items below for what changed as a result.
- Fixed Interfile PET frame combination to apply per-frame decay correction (was a plain
  raw-count sum). `load_interfile_frame`/`load_interfile_series` in
  `src/dlb_radiomics/interfile.py` now scale each frame by its header's `decay correction
  factor` before combining. Regenerated all 37 series' `.nii.gz` outputs and synced the
  corrected versions to Olympus.
- **Pivoted from "reuse ADNI's processed FDG-PET/FreeSurfer outputs" to a DIY pipeline.**
  Verified via direct IDA search that ADNI's own processed-PET/FreeSurfer-segmentation
  products only cover ~36/534 and ~5/534 of the cohort respectively — not viable as the
  primary path. Built the full pipeline instead: `src/dlb_radiomics/ingest.py` (DICOM/
  ECAT7/Interfile → NIfTI, collapses 4D dynamic-frame PET to static 3D, handles series
  directories that bundle two acquisitions), `registration.py` (native-space DKT cortical
  labeling via `antspynet.desikan_killiany_tourville_labeling`, no atlas download needed;
  rigid PET→T1 registration via `antspyx`), `features.py` (SUVR normalization using
  `antspynet.deep_atropos`'s brain-stem+cerebellum labels as the reference region — DKT
  has no pons/vermis; pyradiomics extraction resampled to 2mm isotropic), `classify.py`
  (nested-CV: L1 logistic regression + SelectKBest + SMOTE, all refit per fold). Verified
  end-to-end on a real subject on Olympus (GPU-accelerated, ~360s/subject).
- **Fixed a critical cohort-building bug**: `cohort.py`'s series-selection had no
  modality filter at all, so a subject's "PET" series could silently resolve to an actual
  MRI directory (confirmed on real data). Fixed via DICOM Modality-tag / format-based
  detection (`series_modality()`). Corrected core cohort is smaller: **497 subjects (118
  positive / 379 negative)**, down from the previously-assumed 541 (126/415) — the old
  figure was computed on the buggy manifest and is superseded.
- Set up Olympus's GPU (NVIDIA driver + `tensorflow[and-cuda]`) and added a 24G swapfile
  — see `CLAUDE.md` "Olympus (execution machine)" for the operational details.

## Next

- **ROI set expanded to full DKT cortex + subcortical nuclei (2026-09-05), extraction
  batch relaunching against it.** Rationale, exact regions, label IDs:
  `docs/KNOWLEDGE.md` "ROI scope: expanded to full DKT cortex + subcortical nuclei".
  This coincides with the batch below needing a relaunch anyway, so both land in the same
  fresh run.
- **Full re-extraction batch STALLED, relaunching (found 2026-09-05).** The 491-subject
  FastSurfer batch launched 2026-09-03 (see completed-batch history below) didn't finish:
  the GPU execution machine crashed and rebooted partway through, killing the run at
  199/491 subjects with no surviving session or log. Also found and fixed a repo-history
  divergence between the two machines' `trunk` (FastSurfer-switch commits had only ever
  been committed on the execution machine, never pushed) — reconciled, force-pushed,
  execution machine did a clean `git pull`. **New rule going forward: all commits happen
  on the dev workstation only; the execution machine is pull-only, never edited/committed
  on directly.** Old `features.csv` (199 rows, pre-ROI-expansion) backed up, not deleted;
  fresh batch launched clean.
- **Segmentation switched from antspynet to FastSurfer (2026-09-03).** Full rationale,
  validation, and the old antspynet-era 13-ROI implementation notes:
  `docs/KNOWLEDGE.md` "Superseded: switched from antspynet to FastSurfer" and its
  "Implementation" subsection.
- **Feature non-determinism + duplicate-subject rows FIXED (2026-08-29).** Root cause,
  fix, and verification: `docs/KNOWLEDGE.md` "Feature reproducibility" and "Cohort /
  series-selection correctness".
- **ECAT7 decay-correction FIXED (2026-08-29), and PET orientation bugs (ECAT7 + Interfile)
  FIXED and visually verified across all format/geometry variants (2026-09-02/03).** Full
  investigation, evidence, and residual left-right-correctness caveat:
  `docs/KNOWLEDGE.md` "Image ingestion" and "PET field-of-view coverage".
- **Extraction batch history:** launched 2026-08-29 (post dedup/determinism/ECAT7 fixes),
  completed 2026-09-02 (491/491) at near-chance AUC-ROC (0.547 ± 0.074) — which is what
  triggered the FOV/orientation investigation above — then superseded by the FastSurfer
  switch and now the ROI expansion. **Do not run `classify.nested_cv` until the current
  (ROI-expanded, post-crash-relaunch) batch finishes.**
- **Classifier stage must use nested cross-validation.** Literature review
  (Demircioğlu 2021/2024) found that feature selection or class-balancing (oversampling the
  SAA-positive minority) performed outside a per-fold loop inflates reported performance by
  up to 0.15 AUC-ROC / 0.17 accuracy. Implemented in `classify.py`'s `nested_cv`.
- **Extract to one scan per subject.** Both image sets currently include every visit where a
  qualifying MRI/FDG-PET scan exists, not just the one closest to each subject's SAA draw
  date. Per-subject target dates already exist in `dlb_cohort_candidates.csv` /
  `saa_negative_controls.csv` (`FDG_PET_EXAMDATE`, `MRI_EXAMDATE`) for this filter. PET side
  is largely clean (541/541 exact-date matches, 6 need a same-date tie-break); MRI side
  status needs rechecking against the current cohort manifest.
- **OASIS data likely unused.** `data/oasis/` (oasis-1, oasis-2, oasis-scripts) is staged but
  probably won't be wired into the pipeline — ADNI alone covers the current plan. Left in
  place rather than deleted in case an sMRI-only external validation need comes up later.

## Deferred / not started

- **E-DLB consortium external validation.** Referenced in `docs/advisor_notes/2.md` as a
  possible future validation cohort. Not a public download — requires a data access request
  to the consortium. No request has been made.
- **Other PET tracers (amyloid, tau).** Out of scope for the primary FDG-PET target. Tabular
  SUVR summaries are already present in `data/adni/tables/` if wanted as covariates later;
  the underlying PET images were not downloaded.
- **Raw genetic data (WGS/SNP arrays).** APOE genotype (the standard AD/DLB covariate) is
  already in `data/adni/tables/APOERES.csv`. Full genetic data would only matter for a
  polygenic-risk/GWAS-style analysis, not currently planned.
- **Fix nested `.git` in `data/oasis/oasis-scripts/`.** That directory was cloned in place and
  retains its own `.git/`, which isn't covered by `data/.gitignore`'s negation rules. Flagged
  as a risk (could get added as a broken submodule gitlink if someone runs `git add -A` on
  `data/`), not yet fixed.
