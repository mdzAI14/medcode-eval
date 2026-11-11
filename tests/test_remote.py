"""Tests for the remote backend, the spending stop and the usage summary.

Every request goes to a fake transport; no test opens a network
connection. Keys, prices and usage numbers are invented.
"""

import json
import tempfile
import unittest
from pathlib import Path

from medcode_eval.run import part_b, runner, spend, usage
from medcode_eval.run.runner import RemoteAbort, RemoteBackend, RemoteError, run
from tests.part_b_fixture import CASES, TempDir, make_data_dir, make_refdata
from tests.test_run import probes, read_jsonl, write_jsonl

FAKE_KEY = "fake-key-0123456789abcdef"


def setUpModule():
    global TMP, DATA
    TMP = tempfile.TemporaryDirectory()
    DATA = make_refdata(TMP.name)


def tearDownModule():
    TMP.cleanup()


def reply_body(text="ok", usage_=None, stop="end_turn", extra_blocks=()):
    content = [{"type": b} for b in extra_blocks] + [{"type": "text", "text": text}]
    return json.dumps({"id": "msg_x", "type": "message", "model": "m-1", "role": "assistant",
                       "content": content, "stop_reason": stop,
                       "usage": usage_ or {"input_tokens": 10, "output_tokens": 5}}).encode()


def error_body(etype="invalid_request_error", msg="bad thing"):
    return json.dumps({"type": "error", "error": {"type": etype, "message": msg}}).encode()


class FakeTransport:
    """Returns queued (status, headers, body) answers and records calls."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": dict(headers),
                           "body": json.loads(body.decode()), "timeout": timeout})
        a = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(a, BaseException):
            raise a
        return a


def make_env(dirpath, line=f"ANTHROPIC_API_KEY={FAKE_KEY}\n"):
    p = Path(dirpath) / ".env"
    p.write_text("OTHER=1\n" + line, encoding="utf-8")
    return p


class RemoteBackendTests(unittest.TestCase):
    def setUp(self):
        self.dir = TempDir(self).path
        self.env = make_env(self.dir)
        self.sleeps = []

    def backend(self, answers, **kw):
        self.t = FakeTransport(answers)
        return RemoteBackend("m-1", "ANTHROPIC_API_KEY", effort="medium", max_tokens=100,
                             env_file=self.env, transport=self.t, sleep=self.sleeps.append,
                             **kw)

    def test_request_shape(self):
        b = self.backend([(200, {}, reply_body())])
        msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"}]
        b.generate(msgs)
        c = self.t.calls[0]
        self.assertEqual(c["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(c["headers"], {"x-api-key": FAKE_KEY,
                                        "anthropic-version": "2023-06-01",
                                        "content-type": "application/json"})
        self.assertEqual(c["body"], {"model": "m-1", "max_tokens": 100,
                                     "output_config": {"effort": "medium"},
                                     "messages": msgs})
        self.assertEqual(c["timeout"], 300)

    def test_reply_fields(self):
        u = {"input_tokens": 12, "output_tokens": 30, "cache_read_input_tokens": 0,
             "output_tokens_details": {"thinking_tokens": 20}}
        b = self.backend([(200, {}, reply_body("[\"A1\"]", u, "max_tokens",
                                               ("thinking", "thinking")))])
        out = b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(out["raw"], "[\"A1\"]")
        self.assertEqual(out["reply_id"], "msg_x")
        self.assertEqual(out["reply_model"], "m-1")
        self.assertEqual(out["stop_reason"], "max_tokens")
        self.assertEqual(out["usage"], u)
        self.assertEqual(out["block_types"], {"thinking": 2, "text": 1})
        self.assertEqual(out["http_status"], 200)
        self.assertNotIn("thinking", json.dumps(out["raw"]))

    def test_text_blocks_concatenated_others_not_stored(self):
        body = json.dumps({"id": "i", "model": "m", "stop_reason": "end_turn",
                           "usage": {"input_tokens": 1, "output_tokens": 1},
                           "content": [{"type": "text", "text": "ab"},
                                       {"type": "thinking", "thinking": "SECRETTHOUGHT"},
                                       {"type": "text", "text": "cd"}]}).encode()
        out = self.backend([(200, {}, body)]).generate([{"role": "user", "content": "x"}])
        self.assertEqual(out["raw"], "abcd")
        self.assertNotIn("SECRETTHOUGHT", json.dumps(out))

    def test_key_read_at_first_request_only(self):
        self.env.unlink()
        b = self.backend([(200, {}, reply_body())])
        b.describe()  # no key needed
        make_env(self.dir)
        b.generate([{"role": "user", "content": "x"}])
        self.env.unlink()
        b.generate([{"role": "user", "content": "y"}])  # held in memory
        self.assertEqual(len(self.t.calls), 2)

    def test_key_never_in_repr_describe_or_errors(self):
        b = self.backend([(401, {}, error_body("authentication_error", "invalid x-api-key"))])
        with self.assertRaises(RemoteAbort) as cm:
            b.generate([{"role": "user", "content": "x"}])
        for s in (repr(b), str(b), json.dumps(b.describe()), str(cm.exception),
                  repr(cm.exception)):
            self.assertNotIn(FAKE_KEY, s)
        self.assertIn("401", str(cm.exception))
        self.assertIn("authentication_error", str(cm.exception))
        self.assertIn("invalid x-api-key", str(cm.exception))

    def test_missing_key_aborts_without_value(self):
        make_env(self.dir, "ANTHROPIC_API_KEY=\n")
        with self.assertRaises(RemoteAbort):
            self.backend([(200, {}, reply_body())]).generate([{"role": "user", "content": "x"}])
        self.assertEqual(self.t.calls, [])

    def test_quoted_and_exported_key(self):
        make_env(self.dir, f'export ANTHROPIC_API_KEY="{FAKE_KEY}"\n')
        b = self.backend([(200, {}, reply_body())])
        b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(self.t.calls[0]["headers"]["x-api-key"], FAKE_KEY)

    def test_abort_statuses(self):
        for status in (400, 401, 403, 404):
            b = self.backend([(status, {}, error_body())])
            with self.assertRaises(RemoteAbort):
                b.generate([{"role": "user", "content": "x"}])
            self.assertEqual(len(self.t.calls), 1)
        self.assertFalse(issubclass(RemoteAbort, (OSError, ValueError, TimeoutError)))

    def test_retry_schedule_then_success(self):
        b = self.backend([(529, {}, error_body("overloaded_error")),
                          (500, {}, error_body("api_error")),
                          (503, {}, error_body()), (200, {}, reply_body())])
        out = b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(out["raw"], "ok")
        self.assertEqual(self.sleeps, [5, 15, 45])
        self.assertEqual(out["attempts"], 4)

    def test_retry_after_header_used(self):
        b = self.backend([(429, {"retry-after": "7"}, error_body("rate_limit_error")),
                          (200, {}, reply_body())])
        b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(self.sleeps, [7.0])

    def test_retries_exhausted_is_item_error(self):
        b = self.backend([(502, {}, error_body("api_error"))])
        with self.assertRaises(RemoteError) as cm:
            b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(len(self.t.calls), 4)
        self.assertEqual(self.sleeps, [5, 15, 45])
        self.assertIn("502", str(cm.exception))

    def test_other_status_is_item_error_no_retry(self):
        b = self.backend([(418, {}, b"not json")])
        with self.assertRaises(RemoteError):
            b.generate([{"role": "user", "content": "x"}])
        self.assertEqual(len(self.t.calls), 1)
        self.assertTrue(issubclass(RemoteError, ValueError))

    def test_describe(self):
        d = self.backend([(200, {}, reply_body())]).describe()
        self.assertEqual(d["backend"], "remote")
        self.assertEqual(d["model"], "m-1")
        s = d["settings"]
        self.assertEqual(s["api_version"], "2023-06-01")
        self.assertEqual(s["key_env"], "ANTHROPIC_API_KEY")
        self.assertEqual(s["effort"], "medium")
        self.assertEqual(s["max_tokens"], 100)
        self.assertEqual(s["timeout_seconds"], 300)
        self.assertEqual(self.t.calls, [])

    def test_key_env_must_be_a_name(self):
        with self.assertRaises(ValueError):
            RemoteBackend("m", "not a name", effort="medium", max_tokens=1)

    def test_part_a_run_through_remote(self):
        pf = self.dir / "probes.jsonl"
        write_jsonl(pf, probes())
        b = self.backend([(200, {}, reply_body("Answer: B"))])
        led = spend.Ledger(self.dir / "spend" / "l.jsonl", 1.0, 2.0, 5.0, run_id="r")
        run(pf, self.dir / "out", b, ledger=led)
        raw = read_jsonl(self.dir / "out" / "raw.jsonl")
        self.assertEqual(len(raw), 4)
        for r in raw:
            self.assertEqual(r["stop_reason"], "end_turn")
            self.assertEqual(r["usage"], {"input_tokens": 10, "output_tokens": 5})
            self.assertIn("request_chars", r)
        self.assertEqual(len(read_jsonl(self.dir / "spend" / "l.jsonl")), 4)
        meta = json.loads((self.dir / "out" / "run.json").read_text())
        self.assertEqual(meta["spend"], {"price_in_usd_per_mtok": 1.0,
                                         "price_out_usd_per_mtok": 2.0, "max_usd": 5.0,
                                         "ledger": "l.jsonl"})
        self.assertNotIn(FAKE_KEY, (self.dir / "out" / "raw.jsonl").read_text())
        self.assertNotIn(FAKE_KEY, (self.dir / "out" / "run.json").read_text())

    def test_abort_ends_run(self):
        pf = self.dir / "probes.jsonl"
        write_jsonl(pf, probes())
        b = self.backend([(200, {}, reply_body()), (401, {}, error_body())])
        led = spend.Ledger(self.dir / "l.jsonl", 1.0, 2.0, 5.0, run_id="r")
        with self.assertRaises(RemoteAbort):
            run(pf, self.dir / "out", b, ledger=led)
        self.assertEqual(len(read_jsonl(self.dir / "out" / "raw.jsonl")), 1)
        self.assertEqual(len(self.t.calls), 2)

    def test_remote_run_needs_ledger(self):
        pf = self.dir / "probes.jsonl"
        write_jsonl(pf, probes())
        with self.assertRaises(ValueError):
            run(pf, self.dir / "out", self.backend([(200, {}, reply_body())]))
        self.assertEqual(self.t.calls, [])


class MeteredFake(runner.FakeBackend):
    """A fake backend that reports usage, like the remote one."""

    def __init__(self, fn, out_tokens=100, max_tokens=1000, messages=False):
        super().__init__(fn, messages=messages)
        self.max_tokens = max_tokens
        self.out_tokens = out_tokens
        self.calls = 0

    def generate(self, messages):
        out = super().generate(messages)
        self.calls += 1
        n = sum(len(m["content"]) for m in messages)
        return {**out, "stop_reason": "end_turn",
                "usage": {"input_tokens": n // 4, "cache_read_input_tokens": 2,
                          "output_tokens": self.out_tokens}}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.dir = TempDir(self).path
        self.path = self.dir / "spend" / "l.jsonl"

    def test_cost_counts_cache_fields_at_input_price(self):
        led = spend.Ledger(self.path, 4.0, 20.0, 5.0, run_id="r")
        u = {"input_tokens": 1000, "cache_creation_input_tokens": 500,
             "cache_read_input_tokens": 500, "output_tokens": 100,
             "cache_creation": {"ephemeral_5m_input_tokens": 500},
             "output_tokens_details": {"thinking_tokens": 50}}
        self.assertAlmostEqual(led.cost(u), (2000 * 4 + 100 * 20) / 1e6)

    def test_record_and_total_shared(self):
        a = spend.Ledger(self.path, 1.0, 1.0, 5.0, run_id="a")
        b = spend.Ledger(self.path, 1.0, 1.0, 5.0, run_id="b")
        a.record("x", 1, {"input_tokens": 1_000_000, "output_tokens": 0}, 10)
        b.record("y", 2, {"input_tokens": 0, "output_tokens": 500_000}, 10)
        self.assertAlmostEqual(a.total(), 1.5)
        rows = read_jsonl(self.path)
        self.assertEqual([(r["run_id"], r["item_id"], r["turn"]) for r in rows],
                         [("a", "x", 1), ("b", "y", 2)])
        for r in rows:
            self.assertEqual(set(r), {"time", "run_id", "item_id", "turn", "usage",
                                      "cost_usd", "request_chars"})

    def test_worst_case(self):
        led = spend.Ledger(self.path, 3.0, 10.0, 5.0, run_id="r")
        self.assertAlmostEqual(led.worst_case(3000, 1000), (1000 * 3 + 1000 * 10) / 1e6)

    def test_check_refuses_when_total_plus_worst_passes_cap(self):
        led = spend.Ledger(self.path, 1.0, 1.0, 1.0, run_id="r")
        led.record("x", 1, {"input_tokens": 900_000, "output_tokens": 0}, 0)
        led.check(3 * 50_000, 50_000)  # 0.9 + 0.1 = 1.0: allowed
        with self.assertRaises(spend.SpendStop):
            led.check(3 * 50_000, 50_001)

    def test_options_validated(self):
        for bad in ((-1, 1, 1), (1, -1, 1), (1, 1, 0)):
            with self.assertRaises(ValueError):
                spend.Ledger(self.path, *bad, run_id="r")


class SpendStopRunTests(unittest.TestCase):
    """The stop fires before the request that could cross the cap, never after."""

    def setUp(self):
        self.dir = TempDir(self).path
        self.pf = self.dir / "probes.jsonl"
        write_jsonl(self.pf, probes())
        self.lpath = self.dir / "spend" / "l.jsonl"

    def test_part_a_stops_before_crossing(self):
        # price 1 USD per token each way makes the arithmetic plain
        b = MeteredFake(lambda p: "A", out_tokens=10, max_tokens=20)
        prompts = [runner.render_prompt(p) for p in probes()]
        worst = [len(p) / 3 + 20 for p in prompts]
        spent = [len(p) // 4 + 2 + 10 for p in prompts]
        # cap allows exactly two requests: after two, the third's worst case passes it
        cap = spent[0] + spent[1] + worst[2] - 0.5
        self.assertGreaterEqual(cap, spent[0] + worst[1])
        led = spend.Ledger(self.lpath, 1e6, 1e6, cap, run_id="r")
        n = run(self.pf, self.dir / "out", b, ledger=led)
        self.assertEqual(n, 2)
        self.assertEqual(b.calls, 2)
        self.assertIsNotNone(led.stopped)
        self.assertLessEqual(led.total(), cap)
        self.assertEqual(len(read_jsonl(self.dir / "out" / "raw.jsonl")), 2)
        self.assertEqual(len(read_jsonl(self.dir / "out" / "responses.jsonl")), 2)
        self.assertEqual(len(read_jsonl(self.lpath)), 2)
        # resumable: a higher cap continues where it stopped
        led2 = spend.Ledger(self.lpath, 1e6, 1e6, cap * 10, run_id="r")
        run(self.pf, self.dir / "out", b, ledger=led2)
        self.assertEqual(b.calls, 4)
        self.assertIsNone(led2.stopped)

    def test_existing_ledger_counts(self):
        led = spend.Ledger(self.lpath, 1.0, 1.0, 1.0, run_id="other")
        led.record("z", 1, {"input_tokens": 1_000_000, "output_tokens": 0}, 0)
        b = MeteredFake(lambda p: "A")
        led2 = spend.Ledger(self.lpath, 1.0, 1.0, 1.0, run_id="r")
        self.assertEqual(run(self.pf, self.dir / "out", b, ledger=led2), 0)
        self.assertEqual(b.calls, 0)
        self.assertIsNotNone(led2.stopped)

    def test_part_b_stop_before_second_turn_is_resumable(self):
        data = make_data_dir(self.dir)
        out = self.dir / "b"
        b = MeteredFake(lambda m: '["U90.012"]', out_tokens=10, max_tokens=20, messages=True)
        first = part_b.render_first(part_b.load_cases(data)[0])
        # room for the first turn of the first case only
        cap = len(first) // 4 + 2 + 10 + 1
        led = spend.Ledger(self.lpath, 1e6, 1e6, cap + len(first) / 3 + 20, run_id="b")
        part_b.run(data, out, b, "with_checker", checker_data=DATA, ledger=led)
        self.assertEqual(b.calls, 1)
        self.assertIsNotNone(led.stopped)
        self.assertEqual(read_jsonl(out / "answers.jsonl"), [])
        led2 = spend.Ledger(self.lpath, 1e6, 1e6, 1e12, run_id="b")
        part_b.run(data, out, b, "with_checker", checker_data=DATA, ledger=led2)
        raw = read_jsonl(out / "raw.jsonl")
        self.assertEqual(sorted((r["id"], r["turn"]) for r in raw),
                         sorted((c, t) for c in CASES for t in (1, 2)))
        self.assertEqual(len(read_jsonl(self.lpath)), 6)
        self.assertEqual({r["turn"] for r in read_jsonl(self.lpath)}, {1, 2})

    def test_resume_refuses_other_prices_or_ledger(self):
        b = MeteredFake(lambda p: "A")
        run(self.pf, self.dir / "out", b, limit=1,
            ledger=spend.Ledger(self.lpath, 1.0, 1.0, 5.0, run_id="r"))
        for args in ((self.lpath, 2.0, 1.0, 5.0), (self.lpath, 1.0, 2.0, 5.0),
                     (self.dir / "spend" / "other.jsonl", 1.0, 1.0, 5.0)):
            with self.assertRaises(ValueError):
                run(self.pf, self.dir / "out", b, ledger=spend.Ledger(*args, run_id="r"))
        self.assertEqual(b.calls, 1)

    def test_no_ledger_for_fake_leaves_part_a_unchanged(self):
        run(self.pf, self.dir / "out", runner.FakeBackend(lambda p: "A"))
        meta = json.loads((self.dir / "out" / "run.json").read_text())
        self.assertNotIn("spend", meta)
        for r in read_jsonl(self.dir / "out" / "raw.jsonl"):
            self.assertEqual(set(r), {"id", "raw", "error", "seconds"})


class CliTests(unittest.TestCase):
    def setUp(self):
        self.root = TempDir(self).path
        self.orig = runner.REPO_ROOT
        runner.REPO_ROOT = self.root
        self.addCleanup(setattr, runner, "REPO_ROOT", self.orig)
        self.built = []
        orig_cls = runner.RemoteBackend

        def trap(*a, **k):
            self.built.append((a, k))
            raise AssertionError("backend built")
        runner.RemoteBackend = trap
        self.addCleanup(setattr, runner, "RemoteBackend", orig_cls)

    BASE = ["--backend", "remote", "--model", "m", "--key-env", "K", "--effort", "medium",
            "--max-tokens", "10", "--probes", "p.jsonl", "--run-id", "r"]
    SPEND = ["--price-in", "1", "--price-out", "2", "--max-usd", "1",
             "--ledger", "runs/spend/x.jsonl"]

    def test_remote_needs_all_four_spend_options(self):
        for drop in range(4):
            argv = self.BASE + self.SPEND[:2 * drop] + self.SPEND[2 * drop + 2:]
            with self.assertRaises(SystemExit):
                runner.main(argv)
        self.assertEqual(self.built, [])

    def test_ledger_must_be_under_runs_spend(self):
        argv = self.BASE + self.SPEND[:-1] + ["runs/part_a/x.jsonl"]
        with self.assertRaises(SystemExit):
            runner.main(argv)
        self.assertEqual(self.built, [])

    def test_remote_needs_effort_and_max_tokens(self):
        for i in (6, 8):
            argv = self.BASE[:i] + self.BASE[i + 2:] + self.SPEND
            with self.assertRaises(SystemExit):
                runner.main(argv)
        self.assertEqual(self.built, [])


class UsageSummaryTests(unittest.TestCase):
    def test_summary(self):
        d = TempDir(self).path
        (d / "run.json").write_text(json.dumps({"spend": {
            "price_in_usd_per_mtok": 4.0, "price_out_usd_per_mtok": 20.0,
            "max_usd": 5.0, "ledger": "runs/spend/x.jsonl"}}))
        rows = [
            {"id": "a", "turn": 1, "error": None, "request_chars": 400,
             "stop_reason": "end_turn",
             "usage": {"input_tokens": 120, "cache_read_input_tokens": 0,
                       "output_tokens": 50,
                       "output_tokens_details": {"thinking_tokens": 30}}},
            {"id": "a", "turn": 2, "error": None, "request_chars": 800,
             "stop_reason": "max_tokens",
             "usage": {"input_tokens": 230, "output_tokens": 150}},
            {"id": "b", "turn": 1, "error": "x", "raw": None},
        ]
        write_jsonl(d / "raw.jsonl", rows)
        s = usage.summarize(d)
        self.assertEqual(s["replies"], 2)
        self.assertEqual(s["input_tokens"]["total"], 350)
        self.assertAlmostEqual(s["input_tokens"]["mean"], 175)
        self.assertEqual(s["output_tokens"]["total"], 200)
        self.assertEqual(s["thinking_tokens"], {"replies_with_field": 1, "total": 30})
        self.assertEqual(s["stop_reasons"], {"end_turn": 1, "max_tokens": 1})
        self.assertAlmostEqual(s["cost_usd"], (350 * 4 + 200 * 20) / 1e6)
        self.assertAlmostEqual(s["input_ratio_to_chars_div_4"], 350 / 300)
        self.assertEqual(s["per_item"]["a"]["input_tokens"], 350)
        self.assertEqual(s["per_item"]["a"]["output_tokens"], 200)
        self.assertAlmostEqual(s["per_item"]["a"]["cost_usd"], s["cost_usd"])
        self.assertIn("replies", usage.to_markdown(s))


class PartBScoreStopReasonTests(unittest.TestCase):
    def test_not_end_turn_counted(self):
        from medcode_eval.part_b import score
        root = TempDir(self).path
        data = make_data_dir(root)
        answers = [{"id": "b-t-001", "first_answer": ["U95"], "final_answer": ["U95"],
                    "first_valid": True, "final_valid": True, "second_turn": False,
                    "error": None, "stop_reasons": {"1": "max_tokens"}},
                   {"id": "b-t-002", "first_answer": [], "final_answer": [],
                    "first_valid": True, "final_valid": True, "second_turn": False,
                    "error": None, "stop_reasons": {"1": "end_turn"}}]
        r = score.score(score.load_gold(data), score.load_case_meta(data), answers,
                        checker_data=DATA)
        self.assertEqual(r["not_end_turn"], 1)
        self.assertEqual(r["stop_reasons"], {"end_turn": 1, "max_tokens": 1})
        self.assertIn("not end_turn: 1", score.to_markdown(r))

    def test_answers_carry_stop_reasons(self):
        root = TempDir(self).path
        data = make_data_dir(root)
        out = root / "o"
        b = MeteredFake(lambda m: '["U95"]', messages=True)
        led = spend.Ledger(root / "l.jsonl", 1.0, 1.0, 5.0, run_id="o")
        part_b.run(data, out, b, "plain", checker_data=DATA, ledger=led)
        for a in read_jsonl(out / "answers.jsonl"):
            self.assertEqual(a["stop_reasons"], {"1": "end_turn"})


if __name__ == "__main__":
    unittest.main()
