"""Tests for the Part C run conditions (medcode_eval.run.part_c) with the fake
backend and the invented checker fixture. No network and no model.
"""

import hashlib
import json
import unittest
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import REPO_ROOT
from medcode_eval.run import part_b, part_c, runner
from medcode_eval.run.runner import FakeBackend
from tests.part_c_fixture import CASES, CODE_SET, TempDir, make_c_data_dir, make_refdata

REMINDED_SHA256 = "1e842fcacef54cac789fb003754a2890d838f35916e47cbbed812c5ddd4f7b8b"
ADDED = (b"Report only what the note documents. Do not assume a detail the\n"
         b"note does not state.\n")
REPORTED_RUN = REPO_ROOT / "results" / "part_b" / "p612-b-plain-opus-5-5" / "run.json"


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def setUpModule():
    global TMP, DATA
    import tempfile
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


def prompt_bytes(name):
    return (runner.PROMPT_DIR / name).read_bytes()


class PinTests(unittest.TestCase):
    def test_reminded_sha256(self):
        self.assertEqual(hashlib.sha256(prompt_bytes("part_c_reminded.txt")).hexdigest(),
                         REMINDED_SHA256)

    def test_removing_added_lines_gives_plain(self):
        text = prompt_bytes("part_c_reminded.txt")
        self.assertEqual(text.count(ADDED), 1)
        self.assertEqual(text.replace(ADDED, b""), prompt_bytes("part_b_plain.txt"))
        self.assertIn(b"\nfirst.\n" + ADDED, text)

    def test_reminded_built_by_code(self):
        self.assertEqual(part_c.build_reminded(prompt_bytes("part_b_plain.txt")),
                         prompt_bytes("part_c_reminded.txt"))

    def test_part_b_prompts_equal_reported_run(self):
        stored = json.loads(REPORTED_RUN.read_text(encoding="utf-8"))["prompts_sha256"]
        for name in ("part_b_plain.txt", "part_b_checker.txt"):
            self.assertEqual(hashlib.sha256(prompt_bytes(name)).hexdigest(), stored[name])

    def test_part_b_settings_unchanged(self):
        self.assertEqual(part_b.PROMPT_FILES,
                         {"plain": "part_b_plain.txt", "checker": "part_b_checker.txt"})
        self.assertEqual(part_b.CONDITIONS, ("plain", "with_checker"))
        self.assertEqual(part_b.RUNS_DIR, Path("runs") / "part_b")

    def test_part_c_settings(self):
        self.assertEqual(part_c.PROMPT_FILES,
                         {"plain": "part_b_plain.txt", "reminded": "part_c_reminded.txt",
                          "checker": "part_b_checker.txt"})
        self.assertEqual(part_c.CONDITIONS, ("plain", "reminded", "with_checker"))
        self.assertEqual(part_c.RUNS_DIR, Path("runs") / "part_c")
        self.assertEqual(part_c.DATA_DIR, Path("data") / "part_c")


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.dir = make_c_data_dir(TempDir(self).path)
        self.cases = part_b.load_cases(self.dir)

    def test_plain_is_part_b_plain(self):
        for c in self.cases:
            self.assertEqual(part_c.render_first(c, "plain"), part_b.render_first(c))
            self.assertEqual(part_c.render_first(c, "with_checker"), part_b.render_first(c))

    def test_reminded_is_new_file(self):
        template = prompt_bytes("part_c_reminded.txt").decode("ascii")
        for c in self.cases:
            text = part_c.render_first(c, "reminded")
            self.assertEqual(text, template.format(note=c["note"]).rstrip("\n"))
            self.assertIn("Do not assume a detail the\nnote does not state.", text)
            self.assertIn(c["note"], text)

    def test_suffix(self):
        c = self.cases[0]
        self.assertEqual(part_c.render_first(c, "reminded", prompt_suffix="/no_think"),
                         part_c.render_first(c, "reminded") + "\n/no_think")

    def test_unknown_condition(self):
        with self.assertRaises(ValueError):
            part_c.render_first(self.cases[0], "other")


class RunTests(unittest.TestCase):
    def setUp(self):
        self.root = TempDir(self).path
        self.data = make_c_data_dir(self.root, sentinel=True)
        self.out = self.root / "runs" / "r1"
        self.cases = {c["id"]: c for c in part_b.load_cases(self.data)}

    def backend(self, seen, reply='["U95"]'):
        return FakeBackend(lambda m: seen.append(m) or reply, messages=True)

    def test_reminded_one_turn(self):
        seen = []
        part_c.run(self.data, self.out, self.backend(seen), "reminded", checker_data=DATA)
        self.assertEqual(len(seen), len(CASES))
        for m in seen:
            self.assertEqual(len(m), 1)
        texts = sorted(m[0]["content"] for m in seen)
        self.assertEqual(texts, sorted(part_c.render_first(c, "reminded")
                                       for c in self.cases.values()))
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["part"], "c")
        self.assertEqual(meta["condition"], "reminded")
        self.assertIsNone(meta["checker"])
        self.assertEqual(meta["code_set"], CODE_SET)
        self.assertEqual(meta["prompts_sha256"], {
            f: runner._sha(runner.PROMPT_DIR / f)
            for f in ("part_b_plain.txt", "part_c_reminded.txt", "part_b_checker.txt")})
        ans = read_jsonl(self.out / "answers.jsonl")
        self.assertEqual(len(ans), len(CASES))
        self.assertTrue(all(not a["second_turn"] for a in ans))

    def test_only_note_reaches_model(self):
        seen = []
        part_c.run(self.data, self.out, self.backend(seen, '["U90.012"]'), "with_checker",
                   checker_data=DATA)
        self.assertEqual(len(seen), 2 * len(CASES))
        for messages in seen:
            for m in messages:
                self.assertNotIn("SENTINEL", m["content"])
                for cid in CASES:
                    self.assertNotIn(cid, m["content"])
                if m["role"] == "user":
                    self.assertNotIn("U96", m["content"])   # an unsupported entry

    def test_plain_one_turn(self):
        seen = []
        part_c.run(self.data, self.out, self.backend(seen, '["U90.012"]'), "plain",
                   checker_data=DATA)
        self.assertEqual(len(seen), len(CASES))
        self.assertEqual({m[0]["content"] for m in seen},
                         {part_b.render_first(c) for c in self.cases.values()})
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual((meta["part"], meta["condition"]), ("c", "plain"))

    def test_with_checker_second_turn_is_part_b(self):
        seen = []
        part_c.run(self.data, self.out, self.backend(seen, '["U90.012"]'), "with_checker",
                   checker_data=DATA)
        findings = checker.check(["U90.012"], data=DATA)
        second = [m for m in seen if len(m) == 3]
        self.assertEqual(len(second), len(CASES))
        for m in second:
            self.assertEqual(m[0]["content"], part_c.render_first(
                next(c for c in self.cases.values() if c["note"] in m[0]["content"]),
                "plain"))
            self.assertEqual(m[2]["content"], part_b.render_second(findings))
        meta = json.loads((self.out / "run.json").read_text())
        self.assertIsNotNone(meta["checker"])

    def test_ids_limit_suffix_resume(self):
        seen = []
        n = part_c.run(self.data, self.out, self.backend(seen), "reminded", limit=1,
                       ids=["c-t-002", "c-t-003"], prompt_suffix="/no_think",
                       checker_data=DATA)
        self.assertEqual(n, 1)
        self.assertTrue(seen[0][0]["content"].endswith("\n/no_think"))
        self.assertEqual([r["id"] for r in read_jsonl(self.out / "raw.jsonl")], ["c-t-002"])
        n = part_c.run(self.data, self.out, self.backend(seen), "reminded",
                       ids=["c-t-002", "c-t-003"], prompt_suffix="/no_think",
                       checker_data=DATA)
        self.assertEqual(n, 1)
        self.assertEqual([r["id"] for r in read_jsonl(self.out / "raw.jsonl")],
                         ["c-t-002", "c-t-003"])
        with self.assertRaises(ValueError):
            part_c.run(self.data, self.out, self.backend(seen), "plain", checker_data=DATA)

    def test_unknown_condition(self):
        with self.assertRaises(ValueError):
            part_c.run(self.data, self.out, self.backend([]), "other", checker_data=DATA)

    def test_part_b_refuses_reminded(self):
        with self.assertRaises(ValueError):
            part_b.run(self.data, self.out, self.backend([]), "reminded", checker_data=DATA)

    def test_remote_needs_ledger(self):
        class Remote(FakeBackend):
            name = "remote"
        with self.assertRaises(ValueError):
            part_c.run(self.data, self.out, Remote(lambda m: "[]"), "plain")

    def test_part_b_run_json_has_no_part_c_field(self):
        part_b.run(self.data, self.out, self.backend([]), "plain", checker_data=DATA)
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["part"], "b")
        self.assertEqual(sorted(meta["prompts_sha256"]),
                         ["part_b_checker.txt", "part_b_plain.txt"])


class MainTests(unittest.TestCase):
    """runner.main with --part c; REPO_ROOT and the Ollama backend patched."""

    def setUp(self):
        self.root = TempDir(self).path
        src = make_c_data_dir(self.root / "x")
        (self.root / "data").mkdir()
        src.rename(self.root / "data" / "part_c")
        self.seen = []
        seen = self.seen

        def fake_ollama(model, host=None, endpoint=None):
            self.assertEqual(endpoint, "/api/chat")
            return FakeBackend(lambda m: seen.append(m) or '["U95"]', messages=True)
        self.orig = (runner.REPO_ROOT, runner.OllamaBackend, checker.default_data)
        runner.REPO_ROOT = self.root
        runner.OllamaBackend = fake_ollama
        checker.default_data = lambda: DATA

    def tearDown(self):
        runner.REPO_ROOT, runner.OllamaBackend, checker.default_data = self.orig

    def test_run_folder_under_runs_part_c(self):
        for cond in ("plain", "reminded", "with_checker"):
            runner.main(["--part", "c", "--condition", cond, "--run-id", f"r-{cond}"])
            d = self.root / "runs" / "part_c" / f"r-{cond}"
            meta = json.loads((d / "run.json").read_text())
            self.assertEqual((meta["part"], meta["condition"]), ("c", cond))
            self.assertEqual(meta["data_dir"], "data/part_c")
            self.assertEqual(len(read_jsonl(d / "answers.jsonl")), len(CASES))
        self.assertFalse((self.root / "runs" / "part_b").exists())

    def test_rederive(self):
        runner.main(["--part", "c", "--condition", "reminded", "--run-id", "r1"])
        d = self.root / "runs" / "part_c" / "r1"
        (d / "answers.jsonl").write_text("stale\n")
        runner.OllamaBackend = None
        runner.main(["--part", "c", "--run-id", "r1", "--rederive"])
        self.assertEqual(len(read_jsonl(d / "answers.jsonl")), len(CASES))

    def test_bad_condition(self):
        with self.assertRaises(SystemExit):
            runner.main(["--part", "c", "--condition", "other", "--run-id", "r1"])
        with self.assertRaises(SystemExit):
            runner.main(["--part", "b", "--condition", "reminded", "--run-id", "r1"])


if __name__ == "__main__":
    unittest.main()
