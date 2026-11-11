# Part B schema

Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Each Part B case is three files that share one id. Gold codes and
citations are drafted with AI assistance and verified by the author; each
gold file's `method` and `method_detail` fields record how it was produced.

| File | Holds | Written by |
|---|---|---|
| `data/specs/<id>.md` | the clinical facts the note is written from | mdzAI14 |
| `data/cases/<id>.md` | the note text given to the tested condition | the drafter named in it |
| `data/gold/<id>.json` | the gold codes, citations, target trap and method | placed by mdzAI14 only; see `method` |

An id matches `^[a-z0-9-]+$` and is the file name without its extension.
`README.md` and `.gitkeep` in these folders are not cases. Blank
templates are in `templates/`.

Check every case with:

    venv/bin/python -m medcode_eval.part_b.validate

It reports and never changes a file. Exit 0: no problem. Exit 1: at
least one problem. Exit 2: a usage or setup problem (a folder or the
reference data is missing). Warnings and checker review findings are
listed but do not change the exit status.

## Front matter (spec and case)

A spec and a case open with a front matter block: a `---` line, one
`key: value` line per field, and a closing `---` line. Values are plain
text on one line, without quotes. Every field is required and non-empty;
a field that is not listed here, or a field given twice, is a problem.
Dates are `YYYY-MM-DD`.

## data/specs/<id>.md

| Field | Value |
|---|---|
| `id` | the case id; equal to the file name |
| `specialty` | one of `ortho`, `ophtho`, `gi`, `ent`, `ed` |
| `setting` | free text, e.g. outpatient clinic visit, emergency department |
| `author` | who wrote the spec |
| `date` | date written, `YYYY-MM-DD` |

Body: the clinical facts as a markdown list, one fact per line starting
with `- `. No codes and no trap label.

## data/cases/<id>.md

| Field | Value |
|---|---|
| `id` | the case id; equal to the file name |
| `specialty` | as in the spec, and equal to the spec's |
| `setting` | as in the spec, and equal to the spec's |
| `origin` | how the note was made, e.g. AI-drafted from clinical facts, human-written |
| `drafter` | who or what drafted the note (a person, or a model and version) |
| `draft_date` | date drafted, `YYYY-MM-DD` |

Body: the note text, non-empty. No codes and no trap label.

## data/gold/<id>.json

One JSON object. JSON allows no comments, so the field notes are here.
Every field is required; any other field is a problem.

| Field | Type | Value |
|---|---|---|
| `id` | string | the case id; equal to the file name |
| `codes` | list of strings | ICD-10-CM codes in claim order; the first is first-listed. Dotted form: three characters, a dot, then the rest. No code twice. |
| `optional_codes` | list of objects | codes that are neither required nor penalized; may be empty (`[]`). Each entry is `{"code": "<code>", "reason": "<why>"}` with exactly these two keys, both non-empty strings. The code is in the dotted form used by `codes`; no code twice, and none that is also in `codes`. |
| `citations` | object | either `{"case": "<citation>"}` for one citation covering the case, or one key per code (the code as written in `codes`, dotted or not) whose value is that code's citation. Both may be given. Every value is a non-empty string, and every key other than `case` is one of the codes. |
| `target_trap` | string | one of `laterality`, `seventh_character`, `excludes1`, `combination`, `sequencing` |
| `coder_notes` | string | the coder's notes; may be the empty string |
| `method` | string | how the gold was produced: one of `ai_assisted_coder_verified` (drafted with AI assistance, every code and citation verified by the coder) or `coder_unassisted` (coded by the coder without AI assistance) |
| `method_detail` | string | non-empty free text: the tools or models used and who verified what |
| `code_set` | string | exactly `ICD-10-CM FY2027 (October 1, 2026 release)` |
| `date_coded` | string | date coded, `YYYY-MM-DD` |

A citation names the guideline it rests on, e.g. a section of the
ICD-10-CM Official Guidelines for Coding and Reporting FY2027. A citation
key may not name an optional code.

An optional code is one the coder judges defensible either way for this
case. The scorer neither requires nor penalizes it: it is removed from an
answer before the answer is compared with `codes`.

## What the validator checks

Problems (exit 1):

- pairing: every case has a spec and a gold file, and every spec and gold
  file has a case; file names are valid ids; nothing else is in the
  folders; the `id` field equals the file name
- fields: front matter present; required fields present and non-empty;
  no unknown or repeated field; `specialty`, `target_trap` and `method`
  in their lists; dates valid; the spec has a list of facts and the case has note
  text; the case's `specialty` and `setting` equal the spec's
- gold: valid JSON object; `codes` a non-empty list of non-empty strings
  with no repeat; `code_set` exactly this code set's label; every
  citation non-empty and every code covered (by its own key or by
  `case`)
- optional codes: `optional_codes` a list (may be empty) of objects with
  exactly the keys `code` and `reason`, both non-empty strings; each code
  in dotted form, not given twice and not also in `codes`; no citation key
  names an optional code
- gold codes: `medcode_eval.checker.check` is run on the codes in order.
  Every error-level finding (not in the code set, header not billable,
  manifestation first-listed) is a problem. It is run again on `codes`
  followed by the optional codes, in that order: every error-level
  finding that involves an optional code is a problem
- codes in text: a dotted string in a spec or a case (front matter
  included, any letter case) that is a stored code or a prefix of stored
  codes, for example a string of the shape `Ann.n` or `Ann.-`

Warnings (listed, not problems):

- an undotted three-character string in a spec or a case that is a
  stored category. Notes hold strings of this shape that are not codes,
  such as vertebral levels, so these are for a human to look at.

Checker review findings (listed, not problems):

- review-level findings of the checker on the gold codes (excludes1 pairs,
  codeFirst order), and those of the second run that involve an optional
  code. They are for the coder to confirm.

Code facts come from `refdata/icd10cm_fy2027/` only, through
`medcode_eval.checker`, `medcode_eval.orderfile` and
`medcode_eval.tabular`.
