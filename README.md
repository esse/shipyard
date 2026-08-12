# Shipyard

A five-stage shipping pipeline for Claude Code. Fable writes the plan, an
adversarial reviewer tries to kill it, Codex agents implement every independent
task in parallel git worktrees, and nothing merges until a second adversarial
reviewer signs it off.

Four models, five stages, one rule: **reviewers hunt for reasons to reject,
never to approve.**

## Install

```
/plugin marketplace add esse/shipyard
/plugin install shipyard@shipyard
```

## Requires

- The [Codex CLI](https://github.com/openai/codex) on `PATH` and authenticated
  (`codex login`). Two of the four roles shell out to `codex exec`.
- Git, for the worktree isolation used during implementation.

If you already keep `fable.md`, `codex.md`, `sol-reviewer.md`, or
`opus-reviewer.md` in `~/.claude/agents/`, delete them after installing — the
plugin ships the same names and duplicates are confusing.

## The cast

| Name | Agent | Model | Access |
| --- | --- | --- | --- |
| Fable | `fable` | Claude Fable | read-only |
| Sol | `sol-reviewer` | gpt-5.6-sol, xhigh reasoning | read-only |
| Luna | `codex` | gpt-5.6-luna, max reasoning | write |
| Opus | `opus-reviewer` | Claude Opus | read-only |

Every name is a model, pinned in that agent's frontmatter. **Your session model
doesn't matter** — start on Opus, Sonnet or Haiku and the plan is still written
by Fable and the branch still reviewed by Fable, because both are dispatches to
the pinned `fable` agent. Your session orchestrates: it dispatches, merges,
resolves conflicts, and talks to you.

Swap the model IDs in `agents/*.md` for whatever your accounts have. If your
build doesn't recognise the `fable` alias, use the full ID `claude-fable-5`.

## The pipeline

1. **Plan** — Fable writes the spec, split into small tasks, marking which are
   independent.
2. **Plan review** — Sol attacks the plan on paper. Blockers get fixed before a
   line of code is written. Verdict: `EXECUTE AS-IS` / `EXECUTE WITH FIXES` /
   `REWORK PLAN`.
3. **Implement** — one Luna agent per task, all dispatched at once, each in its
   own git worktree so parallel file edits can't collide. Each commits in its
   worktree.
4. **Task review** — Opus reviews each finished task against the plan step that
   spawned it. `FIX` goes back to Luna in the same worktree; `APPROVE` lets the
   branch merge. A task is done only when approved *and* merged.
5. **Branch review** — Fable and Sol both review the integrated diff, in
   parallel, before the PR opens.

The full stage-by-stage instructions live in
`skills/shipping-plans-with-agents/SKILL.md`, which your session loads on its
own when a plan is ready to build. You can also just say "ship this with
shipyard".

## Why cross-model

The plan author and the plan reviewer share no weights, no context, and no
sunk cost. Every role receives a self-contained prompt rather than the
conversation, so none of them can inherit the assumption that produced the bug.

Because the roles are pinned models rather than "whatever is running", that
independence doesn't quietly disappear when you switch your session model.

## Adapting it

Everything is markdown. Common edits:

- **No Codex account?** Point `agents/codex.md` at a different CLI, or replace
  it with a plain Claude subagent — the pipeline shape survives.
- **Solo tasks.** Stage 3 with one task is just "implement in a worktree". The
  review gates still apply.
- **Different verdict vocabulary.** The skill's red-flags list keys off the
  gates, not the exact words; rename them in the agent files if you prefer.

## License

MIT
