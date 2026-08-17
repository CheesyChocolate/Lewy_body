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

- **Integrate re-downloaded MRI and close the missing-MRI gap.** While starting the
  "one scan per subject" reduction below, discovered 376/541 cohort rows (69%) had zero
  raw MRI on disk despite `has_mri` being true — the original MRI search's `*SPGR*`
  wildcard only matches GE-scanner T1 naming, silently missing Siemens `MPRAGE`/`MP-RAGE`
  sites. Full root-cause and fix in `docs/data_acquisition.md` section 7. A corrected
  search (`*MP*RAGE*` + T1 + MRI, 3,603 series, 370 subjects) has been downloaded to
  Olympus (`~/adni_download/DLB_missing_MRI_v1_v2/`, `zip1.zip` 39.1GB + `zip2.zip`
  519MB, both complete and verified as of 2026-08-07). Integration decision made:
  stage first in `data/adni/images/ADNI_missing_mri_v1_v2_staging/` (dir already
  created), not merged directly. Pull command (needs `sshuttle` tunnel up first):
  `rsync -avP Olympus:~/adni_download/DLB_missing_MRI_v1_v2/ data/adni/images/ADNI_missing_mri_v1_v2_staging/`.
  **User is running this transfer themselves outside the session** — not yet done as of
  2026-08-07. Next session: confirm the staging dir is populated, unzip, decide
  merge-into-`ADNI/`-vs-keep-staged, then re-run the missing-MRI check to confirm closure.
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
