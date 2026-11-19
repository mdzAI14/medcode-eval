"""Part C: when not to code (ICD-10-CM FY2027, October 1, 2026 release).

Each Part C case leaves out one thing that a more specific code would
need; the gold codes are what can be reported from the note as written.
The layout and the fields are in docs/part_c_schema.md.

The gap types and the matching rule for unsupported_codes live here, so
that the validator and the scorer use the same ones.
"""

from medcode_eval import checker

GAP_TYPES = ("unspecified_detail", "uncertain_diagnosis", "provider_statement",
             "unstated_link", "not_current")
COUNTER_CASE = "counter_case"
GAP_TYPE_VALUES = GAP_TYPES + (COUNTER_CASE,)


def is_gap_case(gap_type):
    """True for the five gap types, False for counter_case; ValueError
    for anything else."""
    if gap_type in GAP_TYPES:
        return True
    if gap_type == COUNTER_CASE:
        return False
    raise ValueError(f"gap_type {gap_type!r} is not one of {', '.join(GAP_TYPE_VALUES)}")


def matches(code, entry):
    """True when code, normalised as the checker normalises codes, equals
    the normalised entry or starts with it."""
    c, e = checker.normalise(code), checker.normalise(entry)
    return c.startswith(e)


def matching(codes, entries):
    """The codes (in order, each once) that match any entry."""
    out = []
    for c in codes:
        if c not in out and any(matches(c, e) for e in entries):
            out.append(c)
    return out
