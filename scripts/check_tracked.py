#!/usr/bin/env python3
"""Refuse staged files, tracked files or unpushed commits that match a denylist.

The denylist is a file named by the environment variable
MEDCODE_EVAL_DENYLIST: one case-insensitive regular expression per line.
Blank lines are skipped; a pattern is referred to as P<line number>.

Modes
  (default)    staged files: every path added, copied, modified, renamed or
               retyped in the index relative to HEAD
  --all        every tracked file (every entry in the index)
  --unpushed   author, committer and message of every commit on a local
               branch that is not on origin/main (all commits when
               origin/main does not exist)

File content is always read from the index (the staged blob), never from
the working copy. File names are scanned too.

Output never contains a pattern or matched text. A path that itself matches
a pattern is shown only as its index entry number and blob id.

Exit status
  0  no hits; prints one summary line
  1  at least one hit
  2  denylist variable unset, file missing, empty or invalid; git error
"""

import os
import re
import subprocess
import sys

ENV_VAR = "MEDCODE_EVAL_DENYLIST"


class SetupError(Exception):
    pass


def load_patterns():
    name = os.environ.get(ENV_VAR)
    if not name:
        raise SetupError(f"{ENV_VAR} is not set")
    try:
        with open(name, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise SetupError(f"cannot read denylist named by {ENV_VAR}: {exc.strerror}")
    patterns = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            patterns.append((number, re.compile(line, re.IGNORECASE)))
        except re.error:
            raise SetupError(f"denylist pattern P{number} is not a valid regex")
    if not patterns:
        raise SetupError(f"denylist named by {ENV_VAR} has no patterns")
    return patterns


def git(*args):
    # input=b"": git gets an empty stdin, never the caller's (hash-object
    # --stdin below would otherwise wait on it for ever).
    proc = subprocess.run(["git", *args], capture_output=True, input=b"")
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", "replace").strip()
        raise SetupError(f"git {args[0]} failed: {msg}")
    return proc.stdout


def git_ok(*args):
    return subprocess.run(["git", *args], capture_output=True,
                          stdin=subprocess.DEVNULL).returncode == 0


def matching(patterns, text):
    return [number for number, rx in patterns if rx.search(text)]


def index_entries():
    """Return [(path, mode, blob sha)] for stage-0 index entries."""
    entries = []
    for record in git("ls-files", "-s", "-z").split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, sha, stage = meta.decode().split()
        if stage == "0":
            entries.append((path.decode("utf-8", "surrogateescape"), mode, sha))
    return entries


def staged_paths():
    args = ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT"]
    if not git_ok("rev-parse", "--verify", "--quiet", "HEAD"):
        # No commits yet: compare the index with the empty tree.
        empty_tree = git("hash-object", "-t", "tree", "--stdin").decode().strip()
        args.append(empty_tree)
    out = git(*args)
    return {p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p}


def scan_files(patterns, entries):
    hits = []
    for position, (path, mode, sha) in enumerate(entries, start=1):
        name_hits = matching(patterns, path)
        if name_hits:
            label = f"index entry {position} (blob {sha[:12]})"
            for number in name_hits:
                hits.append(f"{label}: file name P{number}")
        else:
            label = path
        if mode == "160000":  # submodule: no blob to read
            continue
        text = git("cat-file", "blob", sha).decode("utf-8", "replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for number in matching(patterns, line):
                hits.append(f"{label}:{line_no} P{number}")
    return hits


def unpushed_commits():
    if not git_ok("rev-parse", "--verify", "--quiet", "HEAD"):
        return []
    args = ["rev-list", "--branches"]
    if git_ok("rev-parse", "--verify", "--quiet", "refs/remotes/origin/main"):
        args += ["--not", "refs/remotes/origin/main"]
    return git(*args).decode().split()


def scan_commits(patterns, shas):
    hits = []
    for sha in shas:
        raw = git("log", "-1", "--format=%an <%ae>%x00%cn <%ce>%x00%B", sha)
        author, committer, message = raw.decode("utf-8", "replace").split("\0", 2)
        for field, text in (("author", author), ("committer", committer)):
            for number in matching(patterns, text):
                hits.append(f"{sha[:12]} {field} P{number}")
        for line_no, line in enumerate(message.splitlines(), start=1):
            for number in matching(patterns, line):
                hits.append(f"{sha[:12]} message:{line_no} P{number}")
    return hits


def main(argv):
    modes = {"--all": "all", "--unpushed": "unpushed"}
    if len(argv) > 1 or (argv and argv[0] not in modes):
        print("usage: check_tracked.py [--all | --unpushed]", file=sys.stderr)
        return 2
    mode = modes[argv[0]] if argv else "staged"
    try:
        patterns = load_patterns()
        if not git_ok("rev-parse", "--git-dir"):
            raise SetupError("not inside a git repository")
        if mode == "unpushed":
            items = unpushed_commits()
            hits = scan_commits(patterns, items)
        else:
            items = index_entries()
            if mode == "staged":
                wanted = staged_paths()
                items = [e for e in items if e[0] in wanted]
            hits = scan_files(patterns, items)
    except SetupError as exc:
        print(f"check_tracked: ERROR: {exc}", file=sys.stderr)
        return 2
    for hit in hits:
        print(f"HIT {hit}")
    print(f"check_tracked: mode={mode}, items={len(items)}, hits={len(hits)}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
