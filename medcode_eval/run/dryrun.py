"""Dry-run: render every first-turn prompt and estimate input size and cost
for ICD-10-CM FY2027 (October 1, 2026 release). No backend is built and no
model is called.

Sets: Part A lite, full and changes (data/part_a/probes_*.jsonl); Part B
plain and with_checker for the cases in data/cases/ (their first turns are
the same text).

Token estimate: characters / CHARS_PER_TOKEN (4), rounded. No tokenizer is
installed, so this is an estimate, not a count. It leaves out the chat
template the server wraps around each message.

with_checker upper bound for the second turn: every case is assumed to get
one. Its input is the first prompt, the first reply (assumed output size)
and the second prompt with a findings block of ASSUMED_FINDINGS_CHARS
characters.

Output tokens are assumptions for two kinds of model:
  direct     answers without reasoning: DIRECT_OUTPUT tokens per answer
  reasoning  reasons first: the mean eval_count of the rows in
             REASONING_SOURCE (a Part A run with reasoning on) when that
             file has any; otherwise DEFAULT_REASONING_OUTPUT
Cost = input tokens / 1e6 * P_in + output tokens / 1e6 * P_out, with P_in
and P_out the prices per million input and output tokens, supplied by the
reader. No price is stored here.

Output in runs/dryrun/<id>/: one JSONL file of {id, prompt} per set,
part_b_prompts/<case id>.txt, summary.json and summary.md.
"""

import json
from pathlib import Path

from medcode_eval.part_a.generate import CODE_SET
from medcode_eval.part_a.score import load_jsonl
from medcode_eval.run import part_b
from medcode_eval.run.runner import _relative, load_prompts, render_prompt

CHARS_PER_TOKEN = 4
ASSUMED_FINDINGS_CHARS = 1200   # about three findings of 400 characters, note text included
DIRECT_OUTPUT = {"part_a": 5, "part_b": 40}
DEFAULT_REASONING_OUTPUT = 1000
SCALE_CASES = 60
PART_A_SETS = {"lite": "data/part_a/probes_lite.jsonl",
               "full": "data/part_a/probes_full.jsonl",
               "changes": "data/part_a/probes_changes.jsonl"}
REASONING_SOURCE = "runs/part_a/lite-qwen3-4b/raw.jsonl"
DRYRUN_DIR = Path("runs") / "dryrun"


def tokens(chars):
    return round(chars / CHARS_PER_TOKEN)


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def reasoning_output(source):
    p = Path(source)
    counts = []
    if p.is_file():
        counts = [r["eval_count"] for r in load_jsonl(p)
                  if isinstance(r.get("eval_count"), int)]
    if counts:
        return {"tokens_per_answer": round(sum(counts) / len(counts)), "n": len(counts),
                "source": _relative(p), "how": "mean eval_count of the rows that have one"}
    return {"tokens_per_answer": DEFAULT_REASONING_OUTPUT, "n": None,
            "source": None, "how": f"default; {_relative(p)} has no eval_count rows"}


def dry_run(out_dir, part_a_sets, data_dir, prompt_suffix="", reasoning_source=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    prompts_a = load_prompts()
    for name, path in part_a_sets.items():
        rendered = [{"id": p["id"], "prompt": render_prompt(p, prompts_a, prompt_suffix)}
                    for p in load_jsonl(path)]
        _write_jsonl(out / f"part_a_{name}.jsonl", rendered)
        chars = sum(len(r["prompt"]) for r in rendered)
        rows.append({"set": f"part_a_{name}", "condition": None, "source": _relative(path),
                     "prompts": len(rendered), "input_chars": chars,
                     "input_tokens_est": tokens(chars)})
    cases = part_b.load_cases(data_dir)
    prompts_b = part_b.load_prompts()
    rendered = [{"id": c["id"], "prompt": part_b.render_first(c, prompts_b, prompt_suffix)}
                for c in cases]
    (out / "part_b_prompts").mkdir(exist_ok=True)
    for r in rendered:
        (out / "part_b_prompts" / f"{r['id']}.txt").write_text(r["prompt"] + "\n",
                                                                encoding="utf-8")
    chars = sum(len(r["prompt"]) for r in rendered)
    second = part_b.render_second_template_chars(ASSUMED_FINDINGS_CHARS, prompt_suffix)
    for cond in part_b.CONDITIONS:
        _write_jsonl(out / f"part_b_{cond}.jsonl", rendered)
        row = {"set": "part_b", "condition": cond, "source": _relative(Path(data_dir) / "cases"),
               "prompts": len(rendered), "input_chars": chars,
               "input_tokens_est": tokens(chars)}
        if cond == "with_checker":
            row["second_turn_upper"] = {
                "turns": len(rendered), "history_chars": chars,
                "second_prompt_chars": len(rendered) * second,
                "second_prompt_chars_each": second,
                "assumed_findings_chars": ASSUMED_FINDINGS_CHARS}
        rows.append(row)

    reasoning = reasoning_output(reasoning_source or REASONING_SOURCE)
    assumptions = {
        "direct": {"part_a": DIRECT_OUTPUT["part_a"], "part_b": DIRECT_OUTPUT["part_b"],
                   "how": "assumed: a one-word Part A answer; a JSON list of a few codes"},
        "reasoning": reasoning,
    }
    cost = _cost_rows(rows, assumptions)
    summary = {"code_set": CODE_SET, "prompt_suffix": prompt_suffix,
               "chars_per_token": CHARS_PER_TOKEN, "rows": rows,
               "output_assumptions": assumptions, "cost": cost,
               "scale_cases": SCALE_CASES}
    (out / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n",
                                      encoding="utf-8")
    (out / "summary.md").write_text(to_markdown(summary), encoding="utf-8")
    return summary


def _formula(i, o):
    return f"{i / 1e6:.6f} * P_in + {o / 1e6:.6f} * P_out"


def _cost_rows(rows, assumptions):
    out = []
    plain = next(r for r in rows if r["condition"] == "plain")
    chk = next(r for r in rows if r["condition"] == "with_checker")
    n = plain["prompts"]
    for kind in ("direct", "reasoning"):
        per_a = (assumptions[kind]["part_a"] if kind == "direct"
                 else assumptions[kind]["tokens_per_answer"])
        per_b = (assumptions[kind]["part_b"] if kind == "direct"
                 else assumptions[kind]["tokens_per_answer"])

        def add(row, i, o, note=""):
            out.append({"model_kind": kind, "row": row, "input_tokens": i,
                        "output_tokens": o, "formula": _formula(i, o), "note": note})
        for r in rows:
            if r["set"].startswith("part_a_"):
                add(r["set"], r["input_tokens_est"], r["prompts"] * per_a)
        add("part_b_plain", plain["input_tokens_est"], n * per_b)
        b = chk["second_turn_upper"]
        second_in = tokens(b["history_chars"] + b["second_prompt_chars"]) + b["turns"] * per_b
        with_in = chk["input_tokens_est"] + second_in
        add("part_b_with_checker", with_in, (n + b["turns"]) * per_b,
            "upper bound: every case gets a second turn")
        if n:
            add(f"part_b_plain_x{SCALE_CASES}", round(plain["input_tokens_est"] * SCALE_CASES / n),
                SCALE_CASES * per_b, f"scaled from {n} cases")
            add(f"part_b_with_checker_x{SCALE_CASES}", round(with_in * SCALE_CASES / n),
                2 * SCALE_CASES * per_b, f"scaled from {n} cases; upper bound")
    return out


def to_markdown(s):
    lines = [f"Code set: {s['code_set']}. prompt_suffix: {s['prompt_suffix']!r}.", "",
             f"Estimated tokens = characters / {s['chars_per_token']} (an estimate; no "
             "tokenizer is installed; the server's chat template is not counted).", "",
             "| Set | Condition | Prompts | Input chars | Est. input tokens |",
             "|---|---|---|---|---|"]
    for r in s["rows"]:
        lines.append(f"| {r['set']} | {r['condition'] or ''} | {r['prompts']} "
                     f"| {r['input_chars']} | {r['input_tokens_est']} |")
    for r in s["rows"]:
        b = r.get("second_turn_upper")
        if b:
            lines += ["", f"with_checker second turn, upper bound: {b['turns']} turns; each "
                      f"resends the first prompt and the first reply, plus a second prompt of "
                      f"{b['second_prompt_chars_each']} characters with an assumed findings "
                      f"block of {b['assumed_findings_chars']} characters."]
    a = s["output_assumptions"]
    lines += ["", f"Output tokens per answer: direct model {a['direct']['part_a']} (Part A), "
              f"{a['direct']['part_b']} (Part B), {a['direct']['how']}; reasoning model "
              f"{a['reasoning']['tokens_per_answer']} ({a['reasoning']['how']}"
              + (f", n = {a['reasoning']['n']}, from {a['reasoning']['source']}"
                 if a['reasoning']['n'] else "") + ").", "",
              "| Model kind | Row | Input tokens | Output tokens | Cost (P_in, P_out per "
              "million tokens) | Note |", "|---|---|---|---|---|---|"]
    for c in s["cost"]:
        lines.append(f"| {c['model_kind']} | {c['row']} | {c['input_tokens']} "
                     f"| {c['output_tokens']} | {c['formula']} | {c['note']} |")
    return "\n".join(lines) + "\n"


def main_dry_run(repo_root, run_id, prompt_suffix=""):
    root = Path(repo_root)
    out = root / DRYRUN_DIR / run_id
    dry_run(out, {k: root / v for k, v in PART_A_SETS.items()}, root / "data",
            prompt_suffix=prompt_suffix, reasoning_source=root / REASONING_SOURCE)
    return DRYRUN_DIR / run_id
