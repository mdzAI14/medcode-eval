"""Score a Part C run against the gold for
ICD-10-CM FY2027 (October 1, 2026 release).

Everything the Part B scorer reports (medcode_eval.part_b.score, run with
group_key gap_type), for the first and the final answer, with rows overall,
by gap_type and by specialty, plus:

  unsupported_given   per case and answer: the answer's codes, less its
                      optional codes, that match an entry of the gold's
                      unsupported_codes (medcode_eval.part_c.matches: equal
                      to the entry or starting with it, both normalised as
                      the checker normalises codes), each once, in answer
                      order
  gap_cases, gap_cases_with_unsupported
                      in every row: the number of gap cases in the row and
                      the number of them whose answer has at least one
                      unsupported code. A counter_case is never counted here.
  by_case_kind        one row for all gap cases together (gap_case) and one
                      for all counter-cases (counter_case)

score.md opens with the Part B header line and a headline:
"Unsupported code given: X of N gap cases (first answer), Y of N (final
answer)". gold_sha256 is medcode_eval.part_b.score.gold_sha256 of the
data folder used (its gold/ files).

Usage (from the repo root):
    venv/bin/python -m medcode_eval.part_c.score --run-id RUN [--data-dir data/part_c] \
        [--out-json S.json --out-md S.md]
Run folders are runs/part_c/<run-id>/. Without --out-*, score.json and
score.md are written in the run directory.
"""

import argparse
import json
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import REPO_ROOT
from medcode_eval.part_a.score import load_jsonl
from medcode_eval.part_b import score as part_b
from medcode_eval.part_b.score import _fmt, _group, _stops, gold_sha256, load_case_meta, load_gold
from medcode_eval.part_c import is_gap_case, matching

ANSWERS = part_b.ANSWERS
KINDS = ("gap_case", "counter_case")
KIND_LABELS = {"gap_case": "gap cases", "counter_case": "counter-cases"}


def _gap_counts(rows, which):
    gaps = [c for c in rows if c["case_kind"] == "gap_case"]
    return {"gap_cases": len(gaps),
            "gap_cases_with_unsupported": sum(bool(c[which]["unsupported_given"])
                                              for c in gaps)}


def score(gold, case_meta, answers, checker_data=None, gold_hash=None):
    """As medcode_eval.part_b.score.score, with the Part C counts (see the
    module text). A gap_type outside the schema raises ValueError."""
    kinds = {cid: "gap_case" if is_gap_case(g.get("gap_type")) else "counter_case"
             for cid, g in gold.items()}
    out = part_b.score(gold, case_meta, answers, checker_data=checker_data,
                       gold_hash=gold_hash, group_key="gap_type")
    cases = out["cases"]
    for c in cases:
        entries = [checker.normalise(e["code"])
                   for e in gold[c["id"]].get("unsupported_codes") or []]
        c["case_kind"] = kinds[c["id"]]
        c["unsupported"] = entries
        opt = set(c["optional"])
        for which in ANSWERS:
            given = [x for x in c[which]["codes"] or [] if x not in opt]
            c[which]["unsupported_given"] = matching(given, entries)
    out["part"] = "c"
    out["gap_cases"] = sum(k == "gap_case" for k in kinds.values())
    for which in ANSWERS:
        r = out[which]
        r["overall"].update(_gap_counts(cases, which))
        for key, field in (("by_gap_type", "gap_type"), ("by_specialty", "specialty")):
            for v, g in r[key].items():
                g.update(_gap_counts([c for c in cases if str(c[field]) == v], which))
        r["by_case_kind"] = {}
        for kind in KINDS:
            sel = [c for c in cases if c["case_kind"] == kind]
            r["by_case_kind"][kind] = {**_group([c[which] for c in sel]),
                                       **_gap_counts(sel, which)}
    return out


def headline(result):
    n = result["gap_cases"]
    x = result["first"]["overall"]["gap_cases_with_unsupported"]
    y = result["final"]["overall"]["gap_cases_with_unsupported"]
    return (f"Unsupported code given: {x} of {n} gap cases (first answer), "
            f"{y} of {n} (final answer)")


def to_markdown(result):
    head = ("| Group | Value | n | Exact | First-listed | Correct | Missing | Extra "
            "| Optional given | Precision | Recall | Invalid | No answer | Error findings "
            "| Review findings | Cases with an error finding | Gap cases "
            "| Gap cases with an unsupported code | Note |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")

    def line(group, value, g):
        note = "fewer than 10 cases" if g["fewer_than_10"] else ""
        return (f"| {group} | {value} | {g['n']} | {g['exact']} | {g['first_listed']} "
                f"| {g['correct']} | {g['missing']} | {g['extra']} | {g['optional_given']} "
                f"| {_fmt(g['precision'])} | {_fmt(g['recall'])} | {g['invalid']} "
                f"| {g['no_answer']} | {g['findings']['error']} | {g['findings']['review']} "
                f"| {g['cases_with_error_finding']} | {g['gap_cases']} "
                f"| {g['gap_cases_with_unsupported']} | {note} |\n")

    def dotted(codes):
        return " ".join(checker.dotted(v) for v in codes)

    out = [f"Part C. Code set: {result['code_set']}. Gold sha256: {result.get('gold_sha256')}. "
           f"Cases: {result['n_cases']} ({result['gap_cases']} gap cases). "
           f"Answers: {result['n_answers']} ({result['unknown_answer_ids']} with unknown "
           f"ids). Second turns: {result['second_turns']}. Stop reasons: "
           f"{_stops(result)}; cases with a reply whose stop reason is not end_turn: "
           f"{result.get('not_end_turn', 0)}.\n",
           f"\n{headline(result)}.\n"]
    for which, title in (("first", "First answer"), ("final", "Final answer")):
        r = result[which]
        out += [f"\n{title}:\n\n", head, line("overall", "", r["overall"])]
        for k in KINDS:
            out.append(line("case kind", KIND_LABELS[k], r["by_case_kind"][k]))
        for k, g in r["by_gap_type"].items():
            out.append(line("gap type", k, g))
        for k, g in r["by_specialty"].items():
            out.append(line("specialty", k, g))
    out.append("\nPer case:\n\n| Case | Gap type | Specialty | Gold | Optional | Unsupported "
               "| First | Final | Second turn | Exact first / final "
               "| Unsupported given first | Unsupported given final |\n"
               "|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for c in result["cases"]:
        def codes(x):
            return "invalid" if x["invalid"] else "none" if x["no_answer"] else \
                dotted(x["codes"]) or "[]"
        out.append(f"| {c['id']} | {c['gap_type']} | {c['specialty']} | {dotted(c['gold'])} "
                   f"| {dotted(c['optional']) or '-'} | {dotted(c['unsupported']) or '-'} "
                   f"| {codes(c['first'])} | {codes(c['final'])} "
                   f"| {'yes' if c['second_turn'] else 'no'} "
                   f"| {'yes' if c['first']['exact'] else 'no'} / "
                   f"{'yes' if c['final']['exact'] else 'no'} "
                   f"| {dotted(c['first']['unsupported_given']) or '-'} "
                   f"| {dotted(c['final']['unsupported_given']) or '-'} |\n")
    return "".join(out)


def main(argv=None, checker_data=None):
    from medcode_eval.run.part_c import DATA_DIR, RUNS_DIR
    ap = argparse.ArgumentParser(prog="python -m medcode_eval.part_c.score",
                                 description="Score a Part C run.")
    ap.add_argument("--run-id", help=f"a run folder under {RUNS_DIR}/")
    ap.add_argument("--answers", help="an answers.jsonl path instead of --run-id")
    ap.add_argument("--data-dir", default=None, help=f"default {DATA_DIR}/")
    ap.add_argument("--out-json")
    ap.add_argument("--out-md")
    args = ap.parse_args(argv)
    if bool(args.run_id) == bool(args.answers):
        ap.error("give exactly one of --run-id and --answers")
    run_dir = REPO_ROOT / RUNS_DIR / args.run_id if args.run_id else None
    answers_path = Path(args.answers) if args.answers else run_dir / "answers.jsonl"
    if not (args.out_json and args.out_md) and run_dir is None:
        ap.error("--out-json and --out-md are needed with --answers")
    data_dir = Path(args.data_dir) if args.data_dir else REPO_ROOT / DATA_DIR
    result = score(load_gold(data_dir), load_case_meta(data_dir), load_jsonl(answers_path),
                   checker_data=checker_data, gold_hash=gold_sha256(data_dir))
    out_json = Path(args.out_json) if args.out_json else run_dir / "score.json"
    out_md = Path(args.out_md) if args.out_md else run_dir / "score.md"
    out_json.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="ascii")
    out_md.write_text(to_markdown(result), encoding="ascii")
    return result


if __name__ == "__main__":
    main()
