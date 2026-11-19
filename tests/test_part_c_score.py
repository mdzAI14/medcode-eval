"""Tests for medcode_eval.part_c.score on invented fixtures. No network."""

import json
import tempfile
import unittest

from medcode_eval.part_b import score as score_b
from medcode_eval.part_c import score as sc
from medcode_eval.run import part_c as run_c
from tests.part_c_fixture import CODE_SET, TempDir, make_c_data_dir, make_refdata


def setUpModule():
    global TMP, DATA
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


def row(cid, first, final, second=False):
    return {"id": cid, "first_answer": first, "first_valid": first is not None,
            "final_answer": final, "final_valid": final is not None,
            "second_turn": second, "error": None}


# c-t-001 (gap; unsupported U96, U93): first gives U96 (equal), final U93.1 (prefix)
# c-t-002 (gap; unsupported U92; optional U94.0): neither answer matches
# c-t-003 (counter_case): an answer with a code matching nothing it could hold
ANSWERS = [
    row("c-t-001", ["U95", "U96"], ["U931"], second=True),
    row("c-t-002", ["U910", "U940"], ["U910"]),
    row("c-t-003", ["U96"], ["U90012A"]),
]


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = make_c_data_dir(TempDir(self).path)
        self.gold = score_b.load_gold(self.dir)
        self.meta = score_b.load_case_meta(self.dir)

    def result(self, answers=ANSWERS, gold=None):
        return sc.score(gold or self.gold, self.meta, answers, checker_data=DATA,
                        gold_hash="h")

    def case(self, r, cid):
        return next(c for c in r["cases"] if c["id"] == cid)

    def test_equality_and_prefix_matches(self):
        r = self.result()
        c = self.case(r, "c-t-001")
        self.assertEqual(c["first"]["unsupported_given"], ["U96"])
        self.assertEqual(c["final"]["unsupported_given"], ["U931"])
        self.assertEqual(c["unsupported"], ["U96", "U93"])

    def test_answer_without_match_not_counted(self):
        c = self.case(self.result(), "c-t-002")
        self.assertEqual(c["first"]["unsupported_given"], [])
        self.assertEqual(c["final"]["unsupported_given"], [])

    def test_optional_code_not_counted(self):
        gold = json.loads(json.dumps(self.gold))
        # an (invalid) gold whose optional code matches an entry: still not counted
        gold["c-t-002"]["unsupported_codes"].append({"code": "U94", "reason": "x"})
        c = self.case(self.result(gold=gold), "c-t-002")
        self.assertEqual(c["first"]["unsupported_given"], [])

    def test_counter_case_left_out(self):
        r = self.result()
        for which in ("first", "final"):
            g = r[which]["overall"]
            self.assertEqual(g["n"], 3)
            self.assertEqual(g["gap_cases"], 2)
            cc = r[which]["by_case_kind"]["counter_case"]
            self.assertEqual((cc["n"], cc["gap_cases"], cc["gap_cases_with_unsupported"]),
                             (1, 0, 0))
        c = self.case(r, "c-t-003")
        self.assertEqual(c["first"]["unsupported_given"], [])
        self.assertEqual(r["gap_cases"], 2)

    def test_first_and_final_counted_apart(self):
        gold = json.loads(json.dumps(self.gold))
        r = self.result(answers=[row("c-t-001", ["U95"], ["U96"], True), ANSWERS[1],
                                 ANSWERS[2]], gold=gold)
        self.assertEqual(r["first"]["overall"]["gap_cases_with_unsupported"], 0)
        self.assertEqual(r["final"]["overall"]["gap_cases_with_unsupported"], 1)
        r = self.result()
        self.assertEqual(r["first"]["overall"]["gap_cases_with_unsupported"], 1)
        self.assertEqual(r["final"]["overall"]["gap_cases_with_unsupported"], 1)

    def test_rows(self):
        r = self.result()
        for which in ("first", "final"):
            self.assertEqual(sorted(r[which]["by_gap_type"]),
                             ["counter_case", "uncertain_diagnosis", "unspecified_detail"])
            self.assertEqual(sorted(r[which]["by_specialty"]), ["ent", "ortho"])
            self.assertEqual(sorted(r[which]["by_case_kind"]), ["counter_case", "gap_case"])
            gc = r[which]["by_case_kind"]["gap_case"]
            self.assertEqual((gc["n"], gc["gap_cases"]), (2, 2))
            ortho = r[which]["by_specialty"]["ortho"]
            self.assertEqual((ortho["n"], ortho["gap_cases"]), (2, 1))
            self.assertEqual(r[which]["by_gap_type"]["counter_case"]["gap_cases"], 0)
        self.assertEqual(r["first"]["by_specialty"]["ortho"]["gap_cases_with_unsupported"], 1)
        self.assertEqual(r["first"]["by_specialty"]["ent"]["gap_cases_with_unsupported"], 0)

    def test_part_b_measures_kept(self):
        r = self.result()
        g = r["final"]["overall"]
        for k in ("exact", "first_listed", "correct", "missing", "extra", "optional_given",
                  "precision", "recall", "invalid", "no_answer", "findings",
                  "cases_with_error_finding", "fewer_than_10"):
            self.assertIn(k, g)
        self.assertEqual(g["exact"], 2)   # c-t-002 and c-t-003
        self.assertEqual(r["code_set"], CODE_SET)
        self.assertEqual(r["second_turns"], 1)
        self.assertNotIn("by_target_trap", r["final"])

    def test_unknown_gap_type_refused(self):
        gold = json.loads(json.dumps(self.gold))
        gold["c-t-001"]["gap_type"] = "invented"
        with self.assertRaises(ValueError):
            self.result(gold=gold)

    def test_headline(self):
        md = sc.to_markdown(self.result(answers=[row("c-t-001", ["U95"], ["U96"], True),
                                                 ANSWERS[1], ANSWERS[2]]))
        self.assertIn("Unsupported code given: 0 of 2 gap cases (first answer), "
                      "1 of 2 (final answer)", md)
        self.assertIn("Code set: " + CODE_SET, md)
        self.assertIn("Gold sha256: h", md)


class MainTests(unittest.TestCase):
    def test_default_folders_and_gold_hash(self):
        root = TempDir(self).path
        src = make_c_data_dir(root / "x")
        (root / "data").mkdir()
        data = src.rename(root / "data" / "part_c")
        run_dir = root / run_c.RUNS_DIR / "r1"
        run_dir.mkdir(parents=True)
        (run_dir / "answers.jsonl").write_text(
            "".join(json.dumps(a) + "\n" for a in ANSWERS), encoding="utf-8")
        orig = sc.REPO_ROOT
        sc.REPO_ROOT = root
        try:
            sc.main(["--run-id", "r1"], checker_data=DATA)
        finally:
            sc.REPO_ROOT = orig
        out = json.loads((run_dir / "score.json").read_text())
        self.assertEqual(out["gold_sha256"], score_b.gold_sha256(data))
        md = (run_dir / "score.md").read_text()
        self.assertIn(score_b.gold_sha256(data), md)
        self.assertIn("Unsupported code given: 1 of 2 gap cases (first answer), "
                      "1 of 2 (final answer)", md)

    def test_answers_option_needs_out_paths(self):
        with self.assertRaises(SystemExit):
            sc.main(["--answers", "x.jsonl"], checker_data=DATA)


if __name__ == "__main__":
    unittest.main()
