# DLB CSF Proteomics — Project Overview

## Goal

Python reimplementation of del Campo et al. (2023, *Nature Communications*):
"CSF proteome profiling reveals biomarkers to discriminate dementia with Lewy bodies from Alzheimer's disease."

The original analysis was performed in R (interactive, monolithic scripts). This project recreates the core results in a modular, unattended Python pipeline.

## Target Results

| Comparison | Paper AUC | Method |
|---|---|---|
| DLB vs CN (discovery) | 0.947 | Elastic net (all 664 proteins) |
| DLB vs AD (discovery) | 0.929 | Elastic net (all 664 proteins) |
| DLB vs CN (validation 1) | ~0.95 | 6-protein panel |
| DLB vs AD (validation 1) | ~0.86 | 6-protein panel |

## 7-Protein Panel

DDC · FCER2 · CRH · MMP-3 · ABL1 · MMP-10 · THOP1

DDC (DOPA decarboxylase) is the strongest individual discriminator (AUC 0.91 DLB vs CN, 0.81 DLB vs AD).

## Pipeline Modules

| Module | Purpose |
|---|---|
| `src/lewy/data.py` | Load and preprocess all 4 datasets |
| `src/lewy/features.py` | Differential analysis, LOD filtering |
| `src/lewy/model.py` | Elastic net classifier, repeated CV |
| `src/lewy/evaluate.py` | AUROC, ROC curves, validation |
| `src/lewy/plots.py` | All publication figures |
| `src/pipeline.py` | CLI entrypoint |

## Running

```bash
uv run python src/pipeline.py                  # 100 CV repeats (fast)
uv run python src/pipeline.py --full           # 1000 repeats (paper-faithful)
uv run python src/pipeline.py --output-dir out # custom output directory
```
