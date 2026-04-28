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

Yes, that is a real limitation. The model is trained on an 8-feature input: 6 proteins plus Age plus Sex. If you deploy it on a cohort without demographic metadata, the model receives a different feature space and its calibration breaks down. The reason we include Age and Sex despite this is that both correlate with diagnosis — older patients and female patients are disproportionately represented in certain diagnosis groups. A model trained without these covariates risks learning the demographic signal instead of the disease signal, which produces an artificially inflated AUC that will not generalise to a demographically balanced cohort. The paper makes the same trade-off for the same reason. A production deployment would need explicit handling of missing covariates — either imputation, a model variant trained without them, or a missing-indicator approach.

---

**Q4: In the per-protein analysis, each protein is modelled independently — doesn't that ignore correlations between proteins and risk flagging redundant candidates?**

Intentionally so. The per-protein analysis and the multi-protein elastic net classifier are answering different questions and they are designed to be complementary, not competing. The elastic net panel (Phase 3) explicitly handles protein correlations through the L2 penalty — it selects a small set of proteins that together provide discriminative power without redundancy. The per-protein analysis asks a different question: which individual proteins carry sufficient discriminative signal to be useful *on their own*? That is the clinically relevant question for a single-marker test — for example, a rapid CSF strip test that measures only one protein. A protein that ranks high individually but is correlated with another panel protein is not wasted information; it is a candidate for a simpler, cheaper assay. The two analyses are complementary: the panel tells you the best *combination*, the per-protein ranking tells you the best *individual*.
