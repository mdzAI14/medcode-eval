"""The checker condition for Part A description-to-code probes
for ICD-10-CM FY2027 (October 1, 2026 release).

Input is a stored Part A run (the source run: run.json, raw.jsonl and
responses.jsonl, as medcode_eval.run.runner writes them). Its first answers
are reused; only second turns are ever sent.

For each description_to_code probe of the source run's probe file:
  first answer  the code that medcode_eval.part_a.score.parse_response reads
                from the stored response (responses.jsonl). No code read: no
                second turn, and the final answer is the first (invalid).
  check         medcode_eval.checker checks that one code. Only findings
                whose rule is in RULES (not_in_code_set, header_not_billable)
                count; every other rule is recorded in answers.jsonl and never
                sent. No such finding: no second turn, the final answer is
                the first.
  second turn   otherwise, once: the first prompt exactly as the Part A
                runner renders it (runner.render_prompt, with the source
                run's prompt_suffix), the stored first reply with think
                blocks dropped (runner.drop_think) as the assistant turn,
                then prompts/part_a_checker.txt with {findings} filled by
                part_b.render_findings and the same prompt_suffix rule. The
                reply is read with runner.read_reply and the source run's
                reader. There is never a third turn.

The backend must describe the same backend, model and settings as the
source run's run.json. A remote backend needs a ledger; the spending stop
(medcode_eval.run.spend) is checked before every request. A stop leaves the
run resumable: a rerun with the same output folder skips probes whose
second turn is stored and refuses if run.json would differ (only the cap may
differ; runner.same_inputs). A probe whose second turn is owed but not yet
stored is left out of answers.jsonl.

Output (runs/part_a/<run-id>/):
  run.json      code set, source run path and the sha256 of its raw.jsonl and
                responses.jsonl, probe file and sha256, sha256 of the two
                prompt files used, prompt_suffix, reader, the checker's
                reference files, the rules, the backend description, spend
  raw.jsonl     one row per second turn tried (turn 2, with the findings sent)
  answers.jsonl one row per description_to_code probe: id, first_answer,
                first_valid, rules (all rules the checker found), second_turn,
                final_answer, final_valid, error
  score.json, score.md   with --score (no model call)

Usage (from the repo root):
    venv/bin/python -m medcode_eval.run.part_a_checker --plan --source-run DIR \
        --run-id ID [--backend remote --model M ...]
    venv/bin/python -m medcode_eval.run.part_a_checker --source-run DIR --run-id ID \
        --backend remote --model M --key-env NAME --effort E --max-tokens N \
        --price-in P --price-out Q --max-usd C --ledger runs/spend/L.jsonl
    venv/bin/python -m medcode_eval.run.part_a_checker --score --run-id ID
"""

import argparse
import json
import re
import time
import urllib.error
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a import score as part_a_score
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_a.score import load_jsonl, parse_response
from medcode_eval.run import part_b, runner, spend
from medcode_eval.run.runner import (
    PROMPT_DIR,
    READERS,
    RemoteAbort,
    _append,
    _sha,
    check_messages,
    drop_think,
    read_reply,
    render_prompt,
    same_inputs,
    user_message,
)

PROMPT_FILE = "part_a_checker.txt"
FIRST_PROMPT_FILE = runner.PROMPT_FILES["description_to_code"]
RULES = ("not_in_code_set", "header_not_billable")
TYPE = "description_to_code"
SOURCE_FILES = ("run.json", "raw.jsonl", "responses.jsonl")
RUNS_DIR = runner.RUNS_DIR


def load_prompt():
    return (PROMPT_DIR / PROMPT_FILE).read_text(encoding="ascii")


def render_second(findings, prompt_suffix=""):
    """The second-turn prompt, without the file's trailing newline."""
    text = load_prompt().format_map({"findings": part_b.render_findings(findings)})
    return part_b._with_suffix(text.rstrip("\n"), prompt_suffix)


def _rel(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{path} is not under the repo root") from None


def load_source(source_dir, root=REPO_ROOT):
    """The source run, checked. Raises ValueError (nothing is written)."""
    d = Path(source_dir)
    for name in SOURCE_FILES:
        if not (d / name).is_file():
            raise ValueError(f"source run {d.name}: no {name}")
    meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
    for k in ("probes_file", "probes_sha256", "model", "settings"):
        if k not in meta:
            raise ValueError(f"source run {d.name}: run.json has no {k}")
    probes_path = Path(root) / meta["probes_file"]
    if not probes_path.is_file():
        raise ValueError(f"source run {d.name}: probe file {meta['probes_file']} not found")
    if _sha(probes_path) != meta["probes_sha256"]:
        raise ValueError(f"{meta['probes_file']} differs from the source run's probes_sha256")
    probes = load_jsonl(probes_path)
    code_sets = {p.get("code_set") for p in probes}
    if code_sets != {CODE_SET}:
        raise ValueError(f"probe file code sets {sorted(map(str, code_sets))}, "
                         f"expected only {CODE_SET!r}")
    raw = {}
    for r in load_jsonl(d / "raw.jsonl"):
        if r["id"] in raw:
            raise ValueError(f"source raw.jsonl has id {r['id']!r} twice")
        raw[r["id"]] = r
    lacking = [p["id"] for p in probes if p["id"] not in raw]
    if lacking:
        raise ValueError(f"probes without a raw row in the source run: {lacking[:10]}"
                         + (f" and {len(lacking) - 10} more" if len(lacking) > 10 else ""))
    responses = {}
    for r in load_jsonl(d / "responses.jsonl"):
        if r["id"] in responses:
            raise ValueError(f"source responses.jsonl has id {r['id']!r} twice")
        responses[r["id"]] = r
    readers = {r.get("reader") for r in responses.values()}
    if len(readers) != 1 or next(iter(readers)) not in READERS:
        raise ValueError(f"source responses.jsonl readers {sorted(map(str, readers))}; "
                         "expected exactly one known reader")
    suffix = meta.get("prompt_suffix", "")
    part_b._with_suffix("", suffix)
    return {"dir": d, "meta": meta, "probes": probes, "raw": raw, "responses": responses,
            "reader": next(iter(readers)), "prompt_suffix": suffix}


def items(src, data):
    """One entry per description_to_code probe: probe, first_response (the
    stored response or None), first (the code read, or None), rules (all
    rules found), send (the findings that count)."""
    out = []
    for p in src["probes"]:
        if p["type"] != TYPE:
            continue
        row = src["responses"].get(p["id"])
        response = row.get("response") if row else None
        first = parse_response(p, response)
        found = checker.check([first], data=data) if first is not None else []
        out.append({"probe": p, "first_response": response, "has_response": row is not None,
                    "first": first, "rules": [f["rule"] for f in found],
                    "send": [f for f in found if f["rule"] in RULES]})
    return out


def messages_for(src, item):
    """The three messages of an item's second turn."""
    p, sfx = item["probe"], src["prompt_suffix"]
    return check_messages([
        user_message(render_prompt(p, runner.load_prompts(), sfx)),
        {"role": "assistant", "content": drop_think(src["raw"][p["id"]]["raw"])},
        user_message(render_second(item["send"], sfx)),
    ])


def _match_backend(src, desc):
    for k in ("backend", "model", "settings"):
        if desc.get(k) != src["meta"].get(k):
            raise ValueError(f"the backend's {k} differs from the source run's")


def _meta(src, desc, data, ledger, root):
    d = src["dir"]
    return {
        "code_set": CODE_SET,
        "part": "a",
        "condition": "with_checker_description_to_code",
        "source_run": _rel(d, root),
        "source_raw_sha256": _sha(d / "raw.jsonl"),
        "source_responses_sha256": _sha(d / "responses.jsonl"),
        "probes_file": src["meta"]["probes_file"],
        "probes_sha256": src["meta"]["probes_sha256"],
        "prompts_sha256": {f: _sha(PROMPT_DIR / f) for f in (FIRST_PROMPT_FILE, PROMPT_FILE)},
        "prompt_suffix": src["prompt_suffix"],
        "reader": src["reader"],
        "checker": {"order_file": data.order_file, "tabular_file": data.tabular_file,
                    "tabular_version": data.tree.version},
        "rules": list(RULES),
        **desc,
        "spend": None if ledger is None else ledger.describe(runner._relative(ledger.path)),
    }


def run(source_dir, run_dir, backend, ledger=None, log=None, checker_data=None,
        root=REPO_ROOT):
    """Send the second turns not yet in raw.jsonl; returns the number tried."""
    src = load_source(source_dir, root)
    run_dir = Path(run_dir)
    if run_dir.resolve() == src["dir"].resolve():
        raise ValueError("the output folder is the source run")
    if ledger is None and getattr(backend, "name", None) == "remote":
        raise ValueError("a remote run needs a ledger (the spending stop)")
    desc = backend.describe()
    _match_backend(src, desc)
    data = checker_data or checker.default_data()
    meta = _meta(src, desc, data, ledger, root)
    meta_path = run_dir / "run.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        old.pop("started", None)
        if not same_inputs(old, meta):
            diff = sorted(k for k in set(old) | set(meta) if old.get(k) != meta.get(k))
            raise ValueError(f"run directory was made with other inputs: {diff}")
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps({**meta, "started": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z")}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_path = run_dir / "raw.jsonl"
    rows = {r["id"]: r for r in load_jsonl(raw_path)} if raw_path.exists() else {}
    its = items(src, data)
    tried = 0
    for it in its:
        pid = it["probe"]["id"]
        if not it["send"] or pid in rows:
            continue
        messages = messages_for(src, it)
        try:
            chars = spend.before(ledger, backend, messages)
        except spend.SpendStop as exc:
            if log:
                log(str(exc))
            break
        start = time.monotonic()
        row = {"id": pid, "turn": 2, "raw": None, "error": None, "findings": it["send"]}
        try:
            row.update(backend.generate(messages))
        except (OSError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        except RemoteAbort:
            write_answers(run_dir, src, its, rows)
            raise
        row["seconds"] = round(time.monotonic() - start, 3)
        spend.after(ledger, pid, 2, row, chars)
        _append(raw_path, row)
        rows[pid] = row
        tried += 1
        if log:
            log(f"{pid} turn 2 {row['seconds']:.1f}s"
                + (f" error {row['error']}" if row["error"] else ""))
    write_answers(run_dir, src, its, rows)
    return tried


def _finals(src, its, rows):
    """Per item: the item plus row2, final_response, final, owed."""
    out = []
    for it in its:
        p = it["probe"]
        r2 = rows.get(p["id"])
        f = dict(it, row2=r2, owed=bool(it["send"]) and r2 is None,
                 final_response=it["first_response"], final_missing=not it["has_response"],
                 final=it["first"], error=src["raw"][p["id"]].get("error"))
        if r2 is not None:
            f["error"] = r2["error"]
            if r2["error"] is None:
                f["final_response"] = read_reply(r2["raw"], p, src["reader"])
                f["final"] = parse_response(p, f["final_response"])
                f["final_missing"] = False
            else:
                f["final_response"], f["final"], f["final_missing"] = None, None, True
        out.append(f)
    return out


def write_answers(run_dir, src, its, rows):
    with open(Path(run_dir) / "answers.jsonl", "w", encoding="utf-8") as fh:
        for f in _finals(src, its, rows):
            if f["owed"]:
                continue
            fh.write(json.dumps({
                "id": f["probe"]["id"], "first_answer": f["first"],
                "first_valid": f["first"] is not None, "rules": f["rules"],
                "second_turn": f["row2"] is not None, "final_answer": f["final"],
                "final_valid": f["final"] is not None, "error": f["error"]},
                sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# plan

def plan(source_dir, checker_data=None, root=REPO_ROOT):
    """Counts and request sizes; no model call, nothing written."""
    src = load_source(source_dir, root)
    data = checker_data or checker.default_data()
    its = items(src, data)
    by_rule = {r: 0 for r in RULES}
    ignored = {}
    for it in its:
        for f in it["send"]:
            by_rule[f["rule"]] += 1
        for r in it["rules"]:
            if r not in RULES:
                ignored[r] = ignored.get(r, 0) + 1
    sizes = [spend.request_chars(messages_for(src, it)) for it in its if it["send"]]
    return {"code_set": CODE_SET, "source_run": _rel(src["dir"], root),
            "reader": src["reader"], "prompt_suffix": src["prompt_suffix"],
            "probes": len(its), "first_with_code": sum(it["first"] is not None for it in its),
            "findings_by_rule": by_rule, "other_rules_ignored": dict(sorted(ignored.items())),
            "second_turns": len(sizes),
            "request_chars": {"total": sum(sizes),
                              "mean": sum(sizes) / len(sizes) if sizes else None,
                              "largest": max(sizes) if sizes else None}}


def print_plan(p):
    rc = p["request_chars"]
    print(f"code set: {p['code_set']}")
    print(f"source run: {p['source_run']} (reader {p['reader']}, "
          f"prompt_suffix {p['prompt_suffix']!r})")
    print(f"description_to_code probes used: {p['probes']}")
    print(f"first answers with a code: {p['first_with_code']}")
    for r, n in p["findings_by_rule"].items():
        print(f"findings {r}: {n}")
    for r, n in p["other_rules_ignored"].items():
        print(f"other rule found, not sent, {r}: {n}")
    print(f"second turns that would be sent: {p['second_turns']}")
    mean = "n/a" if rc["mean"] is None else f"{rc['mean']:.1f}"
    print(f"request size in characters: total {rc['total']}, mean {mean}, "
          f"largest {rc['largest'] if rc['largest'] is not None else 'n/a'}")


# ---------------------------------------------------------------------------
# score

_GROUP_KEYS = ("n", "final_correct", "final_wrong_still_rule", "final_wrong_no_rule",
               "final_invalid", "final_same_as_first")


def _counts(probes, answers, reader):
    """n, correct, wrong, invalid, missing as medcode_eval.part_a.score scores."""
    g = part_a_score.score(probes, [{"id": i, "reader": reader, "response": r}
                                    for i, r in answers])["overall"]
    return {"n": g["n"], "correct": g["correct"],
            "wrong": g["n"] - g["correct"] - g["invalid"] - g["missing"],
            "invalid": g["invalid"], "missing": g["missing"]}


def _correct(probe, response, reader):
    return _counts([probe], [] if response is None else [(probe["id"], response)],
                   reader)["correct"] == 1


def score_run(run_dir, checker_data=None, root=REPO_ROOT, source_dir=None):
    """Write score.json and score.md in run_dir; returns the score.
    source_dir: read the source run from this folder instead of run.json's
    source_run (a copy of it elsewhere); the sha256 checks still apply."""
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    src = load_source(Path(source_dir) if source_dir is not None
                      else Path(root) / meta["source_run"], root)
    for name, key in (("raw.jsonl", "source_raw_sha256"),
                      ("responses.jsonl", "source_responses_sha256")):
        if _sha(src["dir"] / name) != meta[key]:
            raise ValueError(f"the source run's {name} differs from run.json's {key}")
    data = checker_data or checker.default_data()
    if meta["checker"] != {"order_file": data.order_file, "tabular_file": data.tabular_file,
                           "tabular_version": data.tree.version}:
        raise ValueError("the checker's reference files differ from run.json's")
    raw_path = run_dir / "raw.jsonl"
    rows = {r["id"]: r for r in load_jsonl(raw_path)} if raw_path.exists() else {}
    finals = _finals(src, items(src, data), rows)
    owed = sum(f["owed"] for f in finals)
    if owed:
        raise ValueError(f"{owed} second turns are still owed; resume the run first")
    reader = src["reader"]
    probes = [f["probe"] for f in finals]
    first = _counts(probes, [(f["probe"]["id"], f["first_response"]) for f in finals
                             if f["has_response"]], reader)
    final = _counts(probes, [(f["probe"]["id"], f["final_response"]) for f in finals
                             if not f["final_missing"]], reader)
    by_rule = {r: dict.fromkeys(_GROUP_KEYS, 0) for r in RULES}
    total = dict.fromkeys(_GROUP_KEYS, 0)
    for f in finals:
        if f["row2"] is None:
            continue
        rule = f["send"][0]["rule"]
        if f["final"] is None:
            k = "final_invalid"
        elif _correct(f["probe"], f["final_response"], reader):
            k = "final_correct"
        elif any(x["rule"] in RULES for x in checker.check([f["final"]], data=data)):
            k = "final_wrong_still_rule"
        else:
            k = "final_wrong_no_rule"
        for g in (by_rule[rule], total):
            g["n"] += 1
            g[k] += 1
            g["final_same_as_first"] += int(f["final"] == f["first"])
    source_score = src["dir"] / "score.json"
    stored = None
    matches = None
    if source_score.is_file():
        stored = json.loads(source_score.read_text(encoding="utf-8"))["by_type"].get(TYPE)
        matches = stored is not None and all(
            stored[k] == first[k] for k in ("n", "correct", "invalid", "missing"))
    result = {"code_set": CODE_SET, "source_run": meta["source_run"], "reader": reader,
              "model": meta["model"], "first": first, "final": final,
              "first_matches_source": matches, "source_score": stored,
              "second_turn": {"by_rule": by_rule, "total": total}}
    (run_dir / "score.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                                        encoding="ascii")
    (run_dir / "score.md").write_text(to_markdown(result), encoding="ascii")
    return result


def to_markdown(s):
    m = s["first_matches_source"]
    out = [f"Code set: {s['code_set']}. Source run: {s['source_run']}. Model: {s['model']}. "
           f"Reader: {s['reader']}. Probes: description_to_code.\n\n",
           "| Answer | n | Correct | Wrong | Invalid | Missing |\n|---|---|---|---|---|---|\n"]
    for name in ("first", "final"):
        g = s[name]
        out.append(f"| {name} | {g['n']} | {g['correct']} | {g['wrong']} | {g['invalid']} "
                   f"| {g['missing']} |\n")
    out.append("\nFirst-answer counts equal the source run's stored score: "
               + ("no stored score" if m is None else "yes" if m else "no") + ".\n\n")
    out.append("Probes with a second turn:\n\n| Rule | " + " | ".join(_GROUP_KEYS)
               + " |\n|---|" + "---|" * len(_GROUP_KEYS) + "\n")
    groups = list(s["second_turn"]["by_rule"].items()) + [("total", s["second_turn"]["total"])]
    for name, g in groups:
        out.append(f"| {name} | " + " | ".join(str(g[k]) for k in _GROUP_KEYS) + " |\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# command line

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="python -m medcode_eval.run.part_a_checker",
        description="Checker condition for Part A description-to-code probes of a stored "
                    "run (ICD-10-CM FY2027): one second turn for a code that is not in the "
                    "code set or is a header.")
    ap.add_argument("--source-run", help="folder of the stored Part A run")
    ap.add_argument("--run-id", required=True, help="output folder under runs/part_a/")
    ap.add_argument("--backend", choices=("remote",),
                    help="remote (the source run's backend; a second turn needs messages)")
    ap.add_argument("--model")
    ap.add_argument("--key-env", help="remote: NAME of the key variable in the repo's .env")
    ap.add_argument("--effort", help="remote: output_config.effort")
    ap.add_argument("--max-tokens", type=int, help="remote: max_tokens per request")
    ap.add_argument("--price-in", type=float, help="remote: USD per million input tokens")
    ap.add_argument("--price-out", type=float, help="remote: USD per million output tokens")
    ap.add_argument("--max-usd", type=float, help="remote: spending cap over the ledger")
    ap.add_argument("--ledger", help="remote: JSONL ledger under runs/spend/")
    ap.add_argument("--plan", action="store_true",
                    help="print counts and request sizes; no model call, no key read, "
                         "nothing written")
    ap.add_argument("--score", action="store_true",
                    help="write score.json and score.md for the run; no model call")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
        ap.error("run id: letters, digits, '.', '_' and '-' only")
    if args.plan and args.score:
        ap.error("--plan and --score cannot be combined")
    run_dir = REPO_ROOT / RUNS_DIR / args.run_id
    try:
        if args.score:
            s = score_run(run_dir)
            print(f"wrote {RUNS_DIR / args.run_id / 'score.json'} and score.md")
            print(f"first {s['first']}; final {s['final']}; "
                  f"first matches source: {s['first_matches_source']}")
            return
        if not args.source_run:
            ap.error("--source-run is required unless --score is given")
        source = Path(args.source_run)
        source = source if source.is_absolute() else REPO_ROOT / source
        if args.plan:
            p = plan(source)
            print_plan(p)
            if args.backend is not None:
                if args.model is None:
                    ap.error("--backend remote needs --model")
                runner._ledger(ap, args)          # options checked; nothing written
                _match_backend(load_source(source), runner._remote(args).describe())
                print("backend, model and settings equal the source run's: yes")
            else:
                print("backend not checked (no --backend given)")
            return
        if args.backend is None:
            ap.error("--backend remote is required for a run")
        if args.model is None:
            ap.error("--backend remote needs --model")
        ledger = runner._ledger(ap, args)
        backend = runner._remote(args)
        try:
            n = run(source, run_dir, backend, ledger=ledger, log=print)
        except RemoteAbort as exc:
            print(f"run aborted: {exc}")
            raise SystemExit(2)
        print(f"second turns tried {n}")
        runner._end(ledger)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
