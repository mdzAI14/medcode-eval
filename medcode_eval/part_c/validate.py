"""Validate the Part C folders for ICD-10-CM FY2027 (October 1, 2026 release).

Usage (from the repo root):
    venv/bin/python -m medcode_eval.part_c.validate [--data-dir DIR]

DIR (default data/part_c/) holds specs/, cases/ and gold/, laid out as in
Part B. Every Part B check applies (medcode_eval.part_b.validate, run with
the Part C schema): the gold file has gap_type and unsupported_codes in
place of target_trap. The further rules for unsupported_codes are in
check_unsupported and docs/part_c_schema.md.

The validator reports and never changes a file. Exit codes as in Part B:
0 with no problem, 1 with any problem, 2 for a usage or setup problem.

Code facts come from refdata/icd10cm_fy2027/ only, through
medcode_eval.checker (which reads medcode_eval.orderfile and
medcode_eval.tabular).
"""

import sys

from medcode_eval import checker
from medcode_eval.part_b import validate as part_b
from medcode_eval.part_b.validate import Item, Schema
from medcode_eval.part_c import GAP_TYPE_VALUES, COUNTER_CASE, matches

GOLD_FIELDS = ("id", "codes", "optional_codes", "unsupported_codes", "citations", "gap_type",
               "coder_notes", "method", "method_detail", "code_set", "date_coded")
UNSUPPORTED_KEYS = {"code", "reason"}


def check_unsupported(g, norm, optional, rel, data, result):
    """The unsupported_codes rules. norm and optional are the normalised
    codes and optional codes (None when malformed or absent)."""
    if "unsupported_codes" not in g:
        return  # reported as a missing field

    def bad(kind, msg):
        result.problems.append(Item(kind, rel, msg))

    entries = g["unsupported_codes"]
    if not isinstance(entries, list):
        bad("bad_unsupported", "unsupported_codes must be a list")
        return
    gap = g.get("gap_type")
    if gap == COUNTER_CASE and entries:
        bad("bad_unsupported", "unsupported_codes must be empty for a counter_case")
    elif gap in GAP_TYPE_VALUES and gap != COUNTER_CASE and not entries:
        bad("bad_unsupported", f"unsupported_codes must not be empty for a gap case "
                               f"({gap})")
    seen = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or set(e) != UNSUPPORTED_KEYS:
            bad("bad_unsupported", f"unsupported_codes entry {i} must be an object with "
                                   "exactly the keys code and reason")
            continue
        if not all(isinstance(e[k], str) and e[k].strip() for k in ("code", "reason")):
            bad("bad_unsupported", f"unsupported_codes entry {i}: code and reason must be "
                                   "non-empty strings")
            continue
        code = e["code"]
        n = checker.normalise(code)
        if code != checker.dotted(n):
            bad("bad_unsupported", f"unsupported code {code!r} is not in dotted form or a "
                                   f"three-character category ({checker.dotted(n)})")
            continue
        if n in seen:
            bad("bad_unsupported", f"unsupported code {code} is listed more than once")
            continue
        seen.append(n)
        if n not in data.records:
            bad("unsupported_not_in_code_set",
                f"unsupported code {code} is not a row of the order file")
        for c in norm or []:
            if matches(c, n):
                bad("unsupported_matches_code",
                    f"gold code {checker.dotted(c)} matches unsupported code {code}")
        for c in optional or []:
            if matches(c, n):
                bad("unsupported_matches_optional",
                    f"optional code {checker.dotted(c)} matches unsupported code {code}")


SCHEMA = Schema("Part C", "medcode_eval.part_c.validate", "data/part_c", GOLD_FIELDS,
                (("gap_type", GAP_TYPE_VALUES),), check_unsupported)


def validate(root, data=None):
    """Result for a Part C data folder holding specs/, cases/ and gold/."""
    return part_b.validate(root, data=data, schema=SCHEMA)


def main(argv=None, data=None, ref_root=None):
    return part_b.main(argv, data=data, ref_root=ref_root, schema=SCHEMA)


if __name__ == "__main__":
    sys.exit(main())
