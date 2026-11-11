"""Tests for medcode_eval.run (Part A runner) with the fake backend.

Probes are hand-made with invented codes (U9x). No network and no model.
"""

import json
import tempfile
import unittest
from pathlib import Path

from medcode_eval.run import runner
from medcode_eval.run.runner import (
    FakeBackend,
    OllamaBackend,
    extract_answer,
    load_prompts,
    render_prompt,
    run,
)

CODE_SET = "ICD-10-CM FY2027 (October 1, 2026 release)"
HIDDEN = ("id", "answer", "kind", "change", "derived_from", "source", "origin")


def probes():
    base = {"code_set": CODE_SET, "chapter": 1, "source": "order.txt", "origin": "o"}
    return [
        {**base, "id": "c2d-0001", "type": "code_to_description", "code": "U90.0",
         "options": ["Invented one", "Invented two", "Invented three", "Invented four"],
         "answer": "C"},
        {**base, "id": "d2c-0001", "type": "description_to_code",
         "description": "Invented alpha {not a field}", "answer": "U900"},
        {**base, "id": "st-0001", "type": "status", "code": "U90.01",
         "answer": "not_a_code", "kind": "extended", "derived_from": "U900"},
        {**base, "id": "chg-st-0001", "type": "status", "code": "U95.8",
         "answer": "not_a_code", "change": "removed"},
    ]


def sentinel_probes():
    """The same probes with every non-prompt field set to a unique marker."""
    out = []
    for i, p in enumerate(probes()):
        q = dict(p)
        for k in HIDDEN:
            q[k] = f"SENTINEL{k.upper()}{i}"
        q["id"] = p["id"]  # the runner needs the real id; checked separately
        out.append(q)
    return out


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="ascii")


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


class PromptTests(unittest.TestCase):
    def test_prompt_files_exact(self):
        p = load_prompts()
        self.assertEqual(set(p), {"code_to_description", "description_to_code", "status"})
        self.assertEqual(p["description_to_code"],
                         "Code set: ICD-10-CM FY2027 (October 1, 2026 release).\n"
                         "Give the billable code whose official long description is:\n"
                         "{description}\n"
                         "Answer with the code only.\n")

    def test_render_code_to_description(self):
        text = render_prompt(probes()[0])
        self.assertEqual(text.splitlines(), [
            "Code set: ICD-10-CM FY2027 (October 1, 2026 release).",
            "Which description belongs to code U90.0?",
            "A. Invented one", "B. Invented two", "C. Invented three", "D. Invented four",
            "Answer with one letter only: A, B, C or D."])

    def test_render_braces_in_description_kept(self):
        self.assertIn("Invented alpha {not a field}", render_prompt(probes()[1]))

    def test_render_status(self):
        self.assertIn("What is the status of U90.01 in this code set?",
                      render_prompt(probes()[2]))

    def test_hidden_fields_never_rendered(self):
        for p in sentinel_probes():
            text = render_prompt(p)
            self.assertNotIn("SENTINEL", text)
            self.assertNotIn(p["id"], text)

    def test_hidden_fields_do_not_change_prompt(self):
        for p, q in zip(probes(), sentinel_probes()):
            self.assertEqual(render_prompt(p), render_prompt(q))

    def test_backend_sees_only_prompt(self):
        seen = []
        backend = FakeBackend(lambda prompt: seen.append(prompt) or "A")
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "p.jsonl"
            write_jsonl(pf, sentinel_probes())
            run(pf, Path(tmp) / "run", backend)
        self.assertEqual(len(seen), 4)
        for text in seen:
            self.assertNotIn("SENTINEL", text)


class ExtractTests(unittest.TestCase):
    def test_think_block_dropped(self):
        self.assertEqual(extract_answer("<think>\nmaybe A\nor B\n</think>\n\nC"), "C")

    def test_last_non_empty_line(self):
        self.assertEqual(extract_answer("The answer is:\n\nheader\n\n  \n"), "header")

    def test_strip_marks(self):
        self.assertEqual(extract_answer('"billable"'), "billable")
        self.assertEqual(extract_answer("`U90.01`"), "U90.01")
        self.assertEqual(extract_answer("**B**"), "B")
        self.assertEqual(extract_answer("**B.**"), "B")
        self.assertEqual(extract_answer("`U90.0`."), "U90.0")
        self.assertEqual(extract_answer("'header'."), "header")

    def test_only_one_trailing_full_stop(self):
        self.assertEqual(extract_answer("B.."), "B.")

    def test_inner_text_untouched(self):
        self.assertEqual(extract_answer("Answer: B"), "Answer: B")

    def test_unclosed_think_gives_empty(self):
        # a reply cut off inside its reasoning has no answer line
        self.assertEqual(extract_answer("<think>\nlet me think\nbillable"), "")

    def test_empty(self):
        self.assertEqual(extract_answer(""), "")
        self.assertEqual(extract_answer("<think>x</think>"), "")


class RunTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.pf = self.dir / "probes.jsonl"
        write_jsonl(self.pf, probes())
        self.out = self.dir / "runs" / "r1"

    def reply(self, prompt):
        if "Which description" in prompt:
            return "<think>hmm</think>\n\n**C**"
        if "long description" in prompt:
            return "U90.0"
        return "not_a_code."

    def test_outputs(self):
        run(self.pf, self.out, FakeBackend(self.reply))
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["code_set"], CODE_SET)
        self.assertEqual(meta["backend"], "fake")
        self.assertEqual(len(meta["probes_sha256"]), 64)
        self.assertEqual(set(meta["prompts_sha256"]),
                         {"part_a_code_to_description.txt",
                          "part_a_description_to_code.txt", "part_a_status.txt"})
        for key in ("model", "model_digest", "settings"):
            self.assertIn(key, meta)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual([r["id"] for r in raw],
                         ["c2d-0001", "d2c-0001", "st-0001", "chg-st-0001"])
        for r in raw:
            self.assertEqual(set(r) >= {"id", "raw", "seconds", "error"}, True)
            self.assertIsNone(r["error"])
            self.assertIsInstance(r["seconds"], float)
        resp = {r["id"]: r["response"] for r in read_jsonl(self.out / "responses.jsonl")}
        self.assertEqual(resp, {"c2d-0001": "C", "d2c-0001": "U90.0",
                                "st-0001": "not_a_code", "chg-st-0001": "not_a_code"})

    def test_resume_skips_done_ids(self):
        calls = []

        def counting(prompt):
            calls.append(prompt)
            return "A"
        run(self.pf, self.out, FakeBackend(counting), limit=2)
        self.assertEqual(len(calls), 2)
        run(self.pf, self.out, FakeBackend(counting))
        self.assertEqual(len(calls), 4)
        run(self.pf, self.out, FakeBackend(counting))
        self.assertEqual(len(calls), 4)
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual(len(raw), 4)
        self.assertEqual(len({r["id"] for r in raw}), 4)
        self.assertEqual(len(read_jsonl(self.out / "responses.jsonl")), 4)

    def test_ids_selection(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"), ids=["st-0001", "d2c-0001"])
        raw = read_jsonl(self.out / "raw.jsonl")
        self.assertEqual([r["id"] for r in raw], ["d2c-0001", "st-0001"])

    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A"), ids=["nope"])

    def test_error_recorded_and_not_a_response(self):
        def failing(prompt):
            if "long description" in prompt:
                raise TimeoutError("timed out")
            return "A"
        run(self.pf, self.out, FakeBackend(failing))
        raw = {r["id"]: r for r in read_jsonl(self.out / "raw.jsonl")}
        self.assertIn("timed out", raw["d2c-0001"]["error"])
        self.assertIsNone(raw["d2c-0001"]["raw"])
        resp = {r["id"] for r in read_jsonl(self.out / "responses.jsonl")}
        self.assertNotIn("d2c-0001", resp)
        self.assertEqual(len(resp), 3)

    def test_resume_refuses_other_probe_file(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"), limit=1)
        other = self.dir / "other.jsonl"
        write_jsonl(other, probes()[:2])
        with self.assertRaises(ValueError):
            run(other, self.out, FakeBackend(lambda p: "A"))

    def test_resume_refuses_other_settings(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"), limit=1)
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A", model="other"))

    def test_mixed_code_sets_rejected(self):
        rows = probes()
        rows[0] = dict(rows[0], code_set="ICD-10-CM FY2099")
        write_jsonl(self.pf, rows)
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A"))


class OllamaBackendTests(unittest.TestCase):
    """Request building only; no server is contacted."""

    def test_local_only(self):
        with self.assertRaises(ValueError):
            OllamaBackend("qwen3:4b", host="http://example.com:11434")
        OllamaBackend("qwen3:4b", host="http://127.0.0.1:11434")
        OllamaBackend("qwen3:4b", host="http://localhost:11434")

    def test_request_body(self):
        b = OllamaBackend("qwen3:4b")
        body = b.request_body("hello")
        self.assertEqual(body["model"], "qwen3:4b")
        self.assertEqual(body["prompt"], "hello")
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertEqual(body["options"]["seed"], runner.SEED)
        self.assertEqual(body["options"]["num_predict"], runner.NUM_PREDICT)
        # default reasoning behaviour: no think switch, no system prompt
        self.assertNotIn("think", body)
        self.assertNotIn("system", body)
        self.assertNotIn("/no_think", body["prompt"])


if __name__ == "__main__":
    unittest.main()
