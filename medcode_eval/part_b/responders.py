"""Fake Part B responders for tests and harness checks. No model is called.

Each returns a function from messages to a reply, for
FakeBackend(fn, messages=True).

  oracle  replies with the gold codes of the case whose note is in the first
          user message, as a JSON list (codes as written in data/gold), on
          every turn. It reads gold so that the harness can be checked; the
          model backends never do.
  fixed   replies with the same JSON list on every turn. WRONG is a code
          that the checker reports with an error finding on the committed
          FY2027 refdata (a header: the 7th character is missing).
"""

import json
from pathlib import Path

from medcode_eval.run.part_b import load_cases

WRONG = ["S52.501"]


def oracle(data_dir):
    data_dir = Path(data_dir)
    by_note = {}
    for c in load_cases(data_dir):
        gold = json.loads((data_dir / "gold" / f"{c['id']}.json").read_text(encoding="utf-8"))
        by_note[c["note"]] = gold["codes"]

    def fn(messages):
        first = messages[0]["content"]
        hits = [codes for note, codes in by_note.items() if note in first]
        if len(hits) != 1:
            raise ValueError(f"oracle: {len(hits)} case notes match the prompt")
        return json.dumps(hits[0])
    return fn


def fixed(answer):
    reply = json.dumps(list(answer))
    return lambda messages: reply
