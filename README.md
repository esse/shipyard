# Shipyard

A five-stage shipping pipeline for Claude Code. Fable writes the plan, two
adversarial reviewers on two other labs' models try to kill it, Codex and Grok
agents implement every independent task in parallel git worktrees, and nothing
merges until Fable, Sol and Grok have all attacked the integrated diff.

Five models, five stages, one rule: **every review is adversarial — reviewers
hunt for reasons to reject, never to approve.** Fable reviews the branch built
from its own plan, and is told to distrust it.

## Install

```
/plugin marketplace add esse/shipyard
/plugin install shipyard@shipyard
```

## Requires

- The [Codex CLI](https://github.com/openai/codex) on `PATH` and authenticated
  (`codex login`). Two roles shell out to `codex exec`.
- The Grok CLI (`grok`) on `PATH` and authenticated (`grok login`). Two roles
  shell out to `grok --prompt-file`. Required unless you switch Grok off — see
  [Turning Grok off](#turning-grok-off).
- Git, for the worktree isolation used during implementation.

Run `/shipyard:doctor` to check both CLIs before you rely on them. It exercises
the exact delegation form the wrappers use, and asserts that the read-only
reviewer gates actually refuse a write — a green round-trip with a broken gate
is the one failure that would otherwise look healthy.

If you already keep any of `fable.md`, `codex.md`, `sol-reviewer.md`,
`opus-reviewer.md`, `grok-implementer.md` or `grok-reviewer.md` in
`~/.claude/agents/`, delete them after installing — the plugin ships the same
names and duplicates are confusing.

## The cast

| Name | Agent | Model | Access |
| --- | --- | --- | --- |
| Fable | `fable` | Claude Fable | read-only |
| Sol | `sol-reviewer` | gpt-5.6-sol, xhigh reasoning | read-only |
| Luna | `codex` | gpt-5.6-luna, max reasoning | write |
| Opus | `opus-reviewer` | Claude Opus | read-only |
| Grok | `grok-implementer` | grok-4.6, xhigh reasoning | write |
| Grok | `grok-reviewer` | grok-4.6, xhigh reasoning | read-only |

Every name is a model, pinned in the agent definition — frontmatter for the
Claude agents, a CLI argument for the wrappers. **Your session model
doesn't matter** — start on Opus, Sonnet or Haiku and the plan is still written
by Fable and the branch still reviewed by Fable, because both are dispatches to
the pinned `fable` agent. Your session orchestrates: it dispatches, merges,
resolves conflicts, and talks to you.

Swap the model IDs in `agents/*.md` for whatever your accounts have. If your
build doesn't recognise the `fable` alias, use the full ID `claude-fable-5`.

## The pipeline

1. **Plan** — Fable turns the spec into a plan, split into small tasks,
   marking which are independent and tagging each `ROUTINE` or `HARD`.
2. **Plan review** — Sol and Grok attack the plan on paper, in parallel.
   Blockers get fixed before a line of code is written. Verdict:
   `EXECUTE AS-IS` / `EXECUTE WITH FIXES` / `REWORK PLAN`.
3. **Implement** — one agent per task, all dispatched at once, each in its own
   git worktree so parallel file edits can't collide, and sandboxed to it
   (with one caveat — see [How the Grok roles are
   confined](#how-the-grok-roles-are-confined)). `ROUTINE` tasks go to
   Luna, `HARD` ones to Grok. Each commits in its worktree.
4. **Task review** — Opus reviews each finished task against the plan step that
   spawned it. `FIX` goes back to the same implementer in the same worktree;
   `APPROVE` lets the branch merge. A task is done only when approved *and*
   merged.
5. **Branch review** — Fable, Sol and Grok all attack the integrated diff, in
   parallel. Verdict: `MERGE AS-IS` / `MERGE WITH FIXES` / `DO NOT MERGE`. Fixes
   send the branch back through this stage; the PR opens only once every
   enabled reviewer returns `MERGE AS-IS` on the diff as it then stands.

The full stage-by-stage instructions live in
`skills/shipping-plans-with-agents/SKILL.md`, which your session loads on its
own when a plan is ready to build. You can also just say "ship this with
shipyard".

## Turning Grok off

Set `SHIPYARD_NO_GROK=1` and the two Grok roles drop out: the plan gets reviewed
by Sol alone, `HARD` tasks go to Luna with the routine ones, and the branch
review runs Fable + Sol. The stage gates are unchanged. In
`.claude/settings.json`:

```json
{ "env": { "SHIPYARD_NO_GROK": "1" } }
```

Any non-empty value counts, `0` and `false` included — it's a switch, not a
boolean. This env var is the *only* way to run without Grok: with it unset, a
missing or unauthenticated `grok` stops the pipeline exactly like a missing
`codex` would, rather than quietly shipping with one less reviewer.

## How the Grok roles are confined

Every flag in the two grok commands is load-bearing, so don't trim them:

- **`grok-reviewer` gets two gates.** `--sandbox read-only` is kernel-enforced
  and refuses writes to the project; the `--deny Edit/Write/Bash/MCPTool` rules
  cover what a sandbox can't, since `--deny MCPTool` is the only thing that
  closes MCP tools — the `--tools` allowlist leaves them reachable.
  `--permission-mode plan`, by contrast, does not block writes headlessly.
- **`grok-implementer` is confined by `--sandbox workspace`**: writes are
  limited to its worktree plus `~/.grok` and the temp dirs, so the rest of the
  repo, sibling worktrees and the main `.git` are all off limits. That last one
  is also why it can't commit its own work — committing from a linked worktree
  writes the main checkout's `.git` — so the wrapper agent runs the commit.
  Both roles also pass `--deny MCPTool`, because MCP servers run as separate
  processes that no sandbox profile covers.
- **A built-in profile that can't be applied only warns, then runs
  unconfined.** The wrappers are told to detect that — on stderr and via the
  `ProfileApplied` event in `~/.grok/sandbox-events.jsonl` — and refuse to
  commit, but detection happens after the run. For prevention instead, define a
  custom profile with a non-empty `deny` list in `.grok/sandbox.toml` and name
  it in the command: grok refuses to start rather than expose denied paths when
  a custom profile is unknown, its `sandbox.toml` is malformed, or (on Linux)
  `bubblewrap` is missing. That does not extend to the kernel and entitlement
  failures that make a built-in profile fail open.

## Why cross-model

The plan author and the plan reviewers share no weights, no context, and no
sunk cost. Every role receives a self-contained prompt rather than the
conversation, so none of them can inherit the assumption that produced the bug.
Fable is the one role that reads its own work twice, and stage 5 tells it to
attack the branch rather than defend the plan.

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
