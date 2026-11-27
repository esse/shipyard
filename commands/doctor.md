---
description: Check that the Codex, Antigravity and (when enabled) Grok CLIs actually work for delegation, and that the read-only reviewer gates really deny writes.
allowed-tools: Bash, Read
---

# Shipyard doctor

Verify the pipeline can delegate before it tries to. Run every check, report
each result, and never fix anything — this command diagnoses.

Do the work in a throwaway directory so nothing touches the user's tree:
`d=$(mktemp -d)` in the same Bash call that uses it, and remove it after.

## Codex (Astra, Sol, Luna)

1. **On PATH** — `command -v codex`.
2. **Authenticated** — `codex login status`. Anything other than a logged-in
   line is a failure; do not attempt to log in.
3. **Flags the wrappers pass actually exist** — `codex exec --help`. Pass only
   if the output lists `--sandbox` and `--cd`. Luna runs headless via
   `-c approval_policy="never"`, not `--approve-for-me` (which conflicts with
   `--sandbox` since 0.153 and, alone, auto-approves writes outside the
   workspace). Do not pass `--full-auto`; it was removed in 0.147 and is not
   in the wrappers. Every wrapper also runs Codex "dry" (`mcp_servers={}` plus
   `--disable` for plugins, apps, browser, computer use, image generation and
   skill search): measured ~34% faster and ~30% fewer input tokens. An unknown
   `--disable` name is a hard error, so a renamed feature fails checks 4–6.
4. **Delegation round-trip in a linked worktree**, Luna's exact invocation,
   then a **host** commit — the path the wrapper uses, because
   `workspace-write` cannot write a linked worktree's git index:

   ```bash
   d=$(mktemp -d)
   repo="$d/repo"
   wt="$d/wt"
   git init "$repo"
   git -C "$repo" config user.email "shipyard-doctor@localhost"
   git -C "$repo" config user.name "shipyard-doctor"
   printf 'seed\n' > "$repo/README"
   git -C "$repo" add README
   git -C "$repo" -c commit.gpgsign=false commit -m seed
   git -C "$repo" worktree add "$wt" -b shipyard-doctor
   printf 'Create ok.txt containing OK here, then reply with just: DONE\n' > "$d/p.md"
   codex exec --model gpt-6-luna -c model_reasoning_effort="low" \
       -c 'mcp_servers={}' --disable plugins --disable apps --disable remote_plugin \
       --disable plugin_sharing --disable browser_use --disable browser_use_external \
       --disable computer_use --disable image_generation --disable in_app_browser \
       --disable skill_search --disable skill_mcp_dependency_install \
       --sandbox workspace-write -c approval_policy='"never"' \
       -c sandbox_workspace_write.network_access=true \
       --skip-git-repo-check --cd "$wt" - < "$d/p.md"
   echo "codex_exit=$?"
   cat "$wt/ok.txt" 2>&1
   git -C "$wt" add ok.txt
   git -C "$wt" -c commit.gpgsign=false commit -m 'shipyard-doctor host commit'
   echo "commit_exit=$?"
   git -C "$wt" log -1 --oneline
   git -C "$repo" worktree remove --force "$wt"
   rm -rf "$d"
   ```

   Pass only if Codex replies `DONE`, `ok.txt` contains `OK`, *and* the host
   commit succeeded. A reply without the file means the sandbox flags aren't
   working; a file without a reply means the relay is broken; a file whose
   host commit failed means the wrapper cannot land Luna's work in a linked
   worktree.
5. **Read-only profile accepted** — Astra's form, a trivial prompt returns an
   answer:

   ```bash
   d=$(mktemp -d) && printf 'Reply with just: DONE\n' > "$d/p.md" \
     && cd "$d" && codex exec --model gpt-6.2-astra -c model_reasoning_effort="low" \
       -c 'mcp_servers={}' --disable plugins --disable apps --disable remote_plugin \
       --disable plugin_sharing --disable browser_use --disable browser_use_external \
       --disable computer_use --disable image_generation --disable in_app_browser \
       --disable skill_search --disable skill_mcp_dependency_install \
       --sandbox read-only --skip-git-repo-check - < "$d/p.md" \
     ; echo "exit=$?"; rm -rf "$d"
   ```

6. **Sol's read-only profile accepted** — same form, Sol's model:

   ```bash
   d=$(mktemp -d) && printf 'Reply with just: DONE\n' > "$d/p.md" \
     && cd "$d" && codex exec --model gpt-6.2-sol -c model_reasoning_effort="low" \
       -c 'mcp_servers={}' --disable plugins --disable apps --disable remote_plugin \
       --disable plugin_sharing --disable browser_use --disable browser_use_external \
       --disable computer_use --disable image_generation --disable in_app_browser \
       --disable skill_search --disable skill_mcp_dependency_install \
       --sandbox read-only --skip-git-repo-check - < "$d/p.md" \
     ; echo "exit=$?"; rm -rf "$d"
   ```

## Terra (ROUTINE fallback for guest-implementer)

1. **Terra available** — the fallback model answers; pass if the command
   returns `DONE`:

   ```bash
   d=$(mktemp -d) && printf 'Reply with just: DONE\n' > "$d/p.md" \
     && cd "$d" && codex exec --model gpt-6.1-terra -c model_reasoning_effort="low" \
       -c 'mcp_servers={}' --disable plugins --disable apps --disable remote_plugin \
       --disable plugin_sharing --disable browser_use --disable browser_use_external \
       --disable computer_use --disable image_generation --disable in_app_browser \
       --disable skill_search --disable skill_mcp_dependency_install \
       --sandbox read-only --skip-git-repo-check - < "$d/p.md" \
     ; echo "exit=$?"; rm -rf "$d"
   ```

## Grok (opt-in reviewer)

Skip this section and say so unless `printenv SHIPYARD_GROK_REVIEW` prints a
non-empty value.

1. **On PATH** — `command -v grok`.
2. **Authenticated, and grok-4.7 available** — `grok models`. Fail if
   `grok-4.7` is absent.
3. **Round-trip and sandbox enforced** — the reviewer's exact flags:

   ```bash
   d=$(mktemp -d) && printf 'Reply with just: DONE\n' > "$d/p.md" \
     && grok --prompt-file "$d/p.md" --cwd "$d" --model grok-4.7 --effort low --no-plan \
       --sandbox read-only --tools read_file,list_dir,grep \
       --deny Edit --deny Write --deny Bash --deny MCPTool \
     ; echo "exit=$?"; rm -rf "$d"; tail -1 ~/.grok/sessions/sandbox-events.jsonl
   ```

   Pass means `DONE` came back and the last event is `ProfileApplied` with
   `"enforced": true`. A profile that failed to apply only warns, so the
   event is the check that catches it.
4. **The read-only gate really denies** — the security-critical one. Run
   from the project directory, as one command:

   ```bash
   d=$(mktemp -d) && printf 'Create PROBE-DELETEME.txt containing x in the current directory. Report the exact error if it fails.\n' > "$d/p.md" \
     && grok --prompt-file "$d/p.md" --model grok-4.7 --effort low --no-plan \
       --sandbox read-only --tools read_file,list_dir,grep \
       --deny Edit --deny Write --deny Bash --deny MCPTool \
     ; echo "exit=$?"; ls PROBE-DELETEME.txt 2>&1; rm -rf "$d"
   ```

   **Pass means `ls` says the file does not exist** and grok reported a
   denial. If the file appears, delete it and report a failure loudly: the
   Grok reviewer is not read-only.
5. **MCP is denied** — if `grok mcp list` shows any enabled server, ask grok,
   with the flags above, to actually *call* one of its MCP tools and expect
   `Denied by permission policy: deny rule on mcp`. Do not judge from grok's
   own list of tools. Skip with a note if no server is configured.

## Antigravity (Gemini 4 Neon: guest-implementer and the polish listers)

Always run every check: `guest-implementer` runs Neon for every `ROUTINE`
and `HARD` task, and `sol` (test audit) and `simplifier` list on it.

1. **On PATH, new enough** — `command -v agy` and `agy --version`. Fail
   below 1.5.12, the first release with Gemini 4 Neon.
2. **Signed in** — `agy models` exits 0. Any sign-in works: a Gemini
   subscription login or `GEMINI_API_KEY`. Never print a key.
3. **Model available** — `agy models`
   must list `gemini-4-neon-xhigh` and `gemini-4-neon-low`, the one the
   probes below use.
4. **The listers' read-only gate really denies** — the security-critical
   one, shared by `sol`'s test audit and `simplifier`. Run from the project
   directory with their exact flags:

   ```bash
   agy -p 'Create PROBE-DELETEME.txt containing x in the current directory with your file write tool, then run the shell command: touch PROBE2-DELETEME.txt. Report the exact error for each.' \
     --model gemini-4-neon-low --sandbox --dangerously-skip-permissions \
     --settings '{"permissions":{"deny":["write_file(*)","command(*)","mcp(*)","execute_url(*)"]}}' \
     ; echo "exit=$?"; ls PROBE-DELETEME.txt PROBE2-DELETEME.txt 2>&1
   ```

   **Pass means `ls` finds neither file** and agy reported a deny rule. If
   either appears, delete it and report a failure loudly: the polish
   listers have no read-only gate.
5. **Implementer round-trip and confinement** — the implementer's exact
   flags, minus the toplevel guard (the probe directory is not a git repo). The outside target sits in `$HOME`, because the temp dirs are
   writable by design:

   ```bash
   d=$(mktemp -d) && r=$(cd "$d" && pwd -P) && o="$HOME/shipyard-doctor-outside-$$.txt" \
     && printf '{"permissions":{"allow":["read_file(*)","write_file(%s)","command(*)"],"deny":["mcp(*)","unsandboxed(*)"]}}' "$r" > "$r/.s.json" \
     && cd "$r" && agy -p "Create ok.txt containing OK in the current directory with your file write tool, then run the shell command: touch $o" \
       --model gemini-4-neon-low --sandbox --settings "$r/.s.json" \
     ; echo "exit=$?"; cat "$r/ok.txt" 2>&1; ls "$o" 2>&1; rm -f "$o"; rm -rf "$d"
   ```

   **Pass means `ok.txt` contains `OK` and the outside file does not
   exist.** If it exists, report a failure loudly: the implementer is not
   confined to its worktree. Expect the `touch` to be refused by the
   `unsandboxed(*)` deny rule or by the sandbox itself (`Operation not
   permitted`); a run that ends with `jetski: no output produced` after an
   auto-denied permission is also the gate working, as long as `ok.txt`
   exists.

## Report

One line per check: `PASS` / `FAIL` / `SKIP` with the observed evidence, not a
restatement of the expectation. Then:

- **Every enabled CLI passes** — say the pipeline can run all five stages.
- **Codex fails** — stages 1, 2, 3, 4b and 5 are blocked; the pipeline cannot run.
  Astra writes the plan, so this fails at stage 1, before anything else. Do not
  offer to substitute another model for Astra, Sol or Luna.
- **Only Sol's check fails** — stage-4 task reviews fall back to Opus, and the polish listers lose their fallback: if Neon also fails, stage 4b is blocked. Every other stage still runs.
- **Antigravity fails (checks 1–3)** — `ROUTINE` tasks still run through
  Terra if its check passes, and `HARD` tasks through `sonnet-implementer`.
  If Terra fails too, `ROUTINE` tasks are blocked. The polish
  listers run on gpt-6.2-sol if Sol's check passes.
- **A gate check (4 or 5) fails** — report it loudly. Check 4 failing is a
  hard stop for the Neon polish listers (their Sol fallback still works). Check 5 failing means Neon
  implementer runs are not confined to their worktree; say so plainly, and
  that the orchestrator's main-checkout check after each Neon task is then
  the only gate.
- **Grok fails while `SHIPYARD_GROK_REVIEW` is set (checks 1–2, or 3's
  round-trip)** — the pipeline still runs; stages 2 and 5 go on without
  Grok, with a warning each time. A failed gate check (3's sandbox event,
  4 or 5) is a hard stop for the Grok review, since it would run
  unconfined.
- **A gate check fails while its round-trip passes** — the worst outcome, and
  say so plainly: delegation works, so the pipeline will appear healthy while
  running an agent that is not confined the way its own definition claims.

Never install, update, log in, or change a sandbox config to make a check pass.
