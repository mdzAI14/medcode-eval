"""Score a Part B run against the gold (ICD-10-CM FY2027, October 1, 2026
release).

Gold comes from <data-dir>/gold/<id>.json (codes, target_trap); the
specialty from the case file's front matter. Answers come from a run's
answers.jsonl (medcode_eval.run.part_b). Codes on both sides are normalised
with medcode_eval.checker.normalise.

For the first and the final answer, per case and overall:
  exact             the answer's code set equals the gold's (order ignored)
  first_listed      the answer's first code is the gold's first code
  correct, missing, extra
                    codes in both, only in gold, only in the answer (sets);
                    precision = correct / (correct + extra) and recall =
                    correct / (correct + missing), over all codes of the group
  invalid           an answers row whose answer is invalid (or errored)
  no_answer         a gold case with no answers row
  findings          checker findings on the answer's codes, by level, and
                    the number of cases with any error finding
An invalid answer or no answer counts as no codes. Groups: overall, by
target trap and by specialty; every group with fewer than 10 cases is
flagged (fewer_than_10) and the markdown says so.

Usage (from the repo root):
    venv/bin/python -m medcode_eval.part_b.score --run-id RUN [--data-dir data] \
        [--out-json S.json --out-md S.md]
Without --out-*, score.json and score.md are written in the run directory.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_a.score import load_jsonl
from medcode_eval.part_b.validate import IGNORED, parse_front_matter

SMALL = 10
ANSWERS = ("first", "final")
LEVELS = ("error", "review")


def load_gold(data_dir):
    out = {}
    for p in sorted((Path(data_dir) / "gold").glob("*.json")):
        if p.name not in IGNORED:
            out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def load_case_meta(data_dir):
    out = {}
    for p in sorted((Path(data_dir) / "cases").glob("*.md")):
        if p.name in IGNORED:
            continue
        parsed = parse_front_matter(p.read_text(encoding="utf-8"))
        out[p.stem] = {"specialty": (parsed[0] if parsed else {}).get("specialty")}
    return out


def _case(gold_codes, answer, present, data):
    g = [checker.normalise(c) for c in gold_codes]
    a = answer if answer is not None else []
    gs, as_ = set(g), set(a)
    levels = Counter(f["level"] for f in checker.check(a, data=data)) if a else Counter()
    return {
        "codes": answer,
        "exact": answer is not None and gs == as_,
        "first_listed": bool(a) and a[0] == g[0],
        "correct": len(gs & as_), "missing": len(gs - as_), "extra": len(as_ - gs),
        "invalid": present and answer is None,
        "no_answer": not present,
        "findings": {lv: levels.get(lv, 0) for lv in LEVELS},
    }


def _group(rows):
    n = len(rows)
    c = sum(r["correct"] for r in rows)
    m = sum(r["missing"] for r in rows)
    e = sum(r["extra"] for r in rows)
    return {
        "n": n,
        "exact": sum(r["exact"] for r in rows),
        "first_listed": sum(r["first_listed"] for r in rows),
        "correct": c, "missing": m, "extra": e,
        "precision": c / (c + e) if c + e else None,
        "recall": c / (c + m) if c + m else None,
        "invalid": sum(r["invalid"] for r in rows),
        "no_answer": sum(r["no_answer"] for r in rows),
        "findings": {lv: sum(r["findings"][lv] for r in rows) for lv in LEVELS},
        "cases_with_error_finding": sum(r["findings"]["error"] > 0 for r in rows),
        "fewer_than_10": n < SMALL,
    }


def score(gold, case_meta, answers, checker_data=None):
    """gold: {id: gold dict}; case_meta: {id: {"specialty"}}; answers: rows."""
    data = checker_data or checker.default_data()
    given = {}
    for r in answers:
        if r["id"] in given:
            raise ValueError(f"duplicate answer id {r['id']!r}")
        given[r["id"]] = r
    cases = []
    for cid in sorted(gold):
        g = gold[cid]
        r = given.get(cid)
        row = {"id": cid, "target_trap": g.get("target_trap"),
               "specialty": case_meta.get(cid, {}).get("specialty"),
               "gold": [checker.normalise(c) for c in g["codes"]],
               "second_turn": bool(r and r.get("second_turn"))}
        for which in ANSWERS:
            row[which] = _case(g["codes"], r.get(f"{which}_answer") if r else None,
                               r is not None, data)
        cases.append(row)

    def groups(which, key):
        values = sorted({c[key] for c in cases}, key=str)
        return {str(v): _group([c[which] for c in cases if c[key] == v]) for v in values}

    out = {
        "code_set": CODE_SET,
        "n_cases": len(cases),
        "n_answers": len(given),
        "unknown_answer_ids": len(set(given) - set(gold)),
        "second_turns": sum(c["second_turn"] for c in cases),
        "small_group_threshold": SMALL,
        "cases": cases,
    }
    for which in ANSWERS:
        out[which] = {"overall": _group([c[which] for c in cases]),
                      "by_target_trap": groups(which, "target_trap"),
                      "by_specialty": groups(which, "specialty")}
    return out


def _fmt(x):
    return "n/a" if x is None else f"{x:.4f}"


def to_markdown(result):
    head = ("| Group | Value | n | Exact | First-listed | Correct | Missing | Extra "
            "| Precision | Recall | Invalid | No answer | Error findings | Review findings "
            "| Cases with an error finding | Note |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")

    def line(group, value, g):
        note = "fewer than 10 cases" if g["fewer_than_10"] else ""
        return (f"| {group} | {value} | {g['n']} | {g['exact']} | {g['first_listed']} "
                f"| {g['correct']} | {g['missing']} | {g['extra']} | {_fmt(g['precision'])} "
                f"| {_fmt(g['recall'])} | {g['invalid']} | {g['no_answer']} "
                f"| {g['findings']['error']} | {g['findings']['review']} "
                f"| {g['cases_with_error_finding']} | {note} |\n")

    out = [f"Code set: {result['code_set']}. Cases: {result['n_cases']}. "
           f"Answers: {result['n_answers']} ({result['unknown_answer_ids']} with unknown "
           f"ids). Second turns: {result['second_turns']}.\n"]
    for which, title in (("first", "First answer"), ("final", "Final answer")):
        r = result[which]
        out += [f"\n{title}:\n\n", head, line("overall", "", r["overall"])]
        for k, g in r["by_target_trap"].items():
            out.append(line("target trap", k, g))
        for k, g in r["by_specialty"].items():
            out.append(line("specialty", k, g))
    out.append("\nPer case:\n\n| Case | Trap | Specialty | Gold | First | Final "
               "| Second turn | Exact first / final |\n|---|---|---|---|---|---|---|---|\n")
    for c in result["cases"]:
        def codes(x):
            return "invalid" if x["invalid"] else "none" if x["no_answer"] else \
                " ".join(checker.dotted(v) for v in x["codes"]) or "[]"
        out.append(f"| {c['id']} | {c['target_trap']} | {c['specialty']} "
                   f"| {' '.join(checker.dotted(v) for v in c['gold'])} | {codes(c['first'])} "
                   f"| {codes(c['final'])} | {'yes' if c['second_turn'] else 'no'} "
                   f"| {'yes' if c['first']['exact'] else 'no'} / "
                   f"{'yes' if c['final']['exact'] else 'no'} |\n")
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score a Part B run.")
    ap.add_argument("--run-id")
    ap.add_argument("--answers", help="an answers.jsonl path instead of --run-id")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--out-json")
    ap.add_argument("--out-md")
    args = ap.parse_args(argv)
    if bool(args.run_id) == bool(args.answers):
        ap.error("give exactly one of --run-id and --answers")
    from medcode_eval.run.part_b import RUNS_DIR
    run_dir = REPO_ROOT / RUNS_DIR / args.run_id if args.run_id else None
    answers_path = Path(args.answers) if args.answers else run_dir / "answers.jsonl"
    if not (args.out_json and args.out_md) and run_dir is None:
        ap.error("--out-json and --out-md are needed with --answers")
    data_dir = Path(args.data_dir) if args.data_dir else REPO_ROOT / "data"
    result = score(load_gold(data_dir), load_case_meta(data_dir), load_jsonl(answers_path))
    out_json = Path(args.out_json) if args.out_json else run_dir / "score.json"
    out_md = Path(args.out_md) if args.out_md else run_dir / "score.md"
    out_json.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="ascii")
    out_md.write_text(to_markdown(result), encoding="ascii")
    return result


if __name__ == "__main__":
    main()
