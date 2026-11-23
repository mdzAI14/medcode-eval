# results

Stored outputs of the model runs behind this repository's reported
numbers. Code set: ICD-10-CM FY2027 (October 1, 2026 release).

Every file in the run folders is a byte-for-byte copy of what the
run wrote. Each run was made once.

- part_a/, part_b/ and part_c/: the reported runs. Each folder
  holds the run settings (run.json), the model's replies as
  received (raw.jsonl), the answers as read from them
  (responses.jsonl or answers.jsonl), and the scores (score.json,
  score.md). Most runs through a paid API also hold a usage
  summary (usage.json).
- part_c/repeat/: one run that is not a reported result. It is
  the Part C "reminded" condition run a second time on the same
  model, kept only to show how much two runs of one prompt
  differ. Which run is reported and which is the repeat was fixed
  before either was made. It is scored on the same gold and
  checked like the reported runs.
- review/part_b/: runs that are not reported results. They were
  made while the Part B cases were being written, as a second look
  at the gold codes, on the gold as it stood on the day of each
  run. Gold files changed after some of them, so they carry no
  score files. They are kept so that a reader can see the answers
  those changes followed. The datasheet in the top-level README
  names each change.
- review/part_c/: runs that are not reported results. They were
  made while the Part C cases were being written, five cases at a
  time, as a second look at the gold codes. Each was scored at the
  time against the cases that existed that day, so they carry no
  score files. No gold file changed after any of them. They are
  kept so that a reader can see what the author had seen of the
  evaluated model before the later cases were written and before
  the reported runs were made. The Part C datasheet in the
  top-level README says more.
- RESULTS.md and results.json: every figure quoted in the
  top-level README, rebuilt from the files above by

      venv/bin/python -m medcode_eval.results --write

  and checked against them by

      venv/bin/python -m medcode_eval.results --check

Folder names are the run ids. A name ending in -reader2 is a run
whose replies were read again with answer reader 2, the reader all
reported Part A numbers use.

In a score.md, a code that the model wrote in a malformed way (a
misplaced dot, or too many characters) is shown with an extra dot,
for example "T82..119XA" for the eight-character answer
"T82.119XA". RESULTS.md shows such a code as the model gave it.
Either way it counts as an extra code.
