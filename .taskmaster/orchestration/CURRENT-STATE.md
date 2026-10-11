# CURRENT-STATE.md (last verified: 2026-10-11, session-14 close + post-close rulings — main @ origin/main)

_Living state header — the ONE mandatory session-start read (~80-line budget; state + pointers
only). Rewritten at close/park (ORCHESTRATION "Artifacts and ownership"); work done outside a
numbered session appends a dated `## Outside-session — folded at next rewrite` block at the top,
which the next boot folds. How-it-got-here: latest `sessions/session-NN.md` (+ the previous three
braindumps); routing: `sessions/INDEX.md`. Every claim here is a pointer to verify, not a fact._

## Process

- Session-14 ran Fable, then **Opus** from the user's `/model` swap (saved as default); routing table unchanged (DECISIONS #24).
- New this session (homes carry them): quote the user only when the wording is operative (role prompt + ORCHESTRATION log
  vocabulary); the user's "close bug classes … resolve all assumptions" + "consolidating seams" instructions (role prompt —
  put them in every packet); concurrency cap 1 build + 3 lanes, nothing new above load ~40 (ORCHESTRATION step 7).
- Post-close (user accepted all pending items): implementer defs (`never git stash`, tests never touch the real HOME), role
  prompt (standing fix instructions, fresh reader for a rewritten spec, a pre-execution closing mechanism is a HYPOTHESIS),
  searcher-offload brief rule — all COMMITTED. Global `~/.local/bin/pflow` reinstalled at 0.16.0 (editable, mcp 1.30).

## In flight — nothing live; TWO parked worktrees (branches LOCAL, not pushed), both RULED

- **Task 184** (One Run Outcome) — `feat/task-184-run-outcome` @ `aa96b450`: Fable plan committed (P0–P4, all Opus; one module
  `execution/formatters/run_outcome.py`; ~30 test files; no engine/trace/web). Spec D1–D4 DECIDED; 8 spec corrections on the
  branch. **CP-1 RULED** (all four as recommended — `scratchpads/session-14/CP-1-RULED.md` in the worktree; the orchestrator
  records it on the branch first). NEXT: Opus task-orchestrator, implement-from-plan; packet adds the F20 note (what `success` means for paused/denied — dogfood
  `scratchpads/session-14/dogfood/verified.md`) and `ui/server.py`'s raw `to_dict()` bodies (#799's sibling list).
- **#799** (batched `child_failure` printed raw) — `fix/issue-799-batch-child-failure-redaction` @ `05884642`, uncommitted fix
  + 4 tests (patch copy `scratchpads/session-14/lane-799-parked.patch`). **RULED B** (split the compactor; the user waived the lane-B engine
  exclusion for the one `workflow_executor.py` call-site line) — park + ruling comments on #799 hold the resume steps.
- ~~#749~~ — CLOSED into **Task 152** (ruled A); 152's spec refreshed against `cf8b7fcb` and moved to `next`; worktree removed.

## Next session, recommended order (NOT yet user-agreed)

1. Launch 184's Opus task-orchestrator (implement-from-plan) and resume #799 as a lane (option B) — both ruled.
2. **#801** (SECURITY: name-only masking prints the value) — lane, after #799 (same redaction seam; #801's value-scrub
   would cover #799's field too — decide whether one lane takes both).
3. **#795** (examples capture net → `baseline-oracle` job or delete) · **#755** (stderr head/tail preview, now unblocked) ·
   **#722** (MCP input blocklist) — parallel-safe fills, Opus lanes.
4. Dogfood classes #802–#807 (#802 with #458 as one lane; #804 carries an open exact-case-env decision, rec (a); #805 has a
   trace-format note → may be task-sized). Evidence comments posted on #675 (raise to medium), #735 (widen), #245, #689,
   #740, #694, #350. Lane residuals recorded in session-14 (e.g. `delete_file.py:183` allow-listed in the remedy ratchet).
5. **Task 152** planner (now `next`; refreshed spec) — then Task 178 (client-era Q1 is the user's); both reshape `mcp_server/`,
   serialize them.
6. Release once the security lanes land (changelog links fixed by #741).

## Decisions pending the user

- #804's open question (exact-case env matching for inputs; rec (a)) — at its pick-up.
- Carried: #692 (`pflow delete`, low, stays open — dogfood re-hit it); PyPI yank — orchestrator's rec NO, not ruled.

## Do not re-raise (declined, with the trigger that reopens each)

- pr-closer / RELEASE-BLOCK / batched releases / docs-PR lane / automatic PR review / cross-task knowledge base — never.
- #665 (`save --force` data loss) — reopens when saved-library use becomes real.
- #697 trace file mode 0644 — declined 2026-10-06; dogfood re-observed it, reopen trigger not met.
- Execution-start MCP auto-sync — DELETED by ruling (#751). An mtime-based test guard (#793) — refuted by concurrent writers.
- Loudkult s13 declines (deprecation windows, `-p` multi-output, `PFLOW_HOME`, CI validator package, validated-workflow cache).
- #743 / #742 stay separate from Task 120 (merged).

## Regime facts (dated — re-measure, never inherit)

- 2026-10-11: suite ~11,550 tests; `baseline-oracle` CI job ~4 min (required); oracle 87/87; examples capture 12/29 drift (#795).
- 2026-10-11: open issues 172. Host load ~7 at close (peaked 86 with 1 build + 3 lanes + 2 offloads).

## Watch list (non-obvious, easy to miss)

- **The test suite redirects HOME for the whole session** (#793 guard): a lane running `git push`/`gh` inside a test-shaped
  env fails the credential helper — push with the normal HOME. Spawns without HOME are refused by the guard.
- **User's machine:** stale uvx env with pflow 0.15.1 + mcp 2.3.0 (`uv cache clean pflow-cli`); registry
  backup before the s14 re-sync at the session scratchpad (`registry.before-resync.json`).
- Task 118 Part 2 is breaking for old-form shell/code bodies in the user's saved library — converting is THEIRS.
- MCP stdio shims + `anyio>=4.5` exist only for Task 178 to delete — never port them.
- `stash@{0}` (Task 125 WIP) is the user's — no agent ever runs `git stash` (in the implementer defs).
- Agent defs/skills in the MAIN checkout are read live by agents launched from the session — committed or not.
