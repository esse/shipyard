---
name: shipping-plans-with-agents
description: Use when a spec, design, or implementation plan is ready to build and the work will be split across subagents — planning, plan review, parallel implementation in worktrees, per-task review, branch review, and PR.
---

# Shipping Plans With Agents

Five stages, in order. No skipping, no reordering.

## Cast

| Name | Agent | Model | Access |
|---|---|---|---|
| Fable | main session | session model | full |
| Sol | `sol-reviewer` | gpt-5.6-sol, xhigh | read-only |
| Luna | `codex` | gpt-5.6-luna, max | write |
| Opus | `opus-reviewer` | Claude Opus | read-only |

Sol and Opus are **adversarial**: they hunt for reasons to reject, never to approve.

Fable is a role, not a model — it is whatever model this session runs on. If that is already Opus, stage 4 still dispatches the separate `opus-reviewer` subagent: same weights, but a fresh context that never saw the plan being written. Never review a task inline because "I am Opus already".

Sol and Luna shell out to the Codex CLI. If `codex` is missing from PATH or unauthenticated they report the error and stop — that blocks stages 2 and 3; don't route around it by doing the work yourself.

## Stages

**1. Plan — Fable.** Write the spec / implementation plan yourself, broken into small tasks. Mark which tasks are independent.

**2. Plan review — Sol.** `Agent(subagent_type: "sol-reviewer")` on the full plan text. Address blockers before executing. Re-review after major rework. **Never start executing a plan that hasn't passed sol-reviewer in this session.**

**3. Implement — Luna.** One `Agent(subagent_type: "codex", isolation: "worktree")` per task, all dispatched in a single message so they run in parallel. Worktrees make file overlap safe. Each agent commits its work in its own worktree.

Codex sees nothing of this conversation — every dispatch prompt must be self-contained: the task, the files it touches, the conventions it must follow, the definition of done.

**4. Task review — Opus.** As each task finishes, `Agent(subagent_type: "opus-reviewer")` on that worktree's commit plus the plan step it implements. FIX verdict → back to a `codex` agent in the *same* worktree, then re-review. APPROVE → merge that worktree branch into the working branch (you resolve conflicts).

A task is done only when approved **and** merged.

**5. Branch review — Fable + Sol.** Once every task is approved: review the whole branch diff yourself, and in parallel run `sol-reviewer` on the same diff. Fix confirmed findings via `codex`, re-reviewed per stage 4. Only then commit, push, open the PR.

## Red flags

- Dispatching codex before Sol has passed the plan → stop, review first.
- Merging a worktree branch Opus hasn't approved → not done.
- Sequential codex dispatches for independent tasks → wasted wall-clock; one message, many calls.
- A dispatch prompt that says "as discussed above" → codex has no above.
- Opening the PR without the stage-5 branch review → the per-task reviews never saw the integrated diff.
