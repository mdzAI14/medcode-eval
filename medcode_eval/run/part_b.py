"""Put Part B cases in front of a model, with or without the checker,
for ICD-10-CM FY2027 (October 1, 2026 release).

Only the case file's text after its front matter (surrounding blank lines
removed) reaches the model, filled into prompts/part_b_plain.txt as {note}.
Nothing from the front matter, the spec or the gold is read here.

Conditions:
  plain         one turn.
  with_checker  the first turn is the same as plain. medcode_eval.checker
                checks the first answer's codes in the order given. With no
                finding (or an invalid or empty first answer, which gives the
                checker nothing to check) the first answer is final. With any
                finding the second turn (prompts/part_b_checker.txt, the
                findings filled in as {findings}) is sent once, after the
                first prompt and the first reply with its think blocks
                dropped (runner.drop_think; raw.jsonl keeps the reply as
                given); its answer is final. There is never a third turn.

The setting prompt_suffix (empty by default) is added to every user turn on
its own last line, as in Part A.

Reading an answer (parse_answer): drop <think> blocks as Part A does; take
the last JSON list in the reply (the one that ends last; a list nested in it
is part of it); every item must be a non-empty string; each is normalised
with medcode_eval.checker.normalise. Anything else is invalid (None). An
empty list is a valid answer with no codes. Order and repeats are kept.

Output in the run directory (runs/part_b/<run-id>/):
  run.json       as Part A (backend, model, settings, prompt_suffix, code-set
                 release, sha256 of the prompt files) plus the condition, the
                 sha256 of every case file, and for with_checker the checker's
                 reference files
  raw.jsonl      one row per turn tried: id, turn (1 or 2), raw reply,
                 seconds, error (plus done_reason and eval_count when the
                 server gives them); a turn-2 row also holds the findings sent
  answers.jsonl  per complete case: id, first answer, final answer, whether
                 each is valid, whether a second turn happened, error, and
                 stop_reasons ({turn: stop_reason} for the turns whose raw
                 row has one; remote backend)

With a ledger (medcode_eval.run.spend) the spending stop is checked before
every turn, as in the Part A runner; a refused turn is not sent and the run
ends there, resumable. On a resume only the cap may differ from run.json
(runner.same_inputs).

A rerun with the same run directory skips (case, turn) pairs already in
raw.jsonl, so an interrupted case resumes at its second turn; it refuses
to continue when run.json would differ. A case whose first answer draws a
finding but has no second-turn row yet is left out of answers.jsonl.
write_answers() is what --rederive runs: no backend, no model call.
"""

import json
import time
import urllib.error
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_a.score import load_jsonl
from medcode_eval.part_b.validate import IGNORED, parse_front_matter
from medcode_eval.run import spend
from medcode_eval.run.runner import (
    PROMPT_DIR,
    RemoteAbort,
    _append,
    same_inputs,
    _relative,
    _sha,
    check_messages,
    drop_think,
    user_message,
)

PROMPT_FILES = {"plain": "part_b_plain.txt", "checker": "part_b_checker.txt"}
CONDITIONS = ("plain", "with_checker")
RUNS_DIR = Path("runs") / "part_b"
# checker rules whose findings come from a tabular note, and the note kind
NOTE_RULES = {rule: kind for kind, (rule, _) in checker.PAIR_RULES.items()}


def load_prompts():
    return {k: (PROMPT_DIR / f).read_text(encoding="ascii") for k, f in PROMPT_FILES.items()}


def load_cases(data_dir):
    """[{id, path, note}] for every cases/<id>.md, sorted by id."""
    folder = Path(data_dir) / "cases"
    out = []
    for p in sorted(folder.iterdir()):
        if p.name in IGNORED or p.suffix != ".md" or not p.is_file():
            continue
        parsed = parse_front_matter(p.read_text(encoding="utf-8"))
        if parsed is None:
            raise ValueError(f"cases/{p.name}: no front matter")
        out.append({"id": p.stem, "path": p, "note": parsed[2].strip()})
    return out


def _with_suffix(text, prompt_suffix):
    if "\n" in prompt_suffix or "\r" in prompt_suffix:
        raise ValueError("prompt_suffix must be a single line")
    return text + "\n" + prompt_suffix if prompt_suffix else text


def render_first(case, prompts=None, prompt_suffix=""):
    """The first-turn prompt for a case, without the file's trailing newline."""
    template = (prompts or load_prompts())["plain"]
    return _with_suffix(template.format_map({"note": case["note"]}).rstrip("\n"),
                        prompt_suffix)


def render_findings(findings):
    """One block per finding, blocks separated by a blank line:
        Finding <k> of <n>
        Level: <level>
        Rule: <rule>
        Message: <message>
        Note: <note text>        (excludes1_pair and code_first_order only)
    """
    n = len(findings)
    blocks = []
    for k, f in enumerate(findings, start=1):
        lines = [f"Finding {k} of {n}", f"Level: {f['level']}", f"Rule: {f['rule']}",
                 f"Message: {f['message']}"]
        if f["rule"] in NOTE_RULES:
            for s in f.get("source", []):
                if s.get("element") == NOTE_RULES[f["rule"]] and "text" in s:
                    lines.append(f"Note: {s['text']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_second(findings, prompts=None, prompt_suffix=""):
    template = (prompts or load_prompts())["checker"]
    return _with_suffix(template.format_map({"findings": render_findings(findings)})
                        .rstrip("\n"), prompt_suffix)


def render_second_template_chars(findings_chars, prompt_suffix=""):
    """Length of a second-turn prompt whose findings block has findings_chars
    characters (for the dry-run's upper bound)."""
    template = load_prompts()["checker"]
    return len(_with_suffix(template.format_map({"findings": "x" * findings_chars})
                            .rstrip("\n"), prompt_suffix))


def parse_answer(text):
    """Normalised codes from a reply, or None when the reply is invalid."""
    if not isinstance(text, str):
        return None
    text = drop_think(text)
    dec = json.JSONDecoder()
    best = None
    for i, ch in enumerate(text):
        if ch != "[":
            continue
        try:
            value, end = dec.raw_decode(text, i)
        except ValueError:
            continue
        if isinstance(value, list) and (best is None or end > best[0]):
            best = (end, value)
    if best is None:
        return None
    items = best[1]
    if not all(isinstance(x, str) for x in items):
        return None
    try:
        return [checker.normalise(x) for x in items]
    except checker.UsageError:
        return None


def _first_findings(row1, data):
    """Checker findings on a stored first turn ([] when it has no codes)."""
    if row1.get("error") is not None:
        return []
    codes = parse_answer(row1.get("raw"))
    if not codes:
        return []
    return checker.check(codes, data=data)


def _meta(data_dir, condition, backend, prompt_suffix, data, ledger=None, part="b",
          prompt_files=None):
    cases = load_cases(data_dir)
    prompt_files = PROMPT_FILES if prompt_files is None else prompt_files
    meta = {
        "code_set": CODE_SET,
        "part": part,
        "condition": condition,
        "data_dir": _relative(data_dir),
        "cases_sha256": {c["id"]: _sha(c["path"]) for c in cases},
        "prompts_sha256": {f: _sha(PROMPT_DIR / f) for f in prompt_files.values()},
        "prompt_suffix": prompt_suffix,
        "checker": None if condition != "with_checker" else {
            "order_file": data.order_file, "tabular_file": data.tabular_file,
            "tabular_version": data.tree.version},
        **backend.describe(),
    }
    if ledger is not None:
        meta["spend"] = ledger.describe(_relative(ledger.path))
    return cases, meta


def run(data_dir, run_dir, backend, condition, ids=None, limit=None, log=None,
        prompt_suffix="", checker_data=None, ledger=None, part="b", conditions=None,
        prompt_files=None, prompts=None):
    """Run the cases (all, or those in ids) not yet complete in raw.jsonl.

    limit caps the number of cases that get a model call in this call.
    Returns that number. ledger: the spending stop (see the module text);
    a remote backend needs one.

    The last four are for another part that runs its cases this way
    (medcode_eval.run.part_c); left at None they are Part B's: part "b",
    CONDITIONS, PROMPT_FILES (hashed into run.json) and load_prompts().
    prompts holds the first-turn template as "plain" and the second-turn
    template as "checker". Every condition other than with_checker is one
    turn.
    """
    conditions = CONDITIONS if conditions is None else conditions
    if condition not in conditions:
        raise ValueError(f"condition must be one of {conditions}, not {condition!r}")
    _with_suffix("", prompt_suffix)
    if ledger is None and getattr(backend, "name", None) == "remote":
        raise ValueError("a remote run needs a ledger (the spending stop)")
    data = None
    if condition == "with_checker":
        data = checker_data or checker.default_data()
    run_dir = Path(run_dir)
    cases, meta = _meta(data_dir, condition, backend, prompt_suffix, data, ledger, part,
                        prompt_files)
    if ids is not None:
        known = {c["id"] for c in cases}
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise ValueError(f"ids not in the cases folder: {unknown}")
        cases = [c for c in cases if c["id"] in set(ids)]
    prompts = load_prompts() if prompts is None else prompts
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "run.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        old.pop("started", None)
        if not same_inputs(old, meta):
            diff = sorted(k for k in set(old) | set(meta) if old.get(k) != meta.get(k))
            raise ValueError(f"run directory was made with other inputs: {diff}")
    else:
        meta_path.write_text(json.dumps({**meta, "started": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z")}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_path = run_dir / "raw.jsonl"
    rows = {(r["id"], r["turn"]): r for r in load_jsonl(raw_path)} if raw_path.exists() else {}

    def call(case_id, turn, messages, extra=None):
        check_messages(messages)
        chars = spend.before(ledger, backend, messages)  # may raise SpendStop
        start = time.monotonic()
        row = {"id": case_id, "turn": turn, "raw": None, "error": None, **(extra or {})}
        try:
            row.update(backend.generate(messages))
        except (OSError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        except RemoteAbort:
            write_answers(run_dir, checker_data=data)
            raise
        row["seconds"] = round(time.monotonic() - start, 3)
        spend.after(ledger, case_id, turn, row, chars)
        _append(raw_path, row)
        rows[(case_id, turn)] = row
        if log:
            log(f"{case_id} turn {turn} {row['seconds']:.1f}s"
                + (f" error {row['error']}" if row["error"] else ""))
        return row

    tried = 0
    try:
        tried = _loop(cases, rows, condition, data, prompts, prompt_suffix, limit, call)
    except spend.SpendStop as exc:
        tried = exc.tried
        if log:
            log(str(exc))
    write_answers(run_dir, checker_data=data)
    return tried


def _loop(cases, rows, condition, data, prompts, prompt_suffix, limit, call):
    tried = 0
    for c in cases:
        cid = c["id"]
        first = render_first(c, prompts, prompt_suffix)
        row1 = rows.get((cid, 1))
        findings = None
        if row1 is not None:
            if condition != "with_checker" or (cid, 2) in rows:
                continue
            findings = _first_findings(row1, data)
            if not findings:
                continue
        if limit is not None and tried >= limit:
            break
        fresh = row1 is None
        try:
            if fresh:
                row1 = call(cid, 1, [user_message(first)])
                tried += 1
                if condition != "with_checker":
                    continue
                findings = _first_findings(row1, data)
                if not findings:
                    continue
            second = render_second(findings, prompts, prompt_suffix)
            call(cid, 2, [user_message(first),
                          {"role": "assistant", "content": drop_think(row1["raw"])},
                          user_message(second)], extra={"findings": findings})
            if not fresh:
                tried += 1
        except spend.SpendStop as exc:
            exc.tried = tried
            raise
    return tried


def write_answers(run_dir, checker_data=None):
    """Rewrite answers.jsonl from raw.jsonl and run.json's condition."""
    run_dir = Path(run_dir)
    condition = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["condition"]
    raw_path = run_dir / "raw.jsonl"
    rows = {(r["id"], r["turn"]): r for r in load_jsonl(raw_path)} if raw_path.exists() else {}
    data = checker_data
    out = []
    for cid in sorted({k[0] for k in rows}):
        r1, r2 = rows.get((cid, 1)), rows.get((cid, 2))
        if r1 is None:
            continue
        first = None if r1["error"] is not None else parse_answer(r1["raw"])
        if condition == "with_checker" and r2 is None and first:
            data = data or checker.default_data()
            if checker.check(first, data=data):
                continue  # incomplete: the second turn is still owed
        final, error = first, r1["error"]
        if r2 is not None:
            final = None if r2["error"] is not None else parse_answer(r2["raw"])
            error = error or r2["error"]
        stops = {str(t): r["stop_reason"] for t, r in ((1, r1), (2, r2))
                 if r is not None and "stop_reason" in r}
        out.append({"id": cid, "first_answer": first, "first_valid": first is not None,
                    "final_answer": final, "final_valid": final is not None,
                    "second_turn": r2 is not None, "error": error,
                    "stop_reasons": stops})
    with open(run_dir / "answers.jsonl", "w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
