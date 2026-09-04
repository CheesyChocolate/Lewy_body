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

### 6. Raw image format mix: DICOM, ECAT7, and Interfile

The downloaded FDG-PET raw images aren't uniformly DICOM. Counted directly in
`data/adni/images/ADNI/`: 1,944 DICOM series (`.dcm`), 179 ECAT7 series (`.v` files,
magic bytes `MATRIX72`), and 37 Interfile series (`.hdr` text header + `.i` raw binary,
`!INTERFILE` magic). All three are early-phase ADNI-1 FDG-PET reconstructions (site
`HRRT` scanner, e.g. `128_S_2002`) that predate ADNI's later standardization on DICOM for
PET exports; they're dynamic acquisitions (6 frames × 300s each, confirmed from an
Interfile header's `frame definition := 300*6`), not static images.

- **DICOM** — the large majority, converts fine with `dcm2niix`.
- **ECAT7 (`.v`)** — `dcm2niix` converts these too, with a
  `Warning: ECAT support VERY experimental (Spatial transforms unknown)`.
- **Interfile (`.hdr`/`.i`)** — neither `dcm2niix` nor `SimpleITK` can read this format at
  all. Checked whether these 37 series (25 subjects, all already in the cohort) could
  just be dropped in favor of a DICOM/ECAT visit for the same subject: **no** — none of
  the 25 subjects have any non-Interfile FDG-PET visit, so dropping them would cost real
  cohort size and bias it toward later ADNI phases. Tried `medcon`/`xmedcon` (a
  general-purpose Interfile-capable converter) as a shortcut: it parses the header
  correctly but **silently corrupts the pixel values** for this Siemens/HRRT variant
  (warns `Unsupported Siemens PET data type` but still writes float32 garbage up to
  ~1e38, instead of failing) — confirmed by comparing against the raw bytes read directly
  as little-endian float32, which are clean (`[0, ~0.5]`). Do not use medcon for these
  files. Wrote a direct reader instead: `src/dlb_radiomics/interfile.py` +
  `scripts/convert_interfile_series.py`, run successfully against all 37 series
  (2026-08-07). Frames are combined into a static volume by raw-count sum by default
  (not decay-corrected — an open question, applies to the ECAT `.v` series too, see
  `docs/TODO.md`).

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

### 7. Missing-MRI gap discovery and remediation (2026-08-07)

While working on "reduce images to one visit per subject" (`docs/TODO.md`), found that
**376 of 541 cohort rows (376/534 unique RIDs, ~69%) had no raw MRI on disk at all**,
only FDG-PET — despite `has_mri` being true in `dlb_cohort_candidates.csv` /
`saa_negative_controls.csv`. Root cause: `has_mri` is derived from ADNI's precomputed
`UCSFFSX51` FreeSurfer table (a scan was processed), not from raw-image download
verification, and the original MRI search (section 4 above) used `Image Description`
wildcard `*SPGR*`, which only matches **GE-scanner** T1 naming (`Sag IR-SPGR`,
`Accelerated Sag IR-FSPGR`). Siemens-site subjects' T1 sequences are named
`MPRAGE`/`MP-RAGE`/`MP RAGE` instead and were silently excluded — confirmed via
`data/adni/tables/MRIPROT.csv` `SERIESDESC` values for a sample of the missing RIDs.

**Fix:** new IDA Advanced Search, `Image Description` wildcard `*MP*RAGE*` (catches
`MPRAGE`/`MP-RAGE`/`MP RAGE` and REPEAT/GRAPPA2/SENSE2 variants) + `Weighting = T1` +
`Modality = MRI`, restricted to the 370 missing PTIDs → 3,603 candidate series.
Collection `DLB_missing_MRI_v1_v2` (regrouped once from `DLB_missing_MRI_v1` to get an
unlocked download link for Olympus, same pattern as section 4). Downloaded to Olympus
(`~/adni_download/DLB_missing_MRI_v1_v2/`): `zip1.zip` (39.1 GB, main DICOM archive) and
`zip2.zip` (519 MB, "dataset"/metadata archive) — both complete and verified as of
2026-08-07.

**Integration decision (2026-08-07):** stage first, don't merge directly into
`data/adni/images/ADNI/`. Target: `data/adni/images/ADNI_missing_mri_v1_v2_staging/`
(already created, empty). Pull command (resumable, requires `sshuttle --remote
dev@213.14.157.19:2222 0.0.0.0/0` running so the `Olympus` SSH alias resolves):

```
rsync -avP Olympus:~/adni_download/DLB_missing_MRI_v1_v2/ data/adni/images/ADNI_missing_mri_v1_v2_staging/
```

**Resolved (2026-08-17).** Extracted directly on Olympus (no need to re-pull the zips to
the workstation — they were already sitting in `~/adni_download/` from the original
download) straight into `data/adni/images/ADNI/`, merging automatically since the zip's
top-level path prefix matches the existing tree. 624,113 files added, zips deleted after
extraction to reclaim disk. This happened as part of the broader data-location move to
Olympus — see section 8 below.

**Refined understanding of the IP-lock mechanism** (extends section 4's note): locking
appears to bind to whichever IP "initiates" the download by generating/clicking the
Advanced Downloader's manifest/zip link *in-browser*, not strictly to the first raw-byte
GET against the zip itself. Confirmed via a 291-byte error-stub zip whose embedded
`README.txt` read: *"You have attempted to download this file from IP address
213.14.157.19, which is different from the IP address (185.218.216.241) you used to
initiate this download."* Practical effect: even a link generated for a collection
already regrouped for Olympus can still lock to the local workstation's IP if the
workstation's browser is the one that clicks the download link while not routed through
`sshuttle`. Fix each time: have the user start `sshuttle --remote
dev@213.14.157.19:2222 0.0.0.0/0`, verify both the workstation and Olympus report the
same IP via `curl -s https://ifconfig.me`, then click/regenerate the specific
zip/URL-list link in-browser while sshuttle is active, and only then let Olympus's own
`curl` fetch it.

### 8. Data relocated to Olympus as canonical store (2026-08-17)

The local workstation only has ~69GB free, not enough for the full ~190GB uncompressed
image dataset (missing-MRI fix + SAA-negative controls + SAA-positive cohort v2). Decided
to develop pipeline code on the workstation but run the pipeline and store all data on
`Olympus`, which already has a git clone of this repo at `~/Projects/Lewy_body` (pushed
via a dedicated deploy key, `github-lewy-body` SSH alias).

All three raw zip sets already sitting in `~/adni_download/` on Olympus (from the original
download runs, never re-transferred) were extracted directly into
`~/Projects/Lewy_body/data/adni/images/ADNI/` on Olympus, in a detached tmux session
(`data_extract`) so the multi-hour job survived session restarts:

- `DLB_missing_MRI_v1_v2` (zip1 + zip2): 624,113 files
- `DLB_SAAneg_controls`: 356,960 files
- `DLB_SAApos_cohort_v2`: 113,133 files

Total: 1,094,206 files, extracted sequentially (deleting each zip immediately after its
own extraction to keep disk headroom, since all three together exceed Olympus's free
space at once). Additionally rsynced from the workstation, since these aren't derivable
from the raw zips: `ADNIMERGE2/`, `tables/`, `biospecimen/`, the cohort/tracking CSVs
(`dlb_cohort_candidates.csv`, `saa_negative_controls.csv`, `DATADIC_03Aug2026.csv`,
`missing_mri_ptids.txt`, `DLB_missing_MRI_v1*.csv`), and the 37 Interfile-converted
`.nii.gz` PET series outputs (`scripts/convert_interfile_series.py` writes these inline
into the raw image tree, so they aren't part of any zip). Final count on Olympus:
1,094,243 files under `data/adni/images/ADNI/`.

`data/adni/` remains gitignored on Olympus too — only the data location changed, not the
tracking scheme. The workstation's own copies of `data/adni/images/ADNI/` (74GB) and
`data/adni/images/ADNI_missing_mri_v1_v2_staging/` (40GB, the local rsync'd copy of the
same zips already deleted on Olympus) are now redundant but were deliberately left in
place pending explicit confirmation before deletion.

### 9. PET field-of-view coverage gap discovered during model QA (2026-09-02)

After the first full nested-CV run came back near-chance (mean AUC-ROC 0.547 on the
491-subject `features.csv`), spot-checked registration quality on 6 subjects (mix of
SAA+/SAA-, mix of DICOM/ECAT7/Interfile PET source format) before trusting the "weak
signal" explanation. Found a real, previously invisible data-quality bug, not just a weak
classifier.

**The mechanism**: `register_pet_to_t1` (rigid `ants.registration`) resamples PET onto the
T1's voxel grid, but only within the PET's own original physical extent — anything in the
T1 volume outside where the PET was actually acquired gets zero-filled. A PET scanner's
axial field of view is fixed by hardware (e.g. the HRRT/ECAT-Exact-HR+ scanners behind this
project's 179 ECAT7 series have a ~153mm z-FOV: 63 slices × 2.425mm), and if the bed wasn't
positioned to fully include the top of the head, the resulting zero-fill silently clips into
cortex — with no error, no NaN, nothing pyradiomics would flag. It just extracts texture
features from a mix of real PET signal and zero-padding.

**Evidence** — two subjects on the *same* scanner/FOV size (ECAT7, 128×128×63 @
2.57×2.57×2.43mm):

- `041_S_4041` (SAA-positive): registered-PET nonzero fraction 59.2% overall, but per-ROI
  coverage was badly uneven — `paracentral` only **28.3%** covered by real PET data,
  `postcentral` **60.2%**, `superior_parietal` **60.6%**, `precuneus` **84.0%** (the rest
  ≥98%). See `figs/pet_fov_clip_041_S_4041.png` — note the hard horizontal cutoff in the
  PET-overlay row (middle row), and the DKT ROI contours (yellow, bottom row) extending
  into visibly PET-signal-free territory.
- `006_S_4363` (SAA-negative), same scanner/FOV size: registered-PET nonzero fraction
  58.9% overall, but **every one of the 13 cortical ROIs was 100% covered**. See
  `figs/pet_fov_ok_006_S_4363.png`.

Same hardware, same overall PET-volume-fill fraction, wildly different per-ROI outcomes —
**this is not a fixed defect of the ECAT7 format**, it's a function of how well each
individual subject's head happened to be centered in the scanner's fixed FOV at acquisition
time. It's silent and undetectable from the feature values alone (no NaN, no obvious
outlier — a texture feature computed on 30% zero-padding still looks like a normal float).

**Status**: a full-cohort audit (`scripts/audit_pet_fov_coverage.py`, all 491 subjects,
resumable, output `data/adni/pet_fov_coverage_audit.csv` on Olympus) is running as of
2026-09-02 to quantify how many subjects/ROIs are actually affected before deciding on a
fix (candidates: exclude affected ROI-subject feature rows, intersect each ROI mask with
the PET's actual coverage before extraction and flag/drop under-covered ROIs, or re-pull
PET series with better FOV where ADNI has an alternative visit). This audit skips the
expensive DKT segmentation step (the real per-subject cortical masks) in favor of a cheap
intensity-threshholded whole-brain mask restricted to the top 35% of the head by z — a
proxy for "the vertex-near region where the clipping was observed" — because a full,
DKT-accurate 491-subject audit would cost the same ~60 hours as the original extraction
batch. See `docs/KNOWLEDGE.md` "PET field-of-view coverage" for the full technical
writeup and the audit's eventual results.

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
