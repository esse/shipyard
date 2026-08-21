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
| Grok | `grok-implementer` | grok-4.6, xhigh | write |
| Grok | `grok-reviewer` | grok-4.6, xhigh | read-only |

Every review in this pipeline is **adversarial** — Sol, Opus, Grok, and Fable on the branch diff all hunt for reasons to reject. The gate is blockers, not an empty findings list. `EXECUTE AS-IS` / `MERGE AS-IS` / `APPROVE` mean no blockers, not praise. `grok-reviewer` returns no verdict word at all — its blocker list *is* its verdict, because its verdicts ran lenient while its findings ran sharp. Fable wrote the plan and reviews the branch anyway; the fresh dispatch is what keeps that honest.

**Grok is optional, and the env var is the only switch.** Before stage 2, run `printenv SHIPYARD_NO_GROK`. Any non-empty value (use `1`) turns Grok off for this project, which changes exactly three dispatch sites: stage 2 drops `grok-reviewer`, stage 3 routes HARD tasks to `codex` along with the routine ones, stage 5 drops `grok-reviewer`. Say once, in stage 2, that Grok is disabled; every gate stays as it is. With the var unset, a missing or unauthenticated `grok` is a hard stop exactly like a missing `codex` — report it and wait, don't decide for yourself to run without Grok.

Every name is a **model**, pinned in `agents/*.md`, and every stage runs on the model named for it — whatever model this session happens to be. You are the orchestrator, not one of the cast: you dispatch, you merge, you resolve conflicts, you talk to the user. Stages 1 and 5 are `fable` dispatches even if this session is already Fable, and stage 4 is an `opus-reviewer` dispatch even if this session is already Opus. Never do a stage's work inline because you happen to share its weights — the fresh context is half the point.

Sol and Luna shell out to the Codex CLI; the two Grok agents shell out to the Grok CLI. If either binary is missing from PATH or unauthenticated, the agent reports the error and stops — don't route around it by doing the work yourself. `/shipyard:doctor` checks both CLIs end to end, including whether the read-only gates really deny; run it when a dispatch fails for a reason that looks environmental rather than about the task.

**Access is enforced differently per agent, and the flags are load-bearing.** Fable and Opus are native Claude subagents held read-only by their instructions alone — their tool lists include `Bash`, so nothing mechanical stops them. Sol is confined by `--sandbox read-only`; Luna by `--sandbox workspace-write` (headless via `--approve-for-me`); `grok-implementer` by `--sandbox workspace`, which refuses writes to the repository outside its worktree while still allowing `~/.grok` and the temp dirs. `grok-reviewer` is confined twice over, by `--sandbox read-only` and by four deny rules. Both grok roles need `--deny MCPTool` on top of any sandbox, because MCP servers are separate processes a sandbox does not cover.

One caveat that reaches you, not just the agents: a built-in grok sandbox profile that *cannot* be applied only warns and then runs unconfined. Both grok agents are required to detect that and stop, but detection is after the fact — so if one reports it, treat that worktree as untrusted and don't merge it. Never drop one of those flags to "simplify" a command.

None of them sees this conversation. Every dispatch prompt must be self-contained: the goal, the constraints the user stated, the files in play, the definition of done.

**Self-contained means paths and anchors, not pasted files.** The four CLI wrappers (`sol-reviewer`, `codex`, `grok-reviewer`, `grok-implementer`) are Claude subagents that spend Claude tokens on everything they read, and each one starts with a cold context. Give them absolute paths and `file:line` anchors and let the CLI read the tree on its own provider's budget — that is what the read-only and workspace sandboxes are for. Paste only what is not on disk: diffs, `git log`, test output, a previous review. A brief that quotes file bodies at a wrapper buys the same bytes twice, at the higher price, and can hand it a stale copy.

**Key off the blocker list, not the verdict word.** Reviewers classify findings as blocker / risk / nit. If `blockers` is empty, that review has passed — even if the model wrote `EXECUTE WITH FIXES`, `MERGE WITH FIXES`, or `FIX` above only nits and risks. Say so when you override a mislabeled verdict. Do not auto-convert `REWORK PLAN` or `DO NOT MERGE`; those stop the pipeline even when the list is messy. Grok has no verdict line to override, and no way to say `REWORK PLAN` — a structural objection from it arrives as a blocker, which gates the same way.

## Stages

**1. Plan — Fable.** `Agent(subagent_type: "fable")` with the spec or brief and everything the user said about it. Fable returns the plan, broken into small tasks, with the independent ones marked and each tagged `ROUTINE` or `HARD`. You own it from there: read it, and send it back if it missed the ask or left tasks untagged.

**2. Plan review — Sol + Grok.** Dispatch `sol-reviewer` and `grok-reviewer` in one message so they run in parallel, each given the original spec *and* the plan — a reviewer holding only the plan cannot see a requirement the plan dropped.

Round 1 is a full review. `REWORK PLAN` from any one reviewer blocks outright, however happy the others are. If every enabled reviewer has an empty blocker list, append any nits and risks to the implementer briefs and open stage 3 — do not run a second round to hunt for more.

Otherwise fold blockers into one revised plan of record. Residual nits and risks are notes, not folds, unless they come along for free. Round 2 is a **delta**, never a new first pass: re-dispatch every enabled reviewer with the original spec, the current plan, that reviewer's previous review (verbatim), and the plan delta / folded-blocker list, labelled as a delta review. Editing the plan does not license a full re-read of accepted text.

Cap at two rounds (one full, one delta). After round 2:

- Remaining nits and risks → append them to every implementer brief as non-blocking notes, tell the user once, and open stage 3. That is a success path, not a bypass.
- Remaining blockers you accept → fold, then stop and ask. Do not start a third round on your own.
- Remaining blockers you think are wrong → the same stop-and-ask as in stage 5 below.

**Implementation starts when every enabled reviewer has an empty blocker list on the current plan, or when round 2 closed with only nits and risks remaining** (with `SHIPYARD_NO_GROK` set, that set is Sol alone). Nothing else opens the gate. Where reviewers contradict each other on a non-blocking finding, say which you took and why.

**3. Implement — Luna and Grok.** One agent per task, all dispatched in a single message so they run in parallel, each with `isolation: "worktree"` so file overlap is safe. Route by the plan's tag: `ROUTINE` → `codex`, `HARD` → `grok-implementer`. Include residual stage-2 nits and risks in each brief as non-blocking notes. Each wrapper commits in its own worktree; the inner CLI does not.

**4. Task review — Opus.** As each task finishes, `Agent(subagent_type: "opus-reviewer")` on that worktree's commit plus the plan step it implements. `FIX` (non-empty blockers) → back to the *same* implementer agent (`codex` or `grok-implementer`) in the *same* worktree, then re-review. `APPROVE` (empty blockers, nits allowed) → merge that worktree branch into the working branch (you resolve conflicts).

A task is done only when approved **and** merged.

**5. Branch review — Fable + Sol + Grok.** Once every task is approved *and merged*: dispatch `fable`, `sol-reviewer` and `grok-reviewer` in one message so they run in parallel, each given the spec, the final plan, the base revision, and the integrated diff. All three are adversarial; verdicts are MERGE AS-IS / MERGE WITH FIXES / DO NOT MERGE, derived from blockers the same way. `MERGE AS-IS` means no blockers.

This stage gates the branch's *final* state, so a verdict dies the moment the diff changes. Do not round-cap stage 5. The repair loop, when any reviewer reports a blocker you accept:

1. Tag the repair brief and dispatch it to `codex` (`ROUTINE`) or `grok-implementer` (`HARD`) in a fresh worktree, where it commits. Same rule as stage 1: `ROUTINE` only if the change is fully prescribed, follows a pattern already in the codebase, and leaves no open decision about API shape, data format, security, compatibility, concurrency or migration; otherwise `HARD`.
2. `opus-reviewer` on that commit, with the findings as the step it implements. FIX goes back to the same agent; APPROVE lets you merge it into the branch.
3. Regenerate the integrated diff and **re-dispatch every enabled reviewer as a delta**, not only the ones who complained: previous review, new diff, what was fixed. Not a first-pass re-read of accepted text.

**The PR opens only when every enabled reviewer has an empty blocker list on the current diff.** Nothing else clears the gate. `MERGE WITH FIXES` (non-empty blockers) obliges you to apply the fixes and loop. Nits on a `MERGE AS-IS` (or a mislabeled `MERGE WITH FIXES` with empty blockers) are reported once and do not block. If you think a blocker should be declined, the pipeline *stops there*: report it to the user and wait. Agreeing that a finding is wrong does not convert a verdict, so say plainly that they have two ways to resume — tell you to re-dispatch with that finding excluded from the gate, or tell you to bypass Shipyard and open the PR as it stands. Never pick either one for them. That bypass is for declining a blocker, not for escaping nits.

## Red flags

- Dispatching an implementer while a plan reviewer still has blockers, except the round-2 residual-nit path → stop, review first. Sol alone is the gate only when `SHIPYARD_NO_GROK` is set.
- Full re-review of a plan or branch after a fold → that is a delta. A new first pass is how nits regenerate.
- Starting a third stage-2 round on your own → stop and ask.
- Folding nits as if they were blockers, or looping until findings are zero → the gate is blockers.
- Sending a `HARD` task to `codex` while Grok is enabled, or a `ROUTINE` one to `grok-implementer` ever → the tag exists to pick the model; follow it.
- Deciding for yourself that Grok is "not needed" → `SHIPYARD_NO_GROK` is the user's switch, not your call.
- Merging a worktree branch Opus hasn't approved → not done.
- Sequential implementer dispatches for independent tasks → wasted wall-clock; one message, many calls.
- A dispatch prompt that says "as discussed above" → no subagent has an above.
- A brief that pastes file bodies a CLI wrapper could read itself → paths and `file:line` anchors instead; you are billed for every quote, twice.
- Waiting on a CLI wrapper by tailing its log → one blocking wait on an end marker; progress checks are a full context round-trip each.
- Opening the PR without the stage-5 branch review → the per-task reviews never saw the integrated diff.
- Opening the PR on a diff that changed after the last stage-5 pass → the verdict you are citing was about a different branch.
- Opening the PR while a stage-5 reviewer still has blockers → nits do not block; blockers do.
- Writing the plan or the branch review inline instead of dispatching `fable` → wrong model, and no fresh context.
