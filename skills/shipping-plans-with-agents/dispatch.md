# Dispatch from Codex, Antigravity, or another shell-capable host

Use the CLI path below when the lead session lacks the installed Shipyard
Claude Code agents. The lead model is the one the user chose in the host.
Each invocation starts a new worker on the role's provider and pinned model.
Keep the stage order, cast, worktree checks, and review and test gates in
`SKILL.md` and `boatyard.md`.

## Run a worker

Use the absolute path to `dispatch.py` in this skill's directory:

```sh
python3 /path/to/shipyard/skills/shipping-plans-with-agents/dispatch.py ROLE /absolute/checkout /absolute/brief.md
```

`ROLE` is the agent name in the cast. Add `--tier ROUTINE` or `--tier HARD`
for `guest-implementer`, and `--task-review` for `sol`'s task-review job,
which keeps it on gpt-6.2-sol even under `ANTIGRAVITY_ENABLED`. The checkout argument is the working checkout for
planning, branch review, and polish lists, and the task worktree for
implementation and task review. The lead needs permission to run the CLI and
its provider subprocesses, reach their services, and manage the worktrees
and git metadata. Use the host's normal approval flow if those operations
require approval.

Write each brief to a separate temporary file with a file tool. Give the
worker absolute paths, the stage or job, the constraints and the definition
of done. For `astra`, `sol`, and `grok`, use the inner prompt and job
instructions in the corresponding `agents/*.md` from the same Shipyard
checkout. The launcher supplies the commands and, for Claude workers, the
role instructions. The implementation brief must name the tests to run and
say that the caller commits. Claude, Grok, and Neon in the Sol seat have
no shell on read-only jobs. Include the exact diff, git history excerpts, or
test output they need. In particular, when `ANTIGRAVITY_ENABLED` is set,
supply the changed-test diff to `sol` in its brief and point the worker at
that diff.

Launch independent calls together using the host's concurrent tools or
separate background jobs with individual logs and exit codes. Wait for each
process and collect its result before advancing its gate. Remove the
temporary briefs and logs after collecting the results. Every review and
delta is a new invocation with the inputs required by the stage. Check the
expected output format before treating a review as complete.

## Collect the result

- The launcher prints the model and answer on stdout. Nonzero exits leave
  all gates pending. A `GROK UNAVAILABLE:` error follows the existing
  opt-in warning path. A failed `sol --task-review` run sends that review to
  `opus-reviewer` with a one-line warning. A missing read-only gate or malformed review stops
  the gate. For Mythos, only an explicit model-unavailable error follows
  the opt-in warning path.
- The dispatcher tries Terra for ROUTINE work if Neon fails while its
  worktree is still clean and at the original HEAD. For HARD work in the
  same situation, `NEON UNAVAILABLE:` tells the lead to launch
  `sonnet-implementer` in that worktree. A failed run with changes is left
  for inspection. Never retry by discarding edits or broadening permissions.
- The lead checks the worktree's diff, status, and required checks before
  committing. All portable implementers leave edits unstaged. For the
  Sonnet fallback the lead runs the required checks because the worker has
  only file tools. Use the worktree path for tests and git commands. Confirm
  the main checkout has no unexpected changes, especially after Neon, before
  committing. Require successful checks and a nonempty diff, except when a
  polish pass explicitly declined every item. Report the branch and commit
  SHA, then send the exact commit for task review.

For environmental errors, use the provider probes in
[`commands/doctor.md`](../../commands/doctor.md). That command exercises the
original Claude plugin wrappers. To check the portable path too, use
`dispatch.py` in a disposable git repo with a one-line brief and the roles
needed for the run. Check the CLI's exit, returned model and answer. For
read-only roles, ask the worker to attempt a sentinel write and verify that
the sentinel is absent. For implementation use a disposable linked worktree.
