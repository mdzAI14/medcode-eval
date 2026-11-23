"""Put Part C cases in front of a model, for
ICD-10-CM FY2027 (October 1, 2026 release).

Cases are read and sent as in Part B (medcode_eval.run.part_b, whose run
and write_answers do the work): only the case file's text after its front
matter reaches the model. Default data folder data/part_c/; run folders
runs/part_c/<run-id>/.

Conditions:
  plain         one turn: prompts/part_b_plain.txt itself.
  reminded      one turn: prompts/part_c_reminded.txt, which is
                part_b_plain.txt with REMINDER inserted after the line
                "first." (build_reminded) and nothing else changed.
  with_checker  the first turn is plain; the second turn reads
                prompts/part_b_checker.txt and works as in Part B.

run.json is Part B's with part "c", the condition, and the sha256 of all
three prompt files Part C can use. --ids, --limit, --prompt-suffix, the
backends, the spending stop and resume work as for Part B.
"""

from pathlib import Path

from medcode_eval.run import part_b
from medcode_eval.run.part_b import write_answers  # noqa: F401  (used by the runner)
from medcode_eval.run.runner import PROMPT_DIR

PROMPT_FILES = {"plain": "part_b_plain.txt", "reminded": "part_c_reminded.txt",
                "checker": "part_b_checker.txt"}
CONDITIONS = ("plain", "reminded", "with_checker")
FIRST_PROMPT = {"plain": "plain", "reminded": "reminded", "with_checker": "plain"}
RUNS_DIR = Path("runs") / "part_c"
DATA_DIR = Path("data") / "part_c"
AFTER = b"first.\n"
REMINDER = (b"Report only what the note documents. Do not assume a detail the\n"
            b"note does not state.\n")


def build_reminded(plain):
    """The bytes of part_c_reminded.txt from the bytes of part_b_plain.txt:
    REMINDER inserted after the one line "first."."""
    lines = plain.splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if l == AFTER]
    if len(hits) != 1:
        raise ValueError(f'expected one line "first." in the plain prompt, found {len(hits)}')
    i = hits[0] + 1
    return b"".join(lines[:i]) + REMINDER + b"".join(lines[i:])


def load_prompts(condition):
    """{"plain": first-turn template, "checker": second-turn template} for a
    condition, the form medcode_eval.run.part_b reads."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, not {condition!r}")
    first = PROMPT_FILES[FIRST_PROMPT[condition]]
    return {"plain": (PROMPT_DIR / first).read_text(encoding="ascii"),
            "checker": (PROMPT_DIR / PROMPT_FILES["checker"]).read_text(encoding="ascii")}


def render_first(case, condition, prompt_suffix=""):
    """The first-turn prompt of a case under a condition."""
    return part_b.render_first(case, load_prompts(condition), prompt_suffix)


def run(data_dir, run_dir, backend, condition, **kw):
    """medcode_eval.run.part_b.run with Part C's part, conditions, prompt
    files and prompts. Keyword arguments as there (ids, limit, log,
    prompt_suffix, checker_data, ledger)."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, not {condition!r}")
    return part_b.run(data_dir, run_dir, backend, condition, part="c", conditions=CONDITIONS,
                      prompt_files=PROMPT_FILES, prompts=load_prompts(condition), **kw)
