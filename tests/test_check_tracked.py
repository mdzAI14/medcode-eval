"""Tests for scripts/check_tracked.py.

Every test builds a throwaway git repo in the system temp dir, uses made-up
patterns, and never touches the network.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_tracked.py"

# Made-up patterns. Line 1 is blank on purpose so pattern numbers follow file
# line numbers (P2, P3, P4).
PATTERNS = "\nzebra-?quokka\\d+\nPLATYPUS\nnarwhal_[a-z]{3}\n"


def _git_env():
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = "Test Author"
    env["GIT_AUTHOR_EMAIL"] = "author@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Test Committer"
    env["GIT_COMMITTER_EMAIL"] = "committer@example.invalid"
    env.pop("MEDCODE_EVAL_DENYLIST", None)
    return env


class CheckTrackedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.denylist = base / "denylist.txt"
        self.denylist.write_text(PATTERNS, encoding="utf-8")
        self.env = _git_env()
        self.git("init", "-q", "-b", "main")

    # helpers -------------------------------------------------------------
    def git(self, *args, env=None):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=env or self.env,
            check=True,
            capture_output=True,
            text=True,
        )

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, *args, denylist="default"):
        env = dict(self.env)
        if denylist == "default":
            env["MEDCODE_EVAL_DENYLIST"] = str(self.denylist)
        elif denylist is not None:
            env["MEDCODE_EVAL_DENYLIST"] = str(denylist)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )

    def assert_setup_error(self, result):
        # Exit 2 alone could come from Python failing to start the script.
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("check_tracked: ERROR:", result.stderr)
        self.assertNotIn("hits=0", result.stdout)

    def assert_no_leak(self, result, *secrets):
        out = result.stdout + result.stderr
        for s in secrets:
            self.assertNotIn(s.lower(), out.lower())
        for line in PATTERNS.splitlines():
            if line:
                self.assertNotIn(line, out)

    # staged mode ---------------------------------------------------------
    def test_staged_hit(self):
        self.write("notes.txt", "fine\nsee zebraquokka42 here\n")
        self.git("add", "notes.txt")
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("notes.txt:2", r.stdout)
        self.assertIn("P2", r.stdout)
        self.assert_no_leak(r, "zebraquokka42")

    def test_staged_no_hit(self):
        self.write("notes.txt", "nothing to see\n")
        self.git("add", "notes.txt")
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("mode=staged", r.stdout)
        self.assertIn("items=1", r.stdout)
        self.assertIn("hits=0", r.stdout)

    def test_case_insensitive(self):
        self.write("a.txt", "a platypus appears\n")
        self.git("add", "a.txt")
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("a.txt:1", r.stdout)
        self.assertIn("P3", r.stdout)
        self.assert_no_leak(r, "platypus")

    def test_file_name_hit(self):
        self.write("docs/narwhal_abc.md", "clean content\n")
        self.git("add", "docs/narwhal_abc.md")
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("P4", r.stdout)
        self.assertIn("file name", r.stdout)
        # The path itself matches, so it must not be printed.
        self.assert_no_leak(r, "narwhal_abc")

    def test_index_only_hit(self):
        path = self.write("staged.txt", "zebra-quokka7\n")
        self.git("add", "staged.txt")
        path.unlink()
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("staged.txt:1", r.stdout)
        self.assert_no_leak(r, "zebra-quokka7")

    def test_working_copy_only_hit_is_ignored(self):
        path = self.write("w.txt", "clean\n")
        self.git("add", "w.txt")
        path.write_text("PLATYPUS\n", encoding="utf-8")
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_unstaged_untracked_file_not_scanned(self):
        self.write("tracked.txt", "clean\n")
        self.git("add", "tracked.txt")
        self.write("untracked.txt", "PLATYPUS\n")
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_non_utf8_file_is_scanned(self):
        # Bytes that are not valid UTF-8 (as in a PDF), with a made-up
        # pattern in a readable stretch. The file is scanned, not skipped.
        data = (
            b"%PDF-1.7\n\xff\xfe\x80\x81\xc3\x28 binary\x00\x01\n"
            b"readable PLATYPUS text\n\xe2\x82\n"
        )
        (self.repo / "doc.pdf").write_bytes(data)
        self.git("add", "doc.pdf")
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("doc.pdf:3 P3", r.stdout)
        self.assert_no_leak(r, "platypus")

    # all mode ------------------------------------------------------------
    def test_all_mode_scans_committed_files(self):
        self.write("old.txt", "narwhal_xyz\n")
        self.git("add", "old.txt")
        self.git("commit", "-q", "-m", "c1")
        self.write("new.txt", "clean\n")
        self.git("add", "new.txt")
        staged = self.run_check()
        self.assertEqual(staged.returncode, 0, staged.stdout + staged.stderr)
        r = self.run_check("--all")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("old.txt:1", r.stdout)
        self.assert_no_leak(r, "narwhal_xyz")

    def test_all_mode_clean(self):
        self.write("a.txt", "clean\n")
        self.write("b.txt", "also clean\n")
        self.git("add", ".")
        r = self.run_check("--all")
        self.assertEqual(r.returncode, 0)
        self.assertIn("mode=all", r.stdout)
        self.assertIn("items=2", r.stdout)
        self.assertIn("hits=0", r.stdout)

    # unpushed mode -------------------------------------------------------
    def test_commit_metadata_hit(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        env = dict(self.env)
        env["GIT_AUTHOR_NAME"] = "Platypus Person"
        self.git("commit", "-q", "-m", "clean message", env=env)
        sha = self.git("rev-parse", "HEAD").stdout.strip()
        r = self.run_check("--unpushed")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(sha[:12], r.stdout)
        self.assertIn("author", r.stdout)
        self.assertIn("P3", r.stdout)
        self.assert_no_leak(r, "platypus")

    def test_commit_message_and_committer_hit(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        env = dict(self.env)
        env["GIT_COMMITTER_EMAIL"] = "narwhal_bot@example.invalid"
        self.git("commit", "-q", "-m", "subject\n\nbody zebraquokka1", env=env)
        r = self.run_check("--unpushed")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("committer", r.stdout)
        self.assertIn("message", r.stdout)
        self.assert_no_leak(r, "narwhal_bot", "zebraquokka1")

    def test_unpushed_clean(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "clean")
        r = self.run_check("--unpushed")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("mode=unpushed", r.stdout)
        self.assertIn("items=1", r.stdout)

    def test_unpushed_skips_commits_on_origin_main(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "PLATYPUS already pushed")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.write("b.txt", "clean\n")
        self.git("add", "b.txt")
        self.git("commit", "-q", "-m", "clean second")
        r = self.run_check("--unpushed")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("items=1", r.stdout)

    def test_unpushed_no_commits(self):
        r = self.run_check("--unpushed")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("items=0", r.stdout)

    # denylist problems ---------------------------------------------------
    def test_unset_variable(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        r = self.run_check(denylist=None)
        self.assert_setup_error(r)

    def test_missing_list(self):
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        r = self.run_check(denylist=Path(self._tmp.name) / "nope.txt")
        self.assert_setup_error(r)

    def test_empty_list(self):
        empty = Path(self._tmp.name) / "empty.txt"
        empty.write_text("", encoding="utf-8")
        self.write("a.txt", "clean\n")
        self.git("add", "a.txt")
        r = self.run_check(denylist=empty)
        self.assert_setup_error(r)

    def test_blank_only_list(self):
        blank = Path(self._tmp.name) / "blank.txt"
        blank.write_text("\n  \n\n", encoding="utf-8")
        r = self.run_check(denylist=blank)
        self.assert_setup_error(r)

    def test_invalid_regex(self):
        bad = Path(self._tmp.name) / "bad.txt"
        bad.write_text("ok\n(unclosed\n", encoding="utf-8")
        r = self.run_check(denylist=bad)
        self.assert_setup_error(r)
        self.assertIn("P2", r.stdout + r.stderr)
        self.assertNotIn("(unclosed", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
