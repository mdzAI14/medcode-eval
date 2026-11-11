"""Tests for medcode_eval.run.dryrun on invented fixtures. No network and
no model."""

import json
import unittest
from pathlib import Path

from medcode_eval.run import dryrun, part_b, runner
from tests.part_b_fixture import CASES, TempDir, make_data_dir
from tests.test_run import probes, write_jsonl


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.root = TempDir(self).path
        self.data = make_data_dir(self.root)
        self.pf = self.root / "probes.jsonl"
        write_jsonl(self.pf, probes())
        self.out = self.root / "dry"
        self.raw = self.root / "raw.jsonl"
        write_jsonl(self.raw, [{"id": "a", "eval_count": 100}, {"id": "b", "eval_count": 300},
                               {"id": "c", "eval_count": None}])

    def go(self, **kw):
        kw.setdefault("reasoning_source", self.raw)
        return dryrun.dry_run(self.out, {"lite": self.pf}, self.data, **kw)

    def row(self, s, set_, condition=None):
        return next(r for r in s["rows"] if r["set"] == set_ and r["condition"] == condition)

    def test_part_a_counts(self):
        s = self.go()
        r = self.row(s, "part_a_lite")
        texts = [runner.render_prompt(p) for p in probes()]
        self.assertEqual(r["prompts"], 4)
        self.assertEqual(r["input_chars"], sum(len(t) for t in texts))
        self.assertEqual(r["input_tokens_est"], round(r["input_chars"] / 4))
        rows = read_jsonl(self.out / "part_a_lite.jsonl")
        self.assertEqual([x["prompt"] for x in rows], texts)

    def test_part_b_counts(self):
        s = self.go()
        texts = [part_b.render_first(c) for c in part_b.load_cases(self.data)]
        for cond in ("plain", "with_checker"):
            r = self.row(s, "part_b", cond)
            self.assertEqual(r["prompts"], len(CASES))
            self.assertEqual(r["input_chars"], sum(len(t) for t in texts))
            rows = read_jsonl(self.out / f"part_b_{cond}.jsonl")
            self.assertEqual([x["prompt"] for x in rows], texts)
        self.assertTrue((self.out / "part_b_prompts" / "b-t-001.txt").is_file())

    def test_suffix_applied(self):
        s = self.go(prompt_suffix="/no_think")
        rows = read_jsonl(self.out / "part_a_lite.jsonl")
        self.assertTrue(all(x["prompt"].endswith("\n/no_think") for x in rows))
        self.assertEqual(s["prompt_suffix"], "/no_think")

    def test_second_turn_upper_bound(self):
        s = self.go()
        r = self.row(s, "part_b", "with_checker")
        second = part_b.render_second_template_chars(dryrun.ASSUMED_FINDINGS_CHARS)
        b = r["second_turn_upper"]
        self.assertEqual(b["turns"], len(CASES))
        self.assertEqual(b["second_prompt_chars"], len(CASES) * second)
        self.assertEqual(b["history_chars"], r["input_chars"])
        self.assertEqual(b["assumed_findings_chars"], dryrun.ASSUMED_FINDINGS_CHARS)

    def test_reasoning_output_from_raw(self):
        s = self.go()
        self.assertEqual(s["output_assumptions"]["reasoning"]["tokens_per_answer"], 200)
        self.assertEqual(s["output_assumptions"]["reasoning"]["n"], 2)

    def test_reasoning_default_when_raw_missing(self):
        s = self.go(reasoning_source=self.root / "nope.jsonl")
        a = s["output_assumptions"]["reasoning"]
        self.assertEqual(a["tokens_per_answer"], dryrun.DEFAULT_REASONING_OUTPUT)
        self.assertIsNone(a["n"])

    def test_cost_rows(self):
        s = self.go()
        cost = {(c["model_kind"], c["row"]): c for c in s["cost"]}
        direct = dryrun.DIRECT_OUTPUT
        c = cost[("direct", "part_a_lite")]
        self.assertEqual(c["output_tokens"], 4 * direct["part_a"])
        self.assertEqual(c["input_tokens"], self.row(s, "part_a_lite")["input_tokens_est"])
        self.assertEqual(c["formula"], f"{c['input_tokens'] / 1e6:.6f} * P_in + "
                                       f"{c['output_tokens'] / 1e6:.6f} * P_out")
        w = cost[("reasoning", "part_b_with_checker")]
        self.assertEqual(w["output_tokens"], 2 * len(CASES) * 200)
        bound = self.row(s, "part_b", "with_checker")["second_turn_upper"]
        self.assertEqual(w["input_tokens"],
                         self.row(s, "part_b", "plain")["input_tokens_est"]
                         + round((bound["history_chars"] + bound["second_prompt_chars"]) / 4)
                         + len(CASES) * 200)
        p60 = cost[("direct", "part_b_plain_x60")]
        p = cost[("direct", "part_b_plain")]
        self.assertEqual(p60["input_tokens"], round(p["input_tokens"] * 60 / len(CASES)))
        self.assertEqual(p60["output_tokens"], 60 * direct["part_b"])

    def test_markdown_written(self):
        self.go()
        md = (self.out / "summary.md").read_text()
        self.assertIn("estimate", md)
        self.assertIn("P_in", md)
        self.assertIn("ICD-10-CM FY2027", md)
        json.loads((self.out / "summary.json").read_text())

    def test_no_backend_called(self):
        orig = runner.OllamaBackend

        def no_backend(*a, **k):
            raise AssertionError("a backend was built")
        runner.OllamaBackend = no_backend
        try:
            self.go()
        finally:
            runner.OllamaBackend = orig


if __name__ == "__main__":
    unittest.main()
