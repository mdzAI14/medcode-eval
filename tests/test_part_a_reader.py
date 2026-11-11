"""Tests for the Part A answer readers (medcode_eval.run.runner).

Reader 1 reads the last non-empty line. Reader 2 reads the first and the
last non-empty line with the same line-level logic and keeps the one valid
answer, or the shared answer when both agree. Probes are hand-made with
invented codes (U9x). No network and no model.
"""

import json
import tempfile
import unittest
from pathlib import Path

from medcode_eval.part_a.score import score, to_markdown
from medcode_eval.run import runner
from medcode_eval.run.runner import (
    DEFAULT_READER,
    FakeBackend,
    extract_answer,
    read_reply,
    run,
    write_responses,
)
from tests.test_run import probes, read_jsonl, write_jsonl

P = {p["type"]: p for p in probes()}
C2D, D2C, ST = P["code_to_description"], P["description_to_code"], P["status"]

# (name, probe, reply, reader 1 response, reader 2 response); None = invalid
FIXTURES = [
    ("c2d answer then caveat", C2D,
     "B\n\nNote: this assumes the invented tabular list.",
     "Note: this assumes the invented tabular list", "B"),
    ("status answer then caveat", ST,
     "header\n\nIt has subcodes, so it is not reported on its own.",
     "It has subcodes, so it is not reported on its own", "header"),
    ("d2c answer then caveat", D2C,
     "U90.0\nThis assumes no further specificity is documented",
     "This assumes no further specificity is documented", "U90.0"),
    ("status reasoning then answer", ST,
     "The invented code has subcodes under it.\n\nheader",
     "header", "header"),
    ("c2d reasoning then answer", C2D,
     "Looking at the four invented options:\n**C**", "C", "C"),
    ("c2d answer first, different answer last", C2D,
     "A\n\nOn reflection:\nB", "B", None),
    ("status answer first, different answer last", ST,
     "billable\nheader", "header", None),
    ("both lines agree", C2D, "C. Invented three\nSo the answer is\nC", "C", "C"),
    ("one line letter with text", C2D, "D. Invented four",
     "D. Invented four", "D. Invented four"),
    ("one line invalid", ST, "I am not sure", "I am not sure", "I am not sure"),
    ("one line labelled", ST, "**Answer:** `header`.", "header", "header"),
    ("neither line valid", ST, "I am not sure.\nIt could be either",
     "It could be either", "It could be either"),
    ("empty reply", ST, "", "", ""),
    ("only whitespace", C2D, "  \n\n ", "", ""),
    ("only a think block", C2D, "<think>A</think>", "", ""),
    ("think block before answer then caveat", C2D,
     "<think>\nmaybe A\nor B\n</think>\n\nC\nI am fairly sure of this.",
     "I am fairly sure of this", "C"),
    ("think block between answer lines", ST,
     "header\n<think>\nbillable\n</think>\nheader", "header", "header"),
]


class Reader2Tests(unittest.TestCase):
    def test_default_is_reader_2(self):
        self.assertEqual(DEFAULT_READER, 2)

    def test_reader_2_fixtures(self):
        for name, probe, reply, _, want in FIXTURES:
            with self.subTest(name):
                self.assertEqual(read_reply(reply, probe), want)
                self.assertEqual(read_reply(reply, probe, reader=2), want)

    def test_reader_1_by_option_gives_old_result(self):
        for name, probe, reply, want, _ in FIXTURES:
            with self.subTest(name):
                self.assertEqual(read_reply(reply, probe, reader=1), want)
                self.assertEqual(read_reply(reply, probe, reader=1), extract_answer(reply))

    def test_one_line_reply_as_today(self):
        for name, probe, reply, _, _ in FIXTURES:
            lines = [l for l in runner.drop_think(reply).splitlines() if l.strip()]
            if len(lines) <= 1:
                with self.subTest(name):
                    self.assertEqual(read_reply(reply, probe, reader=2),
                                     extract_answer(reply))

    def test_scored_reading(self):
        # the response string scores as the reading named in FIXTURES
        for name, probe, reply, r1, r2 in FIXTURES:
            with self.subTest(name):
                for reader, want in ((1, r1), (2, r2)):
                    got = read_reply(reply, probe, reader=reader)
                    self.assertEqual(got, want)
        res = score([C2D], [{"id": C2D["id"], "response": None}])
        self.assertEqual((res["overall"]["invalid"], res["overall"]["missing"]), (1, 0))

    def test_unknown_reader(self):
        with self.assertRaises(ValueError):
            read_reply("A", C2D, reader=3)


class WriteResponsesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.pf = self.root / "probes.jsonl"
        write_jsonl(self.pf, probes())
        self.out = self.root / runner.RUNS_DIR / "r1"
        replies = {"Which description": "C\nThis is my best reading.",
                   "long description": "U90.0",
                   "status": "billable\nheader"}

        def reply(prompt):
            for k, v in replies.items():
                if k in prompt:
                    return v
            return "not_a_code\nThe code is invented."
        self.reply = reply

    def responses(self):
        return {r["id"]: r for r in read_jsonl(self.out / "responses.jsonl")}

    def test_run_writes_reader_2_rows(self):
        run(self.pf, self.out, FakeBackend(self.reply))
        resp = self.responses()
        self.assertEqual({r["reader"] for r in resp.values()}, {2})
        self.assertEqual(resp["c2d-0001"]["response"], "C")
        self.assertEqual(resp["d2c-0001"]["response"], "U90.0")

    def test_run_reader_1_option(self):
        run(self.pf, self.out, FakeBackend(self.reply), reader=1)
        resp = self.responses()
        self.assertEqual({r["reader"] for r in resp.values()}, {1})
        self.assertEqual(resp["c2d-0001"]["response"], "This is my best reading")

    def test_rewrite_switches_reader(self):
        run(self.pf, self.out, FakeBackend(self.reply), reader=1)
        write_responses(self.out, reader=2, probes=probes())
        self.assertEqual(self.responses()["c2d-0001"]["response"], "C")
        write_responses(self.out, reader=1)
        self.assertEqual(self.responses()["c2d-0001"]["response"],
                         "This is my best reading")

    def rederive(self, *extra):
        orig = runner.REPO_ROOT
        runner.REPO_ROOT = self.root
        try:
            runner.main(["--run-id", "r1", "--rederive", *extra])
        finally:
            runner.REPO_ROOT = orig

    def test_rederive_default_and_option(self):
        run(self.pf, self.out, FakeBackend(self.reply), reader=1)
        raw = (self.out / "raw.jsonl").read_bytes()
        self.rederive()
        resp = self.responses()
        self.assertEqual(resp["c2d-0001"], {"id": "c2d-0001", "reader": 2, "response": "C"})
        self.rederive("--reader", "1")
        self.assertEqual(self.responses()["c2d-0001"]["reader"], 1)
        self.assertEqual((self.out / "raw.jsonl").read_bytes(), raw)

    def test_rederive_reader_2_refuses_changed_probe_file(self):
        run(self.pf, self.out, FakeBackend(self.reply))
        write_jsonl(self.pf, probes()[:2])
        orig = runner.REPO_ROOT
        runner.REPO_ROOT = self.root
        try:
            with self.assertRaises(ValueError):
                write_responses(self.out, reader=2)
        finally:
            runner.REPO_ROOT = orig

    def test_score_records_reader(self):
        run(self.pf, self.out, FakeBackend(self.reply))
        res = score(probes(), read_jsonl(self.out / "responses.jsonl"))
        self.assertEqual(res["reader"], 2)
        self.assertIn("Reader: 2.", to_markdown(res).splitlines()[0])
        # status probe st-0001 got "billable" then "header": invalid
        self.assertEqual(res["by_type"]["status"]["invalid"], 2)

    def test_score_reader_not_recorded(self):
        res = score([C2D], [{"id": C2D["id"], "response": "C"}])
        self.assertIsNone(res["reader"])
        self.assertIn("Reader: not recorded.", to_markdown(res).splitlines()[0])

    def test_score_mixed_readers_rejected(self):
        with self.assertRaises(ValueError):
            score([C2D, ST], [{"id": C2D["id"], "response": "C", "reader": 1},
                              {"id": ST["id"], "response": "header", "reader": 2}])


if __name__ == "__main__":
    unittest.main()
