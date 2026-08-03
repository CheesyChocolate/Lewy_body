# del Campo et al. 2023 — DLB CSF Proteomics

**Source:** Synapse public repository  
**Accession:** https://www.synapse.org/PRIDE_DLB  
**Paper:** del Campo et al. (2023). "CSF proteome profiling reveals biomarkers to discriminate dementia with Lewy bodies from Alzheimer's disease." *Nature Communications* 14, 5635. https://doi.org/10.1038/s41467-023-41122-y

## Data type

Tabular (CSV). Each row is one participant. Columns are: sample ID, clinical metadata, then 664 protein NPX values (Olink Proximity Extension Assay, Explore panel). NPX is a log2-normalised relative abundance unit; values below the limit of detection are NaN.

## Files

| File | Cohort | n | Groups | Notes |
|---|---|---|---|---|
| `DataSet_PRIDE_DLBstudy.csv` | Discovery | 534 | DLB (109), AD (235), CN (190) | Primary cohort; source of the 7-protein panel. 664 proteins after LOD filter. |
| `DataSet_PRIDE_DLBstudy_clinical_validation1.csv` | Clinical validation 1 | 164 | DLB (54), AD (55), CN (55) | Amsterdam Dementia Cohort (ADC). |
| `DataSet_PRIDE_DLBstudy_clinical_validation2.csv` | Clinical validation 2 | 165 | DLB (55), AD (55), CN (55) | Sant Pau Initiative on Neurodegeneration (SPIN), Barcelona. |
| `DataSet_PRIDE_DLBstudy_autopsy.csv` | Autopsy validation | 76 | aDLB (17), aAD (30), CN (29) | Neuropathologically confirmed; BIODEM/UAntwerp. |

**Label note:** validation cohorts use `Control` for cognitively normal; the pipeline harmonises this to `CN` on load.  
**FCER2 note:** FCER2 is absent from all validation cohorts. External validation uses the 6-protein subset only.  
**`filter_.` column:** final column in every file, always value `2`; R artifact, dropped on load.

## R analysis scripts (original)

| File | Purpose |
|---|---|
| `Classification modeling_ecpc.R` | Original ECPC classification modelling (Bayesian group-regularised ridge) |
| `Data_Analysis_internal validations.R` | Internal validation analyses from the paper |

These are the authors' original R scripts, included for reference. The Python reimplementation in `src/lewy/` replaces ECPC with elastic net logistic regression.
