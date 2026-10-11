# Task 184 — progress log

Append-only. Spec: `../task-184.md` · Plan: `implementation-plan.md` · Checkpoint: `show-before-code.md`.

## [2026-10-11 19:10] task-planner (Fable) — planning complete; CP-1 parked on the user
- Did: investigated on `05884642` (== origin/main), wrote `implementation-plan.md` + `show-before-code.md` (BEFORE executed on
  the real CLI/MCP with an isolated HOME; eleven commands + four MCP calls, saved under the session scratchpad `before/`),
  corrected the spec in place, self-reviewed the plan (deep-review plan mode, dispositions below).
- Changed: `task-184.md` (header; runner cites `907-913`/`428-435` → `946-952`/`446-453` — read; `errors` always a list;
  identity keyed on the streamed trace; MCP failure stays a raise; `to_display_dict` note → `to_output_dict` (#776 merged
  2026-10-11, read via `gh issue view 776`); the probe caller of `_build_error_text` (`execution_service.py:791`, read);
  the paused ERROR diagnostic (`runner.py:912` + `exceptions.py:1435`, read); `## Open questions` → `## Resolved at start`;
  References re-cited). `implementation/` created.
- Verified: every §1 cite in the plan by reading; every issue symptom by execution (#695 success JSON has no identity; #699
  HTTP-timeout failure has no `❌` line and no `metrics`, action failure shows `nodes_executed` 2 vs `execution.nodes_executed` 1;
  #737 resumed-then-denied prints `Steps completed: 0 of 3.` with no lineage, resumed-then-failed JSON lacks `resumed_from`;
  MCP failure text has `Trace:` only, no id/metrics). `trace_path` readable pre-finalize: read `workflow_trace.py:1161-1170`,
  `:990`, `:996`, `:1129`. | Assumed: none load-bearing left; the searcher-side gap "do cached nodes record a metrics timing"
  is moot once `metrics.workflow.nodes_executed` is removed.
- Deviations/surprises (vs spec): (1) the spec's "13 builders deleted or reduced" — one keeps a thin twin: the `registry_run`
  probe (#748) calls `_build_error_text`; the plan gives it `format_error_text` built from the shared section functions.
  (2) `#754`'s issue comment said "keep" the no-`execution_id`-on-non-resumable-failure pin (`test_resume_cli.py:996-1005`); D1
  (identity on every status) supersedes it — the test flips to presence of `execution_id` + absence of `resume_command`.
  (3) The `-p`/JSON-mode stderr rules are inconsistent today per status; the plan proposes one tier table (CP-1 Q1/Q4) rather
  than preserving each exception. (4) `metrics.workflow.nodes_executed` (inside the `metrics` block, = `len(node_timings)`) is
  the same attempted count under D2's one-name rule — removed at its source (`core/metrics.py:316`; `get_summary` has no
  other consumer than the three builders). (5) Pre-execution exception documents (no `ExecutionResult`) stay a separate,
  shrunken path — the spec's "no other code path assembles a run-ending dict" is read as "…for a run that happened".
- Self-checks: fully happy with the shape; the one place I expect friction is P1's "no shims — bundle the test moves and gate
  on `tests/test_execution` only" (the tree is import-red between P1 and P2 by design; the orchestrator should not run
  `make test` as P1's gate). test-reflect: not run — planning, no tests written.
- Test inventory the plan relies on (searcher, read-only, classes A keep / B reverse / C re-target / D exact text):
  B — `test_metrics_integration.py:179-180,189,697,732,742,878-879` (top-level/metrics `nodes_executed`), `test_resume_cli.py:1004`
  (`execution_id` absent on output-resolution failure), `test_paused_cli.py:112,119-123,166,555-556` (`paused_node_id`/`gate_request`),
  `test_core/test_metrics.py:85`, MCP `paused_node_id:` line (`test_execution_workflow.py:310`, `test_cli_mcp_parity.py:285`).
  C — all of `test_success_formatter.py` (37 `format_success_as_text` calls, 7 `format_execution_success` calls), all of
  `test_error_formatter.py`, `test_resume_engine.py:497,506,512,515,842-845`, `test_direct_execution_helpers.py:476,515,537,565,587`,
  `test_agent_ux_fixes.py:53-125,426,449`, `test_registry_run_mcp.py:251`, `test_approval_gate_cli.py:154-159`,
  `test_unified_error_output.py:26` (exception path — keeps `format_error_json(exception=)`), `test_workflow_output_handling.py`
  (drives the JSON path with a bare `ExecutionResult`).
  D (text that must survive) — `Paused at '<id>'. Resume token: <id> (exit 4)`, `To answer: pflow resume <id> --approve yes|no`,
  `Denied at gate '<id>'` + `stopped cleanly`, `⤷ Resumed from <id> at '<k>' — N upstream step(s) restored`, `Workflow failed after`,
  `Workflow completed`, `Workflow trace saved`, `To resume from the failed step: pflow resume `, MCP `execution_id: ` / `trace_path: ` /
  `resume_command: ` / `status: paused` lines, `Outputs that resolved before the failure:`, `Advisories:` (substring).
  A guards to keep green untouched — `test_json_diagnostic_redaction.py` (incl. the `_PRINTING_TREES` AST ratchet :256),
  `test_text_diagnostic_redaction.py`, `test_progress_streaming_subprocess.py:957,1021,1078,1230`, `test_declared_input_entry_points.py:444,455`,
  `test_child_input_boundary.py:287-294`, `test_paused_cli.py:1025-1044,1098-1129`, `test_approval_gate_cli.py:54-82` (all `--no-trace`).
- Next: main orchestrator relays CP-1 (`show-before-code.md` Q1–Q4) to the user; on ruling, a task orchestrator implements
  P0–P4 from the plan (or the planner is resumed to implement — see handback size call). Resume point: nothing in flight;
  the worktree holds only the committed planning artifacts.

## [2026-10-11 19:25] task-planner (Fable) — plan self-review (plan-mode deep-review, codex fan-out, 6 lenses) — dispositions
- Did: `review-plan`, `review-architecture-fit`, `review-impact-completeness`, `review-silent-failures`,
  `review-feature-interactions`, `review-agent-ux` via `workflows/review/run-review-lenses.pflow.md` (all six produced; report
  `implementation/reviews/plan-review.md`). Every Critical/Warning verified against code by me before folding in.
- #1 Critical (plan, silent-failures) — CONFIRMED: the stream opens in the engine (`engine.py:919 start_streaming`); a compile-time
  failure (missing required input → `prepare_inputs` in `compile_validation.py:164`, after the collector at `runner.py:198-212`)
  leaves `trace_path None` at render time and `finalize()` (`workflow_trace.py:1150`) creates the file afterwards; MCP finalizes
  first (`runner.py:274`). FIX folded: plan §1 bullet + §4.4 ordering (CLI finalizes before building for non-success; success keeps
  build → set_json_output → finalize → emit), P0 test (b) re-targeted to a validator error, P0 (d) + P2-T8 added; spec gains the
  "pre-engine failure still carries identity" line.
- #2 Warning (all six) "never null vs pricing/gate/output nulls" — CONFIRMED (`core/metrics.py:237-246`, ADR-0009, #757): rule made
  field-specific (plan §3.1, P1-T2 pairs omissions with the nulls that must survive; spec + checkpoint wording).
- #3 Warning (five lenses) shared gate rendering could print `To answer:`/bulk hint after a denial — CONFIRMED (`gate_prompt.py:229-236`
  keys on kind/iteration, not status): `gate_lines` is content-only, `answer_lines` PAUSED-only, gate block PAUSED-only; P2-T9 added.
- #4 Warning (three) batch error details vs `-p` — CONFIRMED (`workflow_errors.py:86-93` prints regardless of `-p` today): split into
  `batch_error_details` (must-act on FAILED) and `shell_stderr_block` (summary); tier table + Q1 text + P2-T5 updated.
- #5 Warning (two) `nodes_skipped` counts a gate-stopped `--only` target and "Ran only" lies — CONFIRMED (`success_formatter.py:124-126`,
  `:569`): target excluded from the count; `format_only_indicator` gains a not-ran form; P1-T9 added.
- #6 Warning (plan) guards at the builder, not the adapter — ACCEPTED: P2-T7 (real CLI JSON matrix), P3-T6 (lineage through
  `render_mcp_text` on a real resumed result), `tests-windows` named in §9.
- #7 Warning (agent-ux) MCP paused text loses the step name — CONFIRMED (`workflow_output.py:677` generic arm): PAUSED completion
  line names `gate.node_id`; P3-T5 added.
- #8 Open decision (architecture-fit) `json_output` trailer content changes — ACCEPTED, resolved as "snapshot of the printed
  document, not a versioned sub-contract; no format bump" (plan §3.6; to be restated in the task-review).
- Verified clean (per the report): D1–D4 intact; probe twin justified; Task 117/178/152 trajectories unaffected; resume shares
  the CLI dispatch; partial `result` rule preserved; MCP failure stays a raise.
- Next: unchanged — CP-1 to the user; implementation on ruling.
