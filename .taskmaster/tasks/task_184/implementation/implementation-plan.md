# Task 184 — Implementation plan: One Run Outcome

Planner: Fable, 2026-10-11, worktree `feat/task-184-run-outcome` @ `05884642` (== `origin/main`; Task 120, #776/#781/#788,
#757/#761 all merged). Spec: `task-184.md` (D1–D4 ruled). Governing issues #695, #699, #737 (closed by this task); #754
(ruled, kept), #748 (out — the probe adapter). **Embedded user checkpoint CP-1:** `implementation/show-before-code.md` —
four questions (Q1–Q4) ruled BEFORE P1 starts; §3/§4 below are written on the recommendations and name where each ruling
lands. **CP-1 RULED 2026-10-11 by the owner — all four as recommended** (Q1 one `-p` tier rule; Q2 uniform MCP identity
block, `paused_node_id:` line and the 3-error cap dropped; Q3 `errors` always a list; Q4 one trace-line emission site, before
the payload in JSON mode) — §2–§4 stand as written. **F20 → A, user, 2026-10-11:** `success` = the run completed (true iff exit 0);
paused/denied stay `false`, `status` says why — §3.3 unchanged; P4 rewords `docs/reference/cli/index.mdx:331` and
`guide/features/approval.md:12`. **#755 carry-in:** the moved `format_stderr_warnings` previews via
`core.diagnostic_render.head_tail_preview`, not `stderr[:300]` (P1). Self-reviewed: plan-mode deep-review, six lenses on codex (`implementation/reviews/plan-review.md`); the Critical and
four Warnings were verified against code and folded in where marked "plan-review #N" (dispositions in `progress-log.md`).

No engine contact (`runtime/engine/`, `workflow_executor` untouched), no trace-format change (the trailer's `json_output`
key keeps today's producer and content; version stays 2.10.0). Not platform-sensitive. No `web/` change.

## 1. Verified ground (code is truth; every cite checked on `05884642`)

- **Builders today (13 + 2 fallbacks, 25 live cells)** — `scratchpads/session-14/verify/builders.out` (local) re-verified
  by reading: S-J `format_execution_success` (`execution/formatters/success_formatter.py:27-151`); S-T stderr summary
  `cli/workflow_output.py:806-878` (`_display_execution_summary`, fed by `_emit_summary_or_only_indicator:692-751`, which
  calls `format_execution_success` a SECOND time just to build the summary); F-J `cli/error_output.py:55-127` over
  `execution/formatters/error_formatter.py:13-80` (`checkpoint` key produced at `:46`, read by nobody in `src/`); F-T
  `cli/workflow_errors.py:40-103`; P-T/P-J `cli/commands/run.py:654-718`; D-T/D-J `run.py:517-559`; M-S
  `mcp_server/services/execution_service.py:53-101` + `format_success_as_text` (`success_formatter.py:315-440`); M-F
  `_build_error_text` (`execution_service.py:130-176`); M-P `_format_paused_text` (`:197-227`); X-T/X-J (pre-execution
  exceptions, no `ExecutionResult`) `error_output.py:129-178`.
- **Dispatch:** `run.py:570-626 _display_execution_result` (DENIED → exit 3; durable PAUSED → exit 4; non-durable PAUSED
  normalized to FAILED at `:598`; success → `_handle_workflow_success:100-152`; else `_emit_failure_tag:562-567` +
  `output_error`). `pflow resume` enters the SAME path (`cli/commands/resume.py:138-184 _dispatch_resume` →
  `execute_json_workflow`), so one fix covers resumed endings. MCP dispatch `execution_service.py:314-348` (success text /
  `is_durable_pause` text / `raise RuntimeError(text)` — the server boundary renders the raise; **stays a raise**).
- **The runner gap (#699):** `execution/runner.py:946-952 _exception_to_result` builds `ExecutionResult` without `metrics=`;
  the normal return (`:446-453`) passes it. `metrics_collector` lives in `run()`'s scope (`:184-199`, created AFTER
  `_prepare_workflow`, so a resolution/validation exception has none — those failures keep today's text; see §6 baseline).
  `MetricsCollector.start_time` is a field default (`core/metrics.py:159`) → always set. `get_summary` (`:387-467`) is
  consumed ONLY by the three document builders (grep), so the `metrics` block of the document IS its only reader.
- **Trace path is readable before the document is emitted (D4):** `runtime/workflow_trace.py:1161-1170` `trace_path` returns
  `_stream_path`, set at `_open_stream` (`:996`) and cleared ONLY by `_disable_streaming` (`:1129`, the stream-fault arm) —
  "valid before AND after `finalize()`". With `--no-trace` the collector still exists (`runner.py:212-234`,
  `stream_to_disk=False`) and mints a UUID, but `_open_stream` returns early (`:990`) so `trace_path` is `None`.
  **Identity rule therefore keys on `trace.trace_path is not None`** (streamed AND healthy), which makes `--no-trace` and
  a stream fault both drop `execution_id`/`trace_path` — D4's "absent when tracing is off" — and keeps
  `tests/test_cli/test_resume_cli.py:953-959` and every `--no-trace` denied test green unchanged.
- **The stream opens in the ENGINE, not at construction** (`runtime/engine/engine.py:919 start_streaming`, eager at depth 0),
  and `finalize()` opens it for a zero-event run (`workflow_trace.py:1150`). So a failure raised AFTER the collector exists but
  BEFORE the engine runs — a compile-time failure such as a missing required input (`_strip_placeholders` → `prepare_inputs`
  in `runtime/compilation/compile_validation.py:164`) — has `trace_path is None` while the CLI renders, and only the later
  `finally` finalize creates the file. MCP finalizes inside `runner.run` (`runner.py:274`) before rendering, so it would carry
  identity for the same failure. **Rule (plan-review Critical #1): the CLI finalizes BEFORE building the outcome for every
  non-success result** — nothing mutates a failure's trace, so the order is safe; the success path keeps `build →
  set_json_output → finalize → emit` (the stream is open by then: the engine ran). `_save_trace_file` is idempotent, so the
  `finally` stays the backstop for `--report` generation only.
- **Durability:** `ExecutionResult.is_durable_pause` (`execution/result.py:126-144`) = PAUSED ∧ trace ∧ ¬`_stream_failed`.
  `has_resumable_step()` (`workflow_trace.py:1557-1585`) is the ONE resumability suppressor, in-memory, valid pre-finalize;
  it is already False for a gate-stopped run, so the `category == "gate"` scan in `_maybe_echo_resume_hint` (`run.py:408`)
  is belt-and-braces that the builder does not need to repeat.
- **Paused results DO carry an ERROR diagnostic** — `_exception_to_result` runs `exception_to_diagnostics(GateNotInteractiveError)`
  (`runner.py:912`, `core/exceptions.py:1435`); that is why `_display_paused_result` filters to WARNING/INFO (`run.py:668`) and
  why the non-durable fallback can render "the gate's remediation ladder". The builder keeps the diagnostic on the result and
  drops it from the PAUSED document only.
- **Gate payloads are one shape:** paused `trace.pause_request = {"paused_node_id": id, "gate_request": request.to_dict()}`
  (`runtime/engine/engine.py:1652-1655`), masked by `core/gate.py:202 masked_gate_dict`; denied `context["gate"] =
  _masked_gate_payload(request)` (`core/exceptions.py:1404`, `:1528-1540` = `masked_gate_dict(request.to_dict())`). Same
  keys (`node_id, node_type, kind, preview, question, options, recommendation, iteration, max_iterations`); `paused_node_id ==
  gate["node_id"]` by construction. Denied is always `kind: action_approval` (`runtime/engine/gate.py:108, 161-166`).
- **Lineage source:** `shared["__execution__"]` carries `resumed_from`, `restored_nodes`, `resume_entry_node`,
  `resume_entry_iteration` (engine `_prepare_resume`; read today only by `success_formatter.py:133-138`). The denied/failed
  results reach the CLI with `shared_after` populated via the exception's `_pflow_shared_store` (`runner.py:424-426`,
  `:923-925`) — executed: the resumed-then-denied JSON BEFORE has `execution` absent only because D-J never builds it.
- **Step table = one source already:** `execution/execution_state.py:40 build_execution_steps` is called by S-J, F-J, F-T
  (`metrics_summary=None`), M-F. Restored nodes relabel `not_executed` (`:113-118`) — the engine rule "restored ≠ executed".
- **Consumers of what gets dropped/renamed** (searcher sweep, verified): top-level `nodes_executed` (= `len(node_timings)`,
  `core/metrics.py:316`) — no `src/`, MCP or `web/` reader; 4 success-run tests in
  `tests/test_integration/test_metrics_integration.py` (:179-180, :189, :697, :732, :742, :878-879) + `docs/reference/cli/index.mdx:259,283`
  + `tests/test_core/test_metrics.py:85`. `checkpoint` — only `tests/test_execution/formatters/test_error_formatter.py:305,365,387`
  (and `FORBIDDEN_FIELDS` at `tests/test_cli/test_unified_error_output.py:61` asserts it is ABSENT from the document — stays
  green). Paused `gate_request`/`paused_node_id` — `tests/test_cli/test_paused_cli.py:112,119-123,166,555-556`; MCP line
  `paused_node_id:` — `tests/test_mcp_server/test_execution_workflow.py:310`, `tests/test_integration/test_cli_mcp_parity.py:285`,
  docstring `mcp_server/tools/execution_tools.py:98`. The web UI reads the TRACE trailer (`ui/run_tailer.py:625-649`), never the
  document — untouched. The trailer's `json_output` is read only for `["result"]` (`ui/run_node.py:202-203`).
- **`_build_error_text` has a second caller:** the `registry_run` probe (`execution_service.py:791`) — the #748 surface, out of
  scope. It keeps a thin errors+warnings text builder (§3.4).
- **Tests pinning today's shapes** — full A/B/C/D inventory in the progress-log (planning entry); the ones the plan must rewrite
  are enumerated per phase below.
- **Redaction ratchet:** `tests/test_cli/test_json_diagnostic_redaction.py:256-278` AST-scans `_PRINTING_TREES = ("cli",
  "execution/formatters", "mcp_server")` for raw diagnostic serialization — the new module MUST live under
  `execution/formatters/` to stay covered. Every printed diagnostic is `Diagnostic.to_output_dict()` (formatters CLAUDE.md).
- **Docs that describe the documents** (searcher sweep): `docs/reference/cli/index.mdx:100, 236-341, 353-360`;
  `src/pflow/guide/features/resume.md:13, 18-21, 31`; `guide/core.md:300` (stays true — `result` on an output-resolution failure
  is kept); `mcp_server/tools/execution_tools.py:43-101` (the `workflow_execute` docstring — its Error example is ALREADY stale);
  `mcp_server/resources/instructions/mcp-agent-instructions.md:853` (claims MCP "does NOT persist a trace" — already false since
  Task 171); CLAUDE.md files `src/pflow/cli/CLAUDE.md:17-19, 68-71`, `src/pflow/execution/formatters/CLAUDE.md:12-13, 28-30,
  52-61`, `src/pflow/mcp_server/services/CLAUDE.md:30-31`; agent defs `.claude/agents/pflow-codebase-searcher.md:163`,
  `review-agent-ux.md:35,135`, `review-feature-interactions.md:80,177,180-181` ("success paths still parallel" — goes stale),
  `review-impact-completeness.md:205`, `review-architecture-fit.md:41` (all gated by `tests/test_docs/test_agent_references.py`;
  `.codex/` mirrors regenerate via `make sync-claude-assets`).
- **Task-159 baseline** (87 cases, CI job `baseline-oracle`, required): NO case records a run's JSON document, `❌ Workflow
  failed`, `Resume token`, `Denied at gate`, `Resumed from` or an MCP response. Candidates that may move: `15-run-flag-interactions/03`
  (success stderr incl. `Workflow trace saved` — ordering only, see Q4), `15/05` (`-p` mode line only), and the five
  "Executing workflow (1 nodes):" failing cases `01-parser-errors/05, 07`, `02-validator-errors/01, 02, 03` — they fail in
  `_prepare_workflow` (no collector → no `❌` line → unchanged) UNLESS a "Cache Failure" is raised at compile time (after the
  collector exists), in which case the case gains an unnormalized `❌ Workflow failed after Xs` line and needs the case-local
  duration `sed` that `15/03`'s `command.sh` already uses. `normalize.py` masks `duration_ms` JSON keys and only the last UUID
  group — never add a case that records `execution_id` or the `❌` line without a mask. Guide case `12/04` does NOT include
  `resume.md`/`core.md`/`approval.md`, so the guide edits here do not move it.
- **Cross-task scan** (`./scripts/tasks`): shipped substrate — Task 171 (identity on MCP success, durability home), 180 (lineage
  fields, resume dispatch), 120 (edited `run.py`/`execution_service.py` — lines re-cited above), 183 (gate iteration fields in
  the payload). Unbuilt overlap — Task 152 (MCP structured responses: D3 defers it; this task hands it ONE dict to serialize
  later), Task 117 (subcommand JSON errors — X-J stays separate, see §3.5), #748 (probe warnings — reuses §3.4's text helper).
  No collision risk in flight (`CURRENT-STATE` watch list has nothing on these files).

## 2. Design (LANGUAGE.md terms)

**One deep module, `execution/formatters/run_outcome.py`** — interface: `build_run_outcome(result, workflow_ir, *,
workflow_metadata, output_key=None) -> RunOutcome`, plus two renderers over it, `render_cli_stderr(outcome, *, text_mode,
print_flag, verbose) -> list[str]` and `render_mcp_text(outcome) -> str`. Behind it: every field rule the 13 builders held
between them (identity, lineage, metrics, warnings split, step table, result selection, gate payload, resume command, status
normalization, exit code). **Leverage:** three channels × five statuses exercise one builder; **locality:** a new field is
added once. The seam is the `RunOutcome` value: callers never reach past it to the collector or the trace (deletion test: delete
the module and the 15 cells reappear).

```python
@dataclass(frozen=True)
class RunOutcome:
    """The one Run outcome (CONTEXT.md). ``document`` is the agent contract (CLI JSON emits it unchanged);
    the Diagnostic lists are the same objects already serialized into document["errors"/"warnings"/"advisories"],
    kept so text renderers can call format_diagnostic (dict → text is not a thing)."""
    document: dict[str, Any]
    status: WorkflowStatus          # after normalization (non-durable PAUSED → FAILED)
    errors: list[Diagnostic]        # [] for PAUSED
    warnings: list[Diagnostic]      # surfaced, non-INFO
    advisories: list[Diagnostic]    # surfaced INFO
    exit_code: int                  # EXIT_CODES[status]: success/degraded 0, failed 1, denied 3, paused 4

EXIT_CODES = {SUCCESS: 0, DEGRADED: 0, FAILED: 1, DENIED: 3, PAUSED: 4}
```

Why a value object and not a bare dict: `format_diagnostic` (`core/diagnostic_render.py:33`) takes a `Diagnostic`; rebuilding
one from its printed dict would be a second serializer. The dict is the contract; the lists are the same data unserialized.

**Rejected shapes:** (a) keep `format_execution_success` and bolt status arms onto it — its loose-argument signature is the
cause of the drift (`run.py` passes `trace_path=None`, MCP patches `execution_id` after); (b) one renderer for CLI stderr AND
MCP text with a `channel` flag — the two differ in kind (MCP has no stdout/stderr split and needs greppable identity lines;
CLI has the token line / data on stdout), so they are two thin renderers over shared section functions, not one with branches;
(c) a dict→Diagnostic reconstruction so renderers read only the dict — a second serializer for no caller.

### Tiers (the `-p` and JSON-mode rules — ONE table, resolves Q1/Q4)

| Tier | Sections | text mode | text + `-p` | JSON mode (stderr) | JSON + `-p` |
|---|---|---|---|---|---|
| data (stdout) | success value (existing `_handle_text_output` data part) / the JSON document / paused token line `Paused at '<id>'. Resume token: <id> (exit 4)` | ✓ | ✓ | document | document |
| must-act (stderr) | errors block, batch-error details **when `status is FAILED`** (`format_batch_errors_section` — item indices, provider diagnoses, child-workflow failures; today printed regardless of `-p`), resolved-outputs note, gate content lines + `To answer: …` + bulk hint (**PAUSED only** — a denial is final; never render an answer or an "approve all remaining" hint after it), `To resume from the failed step: …`, `⤷` mode lines, the denied line | ✓ | ✓ | — (they are in the document) except the `⤷` mode lines, which print | `⤷` mode lines only |
| summary (stderr) | completion line (`✓/⚠️/❌`; not rendered for PAUSED on the CLI — the stdout token line is its announcement), batch-error details on a non-failed (degraded) run, shell-stderr block, cost lines, `⚠️ Warnings:` / `ℹ️ Advisories:`, `Workflow trace saved: <path>` | ✓ | — | ✓ | — |

Today's deviations this unifies (all shown in `show-before-code.md`, Q1/Q4): failure `-p` printed warnings; paused `-p`
printed warnings; JSON failure printed the resume hint on stderr (now only in the document); the trace line had two emission
sites (`_display_execution_summary` for text-success, `_finalize_trace_and_report` for everything else) → one, the summary tier.
`_finalize_trace_and_report` keeps finalizing and generating `--report`; it no longer echoes the path. If Q4 is ruled the other
way, keep `echo_trace_line=not text_success` as today and leave the trace line out of the renderer for non-text-success statuses.

## 3. Document shape — every decision resolved

3.1 **Common keys (every status):** `success`, `status`, `workflow` (caller metadata or `{"action": "unsaved"}`), `errors`
(list; `[]` when none — Q3), `warnings`, `advisories`, `diagnostics` (surfaced WARNING+INFO, split by `partition_surfaced_diagnostics`;
`diagnostics` = surfaced + errors, errors first), and — when the run has them — `execution_id` + `trace_path`
(`str(result.trace.trace_path)`; both present iff `result.trace is not None and result.trace.trace_path is not None`),
`duration_ms` + `total_cost_usd` + pricing tri-state keys (`_mirror_pricing_tri_state`) + `metrics` (iff `result.metrics is not
None`; `metrics` = `get_summary(llm_calls)["metrics"]` with `workflow.nodes_executed` REMOVED at the source — `core/metrics.py:316`
deleted, `tests/test_core/test_metrics.py:85` updated; `node_timings` carries the same information), `execution` (iff
`workflow_ir.get("nodes")` — built from `build_execution_steps(ir, shared_after, metrics_summary)` exactly as
`success_formatter.py:104-145` does today: `duration_ms`, `nodes_executed` = completed count, `nodes_total`, `steps`
(batch details compacted), `only_node` + `nodes_skipped` when `--only`, `resumed_from` + `nodes_restored` + `resume_entry_node` +
`resume_entry_iteration` when resumed, `cache_hits` when > 0; `execution.duration_ms` is omitted when there is no metrics
summary rather than written `null`). **`nodes_skipped` excludes the `--only` target itself** (today's `sum(not_executed)` at
`success_formatter.py:126` counts the target when a gate stopped it — a 3-node `--only three` denial would read "3 other nodes";
plan-review #5).
**The "absent, never null" rule is field-specific** (plan-review #2 — all six lenses): it binds the OUTCOME's own optional
keys — `execution_id`, `trace_path`, `result`, `error`, `gate`, `resume_command`, `duration_ms`, `metrics`, `execution`,
`execution.duration_ms`, the lineage and `--only` keys — which are omitted when the run has no value. It does NOT touch
values whose producers mean something by `null`: `total_cost_usd: null` is the pricing tri-state (subscription-billed or
unpriced calls; `core/metrics.py:237-246`, `_mirror_pricing_tri_state` keeps the discriminators beside it), `gate.question`
/ `recommendation` / `iteration` / `max_iterations` are the canonical `GateRequest` payload (ADR-0009: no per-surface gate
dialect), and a `result` value may be `null` by `?? null` (#757). No recursive null-stripping anywhere.
3.2 **By status:** `result` — success/degraded: `_collect_outputs(shared_after, ir, output_key)` (unchanged selection via
`select_output_mode`); failed: `collect_outputs_resolved_before_failure(result, ir)` when not `None` (#754), else absent; paused/denied:
absent. `error` — when `errors` non-empty: the single error's `message`, or `f"Workflow execution failed ({n} errors)"` (today's
rule, `error_output.py:80-84`). `gate` — paused: `masked_gate_dict(trace.pause_request["gate_request"])`; denied: the gate
diagnostic's `context["gate"]` (already masked); absent otherwise. `resume_command` — paused: `format_resume_answer_command(execution_id,
gate_request)`; failed with `trace_path` present and `trace.has_resumable_step()`: `f"pflow resume {execution_id}"`; absent otherwise.
3.3 **Status normalization lives in the builder:** `status = result.status`; if `PAUSED and not result.is_durable_pause` →
`FAILED` (the CLI's `run.py:598` rule and MCP's `elif is_durable_pause` branch become one line here; a normalized result keeps its
diagnostics so the gate's remediation ladder renders as the failure's errors). `errors = [] if status is PAUSED else result.errors`.
`success = result.success` (false for paused/denied, as today). Exit code from `EXIT_CODES`.
3.4 **Dropped:** top-level `nodes_executed`; `metrics.workflow.nodes_executed`; `checkpoint`; `paused_node_id`; `gate_request`
(→ `gate`). The probe keeps a thin `format_error_text(errors, warnings, trace_path)` in `run_outcome.py` (the errors block +
warnings sections + `trace_path:` line — the same section functions the MCP renderer composes), replacing `_build_error_text`
for its one remaining caller (`execution_service.py:791`); `tests/test_cli/test_agent_ux_fixes.py:411-450` and
`tests/test_mcp_server/test_registry_run_mcp.py:243-267` move to it.
3.5 **Out of the builder, deliberately:** `--dry-run` (`plan_formatter.py` — a plan has no run identity; stays as is;
`tests/test_cli/test_dry_run.py:132` exact key set unchanged); the pre-execution exception documents X-T/X-J
(`error_output.py:_format_from_exception` / `display_exception_text` — no `ExecutionResult` exists; they keep `{success:false,
status:"failed", error, errors, diagnostics, workflow}`; the dead `metrics_collector`/`shared_storage` branch is deleted since the
CLI's outer boundaries never have one — `run.py:355-368` and `:1420-1429`); `pflow resume list` JSON (a listing, not an ending).
3.6 **Trace `json_output`:** `set_json_output(outcome.document)` is called only when `outcome.status in (SUCCESS, DEGRADED)` and
`output_format == "json"` — today's producer rule (`workflow_output.py:914-915`). The trailer key's MEANING is unchanged ("the
JSON document the CLI printed"), but its CONTENT follows the document (gains `execution_id`, `trace_path`, `errors: []`; loses
the two attempted counts) — a snapshot of the printed document, not a versioned trace sub-contract, so no format bump
(plan-review open decision #8, resolved: snapshot semantics; recorded in the task-review for Task 175/152 readers). Its one
reader, `ui/run_node.py:202`, reads `json_output["result"]`, which the success document keeps. Storing the document for every
status is Task 152 / UI territory.
3.7 **Warnings filter:** the builder surfaces WARNING + INFO from `result.diagnostics` (today's CLI rule, `run.py:123-127`). MCP's
narrower advisory policy (`_mcp_surfaced_diagnostics`: INFO only from `parser`/`validator`, `execution_service.py:104-116`) is
RENDERER policy — `render_mcp_text` filters `outcome.advisories` by `diagnostic.source`; the document is identical on both
channels (the parity test's "same warning content"). `_mcp_surfaced_diagnostics` stays for `validate_workflow` and the probe.

## 4. Renderers

4.1 **Section functions** (module-private, each returns `list[str]`; moved from `success_formatter.py`/`workflow_output.py` with their
tests): `completion_line(outcome)` (one function for all five statuses — today's `_format_workflow_completion_status` arms, with
the DENIED arm replaced by the denied prose `✗ Denied at gate '<id>'. Workflow stopped cleanly before the step ran. Steps completed:
<execution.nodes_executed> of <execution.nodes_total>. (exit 3)` — `of N` from the document, not `ctx.obj["total_nodes"]`; the
PAUSED arm names the step: `⏸ Workflow paused at '<gate.node_id>' — a human decision is required.` (today's MCP header; the
generic "paused at gate" arm goes — plan-review #7); the `❌ Workflow failed[ (N warnings)] after Xs` arm reads
`document["duration_ms"]`, replacing `_emit_failure_tag`'s live `perf_counter`), `mode_lines(document)` (`format_resume_indicator`
unchanged; `format_only_indicator(only_node, nodes_skipped, *, ran)` gains the not-ran form for a gate-stopped or denied target —
`  ⤷ Only '<id>' was selected (--only); it did not run, N other node(s) not executed` — because "Ran only 'X'" is false when X
never ran (plan-review #5); both kept public, pinned by `tests/test_runtime/test_resume_engine.py:518-534` and
`test_success_formatter.py:1008-1046`), `batch_error_details(steps)` (`format_batch_errors_section`; must-act on FAILED) and
`shell_stderr_block(steps)` (`format_stderr_warnings`; summary) — two functions, not one, because their tiers differ
(plan-review #4), `format_cost_summary_lines(document)` (kept public; pinned by
`tests/test_cli/test_direct_execution_helpers.py:236-458`), `errors_block(errors, verbose)` (single: `format_diagnostic(e)`;
multi: `❌ Workflow execution failed (N errors[, M warnings])` header then numbered — today's `workflow_errors.py:78-90` rule, no
"first 3" cap — Q2), `diagnostic_sections(warnings, advisories)` (`⚠️ Warnings:` / `ℹ️ Advisories:` headings — CLI wording;
MCP today prints `Warnings:`/`Advisories:` without glyphs: **unify on the CLI wording** so one function serves both — 2 MCP tests
pin `"Advisories:"` as a substring, which survives), `gate_lines(document["gate"])` (content only — `format_gate_lines`) and
`answer_lines(document)` (`To answer: <resume_command>` + `format_bulk_approve_hint`; **rendered only when `status is PAUSED`
and `resume_command` is present** — a denied run renders neither the gate block nor an answer, plan-review #3),
`resolved_outputs_note(document)` (`Outputs that resolved before the failure:` + JSON, today's `_format_resolved_outputs_section`),
`identity_lines(document)` (`status:` / `execution_id:` / `trace_path:` / `resume_command:` — present keys only).
4.2 **`render_cli_stderr(outcome, *, text_mode, print_flag, verbose) -> list[str]`** composes per the tier table (§2); order:
completion line · mode lines · errors block · batch/stderr blocks · resolved-outputs note · cost · warnings · advisories · gate
lines · resume hint (`To resume from the failed step: <resume_command>` when `status is FAILED` and the document has
`resume_command`) · trace line. Blocks are joined with one blank line between present blocks (today's `_echo_summary_blocks`
rule). The caller (`run.py`) echoes the lines to stderr; the formatter never prints (formatters CLAUDE.md).
4.3 **`render_mcp_text(outcome) -> str`**: `{name} was executed` / `was created and executed` first line (MCP-only, kept — the
docstring at `success_formatter.py:342-346` says why), completion line, mode lines, batch/stderr blocks, cost, errors block,
resolved-outputs note, warnings/advisories (advisories filtered per §3.7), `Workflow output:` + `_append_outputs` (success),
`Gate:` block (paused/denied), blank, identity block (Q2). Exactly today's success text plus the identity block's `status:` line;
failure/paused re-laid as `show-before-code.md §6`.
4.4 **CLI wiring (`run.py::_display_execution_result`)** becomes, in this order (the order IS the fix for plan-review #1):
```python
if not result.success and ctx.obj.get("trace", True):
    _save_trace_file(ctx, result.trace)          # settle identity first: a failure's trace is never mutated after the run
outcome = build_run_outcome(result, ir_data, workflow_metadata=ctx.obj.get("workflow_metadata"), output_key=output_key)
if output_format == "json" and outcome.status in (SUCCESS, DEGRADED) and result.trace is not None:
    result.trace.set_json_output(outcome.document)
if ctx.obj.get("trace", True):
    _save_trace_file(ctx, result.trace)          # idempotent; the success path finalizes here, after set_json_output
echo render_cli_stderr(outcome, text_mode=output_format == "text", print_flag=print_flag, verbose=verbose) → stderr
stdout: json → _serialize_json_result(outcome.document); text success → _handle_text_output's data part (its summary call
        removed); text paused → the token line
ctx.exit(outcome.exit_code) when non-zero
```
`_handle_workflow_success`, `_emit_failure_tag`, `_resumable_execution_id`, `_display_paused_result`, `_display_denied_result`,
`_maybe_echo_resume_hint` are deleted; `_finalize_trace_and_report` loses `echo_trace_line` (Q4) and keeps only the `--report`
generation (the `finally` still calls it — idempotent backstop). `execute_json_workflow`'s `except Exception` arm loses
`_emit_failure_tag` and passes only `exception=` to `output_error`.
4.5 **MCP wiring (`execution_service.py::execute_workflow`)**: `outcome = build_run_outcome(result, resolved.ir,
workflow_metadata=_workflow_metadata(resolved, str(workflow)))`; `text = render_mcp_text(outcome)`; `return text` when
`outcome.status in (SUCCESS, DEGRADED, PAUSED)` else `raise RuntimeError(text)` (the server boundary renders a raise, as today —
`tests/test_mcp_server/test_execution_workflow.py:145-176` keep passing). `_format_success_result`, `_build_error_text`,
`_format_resolved_outputs_section`, `_format_paused_text`, `_trace_path_str` are deleted; the metadata derivation
(`execution_service.py:74-85`) becomes `_workflow_metadata(resolved, name)`.

## 5. Deletions (named, with the test that pins the old shape)

| Deleted | Pinning tests → disposition |
|---|---|
| `execution/formatters/success_formatter.py` (renamed to `run_outcome.py`; `format_execution_success`, `format_success_as_text`, `_append_execution_steps`, `_compact_batch_error_details` go; `_collect_outputs`, `collect_declared_outputs`, `collect_outputs_resolved_before_failure`, `partition_surfaced_diagnostics`, `_mirror_pricing_tri_state`, `format_cost_summary_lines`, `format_only_indicator`, `format_resume_indicator`, `format_stderr_warnings`, `_append_outputs` move) | `tests/test_execution/formatters/test_success_formatter.py` → `test_run_outcome.py`: `TestFormatSuccessAsText` (:231-556), `TestPricingUnavailableWarning` (:558), `TestSubscriptionBilledCost` (:707), `TestOnlyNodeDisplay` (:738), `TestCacheStatsDisplay` (:848), `TestAppendExecutionStepsOnlyNode` (:919), `TestAppendOutputsCliMcpParity` (:1049), `TestStderrWarningsCliMcpParity` (:1245), `TestDeniedStatusRendering` (:1525) rewrite their synthetic `success_dict` fixtures as `RunOutcome` built from a real `ExecutionResult` (an in-process `WorkflowRunner().run` on a tiny IR, or `ExecutionResult(...)` constructed directly) and render through `render_mcp_text`/`render_cli_stderr`; `TestFormatOnlyIndicator`, `TestCollectOutputsDottedPath`, `TestFindAutoOutputNamespaceAware`, `TestBatchErrorsSectionFormatting`, `TestErrorMessageTruncation` move unchanged. `tests/test_runtime/test_resume_engine.py:488-515, 823-849` call `build_run_outcome(result, ir, workflow_metadata=None)` and assert the same `execution.*` fields + the `⤷` line via `render_cli_stderr`. |
| `execution/formatters/error_formatter.py` (`format_execution_errors`, `checkpoint`) | `tests/test_execution/formatters/test_error_formatter.py` → folded into `test_run_outcome.py`: the redaction guards (:35-125), no-mutation (:131-143), steps/cache/compaction (:145-283) re-target `build_run_outcome` on a FAILED result; the three `checkpoint` tests (:289-305, :350-366, :371-387) are deleted with the key; `test_formatter_runs_in_under_10ms` (:411) deleted (a timing test with no failure scenario). |
| `cli/workflow_errors.py` (`_display_single_error`, `_display_text_error_details`) | `tests/test_cli/test_agent_ux_fixes.py:53-125` (single-error text, `"Shell details:"`, no `"Error 1:"`) → assert on `render_cli_stderr` lines; `tests/test_cli/test_direct_execution_helpers.py:572-594` → same. |
| `cli/error_output.py::_format_from_result`, the `result=`/`metrics_collector=`/`shared_storage=`/`ir_data=`/`resume_execution_id=` parameters of `format_error_json`/`output_error` | `tests/test_cli/test_unified_error_output.py:24-27` helper keeps `format_error_json(exception=…)`; its `_assert_unified_shape` (:78-103) keeps passing for the exception documents AND for the run documents (same required keys; `checkpoint` still forbidden). |
| `cli/commands/run.py::_display_denied_result`, `_display_paused_result`, `_emit_failure_tag`, `_resumable_execution_id`, `_maybe_echo_resume_hint`, `_handle_workflow_success` | none pin them by name (searcher: zero hits); behaviour pins listed in §7 per phase. |
| `cli/workflow_output.py::_format_workflow_completion_status`, `_emit_summary_or_only_indicator`, `_only_indicator_line`, `_resume_indicator_line`, `_emit_mode_indicators`, `_display_execution_summary`, `_handle_json_output`, `_handle_workflow_output`, `_as_block`, `_echo_summary_blocks` | `tests/test_cli/test_approval_gate_cli.py:154-159` (imports `_format_workflow_completion_status`) → `completion_line` on a DENIED outcome; `tests/test_cli/test_direct_execution_helpers.py:460-569` (`_display_execution_summary`) → `render_cli_stderr`; `tests/test_cli/test_workflow_output_handling.py` JSON tests that drive `_handle_workflow_output` (:687, :1087-1530) re-target `_display_execution_result`/the builder (their `mock_compile` returns a bare `ExecutionResult(success=True, …)` with no trace/metrics — the builder MUST tolerate `trace=None`, `metrics=None`, `shared_after={}`; see P1 failure scenarios). |
| `mcp_server/services/execution_service.py::_format_success_result`, `_build_error_text`, `_format_resolved_outputs_section`, `_format_paused_text`, `_trace_path_str` | `tests/test_cli/test_agent_ux_fixes.py:411-450`, `tests/test_mcp_server/test_registry_run_mcp.py:243-267` → `format_error_text` (§3.4). |
| `core/metrics.py:316` `"nodes_executed": len(node_timings)` | `tests/test_core/test_metrics.py:85` → assert `node_timings` instead. |

## 6. Spec conformance map

| Spec requirement | Where it lands |
|---|---|
| One function builds the document for every status; no other path assembles a run-ending dict | §2 builder; §5 deletions; the AST-free guard is `grep -rn '"success": ' src/pflow/cli src/pflow/mcp_server src/pflow/execution` showing one producer besides `_format_from_exception` and `plan_formatter` — recorded in the completion gate (`review-spec-conformance`). |
| Common keys present for every status when the run has them | §3.1; guard test P1-T1. |
| `result` / `errors`+`error` / `gate`+`resume_command` / `gate` by status | §3.2 (`errors` always a list — Q3). |
| Absent, never `null` | §3.1 (`execution.duration_ms` omitted without metrics; identity keyed on `trace_path`); P1-T2. |
| `ExecutionResult` constructed the same way on both runner paths | P0. |
| CLI JSON emits the document unchanged, with or without `-p` | §4.4; P2-T3. |
| CLI text: `❌`, `⤷ Resumed`, cost, warnings, trace line for every status that has the field | §4.1–4.2; P2-T1/T2/T4. |
| Denied shows this attempt's count AND lineage | `completion_line` DENIED arm + `mode_lines`; P2-T2. |
| MCP text rendered from the document; identity on every status; warnings on paused; metrics on failure | §4.3/4.5; P3-T1/T2. |
| `-p` suppresses the summary tier, never changes the JSON | §2 tier table; P2-T3. |
| Guards: common-key test on five real runs; CLI↔MCP parity; bespoke-shape tests updated not duplicated | P1-T1, P3-T2, §5. |

## 7. Phases

Model tier: **Opus** for every phase (decisions are resolved here; the renderer layout is specified). Effort: P0 `medium`,
P1 `high` (the seam), P2 `high` (CLI tiers + many test rewrites), P3 `medium`, P4 `medium`.
**Agent assignment:** ONE implementer I1 for P0+P1 (bundled: P1 is where P0's `metrics` lands), **stop** for the mid-task
review (its outcome can change the renderers' inputs); resume I1 for P2+P3 (bundled — P3 is a 40-line consumer of P2's
sections); P4 to I1 if its window is healthy (it holds the content), else a fresh Opus with this plan's §1 docs list + the
progress-log tail. Per-phase gate: `make check` + `make test` (plus the targeted commands named below). Completion:
`make test-all-local`, baseline `verify.sh`, the real-surface runs (§8), then the completion gate (§9).

### P0 — the result carries metrics on the exception path (`execution/runner.py`)
- Goal: `_exception_to_result(…, metrics_collector=metrics_collector)` → `ExecutionResult(metrics=metrics_collector)`; signature
  gains the kwarg; the one call site (`:296-298`) passes it (it is `None` when the exception predates the collector — keep that).
- Files: `src/pflow/execution/runner.py`; tests in `tests/test_execution/test_runner*.py` (nearest existing file).
- Decisions: none open. Not an engine file; no review trigger alone.
- Tests must catch: (a) a node exception (an IR whose shell step runs `exit 1` with an `on-error` route absent is an action
  failure — use a `code` step that raises, or an `http` timeout to `10.255.255.1:9`, `timeout: 1`) → `result.metrics is not None`
  and `result.metrics.workflow_nodes` names the completed step; (b) a VALIDATOR error — one `_prepare_workflow` raises, e.g. a
  `next:` to an undefined step or the `## Cache` order mismatch of baseline case `02-validator-errors/01` (NOT a missing required
  input: that is deferred to compile time by the placeholders, `runner.py:729-750`) → `result.metrics is None`, `result.trace is
  None` (pins the "pre-collector exceptions stay metrics-less" boundary that keeps the baseline's failing cases stable); (c) the
  normal return still carries the same collector object (`is`); (d) a COMPILE-TIME failure (missing required input) →
  `result.metrics is not None`, `result.trace is not None`, `result.trace.trace_path is None` until `finalize()` returns a path
  (the exact state the CLI's finalize-first order exists for, §4.4).
- Handoff: `make test tests/test_execution` green; the two construction sites differ only in `success`/`status`/`diagnostics`.

### P1 — the builder (`execution/formatters/run_outcome.py`) + unit guards  **(triggers mid-task review)**
- Goal: `git mv success_formatter.py run_outcome.py`; write `RunOutcome`, `EXIT_CODES`, `build_run_outcome` per §3; move the
  section functions (§4.1) in; delete `error_formatter.py`; delete `core/metrics.py:316`; add `format_error_text` (§3.4) and
  repoint the probe (`execution_service.py:791`) — nothing else in MCP/CLI changes yet (they still import the old names → this
  phase ends RED on imports unless the old names are kept as thin shims for one phase; **do not shim**: bundle P1 with the
  test-file moves and leave `cli/`+`mcp_server/` imports broken until P2/P3, running only `tests/test_execution`,
  `tests/test_core/test_metrics.py`, `tests/test_runtime/test_resume_engine.py` as this phase's gate).
- Files: `src/pflow/execution/formatters/run_outcome.py` (new, from `success_formatter.py`), `error_formatter.py` (deleted),
  `core/metrics.py`, `mcp_server/services/execution_service.py:791` only, `tests/test_execution/formatters/test_run_outcome.py`
  (from `test_success_formatter.py` + the kept parts of `test_error_formatter.py`), `tests/test_runtime/test_resume_engine.py`,
  `tests/test_core/test_metrics.py`, `tests/test_mcp_server/test_registry_run_mcp.py`, `tests/test_cli/test_agent_ux_fixes.py:411-450`.
- Decisions resolved: everything in §3; CP-1 rulings applied here (Q3 `errors` list; Q2 cap).
- Tests must catch (`test_run_outcome.py`, built from REAL results — `WorkflowRunner().run(ir, {}, RunnerConfig(...))` in-process,
  `trace_files` marker where a token is needed; never a hand-typed `success_dict`):
  - **P1-T1 common keys, one table:** `COMMON_KEYS = {success, status, workflow, errors, warnings, advisories, diagnostics}`;
    `IDENTITY_KEYS = {execution_id, trace_path}`; `METRICS_KEYS = {duration_ms, total_cost_usd, metrics, execution}` — asserted
    PRESENT on success, failure-by-exception, failure-by-action, paused, denied (resume `--approve no` in-process via
    `load_resume_source` or the CLI runner) and ABSENT where the rule says (identity absent under `RunnerConfig(trace_enabled=False)`
    — paired with the presence half; `result` absent on paused/denied, present on success; `gate` absent on success/failed,
    present on paused/denied; `resume_command` absent on success/denied/non-resumable failure, present on paused/resumable failure).
  - **P1-T2 absent, never null — field-specific (§3.1):** for every status, none of `execution_id`, `trace_path`, `result`,
    `error`, `gate`, `resume_command`, `duration_ms`, `metrics`, `execution`, `execution.duration_ms`, `execution.resumed_from`
    is present with value `None`; a run with `trace_enabled=False` has neither identity key. Paired with the nulls that MUST
    survive: a subscription-billed/unpriced metrics summary (the moved `TestSubscriptionBilledCost` fixture) keeps
    `total_cost_usd: null` beside `subscription`/`partial_cost_usd`; a declared output resolving via `?? null` keeps
    `result[name] is None`; `gate.question is None` on an approval gate.
  - **P1-T9 `--only` count and wording:** a seeded 3-step workflow, `--only three` where `three` is gate-denied (or gate-stopped
    non-interactively) → `execution.nodes_skipped == 2` (not 3), `execution.only_node == "three"`, and the mode line is the
    not-ran form; a completed `--only` target keeps today's `Ran only 'three' (--only), 2 other nodes not executed`.
  - **P1-T3 one meaning:** on the action failure, `execution.nodes_executed == 1` and the string `"nodes_executed"` occurs exactly
    once in the serialized document (no `metrics.workflow.nodes_executed`, no top-level copy).
  - **P1-T4 paused carries no error:** paused document `errors == []`, `error` absent, `diagnostics` == surfaced only (the
    `resume.loop-restart` set-equality at `test_paused_cli.py:1124-1126` is the integration twin); the NON-durable pause
    (`trace._stream_failed = True` on the collector) normalizes to `status: "failed"`, exit 1, `errors` non-empty, no
    `resume_command`, no identity.
  - **P1-T5 lineage everywhere:** resumed-then-failed and resumed-then-denied documents carry `execution.resumed_from ==
    source id`, `nodes_restored == 2`, `nodes_executed == 0`; a fresh denial has `nodes_executed == 2`, no `resumed_from`.
  - **P1-T6 tolerance:** `build_run_outcome(ExecutionResult(success=True), {}, workflow_metadata=None)` (no trace, no metrics,
    empty store) returns `{success, status, workflow:{action:unsaved}, result:{}, errors:[], warnings:[], advisories:[],
    diagnostics:[]}` — the shape `test_workflow_output_handling.py`'s `mock_compile` depends on.
  - **P1-T7 redaction:** errors/warnings in the document are `to_output_dict()` form — the moved `TestSecurityGuardrails` cases;
    the AST ratchet (`test_json_diagnostic_redaction.py:256`) must pass over the new module.
  - **P1-T8 `format_error_text`:** errors + warnings + `trace_path:` line; empty errors → `❌ Workflow execution failed`.
- **Mid-task review (one job, after P1 handoff):** `review-impact-completeness` (every consumer of the old builders — the
  §5 table — and every field rule folded in; the lens that catches a rule left behind in a deleted function) +
  `review-silent-failures` (absent-vs-null, `None` tolerance, the normalization arm, `has_resumable_step` on `--no-trace`).
  Scope: the P1 diff. Dispositions logged.
- Handoff: `uv run pytest tests/test_execution tests/test_core/test_metrics.py tests/test_runtime/test_resume_engine.py` green;
  the five documents reproduced from the fixtures match `show-before-code.md` key sets (paste the key sets into the log).

### P2 — CLI renders the outcome (`cli/commands/run.py`, `cli/workflow_output.py`, `cli/error_output.py`)
- Goal: §4.2 + §4.4; delete `cli/workflow_errors.py` and the §5 `cli/` functions; tier table (§2) is the spec.
- Files: the three above + `cli/commands/resume.py` (no code change expected — verify `_dispatch_resume` still only sets
  `ctx.obj`); tests: `tests/test_cli/test_paused_cli.py` (:112, :119-123, :166, :555-556 → `document["gate"]`; :1124-1126
  stays), `test_approval_gate_cli.py` (:154-159 → `completion_line`; add the lineage assertion to the resumed-denial case at
  `test_paused_cli.py:225-239`), `test_resume_cli.py` (:1004 → `assert "execution_id" in document` AND `"resume_command" not in
  document` — reversing #754's "keep that" comment by D1, logged), `test_metrics_integration.py` (:179-180, :189, :697, :732,
  :742, :878-879 → `execution.nodes_executed`), `test_unified_error_output.py` (helper unchanged), `test_enhanced_error_output.py`,
  `test_direct_execution_helpers.py`, `test_workflow_output_handling.py`, `test_agent_ux_fixes.py:53-125, 238-300`,
  `test_progress_streaming_subprocess.py` (:957, :1021, :1078, :1230 — real subprocess; keep green), `test_json_diagnostic_redaction.py`
  (keep green), `test_text_diagnostic_redaction.py` (keep green).
- Decisions resolved: Q1/Q4 as ruled; exit codes from `EXIT_CODES`; `set_json_output` on success only (§3.6); the paused token line
  text and the `To answer:` line unchanged; denied prose unchanged + lineage line.
- Tests must catch (new file `tests/test_cli/test_run_outcome_cli.py`, CliRunner + `home` fixture + `trace_files`, real workflows
  — the `_GATE_WF` pattern of `test_paused_cli.py`):
  - **P2-T1 the ❌ line on an exception failure** (HTTP timeout workflow): stderr has `❌ Workflow failed after` AND JSON has
    `metrics`/`duration_ms`/`total_cost_usd`; the action failure keeps both (presence pair). Regression test for #699.
  - **P2-T2 lineage on failed and denied:** resumed-then-failed stderr has `⤷ Resumed from <id> at 'three' — 2 upstream steps
    restored` and its JSON `execution.resumed_from`; resumed-then-denied stderr has the denied line with `Steps completed: 0 of 3.`
    AND the `⤷` line; a fresh denial has `Steps completed: 2 of 3.` and no `⤷`. Regression test for #737.
  - **P2-T3 `-p` never changes the JSON:** `--output-format json` with and without `-p` → identical key sets (and equal documents
    modulo `duration_ms`/`execution_id`/`trace_path`/`node_timings`); with `-p` stderr is empty on success and carries only the
    `⤷` lines on a resumed run; without `-p` it carries `Workflow trace saved:` exactly once (one emission site — Q4).
  - **P2-T4 identity on success JSON:** `execution_id` equals the trace meta line's id and `trace_path` is the file that exists on
    disk after exit; under `--no-trace` neither key exists. Regression test for #695.
  - **P2-T5 tiers under `-p` on failure/paused:** the error block / gate lines / `To answer:` / `To resume…` print; warnings and
    the trace line do not (presence without `-p`, absence with — same medium). Plus the all-failed batch (`error_handling:
    continue`, every item failing — the `batch_executor.py:1198` "first three" summary case): `Batch '<id>' errors:` with item
    indices prints WITH and WITHOUT `-p` on the failed run; on a degraded run it prints without `-p` only.
  - **P2-T6 exit codes:** 0/1/3/4 from one table, including the non-durable pause → 1 (`test_paused_cli.py:1025-1044` is the
    existing twin — keep it).
  - **P2-T7 the spec's guard on the REAL CLI JSON:** the `COMMON_KEYS`/`IDENTITY_KEYS`/`METRICS_KEYS` tables from
    `test_run_outcome.py` imported and asserted on `json.loads(stdout)` of CliRunner runs to all five endings (presence AND the
    by-status absences) — P1-T1 proves the builder, this proves the adapter (plan-review #6).
  - **P2-T8 compile-time failure carries identity (plan-review Critical #1):** a workflow with a required input, run without it,
    `--output-format json` → `execution_id` + `trace_path` present and the file exists at exit with a `run.complete` trailer;
    text mode prints `Workflow trace saved:` once; the same failure through `ExecutionService.execute_workflow` (P3) names the
    same two lines — CLI and MCP agree on a pre-engine failure.
  - **P2-T9 a denial renders no answer:** resume a LOOPING approval gate (`loop:` step with `approval: required`, paused at
    iteration 2) with `--approve no`, text and `-p` → the denied line + lineage print; `To answer:`, `To approve this and every
    remaining iteration` and the gate preview do NOT (presence half: the paused run before it printed all three).
- Mid-task review: none (the completion gate's `agent-ux` lens reads this text; `review-plan` already saw the tier table).
- Handoff: `make check` + `make test` green; the eleven BEFORE commands in `show-before-code.md` re-run and pasted to the log
  as AFTER; `./.taskmaster/tasks/task_159/baseline/verify.sh 01-parser-errors 02-validator-errors 06-dry-run-nudge
  15-run-flag-interactions` — PASS, or the moved case named with its cause and re-recorded (a case that gains the `❌` line
  gets the `15/03`-style duration `sed` in its `command.sh` BEFORE re-recording; never record a raw duration).

### P3 — MCP renders the outcome (`mcp_server/services/execution_service.py`)
- Goal: §4.3 + §4.5; delete the §5 `mcp_server` functions.
- Files: `execution_service.py`; `mcp_server/tools/execution_tools.py` docstring (the Returns block — rewrite to the one layout;
  the Error example is already stale); tests `tests/test_mcp_server/test_execution_workflow.py` (:303-316 `paused_node_id:` line
  → `gate` content via `Gate:`; :354-367, :401-423 keep; :203-238 keep), `tests/test_integration/test_cli_mcp_parity.py:285`,
  `tests/test_cli/test_text_diagnostic_redaction.py` (keep green).
- Decisions resolved: Q2 as ruled; MCP failure stays a raised `RuntimeError`; advisory source filter in the renderer (§3.7);
  `Warnings:` heading unified to the CLI's `⚠️ Warnings:` (substring `Warnings:` survives).
- Tests must catch (add to `test_cli_mcp_parity.py`):
  - **P3-T1 metrics + identity on MCP failure:** the raised text contains `❌ Workflow failed after`, `execution_id: <uuid>`,
    `trace_path: <existing file>`, and (for the resumable action failure) `resume_command: pflow resume <uuid>`; the HTTP-timeout
    failure text has the same three lines (exception path — the #699 twin on MCP).
  - **P3-T2 CLI↔MCP parity (the spec's guard):** one workflow with a validator WARNING (e.g. an unused declared input or an
    `env:` warning — pick one `pflow --validate-only` reports today) run through `ExecutionService.execute_workflow` and through
    the CLI `--output-format json`: every CLI `warnings[].message` appears verbatim in the MCP text; both carry an `execution_id`
    (CLI key, MCP line) and a `trace_path` that exists; a paused run's MCP text contains the warning (presence) where today it
    does not (the BEFORE in `show-before-code.md §6`).
  - **P3-T3 every error, not three:** a validation failure with 4 errors → all four numbered in the MCP text.
  - **P3-T4 advisory policy survives the move:** a runtime INFO advisory (empty batch) is in the CLI JSON `advisories` and NOT in
    the MCP text; a parser/validator INFO is in both.
  - **P3-T5 the paused text names the step:** a fresh non-looping approval pause → the MCP text contains `paused at 'three'`
    (the node id, not only the `Gate:` heading — plan-review #7) and the `Gate:` block.
  - **P3-T6 lineage renders on MCP's renderer:** MCP has no resume entry, so build a real resumed-then-failed `ExecutionResult`
    in-process (the P1-T5 fixture) and assert `render_mcp_text` contains `⤷ Resumed from <id> at 'three' — 2 upstream steps
    restored` and `execution.resumed_from` in the document (plan-review #6: lineage parity at the renderer seam).
- Mid-task review: none.
- Handoff: `make check` + `make test` green; `uv run python` driving `ExecutionService.execute_workflow` on the five fixtures,
  outputs pasted to the log.

### P4 — docs, instruction files, close-out
- Goal: every surface in §1 "Docs that describe the documents": `docs/reference/cli/index.mdx` (:100 paused keys → `gate`,
  `trace_path`, `execution`…; the JSON-mode expandable :236-341 rewritten from REAL AFTER output — the current examples are
  already wrong on `metrics`; key-fields table gains `status`, `execution_id`, `trace_path`, `execution.nodes_executed`,
  `execution.resumed_from`/`nodes_restored`, `gate`, `resume_command`, `error`; exit-code table :353-360 gains 3 and 4; a
  `docs/changelog.mdx` `<Update>` entry per `docs/CLAUDE.md:71-73`); `guide/features/resume.md` (:18-21 `execution_id` always,
  `resume_command` when resumable, `execution.resumed_from`; :31 paused keys); `mcp_server/resources/instructions/mcp-agent-instructions.md:853`
  (MCP streams a trace; the response names it); `src/pflow/cli/CLAUDE.md` (:17-19 owner rows → `run_outcome.py`; :68-71 the
  dispatch paragraph → "one outcome, exit code from `EXIT_CODES`"); `src/pflow/execution/formatters/CLAUDE.md` (:12-13 rows,
  :28-30 "update both consumers" → "both consume `build_run_outcome`; a field is added once", :52-61 parity seams → the section
  functions + `test_run_outcome.py`); `src/pflow/mcp_server/services/CLAUDE.md:30-31`; `.claude/agents/pflow-codebase-searcher.md:163`
  + `review-feature-interactions.md:177-181` ("success paths still parallel" → one builder) + the other agent-file hits (verify
  each still true, edit only the stale); `make sync-claude-assets`. `context/CONTEXT.md` Run outcome entry already matches — no edit.
- Also: spec `## Status` → `done`, `## Completed` date; progress-log close-out; PR body names the baseline cases re-recorded (or
  "none moved") and `Closes #695, #699, #737` + `Refs #754, #748 — not closing`.
- Tests must catch: `make check` (docs tests, agent-reference test, asset sync); `uv run pytest tests/test_docs`.
- Handoff: `make test-all-local` green; §8 evidence pasted; then the completion gate (§9).

## 8. Real-surface verification (Definition of done — pasted into the task-review)

The eleven commands of `show-before-code.md` on the five fixtures (copy them into `tests/fixtures/run_outcome/` so the
integration tests and the manual pass share them): `ok` text/JSON/`-p`/`-p --output-format json`; `fail-action` text/JSON;
`fail-exc` text/JSON/`-p`; `gate` → paused text/JSON/`-p` → `resume <tok> --approve no` text/JSON/`-p`; `gate-fail` → paused →
`resume <tok> --approve yes` text/JSON; `gate` → `resume --approve yes` (resumed success — `⤷` line unchanged); MCP
`ExecutionService.execute_workflow` on `ok`, `fail-action`, `fail-exc`, `gate`. Expected: `show-before-code.md` AFTER, byte-for-byte
on the key sets.

## 9. Completion gate (commissioned by the task orchestrator)

Code-mode `deep-review` on the full branch diff, fan-out on codex: `review-simplicity` + `review-spec-conformance` (deletion/
consolidation + task gate — completion-only lenses), `review-impact-completeness`, `review-silent-failures`, `review-test-fidelity`
(the many rewritten pins — the lens that catches a B-class test rewritten to assert the new behaviour without a presence/absence
pair), `review-agent-ux` targeted at `run_outcome.py` + the guide/docs diff, `review-feature-interactions` (resume × gates × `--only`
× batch × MCP × output routing — the step table under `--only` and a batch failure on the failure path), then `review-falsifier` by
direct launch LAST with the spec and `show-before-code.md` (it executes the eleven commands). The MCP server path is a sensitive
path → the full floor applies regardless of diff size. CI: the PR's `tests-windows` job must be green (no platform-sensitive
code is expected, but the gate is blocking and the spec names it) and `baseline-oracle` must pass on the merged result.

## 10. Risks the implementer should know

- `test_workflow_output_handling.py` drives the JSON path with a mocked compile returning a bare `ExecutionResult` — P1-T6 is the
  contract that keeps those 20+ tests green; do not "fix" them by adding a trace.
- `_handle_text_output`'s data part contains the `-o` miss diagnostics and declared-output ambiguity warnings (`workflow_output.py:165-226`)
  — they stay where they are (stdout-data concerns), only the summary call at `:165-176` is removed.
- `completion_line` for FAILED needs `duration_ms`; a failure with no collector (pre-execution) has none → no `❌` line — the
  baseline's five failing cases depend on this (§1).
- `format_resume_answer_command` and `format_bulk_approve_hint` (`execution/gate_prompt.py`) stay the ONE render shape for the
  answer command (Task 171 invariant); the builder calls them, never formats a resume command itself.
- The MCP `execute_workflow` outer `except Exception` (`execution_service.py:346-348`) wraps renderer bugs as
  `❌ Workflow execution failed: <e>` — keep it; a renderer must never raise on a well-formed outcome (P1-T6).
- Searcher-side gap, unverified: whether a cached node records a metrics timing. Irrelevant after `metrics.workflow.nodes_executed`
  is removed (`node_timings` is the raw data either way).
