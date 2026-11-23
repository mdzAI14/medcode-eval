"""Tests for the Part C side of medcode_eval.results.
Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Built like the tamper tests in tests/test_results.py: each test works on a
temporary copy of the tracked results/ folder and alters it. No network and
no model.
"""

import io
import json
import shutil
import unittest
from contextlib import redirect_stdout

from medcode_eval import results
from medcode_eval.part_a.generate import REPO_ROOT
from tests.part_b_fixture import TempDir

PLAIN = "p101-c-plain-opus-5-5"
REPEAT = "p101-c-reminded2-opus-5-5"
REPORTED = ("p101-c-plain-opus-5-5", "p101-c-plain-qwen3-4b",
            "p101-c-reminded-opus-5-5", "p101-c-reminded-qwen3-4b",
            "p101-c-checker-opus-5-5", "p101-c-checker-qwen3-4b")
PART_C_SECTIONS = ("## S9. Part C reported runs", "## S10. Part C", "## S11. Part C per case",
                   "## S12. Part C derived", "## S13. Part C usage and cost")
OLD_KEYS = ("code_set", "S0_runs", "S1_part_a_lite", "S2_part_a_changes",
            "S3_checker_on_part_a_answers", "S4_part_a_checker_condition", "S5_part_b",
            "S6_part_b_cases", "S7_part_b_derived", "S8_usage")


def run_check(results_dir):
    out = io.StringIO()
    with redirect_stdout(out):
        code = results.main(["--check"], results_dir=results_dir)
    return code, out.getvalue()


def section(md, heading):
    """The text of one section of RESULTS.md, from its heading to the next
    "## " heading."""
    start = md.index(heading + "\n")
    nxt = md.find("\n## ", start + len(heading))
    return md[start:] if nxt < 0 else md[start:nxt + 1]


def rewrite_jsonl(path, change):
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    change(rows)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                    encoding="utf-8")


class PartCCheckTests(unittest.TestCase):
    """--check on a temporary copy of the tracked results/ folder."""

    def setUp(self):
        self.dir = TempDir(self).path / "results"
        shutil.copytree(REPO_ROOT / "results", self.dir)

    def test_copy_passes_and_covers_part_c(self):
        code, out = run_check(self.dir)
        self.assertEqual(code, 0, out)
        lines = out.splitlines()
        for num in (1, 2):
            for run in REPORTED:
                self.assertIn(f"ok {num} part_c/{run}", lines)
            self.assertIn(f"ok {num} part_c/repeat/{REPEAT}", lines)
        self.assertEqual(len(lines), 35, out)
        self.assertEqual(lines[-1], "checks failed: 0")

    def test_altered_answers_fail_check_1(self):
        def change(rows):
            rows[0]["first_answer"] = ["U95"]
        rewrite_jsonl(self.dir / "part_c" / PLAIN / "answers.jsonl", change)
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn(f"FAIL 1 part_c/{PLAIN}", out)

    def test_altered_score_fails_check_2(self):
        p = self.dir / "part_c" / PLAIN / "score.json"
        s = json.loads(p.read_text(encoding="ascii"))
        s["first"]["overall"]["exact"] += 1
        p.write_text(json.dumps(s, sort_keys=True, indent=2) + "\n", encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn(f"FAIL 2 part_c/{PLAIN}", out)
        self.assertNotIn(f"FAIL 1 part_c/{PLAIN}", out)

    def test_altered_repeat_fails(self):
        p = self.dir / "part_c" / "repeat" / REPEAT / "score.md"
        p.write_text(p.read_text(encoding="ascii") + "\n", encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn(f"FAIL 2 part_c/repeat/{REPEAT}", out)

    def test_altered_repeat_answers_fail(self):
        def change(rows):
            rows[0]["final_answer"] = ["U95"]
        rewrite_jsonl(self.dir / "part_c" / "repeat" / REPEAT / "answers.jsonl", change)
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn(f"FAIL 1 part_c/repeat/{REPEAT}", out)

    def test_altered_results_md_fails_check_3(self):
        p = self.dir / "RESULTS.md"
        md = p.read_text(encoding="ascii")
        s9 = md.index("## S9. Part C reported runs")
        p.write_text(md[:s9] + md[s9:].replace(PLAIN, PLAIN + "x", 1), encoding="ascii")
        code, out = run_check(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 3 RESULTS.md", out)
        self.assertNotIn("FAIL 3 results.json", out)


class PartCFigureTests(unittest.TestCase):
    def setUp(self):
        self.dir = TempDir(self).path / "results"
        shutil.copytree(REPO_ROOT / "results", self.dir)

    def test_repeat_not_in_reported_figures(self):
        fig = results.figures(self.dir)
        self.assertEqual(sorted(d["run"] for d in fig["S10_part_c"]), sorted(REPORTED))
        self.assertEqual(sorted(d["run"] for d in fig["S11_part_c_cases"]), sorted(REPORTED))
        self.assertNotIn(REPEAT, json.dumps(fig["S10_part_c"]))
        self.assertNotIn(REPEAT, json.dumps(fig["S11_part_c_cases"]))
        md = results.to_markdown(fig)
        for heading in ("## S10. Part C", "## S11. Part C per case"):
            self.assertNotIn(REPEAT, section(md, heading))

    def test_repeat_labelled_where_it_appears(self):
        fig = results.figures(self.dir)
        md = results.to_markdown(fig)
        for heading in ("## S9. Part C reported runs", "## S12. Part C derived",
                        "## S13. Part C usage and cost"):
            text = section(md, heading)
            hits = [l for l in text.splitlines() if REPEAT in l]
            self.assertTrue(hits, heading)
            for line in hits:
                self.assertIn("repeat", line.replace(REPEAT, ""), (heading, line))
        s9 = [r for r in fig["S9_part_c_runs"] if r["run"] == REPEAT]
        self.assertEqual(len(s9), 1)
        self.assertTrue(s9[0]["repeat"])
        self.assertIn("not a reported score", s9[0]["what"])
        self.assertTrue(all(not r["repeat"] for r in fig["S9_part_c_runs"]
                            if r["run"] != REPEAT))
        s13 = {u["run"]: u for u in fig["S13_part_c_usage"]}
        self.assertTrue(s13[REPEAT]["repeat"])
        opus = [d for d in fig["S12_part_c_derived"] if d["model"] == "claude-opus-5-5"]
        self.assertEqual(opus[0]["runs"]["repeat"], REPEAT)
        self.assertIn("not a reported score", opus[0]["repeat_figures"]["label"])

    def test_without_part_c(self):
        with_c = results.figures(self.dir)
        shutil.rmtree(self.dir / "part_c")
        without = results.figures(self.dir)
        for k in OLD_KEYS:
            self.assertEqual(without[k], with_c[k], k)
        md = results.to_markdown(without)
        for heading in PART_C_SECTIONS:
            self.assertEqual(section(md, heading).strip(), heading + "\n\nNo runs.")
        for k in ("S9_part_c_runs", "S10_part_c", "S11_part_c_cases", "S12_part_c_derived",
                  "S13_part_c_usage"):
            self.assertEqual(without[k], [], k)
        md_with = results.to_markdown(with_c)
        self.assertEqual(md[:md.index("## S9.")], md_with[:md_with.index("## S9.")])

    def test_unknown_condition_raises(self):
        p = self.dir / "part_c" / PLAIN / "run.json"
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta["condition"] = "shouted"
        p.write_text(json.dumps(meta), encoding="utf-8")
        with self.assertRaises(ValueError):
            results.load_part_c_runs(self.dir)
        with self.assertRaises(ValueError):
            results.figures(self.dir)

    def test_wrong_part_raises(self):
        p = self.dir / "part_c" / "repeat" / REPEAT / "run.json"
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta["part"] = "b"
        p.write_text(json.dumps(meta), encoding="utf-8")
        with self.assertRaises(ValueError):
            results.load_part_c_runs(self.dir)


if __name__ == "__main__":
    unittest.main()
