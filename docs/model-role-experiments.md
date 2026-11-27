# Model role experiments

Draft, 25 November 2026. This is a test plan, not a routing change. Keep the
current gates and model pins until a trial clears the decision rules below.

## The questions

1. Which of `EASY`, `ROUTINE`, and `HARD` should Neon implement? Is its
   `xhigh` setting worth using on every task, or only on harder ones?
2. Should Carbon take Grok's **plan-review** seat in shipyard stage 2? The
   current planner is Astra; Grok reviews its plan. Carbon as the **stage-1
   planner** is a separate question.
3. If a model wins in one seat, does the full pipeline still work when the
   winning assignments run together?

The current controls come from [the cast and task tiers](../README.md#the-cast)
and [the dispatch rules](../skills/shipping-plans-with-agents/SKILL.md): Luna
max for `EASY`, Grok 4.7 xhigh for `ROUTINE`, Sonnet 5.5 for `HARD`, Astra
medium for planning, and Grok 4.7 xhigh alongside Fable and a fresh Astra for
shipyard plan and branch review. `ANTIGRAVITY_ENABLED=1` currently changes
three seats together: Grok implementer, Grok reviewer, and Sol's test audit all
become Neon xhigh. Do not use that switch to measure a single seat. Pin each
trial arm explicitly in an isolated evaluation runner; leave production
dispatch unchanged.

## Before scoring a model

- Record the model IDs available from `agy models`, the model ID invoked,
  account tier, CLI version, effort, prompt revision, timeout, date, and price or
  quota consumed. Mark unavailable models as unavailable; never turn a
  fallback run into a score for the requested model.
- Run `/shipyard:doctor`'s round-trip and confinement probes with the exact
  candidate flags. For Carbon and each Neon effort, verify that a read-only
  reviewer cannot write or call MCP tools and that an implementer can write
  only inside its worktree. A failed gate ends that arm before quality trials.
- Freeze a case manifest before seeing candidate outputs. Each case has a
  repository and base SHA, original user spec, reviewed plan or task brief,
  tier assigned under today's rules, relevant tests, and an independent
  acceptance rubric. Use historical tasks whose outcomes were known before
  the trial, plus held-out tasks from other repositories. Exclude tasks the
  candidate may have already seen in a public benchmark or in earlier trial
  prompts where possible.
- Give paired runs identical inputs, tool access, time limit, seeded build
  state, and fresh worktrees. Randomize model order. Do not feed one arm's
  answer, review, or failing test output to another. Use the existing wrapper
  prompt for the seat, changing only provider/model/effort and the minimum
  CLI syntax needed to launch it.
- Hide model names from graders. Run objective tests first; then have a
  reviewer score the diff against the frozen spec and rubric. A human
  adjudicates disputed blockers and security or data-loss findings. Record
  both first-pass results and results after one identical repair opportunity.

The first six cases per arm are a smoke test for the harness and rubric. They
do not count toward a promotion decision. Then run 20 paired cases per tier,
adding blocks of 10 up to 60 when the result is close or uncertain. Balance
each tier across languages, repository sizes, and task shapes; include at
least a quarter with integration or error-path work. Keep the case list and
scoring rules fixed within a block. Estimate paired differences with a
pre-registered bootstrap that resamples by repository, so several tasks from
one codebase do not masquerade as independent evidence. A small sample can
leave a seat undecided.

## Trial 1: implementation tiers

| Tier | Incumbent | Challengers | What this isolates |
| --- | --- | --- | --- |
| `EASY` | Luna max | Neon medium; Hydrogen high; Neon xhigh on a small follow-up only if medium fails | Whether a cheaper/faster Gemini executor can follow a prescribed pattern as reliably as Luna. |
| `ROUTINE` | Grok 4.7 xhigh | Neon high and Neon xhigh | Whether Neon can replace Grok, and whether xhigh buys enough quality over high. |
| `HARD` | Sonnet 5.5 | Neon xhigh; Carbon high as a separate challenger | Whether either Gemini model handles open design decisions without unsafe or incompatible choices. |

Use the *same reviewed plan step* for every arm. Keep its tier fixed even if a
model claims it belongs elsewhere. The primary outcome is an accepted change:
the hidden acceptance checks pass, the changed behavior matches the spec, and
the blinded task reviewer has no valid blocker. Count a run that exceeds the
deadline, escapes its worktree, or silently falls back as a failure. Record
first-pass acceptance, acceptance after one repair, critical regressions,
changed files outside scope, test quality, wall time, tokens, billed cost,
and wrapper failures separately. For `HARD`, score the design decision and
compatibility consequences explicitly, even when the tests pass.

**Routing rule.** A challenger may take a tier only if it has no critical
regression, its paired acceptance rate is no more than five percentage points
below the incumbent with the upper 95% confidence bound on the shortfall also
below five points, and it improves either acceptance or measured cost/latency
without a material regression in the other. For `HARD`, require human review of
every accepted design before any promotion. If the bound does not resolve by
60 cases, keep the incumbent and record the result as inconclusive. Select
the lowest Neon effort that clears the rule; do not infer that xhigh is needed
merely because it was the first Neon setting tried. A single severe safety,
data-loss, or compatibility failure blocks promotion pending investigation.

This trial also measures `EASY` and `ROUTINE` use in boatyard. Do not test
`HARD` inside boatyard: its current contract escalates that task to shipyard.

## Trial 2: Carbon in Grok's review seat

Run two separate paired sets: **stage-2 plan review** and **stage-5 integrated
branch review**. Use Astra-authored plans for the stage-2 set and fixed
reviewed plans plus fixed diffs for stage 5. Test Grok xhigh, Carbon high, and
Neon xhigh as standalone third reviewers. The comparison is between the
unchanged Fable + fresh Astra + Grok panel and the unchanged Fable + fresh
Astra + Carbon panel. Neither candidate sees the other reviewers' findings.
This keeps reviewer diversity and the rest of the gate fixed.

Build each set from at least 24 defective artifacts and 12 clean artifacts.
Defects should include omitted requirements, false repository claims, wrong
task independence, unsafe API or migration choices, misleading tests, and
integration failures. Mix real historical failures with carefully injected
mutations, and keep a clean counterpart so a model cannot pass by rejecting
everything. Include at least eight delta reviews that give the reviewer its
own prior finding and the exact repair; score whether it checks the repair
without reopening accepted text. Extend in blocks of 12 to 60 artifacts if
the result is close.

For every finding, adjudicate whether the cited path and line exist, whether
the defect is real, whether it is a blocker under Shipyard's rubric, and
whether the proposed fix works. Count unique true blockers found by the third
reviewer that Fable and Astra missed, critical blockers missed by the full
panel, false blockers per clean artifact, invalid citations, review time,
cost, and delta-review regressions. Preserve raw outputs and grader notes.

**Seat rule.** Carbon can replace Grok at a stage only if the new panel misses
no critical defect in this set, retains at least the incumbent panel's
incremental true-blocker recall within a five-point 95% confidence bound,
does not increase false blockers by more than 0.1 per artifact, and passes the
read-only gate. Decide stage 2 and stage 5 separately. If only one passes,
do not use one switch that moves both. An unresolved confidence bound means
keep Grok for that stage. Compare Neon here too because the existing
Antigravity mode already gives it this seat, but score it independently of
Neon's implementation results.

## Trial 3: Carbon as the stage-1 planner

This is a separate experiment from replacing Grok. Give Astra medium and
Carbon high the same 20 real shipyard specs and frozen repository revisions.
Compare their plans blind on requirement coverage, verified file claims,
task independence, correct `EASY`/`ROUTINE`/`HARD` tags, implementer-ready
briefs, and valid definitions of done. Adjudicate any proposed API, security,
compatibility, concurrency, or migration choice against the original spec.
On a subset of ten plans per arm, use Sonnet 5.5 as the fixed implementer and the
same external Fable + Grok review panel to measure downstream acceptance and
reviewer repair load. This fixed panel avoids giving Carbon a different
review advantage merely because the author changed. Test fresh self-review
as a separate follow-up before changing the production panel.

Extend the planner set in blocks of ten, up to 60 specs, if results are close.
Promote Carbon as planner only if it has no critical missed requirement or
unsafe design, the upper 95% bound on any downstream acceptance shortfall is
below five percentage points, and it lowers reviewer repair load or improves
downstream acceptance. Otherwise leave Astra in stage 1, with an inconclusive
result if the bound never resolves. If Carbon becomes planner, choose its
stage-2 review panel explicitly; do not silently reuse Carbon in two seats or
remove the fresh-review gate.

## Trial 4: other Gemini seats and pipeline interactions

- **Test audit:** On 20 changed-test diffs, compare Sol xhigh with Neon xhigh
  using [the test-audit rubric](../skills/shipping-plans-with-agents/test-audit.md).
  Score true junk tests found, valid tests wrongly proposed for deletion,
  test-only production seams, and citation accuracy. Any proposal that
  deletes the sole test for a real contract is a critical miss.
- **Whole pipeline:** After provisional seat winners are chosen, replay ten
  held-out feature specs through the complete shipyard or boatyard pipeline
  in disposable repositories. Compare the incumbent configuration and the
  proposed one, including plan review, task review, polish, branch review,
  repairs, and final tests. Score escaped blockers, accepted PR quality,
  total wall time and cost, fallback frequency, and whether each gate ran.
  This catches interactions that isolated seat trials cannot. Do not publish
  these branches or PRs.
- **Provider concentration:** Record where two seats in one review chain use
  the same model or provider. Keep independent fresh context, but evaluate
  the combined panel for correlated misses. Do not call two answers from
  the same model two independent votes.

## Results and decision record

Add `experiments/model-roles/cases.yaml` for the frozen case manifest and
`experiments/model-roles/runs/<date>/` for machine-readable run records when
the runner exists. Each record needs `case_id`, base SHA, pipeline/stage/tier,
model ID and effort, prompt hash, CLI version, sandbox-probe result, elapsed
time, tokens/cost or quota, exit/fallback state, tests, reviewer findings,
adjudicated outcome, and artifact paths. Keep secrets, account data, and
private source out of committed records. Save aggregate tables and the
promotion decision in a dated Markdown report, with the case exclusions and
confidence intervals. Report inconclusive seats as inconclusive.

Only after a decision should routing change. Prefer independent per-seat
model configuration over extending `ANTIGRAVITY_ENABLED`, because that switch
cannot express a result such as “Neon for `ROUTINE`, Carbon for stage 2, Grok
for stage 5.” Update the relevant agent wrappers, skill, README, and doctor
probes together, then run the whole-pipeline trial once more on the exact
new configuration.

### 2026-11-26 quick pass (indicative, no confidence intervals)

There were 15 merged PRs from public repos, 5 per tier. These were chi,
urfave/cli, semver, click, attrs, boltons and more-itertools. Each agent ran
in a history-free repo, the upstream tests were hidden and applied only
after it finished, and a blinded Opus judge graded each diff. Grok had no
balance, so it was not measured. The weekly Gemini quota ran out before
most Gemini arms finished.

| Seat | Result |
| --- | --- |
| `EASY` | Luna max 5/5 accepted; Neon medium 4/4 |
| `ROUTINE` | Neon high 1/1, Neon xhigh 1/2; Grok not run |
| `HARD` | Sonnet 2/5 accepted (judge's design score 3.6/5); Neon xhigh 1/2 (4.5/5); most failures in both were hidden-test details the spec never stated |
| Stage-5 third reviewer | Carbon high and Neon xhigh each caught 6/6 planted defects, with 0 that Fable + Astra (also 6/6) missed; 7 and 13 false blockers against Fable's 3, at 13–18× the wall time |
| Test audit | Sol 5/5 planted junk tests found, 0 wrong deletions; Neon not run |
| Planner | Not compared; Carbon's plans hit the quota |

The implementer confinement probe failed for every Gemini model: under
`--sandbox` with `command(*)`, shell writes reached `$HOME`.

Decision: Neon xhigh takes `ROUTINE` and `HARD`, with Terra and Sonnet as
fallbacks. Grok leaves the pipeline, and the third reviewer seat goes with
it. Planning, plan review, branch review and the test audit stay as they
were. The user accepted the confinement exposure; the orchestrator checks the
main checkout after every Neon task.

### 2026-11-26 follow-up: Gemini as planner and reviewer (Neon xhigh vs Carbon high)

The same cases, now through `GEMINI_API_KEY` (agy `"modelProvider":"gemini"`),
compared only Neon xhigh against Carbon high.

| Seat | Result |
| --- | --- |
| Planner (blind pairwise, Opus judge) | Neon 2, Carbon 2 (semver and click-3884 to Neon; chi-1157 and urfave-2479 to Carbon). Three specs got no pair: Neon hit the 1 h limit on chi-1195 and the API spend rate on click-3877; Carbon failed click-3896 three times and got a 503 on click-3877. Both wrote 17–28K-character plans, 4–5× Astra's, in 10–38 min, and sometimes cut off mid-task. Astra vs Carbon earlier: also 2–2. |
| Stage-2 plan review (one defect planted in each of 7 Astra plans) | Neon caught 7/7 with 13 false blockers, median ~10 min; Carbon 6/6 with 14, median ~14 min, and timed out once at 30 min. Fable and Astra were not run on this set. |
| Stage-5 hard set (6 subtle-bug diffs, 3 clean) | Stopped before any run finished: no reviewer had beaten Fable + Astra so far, and the user judged the seat not worth the wall time. |

Decision: no Gemini planner or reviewer. Astra keeps planning; Fable and
Astra keep stages 2 and 5. Grok returns only as an opt-in third reviewer at
stages 2 and 5 (`SHIPYARD_GROK_REVIEW`), for users who want another lab's
review anyway; it was not re-measured.

### 2026-11-27 provider balance (not measured)

With the orchestrator on Opus 5.5 and the largest plan on Gemini (Ultra),
0.17 moves load off Anthropic without a new trial: the CLI wrappers run on
Haiku instead of inheriting the session model, and the test audit (`sol`)
and `simplifier` list on Neon xhigh, read-only, with gpt-6.2-sol as the
fallback and Opus still judging each polish commit. Task review stays on
Sol (0.16), not Neon, since Neon writes most of the code. Neon's lister
quality is unmeasured; rerun trial 4 for Neon when quota allows.

## Current external facts to verify again at run time

Google's [Antigravity model guide](https://antigravity.google/docs/models)
currently lists Neon at low/medium/high/xhigh, Carbon at low/medium/high,
and Hydrogen at low/medium/high/xhigh; it also documents the account tiers
and Orchestrator pairings. It lists Argon as leaving on 30 November 2026,
so this plan does not spend a new trial budget on Argon. Google's
[Neon announcement](https://antigravity.google/blog/gemini-4-neon-in-google-antigravity)
positions Neon between Carbon and Hydrogen. These are provider descriptions,
not evidence of which Shipyard seat a model should hold. Check model IDs,
access, CLI behavior, and pricing immediately before running the trials.
