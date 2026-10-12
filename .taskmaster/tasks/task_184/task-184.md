# Task 184: One Run Outcome — a Single Document for Every Way a Run Ends

## Description

A run ends in one of five ways — success, failure, paused at a gate, denied at a gate, or a
dry-run plan — and pflow renders that ending on three channels: CLI text, CLI JSON, and the MCP
server's response. Today thirteen separate functions assemble those endings, so which fields a
reader gets depends on which function happened to run: the success document has no run identity,
the failure document has no trace path, resume lineage appears only on success, metrics vanish
when a node failed by exception, and `nodes_executed` means two different counts in one document.
Build the ending once: one document built from the execution result, rendered per channel.

## Status

done

## Completed

2026-10-12

## Priority

medium

## Roadmap

next

> Drafted 2026-10-11 by the main orchestrator (session-14) from two independent searcher passes (native + codex offload)
> over `main` `3a7643c8` that converged on every claim; re-verified by the planner on `05884642` (post-Task-120 — the
> `runner.py` cites below are the current ones; the rest held). D1–D4 **DECIDED** by the user 2026-10-11 (*"go ahead with
> your recommendations for standing decisions"*). The plan's embedded checkpoint (`implementation/show-before-code.md`,
> Q1–Q4) rules the remaining presentation choices before implementation.

## Problem

Observed, each filed from an executed dogfood run:

- **#695** — the CLI JSON *success* document carries neither `execution_id` nor `trace_path`; the failed and paused CLI
  documents carry `execution_id`, and the MCP success response carries both. An agent parsing stdout cannot find the trace
  of the run it just made; `pflow report` with no path defaults to "most recent", which is racy under parallel agents.
- **#699** — a run that fails by *exception* (template resolution, HTTP timeout) loses its metrics: no `❌ Workflow failed
  after Xs` line, no `metrics` / `total_cost_usd` / `nodes_executed` in JSON. A run that fails by *error action* (HTTP 404,
  shell non-zero) keeps them. Where metrics are present, `nodes_executed` at the top level counts attempted nodes while
  `execution.nodes_executed` counts completed ones.
- **#737** — a resumed run's lineage (`resumed_from`, restored-step count) is rendered only on success. A resumed attempt
  that is denied prints `Steps completed: 0 of 3` as if nothing ran; a resumed attempt that fails has no `resumed_from` in
  its JSON, contradicting `guide/features/resume.md:21`.
- The MCP paused response drops the warnings the CLI paused document keeps (`execution_service.py:197-217` vs
  `cli/commands/run.py:659`).

**Why they are one problem.** The run ending is assembled by 13 builder functions (15 format-specific paths) across 25 live
outcome × channel cells, and only the success cell shares a builder — `format_execution_success`
(`execution/formatters/success_formatter.py:27`), which takes loose arguments rather than the `ExecutionResult`, so each
caller bolts identity on itself: the CLI passes `trace_path=None` (`cli/workflow_output.py:902`), MCP patches `execution_id`
in afterwards (`execution_service.py:77-89`). Failure (`cli/error_output.py:55` + `execution/formatters/error_formatter.py:18`),
paused (`run.py:645`), denied (`run.py:508`) and the MCP text builders (`execution_service.py:120, 187`) are each bespoke.
`format_execution_errors` says it is shared with MCP (`error_formatter.py:3-4`); MCP never calls it. Every new field — identity,
lineage, warnings, metrics — has to be added N times, and the four issues above are the N-1 places it was not.

One of the gaps is below presentation: the runner's exception path builds its `ExecutionResult` without `metrics=`
(`execution/runner.py:946-952`; the normal return passes it at `:446-453`). No document builder can recover what the
result never carried.

## Solution

- **One run outcome.** An `ExecutionResult` (any status) becomes one document through one function. The document has one
  shape; `status` is a field, not a different document. Outcome-specific sections (`gate` for paused/denied, `errors` for
  failed, `result` for success) are present or absent by status; everything a run has regardless of how it ended — identity,
  trace path, lineage, metrics, warnings, the step table — is always there.
- **Renderers consume the document.** CLI JSON emits it. CLI text and the MCP text response render *from* it (the MCP
  response stays text; it is built from the same dict, not a parallel one). `-p` is a presentation flag on the text renderer,
  not a separate builder.
- **The result carries what the document needs.** Both runner return paths construct `ExecutionResult` the same way
  (metrics included); the document never reaches around the result to the collector or the trace.
- **One meaning per field.** `nodes_executed` means completed steps everywhere; the attempted count is dropped or gets its own
  name — never the same name with another meaning.
- `--dry-run` keeps its own plan document (`plan_formatter.py`) — it is a plan, not a run ending — but gains the same identity
  convention if the planner finds it cheap; otherwise out of scope.

## Design Decisions

- **DECIDED (user, 2026-10-11) — D1: one JSON shape for every status.** Failed, paused and denied documents gain the success
  document's common keys (`execution_id`, `trace_path`, `execution` with lineage, `metrics`, `warnings`, `advisories`,
  `diagnostics`); success gains `execution_id` + `trace_path`. This changes the JSON agents read. We have no external
  users (root CLAUDE.md), the change is cheap now and expensive later. Alternative: keep the five shapes and copy fields
  across — rejected as the instance-fix route the user ruled out (*"we should always strive to close bug classes rather
  than bugs"*).
- **DECIDED (user, 2026-10-11) — D2: `nodes_executed` = completed steps, one definition.** The attempted count (today `len(node_timings)`,
  `core/metrics.py:316`) is dropped from the document unless the planner finds a consumer; if kept, it is `nodes_attempted`.
- **DECIDED (user, 2026-10-11) — D3: the MCP `workflow_execute` response stays text but is rendered from the one document**, so it can no
  longer drift from the CLI (today it drops paused-run warnings and never shows metrics on failure). A structured MCP
  response is Task 152's question, not this task's.
- **DECIDED (user, 2026-10-11) — D4: `trace_path` appears once known, on every status.** Per #695's verify-at-start: the trace path is readable
  before the document is emitted (`runtime/workflow_trace.py:1161-1170`, "valid before AND after `finalize()`" — searcher-
  verified, re-verify). When tracing is off, the key is absent, never `null`.
- **DECIDED by precedent — restored steps are not counted as executed** (`runtime/engine/CLAUDE.md`; #737). The document
  shows lineage (`resumed_from`, `nodes_restored`) and the completed count of THIS attempt; the display changes, the engine
  counts do not.
- **Out of scope by ruling:** #748 (MCP `registry_run` drops warnings) is the single-node probe adapter
  (`execution_service.py:724-769`), a different surface — a lane after this task, reusing whatever warnings section the
  document defines. The web UI reads the trace trailer, not this document (`ui/run_tailer.py:625-649`) — untouched.
  `pflow report` — untouched.

## Dependencies

None that block starting. Coordinate-with: **Task 120** edits `cli/commands/run.py` and
`mcp_server/services/execution_service.py`; this task starts after 120 merges so its planner cites the post-120 lines.

## Requirements

### The document
- One function builds the document from an `ExecutionResult` for every status: `success`, `failed`, `paused`, `denied`.
  No other code path assembles a run-ending dict (the thirteen builders listed in the Problem are deleted or reduced to
  renderers over this one).
- Present for every status when the run has them: `execution_id`, `trace_path`, `workflow`, `status`, `success`,
  `execution` (step table, `nodes_executed` = completed, `resumed_from` + `nodes_restored` when resumed), `metrics`,
  `duration_ms`, `total_cost_usd`, `warnings`, `advisories`, `diagnostics`.
- Present by status only: `result` (success; partial resolved outputs on an output-resolution failure, as #754 ruled),
  `error` (failed, denied — the summary string), `gate` + `resume_command` (paused), `gate` (denied), `resume_command`
  (failed, only when the run is resumable).
- `errors` is always a list — empty on success and on a pause (a pause carries no error; agents branching on
  `success == false` iterate it without a guard), the gate diagnostic on a denial.
- `execution_id` and `trace_path` are present together, exactly when the trace streamed to disk (`--no-trace` and a
  mid-run stream fault leave both absent — an id with no file to resolve against is not run identity).
- A key is absent, never `null`, when the run genuinely has no value for it (no trace → no `trace_path`; not resumed →
  no `resumed_from`; no metrics collector → no `duration_ms`). This binds the document's own optional keys; a `null` that
  a producer means stays (`total_cost_usd: null` is the pricing tri-state; a `?? null` output; the canonical gate payload's
  `question`/`recommendation`/`iteration`).
- A failure raised before the engine ran (a compile-time input error) still carries `execution_id` and `trace_path`: the
  CLI settles the trace before building the document, as MCP already does, so the two channels never disagree on identity.

### The result
- `ExecutionResult` is constructed the same way on the normal and the exception return path of the runner; a run that
  fails by exception carries metrics (when the collector exists) exactly as a run that fails by error action.

### Renderers
- CLI JSON (`--output-format json`, with or without `-p`) emits the document unchanged.
- CLI text renders the document; the `❌ Workflow failed after Xs` line, the `⤷ Resumed from …` line, cost, warnings and
  the trace line each appear for every status that has the underlying field — not for a subset of failure kinds.
- `pflow resume … --approve no` (denied) shows this attempt's completed count AND its lineage.
- The MCP `workflow_execute` text response is rendered from the document: identity and trace path on every status;
  warnings on paused; metrics on failure. A failed run is still a raised `RuntimeError` carrying that text (the server
  boundary renders raises); success and a durable pause return it.
- `-p` suppresses the stderr summary and the trace line as today; it never changes which fields the JSON carries.

### Guards
- A test enumerates the common key set once and asserts it on a real success, failure-by-exception, failure-by-action,
  paused and denied run (CLI JSON) — presence AND absence halves per ORCHESTRATION's Definition of done.
- A CLI↔MCP parity test: the same run through both channels yields the same identity, lineage and warning content.
- Tests that pin today's bespoke shapes (listed in References) are updated to the one shape, not duplicated.

## Implementation Notes

- The two searcher reports (local, `scratchpads/session-14/verify/builders.out` and the native pass logged in
  `.taskmaster/orchestration/sessions/session-14.md`) hold the full builder inventory, the cell map, the field matrix and
  the list of tests pinning each shape. The planner reads them, then re-derives against post-120 main.
- `format_execution_success` is the seed: it already builds the richest document and already has three callers. The
  likely shape is that it becomes the one builder (taking the `ExecutionResult`) and `format_execution_errors`,
  `_display_paused_result`, `_display_denied_result`, `_build_error_text`, `_format_paused_text` become renderers or go.
- Every diagnostic in a printed document is `Diagnostic.to_output_dict()` (redacted; #776/#781/#788 shipped) — the
  builder inherits that representation.
- `execution_id` on failure is today conditional on resumability (`run.py:629-651`, `_resumable_execution_id`); the
  document carries identity whenever the trace streamed and `resume_command` only when resumable
  (`trace.has_resumable_step()`, the one in-memory suppressor).
- A paused `ExecutionResult` carries the gate's ERROR diagnostic (`exception_to_diagnostics(GateNotInteractiveError)`);
  it stays on the result — the non-durable-pause fallback renders it as the failure's error — and is dropped from the
  paused document only.
- `_build_error_text` also serves the `registry_run` single-node probe (`execution_service.py:791`, the #748 surface);
  the probe keeps a thin errors+warnings text helper built from the same section functions, not the run document.
- The guide (`guide/features/resume.md`, `guide/core.md` output sections), `docs/reference/cli/`, and the MCP instruction
  resources describe the JSON shape — all updated by this task; the Task-159 baseline (`.taskmaster/tasks/task_159/
  baseline/verify.sh`) re-records the cases whose output text changes, named per case in the PR body.

## Verification

- Requirements "The document" and "Renderers" exercised on the real surface: one workflow driven to each of the five
  endings through `uv run pflow` (text, JSON, `-p`) and through MCP `workflow_execute`; outputs pasted in the task-review.
- The failure-by-exception run (an HTTP timeout) prints the `❌` line and carries `metrics`; the resumed-then-denied run
  prints lineage and a non-zero completed count only if steps completed in THIS attempt.
- `make test-all-local` green; Task-159 baseline green after re-record; `tests-windows` green.

## Resolved at start (planner, 2026-10-11)

- `--dry-run`'s plan document stays as is: a plan is not a run, so there is no run identity to add (no trace, no
  execution id exists before a run starts). `tests/test_cli/test_dry_run.py`'s exact key set is unchanged.
- No consumer reads the attempted count: top-level `nodes_executed` is read by no `src/`, MCP or `web/` code (the web UI
  reads the trace trailer's own `nodes_executed`, a different field); only four success-run tests and one docs example
  show it. It is dropped, and so is its source copy `metrics.workflow.nodes_executed` (`core/metrics.py`, derivable from
  `node_timings`). The trace trailer's per-visit count is the trace format's and is out of scope.
- The step table has one source already: `execution/execution_state.py:build_execution_steps` serves the JSON `execution.steps`
  and both text renderers (which call it with `metrics_summary=None`). It stays the one source; the document's `execution`
  block is built from it for every status.

## References

- Issues: #695, #699, #737 (owned; closed by this task), #748 (adjacent, out), #754 (partial `result` on failure, ruled),
  #171/Task 171 (identity on MCP success).
- Builders (main `05884642`): `cli/workflow_output.py:125, 806, 881`; `execution/formatters/success_formatter.py:27, 315`;
  `cli/error_output.py:55, 129, 172`; `execution/formatters/error_formatter.py:13`; `cli/workflow_errors.py:40`;
  `cli/commands/run.py:517, 562, 654`; `mcp_server/services/execution_service.py:130, 197, 314-348`;
  `execution/runner.py:446-453, 946-952`.
- Tests pinning today's shapes: `tests/test_integration/test_metrics_integration.py:152-189, 713-751`;
  `tests/test_cli/test_unified_error_output.py:83-109, 376-432`; `tests/test_cli/test_enhanced_error_output.py:137-163`;
  `tests/test_cli/test_resume_cli.py:939-959`; `tests/test_cli/test_paused_cli.py:80-123`;
  `tests/test_cli/test_approval_gate_cli.py:54-82`; `tests/test_runtime/test_resume_engine.py:488-515`;
  `tests/test_mcp_server/test_execution_workflow.py:87-98, 303-316, 354-367, 402-423`.
- Domain nouns: `context/CONTEXT.md` — Run, Resume, Paused, Resume token. New term (ratified 2026-10-11, in CONTEXT.md): **Run
  outcome** — the one document describing how a Run ended, rendered per channel. _Avoid_: result (collides with the
  `result` field), report (collides with `pflow report`), summary.
