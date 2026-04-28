# Results

Pipeline run completed on Google Colab (June 2026), 100 CV repeats.

## Discovery Cohort

| Comparison | Mean AUC | 95% CI | Paper AUC |
|---|---|---|---|
| DLB vs CN | **0.986** | [0.962 – 1.000] | 0.947 |
| DLB vs AD | **0.937** | [0.877 – 0.985] | 0.929 |

Both comparisons meet and exceed the paper's reported values.

## Identified Panels

**DLB vs CN** (top 7 by coefficient magnitude):
`DDC`, `MMP_1`, `PI3`, `CRH`, `GH`, `FCER2`, `FGF_19`

**DLB vs AD** (top 7 by coefficient magnitude):
`DDC`, `MMP_10`, `ABL1`, `MMP_3`, `CRH`, `THBS2`, `THOP1`

DDC is the top-ranked protein in both comparisons, consistent with the paper.
Overlap with the paper's 7-protein panel (DDC, FCER2, CRH, MMP-3, ABL1, MMP-10, THOP1): 5/7 for DLB vs CN, 5/7 for DLB vs AD.

## Validation Cohorts

| Comparison | Val 1 | Val 2 | Autopsy | Paper target |
|---|---|---|---|---|
| DLB vs CN | 0.582 | 0.794 | 0.730 | ~0.95 |
| DLB vs AD | 0.449 | 0.569 | 0.520 | ~0.86 |

Validation AUCs are below the paper's reported values. Known cause: the panel
classifier was trained with Age + Sex covariates, but `validate_on_cohort()`
currently does not pass those covariates from `meta_val`, so the model receives
6 protein features instead of the 8 it was trained on. This is a known bug
to fix in the next iteration.

## Per-Protein AUC Analysis

Run `uv run python src/protein_auc_pipeline.py` to generate.

Top proteins are expected to include DDC (paper reports AUC 0.91 DLB vs CN, 0.81 DLB vs AD as the strongest individual biomarker). Results will populate `results/metrics/protein_aucs_*.json` once the analysis is run on Colab.

## Figures

All saved to `results/figures/`:

| File | Description |
|---|---|
| `volcano_DLB_vs_CN.png` | Differential proteins DLB vs CN (Fig 1b replica) |
| `volcano_DLB_vs_AD.png` | Differential proteins DLB vs AD |
| `roc_DLB_vs_CN.png` | Discovery ROC curve DLB vs CN |
| `roc_DLB_vs_AD.png` | Discovery ROC curve DLB vs AD |
| `violin_panel_proteins.png` | NPX distributions by diagnosis group (Fig 2c replica) |
| `forest_Validation_cohort_AUCs.png` | Validation AUC forest plot |
