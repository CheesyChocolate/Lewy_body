# ADNI data

Source: [IDA/LONI](https://ida.loni.usc.edu/home/projectPage.jsp?project=ADNI), requires
signed ADNI Data Use Agreement. Not committed to git (see `data/.gitignore`).

## Layout

- `ADNIMERGE2/` — the official `ADNIMERGE2` R data package (ATRI Biostatistics), downloaded
  via ARC Builder → Study Files. Contains 217 ADNI tables as `.rda` files (diagnosis,
  demographics, PET/MRI QC and derived measures, biomarkers, assessments, etc.), plus R
  source and vignettes describing how ADNI's raw tables are merged/derived.
- `tables/` — CSV export of every data.frame in `ADNIMERGE2/data/*.rda`, produced by
  `scripts/convert_adnimerge2_to_csv.R` so the pipeline can stay Python-only. Re-run that
  script if `ADNIMERGE2` is re-downloaded/updated. 215 of 217 objects convert (2 skipped:
  a date scalar and a `Metacore` metadata object, neither of which is tabular data).

## Biospecimen (not in ADNIMERGE2)

`ADNIMERGE2` deliberately excludes some biospecimen tables (`R/utils.R` `exc_tbl`). Downloaded
separately from IDA (ARC Builder → Study Files → Biospecimen) into `biospecimen/`:

- `AMPRION_ASYN_SAA_04Aug2026.csv` — α-synuclein seed amplification assay (SAA), Amprion
  Clinical Laboratory. Key table for identifying the DLB-positive subset (per
  `docs/advisor_notes/1.md`). `Result` field: `Not_Detected`, `Detected-1` (PD/DLB-consistent
  profile — the DLB-positive marker), `Detected-2` (MSA-consistent profile), `Indeterminate`.
- `CSFALPHASYN_03_21_14_04Aug2026.csv` — quantitative CSF alpha-synuclein (Luminex, ng/ml,
  Jing Zhang Lab, UW). Distinct from the SAA seeding assay above; supplementary quantitative
  measure, not the DLB-positive marker itself.
- Methods/protocol PDFs for both are also in `biospecimen/`.

## Cohort candidates

`scripts/build_dlb_subject_list.py` cross-references SAA-positive (`Detected-1`) subjects
against FDG-PET (`UCBERKELEYFDG_8mm`) and structural MRI (`UCSFFSX51`) scan dates, keeping
the closest scan within 365 days of the SAA draw. Output: `dlb_cohort_candidates.csv` (one
row per SAA+ subject, with matched scan dates and day-offsets). Re-run after any data refresh.

## Relevant tables already present (for FDG-PET radiomics direction)

- `UCBERKELEYFDG_8mm.csv`, `BAIPETNMRCFDG.csv` — FDG-PET regional/derived measures.
- `AV45META.csv`, `AV45QC.csv`, `PETMETA3.csv`, `PETQC.csv` — PET acquisition metadata/QC,
  useful for filtering scans by protocol/date.
- `DXSUM.csv` — diagnosis summary.
- `PTDEMOG.csv` — demographics.
- `ADSL.csv` — subject-level analysis dataset (baseline characteristics).
