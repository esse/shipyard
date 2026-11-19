# Boatyard

Shipyard with a smaller crew, for work that is neither large nor hard.
Everything in `SKILL.md` holds — worktrees you create and seed, paths not
pasted files, blockers gate and verdict words don't, citation checks,
round caps, delta reviews, stop-and-ask on a declined blocker, the env-var
switches — except the cast below.

| Stage | Shipyard | Boatyard |
|---|---|---|
| 1. Plan | `astra` | `opus` (job 1) |
| 2. Plan review | `fable` + fresh `astra` + `guest-reviewer` | `fable` + fresh `opus` (job 2) |
| 3. Implement | by tag, `HARD` → `sonnet-implementer` | by tag, no `HARD` |
| 4. Task review | `opus-reviewer` | `sonnet-reviewer` |
| 4b. Test audit | `sol` lists → `codex` applies → `opus-reviewer` | `simplifier` (test-audit job) lists → `codex` applies → `opus-reviewer` |
| 4b. Simplify | `simplifier` (simplify job) → `codex` → `opus-reviewer` | same as shipyard |
| 5. Branch review | `fable` + `astra` + `guest-reviewer` (+ `mythos`) | fresh `opus` (job 3) + `fable` (+ `mythos`) |
| 5. Final tests | orchestrator runs the full suite | same as shipyard |

Routing in stage 3: `TRIVIAL` → `bonsai-implementer` (`codex` when
`CLAUDE_LOCAL_AVAILABLE` is unset), `EASY` → `codex`, `ROUTINE` →
`guest-implementer` (`codex` when `SHIPYARD_NO_GROK` is set and
`ANTIGRAVITY_ENABLED` is not). `SHIPYARD_NO_GROK` changes nothing else
here — boatyard has no Grok reviewer. `ANTIGRAVITY_ENABLED` only moves
`guest-implementer` onto Gemini 4 Neon, since boatyard has no Grok reviewer
and no Sol. `SHIPYARD_SECURITY_SCAN` adds `mythos` to stage 5 exactly as in
shipyard.

Stage 4b runs exactly as in `SKILL.md`, with `simplifier` in place of `sol`
for the test audit. `opus-reviewer` judges both polish commits here too; this
is the one boatyard use of `opus-reviewer`. Sol is not used in boatyard.
Stage-5 repairs, including final-test-run repairs, are reviewed by
`sonnet-reviewer` in boatyard. The first stage-5 brief and every delta brief
for each enabled boatyard reviewer, including `mythos` when enabled, carry
both polish fix lists and their statuses (applied, with any items Luna
declined identified; skipped; dropped; or reverted), labelled as authorised
stage-4b scope.

The two `opus` reviews are fresh dispatches: the spec and the plan text
(or diff), never the planning run's context. Same reason as Astra in
shipyard — the reviewer must not share the author's blind spot.

**A `HARD` tag means triage was wrong.** If the stage-1 plan, a stage-2
reviewer, or a stage-5 repair says a task is `HARD`, stop boatyard, tell
the user in one line which task and why, and restart in shipyard from
stage 1 with the same spec. Work already merged stays on the branch; give
Astra the branch state as context. Never hand a `HARD` task to a boatyard
implementer.

## Red flags

- Dispatching `astra` or `sol` in boatyard, or `opus-reviewer` for anything
  but a stage-4b polish commit, or `sonnet-reviewer` in shipyard → the cast is
  per mode; follow the table.
- Reusing the planning `opus` run for its stage-2 or stage-5 review → that
  is the author reviewing itself.
- Implementing a `HARD` task in boatyard → escalate to shipyard instead.
