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


class SuffixTests(unittest.TestCase):
    def test_default_is_no_suffix(self):
        for p in probes():
            self.assertEqual(render_prompt(p), render_prompt(p, prompt_suffix=""))

    def test_suffix_on_own_last_line(self):
        for p in probes():
            plain = render_prompt(p)
            text = render_prompt(p, prompt_suffix="/no_think")
            self.assertEqual(text, plain + "\n/no_think")
            self.assertEqual(text.splitlines()[-1], "/no_think")

    def test_multiline_suffix_rejected(self):
        with self.assertRaises(ValueError):
            render_prompt(probes()[0], prompt_suffix="a\nb")

    def test_hidden_fields_never_rendered_with_suffix(self):
        for p, q in zip(probes(), sentinel_probes()):
            text = render_prompt(q, prompt_suffix="/no_think")
            self.assertNotIn("SENTINEL", text)
            self.assertNotIn(q["id"], text)
            self.assertEqual(text, render_prompt(p, prompt_suffix="/no_think"))

    def test_backend_sees_suffix_and_no_hidden_fields(self):
        seen = []
        backend = FakeBackend(lambda prompt: seen.append(prompt) or "A")
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "p.jsonl"
            write_jsonl(pf, sentinel_probes())
            run(pf, Path(tmp) / "run", backend, prompt_suffix="/no_think")
        self.assertEqual(len(seen), 4)
        for text in seen:
            self.assertNotIn("SENTINEL", text)
            self.assertTrue(text.endswith("\n/no_think"))

    def test_prompt_files_unchanged_by_suffix(self):
        before = load_prompts()
        render_prompt(probes()[0], prompt_suffix="/no_think")
        self.assertEqual(load_prompts(), before)
        self.assertNotIn("no_think", "".join(before.values()))


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
        self.assertEqual(extract_answer("The answer is B"), "The answer is B")
        self.assertEqual(extract_answer("B Answer: C"), "B Answer: C")

    def test_answer_label_dropped(self):
        self.assertEqual(extract_answer("**Answer:** C"), "C")
        self.assertEqual(extract_answer("Answer: B"), "B")
        self.assertEqual(extract_answer("answer: billable."), "billable")
        self.assertEqual(extract_answer("Final answer: U90.0"), "U90.0")
        self.assertEqual(extract_answer("**FINAL ANSWER:** **header**"), "header")
        self.assertEqual(extract_answer("*Answer*: D"), "D")
        self.assertEqual(extract_answer("**Final Answer**: **A**"), "A")
        self.assertEqual(extract_answer("<think>x</think>\n\nAnswer: not_a_code"),
                         "not_a_code")

    def test_answer_label_only_on_kept_line(self):
        self.assertEqual(extract_answer("Answer: A\nB"), "B")

    def test_answer_label_then_end_strip_again(self):
        # after the label is dropped the end-strip runs again
        self.assertEqual(extract_answer("Answer: `U90.0`"), "U90.0")
        self.assertEqual(extract_answer('Answer: "billable".'), "billable")
        self.assertEqual(extract_answer("**Answer:** `header`."), "header")
        self.assertEqual(extract_answer("Answer: 'B'"), "B")

    def test_second_end_strip_one_full_stop_only(self):
        # first pass takes one stop, second pass one more, never a third
        self.assertEqual(extract_answer("Answer: B..."), "B.")

    def test_answer_word_without_colon_kept(self):
        self.assertEqual(extract_answer("Answer B"), "Answer B")

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

    def test_suffix_recorded(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"), prompt_suffix="/no_think")
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["prompt_suffix"], "/no_think")

    def test_empty_suffix_recorded(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"))
        meta = json.loads((self.out / "run.json").read_text())
        self.assertEqual(meta["prompt_suffix"], "")

    def test_resume_refuses_other_suffix(self):
        run(self.pf, self.out, FakeBackend(lambda p: "A"), limit=1, prompt_suffix="/no_think")
        with self.assertRaises(ValueError) as cm:
            run(self.pf, self.out, FakeBackend(lambda p: "A"))
        self.assertIn("prompt_suffix", str(cm.exception))
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A"), prompt_suffix="/think")
        run(self.pf, self.out, FakeBackend(lambda p: "A"), prompt_suffix="/no_think")
        self.assertEqual(len(read_jsonl(self.out / "raw.jsonl")), 4)

    def test_resume_run_made_before_suffix_setting(self):
        # a run.json written before prompt_suffix existed had no suffix
        run(self.pf, self.out, FakeBackend(lambda p: "A"), limit=1)
        meta_path = self.out / "run.json"
        meta = json.loads(meta_path.read_text())
        del meta["prompt_suffix"]
        meta_path.write_text(json.dumps(meta))
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A"), prompt_suffix="/no_think")
        run(self.pf, self.out, FakeBackend(lambda p: "A"))
        self.assertEqual(len(read_jsonl(self.out / "raw.jsonl")), 4)

    def test_mixed_code_sets_rejected(self):
        rows = probes()
        rows[0] = dict(rows[0], code_set="ICD-10-CM FY2099")
        write_jsonl(self.pf, rows)
        with self.assertRaises(ValueError):
            run(self.pf, self.out, FakeBackend(lambda p: "A"))


class RederiveTests(unittest.TestCase):
    """--rederive rewrites responses.jsonl from raw.jsonl with no model call."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.out = self.root / runner.RUNS_DIR / "r1"
        pf = self.root / "probes.jsonl"
        write_jsonl(pf, probes())
        run(pf, self.out, FakeBackend(lambda p: "Answer: `B`"))
        (self.out / "responses.jsonl").write_text("stale\n")
        self.raw = (self.out / "raw.jsonl").read_bytes()
        self.meta = (self.out / "run.json").read_bytes()

    def test_rederive_no_backend(self):
        def no_backend(*a, **k):
            raise AssertionError("a backend was built")
        orig_root, orig_backend = runner.REPO_ROOT, runner.OllamaBackend
        runner.REPO_ROOT, runner.OllamaBackend = self.root, no_backend
        try:
            runner.main(["--run-id", "r1", "--rederive"])
        finally:
            runner.REPO_ROOT, runner.OllamaBackend = orig_root, orig_backend
        resp = read_jsonl(self.out / "responses.jsonl")
        self.assertEqual([r["response"] for r in resp], ["B"] * 4)
        self.assertEqual((self.out / "raw.jsonl").read_bytes(), self.raw)
        self.assertEqual((self.out / "run.json").read_bytes(), self.meta)

    def test_rederive_missing_run_dir(self):
        orig_root = runner.REPO_ROOT
        runner.REPO_ROOT = self.root
        try:
            with self.assertRaises(SystemExit):
                runner.main(["--run-id", "nope", "--rederive"])
        finally:
            runner.REPO_ROOT = orig_root
        self.assertFalse((self.root / runner.RUNS_DIR / "nope").exists())

    def test_probes_required_without_rederive(self):
        with self.assertRaises(SystemExit):
            runner.main(["--run-id", "r1"])


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


class MessagesTests(unittest.TestCase):
    """Backends take a list of messages; Part A sends one user message."""

    def test_part_a_sends_one_user_message_with_the_prompt(self):
        seen = []
        backend = FakeBackend(lambda m: seen.append(m) or "A", messages=True)
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "p.jsonl"
            write_jsonl(pf, probes())
            run(pf, Path(tmp) / "run", backend, prompt_suffix="/no_think")
        self.assertEqual(len(seen), 4)
        for m, p in zip(seen, probes()):
            self.assertEqual(m, [{"role": "user",
                                  "content": render_prompt(p, prompt_suffix="/no_think")}])

    def test_fake_backend_prompt_form_gets_last_user_text(self):
        b = FakeBackend(lambda prompt: prompt.upper())
        self.assertEqual(b.generate([{"role": "user", "content": "hi"}]), {"raw": "HI"})

    def test_fake_backend_rejects_bad_messages(self):
        b = FakeBackend(lambda m: "x", messages=True)
        for bad in ([], "hello", [{"role": "user"}], [{"role": "robot", "content": "x"}]):
            with self.assertRaises(ValueError):
                b.generate(bad)

    def test_generate_body_unchanged_for_one_message(self):
        b = OllamaBackend("qwen3:4b")
        self.assertEqual(b.request_body([{"role": "user", "content": "hello"}]),
                         b.request_body("hello"))
        self.assertEqual(set(b.request_body("hello")),
                         {"model", "prompt", "stream", "options"})

    def test_generate_endpoint_takes_one_user_message_only(self):
        b = OllamaBackend("qwen3:4b")
        with self.assertRaises(ValueError):
            b.request_body([{"role": "user", "content": "a"},
                            {"role": "assistant", "content": "b"},
                            {"role": "user", "content": "c"}])

    def test_chat_body(self):
        b = OllamaBackend("qwen3:4b", endpoint="/api/chat")
        msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"}]
        body = b.request_body(msgs)
        self.assertEqual(body["messages"], msgs)
        self.assertNotIn("prompt", body)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"], b.request_body("x")["options"])
        self.assertNotIn("think", body)
        self.assertNotIn("system", body)

    def test_chat_reply_read_from_message(self):
        b = OllamaBackend("qwen3:4b", endpoint="/api/chat")
        b._call = lambda path, body=None, timeout=30: {
            "message": {"role": "assistant", "content": "[]"}, "done_reason": "stop",
            "eval_count": 3}
        self.assertEqual(b.generate([{"role": "user", "content": "a"}]),
                         {"raw": "[]", "done_reason": "stop", "eval_count": 3})

    def test_unknown_endpoint(self):
        with self.assertRaises(ValueError):
            OllamaBackend("qwen3:4b", endpoint="/api/embed")


class RemoteBackendTests(unittest.TestCase):
    def test_stub_raises_when_called(self):
        b = runner.RemoteBackend("some-model", "SOME_KEY_VAR")
        with self.assertRaises(NotImplementedError) as cm:
            b.generate([{"role": "user", "content": "x"}])
        self.assertIn("stub", str(cm.exception))

    def test_describe_names_the_variable_only(self):
        import os
        os.environ.pop("P61_TEST_KEY", None)
        d = runner.RemoteBackend("m", "P61_TEST_KEY").describe()
        self.assertEqual(d["backend"], "remote")
        self.assertEqual(d["model"], "m")
        self.assertEqual(d["settings"]["key_env"], "P61_TEST_KEY")

    def test_key_env_must_be_a_name(self):
        with self.assertRaises(ValueError):
            runner.RemoteBackend("m", "not a name")

    def test_no_key_read(self):
        import os
        orig = os.environ
        class Trap(dict):
            def __getitem__(self, k):
                raise AssertionError("environment read")
            get = __getitem__
        os.environ = Trap()
        try:
            b = runner.RemoteBackend("m", "ANY_KEY")
            b.describe()
            with self.assertRaises(NotImplementedError):
                b.generate([{"role": "user", "content": "x"}])
        finally:
            os.environ = orig


if __name__ == "__main__":
    unittest.main()
