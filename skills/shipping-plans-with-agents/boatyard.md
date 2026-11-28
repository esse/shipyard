# Boatyard

Shipyard with a smaller crew, for work that is neither large nor hard.
Everything in `SKILL.md` holds — worktrees you create and seed, paths not
pasted files, blockers gate and verdict words don't, citation checks,
round caps, delta reviews, stop-and-ask on a declined blocker, the env-var
switches — except the cast below.

| Stage | Shipyard | Boatyard |
|---|---|---|
| 1. Plan | `astra` | `opus` (job 1) |
| 2. Plan review | `fable` + fresh `astra` (+ `grok`) | `fable` + fresh `opus` (job 2) (+ `grok`) |
| 3. Implement | by tag, `ROUTINE` → `guest-implementer` (Hydrogen), `HARD` → `guest-implementer` (Neon) | by tag, no `HARD` |
| 4. Task review | `sol` (task-review job; `opus-reviewer` on fallback or `OPUS_REVIEWS_TASK`) | `sonnet-reviewer` |
| 4b. Test audit | `sol` (test-audit job, Neon) lists → `codex` applies → `opus-reviewer` | same as shipyard |
| 4b. Simplify | `simplifier` (Neon) → `codex` → `opus-reviewer` | same as shipyard |
| 5. Branch review | `fable` + `astra` (+ `mythos`, `grok`) | fresh `opus` (job 3) + `fable` (+ `mythos`, `grok`) |
| 5. Final tests | orchestrator runs the full suite | same as shipyard |

Routing in stage 3: `EASY` → `codex`, `ROUTINE` → `guest-implementer`
(Hydrogen, with its Terra fallback). `OPUS_REVIEWS_TASK` changes nothing here,
since boatyard's task reviewer is Sonnet. `SHIPYARD_SECURITY_SCAN` adds `mythos` to
stage 5, and `SHIPYARD_GROK_REVIEW` adds `grok` to stages 2 and 5, exactly as
in shipyard.

Stage 4b runs exactly as in `SKILL.md`, `sol` and `simplifier` included.
`opus-reviewer` judges both polish commits here too; this is the one boatyard
use of `opus-reviewer`. `sol`'s task-review job is not used in boatyard.
Stage-5 repairs, including final-test-run repairs, are reviewed by
`sonnet-reviewer` in boatyard. The first stage-5 brief and every delta brief
for each enabled boatyard reviewer, including `mythos` and `grok` when enabled, carry
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

- Dispatching `astra`, or `sol` for task review, in boatyard, or `opus-reviewer`
  for anything but a stage-4b polish commit, or `sonnet-reviewer` in shipyard →
  the cast is per mode; follow the table.
- Reusing the planning `opus` run for its stage-2 or stage-5 review → that
  is the author reviewing itself.
- Implementing a `HARD` task in boatyard → escalate to shipyard instead.
