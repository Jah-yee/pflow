# Merged Review Report

Merged findings from six independent lenses reviewing Task 184 against HEAD `05884642`. Findings retain their stated severity and attribution; duplicate defects are consolidated without adjudication. D1–D4 remain accepted by the reviews.

References below are relative to `/Users/andfal/projects/pflow-worktrees/feat-task-184-run-outcome`. Abbreviations:

- **Plan:** `.taskmaster/tasks/task_184/implementation/implementation-plan.md`
- **Checkpoint:** `.taskmaster/tasks/task_184/implementation/show-before-code.md`
- **Spec:** `.taskmaster/tasks/task_184/task-184.md`

## Convergent findings

### 1. Critical — CLI compilation failures can silently lose trace identity

**Convergence: 2 lenses — `review-plan`, `review-silent-failures`.** Both independently identify the same lifecycle defect and CLI↔MCP divergence.

The plan assumes trace identity is available before rendering, reads it from `trace.trace_path`, and removes the finalization-time trace announcement (**Plan:33, :153, :219**).

A missing required input exposes the ordering problem:

- Validation placeholders defer the missing-input error until compilation: `src/pflow/execution/runner.py:729–746`; `src/pflow/runtime/compilation/compile_validation.py:164`.
- The runner creates metrics and the trace collector before compilation: `src/pflow/execution/runner.py:198, :212, :356`.
- Streaming ordinarily begins inside the engine: `src/pflow/runtime/engine/engine.py:919`.
- `finalize()` opens a trace even for a zero-event run: `src/pflow/runtime/workflow_trace.py:1150`.
- CLI displays its result before finalization, while MCP finalizes before returning: `src/pflow/cli/commands/run.py:306, :348, :370`; `src/pflow/execution/runner.py:274`.

**Consequence:** CLI constructs a document without identity, then silently creates the trace afterward. MCP includes identity for the equivalent failure. Removing the existing stderr announcement makes the CLI trace undiscoverable from its output.

**Requested correction:** Settle trace availability before constructing these failure outcomes while preserving success JSON’s `set_json_output` ordering. Add real compilation-failure coverage through both CLI and MCP. Correct **Plan:279**, whose missing-input fixture incorrectly expects no collector.

**Related convergence by code area:** The architecture-fit open decision below separately concerns persisted trace output. It is a distinct artifact-contract issue, not a duplicate of this lifecycle defect.

### 2. Warning — “Never null” conflicts with preserved pricing and payload contracts

**Convergence: all 6 lenses — `review-plan`, `review-architecture-fit`, `review-impact-completeness`, `review-silent-failures`, `review-feature-interactions`, `review-agent-ux`.**

The plan preserves pricing fields and tri-state semantics, including `_mirror_pricing_tri_state`, while P1-T2 prohibits top-level nulls (**Plan:154, :304**). The checkpoint promises “absent, never null” but includes four nullable gate fields (**Checkpoint:17, :118**).

**Evidence:**

- Subscription-billed and unpriced calls deliberately produce `total_cost_usd=None`, distinguishing unobserved cost from zero: `src/pflow/core/metrics.py:200, :237–246, :449`.
- Existing tests explicitly preserve that null alongside subscription and partial-cost information: `tests/test_execution/formatters/test_success_formatter.py:727–732`.
- The shipped contract cautions against assuming cost is populated: `.taskmaster/tasks/task_158/task-review.md:426`.
- Nullable gate fields come from the canonical payload: `src/pflow/core/gate.py:50–64`.
- Workflow output nulls are legitimate data and are deliberately preserved: `src/pflow/execution/formatters/success_formatter.py:224–230`.
- ADR-0009 rejects per-surface payload shapes: `context/adr/0009-125-approval-surface-bridges.md:34`.

**Consequences identified by the lenses:**

- Preserving existing pricing violates the blanket guard; removing nulls changes the established cost-state contract.
- Tests restricted to zero-cost shell runs could miss the contradiction.
- An agent step followed by failure or pause cannot satisfy both planned rules.
- Blanket recursive cleanup could erase legitimate output data and create a different gate-payload dialect.
- Architecture-fit identifies this as a T3 agent-facing contract that would otherwise require a later correction across consumers, documentation, and fixtures.

**Requested correction:** Define absence per field, restricting omission rules to unavailable optional outcome metadata while explicitly retaining meaningful nulls in pricing, canonical gate payloads, and workflow outputs. Make the spec, checkpoint, and tests consistent; make P1-T2 field-specific. Include subscription/unpriced outcomes and a legitimate null result in the checkpoint and guards. Do not introduce recursive null removal. This does not reopen D1–D4.

### 3. Warning — Shared gate rendering can advertise answers after final denial

**Convergence: 5 lenses — `review-plan`, `review-impact-completeness`, `review-silent-failures`, `review-feature-interactions`, `review-agent-ux`.**

The proposed `gate_lines` combines gate content with `To answer: <resume_command>` and a bulk-approval hint (**Plan:205**). Gate sections are used for paused and denied outcomes (**Plan:215, :217**), although denied documents intentionally omit `resume_command` (**Plan:165–167**).

**Evidence:**

- Today, answer commands and bulk-approval hints are confined to paused rendering: `src/pflow/cli/commands/run.py:715–718`.
- Denied rendering emits the stopped-run message: `src/pflow/cli/commands/run.py:548`.
- The bulk-hint helper checks gate kind and iteration, not outcome status: `src/pflow/execution/gate_prompt.py:229–236`.
- The checkpoint’s denied example shows completion and lineage without answer instructions, so it does not expose the shared-composition discrepancy: **Checkpoint:145**.

**Failure scenario:** Resume a looping approval gate with `resume <token> --approve no`. Literal reuse of the shared section can access an absent command, print an empty answer instruction, or recommend approving remaining iterations after terminal denial.

**Requested correction:** Separate gate-content rendering from answer actions. Require PAUSED status and a present command before rendering answer instructions; restrict bulk-approval hints to PAUSED as well. Add resumed loop-denial coverage, including `-p`, asserting that gate content and lineage remain while `To answer:` and bulk-approval hints are absent. Extend the checkpoint’s denied rendering accordingly.

**Related convergence by code area:** `review-agent-ux` also identifies loss of the paused node’s identity in this shared rendering area. That distinct warning is retained below.

### 4. Warning — Batch failure details have contradictory `-p` suppression rules

**Convergence: 3 lenses — `review-plan`, `review-feature-interactions`, `review-agent-ux`.**

The tier table assigns “batch-error details” to must-act and “batch-errors” to suppressible summary (**Plan:139–140**). The proposed `batch_blocks` combines batch errors with suppressible shell-stderr warnings (**Plan:199**). Checkpoint Q1 proposes hiding batch blocks under `-p` without specifying a failure exception (**Checkpoint:196, :198**).

**Evidence:**

- One renderer supplies item indices, provider diagnoses, and reconstructed child-workflow failure details: `src/pflow/execution/formatters/batch_errors.py:14–45`, particularly `:26, :30`.
- Current failure rendering emits that section regardless of `-p`: `src/pflow/cli/workflow_errors.py:86–93`.
- For an all-failed batch using `error_handling: continue`, the general exception summarizes only the first three errors: `src/pflow/runtime/engine/batch_executor.py:1198`.
- Existing detailed failure tests cover ordinary text and JSON, not `-p`: `tests/test_cli/test_enhanced_error_output.py:292, :327`.
- P2-T5 currently names error, gate, and resume blocks: **Plan:352**. The manual fixtures contain no batch case.

**Consequence:** Either interpretation contradicts part of the plan. Suppressing the combined block can remove the actionable item/provider/child diagnosis from a text-only failure, especially for batches of child workflows.

**Requested corrections from the lenses:**

- `review-plan`: Choose one explicit tier rule, update Q1, and test failed and degraded batches with and without `-p`.
- `review-feature-interactions`: Keep failure details independently renderable from shell-stderr summaries and add failed-batch × `-p` coverage.
- `review-agent-ux`: Specify that failed-run batch diagnostics survive `-p`; optional shell-stderr summaries may remain suppressed. Add the all-failed case to P2-T5.

### 5. Warning — Extending success-only `--only` counting to gate-stopped outcomes produces false counts and wording

**Convergence: 2 lenses — `review-impact-completeness`, `review-feature-interactions`.** Both identify the same inherited count formula; their denial and refusal scenarios are preserved separately.

The plan copies today’s success execution fields across statuses and adds the mode line to every status (**Plan:157, :198**). The success formatter counts every `not_executed` row as `nodes_skipped`, then describes that count as “other nodes not executed”: `src/pflow/execution/formatters/success_formatter.py:124, :126, :569`.

**Evidence and scenarios:**

- **Impact-completeness:** In a three-node workflow run with `--only three`, denying the target’s approval leaves the target unexecuted too. `only_node` is stamped before the gate, and the gate exception bypasses ordinary failure recording: `src/pflow/runtime/engine/engine.py:1269, :1622, :1696`. The proposed output says **“Ran only 'three' … 3 other nodes not executed”**, although there are only two other nodes and the target never ran.
- **Feature-interactions:** Seed a successful three-step workflow, then run `--only gated` without approval. The engine stamps `only_node`, but the gate stops the target without marking it failed; this attempt ends FAILED rather than PAUSED: `src/pflow/runtime/engine/engine.py:1270, :1584, :1629`. All three steps remain `not_executed`, yielding the same incorrect “three other nodes” count.
- Existing coverage checks fail-versus-pause wording, not the count: `tests/test_cli/test_paused_cli.py:301`.

**Requested correction:** Exclude the target from the “other nodes” count and specify truthful mode wording for gate-stopped attempts. Test the JSON count and ordinary/`-p` text for these newly shared status consumers.

## Critical

No additional non-convergent Critical findings were reported.

`review-architecture-fit` reported no proven roadmap collision requiring reversal of the central builder-and-renderers design. `review-impact-completeness` confirmed no Critical unconverted-consumer break; `review-feature-interactions` established no Critical unhandled combination; `review-agent-ux` established no Critical issue by static review.

## Warnings

### 6. Warning — Planned verification does not deliver the required adapter-level guards

**Lens: `review-plan`.**

The spec requires a common-key matrix on real CLI JSON endings and CLI↔MCP parity including lineage (**Spec:140–142**).

P1-T1 instead tests the builder on runner results (**Plan:296**). P3-T2 checks warnings and identity presence without lineage (**Plan:374**). These can pass despite adapter timing defects such as convergent finding 1.

**Requested correction:** Add the real CLI JSON matrix explicitly and exercise both renderers/adapters with a real resumed result. This does not require adding MCP resume functionality. Include the spec’s explicit `tests-windows` gate (**Spec:173**) in completion requirements.

### 7. Warning — The planned MCP pause renderer loses the paused step’s identity

**Lens: `review-agent-ux`.**

**Same-area convergence:** Five lenses identify denial-unsafe shared gate rendering in finding 3. This warning concerns a separate loss of identification within that rendering area.

**Evidence:**

- The plan reuses existing completion-status arms, replacing only DENIED: **Plan:194**.
- The existing PAUSED arm says only `⏸ Workflow paused at gate after …`: `src/pflow/cli/workflow_output.py:677`.
- `format_gate_lines` renders content and iteration, not the node ID: `src/pflow/execution/gate_prompt.py:253`.
- The plan deletes `paused_node_id:` and changes its test to assert `Gate:`: **Plan:365**.
- The checkpoint nevertheless claims that “the header and `Gate:` name the step”: **Checkpoint:192**.

**Failure scenario:** A fresh, non-looping approval pause through MCP has no resume-lineage line. The planned composition supplies a generic pause header, command preview, and token, but no step name.

**Requested correction:** Specify the PAUSED arm explicitly, for example `⏸ Workflow paused at 'three' — a human decision is required.` Retain a test asserting the actual node ID rather than only the section heading.

## Open decisions

### 8. Open decision — Explicitly account for the persisted `json_output` change

**Lens: `review-architecture-fit`. Severity was not assigned; the lens classified this as an open decision and T4 artifact change.**

**Same-area convergence:** `review-plan` and `review-silent-failures` independently identify trace lifecycle problems in finding 1. This finding concerns the separate persisted-document contract.

**Plan:182** claims that storing `outcome.document` leaves the trace trailer’s content unchanged. The lens identifies changed content: the new success document adds identity and `errors`, and removes both attempted-count fields.

**Evidence:**

- `set_json_output` stores the supplied dictionary directly: `src/pflow/runtime/workflow_trace.py:1450`.
- `_aggregates` writes it into the trailer: `src/pflow/runtime/workflow_trace.py:1105`.
- The existing UI consumer reads only `json_output.result` and remains compatible: `src/pflow/ui/run_node.py:202`.

The lens explicitly states that this is **not a demonstrated UI break**. It is an unpriced T4 artifact change inherited by stored traces and Task 175 output inspection.

**Requested decision:** Specify whether `json_output` is a variable CLI-document snapshot whose envelope may evolve independently, or a versioned trace sub-contract. Record the compatibility/version consequence and correct the unchanged-content claim before implementation.

## Suggestions

No lens reported additional Suggestions beyond the corrections and open decision preserved above. `review-plan` explicitly recommended no additional scope expansion.

## Verified clean

### `review-plan`

- The runner exception path omits metrics; the normal path carries them: `src/pflow/execution/runner.py:446–453, :946–952`.
- Resume uses the same CLI execution dispatch: `src/pflow/cli/commands/resume.py:184`.
- Restored nodes are deliberately excluded from this attempt’s completed count, making the checkpoint’s count-plus-lineage presentation useful and truthful: `src/pflow/execution/execution_state.py:113–145`.
- The probe is a real second consumer of the deleted MCP error builder; retaining a thin diagnostic helper is justified: `src/pflow/mcp_server/services/execution_service.py:791`.
- Greppable MCP identity, complete error lists, and explicit resume commands improve agent actionability. Preserving `Diagnostic.to_output_dict()` and the gate-masking helper retains established display boundaries.

### `review-architecture-fit`

- Stable MCP identity labels, all-error rendering, and resume commands improve actionability without adding another answer mechanism. Q1/Q4 remain explicit choices.
- Task 117 retains its required `output_error()` seam through exception-only preservation: `.taskmaster/tasks/task_117/task-117.md:136`.
- Task 178’s pending transport decision can wrap existing rendered error text without reversing the renderer: `.taskmaster/tasks/task_178/task-178.md:97`.
- One outcome seam centralizes field rules while retaining existing diagnostic, durability, and gate-rendering seams.
- The shared gate payload and MCP text layout are sound subject to checkpoint rulings; their inheriting consumers include Task 152 parity, Task 178 SDK migration, and approval bridges.
- The current UI consumer remains compatible with the persisted-document change because it reads only `json_output.result`: `src/pflow/ui/run_node.py:202`.
- The full live task board ran successfully.

### `review-impact-completeness`

- Reviewed the checkpoint’s JSON matrix, example documents, text renderings, and Q1–Q4.
- The deletion map accounts for CLI dispatch, resume’s shared dispatch, MCP success/failure/pause, and the probe’s second `_build_error_text` caller.
- Partial outputs, diagnostic serialization, MCP advisory filtering, output-selection precedence, and trace/UI consumer separation have explicit preservation paths.
- D1–D4 remain intact; the findings concern applying established rules to newly shared consumers.
- Type checking and import checks do not establish these field semantics or status-dependent text behavior.

### `review-silent-failures`

- Partial outputs remain limited to output-resolution failures, preserving `None` versus an empty dictionary.
- Non-durable pauses retain error diagnostics and normalize to FAILED.
- MCP failures remain raised errors rather than successful text responses.
- The deletion inventory preserves the probe’s separate error-text consumer.
- Resume lineage, restored-step counting, batch-detail truncation indicators, and text output-routing diagnostics have identified preservation paths.
- The identity block and removal of the three-error cap improve agent actionability.

### `review-feature-interactions`

- **Resume × failure/denial:** Lineage comes from shared execution state; P1/P2 explicitly cover both endings: **Plan:312, :344**.
- **MCP × gate durability:** FAILED normalization and raised failure text are preserved. Existing file-versus-inline coverage exercises this distinction: `tests/test_integration/test_cli_mcp_parity.py:271`.
- **Batch × output routing:** The shared output classifier and CLI data renderer preserve target-scoped `--only` selection and dotted `-o` paths. Existing integration tests cover these intersections: `tests/test_integration/test_cli_mcp_parity.py:70, :95`.
- **Output-resolution failure × partial results:** The dedicated partial-output collector remains and feeds both renderers: **Plan:163, :206**.
- The shared builder addresses cross-channel drift, and the checkpoint makes identity and lineage clearer for agents.

### `review-agent-ux`

- The checkpoint explicitly demonstrates success identity, exception-failure metrics, and resumed-denial lineage, improving run correlation and interpretation: **Checkpoint:39, :65, :145**.
- Empty `errors` on PAUSED, with retained errors for non-durable pauses, is clearly specified and guarded: **Plan:308**.
- Preserving `collect_outputs_resolved_before_failure` distinguishes actual partial outputs from unrelated stored values: **Plan:163**; `src/pflow/execution/formatters/success_formatter.py:281`.
- Reusing `format_diagnostic`, printed diagnostic serialization, and existing resume-command helpers preserves actionable context and established formatting: **Plan:201, :317, :431**.

## Coverage

| Lens | Provider | Review produced |
|---|---|---|
| `review-plan` | codex | Yes |
| `review-architecture-fit` | codex | Yes |
| `review-impact-completeness` | codex | Yes |
| `review-silent-failures` | codex | Yes |
| `review-feature-interactions` | codex | Yes |
| `review-agent-ux` | codex | Yes |

**Failed-lens coverage gaps: None.** The supplied gaps list is empty.

**Reported review limits and outstanding coverage:**

- All six reviews were read-only; none ran tests or changed files. `review-silent-failures` also explicitly reports no probes.
- `review-plan` inspected production builders and key consumers but did not exhaustively audit the test/document migration inventory.
- `review-architecture-fit` leaves exhaustive deletion coverage and feature-combination correctness to other lenses.
- `review-impact-completeness` reports high confidence in mapped production entry points and lower confidence in the untested feature combinations it identifies.
- `review-silent-failures` leaves runtime verification, including the full batch/`--only` interaction matrix, to the caller.
- Adapter-level CLI JSON, CLI↔MCP lineage, compilation-failure, nullable-pricing/output, denied-loop, batch × `-p`, and gate-stopped `--only` coverage gaps are preserved in the findings above.
- `review-plan` notes that CP-1 still records “awaiting ruling” at **Checkpoint:3**, separately from accepted D1–D4 decisions.

The lenses’ readiness assessments remain: `review-plan` says the plan is not ready for implementation unchanged; the other reviews support the consolidation while requiring the identified contracts, interactions, or artifact decision to be resolved before coding.
