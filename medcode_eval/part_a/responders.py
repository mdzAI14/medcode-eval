"""Fake responders for testing the Part A scorer. No model is called.

  oracle    answers every probe correctly (codes shown with the dot, so the
            scorer's dot normalisation is exercised); expected accuracy 1.0
  constant  gives the same answer to every probe of a type (CONSTANT);
            expected accuracy per type is chance_rate()

Usage (writes a responses JSONL file):
    venv/bin/python -m medcode_eval.part_a.responders oracle --probes P --out R
"""

import argparse
import json

from medcode_eval.part_a.generate import display
from medcode_eval.part_a.score import _norm_answer, load_jsonl

CONSTANT = {
    "code_to_description": "A",
    "description_to_code": "A00.0",
    "status": "billable",
}


def oracle(probes):
    out = []
    for p in probes:
        answer = display(p["answer"]) if p["type"] == "description_to_code" else p["answer"]
        out.append({"id": p["id"], "response": answer})
    return out


def constant(probes, constants=CONSTANT):
    return [{"id": p["id"], "response": constants[p["type"]]} for p in probes]


def chance_rate(probes, type_, constants=CONSTANT):
    """Share of probes of a type whose answer equals the constant response."""
    items = [p for p in probes if p["type"] == type_]
    want = _norm_answer(type_, constants[type_])
    hits = sum(_norm_answer(type_, p["answer"]) == want for p in items)
    return hits / len(items)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write fake Part A responses.")
    ap.add_argument("responder", choices=("oracle", "constant"))
    ap.add_argument("--probes", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    probes = load_jsonl(args.probes)
    rows = oracle(probes) if args.responder == "oracle" else constant(probes)
    with open(args.out, "w", encoding="ascii") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
