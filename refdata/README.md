# refdata

Rule: facts about codes (validity, billability, descriptions, notes,
hierarchy) come only from the files in this directory.

- Each file is an unmodified copy of a public CDC/CMS release, kept in a
  folder named by code set and fiscal year (for example `icd10cm_fy2027/`).
- Every file is listed in `MANIFEST.md` with its source, release and sha256.
- `incoming/` holds raw downloads and is not tracked.
