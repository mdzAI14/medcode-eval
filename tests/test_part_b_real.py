"""The Part B runner and scorer on the committed cases (data/) and the real
ICD-10-CM FY2027 refdata (October 1, 2026 release), with the fake
responders. Run directories are temporary. No network and no model.
"""

import json
import tempfile
import unittest
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import REPO_ROOT
from medcode_eval.part_b import responders, score
from medcode_eval.run import part_b
from medcode_eval.run.runner import FakeBackend

DATA_DIR = REPO_ROOT / "data"


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


class CommittedCasesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "run"
        self.n = len(part_b.load_cases(DATA_DIR))
        self.gold = score.load_gold(DATA_DIR)
        self.meta = score.load_case_meta(DATA_DIR)

    def test_oracle_matches_and_needs_no_second_turn(self):
        backend = FakeBackend(responders.oracle(DATA_DIR), messages=True)
        part_b.run(DATA_DIR, self.out, backend, "with_checker")
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual({r["turn"] for r in raw}, {1})
        r = score.score(self.gold, self.meta, read_jsonl(self.out / "answers.jsonl"))
        for which in ("first", "final"):
            g = r[which]["overall"]
            self.assertEqual(g["n"], self.n)
            self.assertEqual(g["exact"], self.n)
            self.assertEqual(g["first_listed"], self.n)
            self.assertEqual((g["missing"], g["extra"], g["invalid"]), (0, 0, 0))
            self.assertEqual(g["findings"], {"error": 0, "review": 0})
        self.assertEqual(r["second_turns"], 0)

    def test_wrong_answer_draws_a_second_turn_everywhere(self):
        self.assertTrue(checker.check(responders.WRONG))
        backend = FakeBackend(responders.fixed(responders.WRONG), messages=True)
        part_b.run(DATA_DIR, self.out, backend, "with_checker")
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(sum(r["turn"] == 2 for r in raw), self.n)
        r = score.score(self.gold, self.meta, read_jsonl(self.out / "answers.jsonl"))
        self.assertEqual(r["second_turns"], self.n)
        self.assertEqual(r["final"]["overall"]["exact"], 0)
        self.assertEqual(r["final"]["overall"]["cases_with_error_finding"], self.n)


if __name__ == "__main__":
    unittest.main()
