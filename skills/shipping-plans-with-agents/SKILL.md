---
name: shipping-plans-with-agents
description: Use when a spec, design, or implementation plan is ready to build and the work will be split across subagents — planning, plan review, parallel implementation in worktrees, per-task review, branch review, and PR.
---

# Shipping Plans With Agents

Five stages, in order. No skipping, no reordering.

## Cast

| Name | Agent | Model | Access |
|---|---|---|---|
| Fable | `fable` | Claude Fable | read-only |
| Sol | `sol-reviewer` | gpt-5.6-sol, xhigh | read-only |
| Luna | `codex` | gpt-5.6-luna, max | write |
| Opus | `opus-reviewer` | Claude Opus | read-only |

Sol and Opus are **adversarial**: they hunt for reasons to reject, never to approve.

Every name is a **model**, pinned in `agents/*.md`, and every stage runs on the model named for it — whatever model this session happens to be. You are the orchestrator, not one of the four: you dispatch, you merge, you resolve conflicts, you talk to the user. Stages 1 and 5 are `fable` dispatches even if this session is already Fable, and stage 4 is an `opus-reviewer` dispatch even if this session is already Opus. Never do a stage's work inline because you happen to share its weights — the fresh context is half the point.

Sol and Luna shell out to the Codex CLI. If `codex` is missing from PATH or unauthenticated they report the error and stop — that blocks stages 2 and 3; don't route around it by doing the work yourself.

None of the four sees this conversation. Every dispatch prompt must be self-contained: the goal, the constraints the user stated, the files in play, the definition of done.

## Stages

**1. Plan — Fable.** `Agent(subagent_type: "fable")` with the spec or brief and everything the user said about it. Fable returns the plan, broken into small tasks with the independent ones marked. You own it from there: read it, and send it back if it missed the ask.

**2. Plan review — Sol.** `Agent(subagent_type: "sol-reviewer")` on the full plan text. Address blockers before executing. Re-review after major rework. **Never start executing a plan that hasn't passed sol-reviewer in this session.**

**3. Implement — Luna.** One `Agent(subagent_type: "codex", isolation: "worktree")` per task, all dispatched in a single message so they run in parallel. Worktrees make file overlap safe. Each agent commits its work in its own worktree.

**4. Task review — Opus.** As each task finishes, `Agent(subagent_type: "opus-reviewer")` on that worktree's commit plus the plan step it implements. FIX verdict → back to a `codex` agent in the *same* worktree, then re-review. APPROVE → merge that worktree branch into the working branch (you resolve conflicts).

A task is done only when approved **and** merged.

**5. Branch review — Fable + Sol.** Once every task is approved: dispatch `fable` and `sol-reviewer` on the integrated branch diff, both in one message so they run in parallel. Fix confirmed findings via `codex`, re-reviewed per stage 4. Only then commit, push, open the PR.

## Red flags

- Dispatching codex before Sol has passed the plan → stop, review first.
- Merging a worktree branch Opus hasn't approved → not done.
- Sequential codex dispatches for independent tasks → wasted wall-clock; one message, many calls.
- A dispatch prompt that says "as discussed above" → no subagent has an above.
- Opening the PR without the stage-5 branch review → the per-task reviews never saw the integrated diff.
- Writing the plan or the branch review inline instead of dispatching `fable` → wrong model, and no fresh context.
