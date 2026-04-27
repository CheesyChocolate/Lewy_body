# Knowledge Base — DLB CSF Proteomics Project

Running notes on concepts, data quirks, and decisions made during implementation.

---

## Disease Background

### Dementia with Lewy Bodies (DLB)
- Second most common neurodegenerative dementia after AD
- Core pathology: alpha-synuclein aggregates (Lewy bodies) in cortical neurons
- Clinically overlaps heavily with AD: shared amyloid/tau pathology in ~50% of DLB cases
- Diagnosis is challenging ante-mortem; biomarker-based discrimination is the clinical need

### AD-DLB overlap
- ~50% of DLB patients have co-occurring AD pathology (`CSFAD_profile` column in data)
- CSF AD profile defined by Aβ42, t-Tau, p-Tau181 ratios (Alzheimer's association criteria)

---

## Proteomics Platform

### Olink PEA (Proximity Extension Assay)
- Antibody-based multiplex proteomics: pairs of antibodies with DNA-barcoded oligos
- When both antibodies bind target protein, the oligos hybridise and extend → qPCR quantification
- 665 proteins measured on the EXPLORE panel; 664 passed the LOD filter (85% detection threshold)
- Output: **NPX (Normalized Protein eXpression)** — log2-like relative abundance, typically 1–12
- Values below LOD are reported as NaN (not zero)

### LOD Filter
- Proteins must be detected (above LOD) in ≥85% of samples to be retained
- Applied in `features.filter_by_lod()`: 665 → 664 proteins

---

## Statistical Methods

### Differential Analysis (Nested Linear Model)
- Model per protein: `NPX ~ Dx_group + Age + Sex`
- OLS with two-sample comparison (one group coded 0, other 1)
- Multiple testing correction: Benjamini-Hochberg FDR
- Significance threshold: q < 0.05
- Implemented in `features.differential_proteins()`

### ECPC (Empirical Bayes Co-data Penalised Classification)
- Original R method by Zhu et al., implemented as custom R library
- Bayesian group-regularised ridge regression
- Uses biological co-data (protein groups/pathways) as priors to shrink coefficients
- Key difference from standard ridge: per-group rather than global regularisation strength
- **No Python equivalent exists** → replaced by scikit-learn elastic net

### Elastic Net Logistic Regression
- Combines L1 (lasso, promotes sparsity) + L2 (ridge, handles correlated features) penalties
- `penalty = α * L1 + (1-α) * L2` where α is `l1_ratio`
- `l1_ratio=0` → pure ridge; `l1_ratio=1` → pure lasso
- Paper uses this in the `postHocSelect()` step to sparsify the ECPC dense solution
- Python: `LogisticRegressionCV(penalty='elasticnet', solver='saga')`
- `C` parameter is 1/λ (inverse regularisation); cross-validated

### Repeated Stratified K-Fold CV
- 5-fold CV × 1000 repeats → 5000 per-fold AUROCs
- Distribution gives stable estimate and 95% CI by percentile method
- Computationally expensive: default set to 100 repeats (`--full` for 1000)
- Results cached to JSON to avoid recomputation

---

## Key Proteins

### DDC (DOPA decarboxylase, gene: DDC)
- Enzyme in dopamine/serotonin biosynthesis (L-DOPA → dopamine)
- Strongest individual discriminator in the study
- AUC 0.91 (DLB vs CN), 0.81 (DLB vs AD) when used alone
- Elevated in DLB CSF; reflects dopaminergic neuronal loss

### 7-Protein Panel
| Protein | Full name | Direction in DLB |
|---|---|---|
| DDC | DOPA decarboxylase | ↑ |
| FCER2 | Fc epsilon receptor II | — |
| CRH | Corticotropin-releasing hormone | — |
| MMP3 | Matrix metalloproteinase-3 | — |
| ABL1 | ABL proto-oncogene 1 | — |
| MMP10 | Matrix metalloproteinase-10 | — |
| THOP1 | Thimet oligopeptidase 1 | — |

Note: FCER2 is absent from validation cohorts → only 6 proteins used in external validation.

---

## Data Quirks

### `filter_.` column
- Final column in discovery CSV, always value `2`
- Artifact from R's `dplyr::filter()` when used with `keep = TRUE` flag
- Carries zero information, must be dropped on load

### Label mismatch
- Discovery cohort: `CN` (cognitively normal)
- Validation cohorts: `Control` (same population, different label)
- Harmonised in `data._harmonise_labels()`: `Control` → `CN`

### FCER2 absence
- Validation cohorts were collected/assayed independently, FCER2 not included
- Panel reduced to 6 proteins for all external validation
- Handled by `validate_on_cohort()` using only shared features

---

## Implementation Decisions

| Decision | Rationale |
|---|---|
| Elastic net instead of ECPC | ECPC has no Python equivalent; elastic net is what paper uses for panel selection |
| Age + Sex as covariates in classifier | Per paper methods: classification model includes demographics |
| 100 repeats default (not 1000) | Computation time; `--full` flag for paper-faithful run |
| JSON caching for CV results | Avoid rerunning hours of CV on re-execution |
| `l1_ratios=[0,0.1,0.5,0.9,1.0]` | Sweep from ridge to lasso; paper's ECPC is ridge-dominant |

---

## References

- del Campo et al. (2023). "CSF proteome profiling reveals biomarkers to discriminate dementia with Lewy bodies from Alzheimer's disease." *Nature Communications* 14, 5635. https://doi.org/10.1038/s41467-023-41122-y
- Olink Proteomics EXPLORE panel: https://olink.com/products-services/explore/
- ECPC R package: Zhu et al. — implemented in `data/Classification modeling_ecpc.R`
- scikit-learn LogisticRegressionCV: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegressionCV.html
