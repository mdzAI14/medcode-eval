"""Tests for the Part A checker condition (medcode_eval.run.part_a_checker)
on invented fixtures: the U9x checker fixture of tests/test_checker.py, an
invented probe file and a source run made by the Part A runner with a fake
backend. No network and no model.
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a import score as part_a_score
from medcode_eval.run import part_a_checker as pac
from medcode_eval.run import part_b, runner, spend
from medcode_eval.run.runner import FakeBackend, drop_think
from tests.part_b_fixture import CODE_SET, TempDir, make_refdata
from tests.test_remote import MeteredFake

PROMPT = (
    "A rules checker compared your code with the ICD-10-CM FY2027\n"
    "files and reported the finding below.\n"
    "An error finding means the code cannot be reported as written.\n"
    "\n"
    "{findings}\n"
    "\n"
    "Give your final answer with the code only.\n")


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def probe(pid, answer, description, type_="description_to_code"):
    p = {"id": pid, "type": type_, "answer": answer, "chapter": 1,
         "change": "added_billable", "code_set": CODE_SET, "origin": "invented fixture"}
    if type_ == "status":
        p["code"] = answer
        p["answer"] = "billable"
    else:
        p["description"] = description
    return p


# id -> (gold, description, first reply, second reply or None)
ITEMS = {
    "d-1": ("U95", "Invented desc one", "U95", None),                  # no finding
    "d-2": ("U90012A", "Invented desc two", "<think>hm</think>U90.012",  # header
            "<think>again</think>\nU90.012A"),
    "d-3": ("U930", "Invented desc three", "U93.9", "U93.1"),          # not in set, prefix
    "d-4": ("U920", "Invented desc four", "Z9999", "U94"),             # not in set, no prefix
    "d-5": ("U920", "Invented desc five", "U91.1", None),              # manifestation only
    "d-6": ("U95", "Invented desc six", "I do not know", None),        # no code read
    "d-7": ("U96", "Invented desc seven", "U96.5", "U96.5"),           # same as first
    "d-8": ("U940", "Invented desc eight", "U94", "no idea at all"),    # header, final invalid
}
SECOND_TURN = ["d-2", "d-3", "d-4", "d-7", "d-8"]


def first_fn(text):
    for gold, desc, first, _ in ITEMS.values():
        if desc in text:
            return first
    return "billable"  # the status probe


def second_fn(messages):
    for gold, desc, _, second in ITEMS.values():
        if desc in messages[0]["content"]:
            return second
    raise AssertionError("unknown probe")


def setUpModule():
    global TMP, DATA
    import tempfile
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


class Base(unittest.TestCase):
    suffix = ""
    reader = 2

    def setUp(self):
        self.root = TempDir(self).path
        self.probes = [probe(k, v[0], v[1]) for k, v in ITEMS.items()]
        self.probes.insert(3, probe("s-1", "U95", None, type_="status"))
        self.pf = self.root / "probes.jsonl"
        self.pf.write_text("".join(json.dumps(p) + "\n" for p in self.probes))
        self.src = self.root / "runs" / "src"
        runner.run(self.pf, self.src, FakeBackend(first_fn), prompt_suffix=self.suffix,
                   reader=self.reader)
        self.out = self.root / "runs" / "chk"

    def backend(self, fn=second_fn):
        return FakeBackend(fn, messages=True)

    def go(self, backend=None, **kw):
        return pac.run(self.src, self.out, backend or self.backend(), checker_data=DATA,
                       root=self.root, **kw)

    def answers(self):
        return {r["id"]: r for r in read_jsonl(self.out / "answers.jsonl")}


class PromptFileTests(unittest.TestCase):
    def test_prompt_file_bytes(self):
        raw = (runner.PROMPT_DIR / "part_a_checker.txt").read_bytes()
        self.assertEqual(raw, PROMPT.encode("ascii"))
        self.assertEqual(pac.load_prompt(), PROMPT)
        lines = raw.decode("ascii").split("\n")
        self.assertEqual(len(lines), 8)          # 7 lines and the final newline
        self.assertEqual(lines[7], "")
        self.assertTrue(lines[2].endswith("written."))
        self.assertEqual((lines[3], lines[5]), ("", ""))

    def test_rules(self):
        self.assertEqual(pac.RULES, ("not_in_code_set", "header_not_billable"))

    def test_runner_prompt_files_unchanged(self):
        self.assertEqual(runner.PROMPT_FILES, {
            "code_to_description": "part_a_code_to_description.txt",
            "description_to_code": "part_a_description_to_code.txt",
            "status": "part_a_status.txt"})
        self.assertEqual(set(runner.load_prompts()), set(runner.PROMPT_FILES))


class RunnerStillThreePromptsTests(Base):
    def test_part_a_run_records_the_same_three_prompt_files(self):
        meta = json.loads((self.src / "run.json").read_text())
        self.assertEqual(set(meta["prompts_sha256"]), {
            "part_a_code_to_description.txt", "part_a_description_to_code.txt",
            "part_a_status.txt"})


class BranchTests(Base):
    def test_branches(self):
        calls = []

        def fn(messages):
            calls.append(messages)
            return second_fn(messages)
        self.go(self.backend(fn))
        a = self.answers()
        # only description_to_code probes
        self.assertEqual(sorted(a), sorted(ITEMS))
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(sorted(r["id"] for r in raw), sorted(SECOND_TURN))
        self.assertEqual(len(calls), len(SECOND_TURN))
        # B.3: no code read
        self.assertEqual(a["d-6"]["first_answer"], None)
        self.assertFalse(a["d-6"]["first_valid"])
        self.assertFalse(a["d-6"]["second_turn"])
        self.assertEqual(a["d-6"]["final_answer"], None)
        self.assertFalse(a["d-6"]["final_valid"])
        # B.4: no finding
        self.assertEqual(a["d-1"]["rules"], [])
        self.assertFalse(a["d-1"]["second_turn"])
        self.assertEqual(a["d-1"]["final_answer"], "U95")
        # B.4: only another rule; never sent
        self.assertEqual(a["d-5"]["rules"], ["manifestation_first"])
        self.assertFalse(a["d-5"]["second_turn"])
        self.assertEqual(a["d-5"]["final_answer"], "U911")
        self.assertTrue(a["d-5"]["final_valid"])
        # B.5: a finding
        self.assertEqual(a["d-2"]["rules"], ["header_not_billable"])
        self.assertTrue(a["d-2"]["second_turn"])
        self.assertEqual(a["d-2"]["first_answer"], "U90012")
        self.assertEqual(a["d-2"]["final_answer"], "U90012A")
        self.assertEqual(a["d-3"]["rules"], ["not_in_code_set"])
        self.assertEqual(a["d-4"]["rules"], ["not_in_code_set"])
        self.assertEqual(a["d-8"]["final_answer"], None)
        self.assertFalse(a["d-8"]["final_valid"])
        for r in a.values():
            self.assertIsNone(r["error"])

    def test_three_messages_exact(self):
        seen = {}

        def fn(messages):
            seen[messages[0]["content"]] = messages
            return second_fn(messages)
        self.go(self.backend(fn))
        p = next(x for x in self.probes if x["id"] == "d-2")
        first_text = runner.render_prompt(p)
        self.assertEqual(first_text, runner.load_prompts()["description_to_code"]
                         .format(description="Invented desc two").rstrip("\n"))
        msgs = seen[first_text]
        f = checker.check(["U90012"], data=DATA)
        self.assertEqual([x["rule"] for x in f], ["header_not_billable"])
        self.assertEqual(msgs, [
            {"role": "user", "content": first_text},
            {"role": "assistant", "content": "U90.012"},
            {"role": "user",
             "content": PROMPT.format(findings=part_b.render_findings(f)).rstrip("\n")},
        ])
        self.assertTrue(msgs[2]["content"].endswith("Give your final answer with the code only."))
        raw = {r["id"]: r for r in read_jsonl(self.out / "raw.jsonl")}
        self.assertEqual(raw["d-2"]["findings"], f)
        self.assertEqual(raw["d-2"]["turn"], 2)

    def test_message_names_stored_prefix_or_none(self):
        self.go()
        raw = {r["id"]: r for r in read_jsonl(self.out / "raw.jsonl")}
        self.assertIn("longest stored prefix is U93", raw["d-3"]["findings"][0]["message"])
        self.assertIn("no stored code is a prefix", raw["d-4"]["findings"][0]["message"])

    def test_only_the_two_rules_are_sent(self):
        self.go()
        for r in read_jsonl(self.out / "raw.jsonl"):
            self.assertTrue(r["findings"])
            self.assertTrue(all(f["rule"] in pac.RULES for f in r["findings"]))

    def test_no_third_turn(self):
        calls = []

        def fn(messages):
            calls.append(len(messages))
            return "U99999"   # a final answer that still draws a finding
        self.go(self.backend(fn))
        self.assertEqual(calls, [3] * len(SECOND_TURN))
        self.go(self.backend(fn))
        self.assertEqual(calls, [3] * len(SECOND_TURN))
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(len(raw), len(SECOND_TURN))
        self.assertEqual({r["turn"] for r in raw}, {2})

    def test_run_json(self):
        self.go()
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["code_set"], CODE_SET)
        self.assertEqual(meta["source_run"], "runs/src")
        self.assertEqual(meta["source_raw_sha256"], runner._sha(self.src / "raw.jsonl"))
        self.assertEqual(meta["source_responses_sha256"],
                         runner._sha(self.src / "responses.jsonl"))
        self.assertEqual(meta["probes_file"], "probes.jsonl")
        self.assertEqual(meta["probes_sha256"], runner._sha(self.pf))
        self.assertEqual(meta["prompts_sha256"], {
            "part_a_description_to_code.txt":
                runner._sha(runner.PROMPT_DIR / "part_a_description_to_code.txt"),
            "part_a_checker.txt": runner._sha(runner.PROMPT_DIR / "part_a_checker.txt")})
        self.assertEqual(meta["rules"], list(pac.RULES))
        self.assertEqual(meta["checker"]["order_file"], DATA.order_file)
        self.assertEqual(meta["checker"]["tabular_file"], DATA.tabular_file)
        self.assertEqual(meta["backend"], "fake")
        self.assertEqual(meta["model"], "fake")
        self.assertEqual(meta["reader"], 2)
        self.assertIsNone(meta["spend"])

    def test_error_recorded(self):
        def fn(messages):
            raise OSError("invented failure")
        self.go(self.backend(fn))
        a = self.answers()
        self.assertTrue(a["d-2"]["second_turn"])
        self.assertIsNone(a["d-2"]["final_answer"])
        self.assertIn("invented failure", a["d-2"]["error"])

    def test_refuses_source_as_output(self):
        with self.assertRaises(ValueError):
            pac.run(self.src, self.src, self.backend(), checker_data=DATA, root=self.root)


class SuffixTests(Base):
    suffix = "/no_think"

    def test_suffix_on_both_user_turns(self):
        seen = []

        def fn(messages):
            seen.append(messages)
            return second_fn(messages)
        self.go(self.backend(fn))
        self.assertEqual(len(seen), len(SECOND_TURN))
        for m in seen:
            self.assertTrue(m[0]["content"].endswith("\n/no_think"))
            self.assertTrue(m[2]["content"].endswith(
                "Give your final answer with the code only.\n/no_think"))
            self.assertNotIn("/no_think", m[1]["content"])


class ReaderOneTests(Base):
    reader = 1

    def test_source_reader_is_used(self):
        def fn(messages):
            return "U90.012A\nthat is my answer"
        self.go(self.backend(fn))
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["reader"], 1)
        a = self.answers()
        # reader 1 reads the last line only: invalid
        self.assertIsNone(a["d-2"]["final_answer"])


class ReaderTwoTests(Base):
    def test_source_reader_is_used(self):
        def fn(messages):
            return "U90.012A\nthat is my answer"
        self.go(self.backend(fn))
        self.assertEqual(self.answers()["d-2"]["final_answer"], "U90012A")


class RefusalTests(Base):
    def assert_refused(self, backend=None, regex="", **kw):
        with self.assertRaisesRegex(ValueError, regex):
            self.go(backend, **kw)
        self.assertFalse(self.out.exists())

    def test_missing_files(self):
        for name in ("run.json", "raw.jsonl", "responses.jsonl"):
            with self.subTest(name=name):
                p = self.src / name
                keep = p.read_bytes()
                p.unlink()
                self.assert_refused(regex=name)
                p.write_bytes(keep)

    def test_probes_sha_differs(self):
        self.pf.write_text(self.pf.read_text() + "\n")
        self.assert_refused(regex="probes_sha256")

    def test_probe_lacks_raw_row(self):
        rows = read_jsonl(self.src / "raw.jsonl")
        (self.src / "raw.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows if r["id"] != "d-6"))
        self.assert_refused(regex="d-6")

    def test_model_differs(self):
        self.assert_refused(FakeBackend(second_fn, model="other", messages=True),
                            regex="model")

    def test_settings_differ(self):
        b = self.backend()
        b.describe = lambda: {"backend": "fake", "model": "fake", "model_digest": None,
                              "server_version": None, "settings": {"x": 1}}
        self.assert_refused(b, regex="settings")

    def test_remote_needs_ledger(self):
        b = runner.RemoteBackend("fake", "ANTHROPIC_API_KEY", effort="medium",
                                 max_tokens=10, transport=lambda *a: self.fail("sent"))
        self.assert_refused(b, regex="ledger")


class StopResumeTests(Base):
    def test_stop_and_resume(self):
        lpath = self.root / "spend" / "l.jsonl"
        b = MeteredFake(second_fn, out_tokens=10, max_tokens=20, messages=True)
        # room for exactly one request at the worst case
        sizes = [spend.request_chars(m) for m in
                 (pac.messages_for(self.src_obj(), i) for i in self.planned())]
        cap = (sizes[0] / 3 + 20) + 1e-9
        # the first request fits the cap; once paid, the next one does not
        self.go(b, ledger=spend.Ledger(lpath, 1.0e6, 1.0e6, cap, run_id="chk"))
        self.assertEqual(b.calls, 1)
        self.assertEqual(len(read_jsonl(self.out / "raw.jsonl")), 1)
        # an owed second turn keeps its probe out of answers.jsonl
        a = self.answers()
        self.assertEqual(len(a), len(ITEMS) - (len(SECOND_TURN) - 1))
        # resume with a higher cap (only the cap may differ)
        self.go(b, ledger=spend.Ledger(lpath, 1.0e6, 1.0e6, 1e12, run_id="chk"))
        self.assertEqual(b.calls, len(SECOND_TURN))
        self.assertEqual(sorted(r["id"] for r in read_jsonl(self.out / "raw.jsonl")),
                         sorted(SECOND_TURN))
        self.assertEqual(len(read_jsonl(lpath)), len(SECOND_TURN))
        self.assertEqual(len(self.answers()), len(ITEMS))

    def src_obj(self):
        return pac.load_source(self.src, root=self.root)

    def planned(self):
        return [i for i in pac.items(self.src_obj(), DATA) if i["send"]]

    def test_resume_refuses_other_inputs(self):
        lpath = self.root / "spend" / "l.jsonl"
        b = MeteredFake(second_fn, out_tokens=10, max_tokens=20, messages=True)
        self.go(b, ledger=spend.Ledger(lpath, 1.0, 1.0, 5.0, run_id="chk"))
        with self.assertRaises(ValueError):   # other prices
            self.go(b, ledger=spend.Ledger(lpath, 2.0, 1.0, 5.0, run_id="chk"))
        # a changed source run
        with open(self.src / "responses.jsonl", "a") as fh:
            fh.write("\n")
        with self.assertRaises(ValueError):
            self.go(b, ledger=spend.Ledger(lpath, 1.0, 1.0, 5.0, run_id="chk"))

    def test_resume_skips_stored(self):
        self.go()
        calls = []
        self.go(self.backend(lambda m: calls.append(1) or "U95"))
        self.assertEqual(calls, [])


class PlanTests(Base):
    def test_plan_counts_and_writes_nothing(self):
        before = sorted(p for p in self.root.rglob("*"))
        p = pac.plan(self.src, checker_data=DATA, root=self.root)
        self.assertEqual(sorted(p for p in self.root.rglob("*")), before)
        self.assertEqual(p["probes"], len(ITEMS))
        self.assertEqual(p["first_with_code"], len(ITEMS) - 1)
        self.assertEqual(p["findings_by_rule"], {"not_in_code_set": 3,
                                                 "header_not_billable": 2})
        self.assertEqual(p["second_turns"], len(SECOND_TURN))
        src = pac.load_source(self.src, root=self.root)
        sizes = [spend.request_chars(pac.messages_for(src, i))
                 for i in pac.items(src, DATA) if i["send"]]
        self.assertEqual(p["request_chars"], {"total": sum(sizes),
                                              "mean": sum(sizes) / len(sizes),
                                              "largest": max(sizes)})

    def test_plan_cli_no_backend_call(self):
        out = io.StringIO()
        with redirect_stdout(out):
            pac.print_plan(pac.plan(self.src, checker_data=DATA, root=self.root))
        text = out.getvalue()
        self.assertIn("second turns that would be sent: 5", text)


class ScoreTests(Base):
    def test_score_groups(self):
        # source score.json as the Part A scorer writes it
        resp = read_jsonl(self.src / "responses.jsonl")
        (self.src / "score.json").write_text(json.dumps(
            part_a_score.score(self.probes, resp)))
        self.go()
        s = pac.score_run(self.out, checker_data=DATA, root=self.root)
        self.assertEqual(s["code_set"], CODE_SET)
        # first: d-1 correct; d-6 invalid; the other six wrong
        self.assertEqual(s["first"], {"n": 8, "correct": 1, "wrong": 6, "invalid": 1,
                                      "missing": 0})
        # final: d-1, d-2 correct; d-6, d-8 invalid
        self.assertEqual(s["final"], {"n": 8, "correct": 2, "wrong": 4, "invalid": 2,
                                      "missing": 0})
        self.assertTrue(s["first_matches_source"])
        g = s["second_turn"]
        self.assertEqual(g["total"], {"n": 5, "final_correct": 1,
                                      "final_wrong_still_rule": 2,
                                      "final_wrong_no_rule": 1, "final_invalid": 1,
                                      "final_same_as_first": 1})
        self.assertEqual(g["by_rule"]["header_not_billable"],
                         {"n": 2, "final_correct": 1, "final_wrong_still_rule": 0,
                          "final_wrong_no_rule": 0, "final_invalid": 1,
                          "final_same_as_first": 0})
        self.assertEqual(g["by_rule"]["not_in_code_set"],
                         {"n": 3, "final_correct": 0, "final_wrong_still_rule": 2,
                          "final_wrong_no_rule": 1, "final_invalid": 0,
                          "final_same_as_first": 1})
        self.assertEqual(json.loads((self.out / "score.json").read_text()), s)
        md = (self.out / "score.md").read_text()
        self.assertIn(CODE_SET, md)

    def test_score_without_source_score(self):
        self.go()
        s = pac.score_run(self.out, checker_data=DATA, root=self.root)
        self.assertIsNone(s["first_matches_source"])

    def test_score_refuses_incomplete_run(self):
        lpath = self.root / "spend" / "l.jsonl"
        b = MeteredFake(second_fn, out_tokens=10, max_tokens=20, messages=True)
        self.go(b, ledger=spend.Ledger(lpath, 1e6, 1e6, 1e-9, run_id="chk"))
        with self.assertRaises(ValueError):
            pac.score_run(self.out, checker_data=DATA, root=self.root)


if __name__ == "__main__":
    unittest.main()
