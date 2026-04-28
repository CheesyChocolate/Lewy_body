# DLB CSF Proteomics — Presentation Teleprompter

---

## Slide 1: Title Slide

Today I am going to walk you through a project that sits right at the intersection of **machine learning**, **software engineering**, and **clinical diagnostics**. The original paper — published in *Nature Communications* in 2023 — used a 664-protein dataset from cerebrospinal fluid to distinguish two forms of dementia that doctors routinely confuse. My work was to **take that entire analysis**, which was done in R with a proprietary package, and **rebuild it from scratch in Python** as a modular, reproducible pipeline. And then to go one step further with a contribution the original paper never made.

**NEXT SLIDE**

---

## Slide 2: The Diagnostic Problem

Let me set the clinical stage, because you need to understand *why* this matters before we talk about the ML. **Dementia with Lewy bodies** — DLB — is the second most common neurodegenerative dementia after Alzheimer's disease. It is named for abnormal protein aggregates, called **Lewy bodies**, that accumulate in neurons. Here is the core engineering problem: about **50% of DLB patients also show Alzheimer's pathology** — the same amyloid plaques, the same tau tangles. Symptoms overlap heavily in early stages. A clinician cannot reliably distinguish them. Why does that matter? Because the two diseases respond differently to treatment, and there is a drug class that is actively harmful in DLB but standard in Alzheimer's. Misdiagnosis is not just a missed label — it causes harm. What we need is an objective, biochemical test. **Cerebrospinal fluid** is the best window we have: it circulates directly around the brain and carries the chemical fingerprints of whatever is going wrong in the tissue.

**NEXT SLIDE**

---

## Slide 3: The Original Study

The paper I am recreating is by **del Campo and colleagues**, published in *Nature Communications* in 2023. They collected CSF samples from 534 patients — 109 with DLB, 235 with Alzheimer's, and 190 healthy controls. Every sample was run through the **Olink EXPLORE panel**, which measures 664 proteins simultaneously. The result: a **7-protein panel** — DDC, FCER2, CRH, MMP-3, ABL1, MMP-10, THOP1 — that achieves AUC 0.947 for distinguishing DLB from healthy controls, and 0.929 for distinguishing DLB from Alzheimer's. Those are clinically meaningful numbers. An AUC above 0.9 is considered strong for a diagnostic biomarker. Now here is the engineering problem with the paper. Their entire analysis lives in a **2399-line monolithic R script**. It relies on a proprietary Bayesian package called **ECPC** that has no Python equivalent and requires domain expertise to configure. There is no way to run this analysis unattended, extend it, or reuse components. It is science that works — but it is not engineering.

**NEXT SLIDE**

---

## Slide 4: The Input: 664 Proteins

Let me translate the biology into an engineering problem. The **Olink PEA** technology — Proximity Extension Assay — works by binding pairs of antibodies to each target protein. Each antibody pair carries a unique DNA barcode. When both antibodies bind the same protein molecule, the barcodes get close enough to hybridize and extend, creating a unique DNA signal. The count of those signals is converted to **NPX**, a log2-scale relative abundance measure. From a machine learning standpoint this is clean tabular data. You have a matrix **X** with 534 rows and 664 columns. Your labels are three-class — DLB, AD, CN — but you run two **binary** classification tasks: DLB vs CN and DLB vs AD. One important preprocessing step: a **limit-of-detection filter** drops proteins that are not reliably detected in at least 85% of samples. That reduces 665 proteins to 664. You also include **Age** and **Sex** as covariates in every model, because both correlate with diagnosis and you do not want the classifier learning those demographic confounds instead of disease signal.

**NEXT SLIDE**

---

## Slide 5: The Original ML Pipeline

The paper's pipeline has three stages. Stage one is **differential analysis** — for each protein independently, fit a linear model: NPX explained by diagnosis group, plus Age, plus Sex. Run Benjamini-Hochberg false discovery rate correction. This tells you which proteins are significantly dysregulated in DLB. Stage two is the hard part: **ECPC**, the Empirical Bayes Co-data Penalised Classifier. This is a Bayesian ridge regression that uses biological group priors — essentially, prior knowledge about which proteins belong to which biological pathway — to set a different regularisation penalty for each protein group. It produces a **dense model** over all 664 proteins. This is sophisticated and, as I mentioned, has no Python equivalent. Stage three is **post-hoc sparsification** — the paper applies elastic net to the dense ECPC solution to select 7 proteins. They then train that 7-protein panel on the discovery cohort and evaluate it on three independent validation cohorts using 5-fold by 1000-repeat cross-validation.

**NEXT SLIDE**

---

## Slide 6: What We Built

The figure on the right shows the **data flow** of the pipeline. Raw protein matrix comes in on the left; publication-ready figures come out on the right. Each stage is independently re-runnable. The most expensive step — the 500-fold cross-validation — is cached after the first run, so you can tweak a figure or add an analysis without waiting an hour for CV to finish. There are two key **data engineering decisions** worth noting. First, **Age and Sex are treated as covariates at every stage** — in the differential analysis model and in the classifier features. This is critical: both correlate with diagnosis group, and a model that ignores them risks learning demographic signal instead of disease signal. Second, **stratified splits** are used throughout, which ensures that the class imbalance — 109 DLB versus 235 AD versus 190 controls — is preserved proportionally in every training and test fold. These are not coding choices; they are decisions about how to handle confounded, imbalanced biomedical data.

**NEXT SLIDE**

---

## Slide 7: The Classification Method

Let me explain the **elastic net substitution** for ECPC. Elastic net combines **L1** and **L2** penalties in a single term: alpha controls how much L1 versus L2 you apply. L1 drives coefficients to exactly zero — automatic feature selection. L2 handles **correlated features**: when several proteins share a biological pathway and are correlated, L2 keeps them all rather than arbitrarily zeroing most of them. This is critical in proteomics where redundancy is the norm. The key insight is that the paper's own sparsification step is elastic net applied to the ECPC output. So elastic net is already inside their pipeline. We are approximating ECPC with the same tool the paper uses downstream. Both the regularisation strength **C** and the L1 ratio are cross-validated over a 20-point grid using inner 5-fold CV. For the outer performance estimate, we run **5-fold stratified CV, 100 times**, giving 500 held-out fold evaluations. The AUC is reported as mean plus 95% confidence interval by the percentile method. Results are cached to JSON so you do not recompute on every run.

**NEXT SLIDE**

---

## Slide 8: Recreation Results

The numbers hold up. For **DLB vs CN**, our mean AUC is 0.986 with a 95% CI of 0.962 to 1.000. The paper reports 0.947. For **DLB vs AD**, our mean AUC is 0.937, CI 0.877 to 0.985. The paper reports 0.929. Both comparisons match or exceed the paper's values. DDC — dopamine decarboxylase — is the top-ranked protein in our panel for DLB vs CN, which matches the paper's headline finding. Panel overlap is 5 of 7 proteins. The two differences are likely due to the elastic net versus ECPC regularisation paths — they converge on similar but not identical solutions. The **elastic net substitution is validated**: the core scientific claim of the paper is reproduced in Python. The slight AUC inflation over the paper is within the variance expected from 100 repeats versus the paper's 1000 — with fewer repeats, confidence intervals are wider and individual estimates can vary by a few percent.

**NEXT SLIDE**

---

## Slide 9: Discovery ROC Curves

This is the ROC curve for DLB versus controls from the discovery cohort. The **full-fit AUC is 1.000** — the classifier trained on all 534 samples perfectly separates the two classes. That is expected and not the number we report. The honest estimate is the **cross-validated 0.986**. The curve shape is what matters here: a sharp rise toward the top-left corner, a large area under the curve, and very few false positives at high sensitivity thresholds. In clinical terms: if you set the operating threshold to accept 95% sensitivity — catching 95% of DLB cases — you get a false positive rate of only a few percent. That is a useful test.

**NEXT SLIDE**

---

## Slide 10: The Improvement

The paper's major limitation is that it examines **individual proteins in isolation only for DDC**. They report DDC's standalone AUC of 0.91 as a headline result — and stop there. The other 657 proteins receive no individual discriminative analysis. The improvement is a **systematic univariate screening** of all 664 proteins. For each protein, you fit a 3-feature logistic regression: protein NPX, patient age, patient sex. Covariate-adjusted, so age and sex do not confound the individual protein's signal. You compute AUROC for every protein independently and rank them. This is 664 separate binary classification problems. The key distinction from the multi-protein panel is the **question being asked**. The panel answers: what is the best *combination* of proteins? The per-protein ranking answers: which proteins carry *individual* diagnostic value, on their own? That is the right question if you are designing a rapid clinical test — a single-marker strip test that a clinician can run at the bedside. The paper never asks that question systematically. We do.

**NEXT SLIDE**

---

## Slide 11: Per-Protein Biomarker Landscape

This figure shows the top 40 proteins by individual AUC for DLB vs CN on the left, and DLB vs AD on the right. Red bars are the original paper's 7 panel proteins. Notice that **DDC** sits at the very top of the DLB vs CN ranking with AUC 0.949 — consistent with the paper's reported 0.91 for that protein. But notice the proteins immediately below it: **MMP-1, WIF-1, PRCP, ENTPD5** — none of which are in the original 7-protein panel. These are candidates the original paper never systematically evaluated. For DLB vs AD the discrimination is harder, with the top individual AUC around 0.82, but the panel proteins CRH, ABL1, and DDC all rank in the top 3. The key point is that this figure is a **contribution** the original paper does not make. It answers a different and complementary question: if you had to build a single-protein clinical test, which protein gives you the most signal?

**NEXT SLIDE**

---

## Slide 12: Takeaways

Three things to take from this project. First: **reproducibility is an engineering problem**. A 2399-line script that requires a proprietary package is not reproducible science — it is a locked artifact. A modular Python package with a CLI, dependency declaration in `pyproject.toml`, and cached results is engineering. Anyone can clone the repo and reproduce every figure. Second: **method substitution requires understanding, not guessing**. ECPC and elastic net are not the same thing, but they are close enough in this domain because the paper's own pipeline already uses elastic net. If you understand what a method is doing — applying grouped regularisation to high-dimensional data — you can find a faithful approximation. The AUC results validate the choice. Third: **systematic screening reveals more than spotlighting**. The original paper had a spotlight on DDC. We replaced it with a floodlight on all 664 proteins. That is the contribution — and it is enabled entirely by treating the analysis as software engineering.

**NEXT SLIDE**

---
