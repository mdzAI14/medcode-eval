"""Tests for medcode_eval.part_b.score on invented fixtures. No network."""

import hashlib
import json
import tempfile
import unittest

from medcode_eval.part_b import responders
from medcode_eval.part_b import score as sc
from medcode_eval.run.part_b import load_cases, render_first
from tests.part_b_fixture import (CASES, CODE_SET, OPTIONAL, TempDir, make_data_dir,
                                  make_refdata)


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


def row(cid, first, final=None):
    final = first if final is None else final
    return {"id": cid, "first_answer": first, "first_valid": first is not None,
            "final_answer": final, "final_valid": final is not None,
            "second_turn": False, "error": None}


class OptionalCodeTests(unittest.TestCase):
    """b-t-002: gold U91.0 U96, optional U94.0 (tests/part_b_fixture.py)."""

    def setUp(self):
        self.dir = make_data_dir(TempDir(self).path)
        self.gold = sc.load_gold(self.dir)
        self.meta = sc.load_case_meta(self.dir)

    def case(self, answer, cid="b-t-002", gold=None):
        r = sc.score(gold or self.gold, self.meta, [row(cid, answer)], checker_data=DATA)
        return next(c for c in r["cases"] if c["id"] == cid), r

    def test_fixture_has_the_optional_code(self):
        self.assertEqual([o["code"] for o in self.gold["b-t-002"]["optional_codes"]],
                         ["U94.0"])

    def test_required_plus_optional_is_exact(self):
        c, _ = self.case(["U910", "U96", "U940"])
        self.assertTrue(c["first"]["exact"])
        self.assertTrue(c["first"]["first_listed"])
        self.assertEqual((c["first"]["correct"], c["first"]["missing"], c["first"]["extra"]),
                         (2, 0, 0))
        self.assertEqual(c["first"]["optional_given"], 1)
        self.assertEqual(c["optional"], ["U940"])

    def test_optional_first_is_not_first_listed(self):
        c, _ = self.case(["U940", "U910", "U96"])
        self.assertTrue(c["first"]["exact"])
        self.assertFalse(c["first"]["first_listed"])

    def test_optional_alone_is_neither_correct_nor_extra(self):
        c, r = self.case(["U940"])
        self.assertFalse(c["first"]["exact"])
        self.assertEqual((c["first"]["correct"], c["first"]["missing"], c["first"]["extra"]),
                         (0, 2, 0))
        g = r["first"]["by_specialty"]["ent"]
        self.assertIsNone(g["precision"])
        self.assertEqual(g["optional_given"], 1)

    def test_not_given_counts_zero_and_changes_nothing(self):
        c, _ = self.case(["U910", "U96"])
        self.assertTrue(c["first"]["exact"])
        self.assertEqual(c["first"]["optional_given"], 0)

    def test_optional_of_another_case_is_extra(self):
        c, _ = self.case(["U95", "U940"], cid="b-t-001")
        self.assertFalse(c["first"]["exact"])
        self.assertEqual((c["first"]["extra"], c["first"]["optional_given"]), (1, 0))

    def test_optional_given_summed_in_groups(self):
        r = sc.score(self.gold, self.meta,
                     [row("b-t-001", ["U95"]), row("b-t-002", ["U910", "U96", "U940"],
                                                   ["U910", "U96"])],
                     checker_data=DATA)
        self.assertEqual(r["first"]["overall"]["optional_given"], 1)
        self.assertEqual(r["final"]["overall"]["optional_given"], 0)
        self.assertEqual(r["first"]["overall"]["exact"], 2)
        self.assertEqual(r["first"]["overall"]["precision"], 1.0)

    def test_findings_counted_on_the_answer_as_given(self):
        gold = json.loads(json.dumps(self.gold))
        gold["b-t-001"]["optional_codes"] = [{"code": "U90", "reason": "Invented."}]
        c, _ = self.case(["U95", "U90"], cid="b-t-001", gold=gold)
        self.assertTrue(c["first"]["exact"])
        self.assertEqual(c["first"]["findings"]["error"], 1)

    def test_optional_given_in_markdown(self):
        _, r = self.case(["U910", "U96", "U940"])
        md = sc.to_markdown(r)
        self.assertIn("Optional given", md)
        self.assertIn("U94.0", md)

    def test_oracle_returns_required_codes_only(self):
        fn = responders.oracle(self.dir)
        for c in load_cases(self.dir):
            reply = json.loads(fn([{"role": "user", "content": render_first(c)}]))
            self.assertEqual(reply, CASES[c["id"]][2])
            for code in OPTIONAL.get(c["id"], []):
                self.assertNotIn(code, reply)


class GoldHashTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir(self).path
        self.dir = make_data_dir(self.tmp)

    def expected(self):
        lines = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                        for p in sorted((self.dir / "gold").glob("*.json")))
        return hashlib.sha256(lines.encode("ascii")).hexdigest()

    def test_hash_over_gold_files(self):
        (self.dir / "gold" / "README.md").write_text("invented readme\n")
        self.assertEqual(sc.gold_sha256(self.dir), self.expected())

    def test_hash_changes_with_a_gold_file(self):
        before = sc.gold_sha256(self.dir)
        p = self.dir / "gold" / "b-t-001.json"
        p.write_text(p.read_text() + " ")
        self.assertNotEqual(sc.gold_sha256(self.dir), before)

    def test_main_records_hash_in_json_and_markdown(self):
        answers = self.tmp / "answers.jsonl"
        answers.write_text("".join(json.dumps(row(c, codes)) + "\n"
                                   for c, codes in (("b-t-001", ["U95"]),)))
        oj, om = self.tmp / "s.json", self.tmp / "s.md"
        sc.main(["--answers", str(answers), "--data-dir", str(self.dir),
                 "--out-json", str(oj), "--out-md", str(om)], checker_data=DATA)
        h = self.expected()
        self.assertEqual(json.loads(oj.read_text())["gold_sha256"], h)
        first_line = om.read_text().splitlines()[0]
        self.assertIn(f"Gold sha256: {h}", first_line)


if __name__ == "__main__":
    unittest.main()
