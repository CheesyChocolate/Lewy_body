# Results

*This file is populated after running the pipeline. See `results/metrics/` for raw JSON.*

## Discovery Cohort

Run `uv run python src/pipeline.py` to generate results.

Expected (from paper):

| Comparison | AUC | 95% CI |
|---|---|---|
| DLB vs CN | 0.947 | — |
| DLB vs AD | 0.929 | — |

## Identified Panel

Expected proteins (paper): DDC, FCER2, CRH, MMP-3, ABL1, MMP-10, THOP1

## Validation Cohorts

| Cohort | DLB vs CN AUC | DLB vs AD AUC |
|---|---|---|
| Clinical validation 1 | ~0.95 | ~0.86 |
| Clinical validation 2 | ~0.93 | ~0.88 |
| Autopsy | ~0.92 | ~0.90 |

## Figures

After pipeline run, all figures are in `results/figures/`:
- `volcano_DLB_vs_CN.png` — differential proteins DLB vs CN
- `volcano_DLB_vs_AD.png` — differential proteins DLB vs AD
- `roc_DLB_vs_CN.png` — ROC curve on discovery
- `roc_DLB_vs_AD.png` — ROC curve on discovery
- `violin_panel_proteins.png` — protein abundance by diagnosis
- `forest_Validation_cohort_AUCs.png` — summary forest plot
