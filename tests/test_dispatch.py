"""Exercise portable dispatch with Git worktrees and fake provider CLIs."""

import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

DISPATCH = Path(__file__).resolve().parents[1] / "skills/shipping-plans-with-agents/dispatch.py"
FAKE_CLI = """\
import json, os, sys
from pathlib import Path

role = Path(sys.argv[0]).name
args = sys.argv[1:]
if args == ["models"]:
    print("gemini-4-neon-xhigh\\ngemini-4-hydrogen-high" if role == "agy" else "grok-4.7")
    sys.exit(0)
with open(os.environ["SHIPYARD_TEST_CALLS"], "a") as log:
    json.dump([role, str(Path.cwd()), args, sys.stdin.read()], log)
    log.write("\\n")
if role == "agy" and os.environ.get("SHIPYARD_TEST_NEON"):
    if os.environ["SHIPYARD_TEST_NEON"] == "dirty":
        Path("partial").touch()
    print("jetski: no output produced")
    sys.exit(0)
if role == "grok" and os.environ.get("SHIPYARD_TEST_GROK"):
    event = {"event_type": "ProfileApplied", "profile": "read-only",
             "enforced": True, "workspace": str(Path.cwd())}
    with open(os.environ["SHIPYARD_TEST_EVENTS"], "a") as log:
        log.write(json.dumps(event) + "\\n")
print("blockers:")
"""


class DispatchTest(unittest.TestCase):
    def enter_context(self, manager):
        value = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        return value

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.repo = self.root / "project"
        self.repo.mkdir()
        self.worktree = self.root / "task with spaces"
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-q", "--allow-empty", "-m", "Base")
        self.git("worktree", "add", "-qb", "task", str(self.worktree))
        self.brief = self.root / "brief"
        self.brief.write_text('Input "$(touch marker)" stays literal.\n')
        self.log = self.root / "calls"
        self.events = self.root / "events"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("agy", "claude", "codex", "grok"):
            executable = self.bin / name
            executable.write_text(f"#!{sys.executable}\n{FAKE_CLI}")
            executable.chmod(0o700)
        self.enter_context(patch.dict(os.environ, {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "SHIPYARD_TEST_CALLS": str(self.log),
            "SHIPYARD_TEST_EVENTS": str(self.events),
        }))
        self.main = runpy.run_path(str(DISPATCH))["main"]
        self.enter_context(patch.dict(self.main.__globals__, GROK_EVENTS=self.events))
        self.worker_error = self.main.__globals__["WorkerError"]

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True)

    def dispatch(self, role, cwd, *args):
        with patch.object(sys, "argv", [str(DISPATCH), role, str(cwd), str(self.brief), *args]):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.main()

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_read_only_routes_and_grok_gate(self):
        self.dispatch("astra", self.repo)
        self.dispatch("fable", self.repo)
        self.dispatch("sol", self.repo)
        with patch.dict(os.environ, SHIPYARD_TEST_GROK="1"):
            self.dispatch("grok", self.repo)
        with self.assertRaisesRegex(self.worker_error, "Missing or unenforced Grok read-only"):
            self.dispatch("grok", self.repo)
        astra, fable, neon, grok, _ = self.calls()
        self.assertIn("read-only", astra[2])
        self.assertIn("gpt-6.2-astra", astra[2])
        self.assertEqual(astra[3], self.brief.read_text())
        self.assertIn("Read,Glob,Grep", fable[2])
        self.assertIn("fable", fable[2])
        self.assertIn("## Job 1", fable[2][fable[2].index("--append-system-prompt") + 1])
        self.assertEqual(fable[3], self.brief.read_text())
        self.assertIn("command(*)", json.loads(neon[2][neon[2].index("--settings") + 1])["permissions"]["deny"])
        self.assertEqual(neon[2][-1], self.brief.read_text())
        self.assertIn("MCPTool", grok[2])

    def test_sol_task_review_stays_on_sol(self):
        self.dispatch("sol", self.worktree, "--task-review")
        (call,) = self.calls()
        self.assertEqual(call[0], "codex")
        self.assertIn("gpt-6.2-sol", call[2])
        self.assertIn("read-only", call[2])
        self.assertEqual(call[2][call[2].index("--cd") + 1], str(self.worktree))

    def test_polish_listers_run_neon_then_fall_back_to_sol(self):
        self.dispatch("simplifier", self.repo)
        with patch.dict(os.environ, SHIPYARD_TEST_NEON="unavailable"):
            self.dispatch("simplifier", self.repo)
        neon, failed, sol = self.calls()
        self.assertEqual([neon[0], failed[0], sol[0]], ["agy", "agy", "codex"])
        self.assertIn("write_file(*)", json.loads(neon[2][neon[2].index("--settings") + 1])["permissions"]["deny"])
        self.assertIn("gpt-6.2-sol", sol[2])
        self.assertIn("read-only", sol[2])

    def test_implementation_and_fallback_use_task_worktree(self):
        with patch.dict(os.environ, SHIPYARD_TEST_NEON="unavailable"):
            self.dispatch("guest-implementer", self.worktree, "--tier", "ROUTINE")
            with self.assertRaisesRegex(self.worker_error, "NEON UNAVAILABLE"):
                self.dispatch("guest-implementer", self.worktree, "--tier", "HARD")
        self.dispatch("sonnet-implementer", self.worktree)
        neon, terra, _, sonnet = self.calls()
        self.assertTrue(all(call[1] == str(self.worktree) for call in self.calls()))
        self.assertNotIn("--dangerously-skip-permissions", neon[2])
        self.assertIn("gemini-4-hydrogen-high", neon[2])
        self.assertIn("workspace-write", terra[2])
        self.assertIn("gpt-6.1-terra", terra[2])
        self.assertIn("Read,Glob,Grep,Edit,Write", sonnet[2])

    def test_failed_neon_with_partial_edits_never_falls_back(self):
        with patch.dict(os.environ, SHIPYARD_TEST_NEON="dirty"):
            with self.assertRaisesRegex(self.worker_error, "after changing the worktree"):
                self.dispatch("guest-implementer", self.worktree, "--tier", "ROUTINE")
        self.assertEqual([call[0] for call in self.calls()], ["agy"])
        self.assertTrue((self.worktree / "partial").exists())

    def test_implementation_refuses_main_checkout(self):
        with self.assertRaisesRegex(self.worker_error, "require a linked task worktree"):
            self.dispatch("codex", self.repo)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
