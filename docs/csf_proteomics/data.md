# Data Documentation

All data files are in `data/`. Raw per-sample NPX values were downloaded from Synapse (PRIDE_DLB study).

## Discovery Cohort

**File:** `DataSet_PRIDE_DLBstudy.csv`

- 534 samples × 675 columns
- Column 1 (unnamed): sample ID (used as row index)
- Columns 2–10: clinical metadata
- Columns 11–674: 664 protein NPX values (Olink PEA log2-normalised)
- Column 675: `filter_.` — R artifact, always value `2`, **must be dropped**

| Label | N |
|---|---|
| DLB | 109 |
| AD | 235 |
| CN | 190 |

**Metadata columns:** `Dx_group`, `Age`, `Sex`, `CSFAD_profile`, `Park_med`, `CSF_Abeta42`, `CSF_tTau`, `CSF_pTau181`, `CSF_tTau_Abeta_ratio`

## Validation Cohorts

All validation files share 6 of the 7 panel proteins (`FCER2` is absent).

| File | Samples | Labels |
|---|---|---|
| `_clinical_validation1.csv` | 164 | Control / DLB / AD |
| `_clinical_validation2.csv` | 165 | Control / DLB / AD |
| `_autopsy.csv` | 76 | Control / DLB / AD |

**Note:** `Control` in validation cohorts = `CN` in discovery. Harmonised on load.

**Protein columns (6):** `MMP10`, `CRH`, `MMP3`, `ABL1`, `DDC`, `THOP1`

## Olink NPX Values

NPX (Normalized Protein eXpression) is Olink's proprietary unit:
- log2-like scale relative to a reference sample
- Typical range: 1–12
- Values below the LOD (Limit of Detection) are reported as NaN
- LOD filter: retain proteins detected in ≥85% of samples (665 → 664 proteins)

## R Reference Scripts

Both R scripts are in `data/` for algorithmic reference only:
- `Classification modeling_ecpc.R` — ECPC Bayesian ridge + post-hoc elastic net selection (2399 lines)
- `Data_Analysis_internal validations.R` — caret repeated CV with glmnet (172 lines)
