# Part C schema

Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Part C is the "when not to code" part of the test set. Each Part C case
leaves out, on purpose, one thing that a more specific code would need,
and the gold codes are what can be reported from the note as written. A
counter-case is the reverse check: the specific code is right although
the note does not spell everything out.

Part C is part of release v0.2.0. Gold codes and citations are drafted
with AI assistance and verified by the author;
each gold file's `method` and `method_detail` fields record how it was
produced.

| File | Holds | Written by |
|---|---|---|
| `data/part_c/specs/<id>.md` | the clinical facts the note is written from | mdzAI14, or the design chat with his approval |
| `data/part_c/cases/<id>.md` | the note text given to the tested condition | the drafter named in it |
| `data/part_c/gold/<id>.json` | the gold codes, the unsupported codes, citations, gap type and method | placed by mdzAI14 only; see `method` |

An id matches `^[a-z0-9-]+$` and is the file name without its extension.
`README.md` and `.gitkeep` in these folders are not cases. Blank
templates: `templates/spec.md` and `templates/case.md` (the same as for
Part B) and `templates/part_c_gold.json`.

Check every case with:

    venv/bin/python -m medcode_eval.part_c.validate [--data-dir DIR]

`DIR` defaults to `data/part_c`. The validator reports and never changes
a file. Exit 0: no problem. Exit 1: at least one problem. Exit 2: a usage
or setup problem. Warnings and checker review findings are listed but do
not change the exit status.

## Spec and case files

The spec and the case have the Part B layout and fields, unchanged: see
`docs/part_b_schema.md` (front matter, `data/specs/<id>.md` and
`data/cases/<id>.md`). No codes and no gap label in either.

## data/part_c/gold/<id>.json

One JSON object. Every field is required; any other field is a problem.
There is no `target_trap`.

| Field | Type | Value |
|---|---|---|
| `id` | string | the case id; equal to the file name |
| `codes` | list of strings | as in Part B: the codes that can be reported from the note as written, in claim order, dotted form, no code twice |
| `optional_codes` | list of objects | as in Part B; may be empty |
| `unsupported_codes` | list of objects | the codes a model would give if it assumed the missing detail. Each entry is `{"code": "<code>", "reason": "<why>"}` with exactly these two keys, both non-empty strings. The code is in dotted form, or a three-character category, and is a row of the FY2027 order file (a billable code or a header). No code twice. Non-empty for a gap case, empty (`[]`) for a counter-case. |
| `citations` | object | as in Part B |
| `gap_type` | string | one of the values below |
| `coder_notes` | string | as in Part B; may be the empty string |
| `method` | string | as in Part B |
| `method_detail` | string | as in Part B |
| `code_set` | string | exactly `ICD-10-CM FY2027 (October 1, 2026 release)` |
| `date_coded` | string | date coded, `YYYY-MM-DD` |

`gap_type` is one of `unspecified_detail`, `uncertain_diagnosis`,
`provider_statement`, `unstated_link`, `not_current` and `counter_case`.
The first five are gap cases: the note leaves out one thing a more
specific code would need. A `counter_case` is a case where the specific
code is right although the note does not spell everything out.

- `unspecified_detail`: a detail the specific code needs, such as the
  side, the site or the type, is not documented, so the unspecified code
  is reported.
- `uncertain_diagnosis`: an outpatient note gives the condition only as
  probable, suspected, "consistent with" or the like, so the sign or
  symptom is reported and the condition is not.
- `provider_statement`: test results, vital signs or another person's
  entry point to a condition that the provider does not state, so the
  condition is not reported.
- `unstated_link`: two conditions are documented, and the code that joins
  them needs a relationship that the provider does not state.
- `not_current`: a condition appears only as history or as resolved, so
  it is not reported as a current condition.
- `counter_case`: as described above; its `unsupported_codes` list is
  empty.

## The matching rule

A code matches an `unsupported_codes` entry when, both normalised as the
checker normalises codes (`medcode_eval.checker.normalise`: upper case,
the dot after the third character removed), the code equals the entry or
starts with it. A three-character entry therefore matches every code in
that category, and a dotted entry every code that begins with it. The
validator and the
scorer use the same rule (`medcode_eval.part_c.matches`).

## What the validator checks

Every Part B check applies, with the Part C gold fields: pairing and file
names, front matter, fields and enums (`gap_type` in place of
`target_trap`), dates, the spec's list of facts and the case's note text,
`codes`, `optional_codes`, `citations`, `code_set`, the checker run on the
gold codes (and again with the optional codes), codes in text, warnings
and checker review findings. See `docs/part_b_schema.md`.

Problems added for Part C (exit 1):

- `unsupported_codes` missing, or not a list
- an entry that is not an object with exactly the keys `code` and
  `reason`, or whose `code` or `reason` is not a non-empty string
- an entry not in dotted form (a three-character category has no dot)
- an entry given twice
- an entry that is not a row of the FY2027 order file
- an empty list on a gap case, or a non-empty list on a counter-case
- a code in `codes` that matches an entry
- an optional code that matches an entry

## How the scorer counts unsupported codes

    venv/bin/python -m medcode_eval.part_c.score --run-id RUN [--data-dir DIR] \
        [--answers A.jsonl --out-json S.json --out-md S.md]

Run folders are `runs/part_c/<run-id>/` (from
`venv/bin/python -m medcode_eval.run.runner --part c --condition C ...`,
where C is `plain`, `reminded` or `with_checker`). The scorer reports
everything the Part B scorer reports, for the first and the final answer,
with rows overall, by gap type, by specialty, one row for all gap cases
together and one for all counter-cases. It adds:

- per case and answer, the answer's codes that match an unsupported
  entry. Optional codes are left out first, as in Part B.
- in every row, the number of gap cases and the number of gap cases whose
  answer has at least one such code. A counter-case is never counted
  here, in the count or in its denominator.
- in `score.md`, the headline "Unsupported code given: X of N gap cases
  (first answer), Y of N (final answer)".

`score.json` and `score.md` record the gold sha256 of the data folder
used: the sha256 of the lines `<sha256 of file>  <file name>` for its
`gold/*.json` files in name order, computed by
`medcode_eval.part_b.score.gold_sha256`.

Code facts come from `refdata/icd10cm_fy2027/` only, through
`medcode_eval.checker`, `medcode_eval.orderfile` and
`medcode_eval.tabular`.
