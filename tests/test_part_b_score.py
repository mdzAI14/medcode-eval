"""Tests for medcode_eval.part_b.score on invented fixtures. No network."""

import json
import tempfile
import unittest

from medcode_eval.part_b import score as sc
from tests.part_b_fixture import CODE_SET, TempDir, make_data_dir, make_refdata


def setUpModule():
    global TMP, DATA
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


ANSWERS = [
    {"id": "b-t-001", "first_answer": ["U90012"], "first_valid": True,
     "final_answer": ["U95"], "final_valid": True, "second_turn": True, "error": None},
    {"id": "b-t-002", "first_answer": ["U96", "U910"], "first_valid": True,
     "final_answer": ["U96", "U910"], "final_valid": True, "second_turn": False,
     "error": None},
    {"id": "b-t-003", "first_answer": None, "first_valid": False,
     "final_answer": None, "final_valid": False, "second_turn": False, "error": None},
]


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = make_data_dir(TempDir(self).path)
        self.gold = sc.load_gold(self.dir)
        self.meta = sc.load_case_meta(self.dir)

    def result(self, answers=ANSWERS):
        return sc.score(self.gold, self.meta, answers, checker_data=DATA)

    def test_first_overall(self):
        g = self.result()["first"]["overall"]
        self.assertEqual((g["n"], g["exact"], g["first_listed"]), (3, 1, 0))
        self.assertEqual((g["correct"], g["missing"], g["extra"]), (2, 2, 1))
        self.assertAlmostEqual(g["precision"], 2 / 3)
        self.assertAlmostEqual(g["recall"], 2 / 4)
        self.assertEqual((g["invalid"], g["no_answer"]), (1, 0))
        self.assertEqual(g["findings"], {"error": 1, "review": 0})
        self.assertEqual(g["cases_with_error_finding"], 1)
        self.assertTrue(g["fewer_than_10"])

    def test_final_overall(self):
        g = self.result()["final"]["overall"]
        self.assertEqual((g["exact"], g["first_listed"]), (2, 1))
        self.assertEqual((g["correct"], g["missing"], g["extra"]), (3, 1, 0))
        self.assertEqual(g["precision"], 1.0)
        self.assertAlmostEqual(g["recall"], 0.75)
        self.assertEqual(g["findings"], {"error": 0, "review": 0})

    def test_second_turns_counted(self):
        r = self.result()
        self.assertEqual(r["second_turns"], 1)
        self.assertEqual(r["code_set"], CODE_SET)

    def test_groups(self):
        r = self.result()
        self.assertEqual(sorted(r["final"]["by_target_trap"]),
                         ["excludes1", "laterality", "seventh_character"])
        self.assertEqual(r["final"]["by_specialty"]["ortho"]["n"], 2)
        self.assertEqual(r["final"]["by_specialty"]["ortho"]["exact"], 1)
        self.assertEqual(r["final"]["by_specialty"]["ent"]["exact"], 1)

    def test_missing_answer_counted_apart_from_invalid(self):
        g = self.result(ANSWERS[:2])["final"]["overall"]
        self.assertEqual((g["invalid"], g["no_answer"]), (0, 1))
        self.assertEqual(g["missing"], 1)

    def test_order_ignored_for_exact(self):
        rows = self.result()["cases"]
        row = next(r for r in rows if r["id"] == "b-t-002")
        self.assertTrue(row["first"]["exact"])
        self.assertFalse(row["first"]["first_listed"])

    def test_precision_none_when_no_codes(self):
        answers = [dict(a, final_answer=None, final_valid=False) for a in ANSWERS]
        g = self.result(answers)["final"]["overall"]
        self.assertIsNone(g["precision"])
        self.assertEqual(g["recall"], 0.0)

    def test_duplicate_answer_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.result(ANSWERS + ANSWERS[:1])

    def test_unknown_answer_ids_counted(self):
        r = self.result(ANSWERS + [dict(ANSWERS[0], id="b-t-999")])
        self.assertEqual(r["unknown_answer_ids"], 1)

    def test_markdown_says_small_groups(self):
        md = sc.to_markdown(self.result())
        self.assertIn(CODE_SET, md)
        self.assertIn("fewer than 10 cases", md)
        self.assertIn("| overall |", md)
        self.assertIn("| target trap | laterality |", md)
        self.assertIn("| specialty | ortho |", md)
        self.assertIn("First answer", md)
        self.assertIn("Final answer", md)

    def test_json_serialisable(self):
        json.dumps(self.result())


if __name__ == "__main__":
    unittest.main()
