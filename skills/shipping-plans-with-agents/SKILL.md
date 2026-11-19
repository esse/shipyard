---
name: shipping-plans-with-agents
description: Use when a spec, design, or implementation plan is ready to build and the work will be split across subagents — triage into shipyard or boatyard, planning, plan review, parallel implementation in worktrees, per-task review, test-audit and simplify polish passes, branch review, a final test run, and PR.
---

# Shipping Plans With Agents

Five stages, in order, with a polish stage (4b) between 4 and 5 and a final test run closing 5. No skipping, no reordering.

## Stage 0 — triage: shipyard or boatyard

Before anything else, even before stage 1, decide which pipeline the spec gets:

- **Shipyard** (everything below) if the work is **large or hard**: you expect more than five tasks, it crosses more than one module or service, or any part of it leaves open a decision about API shape, data format, security, compatibility, concurrency or migration. Also if the user asked for the strongest models.
- **Boatyard** otherwise. Read `boatyard.md` next to this file; it swaps the cast and keeps every rule here.

When unsure, it is shipyard. An explicit "use shipyard" / "use boatyard" from the user wins. Tell the user the call in one line, with the reason, then go on without waiting.

## Cast

| Name | Agent | Model | Access |
|---|---|---|---|
| Astra | `astra` | gpt-6.2-astra, medium | read-only |
| Sol | `sol` | gpt-6.2-sol, xhigh | read-only |
| Fable | `fable` | Claude Fable | read-only |
| Luna | `codex` | gpt-6-luna, max | write |
| Opus | `opus-reviewer` | Claude Opus | read-only |
| Simplifier | `simplifier` | Claude Opus | read-only |
| Sonnet | `sonnet-implementer` | Claude Sonnet 5.5 | write |
| Grok | `guest-implementer` | grok-4.7, xhigh | write |
| Grok | `guest-reviewer` | grok-4.7, xhigh | read-only |
| Terra | `guest-implementer` / `guest-reviewer` fallback | gpt-6.1-terra, high | same access as the Grok role |
| Mythos | `mythos` | Claude Mythos 5.2 (opt-in) | read-only |

Every review in this pipeline is **adversarial** — Fable, Astra, Grok, Opus and Mythos all hunt for reasons to reject. The gate is blockers, not an empty findings list. `EXECUTE AS-IS` / `MERGE AS-IS` / `APPROVE` mean no blockers, not praise. `guest-reviewer` returns no verdict word at all — its blocker list *is* its verdict, because its verdicts ran lenient while its findings ran sharp. Astra wrote the plan and reviews it again in stage 2, and the branch in stage 5; the fresh dispatch is what keeps that honest — a new subagent, a new `codex exec`, none of the planning context.

**Grok is optional, and the env var is the only switch.** Before stage 2, run `printenv SHIPYARD_NO_GROK`; it is ignored when `ANTIGRAVITY_ENABLED` is set (next paragraph). Any non-empty value (use `1`) turns Grok off for this project, which changes exactly three dispatch sites: stage 2 drops `guest-reviewer` (leaving Fable and a fresh Astra), stage 3 routes ROUTINE tasks to `codex` along with the easy ones (HARD still goes to `sonnet-implementer`), stage 5 drops `guest-reviewer`. Say once, in stage 2, that Grok is disabled; every gate stays as it is. With the var unset, the Grok agents fall back to Terra (`gpt-6.1-terra`, high, via Codex CLI) on their own when Grok is missing or not working; the orchestrator dispatches them unchanged and tells the user once when a fallback happened. Only Terra also failing is a hard stop. A Grok sandbox profile that failed to apply remains a hard stop, and `guest-implementer` also stops if the worktree is dirty after a failed Grok attempt.

**Antigravity swaps in Gemini 4 Neon, and the env var is the only switch.** Before stage 2, also run `printenv ANTIGRAVITY_ENABLED`. Any non-empty value (use `1`) makes `guest-reviewer`, `guest-implementer` and `sol` run `gemini-4-neon-xhigh` through the Antigravity CLI (`agy`) instead of Grok and gpt-6.2-sol. Dispatch them unchanged — the agent names, routing and gates stay as they are. With it set, `SHIPYARD_NO_GROK` is ignored everywhere in this skill: that switch is about Grok, and Grok no longer runs. Neon failing before producing work falls back to Terra for the two Grok roles and to gpt-6.2-sol for `sol`; tell the user once when that happened. Say once, in stage 2, that Antigravity is enabled.

**The security scan is opt-in, and the env var is the only switch.** Before stage 2, also run `printenv SHIPYARD_SECURITY_SCAN`. Any non-empty value (use `1`) adds `mythos` to stage 5 as one more enabled reviewer: it is dispatched in the same message as the others, its blockers gate the PR like theirs, and it is re-dispatched as a delta on every repair. Nothing else changes. Say once, in stage 2, that the security scan is enabled. With the var set, a `mythos` dispatch that fails because the model is unavailable is a hard stop exactly like a missing `codex` — report it and wait, never open the PR without the scan.

Every name is a **model**, pinned in `agents/*.md`, and every stage runs on the model named for it — whatever model this session happens to be. You are the orchestrator, not one of the cast: you dispatch, you merge, you resolve conflicts, you talk to the user. Stages 2 and 5 are `fable` dispatches even if this session is already Fable, and stage 4 is an `opus-reviewer` dispatch even if this session is already Opus. In stage 4b, `sol` / `simplifier` are lister dispatches and `opus-reviewer` is the judge dispatch. The final test run is the one step the orchestrator runs itself. Never do a stage's work inline because you happen to share its weights — the fresh context is half the point.

Astra, Sol and Luna shell out to the Codex CLI; the two Grok agents try the Grok CLI first and fall back to Terra through Codex when Grok fails before producing work. With `ANTIGRAVITY_ENABLED`, those two and Sol run `agy` instead, with the same fallbacks. If Codex is missing or unauthenticated, or both Grok and Terra fail, the agent reports the exact error(s) and stops — don't route around it by doing the work yourself. `/shipyard:doctor` checks every enabled CLI and Terra's fallback invocation end to end, including whether the read-only gates really deny; run it when a dispatch fails for a reason that looks environmental rather than about the task.

**Access is enforced differently per agent, and the flags are load-bearing.** Fable, Opus, Simplifier and Mythos are native Claude subagents held read-only by their instructions alone — their tool lists include `Bash`, so nothing mechanical stops them. Astra is confined by `--sandbox read-only`, in every job including stage 1's planning; Sol by `--sandbox read-only`; Luna by `--sandbox workspace-write` (headless via `approval_policy="never"`); `guest-implementer` by `--sandbox workspace`, which refuses writes to the repository outside its worktree while still allowing `~/.grok` and the temp dirs. `sonnet-implementer` has no sandbox at all: it is a native Claude subagent held to its worktree by its instructions, so after every Sonnet task run `git status --short` in the main checkout and treat any change you didn't make as a breach — that worktree is untrusted and does not merge. `guest-reviewer` is confined twice over, by `--sandbox read-only` and by four deny rules. Both grok roles need `--deny MCPTool` on top of any sandbox, because MCP servers are separate processes a sandbox does not cover. Under `ANTIGRAVITY_ENABLED`, `guest-reviewer` and `sol` are held read-only by agy deny rules on `write_file(*)`, `command(*)`, `mcp(*)` and `execute_url(*)`, and `guest-implementer` by `--sandbox` plus an allow rule for `write_file` in its worktree, never `--dangerously-skip-permissions`. agy has no `--cwd`, so its launches `cd` behind a `git rev-parse --show-toplevel` check, and it logs no sandbox event, so `/shipyard:doctor` probes these gates.

One caveat that reaches you, not just the agents: a built-in grok sandbox profile that *cannot* be applied only warns and then runs unconfined. Both grok agents are required to detect that and stop, but detection is after the fact — so if one reports it, treat that worktree as untrusted and don't merge it. Never drop one of those flags to "simplify" a command.

None of them sees this conversation. Every dispatch prompt must be self-contained: the goal, the constraints the user stated, the files in play, the definition of done.

**Self-contained means paths and anchors, not pasted files.** The five CLI wrappers (`astra`, `sol`, `codex`, `guest-reviewer`, `guest-implementer`) are Claude subagents that spend Claude tokens on everything they read, and each one starts with a cold context. Give them absolute paths and `file:line` anchors and let the CLI read the tree on its own provider's budget — that is what the read-only and workspace sandboxes are for. Paste only what is not on disk: diffs, `git log`, test output, a previous review. A brief that quotes file bodies at a wrapper buys the same bytes twice, at the higher price, and can hand it a stale copy.

**Key off the blocker list, not the verdict word.** Reviewers classify findings as blocker / risk / nit. If `blockers` is empty, that review has passed — even if the model wrote `EXECUTE WITH FIXES`, `MERGE WITH FIXES`, or `FIX` above only nits and risks. Say so when you override a mislabeled verdict. Do not auto-convert `REWORK PLAN` or `DO NOT MERGE`; those stop the pipeline even when the list is messy. Grok has no verdict line to override, and no way to say `REWORK PLAN` — a structural objection from it arrives as a blocker, which gates the same way.

**Verify a citation before you act on it.** Every finding is supposed to cite `file:line`. Before you fold a blocker, confirm the file is there and the line says what the finding claims — one `sed -n` settles it. **A finding whose citation points at a file that does not exist is a hallucination: discard it on the spot, say so once, and do not fold it, do not ask the user about it, and do not count it toward the gate.** Two things look like this and are not, so check them first: a path the plan itself creates, which of course does not exist yet at plan-review time, and a path that moved in a commit the reviewer never saw. If the defect turns out to be real under a corrected path, keep the finding and fix the path. One hallucinated citation does not disqualify the rest of that review — check its other findings the same way instead of throwing the whole thing out.

## Stages

**1. Plan — Astra.** `Agent(subagent_type: "astra")` with the spec or brief and everything the user said about it. Astra returns the plan, broken into small tasks, with the independent ones marked and each tagged `EASY`, `ROUTINE` or `HARD`. You own it from there: read it, and send it back if it missed the ask or left tasks untagged.

**2. Plan review — Fable + Astra + Grok.** Dispatch `fable`, `astra` and `guest-reviewer` in one message so they run in parallel, each given the original spec *and* the plan — a reviewer holding only the plan cannot see a requirement the plan dropped. The `astra` dispatch is a fresh one: it carries the spec and the plan text, never the planning run's context or session id, so it reads its own plan as a stranger's.

Round 1 is a full review. `REWORK PLAN` from any one reviewer blocks outright, however happy the others are. If every enabled reviewer has an empty blocker list, append any nits and risks to the implementer briefs and open stage 3 — do not run a second round to hunt for more.

Otherwise fold blockers into one revised plan of record. Residual nits and risks are notes, not folds, unless they come along for free. Round 2 is a **delta**, never a new first pass: re-dispatch every enabled reviewer with the original spec, the current plan, that reviewer's previous review (verbatim), and the plan delta / folded-blocker list, labelled as a delta review. Editing the plan does not license a full re-read of accepted text.

Cap at two rounds (one full, one delta). After round 2:

- Remaining nits and risks → append them to every implementer brief as non-blocking notes, tell the user once, and open stage 3. That is a success path, not a bypass.
- Remaining blockers you accept → fold, then stop and ask. Do not start a third round on your own.
- Remaining blockers you think are wrong → the same stop-and-ask as in stage 5 below.

**Implementation starts when every enabled reviewer has an empty blocker list on the current plan, or when round 2 closed with only nits and risks remaining** (with `SHIPYARD_NO_GROK` set and `ANTIGRAVITY_ENABLED` unset, that set is Fable and Astra). Nothing else opens the gate. Where reviewers contradict each other on a non-blocking finding, say which you took and why.

**3. Implement — Luna, Grok and Sonnet.** **Create each worktree yourself, before dispatching**, and pass its absolute path in the brief: `git worktree add <root>/<repo>-<task-slug> -b <branch>`. Then dispatch one agent per task, all in a single message so they run in parallel.

Do **not** use `isolation: "worktree"`. It picks its own path, and you need the path in advance for three things: a project's own convention for where worktrees live, seeding the tree so the agent can build (dependencies, build artifacts, submodule sources — a bare worktree usually cannot compile or run tests), and `guest-implementer`'s `--sandbox workspace`, whose confinement root *is* that path. Verify the tree compiles before you dispatch; an agent that cannot run the suite will report a gate it never ran. Route by the plan's tag: `EASY` → `codex`, `ROUTINE` → `guest-implementer`, `HARD` → `sonnet-implementer`. Include residual stage-2 nits and risks in each brief as non-blocking notes. Each wrapper commits in its own worktree; the inner CLI does not. `sonnet-implementer` has no inner CLI and commits its own work.

**4. Task review — Opus.** As each task finishes, `Agent(subagent_type: "opus-reviewer")` on that worktree's commit plus the plan step it implements. `FIX` (non-empty blockers) → back to the *same* implementer agent (`codex`, `guest-implementer` or `sonnet-implementer`) in the *same* worktree, then re-review. `APPROVE` (empty blockers, nits allowed) → merge that worktree branch into the working branch (you resolve conflicts).

A task is done only when approved **and** merged.

**4b. Polish — test audit, then simplify.** Once every task is approved and merged, run these passes in order.

**Test audit.** Scope is the test files added or changed in `git diff --name-only <base>...HEAD`, plus production code those tests reach that exists only to serve tests. Identify test files from the project's test-runner config or conventional test paths; when unsure, include the file. If no tests changed, skip this pass and tell the user in one line. The lister is `sol` in shipyard and `simplifier` (`test-audit` job) in boatyard. Its brief carries the absolute main-checkout path, base revision, test-file list, and absolute path of `test-audit.md` next to this file.

**Simplify.** Scope is production and test code changed on the branch. The lister is `simplifier` (`simplify` job); its brief carries the absolute main-checkout path, base revision, and all changed files from `git diff --name-only <base>...HEAD`.

Both listers are read-only and return exactly `findings:` with numbered `path/to/file:LINE — what to change, and why (rubric item or simplify rule)` entries, or the single line `no findings`. With fixes, they may follow the list with `notes:`; with notes but no fixes, they print `no findings` followed by a `notes:` block. Production bug fixes are out of scope: listers report them under `notes:`, the orchestrator relays them to the user, and they are not applied.

Test audit merges before simplify starts. For each non-empty fix list, follow these steps; if the list is empty, the pass is done and the orchestrator says so in one line:

Before dispatching Luna for a pass, the orchestrator first strikes any list item whose path is not in `git diff --name-only <base>...HEAD` (for the test audit, also allow test-only production seams the item names explicitly as such) or whose cited line does not exist, and says so in one line. Item paths are repo-relative.

1. Create and seed a fresh worktree from the working branch as in stage 3, at `<root>/<repo>-test-audit` or `<root>/<repo>-simplify`.
2. Dispatch `codex` (Luna) with the whole fix list. Polish passes always go to `codex`, regardless of task tags or `SHIPYARD_NO_GROK`.
3. The codex brief tells the codex wrapper to put each declined item and its reason into the commit body it writes. Luna applies every item it agrees with and commits one commit for the pass. It may decline an item that would change behaviour or delete a still-needed test. If Luna declines every item, nothing is committed; the pass status is "all declined", there is nothing to judge or merge, and the status goes to stage 5 like any other.
4. Before dispatching `opus-reviewer`, the orchestrator squashes the pass worktree's commits into one commit, keeping the declined-items list in the body. `opus-reviewer` judges that commit against the fix list. The brief identifies a stage-4b polish-pass commit and includes the list. Its attack covers changed behaviour, weakened tests or deleted still-needed tests, and changes beyond the list. A declined item with a sound reason is not a blocker; a silently skipped item is. FIX goes back to the same `codex` in the same worktree; after a FIX round, squash the pass worktree's commits into one commit again, keeping the declined-items list in the body, before re-review. The commit Opus approves is the commit that merges.
5. APPROVE means merge with `git merge --ff-only`. If `git merge --ff-only` fails, stop and ask the user; never fall back to a normal merge. If Opus still says FIX after one fix round, the orchestrator may drop the pass and tell the user in one line. A merged polish commit may be reverted if it later causes a stage-5 blocker or test failure; for a test failure, revert only if it reproduces with that commit and not without it. Tell the user in one line; if a revert conflicts, stop and ask the user. A revert changes the diff, so stage 5 gets a delta re-review. After a merge or drop, remove that pass's worktree and branch. Task commits are never dropped this way.

Keep both polish fix lists for stage 5. Every stage-5 brief, in the first pass and in each delta, carries each list with its status (applied, with any declined items; skipped; dropped; or reverted), labelled as authorised stage-4b scope. Changes traceable to a numbered polish item remain in scope and are still attacked for correctness.

**5. Branch review — Fable + Astra + Grok.** Once every task is approved *and merged* and stage 4b is done: dispatch `fable`, `astra` and `guest-reviewer` in one message so they run in parallel, each given the spec, the final plan, the base revision, and the integrated diff, including the polish commits. With `SHIPYARD_SECURITY_SCAN` set, dispatch `mythos` in that same message with the same inputs. All of them are adversarial; verdicts are MERGE AS-IS / MERGE WITH FIXES / DO NOT MERGE, derived from blockers the same way. `MERGE AS-IS` means no blockers.

This stage gates the branch's *final* state, so a verdict dies the moment the diff changes. Do not round-cap stage 5. The repair loop, when any reviewer reports a blocker you accept:

1. Tag the repair brief and dispatch it to `codex` (`EASY`), `guest-implementer` (`ROUTINE`) or `sonnet-implementer` (`HARD`) in a fresh worktree **you create and seed first**, as in stage 3, where it commits. Same rule as stage 1: `EASY` only if the change is fully prescribed, follows a pattern already in the codebase, and leaves no open decision about API shape, data format, security, compatibility, concurrency or migration; `ROUTINE` if it leaves none of those decisions open but is not fully prescribed or has no pattern to copy; otherwise `HARD`.
2. `opus-reviewer` on that commit, with the findings as the step it implements. FIX goes back to the same agent; APPROVE lets you merge it into the branch.
3. Regenerate the integrated diff and **re-dispatch every enabled reviewer as a delta**, not only the ones who complained: previous review, new diff, what was fixed. Not a first-pass re-read of accepted text.

**Final test run.** Once every enabled reviewer has an empty blocker list, the orchestrator itself runs the project's full test suite on the working branch, using the command documented in the base revision's CLAUDE.md / AGENTS.md / README / CI config (or asks the user at the start if none is documented). If the working branch changes the file the command comes from, call that out to stage-5 reviewers as a finding to examine. A failure is a blocker. It goes through the repair loop above (repair, review, delta re-review of every enabled stage-5 reviewer), then the suite runs again. A failure caused by a polish commit may instead be resolved by reverting that commit, but only if it reproduces with the commit and not without it; follow the revert rules in stage 4b, then delta re-review and rerun the suite. If the project has no test suite, tell the user in one line; that is not a pass to claim silently.

**The PR opens only when every enabled reviewer has an empty blocker list on the current diff and the full test suite has passed on that same diff — or, for a project with no test suite, the user has been told so in one line.** Nothing else clears the gate. `MERGE WITH FIXES` (non-empty blockers) obliges you to apply the fixes and loop. Nits on a `MERGE AS-IS` (or a mislabeled `MERGE WITH FIXES` with empty blockers) are reported once and do not block. If you think a blocker should be declined, the pipeline *stops there*: report it to the user and wait. Agreeing that a finding is wrong does not convert a verdict, so say plainly that they have two ways to resume — tell you to re-dispatch with that finding excluded from the gate, or tell you to bypass Shipyard and open the PR as it stands. Never pick either one for them. That bypass is for declining a blocker, not for escaping nits.

## Red flags

- Dispatching an implementer while a plan reviewer still has blockers, except the round-2 residual-nit path → stop, review first. Fable and Astra alone are the gate only when `SHIPYARD_NO_GROK` is set and `ANTIGRAVITY_ENABLED` is not.
- Full re-review of a plan or branch after a fold → that is a delta. A new first pass is how nits regenerate.
- Starting a third stage-2 round on your own → stop and ask.
- Folding nits as if they were blockers, or looping until findings are zero → the gate is blockers.
- Sending a task to any implementer but the one its tag names (`EASY` → `codex`, `ROUTINE` → `guest-implementer`, `HARD` → `sonnet-implementer`; `ROUTINE` → `codex` only when `SHIPYARD_NO_GROK` is set and `ANTIGRAVITY_ENABLED` is not) → the tag exists to pick the model; follow it.
- Merging a Sonnet worktree without checking the main checkout for stray writes → it has no sandbox; the check is the only gate.
- Deciding for yourself that Grok is "not needed" → `SHIPYARD_NO_GROK` is the user's switch, not your call (and it is ignored under `ANTIGRAVITY_ENABLED`).
- Opening the PR with `SHIPYARD_SECURITY_SCAN` set but no `mythos` pass on the current diff → the scan is a stage-5 gate once enabled; an unavailable model stops the pipeline, it doesn't skip the scan.
- Merging a worktree branch Opus hasn't approved → not done.
- Sequential implementer dispatches for independent tasks → wasted wall-clock; one message, many calls.
- Dispatching an implementer with `isolation: "worktree"` instead of a path you created → the harness picks the location, so you cannot seed it, cannot honour a project's worktree convention, and cannot know what `--sandbox workspace` is actually confining.
- A dispatch prompt that says "as discussed above" → no subagent has an above.
- A brief that pastes file bodies a CLI wrapper could read itself → paths and `file:line` anchors instead; you are billed for every quote, twice.
- Folding a blocker whose `file:line` you never opened → the citation is the finding; one that points nowhere is a hallucination, not a gate.
- A wrapper whose result is "the CLI is running in the background, I will wait" → its turn already ended and nothing collected the run. Do not re-dispatch it: find the PID, arm a waiter that *exits* (`Bash` with `run_in_background` and `until ! kill -0 <PID> 2>/dev/null; do sleep 10; done`), and `SendMessage` the same agent to collect and commit when it fires.
- Opening the PR without the stage-5 branch review → the per-task reviews never saw the integrated diff.
- Opening the PR without stage 4b's two passes → each lister runs, except skip test audit only when no tests changed; skip an apply step only for an empty list, saying each skip in one line.
- Dispatching `sol` in boatyard → boatyard uses `simplifier` for test audit; the cast is per mode.
- Skipping the final full test run, or opening the PR on a red or unrun suite → reviewers must be clear and the suite green on the same diff.
- Letting a lister or the polish judge edit files → they list and judge; `codex` applies.
- Opening the PR on a diff that changed after the last stage-5 pass → the verdict you are citing was about a different branch.
- Opening the PR while a stage-5 reviewer still has blockers → nits do not block; blockers do.
- Writing the plan inline instead of dispatching `astra`, or a branch review inline instead of dispatching `fable` and `astra` → wrong model, and no fresh context.
- Reusing the stage-1 planning run for stage 2's Astra review (a resumed codex session, or pasting the planner's reasoning into the review brief) → the reviewer then shares the author's blind spot, which is the whole thing stage 2 exists to break.
