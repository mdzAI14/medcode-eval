"""Spending stop for paid model runs.

A ledger is a JSONL file under runs/spend/ that several runs may share.
Every paid reply appends one line:
    time, run_id, item_id, turn, usage (the reply's whole usage object),
    cost_usd, request_chars
Cost: input_tokens plus every top-level integer cache token field of usage
(cache_creation_input_tokens, cache_read_input_tokens, ...) at the input
price, and output_tokens at the output price. Prices are USD per million
tokens and are given by the caller; none is stored in code.

Before each request, check() adds up cost_usd over the whole ledger and
refuses (raises SpendStop) when that total plus the worst case of the next
request would pass max_usd. Worst case: the request's characters divided
by WORST_CHARS_PER_TOKEN (3) as input tokens, plus max_tokens of output.
A refused request is never sent, so the stop fires before the request that
could cross the cap, never after.
"""

import json
import time
from pathlib import Path

WORST_CHARS_PER_TOKEN = 3


class SpendStop(Exception):
    """The next request could pass the spending cap; it was not sent."""


def _cache_tokens(usage):
    return sum(v for k, v in usage.items()
               if k.startswith("cache_") and k.endswith("_tokens") and isinstance(v, int))


def input_tokens(usage):
    """input_tokens plus the cache token fields."""
    return int(usage.get("input_tokens") or 0) + _cache_tokens(usage)


class Ledger:
    def __init__(self, path, price_in, price_out, max_usd, run_id):
        for name, v in (("price_in", price_in), ("price_out", price_out)):
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"{name} must be a number >= 0")
        if not isinstance(max_usd, (int, float)) or max_usd <= 0:
            raise ValueError("max_usd must be a number > 0")
        self.path = Path(path)
        self.price_in = float(price_in)
        self.price_out = float(price_out)
        self.max_usd = float(max_usd)
        self.run_id = run_id
        self.stopped = None  # the refusal message once the stop has fired

    def describe(self, ledger_name):
        return {"price_in_usd_per_mtok": self.price_in,
                "price_out_usd_per_mtok": self.price_out,
                "max_usd": self.max_usd, "ledger": ledger_name}

    def cost(self, usage):
        return (input_tokens(usage) * self.price_in
                + int(usage.get("output_tokens") or 0) * self.price_out) / 1e6

    def worst_case(self, request_chars, max_tokens):
        return (request_chars / WORST_CHARS_PER_TOKEN * self.price_in
                + max_tokens * self.price_out) / 1e6

    def total(self):
        if not self.path.is_file():
            return 0.0
        total = 0.0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += float(json.loads(line)["cost_usd"])
        return total

    def check(self, request_chars, max_tokens):
        """Raise SpendStop when the ledger total plus this request's worst
        case would pass max_usd."""
        spent = self.total()
        worst = self.worst_case(request_chars, max_tokens)
        if spent + worst > self.max_usd:
            self.stopped = (f"spending stop: spent {spent:.4f} USD; the next request could "
                            f"cost up to {worst:.4f} USD, which would pass the cap of "
                            f"{self.max_usd:.2f} USD; it was not sent")
            raise SpendStop(self.stopped)

    def record(self, item_id, turn, usage, request_chars):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "run_id": self.run_id,
               "item_id": item_id, "turn": turn, "usage": usage,
               "cost_usd": self.cost(usage), "request_chars": request_chars}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()


def request_chars(messages):
    return sum(len(m["content"]) for m in messages)


def before(ledger, backend, messages):
    """The spending check before a request; returns the request's characters.
    Raises SpendStop. A remote backend without a ledger is refused."""
    if ledger is None:
        if getattr(backend, "name", None) == "remote":
            raise ValueError("a remote run needs a ledger (the spending stop)")
        return None
    n = request_chars(messages)
    ledger.check(n, backend.max_tokens)
    return n


def after(ledger, item_id, turn, row, chars):
    """Record a paid reply's usage in the ledger and its characters in the row."""
    if ledger is None:
        return
    row["request_chars"] = chars
    if isinstance(row.get("usage"), dict):
        ledger.record(item_id, turn, row["usage"], chars)
