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

## Next

- **Extract to one scan per subject.** Both image sets currently include every visit where a
  qualifying MRI/FDG-PET scan exists, not just the one closest to each subject's SAA draw
  date. Before feature extraction, filter down using the per-subject target dates already in
  `dlb_cohort_candidates.csv` / `saa_negative_controls.csv` (columns `FDG_PET_EXAMDATE`,
  `MRI_EXAMDATE`) — keep the other-visit scans on disk in case a longitudinal check is wanted
  later, just don't feed them all into the initial model.
- **Design the radiomics pipeline.** No `src/` code exists yet for this project. Needs: DICOM →
  NIfTI conversion, PET/MRI co-registration (a la spatial normalization to an atlas or to the
  MRI), tumor/region segmentation or atlas-based ROI extraction, radiomic feature extraction
  (e.g. PyRadiomics), classifier (SAA+ vs SAA− as the primary label). Tooling decided:
  `dcm2niix` + `SimpleITK` + `antspyx` + `pyradiomics`, which forced pinning the project to
  Python 3.9 exactly (pyradiomics has no working build/wheel past cp39; see git log and,
  while the design task is in progress, `docs/DECISIONS.md`). Stage design (coregistration
  scheme, ROI/atlas source, directory layout) still in progress. A small fraction of raw
  images (37 series, 25 subjects) were in an Interfile format neither `dcm2niix` nor
  `SimpleITK` can read, and `medcon` turned out to silently corrupt the pixel values for
  this variant — wrote a direct reader instead (`src/dlb_radiomics/interfile.py` +
  `scripts/convert_interfile_series.py`), ran successfully against all 37 series. Also
  confirmed FDG-PET acquisitions (at least the Interfile/ECAT ones) are 6-frame dynamic
  scans; frames are currently combined by a plain raw-count sum, not decay-corrected —
  still an open question, see `docs/DECISIONS.md`.
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
