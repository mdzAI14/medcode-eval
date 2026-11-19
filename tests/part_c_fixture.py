"""Invented Part C fixtures for the validator, scorer and runner tests.

Specs and cases are written by tests/part_b_fixture.make_data_dir (the
Part B layout, unchanged); the gold files are then replaced by Part C gold
(gap_type and unsupported_codes, no target_trap). Codes are the invented
U9x codes of tests/test_checker.py. Nothing here is gold: these files live
only in temporary directories that the tests remove. No network.
"""

import json
from pathlib import Path

from tests.part_b_fixture import CODE_SET, TempDir, make_data_dir, make_refdata  # noqa: F401

# id -> (specialty, note body, gold codes, gap_type, unsupported entries)
CASES = {
    "c-t-001": ("ortho", "Invented Part C note one.\nAn invented condition, detail not stated.",
                ["U95"], "unspecified_detail", ["U96", "U93"]),
    "c-t-002": ("ent", "Invented Part C note two {with braces}.\nA possible invented condition.",
                ["U91.0"], "uncertain_diagnosis", ["U92"]),
    "c-t-003": ("ortho", "Invented Part C note three.\nThe detail follows from the note.",
                ["U90.012A"], "counter_case", []),
}
# id -> optional codes
OPTIONAL = {"c-t-002": ["U94.0"]}


def gold_obj(cid, codes, gap_type, unsupported, optional=()):
    return {"id": cid, "codes": list(codes),
            "optional_codes": [{"code": c, "reason": "invented reason"} for c in optional],
            "unsupported_codes": [{"code": c, "reason": "invented assumed detail"}
                                  for c in unsupported],
            "citations": {"case": "Invented guideline section 0.0"},
            "gap_type": gap_type, "coder_notes": "Invented fixture note.",
            "method": "coder_unassisted", "method_detail": "Invented fixture method detail.",
            "code_set": CODE_SET, "date_coded": "2099-01-03"}


def make_c_data_dir(root, cases=CASES, optional=OPTIONAL, sentinel=False):
    """specs/, cases/ and gold/ under root/data (Part C gold); returns it."""
    data = make_data_dir(root, cases={cid: (sp, note, codes, "laterality")
                                      for cid, (sp, note, codes, _, _) in cases.items()},
                         sentinel=sentinel, optional=optional)
    for cid, (_, _, codes, gap, unsupported) in cases.items():
        (Path(data) / "gold" / f"{cid}.json").write_text(
            json.dumps(gold_obj(cid, codes, gap, unsupported, optional.get(cid, ()))),
            encoding="utf-8")
    return data
