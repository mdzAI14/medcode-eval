"""End to end for Part C in a temporary folder, on invented fixtures: two
invented cases (a gap case and a counter-case), the validator, the runner
with the fake backend in the plain and the reminded condition, then the
scorer. No network and no model.
"""

import json
import unittest
from pathlib import Path

from medcode_eval.part_c import score as sc
from medcode_eval.part_c import validate
from medcode_eval.run import part_c
from medcode_eval.run.runner import FakeBackend
from tests.part_c_fixture import TempDir, make_c_data_dir, make_refdata

TWO = {
    "c-e-001": ("ortho", "Invented end-to-end note one.\nA detail is not stated.",
                ["U95"], "unspecified_detail", ["U96"]),
    "c-e-002": ("ent", "Invented end-to-end note two.\nThe detail follows from the note.",
                ["U90.012A"], "counter_case", []),
}
REMINDER = "Do not assume a detail the\nnote does not state."


def responder(messages):
    """Gap case: U96 (the assumed detail) without the reminder, U95 with it.
    Counter-case: U90.012A either way."""
    text = messages[0]["content"]
    if "end-to-end note two" in text:
        return '["U90.012A"]'
    return '["U95"]' if REMINDER in text else '["U95", "U96"]'


def end_to_end(root, ref_root):
    """Builds the folder, runs both conditions and scores them. Returns
    {condition: (score dict, score.md text)} and the validator result."""
    root = Path(root)
    data = make_refdata(ref_root)
    data_dir = make_c_data_dir(root, cases=TWO, optional={})
    checked = validate.validate(data_dir, data=data)
    out = {}
    for cond in ("plain", "reminded"):
        run_dir = root / part_c.RUNS_DIR / f"e2e-{cond}"
        part_c.run(data_dir, run_dir, FakeBackend(responder, messages=True), cond,
                   checker_data=data)
        result = sc.main(["--answers", str(run_dir / "answers.jsonl"),
                          "--data-dir", str(data_dir),
                          "--out-json", str(run_dir / "score.json"),
                          "--out-md", str(run_dir / "score.md")], checker_data=data)
        out[cond] = (result, (run_dir / "score.md").read_text(encoding="ascii"))
    return out, checked


class EndToEnd(unittest.TestCase):
    def test_plain_and_reminded(self):
        out, checked = end_to_end(TempDir(self).path, TempDir(self).path)
        self.assertEqual(checked.problems, [])
        plain, plain_md = out["plain"]
        reminded, reminded_md = out["reminded"]
        self.assertEqual(plain["first"]["overall"]["gap_cases_with_unsupported"], 1)
        self.assertEqual(reminded["first"]["overall"]["gap_cases_with_unsupported"], 0)
        for r in (plain, reminded):
            self.assertEqual(r["gap_cases"], 1)
            self.assertEqual(r["n_cases"], 2)
        self.assertIn("Unsupported code given: 1 of 1 gap cases (first answer), "
                      "1 of 1 (final answer)", plain_md)
        self.assertIn("Unsupported code given: 0 of 1 gap cases (first answer), "
                      "0 of 1 (final answer)", reminded_md)
        self.assertEqual(reminded["final"]["overall"]["exact"], 2)
        json.dumps(plain)


if __name__ == "__main__":
    unittest.main()
