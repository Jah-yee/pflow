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

## [2026-10-11 20:05] task-orchestrator (Opus) — bootstrap: main merged, CP-1 ruling recorded
- Did: merged `origin/main` `5b39ec21` (clean, no hand resolution — PR #800 remedies/`binding_phrase`, PR #798 real-HOME guard);
  `make install`; recorded the CP-1 ruling (plan header).
- [RULING] CP-1 (owner, 2026-10-11, relayed by the main orchestrator from `scratchpads/session-14/CP-1-RULED.md`): the owner
  accepted every recommendation in `show-before-code.md` — Q1 one `-p` tier rule (summary hidden, must-act always prints);
  Q2 uniform MCP identity block, `paused_node_id:` line and the failure text's 3-error cap dropped; Q3 `errors` always a list;
  Q4 one emission site for `Workflow trace saved:`, before the payload in JSON mode. Plan §2–§4 stand as written.
- Carried into the build (packet): F20 (`success` on paused/denied — escalated, see next entry when ruled); `ui/server.py`'s six
  raw `to_dict()` bodies (note coverage in the task-review, don't widen); #801 (name the per-channel scrub attach site in the
  task-review); #795 may add the Task-170 examples capture to `baseline-oracle` (re-record affected examples if the job exists
  at PR time).
- Ordering predicate: P1 starts only after `gh issue view 799` prints CLOSED, then a second `git merge origin/main`; P1 builds
  on the PRINTING compactor. #799 OPEN at 20:05.
- Next: P0 to implementer I1 (Opus, medium).

## [2026-10-11 22:50] implementer I1 (Opus) — P0: the result carries metrics on the exception path
- Did: `_exception_to_result` gained keyword-only `metrics_collector: Any = None` and passes it as `ExecutionResult(metrics=…)`;
  the one call site in `run()`'s `except Exception` passes `metrics_collector` (still `None` when `_prepare_workflow` raised —
  the collector is created after it, unchanged). The two construction sites now differ only in `success`/`status`/
  `shared_after` source/`diagnostics` (same `trace=`, `metrics=` wiring).
- Changed: `src/pflow/execution/runner.py` (call site ~:263, signature ~:881, construction ~:957 — main moved; re-verified);
  `tests/test_execution/test_runner.py` (new `TestResultCarriesRunMetrics`, 4 tests);
  `tests/test_integration/test_failed_node_invariant.py:707` (one-line fix — see Deviations).
- Verified: tests (a)–(d) green; with the runner diff reverted (`git apply -R`) (a) and (d) FAIL (`metrics is None`) and (b)/(c)
  pass — expected, they pin the boundary and the unchanged normal path. The tests use a `created_collectors` fixture: a
  recording subclass of the real `MetricsCollector` swapped in at `pflow.core.metrics` (behaviour untouched), so (a)/(c)/(d)
  assert `result.metrics is` THE collector the run built and (b) asserts none was ever built. (d) runs under `trace_files` with
  `RunnerConfig(finalize_trace=False)` (the CLI's config): `trace_path is None`, then `finalize()` returns a path that
  `is_file()` and equals `trace_path` — the `None` can't come from a disabled stream. `make check` green; `make test`
  **11569 passed** (baseline 11565 + 4 new). Real surface (HOME → scratchpad): a template-resolution failure via
  `uv run pflow fail.pflow.md` now prints `❌ Workflow failed after 0.020s` (absent before — #699's CLI half lands already) and the
  `--output-format json` document gains `duration_ms`/`metrics`/`total_cost_usd`/`nodes_executed`. Baseline oracle
  `verify.sh` 01-parser-errors (10/10), 02-validator-errors (8/8), 15-run-flag-interactions (5/5) PASS — the five
  `_prepare_workflow` failing cases stay `❌`-less as §1 predicted. | Assumed: nothing else in the baseline moves (only those
  three dirs run; the full `verify.sh` is the completion gate's).
- Deviations/surprises: (1) **Plan P0 (a)'s suggested fixture is wrong:** a `code` step that raises does NOT reach
  `_exception_to_result` — the node converts it to an `error` action and the run returns through the normal path (proved by the
  revert run: the code-raise variant passed with the fix reverted). Used a strict template-resolution failure
  (`${first.stdout.b}` on non-matching JSON → `ValueError` "Template Resolution Failed" out of the engine) — #699's own example,
  deterministic, no network (the plan's other option, the HTTP timeout, also reaches the exception path but costs 1s and a
  routable-blackhole assumption). The existing `test_node_valueerror_categorized_as_execution_failure` docstring
  (test_runner.py ~:771) claims that code-raise goes through `_exception_to_result` — stale; NOT edited (outside P0's ask), flag
  for P1/P2 test rewrites. (2) **Plan P0 (d)'s "missing required input" fixture must not reference the input in a shell
  `command`** — `echo ${topic}` is a validator error (shell commands are plain sh) and fails in `_prepare_workflow`, no collector;
  used `env: {T: ${topic}}`. (3) **File outside P0's stated area:** `tests/test_integration/test_failed_node_invariant.py:707`
  went red — it called `result.metrics.get_summary()` with no `llm_calls` arg, a latent bug in a branch that was dead while the
  exception path dropped metrics. Fixed to mirror production (`get_summary(result.trace.collect_llm_calls())`, the
  `error_formatter.py:51-53` shape) with an `assert result.metrics is not None` so the branch can't go dead again. One line, no
  behaviour change; reported here because the plan's file list didn't name it. (4) P0 is NOT invisible to users: the CLI failure
  path already reads `result.metrics` (`run.py` `_emit_failure_tag` + `output_error(metrics_collector=…)`), so the `❌` line and
  JSON metrics block appear on CLI exception failures from this phase on (P1/P2 re-home the rendering). MCP's
  `_build_error_text` does not read metrics (`metrics_summary=None`), so MCP failure text is unchanged until P3. No existing test pinned their absence.
- Self-checks: fully happy — doubts raised: whether (b)/(c) are padding (they pass with and without the fix). Kept: (b) is the
  plan-mandated boundary pin (a future "create the collector earlier" change would flip the baseline's five cases) and (c) is
  the `is`-identity half the plan asks for; neither duplicates an existing test (`test_successful_workflow_runs_through_full_pipeline`
  only asserts `metrics is not None`). The `# type: ignore[valid-type,misc]` on the dynamic subclass carries a coded reason.
  test-reflect: not needed — (d)'s state assertion is paired with a real-file `finalize()` under `trace_files`, so a disabled
  or never-opened stream can't fake-pass it; (a)/(d) were proven to fail on the reverted runner.
  Follow-up (orchestrator-directed): doubt → fixed: kwarg made required (`metrics_collector` keyword-only, no default, so a new
  call site cannot silently drop metrics); direct callers `test_runner.py:681` and `test_cli/test_agent_ux_fixes.py:398` pass `None`.
- Next: P1 — gated on #799 CLOSED + a second `git merge origin/main` (orchestrator).

## [2026-10-11 22:58] task-orchestrator (Opus) — P0 accepted + committed; PARKED on #799 + F20 escalation
- Did: verified I1's P0 handback — read the diff + log entry; my own gate on the tree: `make check` green, `make test` 11569
  passed (baseline 11565 + 4). Loose-ends round: I1 raised that the `metrics_collector=None` default lets a future call site
  silently drop metrics again (the #699 class) → ruled (1/5, reversible): kwarg made REQUIRED keyword-only; direct-call tests
  pass `None` explicitly; runner/invariant/agent-ux tests 115 passed, `make check` green. Committed `9f6cb424`.
- Accepted deviations: plan P0 (a)'s `code`-raise fixture never reaches `_exception_to_result` (node converts to an `error`
  action) → template-resolution failure used; (d) routes the missing input via `env:`; `test_failed_node_invariant.py:707` latent
  `get_summary()` arity bug fixed (branch was dead while metrics were dropped). Carry to P1/P2: the stale docstring of
  `test_node_valueerror_categorized_as_execution_failure` (`test_runner.py` ~:771) claims code-raise uses `_exception_to_result`.
- Note for P2's baseline step: from P0 on, CLI exception failures already print `❌ Workflow failed after Xs` and carry JSON
  metrics (the old renderers read `result.metrics`); `verify.sh` 01/02/15 still PASS (I1).
- ESCALATED (3/5) F20 — what `success` means on paused/denied outcome documents. Facts: today both `success: false`
  (pinned `test_paused_cli.py:110`, `test_approval_gate_cli.py:72`); `docs/reference/cli/index.mdx:331` "`true` if workflow
  completed, `false` if failed"; `guide/features/approval.md:12` deny "stops cleanly (exit 3) — not a failure"; plan §3.3
  `success = result.success`. Options: A `success` ⇔ the run completed (true iff status ∈ {success, degraded} ⇔ exit 0); paused/
  denied stay false, `status` says why; zero code change, two doc lines reworded in P4. B `success: true` on denied (clean
  stop) — contradicts exit 3, the absent `result`, and the denied `errors` list. C drop `success` — contradicts D1. Recommend A.
- Ordering predicate: #799 OPEN at 22:58 (no PR open yet). P0 done 22:50 → the 90-minute fail-closed mark is 00:20.
- RESUME POINT (exact): on resume with (1) #799 CLOSED and (2) the F20 ruling: `git merge origin/main` in this worktree →
  `make check` + `make test` green → record F20 ruling here (+ spec/plan line if not A) → resume I1 (same agent, Opus, effort
  high) with P1, building `run_outcome.py` on #799's PRINTING compactor; P1's gate is the plan's narrower command
  (`uv run pytest tests/test_execution tests/test_core/test_metrics.py tests/test_runtime/test_resume_engine.py`) — confirm it
  runs green at P1's end (the tree is import-red in `cli/`/`mcp_server/` until P2/P3 by plan design; do NOT commit P1 alone
  — the mid-task review (impact-completeness + silent-failures) runs on the uncommitted P1 diff, then P2+P3 bundle).
  Nothing in flight; tree clean at `9f6cb424` except this entry.

## [2026-10-11 23:40] task-orchestrator (Opus) — unparked: #799 merged, F20 ruled, main merged again
- Did: read the main orchestrator's addendum (`scratchpads/session-15/addendum-p1.md`); `git merge origin/main` `93798a80`
  (#809 = #799, #808 = #755; clean, no hand resolution); `make install`; `make check` green; `make test` 11586 passed.
- [RULING] F20 → A (user, 2026-10-11): `success` = the run completed (true iff exit 0); paused/denied stay `false`, `status`
  says why; no code change; P4 rewords `docs/reference/cli/index.mdx:331` + `guide/features/approval.md:12`. Plan header updated.
- Claims verified: (1) #755's fifth head-only site — READ `success_formatter.py:638-641` (`stderr[:300]` + `...`) and
  `core/diagnostic_render.py:733 head_tail_preview` → in scope for P1 (the function moves into `run_outcome.py`); PR body states
  it. (2) #799 compactor split — printing names unchanged (`compact_batch_error_detail`, `compact_batch_output_value`), the raw
  `archive_batch_output_value` is the runtime's only — the `git mv` carries the printing call sites as-is. (3) #799 Residual 1
  (raw `child_failure` via `-o each.errors`, declared `${each.errors}`, child batch output in a successful parent) — scope note
  for the task-review as a member of #801's whole-document pass; not built.
- Text-tier observations (addendum, consumer report) — evaluated against ruled Q1: (a) warnings print after the error block, so
  `tail -3` shows a warning, not the cause → a one-line ORDER choice inside `render_cli_stderr` (P2): carried to P2's brief —
  warnings/advisories render BEFORE the errors block on FAILED; logged when built. (b) shell-failure text repeats the reason
  (headline + `Stderr:`) with `Env:` between → that is `format_diagnostic`'s rendering of ONE diagnostic (`core/diagnostic_render.py`),
  not a separable renderer section → design choice, task-review note, not built. The resume hint on a no-side-effect workflow
  is `has_resumable_step()` policy (the one resumability suppressor) → task-review note, not built.
- Next: resume I1 (Opus, high) with P1.

## [2026-10-12 00:13] implementer I1b (Opus, high) — P1 the builder + unit guards
- Did: `git mv success_formatter.py → run_outcome.py`; `RunOutcome` (+ `exit_code` property over `EXIT_CODES`), `build_run_outcome`
  per §3 (identity keyed on `trace.trace_path`, status normalization, `errors` always a list, `execution` for every status built
  from `build_execution_steps`, `gate` paused/denied, `resume_command` paused/resumable-failure); §4.1 section functions moved in
  (`completion_line`, `mode_lines`, `errors_block`, `diagnostic_sections`, `gate_lines`, `answer_lines`, `resolved_outputs_note`,
  `identity_lines`, `format_cost_summary_lines`, `format_only_indicator(…, *, ran)`, `format_resume_indicator`,
  `format_stderr_warnings` → `head_tail_preview` (#755), `_append_outputs`); `format_error_text` + probe repointed
  (`execution_service.py` ~:787, the one call); `error_formatter.py` deleted; `core/metrics.py` `"nodes_executed": len(node_timings)` deleted.
- Changed: `src/pflow/execution/formatters/{run_outcome.py (R from success_formatter.py), error_formatter.py (D), __init__.py (comment)}`,
  `src/pflow/core/metrics.py`, `src/pflow/mcp_server/services/execution_service.py` (probe call only);
  tests: `tests/test_execution/formatters/test_run_outcome.py` (R from test_success_formatter.py, rewritten; folds the kept parts of
  `test_error_formatter.py` (D)), `tests/test_runtime/test_resume_engine.py`, `tests/test_core/test_metrics.py`,
  `tests/test_mcp_server/test_registry_run_mcp.py`, `tests/test_cli/test_agent_ux_fixes.py` (two `_build_error_text` tests MOVED out),
  `tests/test_execution/test_runner.py` (stale docstring fixed, per P0 carry).
- Verified: P1 gate `uv run pytest tests/test_execution tests/test_core/test_metrics.py tests/test_runtime/test_resume_engine.py
  tests/test_mcp_server/test_registry_run_mcp.py` + both AST ratchets (`test_printed_documents_never_serialize_a_diagnostic_raw`,
  `test_only_the_runtime_takes_the_raw_batch_compactor` — `test_json_diagnostic_redaction.py` COLLECTS: `pflow.cli.main` still imports,
  every old-name import in `cli/`/`mcp_server/` is function-local) → **710 passed** (baseline same paths: 703); `ruff check
  src/pflow/execution src/pflow/core` clean; `mypy run_outcome.py` clean; `ruff check/format --check src tests` clean.
  The five documents from REAL in-process runs (isolated HOME), key order as emitted — match `show-before-code.md` AFTER exactly:
  - success: `success, status, workflow, execution_id, trace_path, result, errors, warnings, advisories, diagnostics, duration_ms,
    total_cost_usd, metrics, execution` (execution: `duration_ms, nodes_executed=2, nodes_total, steps`)
  - failure-by-exception (strict template): `success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories,
    diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command` (nodes_executed=1 — #699 metrics present)
  - failure-by-action (shell exit 1): same key set as by-exception (nodes_executed=1; `"nodes_executed"` occurs once in the JSON)
  - paused: `success, status, workflow, execution_id, trace_path, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd,
    metrics, execution, gate, resume_command` (`gate` = masked GateRequest dict, `question: null`; `resume_command … --approve yes|no`)
  - denied (after resume): `success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics,
    duration_ms, total_cost_usd, metrics, execution, gate` (execution adds `resumed_from, nodes_restored=2, resume_entry_node,
    resume_entry_iteration`, nodes_executed=0); fresh denial nodes_executed=2, no lineage.
  Extra endings checked: output-resolution failure → `result: {"good": 1, "nul": null}`, identity, NO `resume_command`; `--no-trace`
  failure → no identity/no `resume_command`, metrics kept; resumed-then-failed carries the lineage block.
  Full `make test` on this tree (by design red): 334 failed + 3 collection errors. Attribution verified by temporarily restoring the
  two old modules from HEAD (untracked, deleted after; tree confirmed clean of them): the same set then fails only **5** — 3 in
  `test_metrics_integration.py` (top-level `nodes_executed`, plan P2's rewrite list) + 2 `test_compiler_integration.py`
  `TestPerformanceBenchmarks` timing tests (pass alone, 25/25 — load flake). Everything else is the old-name import in `cli/`/`mcp_server/`.
  `uv run pflow ok.pflow.md` (isolated HOME) now prints `No module named 'pflow.execution.formatters.success_formatter'` — expected until P2.
  | Assumed: P2/P3 compose the renderers from these sections without changing the document (the mid-task review's job to challenge).
- Deviations/surprises:
  (1) **Renderers stay P2/P3; their tests moved onto the section functions.** §5 says the moved MCP-text classes "render through
  `render_mcp_text`/`render_cli_stderr`" and `test_resume_engine` asserts the ⤷ line "via `render_cli_stderr`", but P1's phase line
  builds only §4.1 ("moved … with their tests"). Followed the phase line: `TestFormatSuccessAsText`/`TestOnlyNodeDisplay`/
  `TestCacheStatsDisplay`/`TestDeniedStatusRendering`/… now assert `completion_line`/`mode_lines`/`diagnostic_sections` etc. on
  outcomes built from real (or directly-constructed) `ExecutionResult`s; `test_resume_engine` uses `mode_lines(document)` (P2 may
  switch to `render_cli_stderr` — one line each). No renderer, no shim.
  (2) **`_outcome_status` has a second normalization not in §3.3:** `not result.success` with status SUCCESS/DEGRADED → FAILED. The
  dataclass default status is SUCCESS, so `ExecutionResult(success=False, …)` (23 test constructions, e.g. P2's `mock_compile` failures)
  would otherwise render `status: "success"` and exit 0. No production producer emits that pair (both runner constructions set status).
  (3) `exit_code` is a property (`EXIT_CODES[status]`), not a stored field — it cannot disagree with `status`.
  (4) No `batch_error_details`/`shell_stderr_block` wrappers (deletion test: they would just rename): renderers call
  `format_batch_errors_section` / `format_stderr_warnings` (public name kept — 3 existing importers).
  (5) **`gate_lines` renders for PAUSED only** (§4.1 + plan-review #3 + show-before §4 "a denial renders no gate preview"). §4.3 says
  the MCP layout has a "`Gate:` block (paused/denied)" — contradiction for P3 to settle; the denied `gate` stays in the document either way.
  (6) `errors_block([])` returns `[]`; `format_error_text` supplies `❌ Workflow execution failed`. A FAILED outcome with zero errors
  (today's CLI prints "cli: Workflow execution failed - Node returned error action") needs its fallback in P2's renderer.
  (7) Probe text changes (#748 surface, intended by §3.4/§4.1): multi-error header gains the count, no 3-error cap, headings unified to
  `⚠️ Warnings:` / `ℹ️ Advisories:`, trace line is `trace_path: …` (never shown — the probe is traceless).
  (8) Test moves outside the literal line ranges: the two `_build_error_text` tests in `test_agent_ux_fixes.py` were MOVED into
  `TestFormatErrorText` (that file can't collect in P1 — line 13 imports `cli.workflow_errors` → `success_formatter`); the
  single-error `_build_error_text` test in `test_registry_run_mcp.py` deleted as a duplicate of `TestFormatErrorText`, and that file's
  e2e probe test deepened (exact text through `run_registry_node`).
  (9) **For P2 (not in the plan's P2 file list):** `tests/test_cli/test_shell_stderr_warnings.py:14` imports `format_stderr_warnings`
  from the old module and its `TestDisplayStderrWarnings` (~:351-420) duplicates `test_run_outcome.py::TestStderrWarnings`;
  `test_truncates_long_stderr` pins the pre-#755 `[:300]` cut (400 chars is now ≤ head+tail and kept whole) → delete the class, keep
  the file's CLI integration tests. **For P4:** `runtime/engine/engine.py:875` comment names `success_formatter.py`/`error_formatter.py`
  as `__trace_collector__` readers (now stale; the builder reads `result.trace`) — engine file, not touched; formatters `CLAUDE.md` rows.
  (10) **Real-HOME contact (hand-back, not self-repaired):** one ad-hoc probe `uv run python -c "…run_registry_node(…)"` ran WITHOUT
  the HOME redirect (~23:55). Afterwards `~/.pflow/cache/` showed a directory-mtime bump only; `find ~/.pflow -mmin -8` lists no new or
  modified file from it (the cache.db/trace mtimes there are 23:47–23:49, other sessions). Traceless, cache-disabled run; no content
  written that I can find. Every other probe used `HOME=<scratchpad>`.
- Self-checks: fully happy — doubts raised: (a) the absent-vs-null rule only binds the outcome's own keys — pinned both halves
  (`TestAbsentNeverNull`); (b) a test-only paused fixture without `trace_files` would carry `resume_command` with no identity (the
  conftest no-ops `_open_stream`) — production impossible (a durable pause streams), left; (c) `diagnostics` is now errors-first
  (plan §3.1) — failure documents reorder vs today. test-reflect (directed): ran 16 real source mutations (identity on trace only,
  paused keeps errors, no durability normalization, skipped counts target, null step duration, resume w/o resumable, diagnostics drop
  errors, outputs on every status, lineage dropped, statusless failure, head-only stderr, denied gate lost, gate lines on denial,
  `ran` always true, metrics only on success, gate unmasked) — every one killed with a counted failure (1–8 failed each), original
  written back. Deepened: `test_every_error_is_numbered…` (exact `Error N:` blocks, was `"4." or "Error 4"`), probe e2e test (exact
  text); added `test_a_paused_gate_preview_is_masked` (no test caught an unmasked paused gate). Deleted: three `find_auto_output`
  tests (duplicates of `test_output_utils.py`), `test_formatter_runs_in_under_10ms` + the three `checkpoint` tests (plan §5), the
  registry single-error duplicate.
- Next: mid-task review (impact-completeness + silent-failures) on the uncommitted P1 diff; then P2+P3.

## [2026-10-12 00:20] implementer I1b (Opus) — P1 mid-task review (gate-runner)
- Did: dispatched the plan's P1 mid-task review via the pflow fan-out on codex — `review-impact-completeness` +
  `review-silent-failures`, both on the WHOLE uncommitted P1 diff (`git diff HEAD`, HEAD `8531eb67`, staged renames + deleted
  `error_formatter.py`/`test_error_formatter.py` named; cli/+mcp_server/ old-name imports stated as by-design). Launched from the MAIN
  checkout's `uv run pflow` with `cwd=<this worktree>` — this worktree's CLI is import-broken until P2, so its own `pflow` cannot
  render the workflow's output. Report: `implementation/reviews/p1-midtask-review.md` (stdout tee'd; stderr in the gitignored
  `p1-midtask-review.stderr.log`), read in full.
- Changed: nothing in code/tests (no findings to fix); this entry + the review file.
- Verified: `run-codex 2/2 147.8s`, workflow `✓ completed in 170.1s`, Coverage table lists both lenses, "Failed or missing lenses:
  None". Findings: **Critical 0, Warning 0, Suggestion 0.** Both lenses returned specific verified-clean sections (not empty): field
  migration from every named old builder incl. pricing discriminators, partial outputs, lineage, gate payloads, resume commands;
  §3.4 drops; None tolerance (trace/metrics/empty store/`pause_request=None`); both `_outcome_status` arms; stream fault clears
  `trace_path` → no identity/resume; `--no-trace` gate stop → runner FAILED; `head_tail_preview` move; `format_error_text` probe.
  P1 gate re-run after the review: **710 passed** (+ both AST ratchets). | Assumed: the lenses read statically (no tests/probes run —
  their own stated limit); end-to-end rendering stays unverified until P2/P3.
- Deviations/surprises: dispatch from the main checkout (above) — the reviewed tree is still the worktree (`cwd=`), the main
  checkout only supplied a working `pflow` binary; the run's trace landed in the real `~/.pflow/debug` as every fan-out run does
  (process tooling, not a test/probe). A zero-finding mid-task review is weaker evidence than a found-and-fixed one; the P1 mutation
  pass (16/16 killed, prior entry) is the complementary check.
- Self-checks: dispositions — none to record (0 findings); coverage complete, no re-run needed. test-reflect: not re-run — no
  test changed since the directed pass in the P1 entry.
- Next: P2+P3 on the orchestrator's resume (with the #5 ruling: gate block PAUSED-only on both channels).

## [2026-10-12 01:13] implementer I1b (Opus, high) — P2 the CLI renders the outcome
- Did: `render_cli_stderr` (tier table §2) in `run_outcome.py`; `run.py::_display_execution_result` rewritten to §4.4 order
  (non-success → finalize first; build; `set_json_output` on json success only; finalize; echo stderr lines; stdout = document /
  text data / paused token line; `ctx.exit(outcome.exit_code)`); `_finalize_trace_and_report` keeps only `--report`;
  `execute_json_workflow`'s `except` passes only `exception=`. Deleted per §5: `run.py` `_handle_workflow_success`,
  `_emit_failure_tag`, `_resumable_execution_id`, `_display_paused_result`, `_display_denied_result`, `_maybe_echo_resume_hint`;
  `workflow_output.py` summary/JSON functions (`_handle_text_output` keeps only its data part); `cli/workflow_errors.py`;
  `error_output.py` result path + metrics branch (now exception-only, 3 functions).
- Changed: `src/pflow/cli/{commands/run.py, workflow_output.py, error_output.py, workflow_errors.py (D)}`,
  `src/pflow/execution/formatters/run_outcome.py`; tests: new `tests/test_cli/test_run_outcome_cli.py` (P2-T1..T9, 22 tests),
  `test_run_outcome.py::TestRenderCliStderr`, rewrites in `test_paused_cli.py`, `test_approval_gate_cli.py`, `test_resume_cli.py`,
  `test_metrics_integration.py`, `test_workflow_output_handling.py`, `test_agent_ux_fixes.py`, `test_direct_execution_helpers.py`,
  `test_enhanced_error_output.py`, `test_json_diagnostic_redaction.py`, `test_shell_stderr_warnings.py`; `.claude/agents/review-{agent-ux,
  feature-interactions,impact-completeness,silent-failures}.md` (+ `make sync-claude-assets`); Task-159 baseline: 4 cases re-recorded.
- Verified: end-of-P3 tree `make check` green; `make test` **11603 passed** (pre-P1 baseline 11586 → net **+17**). Baseline oracle: the
  four named dirs PASS, and the FULL `verify.sh` **87/87** after re-recording 4 cases, each moved by a ruled/authorized order change,
  none carries a raw duration: `02-validator-errors/02, 03, 05` (warnings now render BEFORE the errors block — the orchestrator's
  authorized order; 05 also gains one blank line before the multi-error header) and `15-run-flag-interactions/03` (the `⤷` mode line
  now sits directly under the completion line, show-before §4/§5; durations already `<DURATION>`-masked). `15/05` (`-p --only`)
  stays unchanged because `-p` output drops the summary's leading blank (no progress stream above it). The eleven show-before
  commands re-run as AFTER on the five fixtures (isolated HOME; `fail-exc` = HTTP timeout to 10.255.255.1:9), condensed transcript
  (ids → `<id>`, trace paths → `<trace>`, durations → `Xs`) pasted below. | Assumed: interleaving on a real terminal (stderr before
  stdout, CliRunner splits streams) — not exercised on a TTY.
- Deviations/surprises:
  (1) **Final CLI stderr order** (one shared order for both channels): completion line + `⤷` mode lines (same block) · batch item
  errors · shell stderr · cost · `⚠️ Warnings:` / `ℹ️ Advisories:` · errors block · resolved-outputs note · gate lines (3-space indent)
  · `To answer:` + bulk hint · `To resume from the failed step:` · `Workflow trace saved:`. Warnings sit after cost (not first) so the
  SUCCESS summary order is unchanged and the error block — the cause — is last but for the hint/trace lines.
  (2) **A denial renders no errors block on either channel** — the denied line says it; the gate diagnostic stays in the document's
  `errors`. (The first AFTER run showed `Error: Gate denied` beneath the denied line; show-before §4's denied text has only the denied
  line + `⤷`.) Pinned: `test_resumed_then_denied…` asserts no `Error: Gate denied`; MCP twin in `test_run_outcome.py`.
  (3) Deviation-6 fallback: a FAILED outcome with no error diagnostic renders `❌ Workflow execution failed — no error details were
  recorded` (in `errors_block`, so the probe shares it); today's CLI said `cli: Workflow execution failed - Node returned error
  action` + `Check node output above` — a guess about the cause, dropped.
  (4) `-p` drops the leading blank line (it separates the summary from the progress stream, which `-p` never prints) — keeps 15/05.
  (5) The denied line loses its yellow `click.style` (renderers return plain strings; tests never saw the colour under CliRunner).
  (6) JSON-mode paused/failure stderr no longer carries the resume hint (it is in the document — Q1/Q4 as ruled); paused text now
  renders warnings before the gate lines (shared order), and they are summary tier, so `-p` hides them (Q1).
  (7) `test_resume_engine` keeps `mode_lines(document)` for its ⤷ assertions (my call — it asserts the document's lineage; the
  renderer is pinned by `test_run_outcome_cli.py`).
  (8) Test deletions: `test_direct_execution_helpers.py::TestDisplayCostSummary` (duplicate of `test_run_outcome.py::TestCostLines`,
  which drives real collectors), `TestDisplayExecutionSummaryAdvisories::test_legacy_warnings_dict_key…` (the legacy key no longer
  exists to resurrect); the advisory/failure-advisory/subscription-to-stderr tests moved to `TestRenderCliStderr`;
  `test_shell_stderr_warnings.py::TestDisplayStderrWarnings` deleted per the ruling (incl. the pre-#755 300-char pin).
  `test_resume_cli.py::test_output_resolution_failure_json_omits_resume_fields` now asserts `execution_id` IS present (D1) and
  `resume_command` absent; `test_failed_run_json_document_carries_resume_fields` proves the id against the trace's meta line instead
  of the (now JSON-absent) stderr hint. `test_json_diagnostic_redaction.py::test_http_401…` gains `trace_files` (resume_command names
  a trace file; without one the run has no identity — the spec's rule).
  (9) Agent files (`.claude/agents/review-*.md`, 4 rows naming the deleted paths/symbols) edited now, not P4 — `make test` cannot be
  green with them stale (`test_agent_references`). Minimal edits; P4 should still re-read them.
  (10) Noticed for P4: `src/pflow/cli/CLAUDE.md` owner rows + the DENIED/PAUSED dispatch paragraph, formatters `CLAUDE.md`,
  `guide/features/resume.md:31` (`paused_node_id`, `gate_request`), and `engine.py:875`'s comment are stale now.
- Self-checks: fully happy — doubts raised + fixed during the AFTER pass: the denied errors block (2), a double blank after shell
  diagnostics (`format_diagnostic`'s trailing newline — stripped in `errors_block`), the `⤷` line's placement. Remaining doubt, left:
  the CLI now prints stderr BEFORE the paused token line on stdout (was after) — streams are separate; only terminal interleaving
  moves. test-reflect (directed): 15 real renderer mutations (must-act in JSON, `-p` ignored, failed batch as summary, warnings after
  errors, completion on pause, errors on denial, resume hint on any status, trace line under `-p`, mode lines hidden without the
  completion line, leading blank under `-p`, MCP gate on denial, MCP all advisories, MCP no identity, MCP errors on denial, no
  zero-error fallback) — 14 killed on first run; "MCP errors on denial" survived → deepened `test_a_pause_renders_its_gate…` with the
  MCP denied text (now killed). Deepened `TestTiersUnderPrint.test_pause` (no `To resume` on a pause) and the resumed-denial test (no
  error block; `⤷` directly under the denied line). Every absence assertion in `test_run_outcome_cli.py` has its presence twin in the
  same stream (plain vs `-p`, paused vs denied).
  Follow-up (orchestrator-directed, 01:25): the open doubt settled to show-before §3 — paused TEXT echoes the stdout token line
  BEFORE the stderr gate/answer lines again (JSON keeps Q4's trace-line-before-payload); pinned by
  `test_the_paused_token_line_comes_before_the_gate_content` on CliRunner's mixed `output` (mutation: token line moved after the
  stderr lines → 1 failed); affected files 1583 passed, `make check` green, baseline 15/* 5/5. Loose ends: none in P2/P3 code; noted
  only — the probe's `format_error_text` keeps errors-before-warnings (#748's lane) and §8's `tests/fixtures/run_outcome/` copy is P4's.
- Next: P3 (built in the same pass — entry below).

AFTER — the show-before-code commands (five fixtures, isolated HOME):
```text

$ pflow FX/ok.pflow.md
--- stdout:
two-value
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

✓ Workflow completed in Xs

Workflow trace saved: <trace>

Workflow output (The second step's text.):

--- exit 0

$ pflow FX/ok.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, result, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution
execution: {'nodes_executed': 2, 'nodes_total': 2}
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

✓ Workflow completed in Xs

Workflow trace saved: <trace>
--- exit 0

$ pflow FX/ok.pflow.md -p
--- stdout:
two-value
--- stderr:
--- exit 0

$ pflow FX/ok.pflow.md -p --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, result, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution
execution: {'nodes_executed': 2, 'nodes_total': 2}
--- stderr:
--- exit 0

$ pflow FX/fail-action.pflow.md
--- stdout:
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✗ Failed

❌ Workflow failed after Xs

Error: Execution Failed

Command failed with exit code 1: boom

  At: node 'two'

  Shell details:
    Command: echo boom >&2; exit 1
    Stderr: boom

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-action.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 1, 'nodes_total': 2}
error: Command failed with exit code 1: boom

resume_command: pflow resume <id>
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✗ Failed

❌ Workflow failed after Xs

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md
--- stdout:
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  slow-fetch... ✗ Failed

❌ Workflow failed after Xs

Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 1, 'nodes_total': 2}
error: Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
resume_command: pflow resume <id>
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  slow-fetch... ✗ Failed

❌ Workflow failed after Xs

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md -p
--- stdout:
--- stderr:
Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

To resume from the failed step: pflow resume <id>
--- exit 1

$ pflow FX/gate.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  echo three-value

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow FX/gate.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate, resume_command
execution: {'nodes_executed': 2, 'nodes_total': 3}
resume_command: pflow resume <id> --approve yes|no
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

Workflow trace saved: <trace>
--- exit 4

$ pflow FX/gate.pflow.md -p
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
   command:  echo three-value

To answer: pflow resume <id> --approve yes|no
--- exit 4

$ pflow resume <id> --approve no
--- stdout:
--- stderr:
Executing workflow (3 nodes):

✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 3

$ pflow FX/gate.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate, resume_command
execution: {'nodes_executed': 2, 'nodes_total': 3}
resume_command: pflow resume <id> --approve yes|no
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve no --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate
execution: {'nodes_executed': 0, 'nodes_total': 3, 'resumed_from': '<id>', 'nodes_restored': 2, 'resume_entry_node': 'three', 'resume_entry_iteration': 1}
error: Denied at gate 'three'.
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):

  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 3

$ pflow resume <id> --approve no -p
--- stdout:
--- stderr:
✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored
--- exit 3

$ pflow FX/gate-fail.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  exit 1

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes
--- stdout:
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✗ Failed

❌ Workflow failed after Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Error: Execution Failed

Command failed with exit code 1
  At: node 'three'

  Shell details:
    Command: exit 1

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/gate-fail.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  exit 1

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 0, 'nodes_total': 3, 'resumed_from': '<id>', 'nodes_restored': 2, 'resume_entry_node': 'three', 'resume_entry_iteration': 1}
error: Command failed with exit code 1
resume_command: pflow resume <id>
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✗ Failed

❌ Workflow failed after Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/gate.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  echo three-value

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes
--- stdout:
three-value
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✓ 0.0s

✓ Workflow completed in Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>

cli: No outputs declared — showing auto-detected key 'stdout'. Declare outputs for reliable results.

Workflow output:

--- exit 0

```

## [2026-10-12 01:15] implementer I1b (Opus, high) — P3 MCP renders the outcome
- Did: `render_mcp_text` (§4.3) over the same section functions; `ExecutionService.execute_workflow` = build → render → return on
  SUCCESS/DEGRADED/PAUSED, else `raise RuntimeError(text)` (outer `except Exception` wrapper kept); `_workflow_metadata` extracted.
  Deleted per §5: `_format_success_result`, `_build_error_text`, `_format_resolved_outputs_section`, `_format_paused_text`,
  `_trace_path_str`. `workflow_execute` docstring Returns block rewritten to the one layout.
- Changed: `src/pflow/mcp_server/services/execution_service.py`, `src/pflow/mcp_server/tools/execution_tools.py`,
  `src/pflow/execution/formatters/run_outcome.py`; tests: `tests/test_integration/test_cli_mcp_parity.py` (P3-T1..T5 + P2-T8's MCP
  half, 7 tests), `test_run_outcome.py` (P3-T6 on the in-process resumed-then-failed outcome; MCP denied text),
  `tests/test_mcp_server/test_execution_workflow.py` (paused line, loop bulk-hint position, identity test rewritten).
- Verified: same end-of-P3 gate as P2 (`make check` green, `make test` 11603 passed, baseline 87/87). `ExecutionService
  .execute_workflow` on the five fixtures (isolated HOME), condensed below — failure texts now carry the ❌ line, `execution_id`,
  `trace_path` and `resume_command` (#699 twin on MCP); the pause leads with the step and keeps the `Gate:` block. | Assumed: the
  MCP server boundary renders the raised text verbatim (unchanged code; `tests/test_mcp_server/test_execution_workflow.py:145-176` green).
- Deviations/surprises:
  (1) **#5 settled as ruled:** `gate_lines` renders PAUSED-only on BOTH channels (§4.3's "paused/denied" → paused); MCP denied text =
  denied line (+ `⤷`) + identity, no `Gate:`, no errors block.
  (2) **Final MCP order** (shared with the CLI): `{name} was executed` (library/created only) · completion line · `⤷` lines · batch
  errors · shell stderr · cost · `⚠️ Warnings:` / `ℹ️ Advisories:` (advisories filtered to parser/validator, §3.7) · errors block
  (FAILED only) · resolved-outputs note · `Workflow output:` + value (success) · `Gate:` (paused) · identity lines (+ bulk hint after
  `resume_command:` on a looping pause). Success text = today's + `status: success`. MCP headings unified on the CLI glyph wording.
  (3) **Bug found by P3-T3 and fixed:** a failure with no completion line (pre-collector validation failure) started the MCP text with
  a blank line; `render_mcp_text` now drops the leading separator when the head is empty.
  (4) `_trace_path_str` deleted and `format_error_text` lost its `trace_path` parameter: the probe runs `trace_enabled=False`, so the
  path was always empty — a parameter nothing could ever fill (plan §3.4 named it; deletion test). `test_execution_workflow.py
  ::test_success_text_carries_execution_id` (asserted an id renders with NO trace file) reversed to the spec's rule —
  `test_identity_lines_need_a_trace_file`; the presence twin is the existing `trace_files` test (`test_mcp_run_streams_a_real_trace`).
  (5) Inline-IR runs (no file) render `status:` but no identity when the stream is off — production MCP always streams, so identity is
  present whenever a trace file exists.
- Self-checks: fully happy — doubt raised: the probe (`format_error_text`) still renders errors BEFORE warnings while the run renderers
  put warnings first; left as is (the probe is a different surface, #748's lane; the orchestrator's order change named the run
  renderers). test-reflect (my judgment, run): the MCP mutations (gate on denial, all advisories, no identity, errors on denial) are in
  the P2 mutation pass — all killed after the one deepening; P3 tests assert exact lines/prefixes, each absence paired with a presence
  in the same text (paused vs denied, parser vs runtime advisory, CLI JSON warning vs MCP text).
- Next: hand back (orchestrator merges origin/main; P4 docs + Task-170 example re-record).

MCP `execute_workflow` on the five fixtures:
```text
### execute_workflow(ok.pflow.md)
✓ Workflow completed in Xs

Workflow output:

two-value

status: success
execution_id: <id>
trace_path: <trace>

### execute_workflow(fail-action.pflow.md)
[raised RuntimeError]
❌ Workflow failed after Xs

Error: Execution Failed

Command failed with exit code 1: boom

  At: node 'two'

  Shell details:
    Command: echo boom >&2; exit 1
    Stderr: boom

status: failed
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id>

### execute_workflow(fail-exc.pflow.md)
[raised RuntimeError]
❌ Workflow failed after Xs

Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

status: failed
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id>

### execute_workflow(gate.pflow.md)
⏸ Workflow paused at 'three' — a human decision is required.

Gate:
  command:  echo three-value

status: paused
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id> --approve yes|no

### execute_workflow(gate-fail.pflow.md)
⏸ Workflow paused at 'three' — a human decision is required.

Gate:
  command:  exit 1

status: paused
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id> --approve yes|no


```

## [2026-10-12 01:25] task-orchestrator (Opus) — P1–P3 accepted; committing; main merge next
- Did: verified I1b's P1 (+ mid-task review: impact-completeness + silent-failures on codex, 0 findings — report
  `reviews/p1-midtask-review.md`), P2, P3 handbacks; my gate on the end-of-P3 tree: `make check` green; `make test` 11602 passed
  + 1 failed `tests/test_third_party_compile_warnings.py::test_no_runtime_dependency_emits_a_compile_time_warning` (litellm
  `ResourceWarning: unclosed event loop` under xdist load; passes alone 2/2; diff touches no import path it scans — load flake,
  re-checked at the P4 gate).
- Fresh-launch reason (P1): the plan routes P1 at effort `high`; the P0 implementer ran at `medium` and held only P0 context, so
  I1b was launched fresh for P1 and resumed (continuity) for the mid-task review and P2+P3.
- Rulings made here (1–2/5, logged): §4.3's MCP "Gate: block (paused/denied)" → PAUSED-only on both channels (plan-review #3;
  MCP never produces a denial); warnings/advisories render before the errors block (main-orchestrator-authorized order; final
  order in the P2 entry); paused TEXT keeps the token line FIRST on stdout (show-before §3 "Text unchanged" — loose-ends round,
  pinned by `test_the_paused_token_line_comes_before_the_gate_content`, mutation-checked).
- Accepted deviations: denial renders no errors block (gate diagnostic stays in the document); zero-error failure fallback text;
  `format_error_text` lost the never-fillable `trace_path` param; `_outcome_status`'s second arm (`success=False` + default
  SUCCESS → FAILED) — a test-fixture-only pair today, kept as the two fields' coherence guard (the completion gate's simplicity
  lens may challenge it); four `.claude/agents/review-*.md` rows edited in P2 (agent-reference test).
- Text deltas received: #810 (Task-170 examples capture now in `baseline-oracle` — re-record affected examples in this PR, name
  them); #818 (59 Task-159 cases re-recorded on main — no overlap with this branch's four re-records `02/02, 02/03, 02/05, 15/03`,
  checked by `git diff --name-only`; missing-input diagnostics now carry `suggestions`; #804 member (d) `_show_workflow_help` →
  P4 evaluates, one-line caller fix only).
- Next: commit P1–P3; `git merge origin/main`; gates; P4 to I1b (window ~570k — P4 is docs it already holds; rotation if degraded).

## [2026-10-12 01:38] implementer I1b (Opus) — P4 docs, instruction files, close-out evidence (merged tree `de1f80d4`)
- Did: examples-capture `trace_path` mask + re-record; Task-159 full check; F20→A doc rewording; every §1 "Docs that describe the
  documents" surface; stale CLAUDE.md / agent defs / comments; changelog entry; close-out gates + §8 real-surface run.
- Changed: `.taskmaster/tasks/task_170/implementation/examples-baseline/{capture.py, README.md, 28 captures}`,
  `tests/test_scripts/test_examples_capture.py`; `docs/reference/cli/index.mdx` (paused paragraph → `gate`/`resume_command`; JSON-mode
  section rewritten from REAL AFTER output — success + failure documents, key-fields table gains `status`, `execution_id`/`trace_path`,
  `error`, `execution.nodes_executed`, `execution.resumed_from`/`nodes_restored`, `gate`, `resume_command`, F20 `success` row; `-p`
  paragraph = the tier rule; exit-code table gains 3 and 4), `docs/changelog.mdx`; `src/pflow/guide/features/{resume.md, approval.md}`;
  `src/pflow/mcp_server/resources/instructions/mcp-agent-instructions.md`; `src/pflow/{cli,execution/formatters,mcp_server/services}/CLAUDE.md`;
  `.claude/agents/{pflow-codebase-searcher, review-agent-ux, review-architecture-fit}.md` (+ `make sync-claude-assets`);
  `src/pflow/runtime/engine/engine.py` (**comment-only**, :875 — the `__trace_collector__` readers list; no code line touched);
  `src/pflow/execution/formatters/output_utils.py` (docstring only); `architecture/core-concepts/data-type-coercion.md:143`.
- Verified: `make check` green; `make test-all-local` **11735 passed, 2 skipped** (0 failed). Examples capture: `capture.py` re-record,
  then `--check` twice → `28 examples, 0 differing` both times (deterministic); `tests/test_scripts/test_examples_capture.py` 8 passed.
  Task-159: FULL `verify.sh` on the merged tree **87/87, 0 drifted** — no case moved by this branch after the P2 re-records were merged
  (main's #818 re-recorded 59 cases; ours stayed green on top). `12-real-world-lyrics-generator/04-guide-auto-detect` re-run AFTER the
  guide edits: PASS (5/5 in its dir) — the auto-detect output includes neither `approval.md` nor `resume.md`, so it does not move from
  this branch (per the course note, untouched). No baseline case records a run's `--output-format json` document (no `command.sh`
  uses it; the only `trace_path` in expected output is analyze-cache's own `"trace_path": null`), so `normalize.py` needs no mask.
  §8 real-surface on the merged tree (fresh isolated HOME `home4`, never the real one): the show-before set + resumed success, and MCP
  `execute_workflow` on ok / fail-action / fail-exc / gate — condensed transcripts below; byte-identical (modulo ids/durations) to the
  P2/P3 AFTER pass. | Assumed: CI `tests-windows` (no platform-sensitive code; not runnable here).
- **Re-recorded examples (verbatim for the PR body — all 28 in the manifest):** bundling/command-ref, bundling/parent-with-sub,
  bundling/simple, bundling/sub-echo, core/conditional-branching, core/error-handling, core/minimal, core/proxy-mappings,
  core/simple-pipeline, core/stateful-loop-judge-round, core/stateful-loop-tournament, core/stdin-echo, core/stdout-result,
  error-handling/coalesce-mixed-absent-failed, error-handling/failed-node-direct-reference, error-handling/loop-recovery,
  error-handling/non-retriable-file-error, error-handling/retry-with-backoff, error-handling/source-line-heavy-offsets,
  error-handling/source-line-multi-output, file-references/code-file-ref, file-references/command-file-ref,
  file-references/no-file-refs, invalid/code-annotation-type-mismatch, invalid/code-missing-result-annotation,
  nested/to-uppercase, simple-workflow, test-nested-index (`examples/<name>.pflow.md`). Cause, from the pre-re-record `--check` diff:
  `+execution_id` (24) / `+trace_path` (26), `-nodes_executed` top-level (22) and `metrics.workflow.nodes_executed` (22), `+errors: []`
  (20); failure documents gain `warnings`/`advisories`/`metrics`/`duration_ms`/`total_cost_usd` and drop `execution.duration_ms: null`
  (4); a pre-engine validation failure (`invalid/*`) gains an `execution` block of `not_executed` steps (plan §3.1: `execution` iff
  the IR has nodes). **Task-159 cases re-recorded by this branch:** in P2 (already committed in `aafe8b90`): `02-validator-errors/02`,
  `/03`, `/05` (warnings before errors) and `15-run-flag-interactions/03` (`⤷` under the completion line); none in P4.
- Deviations/surprises:
  (1) **#804 (d) `_show_workflow_help` NOT folded:** it is two defects (its own `Workflow:` heading duplicates the shared renderer's,
  and it reads `workflow_ir["description"]` — a `.pflow.md` IR has none, the text lives on `ResolvedWorkflow.description` — so the
  caller must receive the resolved workflow), plus the `Source:` line needs a new home once the heading goes; more than a one-line
  caller fix → left for #804's lane.
  (2) Plan §8's `tests/fixtures/run_outcome/` copy skipped: no test consumes those files (the tests write their workflows inline); the
  five fixtures live in my scratchpad only — no dead fixtures.
  (3) **Changelog convention:** every existing `<Update>` is a released version; this entry is `description="Unreleased"` (the
  release bump should rename/merge it) — flagging in case the release process wants it written differently.
  (4) `docs/reference/cli/index.mdx`'s old JSON examples were already wrong (`metrics.workflow.nodes_cached`, `metrics.total
  .total_tokens`/`llm_calls` never existed); the rewrite uses real output, trimmed.
  (5) The `invalid/*` examples showing an `execution` block of all-`not_executed` steps for a run that never started is the plan's
  rule applied faithfully; noting it as a judgement a reviewer may question (alternative: omit `execution` when nothing ran —
  `execution` would then be absent on exactly the pre-collector failures, same boundary as `metrics`).
- Self-checks: fully happy — doubt raised: deviation (5); left as the plan states, surfaced here. test-reflect (my judgment, run): the
  one P4 test change (`stored["trace_path"] == "<TRACE_PATH>"`, `execution_id == "<UUID>"`) — real mutation removing the mask → 3
  failed (the determinism tests + the new assertion), restored. No other test changed in P4.
- Next: hand back (orchestrator merges main incl. #820's 12/04 re-record; completion gate §9).

§8 real-surface — CLI (merged tree, isolated HOME):
```text

$ pflow FX/ok.pflow.md
--- stdout:
two-value
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

✓ Workflow completed in Xs

Workflow trace saved: <trace>

Workflow output (The second step's text.):

--- exit 0

$ pflow FX/ok.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, result, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution
execution: {'nodes_executed': 2, 'nodes_total': 2}
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

✓ Workflow completed in Xs

Workflow trace saved: <trace>
--- exit 0

$ pflow FX/ok.pflow.md -p
--- stdout:
two-value
--- stderr:
--- exit 0

$ pflow FX/ok.pflow.md -p --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, result, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution
execution: {'nodes_executed': 2, 'nodes_total': 2}
--- stderr:
--- exit 0

$ pflow FX/fail-action.pflow.md
--- stdout:
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✗ Failed

❌ Workflow failed after Xs

Error: Execution Failed

Command failed with exit code 1: boom

  At: node 'two'

  Shell details:
    Command: echo boom >&2; exit 1
    Stderr: boom

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-action.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 1, 'nodes_total': 2}
error: Command failed with exit code 1: boom

resume_command: pflow resume <id>
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  two... ✗ Failed

❌ Workflow failed after Xs

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md
--- stdout:
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  slow-fetch... ✗ Failed

❌ Workflow failed after Xs

Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 1, 'nodes_total': 2}
error: Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
resume_command: pflow resume <id>
--- stderr:
Executing workflow (2 nodes):
  one... ✓ 0.0s
  slow-fetch... ✗ Failed

❌ Workflow failed after Xs

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/fail-exc.pflow.md -p
--- stdout:
--- stderr:
Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

To resume from the failed step: pflow resume <id>
--- exit 1

$ pflow FX/gate.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  echo three-value

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow FX/gate.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate, resume_command
execution: {'nodes_executed': 2, 'nodes_total': 3}
resume_command: pflow resume <id> --approve yes|no
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

Workflow trace saved: <trace>
--- exit 4

$ pflow FX/gate.pflow.md -p
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
   command:  echo three-value

To answer: pflow resume <id> --approve yes|no
--- exit 4

$ pflow resume <id> --approve no
--- stdout:
--- stderr:
Executing workflow (3 nodes):

✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 3

$ pflow FX/gate.pflow.md --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate, resume_command
execution: {'nodes_executed': 2, 'nodes_total': 3}
resume_command: pflow resume <id> --approve yes|no
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve no --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, gate
execution: {'nodes_executed': 0, 'nodes_total': 3, 'resumed_from': '<id>', 'nodes_restored': 2, 'resume_entry_node': 'three', 'resume_entry_iteration': 1}
error: Denied at gate 'three'.
gate: {'node_id': 'three', 'node_type': 'ShellNode', 'kind': 'action_approval', 'preview': {'command': 'echo three-value'}, 'question': None, 'options': [], 'recommendation': None, 'iteration': None, 'max_iterations': None}
--- stderr:
Executing workflow (3 nodes):

  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 3

$ pflow resume <id> --approve no -p
--- stdout:
--- stderr:
✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored
--- exit 3

$ pflow FX/gate-fail.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  exit 1

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes
--- stdout:
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✗ Failed

❌ Workflow failed after Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Error: Execution Failed

Command failed with exit code 1
  At: node 'three'

  Shell details:
    Command: exit 1

To resume from the failed step: pflow resume <id>

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/gate-fail.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  exit 1

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes --output-format json (JSON keys)
keys: success, status, workflow, execution_id, trace_path, error, errors, warnings, advisories, diagnostics, duration_ms, total_cost_usd, metrics, execution, resume_command
execution: {'nodes_executed': 0, 'nodes_total': 3, 'resumed_from': '<id>', 'nodes_restored': 2, 'resume_entry_node': 'three', 'resume_entry_iteration': 1}
error: Command failed with exit code 1
resume_command: pflow resume <id>
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✗ Failed

❌ Workflow failed after Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>
--- exit 1

$ pflow FX/gate.pflow.md
--- stdout:
Paused at 'three'. Resume token: <id> (exit 4)
--- stderr:
Executing workflow (3 nodes):
  one... ✓ 0.0s
  two... ✓ 0.0s

   command:  echo three-value

To answer: pflow resume <id> --approve yes|no

Workflow trace saved: <trace>
--- exit 4

$ pflow resume <id> --approve yes
--- stdout:
three-value
--- stderr:
Executing workflow (3 nodes):
✓ Gate 'three' approved via --approve yes
  three... ✓ 0.0s

✓ Workflow completed in Xs
  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored

Workflow trace saved: <trace>

cli: No outputs declared — showing auto-detected key 'stdout'. Declare outputs for reliable results.

Workflow output:

--- exit 0
```

§8 real-surface — MCP `execute_workflow` (ok, fail-action, fail-exc, gate):
```text
### execute_workflow(ok.pflow.md)
✓ Workflow completed in Xs

Workflow output:

two-value

status: success
execution_id: <id>
trace_path: <trace>

### execute_workflow(fail-action.pflow.md)
[raised RuntimeError]
❌ Workflow failed after Xs

Error: Execution Failed

Command failed with exit code 1: boom

  At: node 'two'

  Shell details:
    Command: echo boom >&2; exit 1
    Stderr: boom

status: failed
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id>

### execute_workflow(fail-exc.pflow.md)
[raised RuntimeError]
❌ Workflow failed after Xs

Error: Execution Failed

Request to http://10.255.255.1:9/ timed out after 1 seconds. Increase the step's timeout (e.g. `- timeout: 60`) or check if the service is responding.
  At: node 'slow-fetch'

status: failed
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id>

### execute_workflow(gate.pflow.md)
⏸ Workflow paused at 'three' — a human decision is required.

Gate:
  command:  echo three-value

status: paused
execution_id: <id>
trace_path: <trace>
resume_command: pflow resume <id> --approve yes|no

```

## [2026-10-12 01:50] task-orchestrator (Opus) — P4 accepted; committing; main merge #2
- Did: read I1b's P4 entry; verified `engine.py` diff is comment-only (the `__trace_collector__` readers list) and the
  `capture.py` change is one key-based mask (`trace_path` → `<TRACE_PATH>`, docstring + README). I1b: `make check` green,
  `make test-all-local` 11735 passed / 2 skipped; examples `--check` 28/0 twice; Task-159 87/87.
- Ruled (1/5): the hand-written `docs/changelog.mdx` "Unreleased" `<Update>` is REVERTED — the changelog is generated at release
  by `examples/real-workflows/generate-changelog` (`.claude/skills/release/SKILL.md`; only release commits touch the file);
  the draft text is reused in the PR body.
- Accepted: #804 (d) not folded (two defects + the `Source:` line's home — not a one-line caller fix → task-review note);
  plan §8 fixtures copy skipped (no consumer).
- Open, routed to the completion gate (agent-ux + simplicity lenses): `execution` block of all-`not_executed` steps on a
  pre-collector validation failure (`invalid/*` examples) — plan §3.1 "iff the IR has nodes" vs omitting it when nothing ran.
  If a lens flags it, it comes up as a plan-shape question, not a silent flip.
- Text delta: #820 (→ `92dddfc4`) re-recorded Task-159 `12/04`; this branch's guide edits don't move it (I1b re-ran it: PASS).
- Next: commit P4; merge `origin/main`; gates; completion gate (fresh gate-runner — I1b's window ~620k after four phases).

## [2026-10-12 02:09] gate-runner G1 (Opus) — completion gate: reading battery (7 lenses, codex fan-out) — dispositions
- Did: dispatched §9's seven reading lenses through `workflows/review/run-review-lenses.pflow.md` on codex from THIS worktree's
  `pflow` (tree green), scope `git diff origin/main...HEAD` @ `3c5a901b`, spec/plan/show-before/progress-log named as documents
  (silence = gap). Partition: `review-agent-ux` targeted at the `run_outcome.py` renderers + guide/docs/MCP-instructions/
  `execution_tools.py` diff; `review-test-fidelity` focused on the rewritten pins + new suites; `simplicity`, `spec-conformance`,
  `impact-completeness`, `silent-failures`, `feature-interactions` saw the whole diff. Open questions (a) all-`not_executed`
  `execution` on a pre-collector failure and (b) `_outcome_status`'s second arm put to agent-ux + simplicity; the one-producer grep
  put to spec-conformance. Report `reviews/completion-gate.md` (read in full; stderr in `completion-gate.stderr.log`):
  `run-codex 7/7 277.5s`, merge ✓, Coverage "Failed-lens gaps: None" — all seven produced. Findings: Critical 0, Warning 7
  (1 convergent ×3 lenses), Suggestion 4 (incl. one split assessment). Every Warning verified against code (reads + executed probes,
  isolated HOME) before fixing.
- Changed: `src/pflow/cli/commands/run.py` (`_settled_outcome` extracted from `_display_execution_result`: build → snapshot →
  finalize → rebuild when the trailer write cleared `trace_path`; `_save_trace_file` docstring de-staled; `output_error` callers),
  `src/pflow/execution/formatters/run_outcome.py` (`_execution_block` takes the gate: the gate-stopped step is never `completed`),
  `src/pflow/cli/{error_output.py, main.py, commands/report.py, commands/resume.py}` (unused `ctx` param dropped),
  `docs/reference/cli/index.mdx`, `src/pflow/mcp_server/resources/instructions/mcp-agent-instructions.md`,
  `.claude/agents/review-{silent-failures,agent-ux}.md` (+ `make sync-claude-assets` → 2 `.codex` mirrors);
  tests `tests/test_cli/test_run_outcome_cli.py` (+5), `tests/test_execution/formatters/test_run_outcome.py` (3 deepened).
- Dispositions (every finding):
  1. W convergent (spec-conformance W1, silent-failures W1, feature-interactions W2) — success CLI document keeps identity after a
     trailer-write fault — **CONFIRMED + FIXED.** Read `workflow_trace.py:1018-1036` (`_flush_line` → `_disable_streaming` on any
     write fault) + `:1120-1129` (clears `_stream_path`) + `:1146-1159` (`finalize` returns None): the success path built the
     outcome before `finalize`, so JSON carried `execution_id`/`trace_path` naming a trailer-less file and text printed
     `Workflow trace saved:` — violates spec "stream fault → both absent". Fix keeps §4.4's order (the trailer still snapshots the
     printed document) and rebuilds the outcome only when settling cleared the path; extracted as `_settled_outcome` (also keeps
     `_display_execution_result` under C901). Tests `TestATrailerWriteFaultLeavesNoIdentity::test_json/test_text`: a fault injected
     at the stream's `write` for the `run.complete` line (real `_flush_line` → `_disable_streaming` arm), each paired with a healthy
     run in the same medium (identity / trace line present). Not a re-litigation of the ordering ruling — the order is unchanged.
  2. W feature-interactions W1 — resumed looping gate denied reads `Steps completed: 1 of 1` — **CONFIRMED (executed) + FIXED.**
     Branch printed `1 of 1`; `main` (`923725b8`, same fixture, isolated HOME) printed `0 of 1` (old renderer counted
     `__execution__.completed_nodes`). Cause: the resume seeds the loop target's carried output into `shared[node]` and keeps it out
     of `restored_nodes`, so `build_execution_steps` labels it `completed`. Fix in the builder (no engine contact): the step the
     gate stopped (paused or denied — `gate.node_id`) is relabelled `not_executed` when the store says `completed` (a gate always
     stops its step before it runs). Tests: `test_denied_looping_gate[text|print]` now pins `Steps completed: 0 of 1.`;
     new `test_a_looping_gate_paused_again_has_not_completed_its_step` (JSON paused doc after approve-yes: `nodes_executed == 0`,
     gated step `not_executed`; the marker proves iteration 1 ran). The lens's "re-paused without approving" variant does not exist
     — `pflow resume <paused>` without `--approve` is refused (executed) — dropped.
  3. W spec-conformance W2 — P2-T5's paused warnings `-p` pair missing — **CONFIRMED + FIXED:**
     `TestTiersUnderPrint::test_a_pause_shows_its_warnings_only_without_print` (real validator warning from `${one.stdout.a}` read off
     the JSON document; `⚠️ Warnings:` + its message present without `-p`, absent with; `To answer:` present in both).
  4. W test-fidelity W1 — migrated MCP regression tests assert section helpers, not `render_mcp_text` — **CONFIRMED + FIXED:**
     `test_shell_stderr_upgrades_the_glyph…` now asserts the MCP text's glyph + stderr block (noisy) and their absence (clean);
     `TestCostLines::test_partial_cost` / `test_priced_cost_carries_calls_and_tokens` assert the cost lines inside the MCP text.
  5. W test-fidelity W2 — pricing-key absence lacks a JSON presence twin — **CONFIRMED + FIXED:** `test_partial_cost` asserts
     `total_cost_usd is None`, `partial_cost_usd == 0.03`, `pricing_available is False`, `unavailable_models` on the document.
  6. W impact-completeness — stale routing rows in `review-silent-failures.md:179` / `review-agent-ux.md:35` — **CONFIRMED + FIXED**
     (rows now name `build_run_outcome` for run endings, `cli/error_output.py` for exceptions with no run; agent-ux's
     "Success/error formatters" row → "Run outcome"); `.codex` mirrors regenerated.
  7. W agent-ux W1 — docs say pass `execution_id` or `trace_path` to `pflow report` — **CONFIRMED** (`report.py:76` treats the
     argument as a path) **+ FIXED** ("Pass `trace_path` to `pflow report`").
  8. S simplicity — unused `output_error(ctx, …)` — **FIXED** (pre-existing on `main` too, but this branch reshaped the module; 5 call
     sites, no test calls it directly).
  9. S agent-ux S1 — MCP instructions promise a trace on every run — **FIXED** ("every run that starts … a workflow that fails
     validation never starts"; identity lines "when a trace was written").
  10. S spec-conformance — spec Status / task-review / Windows CI pending — **SKIPPED: close-out work owned by the task
      orchestrator** (Status → done, `create-task-review`, PR CI), not a code defect.
  11. S/split simplicity vs agent-ux — `_outcome_status` second arm — **ruled — orchestrator 01:25 "Accepted deviations"; left
      as is, ESCALATED as open question (b) below** (simplicity: remove + give fixtures explicit status; agent-ux: keep).
  12. Open question (a), all-`not_executed` `execution` on a pre-collector failure — simplicity AND agent-ux both answered **keep**
      (plan §3.1: one rule independent of the collector; the table says explicitly that no step ran). No change.
  13. Spec-conformance note — the plan §6 literal grep also matches the validate-only response (`run.py`), the probe
      (`cli/commands/_probe_impl.py`) and single-node responses (`node_output_formatter.py`); `plan_formatter.py` does not match.
      None is a run-ending document; the lens rules the one-producer requirement **MET** semantically. No change; the plan's
      grep prediction was imprecise (recorded for the task-review).
- Verified: `make check` green; `make test` **11688 passed** (HEAD baseline 11683 + the 1 `TestPerformanceBenchmarks` flake that
  passed this time = 11684, +4 new tests); Task-159 `verify.sh` **87/87, 0 drifted**; examples `capture.py --check` **28 examples,
  0 differing** (no re-record — no capture or case exercises a looping gate or a trailer fault). Mutation check (scratch script,
  originals restored): rebuild-after-fault removed → 2 failed; gate relabel removed → 3 failed; MCP shell-stderr removed → 1;
  MCP cost removed → 2; pricing mirror removed → 1; paused warnings shown under `-p` → 1 — every new/deepened test kills its
  mutant. Real surface: looping gate → approve → deny on this tree prints `Steps completed: 0 of 1.`; paused JSON
  `nodes_executed 0`. Real HOME: `find ~/.pflow -mmin -45` shows only the sanctioned fan-out trace and other sessions' files.
  | Assumed: the trailer-fault test's injected `OSError(ENOSPC)` at `write` stands for every write fault (they share the one
  `except Exception → _disable_streaming` arm); a fault RAISED out of `finalize` itself (e.g. computing aggregates) leaves
  `_stream_path` set — pre-existing, not touched.
- Deviations/surprises: (1) The gate relabel also covers PAUSED, not only the denial the lens reported: a paused-mid-loop step
  whose iteration 1 ran in this attempt now reads `not_executed` (the step vocabulary has no "in progress"; `completed` was false
  for a step waiting at its own gate and would contradict the `0 of 1` its denial prints a moment later) — judgment call, listed
  below. (2) `_settled_outcome` is a new private helper (extracted to hold the rebuild and stay under C901); `_display_execution_result`
  no longer imports `build_run_outcome`. (3) The convergent finding cited plan §4.4's accepted order; the fix preserved it.
- Self-checks: fully happy with the fixes — doubt raised: whether rebuilding (a second `get_summary`, slightly later `duration_ms`)
  only on the fault path is cleaner than "always build after finalize" — kept the conditional so the normal path's printed
  document stays byte-identical to the trailer snapshot. test-reflect: applied by mutation (six mutants above, all killed); every
  new absence has its presence twin in the same medium.
- ESCALATIONS for the orchestrator (none decided here):
  (b) `_outcome_status`'s `success=False`+default-SUCCESS → FAILED arm. Options: A keep (2 lines; no production producer; guards
      exit-0-with-`success:false` for hand-built results) · B delete + give the ~23 fixture constructions `status=FAILED` (one status
      authority; fixture churn, zero user-visible change) · C make the pair unrepresentable at the source (`ExecutionResult`
      derives `success` from `status` or validates in `__post_init__` — touches `execution/result.py` and every constructor; widest).
      Recommend A (1–2/5, reversible) — the lens split itself and the accepted 01:25 ruling stand; B is fine if you prefer one authority.
  (c) FYI (2/5, built): the gate-stopped step is `not_executed` on PAUSED as well as DENIED. Alternative: relabel on DENIED only
      (exactly restores `main`'s denied count; a paused-mid-loop doc would keep counting the gated step completed). Recommend as built.
- Next: orchestrator launches `review-falsifier` on the fixed tree (uncommitted: 14 files + `reviews/completion-gate.md`); resume
  G1 with its report.
- (b) → ruled by orchestrator: success derived from status; arm deleted (2/5, orchestrator 02:15, after reading the dispositions;
  (c) accepted as built). `build_run_outcome` writes `success = status in (SUCCESS, DEGRADED)` (F20 → A's definition), so
  `success`, `status` and `exit_code` cannot disagree in a Run outcome; `_outcome_status` keeps only the non-durable-pause
  normalization; builder + `_outcome_status` docstrings updated (grep: no other restatement in `src/` or the CLAUDE.md files).
  Fixtures: the AST scan of every `ExecutionResult(` in `tests/` + `src/` found only TWO statusless `success=False` constructions
  left (the "~23" of the P1 entry were already given explicit statuses during P2): `tests/test_execution/test_workflow_execution.py:81`
  → `status=WorkflowStatus.FAILED`; `test_run_outcome.py::TestTolerance::test_a_failed_result_built_without_a_status_is_still_a_failure`
  (it pinned the deleted arm) → replaced by `test_success_is_derived_from_the_status` (hand-built `success=True, status=FAILED` →
  document `success: false`, `status: failed`, exit 1; paired `ExecutionResult(success=True)` → `true`, `success`, 0). Mutation:
  `"success": result.success` restored → that test fails (1 failed), original written back. Production unaffected: both runner
  constructions are coherent (`_determine_status` returns `(False, FAILED)` / `(True, DEGRADED|SUCCESS)`; exception path
  `success=False` with an explicit non-success status). Verified: `make check` green; `make test` 11688 passed; `capture.py --check`
  28/0 (verify.sh not re-run — no output can move).
- Falsifier (report `reviews/falsifier.md`, relayed by the orchestrator; 18/19 promises HELD, 0 Critical) — dispositions:
  - **W — a gate inside a sub-workflow child leaves the host step `call` reading `completed` on the failed run — CONFIRMED,
    pre-existing, NOT FIXED here → follow-up issue (write-up below).** Reproduced on this tree AND on `main` `923725b8` with the
    falsifier's `fz/gparent.pflow.md` + `gchild.pflow.md` (isolated HOME, non-TTY, `--output-format json`): exit 1, `failed`,
    steps `prep completed, call completed`, `nodes_executed 2` on both. Root cause (in-process probe of `shared_after`):
    `shared["call"] == {"_pflow_child_workflow_paths": {"call": ".../gchild.pflow.md"}}`, `__failures__` absent,
    `__execution__.completed_nodes == ["prep"]`. (1) `WorkflowExecutor.exec` writes trace bookkeeping into the HOST's namespace
    before the child runs (`runtime/workflow_executor.py:444` → `_record_child_workflow_path` `:741-749`, `parent_shared.setdefault(
    "_pflow_child_workflow_paths", …)` — `parent_shared` is the host's namespaced view); (2) a child gate verdict re-raises
    un-converted by design (`:482-488`, Task 125), so nothing records the host in `__failures__`; (3) `get_node_status`
    (`runtime/node_state.py:84-88`) reads "present and not failed" as SUCCEEDED, so `build_execution_steps`
    (`execution/execution_state.py:131-134`) labels the host `completed`. Why no builder fix: the builder's signals are the store
    (which the executor polluted) and the engine's `completed_nodes`. Making `completed_nodes` the step table's source of truth is a
    source change for every status's table (Task 148 chose `get_node_status`; `--only`/cache/loop/resume bookkeeping would all need
    re-verifying) — a design choice — and keying on "host of a nested gate" from the gate diagnostic would be special-casing (the
    diagnostic names the child's `inner`, not `call`). The honest fix is in the executor/engine (sensitive path; this task has no
    engine contact). Follow-up issue draft:
    - Title: "A gate inside a sub-workflow leaves its host step reading `completed` — executor bookkeeping makes the host namespace
      look like output"
    - Repro: parent `prep` → `call` (`type: workflow`, child's only step `approval: required`); run non-interactively with
      `--output-format json` → exit 1 / `status: failed`, yet `execution.steps[call].status == "completed"`, `nodes_executed: 2`
      (main and this branch); the text progress shows `call...` with no ✗. Contrast: a child failing by exception → `call` `failed`.
    - Root cause: as above — `workflow_executor.py:444/:747` writes `_pflow_child_workflow_paths` into the host namespace at exec
      start; the gate re-raise (`:482-488`) records no failure; `node_state.get_node_status` (`:86`) equates presence with success.
    - Proposed fix (pick one in the lane): A) the engine marks a top-level step whose run ended by a gate exception raised from below
      it as not-completed — e.g. `mark_node_failed`-free: pop the host's namespace / record it as the stopped step, so the Task 148
      invariant holds; B) the executor records the child path somewhere that is not the host's output namespace until the host
      finishes (needs `core/trace_tree.py:600-619`'s reader of `node_output._pflow_child_workflow_paths` re-pointed, and the
      `batch_executor.py:448/:520` twin kept in step). Either closes the class "a step whose run ended at a gate, at any depth, never
      reads completed" at its source; G1's top-level relabel in `run_outcome._execution_block` stays correct beside it.
      Also check the progress line (`call...` with no ✗) in the same lane. Severity: low (wrong count on a failed run; no data loss).
  - Obs 1 — pre-run CLI error documents (file not found, piped input unroutable, newer attempt exists) carry only
    `{success,status,error,errors,diagnostics,workflow}` — **out of scope by plan §3.5** (no `ExecutionResult` exists; Task 117's
    subcommand-JSON territory) → note for the task-review.
  - Obs 2 — non-durable gate after a trace write fault: the fallback remediation lists `--no-trace`/inline/`--only`/unsupported
    position, none of which applies — **pre-existing (falsifier: main identical), out of scope** (the text is
    `GateNotInteractiveError`'s remediation in `core/exceptions.py`, not this task's renderer) → task-review note / candidate issue.
  - Obs 3 — resuming a saved workflow reports `workflow.action: "unsaved"` — **pre-existing, NOT changed by this branch** (verified,
    isolated HOME, `pflow save` → run by name → `resume --approve yes --output-format json`): resumed document
    `{'action': 'unsaved', 'name': 'g184-saved-gate'}` on BOTH `main` and this branch. Cause: `cli/commands/resume.py:161,180` keys
    `action` on `resolved.source == "library"`, and a resume resolves the workflow from the trace's file path (source `file`);
    `resume.py` is untouched by the committed branch (`git diff origin/main...HEAD -- resume.py` is empty; the only working-tree edit is G1's `output_error` call site).
    One branch-side difference noticed: the fresh PAUSED document by name now carries `{'action': 'reused', 'name': …}` where `main`
    had no `workflow` key at all (D1's common keys) — intended. → task-review note.
  - No code changed for the falsifier report (the gate-host fix is the follow-up above); `make check`/`make test` not re-run — tree
    unchanged since the (b) entry's green gate.

## [2026-10-12 02:45] task-orchestrator (Opus) — completion gate closed
- Did: read G1's dispositions (7-lens codex battery: 0 C / 7 W / 4 S — 9 fixed, 1 skipped as close-out work, 1 ruled, 2 no
  change) + the falsifier (direct launch, report `reviews/falsifier.md`: 18/19 HELD, 0 Critical). Ruled (b) (02:15, 2/5):
  document `success` derived from the normalized status; (c) accepted as built.
- Falsifier W (sub-workflow gate leaves its host `completed`; pre-existing on main) → filed **#828** (root cause at the executor's
  host-namespace bookkeeping + `get_node_status`; engine/executor fix, lane A). Observations → task-review notes (pre-run error
  documents out of scope by §3.5; write-fault fallback remediation text pre-existing; resumed saved workflow `action: unsaved`
  pre-existing, branch unchanged).
- Next: commit; `make test-all-local`; spec Status → done; `create-task-review`; `create-pr`.

## [2026-10-12 03:00] task-orchestrator (Opus) — close-out
- Did: merged `origin/main` `f2da18e2` (#825; clean); `make check` green; `make test-all-local` 11796 passed / 2 skipped;
  Task-159 `verify.sh` 87/87; examples `capture.py --check` 28/0; own real-surface spot-check (isolated HOME): exception failure
  text (❌ line, warnings before the error, resume hint, one trace line), paused JSON key set, resumed denial (`0 of 3` + `⤷`).
- Wrote `task-review.md`; spec Status → done, Completed 2026-10-12. Next: `create-pr`.
