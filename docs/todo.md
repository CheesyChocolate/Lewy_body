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

- **Switched segmentation from antspynet to FastSurfer, `--seg_only` partial-GPU mode
  (decided + implemented + validated 2026-09-03).** antspynet's
  `desikan_killiany_tourville_labeling` + `deep_atropos` hybrid (`docs/KNOWLEDGE.md`
  "Registration / segmentation") wasn't accurate enough. Switched to FastSurfer,
  installed on Olympus via Docker (`deepmi/fastsurfer:latest`, NVIDIA Container Toolkit
  configured for `--gpus all`), called from `registration.run_fastsurfer` with
  `--seg_only --device cuda --viewagg_device cpu --no_hypothal` (bias-field correction and
  CerebNet cerebellum sub-segmentation both left on; falls back to `--device cpu` only if
  partial-GPU OOMs on Olympus's 4GB card) — one call now produces both the DKT cortical
  labels and the aseg brain-stem/cerebellum reference region that previously needed two
  separate antspynet models. **No ROI ID remapping was needed** (confirmed directly
  against FastSurfer's `FreeSurferColorLUT.txt`: both tools use the same standard
  FreeSurfer/DKT label numbering); only `REFERENCE_TISSUE_LABELS` in `features.py` changed,
  from `deep_atropos`'s own six-tissue codes to real FreeSurfer `aseg` IDs
  (Brain-Stem=16, Cerebellum-{WM,Cortex} L/R = 7/8/46/47). Validated before the full
  re-extraction: determinism confirmed empirically (two independent runs, same T1,
  0/16,777,216 differing label voxels), and a one-subject diff against the old
  `features.csv` row (`006_S_4363`) matched exactly on feature count (11,063) with
  physiologically plausible SUVR values, confirming no ROI mask was silently eroded by
  the extra native-grid resampling step. Full rationale in `docs/KNOWLEDGE.md` under
  "Superseded: switched from antspynet to FastSurfer" and its "Implementation" subsection.
  `src/dlb_radiomics/__init__.py`'s now-dead TF/cuDNN determinism setup was removed
  (antspynet/tensorflow no longer imported anywhere in this package); the ANTs
  determinism fix (the one that actually matters) is untouched.
- **Full re-extraction of `features.csv` launched (2026-09-03), supersedes the two
  items below.** Old antspynet-based `features.csv` renamed to
  `features_antspynet_backup.csv` (not deleted) rather than resumed-into, since the
  segmentation method changed for every subject, not just the previously-broken ones —
  see the ECAT7/Interfile-orientation and ECAT7-decay-correction re-extraction items
  below, both now moot (a full fresh extraction covers them regardless of their own
  status). Check `data/adni/features.csv` row count / tmux session status before running
  `nested_cv` again.
- **Feature non-determinism and duplicate-subject rows both FIXED (2026-08-29).**
  Root cause and fix: `docs/KNOWLEDGE.md` "Feature reproducibility" and "Cohort /
  series-selection correctness". Spot-check (re-extracted `068_S_2171` twice) now
  gives 0/11,063 differing features, bit-identical. `cohort.py`'s `load_cohort()` now
  dedupes by RID (deduped manifest: 491 unique subjects with both modalities, not 497
  — the old 497 figure was itself inflated by the duplicate rows).
- **ECAT7 decay-correction FIXED and applied (2026-08-29), pending independent
  confirmation.** Rather than wait on the PET specialist's answer (question still sent,
  `docs/ecat7_decay_correction_question.md`), found strong indirect evidence in ADNI's
  own PET Technical Procedures Manual (see `docs/KNOWLEDGE.md` "Image ingestion" and the
  question doc's "What we ended up doing" section for the full reasoning) and
  implemented the fix: `src/dlb_radiomics/ecat.py` (`load_ecat_series`) reads ECAT7
  directly via `nibabel.ecat` and applies each frame's own `decay_corr_fctr` before
  summing, mirroring the Interfile fix. Wired into `ingest.py` in place of the old
  plain-mean `dcm2niix` path. Verified end-to-end on a real ECAT7-sourced subject
  (`006_S_4515`, 11,063 features, no errors). **If the specialist's answer contradicts
  this reasoning, all 179 ECAT7-sourced subjects need re-extraction with the correction
  reversed** — check whether an answer has come back and revisit if so.
- **Full-cohort batch re-launched clean against the fully-fixed pipeline (2026-08-29
  ~01:55 UTC, includes the ECAT7 fix above), running as of end of session — check status
  first next session.** `scripts/extract_all_features.py`, tmux session `extract_all` on
  Olympus, checkpointed to `data/adni/features.csv`. ETA roughly
  **~2026-08-31 06:00 UTC** for all 491 subjects (based on ~234s/subject pace from the
  prior run). Check with
  `ssh Olympus "tmux has-session -t extract_all; wc -l ~/Projects/Lewy_body/data/adni/features.csv"`
  — 492 rows (header + 491) with the tmux session gone means it finished cleanly. Only
  once this finishes should `classify.nested_cv` be run and fold-level AUC-ROC/accuracy
  reported. (Note: while an earlier run of this batch was in progress, its progress
  prints stopped appearing in the tee'd log for 40+ minutes due to Python stdout
  buffering — not a real hang, see `CLAUDE.md` "Olympus" gotcha. Don't panic-kill a
  healthy run over this again; check `features.csv` row count, not just the log tail.)
- **Extraction batch COMPLETE (2026-09-02): 491/491, `features.csv` has 492 rows.**
  `classify.nested_cv` run (`scripts/run_nested_cv.py`, results in
  `data/adni/nested_cv_results.csv`): **mean AUC-ROC 0.547 ± 0.074, mean accuracy 0.536 ±
  0.087** — near-chance. Before accepting "the classifier is just weak," spot-checked
  registration/extraction quality instead of only reasoning about it, and this uncovered a
  real bug (not a genuine FOV limitation as first suspected — see
  `docs/KNOWLEDGE.md` "PET field-of-view coverage" for the full corrected reasoning trail):
  **an ECAT7 orientation bug, FIXED and verified 2026-09-02.** `nibabel.ecat`'s affine
  ignores the same-library data reorientation it applies based on each file's
  `patient_orientation` header, so the two only agree for some files. Confirmed via header
  survey + real per-ROI checks: 30 of 101 ECAT7 subjects (header code 8, unrecognized) had
  corrupted PET orientation; the other 71 (code 3) were already correct. Fixed in
  `src/dlb_radiomics/ecat.py` (forces the correct orientation explicitly instead of
  trusting the header), verified end-to-end on both a previously-broken and a
  previously-correct subject — no regression for the 71, fix confirmed for the 30.
  **A second, independent orientation bug was also found and FIXED in Interfile.**
  `interfile.py`'s hand-built affine didn't match its raw data's y/z axis order (same
  class of risk as ECAT7 — from-scratch code, no library backing). Unlike ECAT7's
  per-file-header split, all 3 spot-checked Interfile subjects showed the bug (systematic,
  not per-subject-random). User visually identified the correct fix (`yz`, a proper
  180-degree rotation — a different transform than ECAT7's `xyz`, as expected since these
  are two unrelated bugs). Fixed in `src/dlb_radiomics/interfile.py`
  (`load_interfile_frame`, added a y/z flip after the reshape), verified via the real
  `ingest_series` path: all 3 spot-checked subjects now 100%/100% (was 46.0-99.6% mean).
  DICOM (2/2 spot-checked) was clean, no bug found there.
  Evidence/figures: `figs/pet_fov_*.png`, `figs/pet_interfile_*.png`.

  - **Verified both fixes across the actual variant space (not just 1-2 examples), per
    user request.** Interfile has only 1 geometry variant total (22/22 subjects identical
    shape/spacing) — already-checked subjects are fully representative. ECAT7 has 5
    distinct (code × matrix size × slice count × pixel spacing) variants; the original
    checks covered 2, the remaining 3 were spot-checked afterward (`109_S_4531`,
    `024_S_4280`, `031_S_4203`) and all came back 99.9-100% coverage, consistent.
    `figs/pet_fov_ecat7_unchecked_variants.png`.
  - **User visually re-confirmed the fix on 2026-09-03** on 2 fresh subjects per variant
    group (14 total across all 5 ECAT7 + Interfile + a DICOM reference pair) — full PET
    coverage to the top of the skull, no clipping, in every group. Scripts:
    `scripts/enumerate_pet_variants.py`, `scripts/plot_pet_variant_checks.py`. Figures:
    `figs/pet_fov_variant_recheck/`, `figs/pet_fov_variant_recheck_index.png`.
  - **Residual open question: left-right correctness isn't fully proven, only strongly
    argued.** A mutual-information check (independent of coverage) came back inconclusive
    for the same reason coverage did — global metrics are blind to laterality because the
    brain is roughly bilaterally symmetric. Current confidence rests on external
    convention (ECAT7) and visual judgment (both). A decisive test would need a
    strongly-lateralized-pathology subject; not done. Revisit if downstream results ever
    look laterality-suspicious.
  - **NOT yet done: re-extract affected subjects.** `features.csv` on Olympus still has
    OLD/WRONG values for: **30 ECAT7 subjects** (header `patient_orientation == 8`) and
    likely **all 22 Interfile subjects** (bug was systematic, not per-subject — safe to
    just re-extract all 22 rather than assume only some are affected). **Do not re-run
    `nested_cv` until both are re-extracted** — delete their rows from `features.csv` on
    Olympus and re-run `scripts/extract_all_features.py` (resumable/append-only, skips
    PTIDs already present, so deleting the affected rows first forces their
    re-extraction against the now-fixed `ecat.py`/`interfile.py`).

- **Reuse ADNI's own FDG-PET and FreeSurfer processing outputs instead of rebuilding from
  raw images.** Decided per `docs/preliminary_research/` (Jagust et al. 2010/2024 on the
  ADNI PET Core's cross-scanner smoothing harmonization): coregistration/normalization
  should extract ROI-space values from the already-harmonized `UCBERKELEYFDG_8mm` table in
  `data/adni/tables/`, not recoregister/renormalize raw PET images with `antspyx`. ROI
  source should be the existing FreeSurfer parcellations in `UCSFFSX51`/`UCSFFSX*`, not a
  new atlas or fresh segmentation — with one remaining check before implementation: confirm
  the parcellation separates posterior cingulate, occipital, and parietal cortex at
  sufficient granularity to capture the DLB "cingulate island sign" (McKeith et al. 2017,
  Lim et al. 2009). This resolves the "coregistration scheme" and "ROI/segmentation source"
  open questions from the pipeline-design task below.
- **ECAT7 frame combination still needs the same decay-correction fix.** The Interfile side
  is done (see Done section): `load_interfile_frame`/`load_interfile_series` in
  `src/dlb_radiomics/interfile.py` now scale each frame by its header's own `decay
  correction factor` before combining (the HRRT scanner computes this factor but leaves it
  unapplied in the raw export). The 179 ECAT7 series (`.v` files) still use a plain sum and
  need the equivalent fix — ECAT's own multi-frame header format encodes a per-frame decay
  factor too, needs the same treatment once `dcm2niix`'s ECAT path is revisited.
- **Classifier stage must use nested cross-validation.** Literature review
  (Demircioğlu 2021/2024) found that feature selection or class-balancing (oversampling the
  SAA-positive minority, 126 vs 415) performed on the full dataset before splitting into CV
  folds inflates reported performance by up to 0.15 AUC-ROC / 0.17 accuracy — both steps
  must be fit independently inside each training fold. Report performance as a distribution
  across outer folds with confidence intervals, not a single point estimate, given the
  cohort size (~541) is in the range where single-split estimates are unstable. Not yet
  implemented (no classifier code exists yet).

- **Extract to one scan per subject.** Both image sets currently include every visit where a
  qualifying MRI/FDG-PET scan exists, not just the one closest to each subject's SAA draw
  date. Before feature extraction, filter down using the per-subject target dates already in
  `dlb_cohort_candidates.csv` / `saa_negative_controls.csv` (columns `FDG_PET_EXAMDATE`,
  `MRI_EXAMDATE`) — keep the other-visit scans on disk in case a longitudinal check is wanted
  later, just don't feed them all into the initial model. PET side is largely clean (541/541
  exact-date matches, only 6 subjects need a same-date multi-series tie-break); MRI side is
  blocked on the gap above.
- **Design the radiomics pipeline.** No `src/` code exists yet for this project. Needs: DICOM →
  NIfTI conversion, PET/MRI co-registration (a la spatial normalization to an atlas or to the
  MRI), tumor/region segmentation or atlas-based ROI extraction, radiomic feature extraction
  (e.g. PyRadiomics), classifier (SAA+ vs SAA− as the primary label). Tooling decided:
  `dcm2niix` + `SimpleITK` + `antspyx` + `pyradiomics`, which forced pinning the project to
  Python 3.9 exactly (pyradiomics has no working build/wheel past cp39; see git log and,
  while the design task is in progress, `docs/DECISIONS.md`). Coregistration scheme and
  ROI/atlas source are now resolved (see item above); directory layout for `src/` and the
  concrete PyRadiomics feature-class list are still open (feature-class defaults from IBSI,
  no literature reason found to narrow them — see `docs/preliminary_research/`). A small
  fraction of raw images (37 series, 25 subjects) were in an Interfile format neither
  `dcm2niix` nor `SimpleITK` can read, and `medcon` turned out to silently corrupt the pixel
  values for this variant — wrote a direct reader instead (`src/dlb_radiomics/interfile.py`
  + `scripts/convert_interfile_series.py`), ran successfully against all 37 series. Also
  confirmed FDG-PET acquisitions (at least the Interfile/ECAT ones) are 6-frame dynamic
  scans; frame combination needs a decay-correction fix, see item above.
- **OASIS data likely unused.** `data/oasis/` (oasis-1, oasis-2, oasis-scripts) is staged but
  probably won't be wired into the pipeline — ADNI alone covers the current plan. Left in
  place rather than deleted in case an sMRI-only external validation need comes up later.
- **Rewrite the differential/statistical framing for the new modality.** The old project's
  `docs/knowledge.md` (now archived) had running notes on biological background and stats
  choices for CSF proteomics — a fresh `docs/knowledge.md` should start once non-obvious
  radiomics/imaging decisions start accumulating (e.g. why a given atlas, why a given
  normalization scheme).

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
