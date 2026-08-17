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

## Next

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
- **Fix PET dynamic-frame combination: needs decay correction, not a plain sum.** Literature
  review found this is nonstandard — ADNI's own PET Core protocol decay-corrects each frame
  to a common reference time before combining into a static image; the current
  `src/dlb_radiomics/interfile.py` / `scripts/convert_interfile_series.py` plain raw-count
  sum under-weights later, more-decayed frames. Affects the 37 Interfile series and the 179
  ECAT7 series (216 of 2,160 total series). Needs per-frame decay correction using each
  frame's start time and the F-18 half-life (109.77 min) before summing; the 37
  already-converted `.nii.gz` outputs on Olympus will need regenerating once this is fixed.
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
