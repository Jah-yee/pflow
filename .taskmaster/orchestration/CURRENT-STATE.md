# CURRENT-STATE.md (last verified: 2026-10-11, session-13 close — main @ f68680ba)

_Living state header — the ONE mandatory session-start read (~80-line budget; state + pointers
only). Rewritten at close/park (ORCHESTRATION "Artifacts and ownership"); work done outside a
numbered session appends a dated `## Outside-session — folded at next rewrite` block at the top,
which the next boot folds. How-it-got-here: latest `sessions/session-NN.md` (+ the previous three
braindumps); routing: `sessions/INDEX.md`. Every claim here is a pointer to verify, not a fact._

## Process

- Root `CLAUDE.md` Code Quality carries the user's governing lens VERBATIM; quote it in every packet.
- Session-13 ran Fable, then **Opus** from the user's `/model` swap (saved as default); routing table unchanged (DECISIONS #24).
- **DECISIONS #5 exception 2 (new, s13):** the close ritual commits + pushes `.taskmaster/orchestration/` itself.
- Session-13's night grant is CLOSED (narrowed by the user to "finish what we started" at ~521k tokens, then drained).

## In flight — nothing live; ONE planned task parked (worktree kept, branch LOCAL, not pushed)

- **Task 120** (declared input types honoured) — `feat/task-120-declared-input-types` @ `c2036d23`. Plan `bd6583ec` (7 phases,
  two mid-task reviews, 7-lens codex plan battery); **CP-1 RULED** (`c2036d23`: R1 "Invalid input value", R2 source clause
  everywhere, R3, R5 80 chars, R6). Spec decisions (a)–(h) + (i)–(iii) DECIDED. Its gate **Task 181 is MERGED** (`f68680ba`,
  task-review present). NEXT: launch an Opus task-orchestrator, implement-from-plan; first act merges `origin/main` (gets 181)
  and P0 re-verifies the seven 181 shapes in plan §0 against 181's task-review "Integration Points". Embedded web-phase
  checkpoint → user. Carrier = `__pflow_input_types__` on the shared store (ADR-0017, amended s13).

## Next session, recommended order (NOT yet user-agreed)

1. **Task 120 build** (above).
2. **Re-measure + file the s13 lane residuals** (each listed in its PR body, NOT re-run by me): the YAML-boolean-key object
   input into a sub-workflow raises `TypeError` (PR #770; likely #742 / Task 120 territory) · `WorkflowManager.exists`
   accepts any string, the web UI's `/api/run` is a second resolver, extension-case mismatch (PR #771) · `Registry.save(
   metadata_updates=)` dead, stdio "increase the timeout" hint, dead `add` syntax in `examples/mcp-http/` (PR #760) ·
   warm memo cache lacks a new interface key (`${step.timeout}`), progress line says "exit code -1" for a timeout (PR #759)
   · `core/exceptions.py:1207` stale "mask-only" docstring (PR #770) · eager `httpx` in `cli/commands/ui.py:22`, eager
   `claude_agent_sdk` in `claude_backend.py:24` (PR #764) · 181's follow-ups (#683's comment clause: batch preview shows
   `true`/`null`; Py↔TS template differential test; `pflow mcp describe` splits hyphenated servers) — task-review.
3. Lane-B fill: #755 · #756 · #728 (widened s13) · #729 · #722 · #716 · #748 · #749 · #768 (on-error bypass, s13).
4. #741 (changelog PR links) before the next release.

## Decisions pending the user

- **#769** — ONE encoding rule for shell bindings: (a) strict UTF-8 everywhere (stdin today) or (b) `surrogateescape`
  everywhere (env today). Recommendation in the issue: decide after measuring whether any producer emits surrogate-escaped text.
- **#767** — Python 3.14 third-party `SyntaxWarning` on stderr once per fresh environment: suppress in `cli_main`, or accept.
- **181 ruled-text adjustment** (agent, 2/5): §4d tail reworded because the ruled `('"#main"')` is a JS SyntaxError — ratify.
- **s13 incident** — Task 181's tests overwrote the user's `~/.pflow` chrome-devtools entry; the agent repaired HOME itself.
  Current config verified working (read-only); the before-image was lost at teardown. User to eyeball the entry; rule on
  the proposed implementer-def rule (session-13 braindump).
- Carried: **#692** (`pflow delete`). RECURRENCE promotions to ratify or revert (s10, s11, s12, s13 — see RECURRENCE).
- #763 (concurrent resume of one token) — RULED s13: stays an issue, low priority, task-vs-lane decided at pick-up.

## Do not re-raise (declined, with the trigger that reopens each)

- pr-closer / RELEASE-BLOCK / batched releases / docs-PR lane / automatic PR review / cross-task knowledge
  base — never (DECISIONS #5/#31).
- **#665** (`save --force` data loss) — reopens when saved-library use becomes real.
- Task 179 final-step loop escalation pause — ruled (b). #624 shape 2 · retired gemini ids · shell lint / H1 check /
  PR-title gate / searcher eval harness / `Blocked by:` field / DECISIONS index split / agent-file fact checker.
- Task 111 default-3 batch limit — WITHDRAWN. Task 182 (linting) — `then`, no planner yet.
- #743 (declared OUTPUT types) and #742 (YAML literal re-typing) are OUT of Task 120 by ruling.
- Loudkult report items declined s13: deprecation window for breaking contract changes (no users); `-p` streaming several
  outputs (#281, by design); `PFLOW_HOME` (`HOME=` works — reopens if a sandbox cannot set HOME); a CI-only validator
  package (`uvx pflow --validate-only` is one); a validated-workflow cache (parse+validate is ~54 ms).
- Execution-start MCP auto-sync — DELETED by ruling (#751, reverses #612); `pflow mcp add` syncs. Not coming back.

## Regime facts (dated — re-measure, never inherit)

- 2026-10-11: `--validate-only` one shell step 0.29–0.30 s, `--version` 0.19–0.21 s (load ~6) — was 2.1–2.3 s on 10-10.
- 2026-10-11: Task-159 baseline 75 pass / 13 drift (#680; +1 from #759 guide text, +1 from #771) — re-record pending.
- 2026-10-11: open issues 165; push CI on `f68680ba` was in progress at close — verify at boot.
- Windows flakes seen: `test_stdin_no_hang_integration`, `test_cache.py::test_concurrent_access`, `tests-windows-mcp-smoke`
  (timeouts, run 38090920552 on main) — each green on one re-run.

## Watch list (non-obvious, easy to miss)

- **Task 118 Part 2 is breaking** for old-form shell/code bodies, including the user's saved library — converting is THEIRS.
- **Shell timeout (#758):** POSIX TERM → 5 s → KILL; Windows immediate tree kill (ADR-0013 amended). macOS `/bin/sh`
  drops a TERM trap when the last line is a single command (it execs) — the docs show the safe form.
- **181's tests wrote to the real `~/.pflow` until its gate fixed the fixture** — any test touching MCP config must run
  under the isolated test home; packets for MCP-touching work say so until a def rule exists.
- MCP stdio shims + `anyio>=4.5` exist only for Task 178 to delete — never port them.
- `stash@{0}` (Task 125 WIP) is the user's — no agent ever runs `git stash`.
- Agent defs/skills in the MAIN checkout are read live by agents launched from the session — committed or not.
- User's HOME/machine leftovers (theirs to delete): `~/.pflow/workflows/dogfood-s12-*` (3), many traces in `~/.pflow/debug`,
  `/tmp/falsify553-*` (7 paths, a falsifier's denied cleanup).
