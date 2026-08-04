#!/usr/bin/env Rscript
# One-time conversion of ADNIMERGE2's bundled .rda tables to CSV, so the
# pipeline can stay Python-only. Re-run if ADNIMERGE2 is updated/re-downloaded.

args <- commandArgs(trailingOnly = TRUE)
rda_dir <- if (length(args) >= 1) args[[1]] else "data/adni/ADNIMERGE2/data"
out_dir <- if (length(args) >= 2) args[[2]] else "data/adni/tables"

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rda_files <- list.files(rda_dir, pattern = "\\.rda$", full.names = TRUE)
cat(sprintf("Found %d .rda files in %s\n", length(rda_files), rda_dir))

for (f in rda_files) {
  env <- new.env()
  loaded <- load(f, envir = env)
  for (obj_name in loaded) {
    obj <- get(obj_name, envir = env)
    if (!is.data.frame(obj)) {
      cat(sprintf("SKIP %s: %s is not a data.frame (%s)\n", basename(f), obj_name, class(obj)[1]))
      next
    }
    out_path <- file.path(out_dir, paste0(obj_name, ".csv"))
    write.csv(obj, out_path, row.names = FALSE, na = "")
  }
}

cat(sprintf("Wrote CSVs to %s\n", out_dir))
