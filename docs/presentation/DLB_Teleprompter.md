# DLB CSF Proteomics — Presentation Teleprompter

---

## Slide 1: Title Slide

Today I am going to talk about a project that combines **machine learning**, **software engineering**, and **clinical diagnostics**. The original paper used a 664-protein dataset from cerebrospinal fluid to distinguish two forms of dementia that doctors routinely confuse. My work was to **take that entire analysis**, which was done in R with a proprietary package, and **rebuild it from scratch in Python** as reproducible pipeline. And then to go one step further with a contribution, the original paper never made.

**NEXT SLIDE**

---

## Slide 2: The Diagnostic Problem

Let me set the clinical stage, because you need to understand *why* this matters before we talk about the ML. **Dementia with Lewy bodies** — DLB — is the second most common neurodegenerative dementia after Alzheimer's disease. Here is the core engineering problem: about **50% of DLB patients also show Alzheimer's pathology**. Symptoms overlap heavily in early stages. A clinician cannot reliably distinguish them. Why does that matter? Because the two diseases respond differently to treatment, and there is a drug class that is actively harmful in DLB but standard in Alzheimer's. **Cerebrospinal fluid** is the best window we have: chemical fingerprints of whatever is going wrong in the tissue.

**NEXT SLIDE**

---

## Slide 3: The Original Study

The paper I am recreating is by **del Campo and colleagues**, published in *Nature Communications* in 2023. They collected CSF samples from 534 patients — 109 with DLB, 235 with Alzheimer's, and 190 healthy controls. Every sample was run through the **Olink EXPLORE panel**, which measures 664 proteins simultaneously. The result: a **7-protein panel** that achieves AUC 0.947 for distinguishing DLB from healthy controls, and 0.929 for distinguishing DLB from Alzheimer's.

**NEXT SLIDE**

---

## Slide 4: The Input: 664 Proteins

Let me translate the biology into an engineering problem. The **Olink PEA** technology works by creating a unique DNA signal. The count of those signals is converted to **NPX**. From a machine learning standpoint this is clean tabular data. You have a matrix **X** with 534 rows and 664 columns. Your labels are three-class — DLB, AD, CN — but you run two **binary** classification tasks: DLB vs CN and DLB vs AD. One important preprocessing step: a **limit-of-detection filter** drops proteins that are not reliably detected in at least 85% of samples. That reduces 665 proteins to 664. You also include **Age** and **Sex** as covariates in every model, because both correlate with diagnosis and you do not want the classifier learning those demographic confounds instead of disease signal.

**NEXT SLIDE**

---

## Slide 5: The Original ML Pipeline

The paper's pipeline has three stages. Stage one is **differential analysis** — for each protein independently, fit a linear model: NPX explained by diagnosis group, plus Age, plus Sex. Run Benjamini-Hochberg false discovery rate correction. This tells you which proteins are not regulated properly in DLB. Stage two is the hard part: **ECPC**, the Empirical Bayes Co-data Penalised Classifier. This is a Bayesian ridge regression that uses biological group priors — (essentially, prior knowledge about which proteins belong to which biological pathway) — to set a different regularisation penalty for each protein group. It produces a **dense model** over all 664 proteins. Stage three is **post-hoc sparsification** — the paper applies elastic net to the dense ECPC solution to select 7 proteins. They then train that 7-protein panel on the discovery cohort and evaluate it on three independent validation cohorts using 5-fold by 1000-repeat cross-validation.

**NEXT SLIDE**

---

## Slide 6: What We Built

The figure on the right shows the **data flow** of the pipeline. There are two key **data engineering decisions** worth noting. First, **Age and Sex are treated as covariates at every stage** — (in the differential analysis model and in the classifier features). We want to ignore them so not risks learning demographic signal instead of disease signal. Second, **stratified splits** are used throughout, which ensures that the class imbalance — 109 DLB versus 235 AD versus 190 controls — is preserved proportionally in every training and test fold.

**NEXT SLIDE**

---

## Slide 7: The Classification Method

Let me explain the **elastic net substitution** for ECPC. Elastic net combines **L1** and **L2** penalties in a single term: alpha controls how much L1 versus L2 you apply. (L1 drives coefficients to exactly zero — automatic feature selection. L2 handles **correlated features**: when several proteins share a biological pathway and are correlated, L2 keeps them all rather than arbitrarily zeroing most of them.) This is critical in proteomics where redundancy is the norm. The key insight is that the paper's own sparsification step is elastic net applied to the ECPC output. We are approximating ECPC with the same tool the paper uses downstream. For the outer performance estimate, we run **5-fold stratified CV, 100 times**, giving 500 held-out fold evaluations. The AUC is reported as mean plus 95% confidence interval by the percentile method.

**NEXT SLIDE**

---

## Slide 8: Recreation Results

The numbers hold up. For **DLB vs CN**, our mean AUC is 0.986 with a 95% CI of 0.962 to 1.000. The paper reports 0.947. For **DLB vs AD**, our mean AUC is 0.937, CI 0.877 to 0.985. The paper reports 0.929. Both comparisons match or exceed the paper's values. DDC is the top-ranked protein in our panel for DLB vs CN, which matches the paper's headline finding. Panel overlap is 5 of 7 proteins. The two differences are likely due to the elastic net versus ECPC regularisation paths.

**NEXT SLIDE**

---

## Slide 9: Discovery ROC Curves

This is the ROC curve for DLB versus controls from the discovery cohort. The **full-fit AUC is 1.000** — (the classifier trained on all 534 samples perfectly separates the two classes). That is expected and not the number we report. The honest estimate is the **cross-validated 0.986**. The curve shape is what matters here: a sharp rise toward the top-left corner, a large area under the curve, and very few false positives at high sensitivity thresholds. In clinical terms: if you set the operating threshold to accept 95% sensitivity — catching 95% of DLB cases — you get a false positive rate of only a few percent. That is a useful test.

**NEXT SLIDE**

---

## Slide 10: The Improvement

The paper's major limitation is that it examines **individual proteins in isolation only for DDC**. They report DDC's standalone AUC of 0.91 as a headline result. The other 657 proteins receive no individual discriminative analysis. The improvement is a **systematic univariate screening** of all 664 proteins. For each protein, you fit a 3-feature logistic regression: protein NPX, patient age, patient sex. Covariate-adjusted, so age and sex do not confound the individual protein's signal. You compute AUROC for every protein independently and rank them. This is 664 separate binary classification problems. The panel answers: what is the best *combination* of proteins? The per-protein ranking answers: which proteins carry *individual* diagnostic value, on their own? That is the right question if you are designing a rapid clinical test — a single-marker strip test that a clinician can run at the bedside. The paper never asks that question systematically. We do.

**NEXT SLIDE**

---

## Slide 11: Per-Protein Biomarker Landscape

This figure shows the top 40 proteins by individual AUC for DLB vs CN on the left, and DLB vs AD on the right. Red bars are the original paper's 7 panel proteins. Notice that **DDC** sits at the very top of the DLB vs CN ranking with AUC 0.949 — consistent with the paper's reported 0.91 for that protein. But notice the proteins immediately below it: **MMP-1, WIF-1, PRCP, ENTPD5** — none of which are in the original 7-protein panel. These are candidates the original paper never systematically evaluated. For DLB vs AD the discrimination is harder, with the top individual AUC around 0.82, but the panel proteins CRH, ABL1, and DDC all rank in the top 3. The key point is that this figure is a **contribution** the original paper does not make. It answers a different and complementary question: if you had to build a single-protein clinical test, which protein gives you the most signal?

**NEXT SLIDE**

---

## Slide 12: Takeaways

First: Anyone can clone the repo and reproduce every figure. Second: **method substitution requires understanding, not guessing**. ECPC and elastic net are not the same thing, but they are close enough in this domain because the paper's own pipeline already uses elastic net. so the idea was if you understand what a method is doing — (applying grouped regularisation to high-dimensional data) — you can find a faithful approximation. The AUC results validate the choice. Third: **systematic screening reveals more than spotlighting**. The original paper had a spotlight on DDC. We replaced it with a floodlight on all 664 proteins. That is the contribution.

**NEXT SLIDE**

---


# Q&A — DLB CSF Proteomics Presentation

---

## Likely Audience Questions

**Q1: Your AUC is higher than the paper's — doesn't that mean you overfit?**

The cross-validated AUC of 0.986 comes from 500 held-out fold evaluations (5-fold × 100 repeats). Those test samples were never seen by the classifier during training in any of those folds. So the number reflects genuine out-of-sample performance, not training-set memorisation. The full-fit AUC on all 534 samples is 1.000 — that *is* overfit, and it is the number we never report as the performance estimate. The slight inflation over the paper's 0.947 is within the variance expected from 100 repeats rather than 1000: with fewer repeats the confidence interval is wider and individual runs vary by a few percent. If anything, more repeats would reduce variance and likely bring the estimate closer to the paper's number, not further from it.

---

**Q2: What does AUC actually mean?**

AUC stands for Area Under the Receiver Operating Characteristic Curve. Concretely, it is the probability that the model ranks a randomly chosen DLB patient higher than a randomly chosen control patient. An AUC of 0.5 means the model does no better than random guessing — it is equivalent to flipping a coin. An AUC of 1.0 means the model perfectly separates every DLB case from every control. The standard clinical benchmark is 0.8 — above that, a test is generally considered useful for diagnostic support. Our AUC of 0.986 means that in 98.6% of random DLB-vs-control pairs, the model correctly assigns the higher probability to the DLB patient.

---

## Smart Questions

**Q3: Age and Sex are features in the classifier — does that mean the model can't generalise to cohorts where that metadata isn't available?**

Yes, that is a real limitation. The model is trained on an 8-feature input: 6 proteins plus Age plus Sex. If you deploy it on a cohort without demographic metadata, the model receives a different feature space and its calibration breaks down. The reason we include Age and Sex despite this is that both correlate with diagnosis — older patients and female patients are disproportionately represented in certain diagnosis groups. A model trained without these covariates risks learning the demographic signal instead of the disease signal, which produces an artificially inflated AUC that will not generalise. The paper makes the same trade-off for the same reason. A production deployment would need explicit handling of missing covariates.

---

**Q4: In the per-protein analysis, each protein is modelled independently — doesn't that ignore correlations between proteins and risk flagging redundant candidates?**

Intentionally so. The per-protein analysis and the multi-protein elastic net classifier are answering different questions and they are designed to be complementary, not competing. The elastic net panel (Phase 3) explicitly handles protein correlations through the L2 penalty — it selects a small set of proteins that together provide discriminative power without redundancy. The per-protein analysis asks a different question: which individual proteins carry sufficient discriminative signal to be useful *on their own*? That is the clinically relevant question for a single-marker test — for example, a rapid CSF strip test that measures only one protein. A protein that ranks high individually but is correlated with another panel protein is not wasted information; it is a candidate for a simpler, cheaper assay. The two analyses are complementary: the panel tells you the best *combination*, the per-protein ranking tells you the best *individual*.
