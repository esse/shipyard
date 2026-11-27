#!/usr/bin/env python3
"""Launch a fresh Shipyard worker from any shell-capable orchestrator."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[2] / "agents"
CLAUDE_ROLES = (
    "fable", "opus", "opus-reviewer",
    "sonnet-reviewer", "sonnet-implementer", "mythos",
)
CODEX_ROLES = {
    "astra": ("gpt-6.2-astra", "medium"),
    "sol": ("gpt-6.2-sol", "high"),
    "codex": ("gpt-6-luna", "max"),
    "terra": ("gpt-6.1-terra", "high"),
}
NEON = "gemini-4-neon-xhigh"
GROK_EVENTS = Path.home() / ".grok/sessions/sandbox-events.jsonl"


class WorkerError(Exception):
    pass


class SandboxError(WorkerError):
    pass


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def worktree_head(cwd):
    return git(cwd, "symbolic-ref", "HEAD"), git(cwd, "rev-parse", "HEAD")


def run(command, cwd, prompt=None, *, inspect_stderr=None):
    try:
        result = subprocess.run(
            command, cwd=cwd, input=prompt if prompt is not None else "",
            text=True, capture_output=True, check=False,
        )
    except OSError as error:
        raise WorkerError(str(error)) from error
    if inspect_stderr:
        inspect_stderr(result)
    output = result.stdout.strip()
    if result.returncode or not output or output.startswith("jetski: no output produced"):
        details = "\n".join(part for part in (result.stderr.strip(), output) if part)
        raise WorkerError(f"{command[0]} exited {result.returncode}: {details or 'no answer'}")
    return output


def codex(role, cwd, brief, write):
    model, effort = CODEX_ROLES[role]
    command = [
        "codex", "exec", "--ephemeral", "--model", model, "-c",
        f'model_reasoning_effort="{effort}"', "-c", "mcp_servers={}",
        "-c", 'approval_policy="never"', "--skip-git-repo-check", "--cd", str(cwd),
        "--sandbox", "workspace-write" if write else "read-only",
    ]
    for feature in (
        "plugins", "apps", "remote_plugin", "plugin_sharing", "browser_use",
        "browser_use_external", "computer_use", "image_generation",
        "in_app_browser", "skill_search", "skill_mcp_dependency_install",
    ):
        command.extend(["--disable", feature])
    if write:
        command.extend(["-c", "sandbox_workspace_write.network_access=true"])
    return f"{model} ({effort}) via Codex CLI", run([*command, "-"], cwd, brief)


def neon(cwd, brief, write):
    require_model("agy", NEON, cwd)
    permissions = {"deny": ["mcp(*)", "unsandboxed(*)"]}
    command = ["agy", "--model", NEON, "--sandbox", "--disable-slash-commands"]
    if write:
        permissions["allow"] = ["read_file(*)", f"write_file({cwd})", "command(*)"]
    else:
        permissions["deny"] += ["write_file(*)", "command(*)", "execute_url(*)"]
        command.append("--dangerously-skip-permissions")
    command.extend(["--settings", json.dumps({"permissions": permissions}), "-p", brief])
    return f"{NEON} via Antigravity CLI", run(command, cwd)


def require_model(cli, model, cwd):
    models = run([cli, "models"], cwd)
    if not re.search(rf"(?<![\w.-]){re.escape(model)}(?![\w.-])", models):
        raise WorkerError(f"{cli} models did not list {model}")


def claude(role, cwd, brief, write):
    _, header, instructions = (AGENTS / f"{role}.md").read_text().split("---", 2)
    model = next(line.removeprefix("model: ").strip() for line in header.splitlines()
                 if line.startswith("model: "))
    tool_list = "Read,Glob,Grep,Edit,Write" if write else "Read,Glob,Grep"
    if write:
        instructions += (
            "\nUse only file tools. The caller runs tests, records git status, and "
            "commits. Leave your changes unstaged and summarize the checks to run."
        )
    else:
        instructions += "\nUse read tools and the supplied diff or command output. Shell is unavailable."
    command = [
        "claude", "--print", "--model", model, "--restricted",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--disable-slash-commands", "--no-session-persistence", "--no-chrome",
        "--append-system-prompt", instructions,
        "--permission-prompts", "none", "--permission-mode",
        "acceptEdits" if write else "dontAsk", "--tools", tool_list,
    ]
    return f"{model} via Claude Code", run(command, cwd, brief)


def grok(cwd, brief_path):
    require_model("grok", "grok-4.7", cwd)
    # Only accept sandbox evidence appended during this invocation for this checkout.
    offset = GROK_EVENTS.stat().st_size if GROK_EVENTS.exists() else 0

    def verify_sandbox(result):
        if "sandbox could not be applied" in result.stderr.lower():
            raise SandboxError(result.stderr.strip())
        try:
            with GROK_EVENTS.open() as log:
                log.seek(offset)
                events = [json.loads(line) for line in log]
        except (OSError, ValueError) as error:
            if result.returncode == 0:
                raise SandboxError(f"Cannot verify Grok sandbox: {error}") from error
            events = []
        applied = [event for event in events if event.get("event_type") == "ProfileApplied"
                   and event.get("workspace") == str(cwd)]
        if any(event.get("enforced") is not True or event.get("profile") != "read-only"
               for event in applied) or (result.returncode == 0 and not applied):
            raise SandboxError("Missing or unenforced Grok read-only sandbox for this checkout")

    output = run([
        "grok", "--prompt-file", str(brief_path), "--cwd", str(cwd), "--model", "grok-4.7",
        "--effort", "xhigh", "--no-plan", "--no-subagents", "--sandbox", "read-only",
        "--tools", "read_file,list_dir,grep",
        "--deny", "Edit", "--deny", "Write", "--deny", "Bash", "--deny", "MCPTool",
    ], cwd, inspect_stderr=verify_sandbox)
    findings = output.splitlines()
    for index, line in enumerate(findings):
        if line == "blockers:":
            return "grok-4.7 (xhigh) via Grok CLI, read-only", "\n".join(findings[index:])
    raise SandboxError("Grok did not return a blockers list")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=[*CLAUDE_ROLES, "astra", "sol", "simplifier",
                                        "codex", "guest-implementer", "grok"])
    parser.add_argument("checkout", type=Path)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--tier", choices=["ROUTINE", "HARD"],
                        help="required for guest-implementer")
    parser.add_argument("--task-review", action="store_true",
                        help="sol only: stage-4 task review, always on Sol")
    args = parser.parse_args()
    role = args.role
    if args.task_review and role != "sol":
        parser.error("--task-review applies only to sol")
    if (role == "guest-implementer") != bool(args.tier):
        parser.error("--tier is required for guest-implementer and applies only to that role")
    cwd = args.checkout.resolve(strict=True)
    if Path(git(cwd, "rev-parse", "--show-toplevel")).resolve() != cwd:
        raise WorkerError("Checkout must be the root of the target git worktree")
    brief_path = args.brief.resolve(strict=True)
    brief = brief_path.read_text()
    if not brief.strip():
        raise WorkerError("Brief is empty")
    write = role in {"codex", "guest-implementer", "sonnet-implementer"}
    if write:
        if git(cwd, "rev-parse", "--git-dir") == git(cwd, "rev-parse", "--git-common-dir"):
            raise WorkerError("Implementers require a linked task worktree")
        if git(cwd, "status", "--porcelain"):
            raise WorkerError("Implementers require a clean task worktree")
        head = worktree_head(cwd)
        brief += "\n\nStay inside this task worktree. Leave edits unstaged. The caller commits."

    if role in CLAUDE_ROLES:
        header, output = claude(role, cwd, brief, write)
    elif role == "grok":
        try:
            header, output = grok(cwd, brief_path)
        except SandboxError:
            raise
        except WorkerError as error:
            raise WorkerError(f"GROK UNAVAILABLE: {error}") from error
    elif role == "guest-implementer":
        try:
            header, output = neon(cwd, brief, write=True)
        except WorkerError as error:
            if git(cwd, "status", "--porcelain") or worktree_head(cwd) != head:
                raise WorkerError(f"Neon failed after changing the worktree: {error}") from error
            if args.tier == "HARD":
                raise WorkerError(f"NEON UNAVAILABLE: {error}") from error
            print(f"Neon unavailable, trying Terra: {error}", file=sys.stderr)
            header, output = codex("terra", cwd, brief, write=True)
    elif role == "simplifier" or (role == "sol" and not args.task_review):
        try:
            header, output = neon(cwd, brief, write=False)
        except WorkerError as error:
            print(f"Neon unavailable, trying Sol: {error}", file=sys.stderr)
            header, output = codex("sol", cwd, brief, write=False)
    else:
        header, output = codex(role, cwd, brief, write)

    if write and (worktree_head(cwd) != head or git(cwd, "diff", "--cached", "--name-only")):
        raise WorkerError("Worker changed the branch, HEAD, or index. Inspect the worktree before proceeding.")
    print(f"{header}\n\n{output}")


if __name__ == "__main__":
    try:
        main()
    except (WorkerError, subprocess.CalledProcessError, OSError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
