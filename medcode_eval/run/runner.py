"""Put Part A probes in front of a model and record its replies.

Only a probe's prompt fields reach the model: code and options
(code_to_description), description (description_to_code), code (status).
Each is filled into the prompt file for its type under prompts/. The
setting prompt_suffix (empty by default) is added to the rendered prompt
on its own last line; the prompt files are not changed. The backend
receives one user message whose text is the rendered prompt, and nothing
else.

Backends (standard library only) take a list of messages, each a dict with
role ("user" or "assistant") and content, so a second turn can follow the
first (Part B, medcode_eval.run.part_b):
  fake    a Python callable; for tests. By default it gets the last
          message's text (the Part A form); with messages=True it gets the
          whole list.
  ollama  the local Ollama server, non-streaming. Only a localhost address
          is accepted. Endpoint /api/generate (Part A; takes exactly one
          user message, sent as "prompt", so the request is the same as
          before messages existed) or /api/chat (Part B; "messages"; both
          endpoints are in the installed server 0.6.8). Settings:
          temperature 0, seed SEED, num_predict NUM_PREDICT, num_ctx
          NUM_CTX, per-call timeout TIMEOUT seconds. No system prompt and no
          API reasoning switch is sent; reasoning can only be changed
          through text in prompt_suffix (e.g. /no_think for a model whose
          template reads it).
  remote  the Anthropic Messages API (RemoteBackend; standard library).
          Needs --model, --key-env (the NAME of the key variable in the
          repo's .env), --effort and --max-tokens, and the spending stop
          (medcode_eval.run.spend): --price-in and --price-out (USD per
          million tokens), --max-usd and --ledger (a JSONL file under
          runs/spend/, which several runs may share). run.json records them
          (settings and "spend"); raw.jsonl rows also hold reply_id,
          reply_model, stop_reason, usage, block_types, http_status,
          attempts and request_chars. A reply whose stop_reason is not
          "end_turn" is still parsed. Exit status 2: the run was aborted
          (HTTP 400, 401, 403, 404, or no key); 3: the spending stop refused
          a request (the same command resumes the run).

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
    venv/bin/python -m medcode_eval.run.runner --backend remote --model M --key-env NAME \
        --effort medium --max-tokens N --price-in P --price-out Q --max-usd C \
        --ledger runs/spend/L.jsonl [--part b --condition C] --run-id R ...
    venv/bin/python -m medcode_eval.run.runner --run-id lite-qwen3-4b --rederive
    venv/bin/python -m medcode_eval.run.runner --part b --condition with_checker \
        --run-id b-qwen3-4b [--model qwen3:4b] [--limit N] [--ids a,b] [--prompt-suffix S]
    venv/bin/python -m medcode_eval.run.runner --part b --run-id b-qwen3-4b --rederive
    venv/bin/python -m medcode_eval.run.runner --dry-run --run-id p61 [--prompt-suffix S]

--rederive rewrites responses.jsonl (Part A) or answers.jsonl (Part B) from
the run's raw.jsonl with the current answer reader; no backend is built and
no model is called; raw.jsonl and run.json are not touched.

--dry-run renders every first-turn prompt of Part A (lite, full, changes)
and Part B (plain, with_checker) into runs/dryrun/<run-id>/ with counts,
estimated tokens and a cost table (medcode_eval.run.dryrun). No backend is
built and no model is called.
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
ROLES = ("user", "assistant")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def user_message(text):
    return {"role": "user", "content": text}


def check_messages(messages):
    """Raise ValueError unless messages is a non-empty list of role/content
    dicts with known roles and string content."""
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    for m in messages:
        if (not isinstance(m, dict) or set(m) != {"role", "content"}
                or m["role"] not in ROLES or not isinstance(m["content"], str)):
            raise ValueError(f"bad message {m!r}")
    return messages


def drop_think(text):
    """Text without <think>...</think> blocks; an unclosed <think> drops
    the rest of the text."""
    text = _THINK.sub("", text)
    if "<think>" in text:
        text = text[:text.index("<think>")]
    return text
_MARKS = "\"'`*"
_LABEL = re.compile(r"^\**\s*(?:final\s+)?answer\s*\**\s*:\s*\**\s*", re.I)


def extract_answer(text):
    """The answer line of a reply.

    Drops reasoning wrapped in <think>...</think> (an unclosed <think> drops
    the rest of the reply), takes the last non-empty line, strips quotes,
    backticks and asterisks at either end and one trailing full stop, then
    drops a leading "Answer:" or "Final answer:" label (any case, asterisks
    around it allowed). When a label was dropped, the end-strip (quotes,
    backticks, asterisks, one trailing full stop) runs again on what is left.
    """
    text = drop_think(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    s = _end_strip(lines[-1])
    unlabelled = _LABEL.sub("", s)
    return s if unlabelled == s else _end_strip(unlabelled)


def _end_strip(s):
    """Strip quotes, backticks and asterisks at either end and one trailing
    full stop (then the marks again)."""
    s = s.strip().strip(_MARKS).strip()
    if s.endswith("."):
        s = s[:-1]
    return s.strip().strip(_MARKS).strip()


class FakeBackend:
    """Replies with fn(last message text), or fn(messages) when messages is
    true. For tests; no model is called."""

    name = "fake"

    def __init__(self, fn, model="fake", messages=False):
        self.fn = fn
        self.model = model
        self.messages = messages

    def describe(self):
        return {"backend": self.name, "model": self.model, "model_digest": None,
                "server_version": None, "settings": {}}

    def generate(self, messages):
        check_messages(messages)
        return {"raw": self.fn(list(messages) if self.messages else messages[-1]["content"])}


ENDPOINTS = ("/api/generate", "/api/chat")


class OllamaBackend:
    """The local Ollama server, /api/generate or /api/chat, stream off."""

    name = "ollama"

    def __init__(self, model, host=DEFAULT_HOST, timeout=TIMEOUT, endpoint="/api/generate"):
        u = urllib.parse.urlparse(host)
        if u.scheme != "http" or u.hostname not in _LOCAL:
            raise ValueError(f"only a local Ollama server is allowed, not {host!r}")
        if endpoint not in ENDPOINTS:
            raise ValueError(f"endpoint must be one of {ENDPOINTS}, not {endpoint!r}")
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.endpoint = endpoint
        self.options = {"temperature": 0, "seed": SEED,
                        "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX}

    def request_body(self, messages):
        """The request for a list of messages (a string is one user message).
        /api/generate takes exactly one user message, sent as "prompt"."""
        if isinstance(messages, str):
            messages = [user_message(messages)]
        check_messages(messages)
        if self.endpoint == "/api/generate":
            if len(messages) != 1 or messages[0]["role"] != "user":
                raise ValueError("/api/generate takes exactly one user message")
            return {"model": self.model, "prompt": messages[0]["content"], "stream": False,
                    "options": dict(self.options)}
        return {"model": self.model, "messages": [dict(m) for m in messages],
                "stream": False, "options": dict(self.options)}

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
                "settings": {"endpoint": self.endpoint, "stream": False,
                             "options": dict(self.options),
                             "timeout_seconds": self.timeout,
                             "system_prompt": None, "reasoning_switch": None}}

    def generate(self, messages):
        out = self._call(self.endpoint, self.request_body(messages), timeout=self.timeout)
        if self.endpoint == "/api/chat":
            raw = (out.get("message") or {}).get("content", "")
        else:
            raw = out.get("response", "")
        return {"raw": raw, "done_reason": out.get("done_reason"),
                "eval_count": out.get("eval_count")}


API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
REMOTE_TIMEOUT = 300           # seconds per request
RETRY_STATUSES = (429, 500, 502, 503, 504, 529)
RETRY_WAITS = (5, 15, 45)      # seconds, when the reply has no retry-after header
ABORT_STATUSES = (400, 401, 403, 404)


class RemoteAbort(Exception):
    """A reply that ends the whole run (HTTP 400, 401, 403, 404, or no key).
    Not an OSError or ValueError, so the run loops do not record it as an
    item error."""


class RemoteError(ValueError):
    """A failed request recorded as that item's error; the run goes on."""


def read_env_value(path, name):
    """The value of NAME=value in a .env file (optional export and quotes),
    or None. The value is never part of an error message."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    value = None
    for line in lines:
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if m and m.group(1) == name:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            value = v
    return value or None


def urllib_transport(url, headers, body, timeout):
    """POST body to url; (status, lower-cased headers, body bytes). An HTTP
    error status is returned, not raised; a network failure raises OSError."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers or {}).items()}
        try:
            data = exc.read()
        except OSError:
            data = b""
        return exc.code, hdrs, data


def _api_error(body):
    """(error type, message) from an API error body, or placeholders."""
    try:
        err = json.loads(body.decode("utf-8")).get("error") or {}
        return str(err.get("type")), str(err.get("message"))
    except (ValueError, AttributeError, UnicodeDecodeError):
        return "unknown", "reply body is not an API error object"


class RemoteBackend:
    """The Anthropic Messages API, standard library only, non-streaming.

    Request: POST API_URL with headers x-api-key, anthropic-version
    API_VERSION and content-type application/json; body model, max_tokens,
    output_config.effort and the messages as given (string content). No
    temperature, system prompt, thinking field, tools or streaming.

    Reply: raw is the concatenation of the text blocks; other block types
    are counted (block_types) and not stored. Kept as well: reply_id,
    reply_model, stop_reason, the whole usage object, http_status, attempts.

    key_env is the NAME of a variable in env_file (the repo's .env). Its
    value is read at the first request, held in memory only, and never
    appears in repr, describe(), a log line or an error. transport and
    sleep are injectable for tests.

    Errors: RETRY_STATUSES are retried up to 3 times (the retry-after
    header when present, else RETRY_WAITS); ABORT_STATUSES raise
    RemoteAbort; anything else, and retries used up, raise RemoteError.
    """

    name = "remote"

    def __init__(self, model, key_env, effort, max_tokens, env_file=None,
                 transport=None, sleep=time.sleep, timeout=REMOTE_TIMEOUT):
        if not isinstance(key_env, str) or not _ENV_NAME.fullmatch(key_env):
            raise ValueError(f"key_env must be an environment variable name, not {key_env!r}")
        if not isinstance(effort, str) or not re.fullmatch(r"[a-z]+", effort):
            raise ValueError("effort must be a lower-case word")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
        self.model = model
        self.key_env = key_env
        self.effort = effort
        self.max_tokens = max_tokens
        self.env_file = Path(env_file) if env_file else REPO_ROOT / ".env"
        self.transport = transport or urllib_transport
        self.sleep = sleep
        self.timeout = timeout
        self.__key = None

    def __repr__(self):
        return f"RemoteBackend(model={self.model!r}, key_env={self.key_env!r})"

    __str__ = __repr__

    def describe(self):
        return {"backend": self.name, "model": self.model, "model_digest": None,
                "server_version": None,
                "settings": {"endpoint": API_URL, "api_version": API_VERSION,
                             "key_env": self.key_env, "effort": self.effort,
                             "max_tokens": self.max_tokens, "stream": False,
                             "timeout_seconds": self.timeout, "system_prompt": None,
                             "temperature": None, "retry_statuses": list(RETRY_STATUSES),
                             "retry_waits_seconds": list(RETRY_WAITS)}}

    def request_body(self, messages):
        check_messages(messages)
        return {"model": self.model, "max_tokens": self.max_tokens,
                "output_config": {"effort": self.effort},
                "messages": [dict(m) for m in messages]}

    def _headers(self):
        if self.__key is None:
            key = read_env_value(self.env_file, self.key_env)
            if not key:
                raise RemoteAbort(f"no value for {self.key_env} in {self.env_file.name}")
            self.__key = key
        return {"x-api-key": self.__key, "anthropic-version": API_VERSION,
                "content-type": "application/json"}

    def generate(self, messages):
        body = json.dumps(self.request_body(messages)).encode("utf-8")
        headers = self._headers()
        attempt = 0
        while True:
            attempt += 1
            status, hdrs, data = self.transport(API_URL, headers, body, self.timeout)
            if status == 200:
                return self._reply(data, attempt)
            etype, emsg = _api_error(data)
            if status in ABORT_STATUSES:
                raise RemoteAbort(f"HTTP {status}: {etype}: {emsg}")
            if status in RETRY_STATUSES and attempt <= len(RETRY_WAITS):
                self.sleep(_retry_after(hdrs) or RETRY_WAITS[attempt - 1])
                continue
            tail = f" after {attempt - 1} retries" if status in RETRY_STATUSES else ""
            raise RemoteError(f"HTTP {status}: {etype}: {emsg}{tail}")

    @staticmethod
    def _reply(data, attempt):
        try:
            out = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise RemoteError(f"HTTP 200 with an unreadable body ({type(exc).__name__})")
        blocks = out.get("content") or []
        types = {}
        text = []
        for b in blocks:
            t = b.get("type") if isinstance(b, dict) else None
            types[str(t)] = types.get(str(t), 0) + 1
            if t == "text" and isinstance(b.get("text"), str):
                text.append(b["text"])
        return {"raw": "".join(text), "reply_id": out.get("id"),
                "reply_model": out.get("model"), "stop_reason": out.get("stop_reason"),
                "usage": out.get("usage"), "block_types": types, "http_status": 200,
                "attempts": attempt}


def _retry_after(headers):
    v = (headers or {}).get("retry-after")
    try:
        s = float(v)
    except (TypeError, ValueError):
        return None
    return s if s >= 0 else None


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
        prompt_suffix="", ledger=None):
    """Run probes (all, or those in ids, in file order) not yet in raw.jsonl.

    limit caps the number of new probes tried in this call. prompt_suffix is
    added to every prompt on its own last line. Returns the number tried.

    ledger (medcode_eval.run.spend.Ledger) is the spending stop; a remote
    backend needs one. With a ledger, run.json gains "spend" (the prices,
    the cap and the ledger name), each raw row gains request_chars, and each
    paid reply is recorded in the ledger. When the stop refuses a request the
    run ends there: responses.jsonl is written, ledger.stopped holds the
    message, and the same call later resumes.
    """
    from medcode_eval.run import spend
    if ledger is None and getattr(backend, "name", None) == "remote":
        raise ValueError("a remote run needs a ledger (the spending stop)")
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
    if ledger is not None:
        meta["spend"] = ledger.describe(_relative(ledger.path))
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "run.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        old.pop("started", None)
        old.setdefault("prompt_suffix", "")  # run.json from before the setting
        if not same_inputs(old, meta):
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
        messages = [user_message(prompt)]
        try:
            chars = spend.before(ledger, backend, messages)
        except spend.SpendStop as exc:
            if log:
                log(str(exc))
            break
        start = time.monotonic()
        row = {"id": p["id"], "raw": None, "error": None}
        try:
            row.update(backend.generate(messages))
        except (OSError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        except RemoteAbort:
            write_responses(run_dir)
            raise
        row["seconds"] = round(time.monotonic() - start, 3)
        spend.after(ledger, p["id"], 1, row, chars)
        _append(raw_path, row)
        done.add(p["id"])
        tried += 1
        if log:
            log(f"{p['id']} {row['seconds']:.1f}s"
                + (f" error {row['error']}" if row["error"] else ""))
    write_responses(run_dir)
    return tried


def same_inputs(old, new):
    """run.json equality for a resume. The spending cap alone may differ
    (run.json keeps the cap the run started with); prices and the ledger
    may not."""
    def key(m):
        m = dict(m)
        if isinstance(m.get("spend"), dict):
            m["spend"] = {k: v for k, v in m["spend"].items() if k != "max_usd"}
        return m
    return key(old) == key(new)


def _relative(path):
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).name


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run Part A probes or Part B cases "
                                             "through a model.")
    ap.add_argument("--part", choices=("a", "b"), default="a")
    ap.add_argument("--probes")
    ap.add_argument("--condition", help="Part B: plain or with_checker")
    ap.add_argument("--data-dir", help="Part B: folder with cases/ (default data/)")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--rederive", action="store_true",
                    help="only rewrite responses.jsonl or answers.jsonl from raw.jsonl; "
                         "no model call")
    ap.add_argument("--dry-run", action="store_true",
                    help="render every first-turn prompt and the cost table; no model call")
    ap.add_argument("--backend", choices=("ollama", "remote"), default="ollama")
    ap.add_argument("--model", default="qwen3:4b")
    ap.add_argument("--key-env", help="remote: NAME of the key variable in the repo's .env")
    ap.add_argument("--effort", help="remote: output_config.effort")
    ap.add_argument("--max-tokens", type=int, help="remote: max_tokens per request")
    ap.add_argument("--price-in", type=float, help="remote: USD per million input tokens")
    ap.add_argument("--price-out", type=float, help="remote: USD per million output tokens")
    ap.add_argument("--max-usd", type=float, help="remote: spending cap over the ledger")
    ap.add_argument("--ledger", help="remote: JSONL ledger under runs/spend/")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="comma-separated probe or case ids")
    ap.add_argument("--prompt-suffix", default="",
                    help="text added to every prompt on its own last line")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
        ap.error("run id: letters, digits, '.', '_' and '-' only")
    if args.dry_run:
        from medcode_eval.run import dryrun
        out = dryrun.main_dry_run(REPO_ROOT, args.run_id, args.prompt_suffix)
        print(f"wrote {out}")
        return
    if args.part == "b":
        return _main_part_b(ap, args)
    run_dir = REPO_ROOT / RUNS_DIR / args.run_id
    if args.rederive:
        if not (run_dir / "raw.jsonl").is_file():
            ap.error(f"no raw.jsonl in {RUNS_DIR / args.run_id}")
        write_responses(run_dir)
        print(f"rewrote {RUNS_DIR / args.run_id / 'responses.jsonl'}")
        return
    if not args.probes:
        ap.error("--probes is required unless --rederive is given")
    ledger = _ledger(ap, args)
    backend = (_remote(args) if args.backend == "remote"
               else OllamaBackend(args.model, host=args.host))
    ids = args.ids.split(",") if args.ids else None
    try:
        n = run(args.probes, run_dir, backend, ids=ids, limit=args.limit, log=print,
                prompt_suffix=args.prompt_suffix, ledger=ledger)
    except RemoteAbort as exc:
        print(f"run aborted: {exc}")
        raise SystemExit(2)
    print(f"tried {n}")
    _end(ledger)


SPEND_OPTIONS = ("price_in", "price_out", "max_usd", "ledger")
REMOTE_OPTIONS = ("key_env", "effort", "max_tokens")
SPEND_DIR = Path("runs") / "spend"


def _ledger(ap, args):
    """The spending stop for a remote run; None for ollama. A remote run
    without all four spend options (and key_env, effort, max_tokens) does
    not start."""
    from medcode_eval.run import spend
    given = [o for o in SPEND_OPTIONS + REMOTE_OPTIONS if getattr(args, o) is not None]
    if args.backend != "remote":
        if given:
            ap.error("--" + given[0].replace("_", "-") + " is for --backend remote only")
        return None
    missing = [o for o in REMOTE_OPTIONS + SPEND_OPTIONS if getattr(args, o) is None]
    if missing:
        ap.error("--backend remote needs " + ", ".join("--" + o.replace("_", "-")
                                                        for o in missing))
    path = Path(args.ledger)
    path = (path if path.is_absolute() else REPO_ROOT / path).resolve()
    spend_dir = (REPO_ROOT / SPEND_DIR).resolve()
    if path.parent != spend_dir or path.suffix != ".jsonl":
        ap.error(f"--ledger must be a .jsonl file directly under {SPEND_DIR}/")
    try:
        return spend.Ledger(path, args.price_in, args.price_out, args.max_usd,
                            run_id=args.run_id)
    except ValueError as exc:
        ap.error(str(exc))


def _remote(args):
    return RemoteBackend(args.model, args.key_env, effort=args.effort,
                         max_tokens=args.max_tokens)


def _end(ledger):
    if ledger is not None:
        print(f"ledger total {ledger.total():.4f} USD of {ledger.max_usd:.2f}")
        if ledger.stopped:
            print(ledger.stopped + "; the run is resumable with the same command")
            raise SystemExit(3)


def _main_part_b(ap, args):
    from medcode_eval.run import part_b
    rel = part_b.RUNS_DIR / args.run_id
    run_dir = REPO_ROOT / rel
    if args.rederive:
        if not (run_dir / "raw.jsonl").is_file():
            ap.error(f"no raw.jsonl in {rel}")
        part_b.write_answers(run_dir)
        print(f"rewrote {rel / 'answers.jsonl'}")
        return
    if args.condition not in part_b.CONDITIONS:
        ap.error(f"--condition must be one of {', '.join(part_b.CONDITIONS)}")
    data_dir = Path(args.data_dir) if args.data_dir else REPO_ROOT / "data"
    ledger = _ledger(ap, args)
    backend = (_remote(args) if args.backend == "remote"
               else OllamaBackend(args.model, host=args.host, endpoint="/api/chat"))
    ids = args.ids.split(",") if args.ids else None
    try:
        n = part_b.run(data_dir, run_dir, backend, args.condition, ids=ids, limit=args.limit,
                       log=print, prompt_suffix=args.prompt_suffix, ledger=ledger)
    except RemoteAbort as exc:
        print(f"run aborted: {exc}")
        raise SystemExit(2)
    print(f"cases tried {n}")
    _end(ledger)


if __name__ == "__main__":
    main()
