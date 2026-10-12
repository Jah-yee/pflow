# Task 184 Review: One Run Outcome — a Single Document for Every Way a Run Ends

## Metadata
- Built 2026-10-11 → 2026-10-12 on `feat/task-184-run-outcome`. Main was merged in four times, the last at `f2da18e2`. Closes #695, #699, #737. Refs #754, #748, #801, #799 (none closed). Follow-up filed: **#828**. Not a trace-format change (the version stays 2.10.0).
- Who did what:

  | Agent | Work |
  |---|---|
  | Planner (Fable) | the plan + the CP-1 checkpoint |
  | Task orchestrator (Opus) | delegation, rulings, close-out |
  | I1 (Opus, medium) | P0 |
  | I1b (Opus, high) | P1, the P1 mid-task review, P2+P3, P4 |
  | G1 (Opus, high) | the completion gate: 7 lenses on codex, plus evaluating the falsifier's report |

- User rulings:
  - **CP-1 Q1–Q4**, all four as recommended (`implementation/show-before-code.md`):
    - one `-p` tier rule for every status;
    - a uniform MCP identity block;
    - `errors` is always a list;
    - one emission site for the trace line.
  - **F20 → A:** `success` means the run completed, so it is true iff the exit code is 0.
- Where things are recorded:
  - The journey, every deviation, every gate finding and its disposition, and the AFTER transcripts (CLI and MCP, all endings): `implementation/progress-log.md`.
  - Review reports: `implementation/reviews/` — plan review, P1 mid-task review, the completion battery, and the falsifier.

## Read First — the load-bearing block
- **What exists now:** one function, `build_run_outcome(result, workflow_ir, *, workflow_metadata, output_key)`, turns ANY `ExecutionResult` into one `RunOutcome`: the `document` dict plus the same Diagnostics left unserialized. CLI JSON emits `document` unchanged. CLI stderr (`render_cli_stderr`) and the MCP `workflow_execute` text (`render_mcp_text`) render from that same value. Every status has one shape:
  - **Common keys, always present:** `success`, `status`, `workflow`, `errors`, `warnings`, `advisories`, `diagnostics`.
  - **Present when the run has them:** identity (`execution_id`/`trace_path`), metrics (`duration_ms`, `total_cost_usd`, `metrics`), and `execution`.
  - **Present by status:** `result`, `error`, `gate`, `resume_command`.
- **Read these first:**
  - `execution/formatters/run_outcome.py`: `build_run_outcome`, `_outcome_status`, `_execution_block`, `_gate_payload`, `_resume_command`, `render_cli_stderr`, `render_mcp_text`.
  - `cli/commands/run.py`: `_settled_outcome` (trace settling and its order) and `_display_execution_result` (the stdout/stderr split and the exit code).
  - `mcp_server/services/execution_service.py::execute_workflow`: build, render, then return, or raise on failure.
  - `execution/runner.py::_exception_to_result`: `metrics_collector` is REQUIRED.
  - The guards: `tests/test_execution/formatters/test_run_outcome.py` (`COMMON_KEYS` / `IDENTITY_KEYS` / `METRICS_KEYS`).
- **Invariants that must NOT break:**
  1. **No other code path builds a run-ending dict.** A new field goes into `build_run_outcome` once, and every channel gets it. A second builder re-opens the drift class this task closed: the four issues were the N−1 places a field wasn't added.
  2. **Identity is the trace FILE.** `execution_id` and `trace_path` appear together, iff `result.trace.trace_path is not None` AFTER settling. `--no-trace`, a stream fault and a trailer-write fault all leave both absent. An id with no file behind it sends `pflow report` / `pflow resume` to nothing.
  3. **Settling order in `_settled_outcome`:**
     - Non-success: finalize FIRST, then build. A compile-time failure only gets its trace file at finalize.
     - Success: build → `set_json_output(document)` → finalize → rebuild ONLY IF finalizing cleared `trace_path`.
     - Reordering it breaks one of two promises: either "a pre-engine failure names its trace" or "the trailer snapshots the printed document".
  4. **`success` is DERIVED from the normalized status** (`status in (SUCCESS, DEGRADED)`), never copied from `result.success`. That way `success`, `status` and `exit_code` cannot disagree (F20 → A). `_outcome_status` normalizes exactly one case: a non-durable PAUSED becomes FAILED, keeping the gate's ERROR diagnostic as the failure's errors.
  5. **Absent, never `null`, binds only the outcome's OWN optional keys.** Producer nulls stay:
     - `total_cost_usd: null` (the pricing tri-state, next to its discriminators);
     - the canonical gate payload's `question` / `recommendation` / `iteration` / `max_iterations` (ADR-0009);
     - a `?? null` output.

     No recursive null-stripping, ever.
  6. **`nodes_executed` has one meaning:** steps completed in THIS attempt, `execution.nodes_executed` only. Restored steps are not executed. The step a top-level gate stopped is never `completed` (`_execution_block` relabels `gate.node_id`). The attempted count (`metrics.workflow.nodes_executed`) is deleted at its source in `core/metrics.py`; don't re-add it under that name.
  7. **The gate block (`gate_lines` + `answer_lines`) renders for PAUSED only, on both channels.** A denial is final: rendering `To answer:` or the "approve every remaining iteration" hint after it invites a dead command. The denied `gate` dict stays in the JSON document.

## What Was Built (actual vs. planned)
Phases ran P0 → P1 → mid-review → P2+P3 → P4 → gate. Deviations that carry knowledge:
- **P0.** The plan's fixture (a `code` step that raises) never reaches `_exception_to_result`, because the node converts the exception into an `error` action. Exception-path tests use a strict template-resolution failure (`${first.stdout.b}` on non-matching JSON). A missing required input referenced inside a shell `command` is a VALIDATOR error, not a compile-time one; route it via `env:`. `metrics_collector` was made a required kwarg so a future second call site cannot silently drop metrics again.
- **P1.**
  - `exit_code` is a property over `EXIT_CODES` (0/0/1/3/4), not a field.
  - `format_stderr_warnings` now previews with `core.diagnostic_render.head_tail_preview`, the #755 carry-in. The old `stderr[:300]` hid the cause that tools write last.
  - The probe helper `format_error_text(errors, warnings)` lost the plan's `trace_path` parameter, because the probe is traceless and the value was always empty.
- **P2/P3 renderer rulings:**
  - **Final stderr order** (the MCP order matches): completion line + `⤷` lines → batch item errors → shell stderr → cost → `⚠️ Warnings:` / `ℹ️ Advisories:` → errors block → resolved-outputs note → gate lines → `To answer:` → `To resume…` → `Workflow trace saved:`.
    - Warnings render BEFORE errors, a change the main orchestrator authorized from a consumer report: `2>&1 | tail` used to show an unrelated warning instead of the cause.
    - Under `-p` the leading blank line is dropped.
  - **Paused TEXT** prints the stdout token line FIRST, as show-before §3 says ("text unchanged"). JSON mode prints stderr (including the trace line) before the document, per Q4.
  - **A denial renders no errors block.** The denied line says it; the gate diagnostic stays in the document's `errors`.
  - **A FAILED outcome with zero errors** renders `❌ Workflow execution failed — no error details were recorded`. The old "Node returned error action" was a guess about the cause.
  - **The MCP advisory policy is renderer policy:** only `parser`/`validator` INFO appears in the MCP text. The document is identical on both channels.
- **P4.**
  - The hand-written `docs/changelog.mdx` entry was reverted. The changelog is generated at release (`.claude/skills/release/SKILL.md`), so the PR body carries the text instead.
  - The `engine.py` edit is comment-only: the `__trace_collector__` readers list.
- **Completion-gate fixes:**
  - A trailer-write fault on a SUCCESS run used to keep identity and print `Workflow trace saved:` → rebuild after settling.
  - A resumed looping gate that was then denied printed `Steps completed: 1 of 1` (main: `0 of 1`) → the gate relabel. That one was a regression introduced by this branch; the battery caught it, and it is fixed.
  - `success` derived from status (the class closed at the document instead of a second normalization arm).
- **Not built (ruled or scoped):**
  - `--dry-run` keeps its plan document: a plan has no run identity.
  - The pre-execution exception documents in `cli/error_output.py` stay separate, because no `ExecutionResult` exists for them. They carry no `warnings`/`advisories` (the falsifier noted this; it's Task 117's territory).
  - Plan §8's `tests/fixtures/run_outcome/` was skipped, since no test reads it.
  - #804 member (d), `_show_workflow_help`, is two defects plus a new home for the `Source:` line — more than a one-line caller fix, so it was left for #804's lane.

## Patterns & Anti-Patterns
- **One value, N thin renderers.** The `RunOutcome` value is the seam. Renderers compose shared module-private section functions (`completion_line`, `mode_lines`, `errors_block`, `diagnostic_sections`, `gate_lines`, `answer_lines`, `identity_lines`, …).
- **Rejected alternatives:**
  - One renderer with a `channel` flag: the CLI has a stdout/stderr split and MCP needs greppable identity lines, so they differ in kind.
  - Rebuilding Diagnostics from the printed dict so renderers read only the dict: that is a second serializer.
  - Bolting status arms onto the old `format_execution_success`: its loose-argument signature caused the drift in the first place.
- **Close the class at the document, not the instance.** `success` derived from status, and the gate relabel keyed on the gate payload, are both one-site rules. The rejected alternatives were per-fixture repair and per-renderer special-casing.
- **Tier table as THE `-p` spec** (plan §2):
  - The *must-act* tier always prints: errors, failed-batch item errors, gate plus answer, the resume hint, `⤷` lines.
  - The *summary* tier is hidden by `-p`: the completion line, cost, warnings, shell stderr, a degraded run's batch errors, the trace line.
  - Add a new stderr section by choosing its tier, never with a per-status `if print_flag`.
- **Anti-pattern: a hand-typed `success_dict` fixture.** Outcome tests build real `ExecutionResult`s through an in-process `WorkflowRunner().run(...)`, or construct the dataclass directly with an explicit `status=`. A statusless `ExecutionResult(success=False)` is now a visibly wrong fixture: it renders as success.

## Gotchas & Non-Obvious Coupling
- **The stream opens in the ENGINE** (`engine.py start_streaming`), not when the collector is built. A failure after collector creation but before the engine runs has `trace_path is None` until `finalize()`. MCP finalizes inside `runner.run` and the CLI does not, which is why the CLI settles before building.
- **`--no-trace` still mints an `execution_id`** (the collector exists with `stream_to_disk=False`). Never key identity on the id.
- **The trailer's `json_output`** is written for json-mode SUCCESS/DEGRADED only. It means "a snapshot of the printed document", not a versioned trace sub-contract. Its content now follows the document: it gained identity and `errors: []`, and lost the two attempted counts. Its one reader, `ui/run_node.py`, reads `["result"]`, which is unchanged.
- **The step table's truth comes from the store** (`build_execution_steps` → `node_state.get_node_status`: "present and not failed" = completed), not from the engine's `completed_nodes`.
  - The top-level gate relabel patches the looping/resumed case.
  - **A gate inside a sub-workflow** still leaves its host `completed`, because the executor writes `_pflow_child_workflow_paths` into the host namespace before the child runs. This is pre-existing and filed as **#828**; the fix is executor/engine work.
- **`build_execution_steps` runs for every status when the IR has nodes.** So a pre-collector validation failure (the `invalid/*` examples) carries an `execution` table of all-`not_executed` steps and no `duration_ms`. Both simplicity and agent-ux lenses said keep it: it says explicitly that no step ran.
- **Task-170 examples capture** (`capture.py`) masks `trace_path` by key, because the file name carries a timestamp; UUIDs are already masked. **Task-159's `normalize.py` has NO `trace_path` mask**: no case records a run's JSON document today. A new case that does must add one, or it is non-deterministic.
- **The `registry_run` probe text** (`format_error_text`) still renders errors BEFORE warnings, unlike the run renderers. That is #748's surface.
- **`test_workflow_output_handling.py`** drives the JSON path with a mocked compile that returns a bare `ExecutionResult` (no trace, no metrics, empty store). The builder must tolerate that; `TestTolerance` pins it.
- **Flakes seen under xdist load, unrelated to this task:** `test_compiler_integration.py::TestPerformanceBenchmarks` and `test_third_party_compile_warnings.py` (a litellm `ResourceWarning`). Both pass when run alone.

## Integration Points
- **JSON contract change (`--output-format json`, all statuses — breaking, no external users):**
  - **Dropped:** top-level `nodes_executed`, `metrics.workflow.nodes_executed`, `checkpoint`, `paused_node_id`, `gate_request` (now `gate`, with `node_id` inside).
  - **Gained:** identity on success; `workflow` / `execution` / metrics / `warnings` / `advisories` on failure, pause and denial; lineage on every resumed ending.
  - **`errors`** is `[]` on success and pause. **`diagnostics`** is errors-first.
- **MCP `workflow_execute` text:** it ends with `status:` / `execution_id:` / `trace_path:` / `resume_command:` lines (present keys only). The `paused_node_id:` line and the 3-error cap are gone, and a pause leads with `⏸ Workflow paused at '<id>'`. Failure is still a raised `RuntimeError` carrying the text. Task 152 (structured MCP responses) gets ONE dict to serialize.
- **Where a whole-document value scrub (#801) attaches:**
  - **For all channels at once:** the return of `build_run_outcome`. It must scrub `document` AND the three Diagnostic lists, because the text renderers format the `Diagnostic` objects, not the dict.
  - **CLI JSON:** `_serialize_json_result(outcome.document)` (`run.py::_display_execution_result`), plus the trailer write `trace.set_json_output` (`run.py::_settled_outcome`).
  - **CLI stderr:** the `render_cli_stderr` line loop.
  - **MCP:** `render_mcp_text`'s return (`execution_service.py::execute_workflow`).
  - **Not covered by the outcome:** the text-mode stdout VALUE (`_handle_text_output`, from `shared_after`) and `-o`. That is where **#799 Residual 1** lives: raw `child_failure` via `-o each.errors`, a declared `${each.errors}` (CLI and MCP `result`), or a child's batch output in a successful parent. Those shapes reach the printer unrecognized by the printing compactor, and they are members of #801's pass.
- **`ui/server.py`'s six raw `to_dict()` error bodies** (`:366, :391, :749, :830, :1065, :1146`) are NOT covered, by construction. They are pre-run validation/preflight 4xx bodies with no `ExecutionResult`, so the run outcome never sees them. They are a printing-redaction question (#799 sibling list / #801), not this builder's.
- **Instruction surfaces updated:**
  - `cli/CLAUDE.md`, `execution/formatters/CLAUDE.md`, `mcp_server/services/CLAUDE.md`;
  - `guide/features/{resume,approval}.md`;
  - `docs/reference/cli/index.mdx`;
  - `mcp-agent-instructions.md`;
  - agent defs `pflow-codebase-searcher`, `review-{agent-ux, architecture-fit, feature-interactions, impact-completeness, silent-failures}` (+ `.codex` mirrors).
- **Re-recorded:**
  - Task-159 cases `02-validator-errors/02, 03, 05` (warnings before errors) and `15-run-flag-interactions/03` (`⤷` under the completion line).
  - All 28 Task-170 example captures.
- **Seen, not fixed (candidate issues for the main orchestrator):**
  - (a) After a trace write fault, a non-durable gate's fallback remediation (`GateNotInteractiveError`, `core/exceptions.py`) lists `--no-trace` / inline / `--only` / an unsupported position — none of which applies. Main is identical.
  - (b) Resuming a saved workflow reports `workflow.action: "unsaved"`, because `cli/commands/resume.py:161,180` keys `action` on `resolved.source == "library"` and a resume resolves the workflow by file. Pre-existing; this branch doesn't change it.
  - (c) The shell-failure text repeats its reason (headline + `Stderr:`) with `Env:` between them. That is `format_diagnostic`'s rendering of one diagnostic, not a renderer section.
  - (d) The resume hint is offered for a workflow with no side effects. That is `has_resumable_step()` policy.

## Tests That Matter
- **`tests/test_execution/formatters/test_run_outcome.py`** (builder + sections, all from real results):
  - `TestEveryEndingHasOneShape` (the key tables, per status: presence and absence);
  - `TestAbsentNeverNull` (paired with the producer nulls that must survive);
  - `TestPausedCarriesNoError` (including the non-durable → FAILED normalization);
  - `TestLineageOnEveryEnding`, `TestOnlyTarget` (`nodes_skipped` excludes the target; the not-ran wording), `TestTolerance`;
  - `test_success_is_derived_from_the_status`;
  - `TestRenderCliStderr`, `TestCostLines`.
  - P1 killed 16 source mutations; the gate killed 6 more.
- **`tests/test_cli/test_run_outcome_cli.py`** (the real CLI):
  - `TestTheSpecsKeyTablesOnRealCliJson` (the spec's guard on the adapter);
  - `TestFailureByExceptionKeepsItsMetrics` (#699);
  - `TestLineageOnFailedAndDenied` (#737);
  - `TestIdentityOnSuccessJson` (#695);
  - `TestPrintFlagNeverChangesTheJson`;
  - `TestTiersUnderPrint` (every absence paired with a presence in the same stream, including `test_the_paused_token_line_comes_before_the_gate_content`);
  - `TestATrailerWriteFaultLeavesNoIdentity` (a real `_flush_line` → `_disable_streaming` arm);
  - `TestCompileTimeFailureCarriesIdentity`;
  - `TestADenialRendersNoAnswer` (looping gate, pins `0 of 1`).
  - P2 killed 15 renderer mutations.
- **`tests/test_integration/test_cli_mcp_parity.py`:**
  - `test_cli_and_mcp_carry_the_same_identity_and_warnings`;
  - `test_mcp_failure_names_its_metrics_and_identity`;
  - `test_mcp_failure_lists_every_error_not_three`;
  - `test_mcp_shows_definition_advisories_and_leaves_runtime_ones_to_the_document`;
  - `test_mcp_pause_names_the_step_and_its_gate`;
  - `test_a_failure_before_the_engine_ran_names_the_same_identity_on_both_channels`.
- **`tests/test_execution/test_runner.py::TestResultCarriesRunMetrics`:** the exception path carries THE run's collector; a pre-collector failure carries none.
- **Keep green, untouched:** `tests/test_cli/test_json_diagnostic_redaction.py`. Its AST ratchets scan `execution/formatters`, so `run_outcome.py` must stay there; another ratchet pins the raw batch compactor to the runtime.
- **Outer nets:** Task-159 `verify.sh` (87/87) and `capture.py --check` (28/0).

## Real-surface evidence
CLI text / JSON / `-p` and MCP `execute_workflow` were exercised on every ending, with an isolated HOME. The condensed AFTER transcripts are in the progress log's P2, P3 and P4 entries.

The falsifier then drove 19 promises through the real `cli_main`, `pflow resume`, piped stdin, a pty denial, real ENOSPC/read-only trace faults and MCP. 18 held. The 19th, the nested-gate host step, is #828: pre-existing, not a regression.

---
*Distilled from the implementation context of Task 184. The chronological journey lives in `implementation/progress-log.md` — this review is the durable forward-reference, not a re-narration of it.*
