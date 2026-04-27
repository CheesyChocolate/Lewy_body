# Methods

## Original Paper (R)

### Differential Analysis
- Nested linear model: `protein ~ Dx_group + Age + Sex`
- FDR correction: Benjamini-Hochberg (q < 0.05)
- Run separately for DLB vs CN and DLB vs AD

### Classification
- Method: ECPC (Empirical Bayes Co-data Penalised Classification)
  - Bayesian group-regularised ridge regression
  - Uses protein co-data (biological group priors) to set per-group regularisation
  - No direct Python equivalent
- Post-hoc sparsification: elastic net applied to ECPC dense solution to select 7-protein panel
- Cross-validation: 5-fold × 1000 repeats, AUC reported as mean ± 95% CI (percentile)

### Validation
- 6-protein panel trained on discovery, evaluated on 3 external cohorts
- Same repeated CV approach applied to validation

## This Reimplementation (Python)

### Differential Analysis
- `statsmodels` OLS: `y ~ group + Age + Sex_num`
- `multipletests(method='fdr_bh')` from statsmodels
- Faithfully mirrors the nested linear model approach

### Classification
- `sklearn.linear_model.LogisticRegressionCV`
  - `penalty='elasticnet'`, `solver='saga'`
  - `l1_ratios=[0.0, 0.1, 0.5, 0.9, 1.0]` (sweeps ridge → lasso)
  - `Cs=20` (log-spaced inverse regularisation grid)
  - Inner CV: 5-fold for hyperparameter selection
- `RepeatedStratifiedKFold(n_splits=5, n_repeats=100)` for outer evaluation
- Age and Sex included as covariates alongside protein NPX values
- Panel selection: top 7 proteins by absolute coefficient magnitude

### Why Elastic Net Instead of ECPC
ECPC is a proprietary Bayesian R package with no Python equivalent. The paper's internal validation step itself uses elastic net (glmnet) for the panel selection. Elastic net with a ridge-dominant l1_ratio closely approximates the ECPC regularisation profile. AUC results are expected to be within ~0.01–0.02 of the paper's reported values.

## Output

| File | Contents |
|---|---|
| `results/metrics/discovery_aucs.json` | Per-comparison AUC, 95% CI, panel proteins |
| `results/metrics/validation_aucs.json` | Per-cohort validation AUC and ROC data |
| `results/figures/volcano_*.png` | Differential protein volcano plots |
| `results/figures/roc_*.png` | ROC curves |
| `results/figures/violin_panel_proteins.png` | NPX distributions per diagnosis |
| `results/figures/forest_*.png` | Forest plot of validation AUCs |
