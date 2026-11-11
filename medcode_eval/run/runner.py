"""Put Part A probes in front of a model and record its replies.

Only a probe's prompt fields reach the model: code and options
(code_to_description), description (description_to_code), code (status).
Each is filled into the prompt file for its type under prompts/. The
setting prompt_suffix (empty by default) is added to the rendered prompt
on its own last line; the prompt files are not changed. The backend
receives the rendered prompt text and nothing else.

Backends (standard library only):
  fake    a Python callable from prompt to reply; for tests
  ollama  the local Ollama server's /api/generate endpoint, non-streaming.
          Only a localhost address is accepted. Settings: temperature 0,
          seed SEED, num_predict NUM_PREDICT, num_ctx NUM_CTX, per-probe
          timeout TIMEOUT seconds. No system prompt and no API reasoning
          switch is sent; reasoning can only be changed through text in
          prompt_suffix (e.g. /no_think for a model whose template reads it).

Output in the run directory (runs/part_a/<run-id>/):
  run.json         backend, model name and digest, settings, prompt_suffix,
                   sha256 of the probe file and of each prompt file,
                   code-set release
  raw.jsonl        one row per probe tried: id, raw reply, seconds, error
                   (plus done_reason and eval_count when the server gives
                   them)
  responses.jsonl  id and extracted answer for every row without an error,
                   for medcode_eval.part_a.score

A rerun with the same run directory skips ids already in raw.jsonl; it
refuses to continue when the probe file, prompts, prompt_suffix, backend,
model or settings differ from run.json. A run.json written before
prompt_suffix existed counts as an empty suffix.

Usage (from the repo root):
    venv/bin/python -m medcode_eval.run.runner --probes data/part_a/probes_lite.jsonl \
        --run-id lite-qwen3-4b [--model qwen3:4b] [--limit N] [--ids a,b,c] \
        [--prompt-suffix /no_think]
"""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from medcode_eval.part_a.generate import CODE_SET, LETTERS, REPO_ROOT
from medcode_eval.part_a.score import load_jsonl

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_FILES = {
    "code_to_description": "part_a_code_to_description.txt",
    "description_to_code": "part_a_description_to_code.txt",
    "status": "part_a_status.txt",
}
RUNS_DIR = Path("runs") / "part_a"

DEFAULT_HOST = "http://127.0.0.1:11434"  # the ollama client's default address
SEED = 20261001
NUM_PREDICT = 4096   # output cap in tokens, reasoning included
NUM_CTX = 8192       # context window in tokens: prompt plus output
TIMEOUT = 900        # seconds per probe
_LOCAL = {"127.0.0.1", "localhost", "::1"}


def load_prompts():
    """Prompt templates by probe type (file text, trailing newline kept)."""
    return {t: (PROMPT_DIR / f).read_text(encoding="ascii") for t, f in PROMPT_FILES.items()}


def prompt_fields(probe):
    """The only probe fields that reach the model, by template field name."""
    t = probe["type"]
    if t == "code_to_description":
        opts = probe["options"]
        if len(opts) != len(LETTERS):
            raise ValueError(f"{probe['id']}: expected {len(LETTERS)} options")
        return {"code": probe["code"],
                **{f"option_{x.lower()}": o for x, o in zip(LETTERS, opts)}}
    if t == "description_to_code":
        return {"description": probe["description"]}
    if t == "status":
        return {"code": probe["code"]}
    raise ValueError(f"unknown probe type {t!r}")


def render_prompt(probe, prompts=None, prompt_suffix=""):
    """The prompt text for a probe, without the file's trailing newline.

    A non-empty prompt_suffix is added on its own last line.
    """
    if "\n" in prompt_suffix or "\r" in prompt_suffix:
        raise ValueError("prompt_suffix must be a single line")
    template = (prompts or load_prompts())[probe["type"]]
    text = template.format_map(prompt_fields(probe)).rstrip("\n")
    return text + "\n" + prompt_suffix if prompt_suffix else text


_THINK = re.compile(r"<think>.*?</think>", re.S)
_MARKS = "\"'`*"
_LABEL = re.compile(r"^\**\s*(?:final\s+)?answer\s*\**\s*:\s*\**\s*", re.I)


def extract_answer(text):
    """The answer line of a reply.

    Drops reasoning wrapped in <think>...</think> (an unclosed <think> drops
    the rest of the reply), takes the last non-empty line, strips quotes,
    backticks and asterisks at either end and one trailing full stop, then
    drops a leading "Answer:" or "Final answer:" label (any case, asterisks
    around it allowed) and strips asterisks again.
    """
    text = _THINK.sub("", text)
    if "<think>" in text:
        text = text[:text.index("<think>")]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    s = lines[-1].strip().strip(_MARKS).strip()
    if s.endswith("."):
        s = s[:-1]
    s = s.strip().strip(_MARKS).strip()
    return _LABEL.sub("", s).strip("*").strip()


class FakeBackend:
    """Replies with fn(prompt). For tests; no model is called."""

    name = "fake"

    def __init__(self, fn, model="fake"):
        self.fn = fn
        self.model = model

    def describe(self):
        return {"backend": self.name, "model": self.model, "model_digest": None,
                "server_version": None, "settings": {}}

    def generate(self, prompt):
        return {"raw": self.fn(prompt)}


class OllamaBackend:
    """The local Ollama server, /api/generate, stream off."""

    name = "ollama"

    def __init__(self, model, host=DEFAULT_HOST, timeout=TIMEOUT):
        u = urllib.parse.urlparse(host)
        if u.scheme != "http" or u.hostname not in _LOCAL:
            raise ValueError(f"only a local Ollama server is allowed, not {host!r}")
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.options = {"temperature": 0, "seed": SEED,
                        "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX}

    def request_body(self, prompt):
        return {"model": self.model, "prompt": prompt, "stream": False,
                "options": dict(self.options)}

    def _call(self, path, body=None, timeout=30):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.host + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def describe(self):
        tags = self._call("/api/tags")["models"]
        digest = next((m["digest"] for m in tags if m["name"] == self.model), None)
        if digest is None:
            raise ValueError(f"model {self.model!r} is not on the local server")
        return {"backend": self.name, "model": self.model, "model_digest": digest,
                "server_version": self._call("/api/version")["version"],
                "settings": {"endpoint": "/api/generate", "stream": False,
                             "options": dict(self.options),
                             "timeout_seconds": self.timeout,
                             "system_prompt": None, "reasoning_switch": None}}

    def generate(self, prompt):
        out = self._call("/api/generate", self.request_body(prompt), timeout=self.timeout)
        return {"raw": out.get("response", ""), "done_reason": out.get("done_reason"),
                "eval_count": out.get("eval_count")}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _append(path, row):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()


def write_responses(run_dir):
    """Rewrite responses.jsonl from raw.jsonl (rows without an error)."""
    run_dir = Path(run_dir)
    rows = load_jsonl(run_dir / "raw.jsonl") if (run_dir / "raw.jsonl").exists() else []
    with open(run_dir / "responses.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            if r["error"] is None:
                fh.write(json.dumps({"id": r["id"], "response": extract_answer(r["raw"])},
                                    sort_keys=True) + "\n")


def run(probes_path, run_dir, backend, ids=None, limit=None, log=None,
        prompt_suffix=""):
    """Run probes (all, or those in ids, in file order) not yet in raw.jsonl.

    limit caps the number of new probes tried in this call. prompt_suffix is
    added to every prompt on its own last line. Returns the number tried.
    """
    if "\n" in prompt_suffix or "\r" in prompt_suffix:
        raise ValueError("prompt_suffix must be a single line")
    probes_path, run_dir = Path(probes_path), Path(run_dir)
    probes = load_jsonl(probes_path)
    code_sets = {p.get("code_set") for p in probes}
    if code_sets != {CODE_SET}:
        raise ValueError(f"probe file code sets {sorted(map(str, code_sets))}, "
                         f"expected only {CODE_SET!r}")
    if ids is not None:
        known = {p["id"] for p in probes}
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise ValueError(f"ids not in the probe file: {unknown}")
        wanted = set(ids)
        probes = [p for p in probes if p["id"] in wanted]
    prompts = load_prompts()
    meta = {
        "code_set": CODE_SET,
        "probes_file": _relative(probes_path),
        "probes_sha256": _sha(probes_path),
        "prompts_sha256": {f: _sha(PROMPT_DIR / f) for f in PROMPT_FILES.values()},
        "prompt_suffix": prompt_suffix,
        **backend.describe(),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "run.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        old.pop("started", None)
        old.setdefault("prompt_suffix", "")  # run.json from before the setting
        if old != meta:
            diff = sorted(k for k in set(old) | set(meta) if old.get(k) != meta.get(k))
            raise ValueError(f"run directory was made with other inputs: {diff}")
    else:
        meta_path.write_text(json.dumps({**meta, "started": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z")}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_path = run_dir / "raw.jsonl"
    done = {r["id"] for r in load_jsonl(raw_path)} if raw_path.exists() else set()
    tried = 0
    for p in probes:
        if p["id"] in done:
            continue
        if limit is not None and tried >= limit:
            break
        prompt = render_prompt(p, prompts, prompt_suffix)
        start = time.monotonic()
        row = {"id": p["id"], "raw": None, "error": None}
        try:
            row.update(backend.generate(prompt))
        except (OSError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["seconds"] = round(time.monotonic() - start, 3)
        _append(raw_path, row)
        done.add(p["id"])
        tried += 1
        if log:
            log(f"{p['id']} {row['seconds']:.1f}s"
                + (f" error {row['error']}" if row["error"] else ""))
    write_responses(run_dir)
    return tried


def _relative(path):
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).name


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run Part A probes through a model.")
    ap.add_argument("--probes", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", default="qwen3:4b")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="comma-separated probe ids")
    ap.add_argument("--prompt-suffix", default="",
                    help="text added to every prompt on its own last line")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
        ap.error("run id: letters, digits, '.', '_' and '-' only")
    backend = OllamaBackend(args.model, host=args.host)
    ids = args.ids.split(",") if args.ids else None
    n = run(args.probes, REPO_ROOT / RUNS_DIR / args.run_id, backend, ids=ids,
            limit=args.limit, log=print, prompt_suffix=args.prompt_suffix)
    print(f"tried {n}")


if __name__ == "__main__":
    main()
