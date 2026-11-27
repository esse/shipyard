# Shipyard

Shipyard is a shipping pipeline for Codex, Antigravity, and Claude Code. One model writes the plan, models from other labs try to kill it, a crew of agents builds every independent task in parallel git worktrees, and nothing reaches a PR until two reviewers from two labs have attacked the integrated diff and the full test suite has passed on it.

Most changes don't need all of that. Before planning, the session triages the spec. Large or hard work gets the full shipyard. Everything else goes to [boatyard](#boatyard), which keeps the same stages and gates with a smaller, cheaper crew.

Every review hunts for reasons to reject. The gate is the blocker list, not an empty findings list, so nits never hold up a merge.

## Install

### Claude Code

For the published plugin, run these inside Claude Code:

```
/plugin marketplace add esse/shipyard
/plugin install shipyard@shipyard
```

To use a local Shipyard checkout, launch Claude Code with
`claude --plugin-dir /absolute/path/to/shipyard`.

### Codex

Keep a Shipyard checkout on disk. Set `SHIPYARD_ROOT` to its absolute path
and create a user-level skill entry that loads the workflow from that checkout:

```sh
SHIPYARD_ROOT=/absolute/path/to/shipyard
skill_dir="$HOME/.agents/skills/shipping-plans-with-agents"
mkdir -p "$(dirname "$skill_dir")" &&
mkdir "$skill_dir" &&
cat > "$skill_dir/SKILL.md" <<EOF
---
name: shipping-plans-with-agents
description: Use when asked to run Shipyard or Boatyard to plan, review, build in worktrees, and verify a change with multiple agent providers.
---

Read and follow the canonical Shipyard skill at $SHIPYARD_ROOT/skills/shipping-plans-with-agents/SKILL.md.
Resolve its supporting files relative to that checkout and use portable dispatch.
EOF
```

Start a new Codex session and invoke `$shipping-plans-with-agents` with your spec.

### Antigravity CLI

Link the skill directory into Antigravity's global skills directory. Keeping
the link to the checkout gives the dispatcher access to the agent definitions.

```sh
SHIPYARD_ROOT=/absolute/path/to/shipyard
skill_dir="$HOME/.gemini/antigravity-cli/skills"
mkdir -p "$skill_dir" &&
ln -s "$SHIPYARD_ROOT/skills/shipping-plans-with-agents" "$skill_dir/"
```

Start a new Antigravity CLI session, check `/skills` for
`shipping-plans-with-agents`, and ask the lead to use it with your spec.

### Antigravity IDE

Use the Codex skill-entry example with
`skill_dir="$HOME/.gemini/config/skills/shipping-plans-with-agents"`.
Open the target workspace and ask Antigravity to use Shipyard with your spec.
See [Antigravity IDE's skill locations](https://codelabs.developers.google.com/getting-started-agy-ide).

### Other shell-capable harnesses

Point the lead at `/absolute/path/to/shipyard/skills/shipping-plans-with-agents/SKILL.md`.
For persistent discovery, add a skill entry that points to that file in the
harness's own skill directory, as in the Codex example.

## Start a session

From the repository you want to work on, start the host with your chosen
lead model. For example:

```sh
codex --model gpt-6.1-terra
# Or start an Antigravity session
agy --model gemini-4-neon-xhigh
```

Give the lead your spec and ask it to use Shipyard. In a desktop session,
make sure the checkout is readable and the terminal can run the provider
CLIs. The [portable dispatcher](skills/shipping-plans-with-agents/dispatch.md)
launches fresh Codex, Antigravity, Claude, and opt-in Grok workers on their
pinned models. The lead runs independent dispatches concurrently, collects
their results, checks the worktrees, and commits. The lead also runs the
final test suite. The same stage order and gates apply in each harness.

Set optional switches in the environment that starts the lead. For example:

```sh
SHIPYARD_GROK_REVIEW=1 codex --model gpt-6.1-terra
```

`OPUS_REVIEWS_TASK=1` makes Opus, not Sol, review each Shipyard task. `SHIPYARD_SECURITY_SCAN=1` adds Mythos to branch review.

## Requirements

- **Codex CLI 0.147 or newer**, on `PATH` and logged in with `codex login`. Astra, Sol and Luna shell out to `codex exec`, and `guest-implementer` uses it for its Terra fallback. Astra writes the plan, so nothing runs without Codex. Luna runs with `--sandbox workspace-write -c approval_policy="never"`. Don't pass `--full-auto`, which 0.147 removed, or `--approve-for-me`, which conflicts with `--sandbox` since 0.153.
- **Antigravity CLI 1.5.12 or newer** (`agy`), signed in with a Gemini subscription or with `GEMINI_API_KEY` exported in the environment the lead session starts from. `guest-implementer` runs Gemini 4 Neon through it for `ROUTINE` and `HARD` tasks, see [Gemini 4 Neon via Antigravity](#gemini-4-neon-via-antigravity). Without it, `ROUTINE` tasks fall back to Terra and `HARD` tasks to Sonnet.
- **Grok CLI**, only if you turn on the [Grok review](#grok-review): on `PATH`, signed in, with `grok-4.7` listed by `grok models`.
- **Claude Code CLI**, on `PATH` and signed in, for the Claude seats in portable sessions.
- **Python 3.9+**, for the portable dispatcher.
- **Git**, for the per-task worktrees.

In Claude Code, run `/shipyard:doctor` before relying on the plugin. It exercises the wrapper commands and probes their CLI sandbox rules. For other hosts, use the [portable dispatch checks](skills/shipping-plans-with-agents/dispatch.md#collect-the-result). To test routing and fallback locally without provider credentials, run `python3 -m unittest discover -s tests`.

If `~/.claude/agents/` already holds a file named after any agent in this plugin, delete it after installing. The plugin ships `astra`, `sol`, `fable`, `opus`, `codex`, `opus-reviewer`, `simplifier`, `sonnet-reviewer`, `sonnet-implementer`, `guest-implementer`, `mythos` and `grok`, and duplicates get confusing. Shipyard 0.4 and earlier shipped a `sol-reviewer` agent. `astra` replaced it, and it has nothing to do with today's `sol`, so delete any stale copy. Shipyard 0.13 and earlier shipped `grok-implementer` and `grok-reviewer`, now `guest-implementer` and `guest-reviewer` because those seats run Grok or Neon, and an opt-in `bonsai-implementer`, now removed. Delete stale copies of all three, and drop `CLAUDE_LOCAL_AVAILABLE` from your settings. Shipyard 0.17 made `simplifier` a Neon wrapper, moved the test audit to Neon by default and removed `ANTIGRAVITY_ENABLED`; drop it from your settings. Shipyard 0.15 dropped Grok as a default seat: delete any stale `guest-reviewer`, and drop `SHIPYARD_NO_GROK` from your settings. Grok now reviews only when you opt in with `SHIPYARD_GROK_REVIEW`.

## The cast

| Name | Agent | Model | Access | Used in |
| --- | --- | --- | --- | --- |
| Astra | `astra` | gpt-6.2-astra, medium reasoning | read-only | shipyard: plan, plan and branch review |
| Sol | `sol` | gpt-6.2-sol, high reasoning | read-only | shipyard: task review; both: test-audit fallback |
| Fable | `fable` | Claude Fable | read-only | both: plan and branch review |
| Opus | `opus` | Claude Opus | read-only | boatyard: plan, plan and branch review |
| Opus | `opus-reviewer` | Claude Opus | read-only | shipyard: task review fallback, or with `OPUS_REVIEWS_TASK`; both: polish review |
| Simplifier | `simplifier` | gemini-4-neon-xhigh via `agy`; gpt-6.2-sol fallback | read-only | both: simplify |
| Sonnet | `sonnet-reviewer` | Claude Sonnet | read-only | boatyard: task review |
| Luna | `codex` | gpt-6-luna, max reasoning | write | both: `EASY` tasks, polish fixes, fallbacks |
| Neon | `guest-implementer` | gemini-4-neon-xhigh via `agy` | write | both: `ROUTINE` tasks; shipyard: `HARD` tasks |
| Neon | `sol` | gemini-4-neon-xhigh via `agy` | read-only | both: test audit |
| Terra | Neon fallback | gpt-6.1-terra, high reasoning | write | `ROUTINE` tasks when Neon fails before producing work |
| Sonnet | `sonnet-implementer` | Claude Sonnet 5.5 | write | shipyard: `HARD` tasks when Neon fails before producing work |
| Mythos | `mythos` | Claude Mythos 5.2, opt-in | read-only | both: security scan in branch review |
| Grok | `grok` | grok-4.7, xhigh reasoning, opt-in | read-only | both: plan and branch review, with `SHIPYARD_GROK_REVIEW` |

Each agent definition pins its model. The Claude agents pin it in frontmatter, the CLI wrappers in a command-line argument. The wrappers themselves (`astra`, `sol`, `simplifier`, `codex`, `guest-implementer`, `grok`) run on Haiku: they only write a prompt file, launch the CLI and relay its answer, so they don't spend your session model's quota. **Your session model doesn't matter.** Start on Terra, Neon, or Opus and Astra still writes the Shipyard plan, because every stage is a dispatch to a pinned agent. Your session orchestrates. It dispatches, merges, resolves conflicts and talks to you.

For the plugin, model IDs are in `agents/*.md`. Portable CLI model IDs are in `dispatch.py`, with Claude models read from the agent definitions. If your build doesn't recognise the `fable` or `sonnet` alias, use `claude-fable-5` or `claude-sonnet-5-5`. On the Codex side, `agents/astra.md` pins `gpt-6.2-astra` and `agents/sol.md` pins `gpt-6.2-sol`.

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

**3. Implement.** The session creates one worktree per task and dispatches independent tasks in parallel. It checks the main checkout for unexpected changes after Neon and Sonnet tasks. In the Claude Code plugin the wrappers and native Sonnet agent commit. In portable sessions the lead checks and commits the worker's unstaged edits. See [How the roles are confined](#how-the-roles-are-confined).

**4. Task review.** Sol reviews each finished task against the plan step that spawned it. If Sol can't run, Opus takes that review and the session warns you; set `OPUS_REVIEWS_TASK=1` to always use Opus. Stage-5 repairs get the same reviewer. `FIX` sends it back to the same implementer in the same worktree. `APPROVE` lets it merge. A task is done when it is approved and merged, not before.

**4b. Polish.** Two passes run in order, test audit and then simplify. Neon, through `sol`, lists fixes for the tests the branch added or changed, against the [test-audit rubric](#test-audit). Neon, through `simplifier`, then lists simplifications for all changed code; both fall back to Sol. The listers never edit. Luna applies each non-empty list in a fresh worktree as one commit and may decline items that would change behaviour, as long as it says why. Opus judges that commit against the list. A pass that still fails after one fix round gets dropped with a one-line note. Task commits never get dropped. The session skips the test audit when no tests changed and says so.

**5. Branch review.** Fable and Astra attack the integrated diff in parallel, joined by Mythos when the security scan is on and by Grok when the Grok review is on. They see both polish lists with their outcomes. Any accepted blocker goes through a repair, a task review, and a delta re-review by every reviewer, not just the one who raised it. Once nobody has blockers, the session runs the project's full test suite. A failure goes through the same repair loop. The PR opens only when the reviewers are clear and the suite is green on the same diff. If the project has no suite, the session says so.

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
| 4. Task review | Sol, Opus fallback | Sonnet |
| 4b. Polish | Neon audits tests and lists simplifications, Opus judges | same |
| 5. Branch review | Fable, Astra, plus Mythos and Grok if on | fresh Opus, Fable, plus Mythos and Grok if on |
| 5. Final tests | full suite, run by the session | same |

- **The Opus reviews are fresh dispatches.** They get the spec and the plan or diff, never the planning run, so the reviewer doesn't inherit the author's blind spots.
- **A `HARD` task means triage got it wrong.** If the plan, a plan reviewer or a branch fix calls a task `HARD`, boatyard stops, names the task and the reason, and restarts in shipyard from stage 1. Merged work stays on the branch.
- **The switches work the same.** `SHIPYARD_SECURITY_SCAN` adds Mythos to the branch review, and `SHIPYARD_GROK_REVIEW` adds Grok to plan and branch review. `OPUS_REVIEWS_TASK` does nothing here, since boatyard's task reviewer is Sonnet.
- **Boatyard gives up cross-lab review.** Anthropic models do all of its planning and reviewing. That buys speed and cost, which is why large or hard work still goes to shipyard.

The boatyard rules live in `skills/shipping-plans-with-agents/boatyard.md`.

## Gemini 4 Neon via Antigravity

`guest-implementer` always runs Gemini 4 Neon (`gemini-4-neon-xhigh`, through the Antigravity CLI) for `ROUTINE` and `HARD` tasks. Neon also lists the polish fixes, read-only: `sol`'s test audit and `simplifier`'s simplifications, in shipyard and boatyard. That puts the token-heavy implementation and listing on the Gemini plan, leaves Anthropic with orchestration and the gates (Fable, Opus judging polish, Opus as task-review fallback), and keeps Codex for planning, review and `EASY` tasks.

Why these seats: on the [Artificial Analysis coding-agent index](https://artificialanalysis.ai/agents/coding-agents) (November 2026), Antigravity with Neon xhigh scores 58.6, level with Claude Fable 5.2 xhigh (58.5) and Opus 5.5 max (58.2) at the top. In the November 2026 quick pass of the [model role experiments](docs/model-role-experiments.md), Neon xhigh matched Sonnet's acceptance rate on `HARD` tasks with higher design scores, though on only two cases. As a third reviewer, Gemini caught nothing Fable and Astra missed and raised more false blockers, so the review panel has no Gemini seat. The Gemini quota is weekly and shared across models, so expect the fallbacks to run when it is spent.

It needs `agy` 1.5.12 or newer, signed in either way agy supports: a Gemini subscription login, or `GEMINI_API_KEY` in the environment the lead session starts from. The wrappers don't pick a backend, so agy uses whichever sign-in you set up. If Neon is missing, out of quota or fails before producing work, `ROUTINE` tasks fall back to Terra (`gpt-6.1-terra`, high reasoning, through Codex), `HARD` tasks go to `sonnet-implementer`, and the polish listers fall back to `gpt-6.2-sol`. The wrapper stops instead of falling back if a failed Neon run left the worktree dirty.

## Security scan

Set `SHIPYARD_SECURITY_SCAN=1` and the branch review gains Mythos, pinned to `claude-mythos-5-2`. It looks at the integrated diff for security problems only, such as injection, missing auth checks, leaked secrets, unsafe data handling and supply-chain risk. Its blockers gate the PR like everyone else's, and every repair gets a delta re-scan. It is off by default.

```json
{ "env": { "SHIPYARD_SECURITY_SCAN": "1" } }
```

Any non-empty value turns it on. If the Mythos model is unavailable, the session warns you that the scan did not run and carries on without it. The agent pins the full model ID because the bare `mythos` alias doesn't resolve.

## Grok review

Set `SHIPYARD_GROK_REVIEW=1` and Grok (`grok-4.7`, xhigh reasoning, read-only) joins plan review and branch review as one more adversarial reviewer, in shipyard and boatyard alike. When it runs, its blockers gate like everyone else's, and every fold or repair gets a delta re-review from it. It is off by default: in the [November 2026 quick pass](docs/model-role-experiments.md), no third reviewer caught anything Fable and Astra missed, so turn it on when you want another lab's eyes on a change anyway.

```json
{ "env": { "SHIPYARD_GROK_REVIEW": "1" } }
```

Any non-empty value turns it on. There is no fallback model: if Grok is unavailable (CLI missing, signed out, out of credit), the session warns you that the review did not run and carries on with Fable and Astra. A Grok sandbox that fails to apply still stops the pipeline, because that is a broken read-only gate, not an outage.

## How the roles are confined

Every flag in the CLI commands does a job. Don't trim them.

- **Luna edits only the task worktree.** Its `--sandbox workspace-write` sandbox blocks writes to the linked worktree's git index. The native `codex` wrapper or portable lead commits the edits.
- **Grok reviews under two gates.** `--sandbox read-only` is kernel-enforced but still lets grok write under `~/.grok` and the temp dirs, so `--deny Edit --deny Write --deny Bash --deny MCPTool` closes the rest; `--deny MCPTool` is the one that stops a write-capable MCP tool. The wrapper treats a sandbox profile that failed to apply as a hard error.
- **Claude workers use different access rules by harness.** Native Claude Code subagents follow their role instructions. Portable reviewers have only read tools. Portable Sonnet can edit through Claude's restricted file tools, and the lead runs its tests and commits.
- **The Antigravity roles use permission rules plus the terminal sandbox.** The Neon polish listers run with deny rules on `write_file(*)`, `command(*)`, `mcp(*)` and `execute_url(*)`. Those hold under `--dangerously-skip-permissions`, which is there only so headless runs don't stall. `guest-implementer` runs under `--sandbox`, which keeps shell commands in the worktree and temp dirs, with an allow rule for `write_file(<worktree>)` and a deny rule for `unsandboxed(*)`, and headless mode refuses anything not allowed, including Neon's requests to leave the sandbox. That is the design; in practice `/shipyard:doctor`'s implementer probe has seen Neon's shell commands write outside the worktree, so the session checks the main checkout after every Neon task, as for Sonnet. Committing from a linked worktree writes the main checkout's `.git`, so the native wrapper or portable lead commits for Neon. Never give the implementer `--dangerously-skip-permissions`, because it approves file writes outside the workspace. agy has no `--cwd`, so the native wrapper checks its `cd` with `git rev-parse --show-toplevel`. The portable dispatcher starts agy directly in the validated target checkout. agy logs no sandbox event, so `/shipyard:doctor` probes both gates. A refused action ends a headless run with exit 0 and `jetski: no output produced`, which the wrappers treat as a failure.

## Why cross-model

The plan's author and its reviewers share no weights, no context and no sunk cost. Every role gets a self-contained prompt instead of the conversation, so no reviewer can inherit the assumption that caused the bug. Astra is the only role that rereads its own work, in stages 2 and 5. Both rereads are fresh dispatches told to attack, with no session resume and no planning context to stay loyal to.

The roles are pinned models, so switching your session model doesn't quietly turn this off.

Boatyard trades some of this away on purpose. Fresh dispatches still keep its reviewers away from the planner's context, but they all come from one lab. Triage limits boatyard to work small and simple enough to make that trade worth it.

## Adapting it

The workflow and role briefs are Markdown. The portable CLI launcher is `skills/shipping-plans-with-agents/dispatch.py`.

- **No Codex account?** Point `agents/codex.md`, `agents/astra.md` and `agents/sol.md` at a different CLI, or swap them for plain Claude subagents. The pipeline still works, but planning and two review seats then come from the same lab.
- **One task?** Stage 3 becomes "implement in a worktree". Every review gate still applies.
- **Different verdict words?** Rename them in the agent files. The skill's red flags key off the gates, not the words.

## License

MIT
