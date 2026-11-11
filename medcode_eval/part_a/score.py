"""Score Part A responses against the probes.

Input: a probes file (JSONL, from generate.py) and a responses file (JSONL,
one {"id": ..., "response": ...} per line). Output: JSON and a markdown
table with accuracy overall, by type, by chapter, for not_a_code probes by
kind and, for probes that carry a `change` field, by change. Each row gives plain accuracy and the mean of the per-chapter
accuracies (chapters present in that row; deleted-code probes with no
chapter form the group "none").

Normalisation before comparing:
  code_to_description  dots and whitespace removed, upper case; valid
                       answers are A, B, C, D. A response that is one
                       letter A-D (either case, leading whitespace allowed)
                       followed by ".", ")" or ":" and then any text counts
                       as that letter.
  description_to_code  dots and whitespace removed, upper case; valid
                       answers are 3-7 letters or digits
  status               dots removed, lower case, runs of whitespace
                       joined by "_"; valid answers are billable, header,
                       not_a_code
A response that is missing, or is not a valid answer for its probe type, is
wrong; missing and invalid responses are counted separately.

status_table: for status probes, counts by expected answer (rows billable,
header, not_a_code) and response (columns billable, header, not_a_code,
invalid, missing).

Usage:
    venv/bin/python -m medcode_eval.part_a.score --probes P --responses R \
        --out-json S.json --out-md S.md
"""

import argparse
import json
import re
from collections import defaultdict

_CODE = re.compile(r"[A-Z0-9]{3,7}")
_LETTER_WITH_TEXT = re.compile(r"\s*([A-Da-d])[.):]", re.S)
STATUS_COLUMNS = ("billable", "header", "not_a_code", "invalid", "missing")
STATUS_ANSWERS = ("billable", "header", "not_a_code")
TYPES = ("code_to_description", "description_to_code", "status")


def _norm_answer(type_, text):
    if type_ == "status":
        return "_".join(text.replace(".", "").lower().split())
    return re.sub(r"[\s.]", "", text).upper()


def parse_response(probe, response):
    """Normalised response, or None when it is not a valid answer."""
    if not isinstance(response, str):
        return None
    t = probe["type"]
    v = _norm_answer(t, response)
    if t == "code_to_description":
        if len(v) == 1 and v in "ABCD":
            return v
        m = _LETTER_WITH_TEXT.match(response)
        return m.group(1).upper() if m else None
    if t == "description_to_code":
        return v if _CODE.fullmatch(v) else None
    if t == "status":
        return v if v in STATUS_ANSWERS else None
    raise ValueError(f"unknown probe type {t!r}")


def _chapter_key(ch):
    return "none" if ch is None else str(ch)


def _group(rows):
    n = len(rows)
    correct = sum(r["correct"] for r in rows)
    per_ch = defaultdict(list)
    for r in rows:
        per_ch[r["chapter"]].append(r["correct"])
    means = [sum(v) / len(v) for v in per_ch.values()]
    return {
        "n": n,
        "correct": correct,
        "accuracy": correct / n if n else None,
        "chapter_mean_accuracy": sum(means) / len(means) if means else None,
        "chapters": len(per_ch),
        "missing": sum(r["missing"] for r in rows),
        "invalid": sum(r["invalid"] for r in rows),
    }


def _chapter_sort(key):
    return (1, 0) if key == "none" else (0, int(key))


def score(probes, responses):
    """Score; responses is a list of {"id", "response"} dicts."""
    given = {}
    for r in responses:
        if r["id"] in given:
            raise ValueError(f"duplicate response id {r['id']!r}")
        given[r["id"]] = r.get("response")
    ids = {p["id"] for p in probes}
    rows = []
    status_table = {a: {c: 0 for c in STATUS_COLUMNS} for a in STATUS_ANSWERS}
    for p in probes:
        missing = p["id"] not in given
        value = None if missing else parse_response(p, given[p["id"]])
        invalid = not missing and value is None
        correct = value is not None and value == _norm_answer(p["type"], p["answer"])
        rows.append({"type": p["type"], "chapter": _chapter_key(p["chapter"]),
                     "kind": p.get("kind"), "change": p.get("change"),
                     "correct": correct,
                     "missing": missing, "invalid": invalid})
        if p["type"] == "status":
            gold = _norm_answer("status", p["answer"])
            col = "missing" if missing else "invalid" if invalid else value
            status_table[gold][col] += 1
    by_chapter = defaultdict(list)
    for r in rows:
        by_chapter[r["chapter"]].append(r)
    code_sets = sorted({p.get("code_set") for p in probes if p.get("code_set")})
    kinds = []
    for r in rows:
        if r["kind"] and r["kind"] not in kinds:
            kinds.append(r["kind"])
    kind_order = ("substituted", "extended", "placeholder_prefix")
    kinds.sort(key=lambda k: (kind_order.index(k) if k in kind_order else 99, k))
    change_order = ("added_billable", "added_header", "billable_to_header", "removed")
    changes = sorted({r["change"] for r in rows if r["change"]},
                     key=lambda c: (change_order.index(c) if c in change_order else 99, c))
    return {
        "code_set": code_sets,
        "n_probes": len(probes),
        "n_responses": len(given),
        "unknown_response_ids": len(set(given) - ids),
        "overall": _group(rows),
        "by_type": {t: _group([r for r in rows if r["type"] == t])
                    for t in TYPES if any(r["type"] == t for r in rows)},
        "by_chapter": {k: _group(by_chapter[k])
                       for k in sorted(by_chapter, key=_chapter_sort)},
        "by_kind": {k: _group([r for r in rows if r["kind"] == k]) for k in kinds},
        "by_change": {c: _group([r for r in rows if r["change"] == c]) for c in changes},
        "status_table": status_table,
    }


def _fmt(x):
    return "n/a" if x is None else f"{x:.4f}"


def to_markdown(result):
    head = ("| Group | Value | n | Correct | Accuracy | Mean of per-chapter accuracy "
            "| Chapters | Missing | Invalid |\n|---|---|---|---|---|---|---|---|---|\n")

    def line(group, value, g):
        return (f"| {group} | {value} | {g['n']} | {g['correct']} | {_fmt(g['accuracy'])} "
                f"| {_fmt(g['chapter_mean_accuracy'])} | {g['chapters']} "
                f"| {g['missing']} | {g['invalid']} |\n")

    out = [f"Code set: {', '.join(result['code_set']) or 'n/a'}. "
           f"Probes: {result['n_probes']}. Responses: {result['n_responses']} "
           f"({result['unknown_response_ids']} with unknown ids).\n\n", head,
           line("overall", "", result["overall"])]
    for t, g in result["by_type"].items():
        out.append(line("type", t, g))
    for k, g in result["by_chapter"].items():
        out.append(line("chapter", k, g))
    for k, g in result["by_kind"].items():
        out.append(line("not_a_code kind", k, g))
    for c, g in result.get("by_change", {}).items():
        out.append(line("change", c, g))
    table = result.get("status_table")
    if table:
        out.append("\nStatus probes, answer by response:\n\n"
                   "| Answer \\ response | " + " | ".join(STATUS_COLUMNS) + " |\n"
                   "|---|" + "---|" * len(STATUS_COLUMNS) + "\n")
        for a, row in table.items():
            out.append(f"| {a} | " + " | ".join(str(row[c]) for c in STATUS_COLUMNS)
                       + " |\n")
    return "".join(out)


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score Part A responses.")
    ap.add_argument("--probes", required=True)
    ap.add_argument("--responses", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    result = score(load_jsonl(args.probes), load_jsonl(args.responses))
    with open(args.out_json, "w", encoding="ascii") as fh:
        fh.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    with open(args.out_md, "w", encoding="ascii") as fh:
        fh.write(to_markdown(result))
    return result


if __name__ == "__main__":
    main()
