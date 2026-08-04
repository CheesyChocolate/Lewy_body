# ADNI Data Acquisition

Living record of what was pulled from ADNI (via IDA/LONI), why, and what was
deliberately left out. Update this whenever the cohort definition or data sources
change — it's the reference for "why do we have exactly this and not more/less."

Project direction: `docs/advisor_notes/4.md` (FDG-PET radiomics, primary) with sMRI and
CSF/blood synucleinopathy markers as supporting/validation modalities. Cohort-selection
strategy: `docs/advisor_notes/1.md` (SAA+ subjects with FDG-PET and MRI within one year).

## Why ADNI

ADNI is the only public, multimodal (PET + MRI + CSF/blood + genetics) longitudinal
dataset large enough to build an FDG-PET radiomics classifier, and it recently added the
Amprion CSF alpha-synuclein seed amplification assay (SAA) as a study-wide biomarker —
which is what makes it possible to identify a DLB-relevant (synucleinopathy-positive)
subset at all, since ADNI's own diagnosis field never labels subjects "DLB" (see below).

## What we got

### 1. Tabular data — `data/adni/tables/` (215 CSVs)

Source: `ADNIMERGE2`, the official ATRI Biostatistics R data package, downloaded via
ARC Builder → Study Files (`data/adni/ADNIMERGE2/`, 217 `.rda` tables), converted to CSV
with `scripts/convert_adnimerge2_to_csv.R` (2 objects skipped: a date scalar and a
`Metacore` object, neither tabular).

This is the bulk data: diagnosis (`DXSUM`), demographics (`PTDEMOG`), APOE genotype
(`APOERES`), PET/MRI QC and derived measures, CSF/plasma amyloid and tau panels (UPENN,
Fujirebio, Blennow, Roche Elecsys), FreeSurfer volumetrics (`UCSFFSX*`), and FDG-PET
regional SUVR (`UCBERKELEYFDG_8mm`). We took the whole package rather than
hand-picking tables, since it's one bundled download and most tables are small; no
selection decision was made here beyond "use the official merged package instead of
assembling raw ADNI CSVs by hand."

### 2. Biospecimen tables not in ADNIMERGE2 — `data/adni/biospecimen/`

`ADNIMERGE2`'s `R/utils.R` (`exc_tbl` list) deliberately excludes certain biospecimen
tables from the bundle. Downloaded separately from ARC Builder → Study Files →
Biospecimen:

- **`AMPRION_ASYN_SAA_04Aug2026.csv`** — the alpha-synuclein SAA result (Amprion Clinical
  Laboratory). `Result` field: `Not_Detected`, `Detected-1` (PD/DLB-consistent
  misfolded-synuclein profile), `Detected-2` (MSA-consistent profile), `Indeterminate`.
  **This is the only signal in ADNI that approximates a DLB label** — see "Why we don't
  have a DLB diagnosis label" below. 1,658 rows; 369 subjects `Detected-1`.
- **`CSFALPHASYN_03_21_14_04Aug2026.csv`** — quantitative CSF alpha-synuclein
  concentration (Luminex immunoassay, ng/ml, Jing Zhang Lab, UW). A different assay
  (concentration, not seeding/aggregation propensity) from the same biological target.
  Kept as a supplementary continuous covariate, not a subject-selection criterion.

Both came with methods/protocol PDFs, also in `biospecimen/`.

**Why these two and not more Biospecimen files:** the Biospecimen category has 245
files total (metabolomics panels, aliquot inventories, various omics). We only pulled
the two that speak directly to synucleinopathy status, since nothing else in that
category is used by the current analysis plan. If a future direction needs e.g. the AD
Metabolomics Consortium panels, they're a `search: <keyword>` away in the same ARC
Builder tab.

### 3. Cohort candidate list — `data/adni/dlb_cohort_candidates.csv`

Built by `scripts/build_dlb_subject_list.py`: takes all `Detected-1` (SAA-positive)
subjects, finds each one's closest FDG-PET scan (`UCBERKELEYFDG_8mm`) and closest
structural MRI scan (`UCSFFSX51`) by exam date, keeps the match only if it's within 365
days of the SAA draw.

Result: 369 SAA-positive subjects → 217 with a qualifying FDG-PET scan → 151 with a
qualifying MRI scan → **126 with both** (the working cohort). Diagnosis breakdown of the
126 (from `DXSUM`, most recent visit): 67 Dementia, 41 MCI, 18 CN — i.e. synucleinopathy
positivity spans ADNI's AD-spectrum labels, which is expected (see below).

**Why 365 days:** a starting cutoff, not a validated one. It trades off cohort size
against how stale the SAA result is relative to the scan. Tightening it will shrink the
126-subject cohort; loosening it risks pairing a scan with a biomarker draw that's no
longer representative of the subject's state. Revisit once the modeling plan needs a
specific N or a sensitivity check.

### 4. Images — `data/adni/images/`

Raw DICOM series for the 126-subject cohort, pulled via IDA Advanced Search →
Collection `DLB_SAApos_cohort` → Advanced Download (IDA Downloader jar tool). Two
image sets, both restricted to the 126 subjects' `PTID`s:

- **341 T1 structural MRI series** — `Image Description` wildcard `*SPGR*` (matches
  ADNI's `Sag IR-SPGR` / `Accelerated Sag IR-FSPGR` naming across phases) AND
  `Weighting = T1`. This excludes localizers, calibration scans, and other
  non-diagnostic series that make up most of a subject's raw MRI folder — an
  unfiltered MRI search on these 126 subjects returned **3,281** images before this
  filter.
- **187 FDG-PET series** — `Radiopharmaceutical` = `18F-FDG` or
  `Fluorodeoxyglucose F^18^` (ADNI uses both spellings depending on phase/site).

Total ~7.4 GB. Multiple visits per subject are included (SPGR/FDG scans exist at more
than one timepoint for many subjects) — **not yet reduced to the single visit closest
to each subject's SAA draw date**; that reduction should happen at preprocessing time
using the per-subject target dates already in `dlb_cohort_candidates.csv`, so we don't
throw away the other-visit scans in case they're useful for a longitudinal check later.

**Download mechanics note:** IDA's "Advanced Download" zip links are IP-locked — a real
(non-HEAD) request against them only succeeds from whichever IP first fetched real bytes
from that exact link, and re-visiting the download page for the *same* collection
returns the *same* locked link rather than a fresh one. To download on a remote host
(`Olympus`, `dev@213.14.157.19`) instead of the local workstation, we had to regroup the
collection into a new-named copy (`DLB_SAApos_cohort_v2`) to get fresh, unlocked
resource URLs, then let Olympus itself make the first real GET so the lock binds to its
IP. Downloads run inside detached `tmux` sessions on Olympus (`adni_positive`,
`adni_positive_small`) so they survive closing the local agent session; resume with
`ssh Olympus` then `tmux attach -t adni_positive`. IDA's own downloader jar
(`IdaDownloader_*.jar`) additionally requires an Oracle-branded JVM (checks
`java.vendor` for "oracle") and fails on Debian's OpenJDK — worked around by invoking
`edu.usc.loni.ida.download.resource.ResourceDownloader` directly via `java -cp` instead
of going through its `launch.Launcher` entry point, though in the end plain `curl -C -`
(resumable) was simpler and equally reliable, so that's what actually ran the transfer.

### 5. SAA-negative control images — `data/adni/images/` (collection `DLB_SAAneg_controls`)

A classifier needs a negative class, not just the 126 SAA-positive subjects. Built the
same way as the positive cohort but starting from `AMPRION_ASYN_SAA.Result ==
"Not_Detected"` (1,275 subjects) instead of `Detected-1`, saved to
`data/adni/saa_negative_controls.csv`. Same FDG-PET/MRI-within-365-days filter →
**415 SAA-negative subjects with both scans available** (688 have FDG-PET alone, 540
have MRI alone). All 415 were pulled (not a size-matched subset), since 3x more
negatives than positives is an acceptable, honestly-labeled class imbalance for now
rather than an artificial deduplication; if balancing turns out to matter for the
classifier, subsample at training time rather than re-downloading.

Same search scoping as the positive cohort (T1 `*SPGR*` MRI + FDG-PET), collection
`DLB_SAAneg_controls`: **1,024 MRI series + 608 PET series = 1,632 images, ~25.9 GB**.
Downloaded straight to Olympus (learned from the positive-cohort run: let Olympus make
the first real GET immediately, no need for a `_v2` regroup this time since the
collection was newly created and never touched from the local workstation).

## What we deliberately did not get, and why

- **Full-cohort images (all ~2,000+ ADNI subjects' MRI/PET).** Scope is the 126-subject
  SAA+/FDG-PET+/MRI+ cohort, not all of ADNI. Pulling everything would be hundreds of GB
  and mostly irrelevant — subjects without an SAA result can't be assessed for
  synucleinopathy status at all, which is the whole point of using ADNI over a generic
  AD imaging set.
- **Localizer / calibration / non-T1 MRI series.** Not diagnostically useful for
  volumetric or radiomic analysis; excluded via the `*SPGR*` + T1-weighting filter
  (dropped ~2,940 of 3,281 raw MRI results for these subjects).
- **Non-FDG PET tracers (amyloid: AV45/Florbetapir/Florbetaben; tau: Flortaucipir/MK-6240
  etc.).** Out of scope for now — the project's primary target is FDG-PET metabolic
  signature, not amyloid/tau burden. Amyloid/tau *tabular* summary measures (SUVR etc.)
  are already present in `data/adni/tables/` in case they're wanted as covariates later;
  we did not pull the underlying PET *images* for those tracers.
- **Genetic files (raw WGS / SNP arrays).** Not downloaded. APOE genotype — the one
  genetic covariate typically used in AD/DLB classification — is already present in
  `APOERES.csv` via `ADNIMERGE2`. Raw genome-wide genetic data would only matter for a
  polygenic-risk or GWAS-style analysis, which isn't part of the current plan.
- **Other Biospecimen categories** (metabolomics panels, aliquot inventories, plasma
  proteomics beyond what's in `ADNIMERGE2`). Not used by the current analysis; see
  "Why these two and not more" above.
- **Non-ADNI cohorts (E-DLB consortium, PPMI/AMP-PD).** Referenced in
  `docs/advisor_notes/2.md` as a possible future external validation source, but no
  data request has been made yet — that's a separate access process (E-DLB is a
  consortium, not a public download) and hasn't been started.

## Why we don't have a DLB diagnosis label

ADNI's `DXSUM.DIAGNOSIS` field only has three values: `CN`, `MCI`, `Dementia` (with the
underlying dementia usually presumed AD). ADNI was never designed to enroll or diagnose
DLB as a distinct category. The SAA result is a *proxy*: alpha-synuclein co-pathology is
common in ADNI's AD-spectrum subjects (consistent with autopsy literature showing
mixed AD+Lewy body pathology is more common than "pure" DLB), so `Detected-1` marks
"has evidence of synucleinopathy," not "clinically diagnosed DLB." This is why the
126-subject cohort spans CN/MCI/Dementia labels rather than being a clean DLB group —
the classification target for the radiomics model is the SAA result itself (or an
FDG-PET metabolic signature correlated with it), not ADNI's `DIAGNOSIS` field.
