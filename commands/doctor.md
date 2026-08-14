---
description: Check that the Codex and Grok CLIs actually work for delegation, and that the read-only reviewer gates really deny writes.
allowed-tools: Bash, Read
---

# Shipyard doctor

Verify the pipeline can delegate before it tries to. Run every check, report
each result, and never fix anything — this command diagnoses.

Do the work in a throwaway directory so nothing touches the user's tree:
`d=$(mktemp -d)` in the same Bash call that uses it, and remove it after.

## Codex (Sol, Luna)

1. **On PATH** — `command -v codex`.
2. **Authenticated** — `codex login status`. Anything other than a logged-in
   line is a failure; do not attempt to log in.
3. **Delegation round-trip**, exercising the exact invocation form the wrappers
   use — prompt on stdin, write-enabled, in the temp dir:

   ```bash
   d=$(mktemp -d) && printf 'Create ok.txt containing OK here, then reply with just: DONE\n' > "$d/p.md" \
     && cd "$d" && codex exec --model gpt-5.6-luna -c model_reasoning_effort="low" \
       --sandbox workspace-write --full-auto --skip-git-repo-check - < "$d/p.md" \
     ; echo "exit=$?"; cat "$d/ok.txt" 2>&1; rm -rf "$d"
   ```

   Pass only if it replies `DONE` *and* `ok.txt` contains `OK`. A reply without
   the file means the sandbox flags aren't working; a file without a reply means
   the relay is broken.
4. **Read-only profile accepted** — same command with `--sandbox read-only` and
   a trivial prompt returns an answer.

## Grok (grok-implementer, grok-reviewer)

Skip this whole section and say so if `printenv SHIPYARD_NO_GROK` prints a
non-empty value — Grok is off for this project, and a missing CLI is then
expected rather than a fault.

1. **On PATH** — `command -v grok`.
2. **Authenticated, and grok-4.6 available** — `grok models`. Fail if the model
   the agents pin is absent from the list.
3. **Delegation round-trip**, the implementer's exact form:

   ```bash
   d=$(mktemp -d) && printf 'Create ok.txt containing OK here, then reply with just: DONE\n' > "$d/p.md" \
     && cd "$d" && grok --prompt-file "$d/p.md" --model grok-4.6 --effort low \
       --always-approve --no-plan --sandbox workspace --deny MCPTool \
     ; echo "exit=$?"; cat "$d/ok.txt" 2>&1; rm -rf "$d"
   ```

   Same pass condition: `DONE` returned and `ok.txt` present.
4. **Sandbox actually enforced** — after that run, the last event in
   `~/.grok/sandbox-events.jsonl` must be `ProfileApplied` with
   `"enforced": true`. A profile that failed to apply only warns, so this is the
   check that catches it:

   ```bash
   tail -1 ~/.grok/sandbox-events.jsonl
   ```

5. **The reviewer's read-only gate really denies** — the security-critical one.
   Run from the project directory, with the reviewer's exact flags, as one
   command so the temp path stays in scope:

   ```bash
   d=$(mktemp -d) && printf 'Create PROBE-DELETEME.txt containing x in the current directory. Report the exact error if it fails.\n' > "$d/p.md" \
     && grok --prompt-file "$d/p.md" --model grok-4.6 --effort low --no-plan \
       --sandbox read-only --tools read_file,list_dir,grep \
       --deny Edit --deny Write --deny Bash --deny MCPTool \
     ; echo "exit=$?"; ls PROBE-DELETEME.txt 2>&1; rm -rf "$d"
   ```

   **Pass means `ls` says the file does not exist** and grok reported a denial
   (`Operation not permitted`, or a `deny rule` message). If the file appears,
   delete it and report a failure loudly: the reviewer is not read-only, so
   stage 2 and stage 5 have no gate.

6. **MCP is denied** — if `grok mcp list` shows any enabled server, confirm the
   deny rule covers it by asking grok, with the reviewer flags above, to
   actually *call* one of its MCP tools. Expect `Denied by permission policy:
   deny rule on mcp`. Do not judge this from grok's own account of which tools
   it has: it lists `use_tool` as available even when the deny rule stops every
   call. Skip with a note if no server is configured.

## Report

One line per check: `PASS` / `FAIL` / `SKIP` with the observed evidence, not a
restatement of the expectation. Then:

- **Both CLIs pass** — say the pipeline can run all five stages.
- **Codex fails** — stages 2 and 3 are blocked; the pipeline cannot run. Do not
  offer to substitute another model for Sol or Luna.
- **Grok fails while enabled** — stages 2, 3 and 5 are blocked. Name
  `SHIPYARD_NO_GROK=1` as the user's choice to run without Grok, and do not set
  it for them.
- **A gate check fails while its round-trip passes** — the worst outcome, and
  say so plainly: delegation works, so the pipeline will appear healthy while
  running an agent that is not confined the way its own definition claims.

Never install, update, log in, or change a sandbox config to make a check pass.
