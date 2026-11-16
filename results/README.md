# results

Stored outputs of the model runs behind this repository's reported
numbers. Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Every file in the run folders is a byte-for-byte copy of what the
run wrote. Each run was made once.

- part_a/ and part_b/: the reported runs. Each folder holds the run
  settings (run.json), the model's replies as received (raw.jsonl),
  the answers as read from them (responses.jsonl or answers.jsonl),
  and the scores (score.json, score.md). Most runs through a paid
  API also hold a usage summary (usage.json).
- review/part_b/: runs that are not reported results. They were
  made while the Part B cases were being written, as a second look
  at the gold codes, on the gold as it stood on the day of each
  run. Gold files changed after some of them, so they carry no
  score files. They are kept so that a reader can see the answers
  those changes followed. The datasheet in the top-level README
  names each change.
- RESULTS.md and results.json: every figure quoted in the
  top-level README, rebuilt from the files above by

      venv/bin/python -m medcode_eval.results --write

  and checked against them by

      venv/bin/python -m medcode_eval.results --check

Folder names are the run ids. A name ending in -reader2 is a run
whose replies were read again with answer reader 2, the reader all
reported Part A numbers use.
