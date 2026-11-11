"""Usage summary of a run whose raw.jsonl rows carry a usage object (the
remote backend). No model is called.

For the rows with usage (replies):
  replies, stop_reasons (counts)
  input_tokens      input_tokens plus the cache token fields
                    (medcode_eval.run.spend.input_tokens): total, mean, min, max
  output_tokens     total, mean, min, max
  thinking_tokens   total over the replies whose usage has
                    output_tokens_details.thinking_tokens, and how many do
  cost_usd          at the prices in run.json's "spend"
  input_ratio_to_chars_div_4
                    real input tokens / the sum of round(request_chars / 4)
                    (the dry-run's estimate), over replies with request_chars
  per_item          per item id (Part B: both turns together): input and
                    output tokens and cost; with min, mean and max of the
                    per-item cost (per_item_cost_usd)

Usage (from the repo root):
    venv/bin/python -m medcode_eval.run.usage --run-dir runs/part_b/RUN [--out-json F]
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from medcode_eval.part_a.score import load_jsonl
from medcode_eval.run.spend import input_tokens


def _stats(values):
    if not values:
        return {"total": 0, "mean": None, "min": None, "max": None}
    return {"total": sum(values), "mean": sum(values) / len(values),
            "min": min(values), "max": max(values)}


def summarize(run_dir):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    prices = meta.get("spend") or {}
    p_in = prices.get("price_in_usd_per_mtok")
    p_out = prices.get("price_out_usd_per_mtok")
    rows = [r for r in load_jsonl(run_dir / "raw.jsonl") if isinstance(r.get("usage"), dict)]

    def cost(i, o):
        return None if p_in is None or p_out is None else (i * p_in + o * p_out) / 1e6

    ins = [input_tokens(r["usage"]) for r in rows]
    outs = [int(r["usage"].get("output_tokens") or 0) for r in rows]
    think = [r["usage"]["output_tokens_details"]["thinking_tokens"] for r in rows
             if isinstance(r["usage"].get("output_tokens_details"), dict)
             and isinstance(r["usage"]["output_tokens_details"].get("thinking_tokens"), int)]
    with_chars = [(i, r["request_chars"]) for i, r in zip(ins, rows)
                  if isinstance(r.get("request_chars"), int)]
    est = sum(round(c / 4) for _, c in with_chars)
    per_item = {}
    for i, o, r in zip(ins, outs, rows):
        d = per_item.setdefault(r["id"], {"replies": 0, "input_tokens": 0, "output_tokens": 0})
        d["replies"] += 1
        d["input_tokens"] += i
        d["output_tokens"] += o
    for d in per_item.values():
        d["cost_usd"] = cost(d["input_tokens"], d["output_tokens"])
    item_costs = [d["cost_usd"] for d in per_item.values() if d["cost_usd"] is not None]
    return {
        "run": run_dir.name,
        "model": meta.get("model"),
        "settings": meta.get("settings"),
        "spend": prices or None,
        "replies": len(rows),
        "items": len(per_item),
        "stop_reasons": dict(sorted(Counter(str(r.get("stop_reason")) for r in rows).items())),
        "input_tokens": _stats(ins),
        "output_tokens": _stats(outs),
        "thinking_tokens": {"replies_with_field": len(think), "total": sum(think)},
        "cost_usd": cost(sum(ins), sum(outs)),
        "input_ratio_to_chars_div_4": (sum(i for i, _ in with_chars) / est) if est else None,
        "per_item": per_item,
        "per_item_cost_usd": _stats(item_costs),
    }


def _f(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def to_markdown(s):
    i, o, c = s["input_tokens"], s["output_tokens"], s["per_item_cost_usd"]
    return "\n".join([
        f"Run {s['run']} ({s['model']}): {s['replies']} replies over {s['items']} items. "
        f"Stop reasons: " + ", ".join(f"{k} {v}" for k, v in s["stop_reasons"].items()) + ".",
        "",
        "| Measure | Total | Mean | Min | Max |", "|---|---|---|---|---|",
        f"| input tokens (incl. cache fields) | {i['total']} | {_f(i['mean'])} "
        f"| {i['min']} | {i['max']} |",
        f"| output tokens | {o['total']} | {_f(o['mean'])} | {o['min']} | {o['max']} |",
        f"| cost per item, USD | {_f(sum(d['cost_usd'] or 0 for d in s['per_item'].values()), 4)} "
        f"| {_f(c['mean'], 5)} | {_f(c['min'], 5)} | {_f(c['max'], 5)} |",
        "",
        f"Thinking tokens: {s['thinking_tokens']['total']} over "
        f"{s['thinking_tokens']['replies_with_field']} replies that report the field. "
        f"Cost at the recorded prices: {_f(s['cost_usd'], 4)} USD. Real input tokens / "
        f"(characters / 4) estimate: {_f(s['input_ratio_to_chars_div_4'], 3)}.",
    ]) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Usage summary of a run.")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-json")
    args = ap.parse_args(argv)
    s = summarize(args.run_dir)
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(s, sort_keys=True, indent=2) + "\n",
                                       encoding="utf-8")
    print(to_markdown(s), end="")
    return s


if __name__ == "__main__":
    main()
