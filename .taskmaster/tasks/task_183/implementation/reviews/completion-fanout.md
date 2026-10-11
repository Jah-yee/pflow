# Merged Review Report

## Convergent findings

None reported. No lens raised a defect or cross-lens handoff. Overlapping verified-clean assertions are retained below and do not constitute convergent findings.

## Critical

None reported by any lens.

## Warnings

None reported by any lens.

## Suggestions

None reported by any lens. The simplicity lens also reported no items worth simplifying or minor changes worth making.

## Verified clean

### review-silent-failures — codex

- Cap lookup remains display-only. Unknown, body-dependent, and invalid caps become `null`; runtime enforcement retains its error path. Dependency checks cover coalesce operands and dynamic indexes.
- Both gate builders propagate the cap into pause events and trailers. Older records retain iteration-only rendering.
- `/api/resume` rejects unknown fields, non-boolean `auto_approve`, and contradictory answers before spawning.
- Bulk approval targets the validated paused step and survives browser submission and `force` retries. Ordinary Approve remains single-use.
- Escalations retain kind validation and cannot receive bulk approval.
- The off-checklist pass found no new argument-parsing or serialization loss.
- No new silent-failure defect was identified in the examined engine, gate, trace, resume, and server paths. Settled rulings were respected.

### review-test-fidelity — codex, Python review

- **Cap production:** `test_gate_trace.py` checks actual streamed payloads at iteration one, both escalation marker shapes, and body-dependent caps after outputs exist.
- **Resume fidelity:** `test_gate_pause.py:285` checks that an upstream-templated cap survives restored outputs across attempts, with exact, distinguishable side effects.
- **Pause surfaces:** `test_paused_cli.py:492` checks JSON fields, the complete list cell, and answer-required output. Compatibility coverage removes the field from a real trailer.
- **HTTP bridge:** `test_ui_interaction_server.py:1467` exercises real pause/preflight paths and exact subprocess arguments. Rejection cases distinguish errors and require no spawn.
- **Behavioral completion:** CLI and MCP tests distinguish single approvals advancing one iteration from bulk approval completing the loop with exactly the expected effects.
- **Renderer contract:** The shared case-table test pins the complete case population, preventing vacuous success.
- Assertions cover observable behavior, production-shaped data, compatibility, and failure cases. Existing tests were strengthened without substantial duplication; no actionable test bloat was identified.

### review-test-fidelity — codex, web review

- **GateCallout:** Exact eyebrow assertions distinguish capped, uncapped, old-record, non-loop, and escalation payloads. Bulk-action absence checks also require the appropriate ordinary answer control.
- **Approval delivery:** Exact payload assertions distinguish bulk and ordinary approval, including absent keys. The pending-promise test checks all three disabled buttons, duplicate-click suppression, and pinning after completion. Forced retry retains `auto_approve: true`.
- **GraphView:** The two-pause scenario exercises the real component chain across distinct run IDs and iterations, checking subscription switching, old-panel removal, the new token fetch, and exact second-iteration text.
- **Shared fixture:** Python and TypeScript tests consume the same six explicit cases and pin their IDs. Expectations include suppressing an already-exceeded cap.
- **Fixture fidelity:** Endpoint tests generate actual paused traces and assert the cap and projected node type returned by `/api/gate`.
- No material test bloat or assertions encoding incorrect behavior were found.

### review-agent-ux — codex

- Pause renderers consistently use `iteration N of up to M`, omit unknown caps, and support older records without the field.
- CLI/MCP bulk hints provide a concrete resume command and retain the ruled human-consent clause.
- `/api/resume` errors identify invalid fields, required types, and contradictory answers; the client preserves these messages.
- The web tooltip explains approval scope by step name, including sub-workflows. Confirmation retries retain `auto_approve`; ordinary Approve remains single-use.
- Non-finite cap errors identify the step, template, offending value, and corrective action.
- The inspected changes provide actionable errors and parseable pause results. No confirmed UX regression against the supplied rulings was found.

### review-impact-completeness — codex

- Approval and escalation builders propagate `max_iterations`, including string-marker escalations.
- Consumers include TTY prompts, flag echoes, CLI/MCP pause output, answer-required diagnostics, resume-list text/JSON, and the web panel.
- Trace serialization and masking preserve the additive field; older records retain bare iteration rendering.
- Bulk approval reaches the client, server validation, preflight-derived step selection, and CLI arguments. Acknowledgement retries preserve `auto_approve`.
- Ordinary Approve and escalation answers retain existing behavior.
- Relevant guides, CLI documentation, and instruction files cover the changes.
- Trace readers accept `2.10.0`; no lexical-version comparison issue was found.
- Searches across direct callers, alternative renderers, persisted payloads, API consumers, and documentation found no concrete missed consumer.

### review-feature-interactions — codex

- **Abstraction boundaries:** None introduced. `max_iterations` extends the existing gate payload; browser bulk approval uses the existing resume CLI and resolver, preserving per-step-name matching across nested workflows.
- **Templates and resume:** Restored upstream values resolve before the resumed iteration. Own-output, iteration-dependent, coalesced, and dynamic-index references remain unknown. Evidence: `TestGateLoopCap`, `test_declared_cap_is_unknown_when_the_template_depends_on_the_loop_body`, and `test_loop_approval_after_first_iteration_pauses_with_position`.
- **Branching and recovery:** Back-edge re-entry may exceed the author cap; payloads preserve both values while renderers omit the misleading ceiling. Evidence: `test_back_edge_past_the_cap_drops_the_cap_clause`.
- **Escalations:** Auto-approval remains approval-only. The web panel excludes escalations; the endpoint refuses an approval answer on an escalation before spawning.
- **Resume refusals:** Acknowledgement and `force` retries retain `auto_approve`. Server tests pin exact CLI arguments, including ordinary approval for absent or false values.
- **Nested workflows and parallel batch:** Resolver propagation and worker prompt suppression remain intact. Existing tests cover nested approval delivery and `test_parallel_batch_gate_cannot_prompt_but_flag_approval_works`. Compilation and validation both reject direct loop-plus-batch.
- **Caching and snapshots:** Cap display preserves memo suppression, cache-before-gate ordering, and single-iteration `--only` behavior.
- **Trace compatibility:** Both payload locations receive the field. Old records retain bare iteration text; Python/web share the rendering fixture. CLI, MCP, resume-list, and `/api/gate` tests cover projections.
- **Version compatibility:** `2.10.0` remains compatible with numeric comparison and existing `2.x` readers.
- No concrete interaction regression was found; supplied rulings remain respected.

### review-spec-conformance — codex

The lens reported **spec-conformance review passes**. “Met” denotes implementation or recorded evidence, not independent execution.

- **Cap contract and derivation:** Upper-bound wording, nullable metadata, omission of safety-limit display, old-record compatibility, gate-time derivation, body-dependent unknown values, non-finite handling, and display-only consumption were met. Evidence includes `src/pflow/core/gate.py:57`, `:150`; `src/pflow/runtime/engine/loop_control.py:183`, `:224`; engine gate callers at `src/pflow/runtime/engine/gate.py:89`, `:167`; and `src/pflow/runtime/resume_source.py:1064`, `:1157`.
- **Rendering surfaces:** Shared Python/web rendering and the six-case fixture, TTY header/echo, non-TTY pause/JSON, MCP, answer-required diagnostics, resume-list text/JSON, and browser payload/eyebrow were met. Evidence includes `src/pflow/execution/gate_prompt.py:133`; `src/pflow/cli/commands/run.py:646`; `src/pflow/mcp_server/services/execution_service.py:230`; `src/pflow/core/exceptions.py:1756`; `src/pflow/cli/commands/resume.py:410`, `:449`; `src/pflow/ui/server.py:1568`; and `web/src/components/GateCallout.tsx:47`, `:142`.
- **Bulk-approval UX:** Human-authorized hints, loop-approval-only button visibility, unknown-cap availability, scope tooltip, and count-free “Approve all remaining” label were met. Evidence: `src/pflow/execution/gate_prompt.py:224`; `web/src/components/GateCallout.tsx:57`, `:136`, `:180`.
- **API behavior:** Boolean validation, contradictory-answer rejection, false/absent behavior, unknown-key and malformed-body rejection, exact CLI mapping, non-loop API parity, and escalation refusal were met. Evidence: `src/pflow/ui/server.py:1162`, `:1238`, `:1308`, `:1333`; `tests/test_cli/test_ui_interaction_server.py:1467`, `:1479`, `:1500`, `:1509`, `:1686`.
- **Browser interaction and layout:** Bulk submission, pinning, disabled buttons, forced retry, ordinary approval without `auto_approve`, and footer/eyebrow layout were met. Evidence: `web/src/components/GateCallout.tsx:180`; `resumeAnswer.tsx:54`; `GateCallout.test.tsx:205`, `:226`, `:235`; `web/src/views/GraphView.test.tsx:1596`; `web/src/index.css:2635`, `:2671`, `:2681`.
- **Trace serialization:** Both field locations were met at `src/pflow/runtime/workflow_trace.py:690`, `:1077`, `:1117`, with coverage at `tests/test_runtime/test_gate_trace.py:584`. The additive version requirement was **“Deviated with record”**: `2.10.0` correctly reflects recorded Task-180 sequencing, with a history comment and version test.
- **Regression scenarios:** Input-template, resumed, past-cap, capped/uncapped, non-loop, old-record, hint, shared-fixture, and named web tests were present. Evidence includes `test_gate_trace.py:619`; `test_gate_pause.py:300`, `:966`; `test_paused_cli.py:600`; and `GateCallout.test.tsx:120`, `:162`, `:205`, `:226`, `:235`, `:264`, `:516`.
- **Documentation:** Named engine/UI/component instructions, approval/resume/UI guides, approval-gates documentation, and CLI reference updates were met.
- **Recorded verification:** The P4 log records bulk completion with exactly three effects and ordinary approval reaching iteration two. Visual evidence covers capped/uncapped, non-loop, escalation, both viewport sizes, short/long previews, and Job 1 reshoots. Planning review dispositions, baseline merge, and serialized engine work were recorded.
- **Recorded local gates:** The latest log records **10,779 passed, 2 skipped**, and Task-159 **76 passed / 11 drifted / 0 errors**, with an identical baseline drift set.
- **Recorded departures:** Numbered answer-required suggestions, iteration-two `pre-approved` echo, MCP hint placement, `/api/gate` display-tag projection, P4 design choices, and main-owned ADR amendments were documented or ruled and explicitly **not findings**.
- **Unrequested behavior:** None identified. The non-finite-cap guard, stricter unknown-key validation, and node-type projection map to the plan or recorded ruling.

**Completion pending:** The inventory marks the remaining sequence **“Partial—completion pending.”** Windows CI, final falsifier/review dispositions, the completion document, and PR closeout are not established by the reviewed evidence. The conformance pass does not certify these gates.

### review-simplicity — codex

- `declared_loop_cap` reuses cap resolution without new engine state or threading display data through the walk.
- Python surfaces share `loop_position`; its TypeScript twin shares the case fixture.
- One bulk-hint implementation serves CLI, MCP, and answer-required diagnostics.
- Bulk approval reuses submission, refusal, and retry machinery; the server remains a thin CLI bridge.
- Eyebrow and tooltip share `shownCap`, keeping the past-cap rule local.
- The ruled `node_type` projection reuses the existing display utility.
- No material duplication, unnecessary abstraction, or separate mechanism was found.

## Coverage

**Eight review outputs from seven distinct lenses; all providers were `codex`.**

| Lens / review | Reported scope and limitations |
|---|---|
| review-silent-failures | Static review of changed logic and relevant callers; not exhaustive full-file reading of every changed file. Does not independently certify the full-branch completion gate. |
| review-test-fidelity — Python | `origin/main...679658d6`; nine specified Python test files and production paths. Browser behavior and test execution remain the caller’s responsibility. |
| review-test-fidelity — web | Named web tests, shared case table, pytest twin, and supporting production paths. Broader Python coverage was inspected only as supporting evidence. CSS assertions establish stylesheet rules, not actual viewport layout. |
| review-agent-ux | Changed UX paths and supporting code; large changed files and test modules were not all read in full. Focused assessment, not complete protocol-level sign-off. |
| review-impact-completeness | All changed hunks and mapped consumer paths; unchanged portions of large files were not exhaustively read. Reported confidence: moderate, not exhaustive completion-gate clearance. |
| review-feature-interactions | Full branch diff and traced intersections; unchanged portions of the largest source/test files were not exhaustively reread. Not complete full-file protocol sign-off. |
| review-spec-conformance | Every changed file read in full except excluded `uv.lock`; spec, plan, progress log, and both ruled artifacts reviewed. Recorded execution evidence was not independently executed. Remaining completion gates are listed above. |
| review-simplicity | Full branch diff and relevant enclosing code; protocol-required full-file reading was incomplete for large modules/tests. Partial review, not unconditional completion-gate sign-off. |

All reviews reported no test execution and no file modifications. The web test-fidelity review also explicitly reported no browser checks.

**Failed or missing lenses:** None listed in the supplied gaps input.
