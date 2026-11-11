"""Invented Part B fixtures for the runner and scorer tests.

Cases use the invented U9x codes of tests/test_checker.py, whose fixture
reference files are imported, not copied. Nothing here is gold: these files
live only in temporary directories that the tests remove. No network.
"""

import json
import tempfile
from pathlib import Path

from medcode_eval import checker
from tests.test_checker import FIXTURE_XML, ORDER_ROWS, PATHS, order_text

CODE_SET = "ICD-10-CM FY2027 (October 1, 2026 release)"

# id -> (specialty, note body, gold codes, target trap)
CASES = {
    "b-t-001": ("ortho", "Invented note one.\nThe patient has invented condition U95.",
                ["U95"], "laterality"),
    "b-t-002": ("ent", "Invented note two {with braces}.\nTwo invented conditions.",
                ["U91.0", "U96"], "excludes1"),
    "b-t-003": ("ortho", "Invented note three.", ["U90.012A"], "seventh_character"),
}


def make_refdata(root):
    root = Path(root)
    (root / "ref").mkdir(parents=True, exist_ok=True)
    (root / PATHS["order"]).write_text(order_text(ORDER_ROWS), encoding="ascii")
    (root / PATHS["tabular"]).write_text(FIXTURE_XML, encoding="utf-8")
    return checker.load(root=root, paths=PATHS)


def make_data_dir(root, cases=CASES, sentinel=False):
    """specs/, cases/ and gold/ under root/data; returns that folder.

    With sentinel=True every front-matter value, the spec and every gold
    field except codes carry the marker SENTINEL.
    """
    data = Path(root) / "data"
    for sub in ("specs", "cases", "gold"):
        (data / sub).mkdir(parents=True, exist_ok=True)
    for i, (cid, (spec, note, codes, trap)) in enumerate(cases.items()):
        mark = (lambda k: f"SENTINEL{k.upper()}{i}") if sentinel else (lambda k: "x")
        fm = {"id": cid, "specialty": spec, "setting": mark("setting"),
              "origin": mark("origin"), "drafter": mark("drafter"),
              "draft_date": "2026-11-11"}
        (data / "cases" / f"{cid}.md").write_text(
            "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n" + note + "\n\n",
            encoding="utf-8")
        (data / "specs" / f"{cid}.md").write_text(
            f"---\nid: {cid}\nspecialty: {spec}\nsetting: {mark('setting')}\n"
            f"author: {mark('author')}\ndate: 2026-11-11\n---\n- {mark('spec')}\n",
            encoding="utf-8")
        gold = {"id": cid, "codes": codes, "citations": {"case": mark("citation")},
                "target_trap": trap, "coder_notes": mark("notes"),
                "method": "coder_unassisted", "method_detail": mark("detail"),
                "code_set": CODE_SET, "date_coded": "2026-11-11"}
        (data / "gold" / f"{cid}.json").write_text(json.dumps(gold), encoding="utf-8")
    return data


class TempDir:
    """A temporary directory removed by the test's cleanup."""

    def __init__(self, test):
        tmp = tempfile.TemporaryDirectory()
        test.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
