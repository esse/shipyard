# Shipyard

Shipyard is a shipping pipeline for Claude Code. One model writes the plan, models from other labs try to kill it, a crew of agents builds every independent task in parallel git worktrees, and nothing reaches a PR until two reviewers from two labs have attacked the integrated diff and the full test suite has passed on it.

Most changes don't need all of that. Before planning, the session triages the spec. Large or hard work gets the full shipyard. Everything else goes to [boatyard](#boatyard), which keeps the same stages and gates with a smaller, cheaper crew.

Every review hunts for reasons to reject. The gate is the blocker list, not an empty findings list, so nits never hold up a merge.

## Install

```
/plugin marketplace add esse/shipyard
/plugin install shipyard@shipyard
```

## Requirements

- **Codex CLI 0.147 or newer**, on `PATH` and logged in with `codex login`. Astra, Sol and Luna shell out to `codex exec`, and `guest-implementer` uses it for its Terra fallback. Astra writes the plan, so nothing runs without Codex. Luna runs with `--sandbox workspace-write -c approval_policy="never"`. Don't pass `--full-auto`, which 0.147 removed, or `--approve-for-me`, which conflicts with `--sandbox` since 0.153.
- **Antigravity CLI 1.5.12 or newer** (`agy`), signed in with a Gemini subscription or with `GEMINI_API_KEY` exported in the environment Claude Code starts from. `guest-implementer` runs Gemini 4 Neon through it for `ROUTINE` and `HARD` tasks, see [Gemini 4 Neon via Antigravity](#gemini-4-neon-via-antigravity). Without it, `ROUTINE` tasks fall back to Terra and `HARD` tasks to Sonnet.
- **Grok CLI**, only if you turn on the [Grok review](#grok-review): on `PATH`, signed in, with `grok-4.7` listed by `grok models`.
- **Git**, for the per-task worktrees.

Run `/shipyard:doctor` before you rely on any of this. It runs the exact commands the wrappers use, and confirms that each read-only reviewer really refuses a write. A broken gate with a green round-trip looks healthy everywhere else, so that last check matters most.

If `~/.claude/agents/` already holds a file named after any agent in this plugin, delete it after installing. The plugin ships `astra`, `sol`, `fable`, `opus`, `codex`, `opus-reviewer`, `simplifier`, `sonnet-reviewer`, `sonnet-implementer`, `guest-implementer`, `mythos` and `grok`, and duplicates get confusing. Shipyard 0.4 and earlier shipped a `sol-reviewer` agent. `astra` replaced it, and it has nothing to do with today's `sol`, so delete any stale copy. Shipyard 0.13 and earlier shipped `grok-implementer` and `grok-reviewer`, now `guest-implementer` and `guest-reviewer` because those seats run Grok or Neon, and an opt-in `bonsai-implementer`, now removed. Delete stale copies of all three, and drop `CLAUDE_LOCAL_AVAILABLE` from your settings. Shipyard 0.15 dropped Grok as a default seat: delete any stale `guest-reviewer`, and drop `SHIPYARD_NO_GROK` from your settings. Grok now reviews only when you opt in with `SHIPYARD_GROK_REVIEW`.

## The cast

| Name | Agent | Model | Access | Used in |
| --- | --- | --- | --- | --- |
| Astra | `astra` | gpt-6.2-astra, medium reasoning | read-only | shipyard: plan, plan and branch review |
| Sol | `sol` | gpt-6.2-sol, xhigh reasoning | read-only | shipyard: test audit |
| Fable | `fable` | Claude Fable | read-only | both: plan and branch review |
| Opus | `opus` | Claude Opus | read-only | boatyard: plan, plan and branch review |
| Opus | `opus-reviewer` | Claude Opus | read-only | shipyard: task review; both: polish review |
| Simplifier | `simplifier` | Claude Opus | read-only | both: simplify; boatyard: test audit |
| Sonnet | `sonnet-reviewer` | Claude Sonnet | read-only | boatyard: task review |
| Luna | `codex` | gpt-6-luna, max reasoning | write | both: `EASY` tasks, polish fixes, fallbacks |
| Neon | `guest-implementer` | gemini-4-neon-xhigh via `agy` | write | both: `ROUTINE` tasks; shipyard: `HARD` tasks |
| Neon | `sol` | gemini-4-neon-xhigh via `agy`, opt-in | read-only | shipyard: test audit, with `ANTIGRAVITY_ENABLED` |
| Terra | Neon fallback | gpt-6.1-terra, high reasoning | write | `ROUTINE` tasks when Neon fails before producing work |
| Sonnet | `sonnet-implementer` | Claude Sonnet 5.5 | write | shipyard: `HARD` tasks when Neon fails before producing work |
| Mythos | `mythos` | Claude Mythos 5.2, opt-in | read-only | both: security scan in branch review |
| Grok | `grok` | grok-4.7, xhigh reasoning, opt-in | read-only | both: plan and branch review, with `SHIPYARD_GROK_REVIEW` |

Each agent definition pins its model. The Claude agents pin it in frontmatter, the CLI wrappers in a command-line argument. **Your session model doesn't matter.** Start on Opus, Sonnet or Haiku and Astra still writes the plan, because every stage is a dispatch to a pinned agent. Your session orchestrates. It dispatches, merges, resolves conflicts and talks to you.

Swap the model IDs in `agents/*.md` for whatever your accounts offer. If your build doesn't recognise the `fable` or `sonnet` alias, use `claude-fable-5` or `claude-sonnet-5-5`. On the Codex side, `agents/astra.md` pins `gpt-6.2-astra` and `agents/sol.md` pins `gpt-6.2-sol`.

## Triage

Before stage 1 the session picks a pipeline.

- **Shipyard** takes work that is large or hard. That means more than five tasks, more than one module or service, or an open decision about API shape, data format, security, compatibility, concurrency or migration. It also takes anything you want on the strongest models.
- **Boatyard** takes the rest.

When unsure, the session picks shipyard. It tells you the call and the reason in one line and carries on. Say "use shipyard" or "use boatyard" to override it.

## Task tiers

The planner tags every task, and the tag picks the implementer.

The routing below follows a quick pass of the
[model role experiments](docs/model-role-experiments.md) (November 2026).

| Tag | Means | Implementer |
| --- | --- | --- |
| `EASY` | Fully prescribed, and copies a pattern already in the codebase | Luna |
| `ROUTINE` | No open design decision, but the implementer works out how | Neon, Terra as fallback |
| `HARD` | Leaves an API, data format, security, compatibility, concurrency or migration decision open | Neon, Sonnet as fallback; shipyard only |

## The pipeline

**1. Plan.** Astra turns the spec into small tasks, marks which ones are independent, and tags each one.

**2. Plan review.** Fable and a fresh Astra attack the plan in parallel. The fresh Astra is a new dispatch and a new `codex exec`. It gets the spec and the plan text and never sees the planning run, so it reads its own plan as a stranger's. Grok joins them when the Grok review is on. Blockers get fixed before anyone writes code. Review stops after two rounds, a full one and then a delta on what changed. Leftover nits ride along in the implementer briefs instead of starting a third round.

**3. Implement.** The session creates one worktree per task and dispatches every agent in one message. Luna runs sandboxed to its worktree. Neon runs under agy's sandbox, which leaks shell writes, and Sonnet has no sandbox at all, so the session checks the main checkout after each of their tasks, see [How the roles are confined](#how-the-roles-are-confined). The Codex and Antigravity wrappers commit for their CLIs, which can't write the main `.git`. Sonnet commits its own work.

**4. Task review.** Opus reviews each finished task against the plan step that spawned it. `FIX` sends it back to the same implementer in the same worktree. `APPROVE` lets it merge. A task is done when it is approved and merged, not before.

**4b. Polish.** Two passes run in order, test audit and then simplify. Sol lists fixes for the tests the branch added or changed, against the [test-audit rubric](#test-audit). Simplifier then lists simplifications for all changed code. The listers never edit. Luna applies each non-empty list in a fresh worktree as one commit and may decline items that would change behaviour, as long as it says why. Opus judges that commit against the list. A pass that still fails after one fix round gets dropped with a one-line note. Task commits never get dropped. The session skips the test audit when no tests changed and says so.

**5. Branch review.** Fable and Astra attack the integrated diff in parallel, joined by Mythos when the security scan is on and by Grok when the Grok review is on. They see both polish lists with their outcomes. Any accepted blocker goes through a repair, an Opus review, and a delta re-review by every reviewer, not just the one who raised it. Once nobody has blockers, the session runs the project's full test suite. A failure goes through the same repair loop. The PR opens only when the reviewers are clear and the suite is green on the same diff. If the project has no suite, the session says so.

The full instructions live in `skills/shipping-plans-with-agents/SKILL.md`. Your session loads it when a plan is ready to build, or when you say "ship this with shipyard".

## Test audit

The rubric in `skills/shipping-plans-with-agents/test-audit.md` keeps a test only if a real regression in some observable behaviour makes it fail, and nothing else does. Each behaviour gets one owning test, at the strongest boundary that can see it.

The listers flag tests that compare a value with itself, restate a list from the source, grep source text, or assert private state, call order or which helper ran. They also flag tests whose expected value comes from the code under test, whose mock supplies the behaviour being asserted, or that check removed code stays gone. So do tests of what the framework, runtime or type system already guarantees, fixtures the real code path could never produce, and test-only seams in production code. The rubric prefers rewriting a test over deleting it when something relies on the behaviour it covers. Deleting a test also deletes any production code that existed only for it.

API, protocol, config, migration, storage, security, default-value and ordering contracts stay, even when their tests are slow or static. A test that fails on the base revision may have found a bug, and bug fixes go to you as notes instead of into the polish commit.

The tombstone, platform-guarantee and rewrite-first rules come from caldoai's [prune-tests](https://github.com/caldoai/skills/blob/main/skills/prune-tests/SKILL.md) skill.

## Boatyard

Boatyard runs the same stages and gates with a smaller crew. Every shipyard rule still applies, including per-task worktrees, blocker-based gates, the two-round cap on plan review and delta re-reviews after every fix.

| Stage | Shipyard | Boatyard |
| --- | --- | --- |
| 1. Plan | Astra | Opus |
| 2. Plan review | Fable, fresh Astra, plus Grok if on | Fable, fresh Opus, plus Grok if on |
| 3. Implement | Luna or Neon by tag | Luna or Neon by tag |
| 4. Task review | Opus | Sonnet |
| 4b. Polish | Sol audits tests, Simplifier simplifies, Opus judges | Simplifier does both, Opus judges |
| 5. Branch review | Fable, Astra, plus Mythos and Grok if on | fresh Opus, Fable, plus Mythos and Grok if on |
| 5. Final tests | full suite, run by the session | same |

- **The Opus reviews are fresh dispatches.** They get the spec and the plan or diff, never the planning run, so the reviewer doesn't inherit the author's blind spots.
- **A `HARD` task means triage got it wrong.** If the plan, a plan reviewer or a branch fix calls a task `HARD`, boatyard stops, names the task and the reason, and restarts in shipyard from stage 1. Merged work stays on the branch.
- **The switches work the same.** `SHIPYARD_SECURITY_SCAN` adds Mythos to the branch review, and `SHIPYARD_GROK_REVIEW` adds Grok to plan and branch review. `ANTIGRAVITY_ENABLED` does nothing here, since boatyard has no Sol.
- **Boatyard gives up cross-lab review.** Anthropic models do all of its planning and reviewing. That buys speed and cost, which is why large or hard work still goes to shipyard.

The boatyard rules live in `skills/shipping-plans-with-agents/boatyard.md`.

## Gemini 4 Neon via Antigravity

`guest-implementer` always runs Gemini 4 Neon (`gemini-4-neon-xhigh`, through the Antigravity CLI) for `ROUTINE` and `HARD` tasks. Set `ANTIGRAVITY_ENABLED=1` and Neon also takes Sol's test audit. Boatyard has no Sol, so the variable changes nothing there.

```json
{ "env": { "ANTIGRAVITY_ENABLED": "1" } }
```

Why these seats: on the [Artificial Analysis coding-agent index](https://artificialanalysis.ai/agents/coding-agents) (November 2026), Antigravity with Neon xhigh scores 58.6, level with Claude Fable 5.2 xhigh (58.5) and Opus 5.5 max (58.2) at the top. In the November 2026 quick pass of the [model role experiments](docs/model-role-experiments.md), Neon xhigh matched Sonnet's acceptance rate on `HARD` tasks with higher design scores, though on only two cases. As a third reviewer, Gemini caught nothing Fable and Astra missed and raised more false blockers, so the review panel has no Gemini seat. The Gemini quota is weekly and shared across models, so expect the fallbacks to run when it is spent.

It needs `agy` 1.5.12 or newer, signed in either way agy supports: a Gemini subscription login, or `GEMINI_API_KEY` in the environment Claude Code starts from. The wrappers don't pick a backend, so agy uses whichever sign-in you set up. For `ANTIGRAVITY_ENABLED`, any non-empty value turns it on. If Neon is missing, out of quota or fails before producing work, `ROUTINE` tasks fall back to Terra (`gpt-6.1-terra`, high reasoning, through Codex), `HARD` tasks go to `sonnet-implementer`, and Sol falls back to `gpt-6.2-sol`. The wrapper stops instead of falling back if a failed Neon run left the worktree dirty.

## Security scan

Set `SHIPYARD_SECURITY_SCAN=1` and the branch review gains Mythos, pinned to `claude-mythos-5-2`. It looks at the integrated diff for security problems only, such as injection, missing auth checks, leaked secrets, unsafe data handling and supply-chain risk. Its blockers gate the PR like everyone else's, and every repair gets a delta re-scan. It is off by default.

```json
{ "env": { "SHIPYARD_SECURITY_SCAN": "1" } }
```

Any non-empty value turns it on. Once it is on, an unavailable Mythos model stops the pipeline instead of skipping the scan. The agent pins the full model ID because the bare `mythos` alias doesn't resolve.

## Grok review

Set `SHIPYARD_GROK_REVIEW=1` and Grok (`grok-4.7`, xhigh reasoning, read-only) joins plan review and branch review as one more adversarial reviewer, in shipyard and boatyard alike. Its blockers gate like everyone else's, and every fold or repair gets a delta re-review from it. It is off by default: in the [November 2026 quick pass](docs/model-role-experiments.md), no third reviewer caught anything Fable and Astra missed, so turn it on when you want another lab's eyes on a change anyway.

```json
{ "env": { "SHIPYARD_GROK_REVIEW": "1" } }
```

Any non-empty value turns it on. Once it is on, an unavailable Grok stops the pipeline instead of skipping the review; there is no fallback model.

## How the roles are confined

Every flag in the CLI commands does a job. Don't trim them.

- **Luna can't commit its own work.** `--sandbox workspace-write` can't reach a linked worktree's git index, so the `codex` wrapper commits. Don't add the git common dir as a writable root to get around this.
- **Grok reviews under two gates.** `--sandbox read-only` is kernel-enforced but still lets grok write under `~/.grok` and the temp dirs, so `--deny Edit --deny Write --deny Bash --deny MCPTool` closes the rest; `--deny MCPTool` is the one that stops a write-capable MCP tool. The wrapper treats a sandbox profile that failed to apply as a hard error.
- **`sonnet-implementer` has no sandbox.** It is a native Claude subagent that only its instructions keep in its worktree. The session checks the main checkout after every Sonnet task and won't merge a task that wrote outside its tree. That catches a breach after it happens. It doesn't prevent one.
- **The Antigravity roles use permission rules plus the terminal sandbox.** Under `ANTIGRAVITY_ENABLED`, `sol` runs with deny rules on `write_file(*)`, `command(*)`, `mcp(*)` and `execute_url(*)`. Those hold under `--dangerously-skip-permissions`, which is there only so headless runs don't stall. `guest-implementer` runs under `--sandbox`, which keeps shell commands in the worktree and temp dirs, with an allow rule for `write_file(<worktree>)` and a deny rule for `unsandboxed(*)`, and headless mode refuses anything not allowed, including Neon's requests to leave the sandbox. That is the design; in practice `/shipyard:doctor`'s implementer probe has seen Neon's shell commands write outside the worktree, so the session checks the main checkout after every Neon task, as for Sonnet. Committing from a linked worktree writes the main checkout's `.git`, so the wrapper agent commits for Neon. Never give the implementer `--dangerously-skip-permissions`, because it approves file writes outside the workspace. agy has no `--cwd`, so every agy launch `cd`s behind a `git rev-parse --show-toplevel` check that fails before agy starts if the `cd` was dropped. agy logs no sandbox event, so `/shipyard:doctor` probes both gates. A refused action ends a headless run with exit 0 and `jetski: no output produced`, which the wrappers treat as a failure.

## Why cross-model

The plan's author and its reviewers share no weights, no context and no sunk cost. Every role gets a self-contained prompt instead of the conversation, so no reviewer can inherit the assumption that caused the bug. Astra is the only role that rereads its own work, in stages 2 and 5. Both rereads are fresh dispatches told to attack, with no session resume and no planning context to stay loyal to.

The roles are pinned models, so switching your session model doesn't quietly turn this off.

Boatyard trades some of this away on purpose. Fresh dispatches still keep its reviewers away from the planner's context, but they all come from one lab. Triage limits boatyard to work small and simple enough to make that trade worth it.

## Adapting it

Everything is markdown.

- **No Codex account?** Point `agents/codex.md`, `agents/astra.md` and `agents/sol.md` at a different CLI, or swap them for plain Claude subagents. The pipeline still works, but planning and two review seats then come from the same lab.
- **One task?** Stage 3 becomes "implement in a worktree". Every review gate still applies.
- **Different verdict words?** Rename them in the agent files. The skill's red flags key off the gates, not the words.

## License

MIT
