"""Tests for the Part B runner (medcode_eval.run.part_b) with the fake
backend and the invented checker fixture. No network and no model.
"""

import json
import unittest
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_b import responders
from medcode_eval.run import part_b, runner
from medcode_eval.run.part_b import (
    load_cases,
    load_prompts,
    parse_answer,
    render_findings,
    render_first,
    render_second,
    run,
    write_answers,
)
from medcode_eval.run.runner import FakeBackend
from tests.part_b_fixture import CASES, CODE_SET, TempDir, make_data_dir, make_refdata


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def setUpModule():
    global TMP, DATA
    import tempfile
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


PLAIN = (
    "Code set: ICD-10-CM FY2027 (October 1, 2026 release).\n"
    "Assign the ICD-10-CM diagnosis codes a professional coder would\n"
    "report for the encounter below. Include external cause codes\n"
    "where the note supports them. Do not assign procedure codes.\n"
    "List the codes in reporting order, with the first-listed code\n"
    "first.\n"
    "\n"
    "{note}\n"
    "\n"
    "Answer with a JSON list of codes only, for example\n"
    "[\"CODE1\", \"CODE2\"].\n")

SECOND = (
    "A rules checker compared your codes with the ICD-10-CM FY2027\n"
    "files and reported the findings below.\n"
    "An error finding means the code cannot be reported as written.\n"
    "A review finding points to a note in the code set that may or\n"
    "may not apply here: keep the code if the note does not apply to\n"
    "this encounter.\n"
    "\n"
    "{findings}\n"
    "\n"
    "Give your final answer as a JSON list of codes only.\n")


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.dir = make_data_dir(TempDir(self).path)

    def test_prompt_files_exact(self):
        p = load_prompts()
        self.assertEqual(p["plain"], PLAIN)
        self.assertEqual(p["checker"], SECOND)

    def test_part_a_prompt_files_untouched(self):
        self.assertEqual(set(runner.PROMPT_FILES), {"code_to_description",
                                                    "description_to_code", "status"})

    def test_note_is_text_after_front_matter(self):
        cases = {c["id"]: c for c in load_cases(self.dir)}
        self.assertEqual(sorted(cases), sorted(CASES))
        self.assertEqual(cases["b-t-001"]["note"],
                         "Invented note one.\nThe patient has invented condition U95.")

    def test_render_first(self):
        case = load_cases(self.dir)[1]
        text = render_first(case)
        self.assertEqual(text, PLAIN.format(note=case["note"]).rstrip("\n"))
        self.assertIn("Invented note two {with braces}.", text)
        self.assertNotIn("---", text)
        self.assertNotIn("specialty", text)

    def test_suffix_on_own_last_line(self):
        case = load_cases(self.dir)[0]
        self.assertEqual(render_first(case, prompt_suffix="/no_think"),
                         render_first(case) + "\n/no_think")
        with self.assertRaises(ValueError):
            render_first(case, prompt_suffix="a\nb")

    def test_hidden_fields_never_reach_backend(self):
        root = TempDir(self).path
        data = make_data_dir(root, sentinel=True)
        for c in load_cases(data):
            self.assertNotIn("SENTINEL", render_first(c))
        seen = []

        def fn(messages):
            seen.append(messages)
            return '["U90.012"]'   # a header: draws a second turn
        out = root / "run"
        run(data, out, FakeBackend(fn, messages=True), "with_checker", checker_data=DATA)
        self.assertEqual(len(seen), 2 * len(CASES))
        for messages in seen:
            for m in messages:
                self.assertNotIn("SENTINEL", m["content"])
                for cid in CASES:
                    self.assertNotIn(cid, m["content"])
        # the gold codes reach no prompt either
        for messages in seen:
            for m in messages:
                if m["role"] == "user":
                    self.assertNotIn("U90.012A", m["content"])
                    self.assertNotIn("U94.0", m["content"])


class FindingsLayoutTests(unittest.TestCase):
    def test_error_finding_block(self):
        f = checker.check(["U95", "U90.012"], data=DATA)
        self.assertEqual([x["rule"] for x in f], ["header_not_billable"])
        self.assertEqual(render_findings(f),
                         "Finding 1 of 1\n"
                         "Level: error\n"
                         "Rule: header_not_billable\n"
                         f"Message: {f[0]['message']}")

    def test_note_finding_block_has_note_text(self):
        f = checker.check(["U91.0", "U92.1", "U90.012"], data=DATA)
        rules = [x["rule"] for x in f]
        self.assertEqual(rules, ["header_not_billable", "excludes1_pair"])
        text = render_findings(f)
        blocks = text.split("\n\n")
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].startswith("Finding 1 of 2\nLevel: error\n"))
        self.assertNotIn("Note:", blocks[0])
        self.assertEqual(blocks[1].splitlines(), [
            "Finding 2 of 2", "Level: review", "Rule: excludes1_pair",
            f"Message: {f[1]['message']}", "Note: invented other (U92.1)"])

    def test_render_second(self):
        f = checker.check(["U90.012"], data=DATA)
        self.assertEqual(render_second(f),
                         SECOND.format(findings=render_findings(f)).rstrip("\n"))
        self.assertEqual(render_second(f, prompt_suffix="/no_think"),
                         render_second(f) + "\n/no_think")


class ParseAnswerTests(unittest.TestCase):
    def test_plain_list(self):
        self.assertEqual(parse_answer('["U90.012A", "u95"]'), ["U90012A", "U95"])

    def test_think_dropped(self):
        self.assertEqual(parse_answer('<think>["U96"]</think>\n["U95"]'), ["U95"])
        self.assertIsNone(parse_answer('<think>["U96"] and never closed'))

    def test_last_list_taken(self):
        self.assertEqual(parse_answer('First ["U96"], then:\n```json\n["U95", "U91.0"]\n```'),
                         ["U95", "U910"])

    def test_nested_list_is_one_list(self):
        self.assertIsNone(parse_answer('[["U95"]]'))

    def test_non_string_items_invalid(self):
        self.assertIsNone(parse_answer('["U95", 3]'))
        self.assertIsNone(parse_answer('["U95", null]'))

    def test_empty_string_item_invalid(self):
        self.assertIsNone(parse_answer('["U95", "  "]'))

    def test_no_list_invalid(self):
        self.assertIsNone(parse_answer("U95, U96"))
        self.assertIsNone(parse_answer('{"codes": "U95"}'))
        self.assertIsNone(parse_answer(""))
        self.assertIsNone(parse_answer(None))

    def test_broken_json_ignored_for_an_earlier_list(self):
        self.assertEqual(parse_answer('["U95"] and then [U96'), ["U95"])

    def test_empty_list_is_valid(self):
        self.assertEqual(parse_answer("[]"), [])

    def test_normalised_as_checker(self):
        for raw in ("U90.012A", " u90.012a ", "U90012A"):
            self.assertEqual(parse_answer(json.dumps([raw])), [checker.normalise(raw)])
        # a dot elsewhere is kept, as the checker keeps it
        self.assertEqual(parse_answer('["U9.0012A"]'), ["U9.0012A"])

    def test_order_and_duplicates_kept(self):
        self.assertEqual(parse_answer('["U96", "U95", "U96"]'), ["U96", "U95", "U96"])


class RunTests(unittest.TestCase):
    def setUp(self):
        root = TempDir(self).path
        self.data = make_data_dir(root)
        self.out = root / "runs" / "r1"
        self.cases = load_cases(self.data)

    def oracle(self):
        return FakeBackend(responders.oracle(self.data), messages=True)

    def wrong(self, answer=("U90.012",)):
        return FakeBackend(responders.fixed(list(answer)), messages=True)

    def test_plain_one_turn(self):
        seen = []
        backend = FakeBackend(lambda m: seen.append(m) or '["U95"]', messages=True)
        run(self.data, self.out, backend, "plain", checker_data=DATA)
        self.assertEqual(len(seen), 3)
        for m in seen:
            self.assertEqual(len(m), 1)
            self.assertEqual(m[0]["role"], "user")
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["condition"], "plain")
        self.assertEqual(meta["code_set"], CODE_SET)
        self.assertEqual(meta["backend"], "fake")
        self.assertEqual(sorted(meta["cases_sha256"]), sorted(CASES))
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual([(r["id"], r["turn"]) for r in raw],
                         [(c, 1) for c in sorted(CASES)])
        ans = read_jsonl(self.out / "answers.jsonl")
        self.assertEqual(len(ans), 3)
        for a in ans:
            self.assertEqual(a["first_answer"], ["U95"])
            self.assertEqual(a["final_answer"], ["U95"])
            self.assertFalse(a["second_turn"])

    def test_plain_never_checks_even_with_findings(self):
        run(self.data, self.out, self.wrong(), "plain", checker_data=DATA)
        self.assertEqual({r["turn"] for r in read_jsonl(self.out / "raw.jsonl")}, {1})

    def test_with_checker_no_finding_no_second_turn(self):
        run(self.data, self.out, self.oracle(), "with_checker", checker_data=DATA)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual({r["turn"] for r in raw}, {1})
        for a in read_jsonl(self.out / "answers.jsonl"):
            self.assertFalse(a["second_turn"])
            self.assertEqual(a["first_answer"], a["final_answer"])
            gold = [checker.normalise(c) for c in CASES[a["id"]][2]]
            self.assertEqual(a["final_answer"], gold)

    def test_with_checker_finding_second_turn_once(self):
        seen = []
        replies = iter(['<think>hmm</think>\n["U90.012"]', '["U90.012A"]'] * 3)

        def fn(messages):
            seen.append(messages)
            return next(replies)
        run(self.data, self.out, FakeBackend(fn, messages=True), "with_checker",
            checker_data=DATA)
        self.assertEqual(len(seen), 6)
        first, second = seen[0], seen[1]
        self.assertEqual(len(first), 1)
        self.assertEqual([m["role"] for m in second], ["user", "assistant", "user"])
        self.assertEqual(second[0], first[0])
        # the reply is resent with its think block dropped; raw.jsonl keeps it
        self.assertEqual(second[1]["content"], '\n["U90.012"]')
        self.assertEqual(second[1]["content"], runner.drop_think(
            '<think>hmm</think>\n["U90.012"]'))
        findings = checker.check(["U90.012"], data=DATA)
        self.assertEqual(second[2]["content"], render_second(findings))
        raw = read_jsonl(self.out / "raw.jsonl")
        t2 = [r for r in raw if r["turn"] == 2]
        self.assertEqual(len(t2), 3)
        self.assertEqual([r["raw"] for r in raw if r["turn"] == 1],
                         ['<think>hmm</think>\n["U90.012"]'] * 3)
        self.assertEqual(t2[0]["findings"], json.loads(json.dumps(findings)))
        for r in raw:
            if r["turn"] == 1:
                self.assertNotIn("findings", r)
        for a in read_jsonl(self.out / "answers.jsonl"):
            self.assertTrue(a["second_turn"])
            self.assertEqual(a["first_answer"], ["U90012"])
            self.assertEqual(a["final_answer"], ["U90012A"])

    def test_never_a_third_turn(self):
        calls = []
        backend = FakeBackend(lambda m: calls.append(m) or '["U90.012"]', messages=True)
        run(self.data, self.out, backend, "with_checker", checker_data=DATA)
        self.assertEqual(len(calls), 6)
        self.assertEqual(max(len(m) for m in calls), 3)
        for a in read_jsonl(self.out / "answers.jsonl"):
            self.assertEqual(a["final_answer"], ["U90012"])

    def test_invalid_first_answer_no_second_turn(self):
        run(self.data, self.out, FakeBackend(lambda m: "U90.012", messages=True),
            "with_checker", checker_data=DATA)
        self.assertEqual({r["turn"] for r in read_jsonl(self.out / "raw.jsonl")}, {1})
        for a in read_jsonl(self.out / "answers.jsonl"):
            self.assertIsNone(a["first_answer"])
            self.assertFalse(a["first_valid"])
            self.assertFalse(a["second_turn"])

    def test_findings_on_codes_in_order_given(self):
        # U92.0 listed after U91.1 matches U91.1's codeFirst note: a finding
        seen = []
        backend = FakeBackend(lambda m: seen.append(m) or '["U91.1", "U92.0"]', messages=True)
        run(self.data, self.out, backend, "with_checker", ids=["b-t-001"], checker_data=DATA)
        t2 = [r for r in read_jsonl(self.out / "raw.jsonl") if r["turn"] == 2]
        self.assertEqual([f["rule"] for f in t2[0]["findings"]],
                         [f["rule"] for f in checker.check(["U91.1", "U92.0"], data=DATA)])
        self.assertIn("code_first_order", [f["rule"] for f in t2[0]["findings"]])

    def test_resume_per_case_and_turn(self):
        calls = []

        def fn(messages):
            calls.append(len(messages))
            if len(messages) == 3 and len(calls) == 2:
                raise KeyboardInterrupt  # interrupted before turn 2 is stored
            return '["U90.012"]'
        with self.assertRaises(KeyboardInterrupt):
            run(self.data, self.out, FakeBackend(fn, messages=True), "with_checker",
                checker_data=DATA)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual([(r["id"], r["turn"]) for r in raw], [("b-t-001", 1)])
        calls.clear()
        run(self.data, self.out, self.wrong(), "with_checker", checker_data=DATA)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(sorted((r["id"], r["turn"]) for r in raw),
                         sorted((c, t) for c in CASES for t in (1, 2)))
        n = len(raw)
        run(self.data, self.out, self.wrong(), "with_checker", checker_data=DATA)
        self.assertEqual(len(read_jsonl(self.out / "raw.jsonl")), n)

    def test_incomplete_case_left_out_of_answers(self):
        def fn(messages):
            if len(messages) == 3:
                raise KeyboardInterrupt
            return '["U90.012"]'
        with self.assertRaises(KeyboardInterrupt):
            run(self.data, self.out, FakeBackend(fn, messages=True), "with_checker",
                checker_data=DATA)
        write_answers(self.out, checker_data=DATA)
        self.assertEqual(read_jsonl(self.out / "answers.jsonl"), [])

    def test_limit_counts_cases(self):
        n = run(self.data, self.out, self.wrong(), "with_checker", limit=2, checker_data=DATA)
        self.assertEqual(n, 2)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(len({r["id"] for r in raw}), 2)
        self.assertEqual(len(raw), 4)

    def test_error_recorded(self):
        def fn(messages):
            raise TimeoutError("timed out")
        run(self.data, self.out, FakeBackend(fn, messages=True), "with_checker",
            checker_data=DATA)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(len(raw), 3)
        for r in raw:
            self.assertIn("timed out", r["error"])
            self.assertIsNone(r["raw"])
        for a in read_jsonl(self.out / "answers.jsonl"):
            self.assertIsNone(a["final_answer"])
            self.assertIn("timed out", a["error"])

    def test_resume_refuses_other_condition(self):
        run(self.data, self.out, self.wrong(), "plain", limit=1, checker_data=DATA)
        with self.assertRaises(ValueError) as cm:
            run(self.data, self.out, self.wrong(), "with_checker", checker_data=DATA)
        self.assertIn("condition", str(cm.exception))

    def test_resume_refuses_changed_case(self):
        run(self.data, self.out, self.wrong(), "plain", limit=1, checker_data=DATA)
        p = self.data / "cases" / "b-t-002.md"
        p.write_text(p.read_text() + "more\n")
        with self.assertRaises(ValueError):
            run(self.data, self.out, self.wrong(), "plain", checker_data=DATA)

    def test_unknown_condition(self):
        with self.assertRaises(ValueError):
            run(self.data, self.out, self.wrong(), "other", checker_data=DATA)

    def test_unknown_id(self):
        with self.assertRaises(ValueError):
            run(self.data, self.out, self.wrong(), "plain", ids=["nope"], checker_data=DATA)


class RederiveTests(unittest.TestCase):
    def setUp(self):
        self.root = TempDir(self).path
        self.data = make_data_dir(self.root)
        self.out = self.root / part_b.RUNS_DIR / "r1"
        run(self.data, self.out, FakeBackend(responders.fixed(["U90.012"]), messages=True),
            "with_checker", checker_data=DATA)
        (self.out / "answers.jsonl").write_text("stale\n")
        self.raw = (self.out / "raw.jsonl").read_bytes()
        self.meta = (self.out / "run.json").read_bytes()

    def test_rederive_no_backend(self):
        def no_backend(*a, **k):
            raise AssertionError("a backend was built")
        orig = (runner.REPO_ROOT, runner.OllamaBackend, part_b.REPO_ROOT)
        runner.REPO_ROOT = part_b.REPO_ROOT = self.root
        runner.OllamaBackend = no_backend
        orig_default = checker.default_data
        checker.default_data = lambda: DATA
        try:
            runner.main(["--part", "b", "--run-id", "r1", "--rederive"])
        finally:
            runner.REPO_ROOT, runner.OllamaBackend, part_b.REPO_ROOT = orig
            checker.default_data = orig_default
        ans = read_jsonl(self.out / "answers.jsonl")
        self.assertEqual(len(ans), 3)
        self.assertTrue(all(a["second_turn"] for a in ans))
        self.assertEqual((self.out / "raw.jsonl").read_bytes(), self.raw)
        self.assertEqual((self.out / "run.json").read_bytes(), self.meta)

    def test_condition_required_without_rederive(self):
        with self.assertRaises(SystemExit):
            runner.main(["--part", "b", "--run-id", "r2"])


class ResponderTests(unittest.TestCase):
    def test_oracle_returns_gold_for_the_note(self):
        data = make_data_dir(TempDir(self).path)
        fn = responders.oracle(data)
        for c in load_cases(data):
            reply = fn([{"role": "user", "content": render_first(c)}])
            self.assertEqual(json.loads(reply), CASES[c["id"]][2])

    def test_oracle_unknown_note(self):
        data = make_data_dir(TempDir(self).path)
        with self.assertRaises(ValueError):
            responders.oracle(data)([{"role": "user", "content": "no case here"}])

    def test_fixed(self):
        self.assertEqual(json.loads(responders.fixed(["X1"])([])), ["X1"])
        self.assertEqual(responders.WRONG, ["S52.501"])


if __name__ == "__main__":
    unittest.main()
