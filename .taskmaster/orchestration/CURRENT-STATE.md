# CURRENT-STATE.md (last verified: 2026-10-08, session-12 close — main @ f78b40a1)

_Living state header — the ONE mandatory session-start read (~80-line budget; state + pointers
only). Rewritten at close/park (ORCHESTRATION "Artifacts and ownership"); work done outside a
numbered session appends a dated `## Outside-session — folded at next rewrite` block at the top,
which the next boot folds. How-it-got-here: latest `sessions/session-NN.md` (+ the previous three
braindumps); routing: `sessions/INDEX.md`. Every claim here is a pointer to verify, not a fact._

## Process

- Root `CLAUDE.md` Code Quality carries the user's governing lens VERBATIM; quote it in every packet.
- Session-12's end-to-end grant is CLOSED. Main orchestrator ran Fable, then **Opus** from the swap (user `/model`,
  saved as default); routing table unchanged (DECISIONS #24).
- Review dispatch changed this session (deep-review SKILL, committed `45e15e2e` + uncommitted spec-mode sentence):
  plan- AND spec-mode reading batteries go through the pflow fan-out on codex; task completion gates add
  `simplicity` + `spec-conformance`.

## In flight — nothing live; two PLANNED tasks parked (worktrees kept, branches LOCAL, not pushed)

- **Task 183** (loop gates "of up to M" + "Approve all remaining") — `feat/task-183-loop-gate-approve-all` @ `9b6354b1`.
  RULED (R1 yes, R2 (a), P4 web phase on **Opus** by the user's word). Branch is behind main by 8+ commits incl. Task
  180's trace 2.9.0 → 183 takes **2.10.0**. Launch an Opus task-orchestrator on the plan; it merges main first.
- **Task 181** (MCP code params + `${x|json}`) — `feat/task-181-mcp-code-params-json` @ `d7383363`. CP-1 RULED (all
  as recommended). Its gate (118 Part 2) is MERGED. P0 re-verifies 118's shipped shapes: `data_flow.step_scope`,
  `body_reference_roots` in `validate_workflow_templates`, web `isCodeBody` (`web/src/utils/format.ts`). Coordinates
  with Task 120 on the `core/templates.resolve` leaf policy.
- Engine seam: 183 and 181 both touch the engine — serialize (183 first: smaller, fully ruled, trace bump).

## Next session, recommended order (NOT yet user-agreed)

1. **User rulings on Task 120's three new decisions (i)–(iii)** (spec `## DECISIONS FOR THE USER`, recommendations
   inline) — then prep-commit the spec + ADR-0017 and launch its **Fable planner** (DECISIONS #24). The spec had
   two review rounds (7 Claude + 6 codex lenses; codex fresh re-read) — ledger `scratchpads/session-12/`.
2. **Task 183 build** (above), then **Task 181 build**.
3. Lane-B fill: #727 (stdin encode before spawn — now unblocked) · #746 (approval preview shows typed env values —
   consent surface) · #728 · #729 · #722 · #716 · #748 · #749 · #741 (changelog workflow, before next release).
4. File Task 180's follow-up candidates after verifying each (`.taskmaster/tasks/task_180/task-review.md`
   follow-ups: web "Resume anyway" when the resume point is gone; replay banner covers the refusal title at
   760×560; failed `--only` prints a resume hint resume rejects; batched host stopped by a child gate resumes as
   "no failed step"; child-file edits invisible to resume; screenshot-tool items).

## Decisions pending the user

- Task 120 (i)–(iii) above. **Task 180 edge**: a run stopped BETWEEN steps (interrupt / escalation), then a step
  inserted right after the last finished one — refuses by the ruled rule, though `--force` would run it (not skip);
  kept refusing (ruled behaviour) — ask whether to relax.
- Carried, never answered: **#692** (`pflow delete <name>` — tonight's dogfood left 3 `dogfood-s12-*` saved
  workflows the CLI cannot remove).
- Promotions to ratify or revert (applied at closes): s10 — kill-by-PID in two defs, the interim sentence, the
  `gh run list --branch` line; s11 — ADR-FORMAT "re-derive every mechanism", lane-implementer "kill shells left in
  the tree"; **s12** — release skill "wait in-turn for the changelog run". RECURRENCE `→ PROPOSED`: never
  `git stash` (severity override, since s09); the `ls`→eza alias (s12, see RECURRENCE).

## Do not re-raise (declined, with the trigger that reopens each)

- pr-closer / RELEASE-BLOCK / batched releases / docs-PR lane / automatic PR review / cross-task knowledge
  base — never (DECISIONS #5/#31).
- **#665** (`save --force` data loss) — reopens when saved-library use becomes real.
- Task 179 final-step loop escalation pause — ruled (b). #624 shape 2 · retired gemini ids · shell lint / H1 check /
  PR-title gate / searcher eval harness / `Blocked by:` field / DECISIONS index split / agent-file fact checker.
- Task 111 default-3 batch limit — WITHDRAWN. Task 182 (linting) — `then`, no planner yet.
- #743 (declared OUTPUT types) and #742 (YAML literal re-typing) are OUT of Task 120 by default — reopen only if
  the user rules them in.

## Regime facts (dated — re-measure, never inherit)

- 2026-10-08: `make test-all-local` 10736 passed (Task 180's merged result); Task-159 baseline 76 pass / 11 drift
  (#680 — re-record after 183's trace bump); open issues 166.
- 2026-10-07/08: two distinct `tests-windows` timing flakes (`test_stdin_no_hang_integration` on a main push;
  `test_cache.py::test_concurrent_access` on PR #726) — each green on one re-run.

## Watch list (non-obvious, easy to miss)

- **Task 118 Part 2 is breaking**: old-form shell/code bodies (`${…}` in a body) fail validation with the fix shown —
  including the user's saved library (`~/.pflow/workflows/`) and skill symlinks; converting is THEIR call. A
  paused/failed run of an old-form workflow resumes only after conversion, with `--force`.
- Resume is now per-step (trace 2.9.0); pre-2.9.0 traces keep the whole-workflow compare, and PR #719's `workflow`-type
  carve-out applies only to traces without `step_identity`.
- The web resume panel renders the server's `errors[0]` verbatim (PR #744) — refusal wording changes need no web edit.
- MCP stdio shims + `anyio>=4.5` exist only for Task 178 to delete — never port them.
- `stash@{0}` (Task 125 WIP) is the user's — no agent ever runs `git stash`.
- Agent defs/skills in the MAIN checkout are read live by agents launched from the session — committed or not.
- User's HOME holds tonight's leftovers (theirs to delete, never an agent's): `~/.pflow/workflows/dogfood-s12-*` (3),
  ~120+ traces in `~/.pflow/debug`, `~/.pflow/reports/{stdin-surrogate,v8-fail,f10-dunder}`.
