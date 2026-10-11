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
