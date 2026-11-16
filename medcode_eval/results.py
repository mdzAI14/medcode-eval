"""Rebuild and check every reported figure from the stored run results
(ICD-10-CM FY2027, October 1, 2026 release).

Reads only results/part_a/, results/part_b/ (the reported runs, byte-for-
byte copies of what each run wrote), data/ and refdata/. Never runs/, never
results/review/, no network and no model call. Standard library only; the
package's own readers, scorers and checker do the work.

    venv/bin/python -m medcode_eval.results --write
        writes results/RESULTS.md and results/results.json
    venv/bin/python -m medcode_eval.results --check
        writes nothing in the repo (the package's writers run in a temporary
        folder that is removed) and exits 0 only if:
        1  every stored reading is reproduced from raw.jsonl: Part A
           responses with runner.write_responses and the reader the rows
           record; Part B answers with part_b.write_answers; the Part A
           checker run's answers with part_a_checker.write_answers, its
           source run read from results/part_a/
        2  every stored score.json and score.md is reproduced: Part A with
           part_a.score, Part B with part_b.score against the gold files as
           they are (whose sha256 must equal the one each score records),
           the checker run with part_a_checker.score_run
        3  RESULTS.md and results.json equal what --write would produce

Figures that come from a pattern (the refusal openings) or from a reading
made after the results were seen (the lenient reading) are labelled so in
RESULTS.md; neither is a reported score.
"""

import argparse
import json
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a import score as part_a_score
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_a.score import _norm_answer, load_jsonl, parse_response
from medcode_eval.part_b import score as part_b_score
from medcode_eval.run import part_a_checker as pac
from medcode_eval.run import part_b, runner, usage
from medcode_eval.run.runner import drop_think

RESULTS_DIR = REPO_ROOT / "results"
DATA_DIR = REPO_ROOT / "data"
PARTS = ("part_a", "part_b")
MD_NAME = "RESULTS.md"
JSON_NAME = "results.json"
D2C = "description_to_code"
RULES = pac.RULES
KIND_ORDER = ("a_lite", "a_changes", "a_checker", "b_plain", "b_checker")
KIND_LABEL = {"a_lite": "Part A lite", "a_changes": "Part A changes",
              "a_checker": "Part A changes, description-to-code with checker",
              "b_plain": "Part B plain", "b_checker": "Part B with checker"}
SHOW_CODES = 8
SHOW_FIRST = 5

LENIENT = re.compile(
    r"(?<![A-Za-z0-9.])[A-Z][0-9][0-9A-Z](?:\.?[0-9A-Z]{1,4})?(?![A-Za-z0-9])")
_REFUSAL = re.compile("I(?: can['’]t|['’]m not| don['’]t)")
_STRIP = str.maketrans("", "", "*_`")


# ---------------------------------------------------------------------------
# readings and classifications

def _first_line(reply):
    if not isinstance(reply, str):
        return None
    lines = [l for l in drop_think(reply).splitlines() if l.strip()]
    return lines[0] if lines else None


def lenient_token(reply):
    """The lenient reading: on the first non-empty line (think blocks
    dropped) with * _ and ` removed, the first token matching LENIENT."""
    line = _first_line(reply)
    if line is None:
        return None
    m = LENIENT.search(line.translate(_STRIP))
    return m.group(0) if m else None


def lenient_equal(reply, expected):
    tok = lenient_token(reply)
    return tok is not None and tok.replace(".", "") == expected.replace(".", "")


def opens_with_refusal(reply):
    """The reply (think blocks dropped) opens with "I can't", "I'm not" or
    "I don't", straight or curly apostrophe. A pattern count, not a reading."""
    if not isinstance(reply, str):
        return False
    return _REFUSAL.match(drop_think(reply).lstrip()) is not None


def is_prefix(final, findings):
    """final equals the longest stored prefix named in a not_in_code_set
    finding."""
    if final is None:
        return False
    for f in findings:
        if f.get("rule") == "not_in_code_set":
            p = (f.get("details") or {}).get("longest_stored_prefix")
            if p and checker.normalise(p["code"]) == final:
                return True
    return False


def is_listed(final, findings):
    """final is one of the codes listed (children) in a header_not_billable
    finding."""
    if final is None:
        return False
    for f in findings:
        if f.get("rule") == "header_not_billable":
            kids = (f.get("details") or {}).get("children") or []
            if final in {checker.normalise(c) for c in kids}:
                return True
    return False


def wrong_class(findings):
    rules = {f.get("rule") for f in findings}
    if "not_in_code_set" in rules:
        return "not_in_code_set"
    if "header_not_billable" in rules:
        return "header_not_billable"
    if any(f.get("level") == "error" for f in findings):
        return "other_error"
    return "no_error"


WRONG_CLASSES = ("not_in_code_set", "header_not_billable", "other_error", "no_error")


# ---------------------------------------------------------------------------
# the stored runs

def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _kind(part, meta):
    if part == "part_b":
        return "b_plain" if meta["condition"] == "plain" else "b_checker"
    if meta.get("condition") == "with_checker_description_to_code":
        return "a_checker"
    name = Path(meta["probes_file"]).name
    if name == "probes_lite.jsonl":
        return "a_lite"
    if name == "probes_changes.jsonl":
        return "a_changes"
    raise ValueError(f"unknown Part A probe file {meta['probes_file']}")


def load_runs(results_dir=RESULTS_DIR):
    """The reported runs under results/part_a and results/part_b, in
    presentation order."""
    results_dir = Path(results_dir)
    runs = []
    for part in PARTS:
        for d in sorted((results_dir / part).iterdir()):
            if not d.is_dir():
                continue
            meta = _json(d / "run.json")
            runs.append({"id": d.name, "part": part, "dir": d, "meta": meta,
                         "kind": _kind(part, meta), "model": meta["model"]})
    runs.sort(key=lambda r: (KIND_ORDER.index(r["kind"]), r["model"], r["id"]))
    return runs


def _probes(run):
    """The run's probe file (data/), refused when its sha256 differs."""
    return runner.run_probes(run["dir"])


def _source_dir(run, results_dir):
    d = Path(results_dir) / "part_a" / Path(run["meta"]["source_run"]).name
    if not d.is_dir():
        raise ValueError(f"source run {run['meta']['source_run']} is not in results/part_a")
    return d


def _readers(run):
    return sorted({r.get("reader") for r in load_jsonl(run["dir"] / "responses.jsonl")},
                  key=str)


# ---------------------------------------------------------------------------
# --check

def _same(path_a, path_b):
    return Path(path_a).read_bytes() == Path(path_b).read_bytes()


def _copy(run, tmp, names=("run.json", "raw.jsonl")):
    t = Path(tmp) / run["id"]
    t.mkdir()
    for n in names:
        shutil.copyfile(run["dir"] / n, t / n)
    return t


def _check_reading(run, results_dir, tmp, data):
    if run["kind"] in ("a_lite", "a_changes"):
        readers = _readers(run)
        if len(readers) != 1:
            return f"responses.jsonl records readers {readers}"
        t = _copy(run, tmp)
        runner.write_responses(t, readers[0], _probes(run))
        name = "responses.jsonl"
    elif run["kind"] == "a_checker":
        src = pac.load_source(_source_dir(run, results_dir))
        rows = {r["id"]: r for r in load_jsonl(run["dir"] / "raw.jsonl")}
        t = Path(tmp) / run["id"]
        t.mkdir()
        pac.write_answers(t, src, pac.items(src, data), rows)
        name = "answers.jsonl"
    else:
        t = _copy(run, tmp)
        part_b.write_answers(t, checker_data=data)
        name = "answers.jsonl"
    return None if _same(t / name, run["dir"] / name) else f"{name} differs"


def _check_score(run, results_dir, tmp, data):
    t = Path(tmp) / (run["id"] + "-score")
    t.mkdir()
    if run["kind"] in ("a_lite", "a_changes"):
        _probes(run)  # the sha256 check
        part_a_score.main(["--probes", str(REPO_ROOT / run["meta"]["probes_file"]),
                           "--responses", str(run["dir"] / "responses.jsonl"),
                           "--out-json", str(t / "score.json"),
                           "--out-md", str(t / "score.md")])
    elif run["kind"] == "a_checker":
        t.rmdir()
        t = _copy(run, tmp)
        pac.score_run(t, checker_data=data, source_dir=_source_dir(run, results_dir))
    else:
        stored = _json(run["dir"] / "score.json")["gold_sha256"]
        if stored != part_b_score.gold_sha256(DATA_DIR):
            return "the gold files differ from the score's gold_sha256"
        part_b_score.main(["--answers", str(run["dir"] / "answers.jsonl"),
                           "--data-dir", str(DATA_DIR),
                           "--out-json", str(t / "score.json"),
                           "--out-md", str(t / "score.md")], checker_data=data)
    bad = [n for n in ("score.json", "score.md") if not _same(t / n, run["dir"] / n)]
    return f"{' and '.join(bad)} differ" if bad else None


def check(results_dir=RESULTS_DIR, log=print):
    """Run checks 1 to 3; returns the number of failures."""
    results_dir = Path(results_dir)
    failures = 0
    runs = load_runs(results_dir)
    data = checker.default_data()

    def report(num, what, problem):
        nonlocal failures
        if problem is None:
            log(f"ok {num} {what}")
        else:
            failures += 1
            log(f"FAIL {num} {what}: {problem}")

    with tempfile.TemporaryDirectory() as tmp:
        for num, fn in ((1, _check_reading), (2, _check_score)):
            for run in runs:
                what = f"{run['part']}/{run['id']}"
                sub = Path(tmp) / f"{num}"
                sub.mkdir(exist_ok=True)
                try:
                    problem = fn(run, results_dir, sub, data)
                except (ValueError, OSError, KeyError) as exc:
                    problem = f"{type(exc).__name__}: {exc}"
                report(num, what, problem)
    try:
        md, js = build(results_dir, runs, data)
        for name, text in ((MD_NAME, md), (JSON_NAME, js)):
            p = results_dir / name
            report(3, name, None if p.is_file() and p.read_bytes() == text.encode("ascii")
                   else "differs from what --write would produce")
    except (ValueError, OSError, KeyError) as exc:
        report(3, MD_NAME, f"{type(exc).__name__}: {exc}")
    log(f"checks failed: {failures}")
    return failures


# ---------------------------------------------------------------------------
# figures

def _settings(meta):
    s = meta.get("settings") or {}
    opts = s.get("options") or {}
    temp = s.get("temperature") if s.get("temperature") is not None else opts.get("temperature")
    return {"effort": s.get("effort"), "temperature": temp, "seed": opts.get("seed"),
            "prompt_suffix": meta.get("prompt_suffix", "")}


def _s0(runs):
    out = []
    for r in runs:
        m = r["meta"]
        if r["kind"] in ("a_lite", "a_changes"):
            reader = f"Part A reader {', '.join(map(str, _readers(r)))}"
            n = len(load_jsonl(r["dir"] / "responses.jsonl"))
        elif r["kind"] == "a_checker":
            reader = f"Part A reader {m['reader']}"
            n = len(load_jsonl(r["dir"] / "answers.jsonl"))
        else:
            reader = "Part B JSON list"
            n = len(load_jsonl(r["dir"] / "answers.jsonl"))
        out.append({"run": r["id"], "part": r["part"], "what": KIND_LABEL[r["kind"]],
                    "model": m["model"], "backend": m["backend"], **_settings(m),
                    "reader": reader, "started": m["started"][:10], "items_answered": n})
    return out


def _g(g):
    return {k: g[k] for k in ("n", "correct", "accuracy", "invalid", "missing")}


def _part_a_basic(run):
    s = _json(run["dir"] / "score.json")
    return {"run": run["id"], "model": run["model"], "reader": s["reader"],
            "overall": _g(s["overall"]),
            "by_type": {t: _g(g) for t, g in s["by_type"].items()},
            "status_table": s["status_table"]}


def _raw_by_id(run_dir):
    return {r["id"]: r for r in load_jsonl(Path(run_dir) / "raw.jsonl")}


def _s2(run):
    out = _part_a_basic(run)
    s = _json(run["dir"] / "score.json")
    out["by_change"] = {c: _g(g) for c, g in s["by_change"].items()}
    probes = _probes(run)
    responses = load_jsonl(run["dir"] / "responses.jsonl")
    status = [p for p in probes if p["type"] == "status"]
    st = part_a_score.score(status, responses)
    out["status_by_change"] = {c: {"n": g["n"], "correct": g["correct"]}
                               for c, g in st["by_change"].items()}
    d = s["by_type"][D2C]
    given = {r["id"]: r.get("response") for r in responses}
    raw = _raw_by_id(run["dir"])
    no_single = [p for p in probes if p["type"] == D2C and p["id"] in given
                 and parse_response(p, given[p["id"]]) is None]
    out["description_to_code"] = {
        "n": d["n"], "correct": d["correct"],
        "wrong_code": d["n"] - d["correct"] - d["invalid"] - d["missing"],
        "no_single_code": d["invalid"], "missing": d["missing"],
        "pattern_refusal_opening": sum(opens_with_refusal(raw[p["id"]].get("raw"))
                                       for p in no_single)}
    return out


def _s3(run, data):
    probes = [p for p in _probes(run) if p["type"] == D2C]
    given = {r["id"]: r.get("response") for r in load_jsonl(run["dir"] / "responses.jsonl")}
    classes = dict.fromkeys(WRONG_CLASSES, 0)
    flagged = []
    n = correct = invalid = 0
    for p in probes:
        if p["id"] not in given:
            continue
        v = parse_response(p, given[p["id"]])
        n += 1
        if v is None:
            invalid += 1
            continue
        found = checker.check([v], data=data)
        if v == _norm_answer(D2C, p["answer"]):
            correct += 1
            errs = [f["rule"] for f in found if f["level"] == "error"]
            if errs:
                flagged.append({"id": p["id"], "code": checker.dotted(v), "rules": errs})
        else:
            classes[wrong_class(found)] += 1
    return {"run": run["id"], "model": run["model"], "answered": n, "correct": correct,
            "invalid": invalid, "wrong": sum(classes.values()), "wrong_by_class": classes,
            "correct_with_error_finding": flagged}


def _s4(run, results_dir, data):
    s = _json(run["dir"] / "score.json")
    src_dir = _source_dir(run, results_dir)
    probes = {p["id"]: p for p in _probes({"dir": src_dir})}
    src_raw = _raw_by_id(src_dir)
    raw2 = _raw_by_id(run["dir"])
    answers = load_jsonl(run["dir"] / "answers.jsonl")
    prefix = prefix_ok = listed = listed_ok = 0
    neither_before = neither_after = 0
    sens = {w: {"invalid": 0, "with_token": 0, "token_equals_expected": 0}
            for w in ("first", "final")}
    for a in answers:
        p = probes[a["id"]]
        want = _norm_answer(D2C, p["answer"])
        fin, first = a["final_answer"], a["first_answer"]
        if first is not None and first != want and not set(a["rules"]) & set(RULES):
            neither_before += 1
        if fin is not None and fin != want and not any(
                f["rule"] in RULES for f in checker.check([fin], data=data)):
            neither_after += 1
        if a["second_turn"]:
            found = raw2[a["id"]]["findings"]
            if is_prefix(fin, found):
                prefix += 1
                prefix_ok += fin == want
            if is_listed(fin, found):
                listed += 1
                listed_ok += fin == want
        replies = {"first": src_raw[a["id"]].get("raw"),
                   "final": raw2[a["id"]].get("raw") if a["second_turn"]
                   else src_raw[a["id"]].get("raw")}
        for w in ("first", "final"):
            if a[f"{w}_valid"]:
                continue
            g = sens[w]
            g["invalid"] += 1
            if lenient_token(replies[w]) is not None:
                g["with_token"] += 1
                g["token_equals_expected"] += lenient_equal(replies[w], p["answer"])
    for w in ("first", "final"):
        sens[w]["correct_if_counted"] = s[w]["correct"] + sens[w]["token_equals_expected"]
    return {"run": run["id"], "model": run["model"], "source_run": src_dir.name,
            "first": s["first"], "final": s["final"],
            "first_matches_source": s["first_matches_source"],
            "second_turn": s["second_turn"],
            "final_is_longest_stored_prefix": {"n": prefix, "correct": prefix_ok},
            "final_is_listed_header_code": {"n": listed, "correct": listed_ok},
            "wrong_with_neither_rule": {"first": neither_before, "final": neither_after},
            "sensitivity_lenient_reading": sens}


_B_KEYS = ("n", "exact", "first_listed", "correct", "missing", "extra", "optional_given",
           "precision", "recall", "invalid", "no_answer", "findings",
           "cases_with_error_finding", "fewer_than_10")


def _bg(g):
    return {k: g[k] for k in _B_KEYS}


def _s5(run):
    s = _json(run["dir"] / "score.json")
    out = {"run": run["id"], "model": run["model"], "condition": run["meta"]["condition"],
           "gold_sha256": s["gold_sha256"],
           "gold_sha256_equals_gold_files": s["gold_sha256"] == part_b_score.gold_sha256(
               DATA_DIR),
           "n_cases": s["n_cases"], "second_turns": s["second_turns"]}
    for w in ("first", "final"):
        out[w] = {"overall": _bg(s[w]["overall"]),
                  "by_target_trap": {k: _bg(g) for k, g in s[w]["by_target_trap"].items()},
                  "by_specialty": {k: _bg(g) for k, g in s[w]["by_specialty"].items()}}
    return out


def _disp(code):
    """A code with the dot after the third character; a code given in
    another form (it already holds a dot, so it is not a stored code) is
    shown as given."""
    return code if "." in code else checker.dotted(code)


def _show(x):
    if x["invalid"]:
        return "invalid"
    if x["no_answer"]:
        return "none"
    codes = [_disp(c) for c in x["codes"]]
    if not codes:
        return "[]"
    if len(codes) > SHOW_CODES:
        return " ".join(codes[:SHOW_FIRST]) + f" ... ({len(codes)} codes)"
    return " ".join(codes)


def _s6(run):
    s = _json(run["dir"] / "score.json")
    return {"run": run["id"], "cases": [
        {"id": c["id"], "trap": c["target_trap"],
         "gold": " ".join(checker.dotted(v) for v in c["gold"]),
         "optional": " ".join(checker.dotted(v) for v in c["optional"]) or "-",
         "first": _show(c["first"]), "final": _show(c["final"]),
         "exact_first": c["first"]["exact"], "exact_final": c["final"]["exact"],
         "optional_given_first": c["first"]["optional_given"],
         "optional_given_final": c["final"]["optional_given"]} for c in s["cases"]]}


def _s7(runs):
    out = []
    for model in sorted({r["model"] for r in runs if r["part"] == "part_b"}):
        mine = {r["kind"]: r for r in runs if r["part"] == "part_b" and r["model"] == model}
        ans = {k: {a["id"]: a for a in load_jsonl(r["dir"] / "answers.jsonl")}
               for k, r in mine.items()}
        entry = {"model": model, "runs": {k: r["id"] for k, r in mine.items()}}
        if "b_plain" in ans and "b_checker" in ans:
            diff = []
            for cid in sorted(set(ans["b_plain"]) | set(ans["b_checker"])):
                a = (ans["b_plain"].get(cid) or {}).get("first_answer")
                b = (ans["b_checker"].get(cid) or {}).get("first_answer")
                if a != b:
                    order = a is not None and b is not None and sorted(a) == sorted(b)
                    diff.append({"id": cid, "order_only": order})
            entry["first_answer_differs_plain_vs_checker"] = diff
        entry["final_differs_from_first"] = {
            k: [cid for cid, a in sorted(v.items()) if a["final_answer"] != a["first_answer"]]
            for k, v in ans.items()}
        entry["runner_error"] = {
            k: [{"id": cid, "error": a["error"].split(":")[0]}
                for cid, a in sorted(v.items()) if a["error"] is not None]
            for k, v in ans.items()}
        if "b_checker" in mine:
            s = _json(mine["b_checker"]["dir"] / "score.json")
            errs = {cid for cid, a in ans["b_checker"].items() if a["error"] is not None}

            def tally(cases):
                return {"error_findings_first": sum(c["first"]["findings"]["error"]
                                                    for c in cases),
                        "error_findings_final": sum(c["final"]["findings"]["error"]
                                                    for c in cases),
                        "changed_answers": sum(c["first"]["codes"] != c["final"]["codes"]
                                               for c in cases),
                        "cases": len(cases)}
            entry["with_checker"] = {
                "all_cases": tally(s["cases"]),
                "without_runner_error": tally([c for c in s["cases"] if c["id"] not in errs]),
                "runner_error_cases": sorted(errs)}
        out.append(entry)
    return out


def _s8(runs):
    out = []
    for r in runs:
        if not (r["dir"] / "usage.json").is_file():
            continue
        u = usage.summarize(r["dir"])
        stored = _json(r["dir"] / "usage.json")
        out.append({"run": r["id"], "model": r["model"], "replies": u["replies"],
                    "cost_usd": u["cost_usd"],
                    "price_in_usd_per_mtok": u["spend"]["price_in_usd_per_mtok"],
                    "price_out_usd_per_mtok": u["spend"]["price_out_usd_per_mtok"],
                    "equals_stored_usage_json": (stored["replies"], stored["cost_usd"])
                    == (u["replies"], u["cost_usd"])})
    return out


def figures(results_dir=RESULTS_DIR, runs=None, data=None):
    results_dir = Path(results_dir)
    runs = runs if runs is not None else load_runs(results_dir)
    data = data or checker.default_data()
    by = {k: [r for r in runs if r["kind"] == k] for k in KIND_ORDER}
    return {
        "code_set": CODE_SET,
        "S0_runs": _s0(runs),
        "S1_part_a_lite": [_part_a_basic(r) for r in by["a_lite"]],
        "S2_part_a_changes": [_s2(r) for r in by["a_changes"]],
        "S3_checker_on_part_a_answers": [_s3(r, data) for r in by["a_lite"] + by["a_changes"]],
        "S4_part_a_checker_condition": [_s4(r, results_dir, data) for r in by["a_checker"]],
        "S5_part_b": [_s5(r) for r in by["b_plain"] + by["b_checker"]],
        "S6_part_b_cases": [_s6(r) for r in by["b_plain"] + by["b_checker"]],
        "S7_part_b_derived": _s7(runs),
        "S8_usage": _s8(runs),
    }


# ---------------------------------------------------------------------------
# markdown

def _f4(x):
    return "n/a" if x is None else f"{x:.4f}"


def _yn(x):
    return "yes" if x else "no"


def _table(head, rows):
    out = "| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(c) for c in r) + " |\n"
    return out


def _acc_rows(d):
    rows = [["overall", "", d["overall"]["n"], d["overall"]["correct"],
             _f4(d["overall"]["accuracy"]), d["overall"]["invalid"], d["overall"]["missing"]]]
    for t, g in d["by_type"].items():
        rows.append(["type", t, g["n"], g["correct"], _f4(g["accuracy"]), g["invalid"],
                     g["missing"]])
    for c, g in d.get("by_change", {}).items():
        rows.append(["change", c, g["n"], g["correct"], _f4(g["accuracy"]), g["invalid"],
                     g["missing"]])
    return _table(["Group", "Value", "n", "Correct", "Accuracy", "Invalid", "Missing"], rows)


def _status_table(t):
    cols = part_a_score.STATUS_COLUMNS
    return _table(["Answer \\ response", *cols],
                  [[a, *(row[c] for c in cols)] for a, row in t.items()])


def _b_rows(d):
    def line(group, value, g):
        return [group, value, g["n"], g["exact"], g["first_listed"], g["correct"],
                g["missing"], g["extra"], g["optional_given"], _f4(g["precision"]),
                _f4(g["recall"]), g["invalid"], g["no_answer"], g["findings"]["error"],
                g["findings"]["review"], g["cases_with_error_finding"],
                "fewer than 10 cases" if g["fewer_than_10"] else ""]
    rows = [line("overall", "", d["overall"])]
    rows += [line("target trap", k, g) for k, g in d["by_target_trap"].items()]
    rows += [line("specialty", k, g) for k, g in d["by_specialty"].items()]
    return _table(["Group", "Value", "n", "Exact", "First-listed", "Correct", "Missing",
                   "Extra", "Optional given", "Precision", "Recall", "Invalid", "No answer",
                   "Error findings", "Review findings", "Cases with an error finding",
                   "Note"], rows)


def _opt(x):
    return "-" if x is None or x == "" else x


def to_markdown(fig):
    o = [f"# Results\n\nCode set: {fig['code_set']}.\n\n"
         "Every figure below is computed by medcode_eval.results from the stored files in "
         "results/part_a/ and results/part_b/ and from data/ and refdata/. Rebuild with "
         "`venv/bin/python -m medcode_eval.results --write`; check with "
         "`venv/bin/python -m medcode_eval.results --check`. Codes are shown with the dot "
         "after the third character.\n"]

    o.append("\n## S0. Reported runs\n\n")
    o.append(_table(["Run", "What", "Model", "Backend", "Effort", "Temperature", "Seed",
                     "Prompt suffix", "Reader", "Started", "Items answered"],
                    [[r["run"], r["what"], r["model"], r["backend"], _opt(r["effort"]),
                      _opt(r["temperature"]), _opt(r["seed"]),
                      f"`{r['prompt_suffix']}`" if r["prompt_suffix"] else "-",
                      r["reader"], r["started"], r["items_answered"]]
                     for r in fig["S0_runs"]]))

    o.append("\n## S1. Part A lite\n")
    for d in fig["S1_part_a_lite"]:
        o.append(f"\n### {d['run']} ({d['model']}, reader {d['reader']})\n\n")
        o.append(_acc_rows(d))
        o.append("\nStatus probes, answer by response:\n\n" + _status_table(d["status_table"]))

    o.append("\n## S2. Part A changes\n")
    for d in fig["S2_part_a_changes"]:
        o.append(f"\n### {d['run']} ({d['model']}, reader {d['reader']})\n\n")
        o.append("Overall, by type and by change (all probe types):\n\n" + _acc_rows(d))
        o.append("\nStatus probes by change:\n\n" + _table(
            ["Change", "n", "Correct"],
            [[c, g["n"], g["correct"]] for c, g in d["status_by_change"].items()]))
        o.append("\nStatus probes, answer by response:\n\n" + _status_table(d["status_table"]))
        x = d["description_to_code"]
        o.append("\nDescription-to-code:\n\n" + _table(
            ["n", "Correct", "Wrong code", "No single code", "Missing"],
            [[x["n"], x["correct"], x["wrong_code"], x["no_single_code"], x["missing"]]]))
        o.append(f"\nPattern count (not a reading): of the {x['no_single_code']} "
                 "no-single-code replies, "
                 f"{x['pattern_refusal_opening']} open (think blocks dropped) with \"I can't\", "
                 "\"I'm not\" or \"I don't\" (straight or curly apostrophe).\n")

    o.append("\n## S3. The checker on the stored Part A answers\n\n"
             "Description-to-code probes only. Each answered code is checked alone. A wrong "
             "code is classed not_in_code_set if that finding is present, else "
             "header_not_billable, else another error rule, else no error finding.\n\n")
    o.append(_table(["Run", "Model", "Answered", "Correct", "Invalid", "Wrong",
                     "not_in_code_set", "header_not_billable", "Other error rule",
                     "No error finding", "Correct with an error finding"],
                    [[d["run"], d["model"], d["answered"], d["correct"], d["invalid"],
                      d["wrong"], *(d["wrong_by_class"][k] for k in WRONG_CLASSES),
                      len(d["correct_with_error_finding"])]
                     for d in fig["S3_checker_on_part_a_answers"]]))
    flagged = [(d["run"], x) for d in fig["S3_checker_on_part_a_answers"]
               for x in d["correct_with_error_finding"]]
    o.append("\nCorrect answers that draw an error finding:\n\n")
    o.append(_table(["Run", "Probe", "Code", "Error rules"],
                    [[r, x["id"], x["code"], ", ".join(x["rules"])] for r, x in flagged])
             if flagged else "None.\n")

    o.append("\n## S4. The Part A checker condition\n")
    for d in fig["S4_part_a_checker_condition"]:
        o.append(f"\n### {d['run']} ({d['model']}, source run {d['source_run']})\n\n")
        o.append(_table(["Answer", "n", "Correct", "Wrong", "Invalid", "Missing"],
                        [[w, d[w]["n"], d[w]["correct"], d[w]["wrong"], d[w]["invalid"],
                          d[w]["missing"]] for w in ("first", "final")]))
        o.append(f"\nFirst-answer counts equal the source run's stored score: "
                 f"{_yn(d['first_matches_source'])}.\n\nSecond turns by rule (from the "
                 "stored score):\n\n")
        keys = pac._GROUP_KEYS
        groups = list(d["second_turn"]["by_rule"].items()) + [("total",
                                                               d["second_turn"]["total"])]
        o.append(_table(["Rule", *keys], [[n, *(g[k] for k in keys)] for n, g in groups]))
        p, l, nr = (d["final_is_longest_stored_prefix"], d["final_is_listed_header_code"],
                    d["wrong_with_neither_rule"])
        o.append(f"\nFinal answers equal to the longest stored prefix named in their "
                 f"not_in_code_set finding: {p['n']}, of which correct: {p['correct']}.\n\n"
                 f"Final answers that are one of the codes listed in their header_not_billable "
                 f"finding: {l['n']}, of which correct: {l['correct']}.\n\n"
                 f"Wrong codes that draw neither rule: first answers {nr['first']}, final "
                 f"answers {nr['final']}.\n")
        o.append("\n#### Sensitivity figure, made after the results were seen; not the "
                 "reported score\n\n"
                 "A lenient reading, applied only where the stored reading is invalid: on the "
                 "first non-empty line of the reply (think blocks dropped) with the characters "
                 "* _ and ` removed, the first token matching "
                 "`(?<![A-Za-z0-9.])[A-Z][0-9][0-9A-Z](?:\\.?[0-9A-Z]{1,4})?(?![A-Za-z0-9])`, "
                 "compared with the expected code without dots.\n\n")
        s = d["sensitivity_lenient_reading"]
        o.append(_table(["Answer", "Invalid replies", "With such a token",
                         "Token equals the expected code", "Correct if they were counted"],
                        [[w, s[w]["invalid"], s[w]["with_token"],
                          s[w]["token_equals_expected"], s[w]["correct_if_counted"]]
                         for w in ("first", "final")]))

    o.append("\n## S5. Part B\n")
    for d in fig["S5_part_b"]:
        o.append(f"\n### {d['run']} ({d['model']}, {d['condition']})\n\n"
                 f"Gold sha256: {d['gold_sha256']} (equals the gold files as they are: "
                 f"{_yn(d['gold_sha256_equals_gold_files'])}). Cases: {d['n_cases']}. "
                 f"Second turns: {d['second_turns']}. Error findings: first answers "
                 f"{d['first']['overall']['findings']['error']}, final answers "
                 f"{d['final']['overall']['findings']['error']}. Required codes found: first "
                 f"{d['first']['overall']['correct']} of "
                 f"{d['first']['overall']['correct'] + d['first']['overall']['missing']}, "
                 f"final {d['final']['overall']['correct']} of "
                 f"{d['final']['overall']['correct'] + d['final']['overall']['missing']}.\n")
        for w, title in (("first", "First answer"), ("final", "Final answer")):
            o.append(f"\n{title}:\n\n" + _b_rows(d[w]))

    o.append(f"\n## S6. Part B per case\n\nAn answer with more than {SHOW_CODES} codes is "
             f"shown as its first {SHOW_FIRST} codes and the count.\n")
    for d in fig["S6_part_b_cases"]:
        o.append(f"\n### {d['run']}\n\n")
        o.append(_table(["Case", "Trap", "Gold", "Optional", "First", "Final",
                         "Exact first / final", "Optional given first / final"],
                        [[c["id"], c["trap"], c["gold"], c["optional"], c["first"],
                          c["final"], f"{_yn(c['exact_first'])} / {_yn(c['exact_final'])}",
                          f"{c['optional_given_first']} / {c['optional_given_final']}"]
                         for c in d["cases"]]))

    o.append("\n## S7. Part B derived\n")
    for d in fig["S7_part_b_derived"]:
        o.append(f"\n### {d['model']}\n\n")
        diff = d.get("first_answer_differs_plain_vs_checker")
        if diff is not None:
            o.append("Cases whose first answer differs between the plain and the "
                     "with-checker run: " + (", ".join(
                         x["id"] + (" (order only)" if x["order_only"] else "")
                         for x in diff) or "none") + ".\n\n")
        for k, ids in d["final_differs_from_first"].items():
            o.append(f"{d['runs'][k]}: cases whose final answer differs from the first: "
                     f"{', '.join(ids) or 'none'}.\n\n")
        for k, errs in d["runner_error"].items():
            o.append(f"{d['runs'][k]}: cases with a runner error: "
                     + (", ".join(f"{e['id']} ({e['error']})" for e in errs) or "none")
                     + ".\n\n")
        w = d.get("with_checker")
        if w:
            o.append(f"{d['runs']['b_checker']}, leaving out: "
                     f"{', '.join(w['runner_error_cases']) or 'nothing'}.\n\n")
            o.append(_table(["Cases", "n", "Error findings first", "Error findings final",
                             "Changed answers"],
                            [[name, g["cases"], g["error_findings_first"],
                              g["error_findings_final"], g["changed_answers"]]
                             for name, g in (("all cases", w["all_cases"]),
                                             ("without a runner error",
                                              w["without_runner_error"]))]))

    o.append("\n## S8. Usage and cost\n\nRuns with a usage.json; cost at the prices "
             "recorded in run.json, recomputed from raw.jsonl by medcode_eval.run.usage.\n\n")
    o.append(_table(["Run", "Model", "Replies", "Cost (USD)", "Price in / out (USD per "
                     "million tokens)", "Equals the stored usage.json"],
                    [[u["run"], u["model"], u["replies"], f"{u['cost_usd']:.4f}",
                      f"{u['price_in_usd_per_mtok']} / {u['price_out_usd_per_mtok']}",
                      _yn(u["equals_stored_usage_json"])] for u in fig["S8_usage"]]
                    + [["total", "", sum(u["replies"] for u in fig["S8_usage"]),
                        f"{sum(u['cost_usd'] for u in fig['S8_usage']):.4f}", "", ""]]))
    return "".join(o)


def build(results_dir=RESULTS_DIR, runs=None, data=None):
    """(RESULTS.md text, results.json text)."""
    fig = figures(results_dir, runs, data)
    return to_markdown(fig), json.dumps(fig, sort_keys=True, indent=2) + "\n"


def write(results_dir=RESULTS_DIR):
    results_dir = Path(results_dir)
    md, js = build(results_dir)
    (results_dir / MD_NAME).write_text(md, encoding="ascii")
    (results_dir / JSON_NAME).write_text(js, encoding="ascii")


def main(argv=None, results_dir=None):
    ap = argparse.ArgumentParser(
        prog="python -m medcode_eval.results",
        description="Rebuild (--write) or check (--check) every reported figure from the "
                    "stored run results (ICD-10-CM FY2027).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true",
                   help="write results/RESULTS.md and results/results.json")
    g.add_argument("--check", action="store_true",
                   help="write nothing; exit 0 only if every check passes")
    args = ap.parse_args(argv)
    results_dir = Path(results_dir) if results_dir is not None else RESULTS_DIR
    if args.write:
        write(results_dir)
        print(f"wrote {MD_NAME} and {JSON_NAME} in {results_dir.name}/")
        return 0
    return 1 if check(results_dir) else 0


if __name__ == "__main__":
    raise SystemExit(main())
