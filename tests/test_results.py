"""Tests for medcode_eval.results (ICD-10-CM FY2027).

The lenient reading and the prefix and listed-code classification are
tested on invented replies and invented findings (U9x codes, made up). The
--check tests alter a temporary copy of the tracked results/ folder; one
test runs --check on the tracked files themselves. No network and no model.
"""

import io
import json
import shutil
import unittest
from contextlib import redirect_stdout

from medcode_eval import results
from medcode_eval.part_a.generate import REPO_ROOT
from tests.part_b_fixture import TempDir


class LenientReadingTests(unittest.TestCase):
    def test_bold_code_with_prose(self):
        reply = "**U93.12** is the code for this.\n\nIt was added this year."
        self.assertEqual(results.lenient_token(reply), "U93.12")
        self.assertTrue(results.lenient_equal(reply, "U9312"))
        self.assertFalse(results.lenient_equal(reply, "U9311"))

    def test_other_marks_removed(self):
        self.assertEqual(results.lenient_token("_`U90.012A`_"), "U90.012A")

    def test_refusal(self):
        reply = ("I can't reliably give this code. I don't know it.\n\n"
                 "It may be near U93.12.")
        self.assertIsNone(results.lenient_token(reply))
        self.assertFalse(results.lenient_equal(reply, "U9312"))

    def test_code_in_the_middle_of_the_first_line(self):
        reply = "The best match is likely U96.1XXA for this description, but check."
        self.assertEqual(results.lenient_token(reply), "U96.1XXA")
        self.assertTrue(results.lenient_equal(reply, "U961XXA"))

    def test_no_code(self):
        self.assertIsNone(results.lenient_token("No such code exists in my data."))
        self.assertIsNone(results.lenient_token(""))
        self.assertIsNone(results.lenient_token(None))

    def test_first_non_empty_line_only_and_think_dropped(self):
        reply = "<think>U95 maybe</think>\n\n  \nI am not sure.\nU95"
        self.assertIsNone(results.lenient_token(reply))

    def test_token_boundaries(self):
        # part of a longer word or number is not a token
        self.assertIsNone(results.lenient_token("XU95 and 1U95"))
        self.assertEqual(results.lenient_token("Code: U95."), "U95")

    def test_refusal_pattern(self):
        self.assertTrue(results.opens_with_refusal("I can’t say"))
        self.assertTrue(results.opens_with_refusal("I can't say"))
        self.assertTrue(results.opens_with_refusal("I’m not sure"))
        self.assertTrue(results.opens_with_refusal("<think>x</think>\n I don’t know"))
        self.assertFalse(results.opens_with_refusal("U95. I can't be sure"))
        self.assertFalse(results.opens_with_refusal("I cannot say"))
        self.assertFalse(results.opens_with_refusal(None))


def nic(code, prefix):
    return {"rule": "not_in_code_set", "level": "error", "codes": [code],
            "details": {"longest_stored_prefix":
                        None if prefix is None else {"code": prefix, "billable": True}}}


def header(code, children):
    return {"rule": "header_not_billable", "level": "error", "codes": [code],
            "details": {"case": "more_specific_codes", "children": children,
                        "children_total": len(children)}}


class ClassificationTests(unittest.TestCase):
    def test_prefix(self):
        f = [nic("U93129", "U93.12")]
        self.assertTrue(results.is_prefix("U9312", f))
        self.assertFalse(results.is_prefix("U9311", f))
        self.assertFalse(results.is_prefix(None, f))
        self.assertFalse(results.is_prefix("U9312", [nic("U93129", None)]))
        self.assertFalse(results.is_prefix("U9312", [header("U931", ["U93.11", "U93.12"])]))

    def test_listed(self):
        f = [header("U931", ["U93.11", "U93.12"])]
        self.assertTrue(results.is_listed("U9312", f))
        self.assertFalse(results.is_listed("U931", f))
        self.assertFalse(results.is_listed(None, f))
        self.assertFalse(results.is_listed("U9312", [nic("U93129", "U93.12")]))

    def test_wrong_class(self):
        self.assertEqual(results.wrong_class(
            [header("U93", []), nic("U93", None)]), "not_in_code_set")
        self.assertEqual(results.wrong_class([header("U93", [])]), "header_not_billable")
        self.assertEqual(results.wrong_class(
            [{"rule": "manifestation_first", "level": "error"}]), "other_error")
        self.assertEqual(results.wrong_class(
            [{"rule": "excludes1_pair", "level": "review"}]), "no_error")
        self.assertEqual(results.wrong_class([]), "no_error")


def run_check(results_dir):
    out = io.StringIO()
    with redirect_stdout(out):
        code = results.main(["--check"], results_dir=results_dir)
    return code, out.getvalue()


class CheckTamperTests(unittest.TestCase):
    """--check on a temporary copy of the tracked results/ folder."""

    def setUp(self):
        self.dir = TempDir(self).path / "results"
        shutil.copytree(REPO_ROOT / "results", self.dir)

    def test_copy_passes(self):
        code, out = run_check(self.dir)
        self.assertEqual(code, 0, out)

    def test_altered_answer_fails(self):
        p = self.dir / "part_b" / "p612-b-plain-opus-5-5" / "answers.jsonl"
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
        rows[0]["final_answer"] = ["U95"]
        p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                     encoding="utf-8")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 1 part_b/p612-b-plain-opus-5-5", out)

    def test_altered_response_fails(self):
        p = self.dir / "part_a" / "p62-a-lite-opus-5-5-reader2" / "responses.jsonl"
        text = p.read_text(encoding="utf-8")
        rows = [json.loads(l) for l in text.splitlines()]
        rows[0]["response"] = "Z"
        p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                     encoding="utf-8")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 1 part_a/p62-a-lite-opus-5-5-reader2", out)

    def test_altered_score_fails(self):
        p = self.dir / "part_a" / "p65-a-changes-opus-5-5" / "score.json"
        s = json.loads(p.read_text(encoding="ascii"))
        s["overall"]["correct"] += 1
        p.write_text(json.dumps(s, sort_keys=True, indent=2) + "\n", encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2 part_a/p65-a-changes-opus-5-5", out)

    def test_altered_checker_score_fails(self):
        p = self.dir / "part_a" / "p615-a-d2c-checker-opus-5-5" / "score.md"
        p.write_text(p.read_text(encoding="ascii") + "\n", encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2 part_a/p615-a-d2c-checker-opus-5-5", out)

    def test_altered_results_md_fails(self):
        p = self.dir / "RESULTS.md"
        p.write_text(p.read_text(encoding="ascii").replace("147", "148", 1), encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 3 RESULTS.md", out)
        self.assertNotIn("FAIL 3 results.json", out)


class RealFilesTests(unittest.TestCase):
    def test_check_passes_on_tracked_files(self):
        code, out = run_check(REPO_ROOT / "results")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
