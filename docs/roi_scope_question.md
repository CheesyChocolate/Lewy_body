# ROI scope question (for advisor review)

**Status (2026-09-03): not blocking anything.** The current FDG-PET radiomics pipeline is
mid-batch-extraction on the ROI set below; this is a question about scope for a possible
follow-up analysis, not something the current run depends on.

## Question

The current pipeline extracts pyradiomics features from only 13 cortical ROI pairs (26
labels) chosen specifically for the DLB cingulate island sign (posterior cingulate,
precuneus, lateral/inferior/superior parietal, supramarginal, postcentral, paracentral,
lingual, pericalcarine, cuneus, and the anterior cingulate variants). Should the primary
classifier also include features from other FastSurfer-segmented regions plausibly
relevant to DLB, or is the tight cingulate-island-sign scope the right call for the
primary analysis?

Specifically, the segmentation already computes (and currently discards) labels for:

- Hippocampus, amygdala -- candidates for AD-comorbidity differentiation, since DLB/AD
  overlap is a known confound in this cohort's SAA-positive population (see
  `docs/saa_positive_not_dlb_diagnosis.md` -- SAA+ is a synucleinopathy proxy covering
  DLB/PD/iRBD/MSA/incidental Lewy, not a DLB-specific label).
- Thalamus, putamen, caudate, pallidum -- subcortical structures with known Lewy
  pathology involvement.
- The rest of the DKT cortical parcellation outside the 13 chosen regions, and other
  aseg structures (ventricles, other white matter, corpus callosum, etc.).

## Why we're asking

This project's own scope note (`CLAUDE.md` / `docs/advisor_notes/4.md`) frames FDG-PET
radiomics of the cingulate island sign as the *primary* classification target, with
structural MRI and CSF/blood markers as supporting/validation modalities rather than
independent classification targets -- which argues for keeping the ROI set narrow and
sign-specific. But the segmentation step (FastSurfer, whole-brain) already produces all of
these other labels at no extra compute cost; only the pyradiomics feature-extraction step
would need to expand to use them.

The tradeoff we see: adding ROIs is "free" on the segmentation side, but each added ROI
pair adds roughly another ~850 pyradiomics feature columns (13 ROIs currently produce
11,063 features total), which worsens an already tight features-to-samples ratio for the
nested-CV classifier at this cohort size (~541 subjects, 126 SAA-positive). Feature
selection is already planned to run inside each CV fold (per `docs/TODO.md`'s nested-CV
plan), so more candidate features isn't necessarily wrong, but it's a real cost we'd like
guidance on before deciding whether to expand scope.

## Specifically what we need

1. Is the cingulate-island-sign-only ROI scope the right choice for the *primary*
   classifier, or should a broader region set be included from the start?
2. If broader, which additional regions are worth the added dimensionality --
   hippocampus/amygdala for AD-comorbidity control, subcortical structures for Lewy
   pathology, both, or something else?
3. Would a secondary/exploratory model with the broader ROI set (run alongside, not
   instead of, the primary cingulate-island-sign model) be a reasonable way to explore
   this without compromising the primary analysis?
