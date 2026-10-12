# Merged Review Report

## Convergent findings

### Warning — Successful CLI output retains trace identity after finalization invalidates it

**Lenses:** `review-spec-conformance` W1, `review-silent-failures` W1, `review-feature-interactions` W2.
**Convergence:** Three lenses independently identified the same defect at `src/pflow/cli/commands/run.py:416`.

Successful/degraded CLI runs build the outcome before trace finalization. The builder immediately copies `execution_id` and `trace_path` (`src/pflow/execution/formatters/run_outcome.py:93`). If writing or flushing `run.complete` fails—for example, because disk space runs out—streaming is disabled and the collector’s trace path is cleared. The previously built document retains both identity fields.

Evidence cited by the lenses:

- Document construction, trace snapshot, finalization, and emission: `src/pflow/cli/commands/run.py:416`, `:421`, `:423`, `:434`, `:438`.
- Trailer-write/flush failure and streaming invalidation: `src/pflow/runtime/workflow_trace.py:1033`, `:1036`, `:1120`, `:1127`, `:1129`, `:1155`.
- Ordinary text still prints `Workflow trace saved:`: `src/pflow/execution/formatters/run_outcome.py:552`.
- A streaming warning is logged, but JSON still identifies the incomplete trace as valid.
- MCP builds after finalization, producing CLI/MCP disagreement under this failure.
- `--report` skips generation because finalization returned no path (`src/pflow/cli/commands/run.py:120`).
- Existing identity tests cover healthy persistence and `--no-trace`, not trailer-write failure (`tests/test_cli/test_run_outcome_cli.py:409`, `:419`).

All three lenses explicitly challenge an **accepted ordering**, rather than identify an unlogged implementation departure: “build → set_json_output → finalize → emit” is recorded in `.taskmaster/tasks/task_184/implementation/progress-log.md:59`, also discussed at `:295`, and in plan §4.4 (`implementation-plan.md:256`). The cited requirement is that identity fields appear together exactly when the trace streamed to disk, with stream faults leaving both absent (`.taskmaster/tasks/task_184/task-184.md:120`).

**Recommendations preserved:** Keep the successful workflow result and the pre-finalization `set_json_output` snapshot, reconcile emitted identity with finalization’s settled state, omit invalid identity and the saved-trace announcement, and add a regression guard specifically for trailer-write failure.

**Evidence status:** Static findings; runtime confirmation was left to `review-falsifier`.

### Suggestion — Fixture-driven status normalization has differing assessments

**Finding lens:** `review-simplicity`.
**Same-area convergence:** `review-agent-ux` independently examined the same normalization arm and recommended retaining it. These assessments are preserved without resolution.

At `src/pflow/execution/formatters/run_outcome.py:137`, `success=False` overrides SUCCESS/DEGRADED to FAILED. Both production constructors explicitly supply status (`src/pflow/execution/runner.py:451`, `:952`), while the contradictory fixture is supported by `tests/test_execution/formatters/test_run_outcome.py:504`.

- **`review-simplicity` — Suggestion:** Remove the fixture-driven normalization arm and give failing fixtures explicit `status=WorkflowStatus.FAILED`. The arm creates a second authority for status, requiring readers to distinguish producer status from formatter repair of invalid fixtures. Retain non-durable-pause normalization; changing the dataclass default is unnecessary. This revisits the accepted deviation at `.taskmaster/tasks/task_184/implementation/progress-log.md:795`, which explicitly invites this challenge.
- **`review-agent-ux` — Retain the arm:** Neither choice has a current production-visible consequence because production returns supply status explicitly. For inconsistent fixtures, the guard prevents `success:false` from accompanying a success renderer and exit 0. This lens found no agent-UX reason to reverse the accepted coherence guard.

## Critical

No lens reported a Critical finding. The lenses variously stated that none were identified, found, established, or demonstrated within their reviewed scope.

## Warnings

### Resume × looping approval × denial counts a previous attempt’s output as completed work

**Lens:** `review-feature-interactions` W1.

The document derives completed counts from `build_execution_steps` at `src/pflow/execution/formatters/run_outcome.py:164`.

Concrete scenario: run a gated loop, approve iteration 1, pause at iteration 2, then resume with `--approve no`.

1. Resume seeds the loop target’s previous output (`src/pflow/runtime/resume_source.py:1016`, `:1031`).
2. The target is deliberately excluded from `restored_nodes` (`src/pflow/runtime/engine/engine.py:677`).
3. Denial occurs before execution and preserves that output (`src/pflow/runtime/engine/engine.py:1359`, `:1583`).
4. The step builder labels the seeded target `completed` (`src/pflow/execution/execution_state.py:143`).
5. The denial renderer reports **“Steps completed: 1 of 1”**, although this attempt executed nothing (`src/pflow/execution/formatters/run_outcome.py:392`).

The lens states that this regresses the deleted denial renderer’s use of this attempt’s `completed_nodes` and violates the restored-versus-executed rule (`.taskmaster/tasks/task_184/task-184.md:93`). Re-pausing at iteration 2 without approving also produces an incorrect JSON completed count.

**Recommendation:** Distinguish a seeded loop value from completion in this attempt while preserving loop carry. Extend `test_denied_looping_gate`, which already exercises this sequence and checks one historical side effect but not the count (`tests/test_cli/test_run_outcome_cli.py:518`).

### P2-T5’s paused-warning presence/absence test is missing

**Lens:** `review-spec-conformance` W2.

The plan explicitly requires failure/paused tiers under `-p`, including warnings present without `-p` and absent with it in the same medium (`.taskmaster/tasks/task_184/implementation/implementation-plan.md:407`).

`TestTiersUnderPrint.test_pause` uses a warning-free workflow and checks only gate/token/trace behavior (`tests/test_cli/test_run_outcome_cli.py:447`). The warning pair at `:431` covers failure; `tests/test_execution/formatters/test_run_outcome.py:339` checks paused document contents without CLI tier rendering.

Consequently, a pause-specific regression that drops ordinary warnings or exposes them under `-p` lacks the promised guard.

**Recommendation:** Add a paused run carrying a real warning and assert both stderr halves. No logged ruling defers this obligation.

### Migrated MCP regression tests no longer exercise the MCP renderer

**Lens:** `review-test-fidelity` W1.

The shell-stderr preview and completion glyph are asserted through section helpers (`tests/test_execution/formatters/test_run_outcome.py:818`), and `TestCostLines` checks cost helpers (`:1143`). Their predecessors exercised the complete MCP response.

Removing either section from `src/pflow/execution/formatters/run_outcome.py:580` would leave these assertions satisfied while MCP lost shell failure clues or billing information.

**Recommendation:** Extend the existing noisy/clean and cost cases to assert corresponding content in `render_mcp_text(outcome)`. Restoring the old test volume is unnecessary.

This challenges retaining the logged section-only migration at completion: `.taskmaster/tasks/task_184/implementation/progress-log.md:226` explicitly deferred renderer coverage to P2/P3.

### The pricing-key absence assertion lacks its JSON presence twin

**Lens:** `review-test-fidelity` W2.

`tests/test_execution/formatters/test_run_outcome.py:321` asserts that subscription billing omits `pricing_available`. Unpriced cases assert only rendered cost lines, which read nested metrics.

Dropping top-level unpriced discriminators from `_mirror_pricing_tri_state` (`src/pflow/execution/formatters/run_outcome.py:245`) would escape these checks: JSON would retain an unexplained `total_cost_usd: null`, while cost text remained correct.

**Recommendation:** Strengthen an existing mixed-cost case to assert `pricing_available == False`, unavailable-model counts, and partial cost in the document before checking its text.

### Remaining review instructions describe obsolete error routing

**Lens:** `review-impact-completeness`.

Two instruction consumers retain the former routing rule:

- `.claude/agents/review-silent-failures.md:179` instructs reviewers to “verify all new error paths route through” `cli/error_output.py`.
- `.claude/agents/review-agent-ux.md:35` describes that module as handling “ALL error types.”

Run failures now use the outcome builder (`src/pflow/cli/commands/run.py:416`). The exception-only document (`src/pflow/cli/error_output.py:28`) omits identity, metrics, and lineage. Following these stale instructions would direct future work away from the shared outcome and recreate those omissions.

**Recommendation:** Update both rows to distinguish run outcomes from exceptions without a run. Path-reference checks cannot catch this semantic contradiction because `error_output.py` still exists.

### Documentation directs agents to an unsupported report command

**Lens:** `review-agent-ux` W1.

`docs/reference/cli/index.mdx:325` says execution ID and trace path can both be passed to `pflow report`: “Pass either.”

An agent following this with `pflow report <execution_id>` gets `Trace file not found: <execution_id>` and exit 1. The command treats its argument as a filesystem path and does not resolve execution IDs (`src/pflow/cli/commands/report.py:76`).

**Recommendation:** Replace the sentence with “Pass `trace_path` to `pflow report`.”

## Suggestions

### Remove the unused `output_error(ctx, …)` parameter

**Lens:** `review-simplicity`; classified as a minor, optional Suggestion.

`src/pflow/cli/error_output.py:44` retains `ctx`, but neither branch reads it. This is inherited interface clutter surviving the rewrite, not a new regression.

**Recommendation:** Remove the parameter and corresponding caller arguments, such as `src/pflow/cli/commands/run.py:289`, eliminating a false context dependency.

### Qualify the unconditional trace promise

**Lens:** `review-agent-ux` S1.

`src/pflow/mcp_server/resources/instructions/mcp-agent-instructions.md:853` promises a saved trace and identity lines on every run. Validation failure during `_prepare_workflow` occurs before trace creation (`src/pflow/execution/runner.py:190`); the builder correctly omits identity when no trace exists (`src/pflow/execution/formatters/run_outcome.py:93`).

**Recommendation:** Use wording such as “CLI and MCP runs save traces by default; when a trace was written, the MCP response includes…” to avoid directing agents to search for nonexistent traces after early validation errors.

### Reconcile pending completion artifacts

**Lens:** `review-spec-conformance`.

The spec still says “not started”; real-surface transcripts remain in the progress log rather than a committed task-review artifact; Windows CI has no recorded green result.

References:

- `.taskmaster/tasks/task_184/task-184.md:15`, `:174`, `:177`.
- `.taskmaster/tasks/task_184/implementation/progress-log.md:826`, `:860`, `:1172`.
- Final status, task-review, and PR references remain close-out work; the baseline case list is prepared at `progress-log.md:838`.

The lens explicitly classifies these as **pending completion evidence, not demonstrated code failures**.

## Verified clean

Assertions below retain each lens’s scope and qualifications. They are not reconciled against other lenses’ findings.

### `review-simplicity`

- **Keep `execution` whenever the IR has nodes.** `src/pflow/execution/formatters/run_outcome.py:160` applies one rule independent of collector availability. An all-`not_executed` table explicitly communicates that no listed step ran. Collectors exist before compilation (`src/pflow/execution/runner.py:198`), so metrics presence does not establish execution. This supports plan §3.1 and resolves the question at `progress-log.md:851`.
- **The consolidation earns its seam.** The builder owns document assembly; renderers compose shared identity, counts, lineage, and diagnostic sections (`run_outcome.py:65`, `:518`, `:559`). Combining renderers would introduce channel switches without removing their real differences.
- **The probe helper earns its interface.** `format_error_text` composes existing diagnostic sections without introducing another run document (`run_outcome.py:616`).
- The integrated design substantially deletes complexity rather than relocating it. No Critical or Warning simplicity finding was reported.
- Spec D1–D4, plan CP-1/F20 and §§2–6, AFTER shapes, and logged deviations were considered. PAUSED-only gates, warnings before errors, denial without an error block, and token-first stdout were accepted shapes (`progress-log.md:791`).

### `review-spec-conformance`

The lens’s requirement inventory reported:

| Requirement or obligation | Preserved verdict and evidence |
|---|---|
| One producer; common and status-specific fields | **MET.** `run_outcome.py:65`, `:87`, `:96`, `:109`, `:151`, `:164`, `:211`, `:225`; CLI `run.py:416`; MCP `execution_service.py:166`; tests `test_run_outcome.py:52`, `:232`, `:258`; real CLI matrix `test_run_outcome_cli.py:266`. |
| Errors always a list; optional values absent rather than null, while intentional producer nulls survive | **MET.** `run_outcome.py:81`, `:93`, `:105`, `:109`, `:172`, `:186`; tests `test_run_outcome.py:270`, `:288`, `:339`. |
| Trace identity | **PARTIAL.** Builder condition is correct (`run_outcome.py:93`); successful CLI snapshots before finalization (`run.py:416`). See convergent warning. |
| Pre-engine identity settlement | **MET.** `run.py:412`; `test_run_outcome_cli.py:498`; `test_cli_mcp_parity.py:532`. |
| Exception metrics and collector boundaries | **MET.** `runner.py:453`, `:952`; `test_runner.py:1452`, `:1474`, `:1483`, `:1508`, `:1525`. Deterministic exception-fixture substitution accepted at `progress-log.md:147`. |
| JSON unchanged by `-p` | **MET.** `run.py:437`; `test_run_outcome_cli.py:372`. |
| CLI failure, lineage, cost, warning, and trace sections | **MET, subject to trace warning.** `run_outcome.py:374`, `:421`, `:518`, `:661`; tests `test_run_outcome_cli.py:296`, `:316`, `:428`. |
| Denied completed count and lineage | **MET.** `run_outcome.py:386`, `:431`; fresh/resumed denial tests `test_run_outcome_cli.py:336`, `:355`. |
| MCP rendering from the document and failure raising | **MET.** `execution_service.py:166`, `:174`; `run_outcome.py:559`; parity tests `test_cli_mcp_parity.py:424`, `:441`. |
| Print tiers | **MET implementation; PARTIAL named guard.** `run_outcome.py:533`; failure/batch pairs `test_run_outcome_cli.py:431`, `:474`, `:483`; missing paused-warning pair reported above. |
| Shared real-run matrix and CLI↔MCP parity | **MET**, with parity under the plan’s renderer-seam approach. Shared constants `test_run_outcome.py:52`, imported at `test_run_outcome_cli.py:20`, asserted at `:266`; parity `test_cli_mcp_parity.py:441`, `:532`; resumed MCP rendering `test_run_outcome.py:399`. |
| Bespoke tests updated rather than duplicated | **MET in inspected changes.** Old formatter suites removed; replacement outcome suite and migrated assertions at `test_paused_cli.py:112`, `test_resume_cli.py:946`, `test_metrics_integration.py:179`. |
| Printed diagnostics use `Diagnostic.to_output_dict()` | **MET.** `run_outcome.py:84`, `:106`; redaction tests `test_run_outcome.py:538`. |
| Identity independent of resumability; non-durable pause preserves errors | **MET.** `run_outcome.py:93`, `:232`, `:81`, `:134`; tests `test_run_outcome.py:258`, `:356`. |
| Builder scenarios P1-T1–T7 | **MET:** common keys, null rules, counts, pause normalization, lineage, bare results, redaction. `test_run_outcome.py:232`, `:288`, `:324`, `:336`, `:379`, `:475`, `:538`. |
| Stopped `--only` target count and wording | **MET.** `run_outcome.py:182`, `:729`; `test_run_outcome.py:437`. |
| CLI obligations P2-T1–T4 and P2-T6–T9 | **MET:** failure metrics, lineage, JSON invariance, successful identity, exits, adapter matrix, compile identity, denied-loop answer suppression. `run_outcome.py:30`; `test_run_outcome_cli.py:266`, `:296`, `:316`, `:372`, `:406`, `:498`, `:514`; `test_paused_cli.py:1025`. |
| MCP obligations P3-T1–T6 | **MET:** metrics, warning/identity parity, every error, advisory filtering, paused step, lineage. `test_cli_mcp_parity.py:424`, `:441`, `:464`, `:480`, `:521`; `test_run_outcome.py:399`. |
| Documentation and instructions | **MET for inspected contract changes.** `docs/reference/cli/index.mdx:244`, `:321`; `src/pflow/guide/features/resume.md:19`; MCP instructions `:853`; three directory `CLAUDE.md` files and six agent definitions updated. Targeted searches found no stale run-document keys. |
| Real-surface verification | **PARTIAL.** CLI/MCP transcripts at `progress-log.md:860`, `:1172`; no committed task-review artifact. HTTP exception and resumed denial **MET as recorded evidence**, at `:942`, `:1020`. |
| Local suite, baseline, Windows | **PARTIAL.** Local suite and baseline recorded green at `progress-log.md:818`; Windows explicitly assumed at `:826`. |
| Deletion inventory | **MET.** Old success/error formatters and `workflow_errors.py` deleted; CLI/MCP call the shared builder. |
| Success-JSON trace snapshot and trace version | **MET / recorded decision.** `run.py:421`; snapshot semantics accepted at `progress-log.md:73`; no trace-version-bump finding. |
| Out-of-scope boundaries | **MET in inspected changes.** Dry-run dispatch `run.py:496`; separate probe `execution_service.py:513`; engine change comment-only; #804(d) deferral accepted at `progress-log.md:1239`. |

Additional preserved qualifications and accepted deviations:

- Probe helper/signature and fallback: **DEVIATED-BY-RULING**, including removal of unused `trace_path`; `run_outcome.py:616`, `execution_service.py:620`, `test_run_outcome.py:1009`, `progress-log.md:795`.
- Renderer ordering, denial gate/errors, and paused token position: **DEVIATED-BY-RULING**; `run_outcome.py:536`, `:589`, `run.py:427`, `progress-log.md:791`.
- Changelog and fixture copies: **DEVIATED-BY-RULING**, reverted/skipped at `progress-log.md:1236`, `:1240`.
- The semantic one-run-producer requirement is met, although the plan’s literal grep prediction is inaccurate. The search returned the run producer (`run_outcome.py:88`), permitted exception document (`cli/error_output.py:29`), validation-only response (`cli/commands/run.py:468`), probe (`cli/commands/_probe_impl.py:262`), and single-node responses (`node_output_formatter.py:209`, `:223`, `:662`). `plan_formatter.py` does not match that literal search.
- No unrequested behavior was identified in inspected changes. Status normalization, probe wording, shell-stderr preview, capture normalization, and renderer differences had plan/log authorization (`progress-log.md:173`, `:228`, `:242`, `:795`, `:806`).

### `review-impact-completeness`

- CLI and MCP run adapters call the shared builder; CLI JSON serializes its document (`src/pflow/cli/commands/run.py:416`; `src/pflow/mcp_server/services/execution_service.py:165`).
- The UI still reads the preserved `json_output["result"]` field (`src/pflow/ui/run_node.py:202`).
- Searches found no remaining deleted-formatter-symbol references across the searched production, test, script, documentation, and agent surfaces.
- No runtime consumer omission was demonstrated. Consumer-map confidence was moderate.
- Spec D1–D4, plan header and §§2–6, AFTER shapes, and phase rulings were read. Gate, warning, denial, token, probe-signature, changelog, and #804(d) decisions were treated as accepted.

### `review-silent-failures`

- Exception-path metrics reach `ExecutionResult`, including failures after earlier completed steps (`src/pflow/execution/runner.py:263`, `:957`).
- Non-durable pauses normalize to failure without losing error diagnostics (`src/pflow/execution/formatters/run_outcome.py:127`).
- Completed-step counting and resume lineage are built independently of ending status (`run_outcome.py:160`).
- Failed-batch details and failure diagnostics survive text `-p`; MCP failures remain raised errors (`run_outcome.py:539`; `src/pflow/mcp_server/services/execution_service.py:173`).
- Spec D1–D4, plan CP-1/F20 and §§2–6, AFTER shapes, and logged deviations informed the review. Accepted gate, denial, ordering, and probe decisions were not otherwise challenged.

### `review-test-fidelity`

- Five real CLI endings check exact common/by-status key sets, including genuine resume-to-denial (`tests/test_cli/test_run_outcome_cli.py:266`).
- #695 tests compare success JSON with actual trace metadata and pair it with `--no-trace` (`test_run_outcome_cli.py:406`).
- #699 reaches the exception return through unresolved templates and checks metrics/failure lines for both failure kinds (`tests/test_execution/test_runner.py:1483`; `test_run_outcome_cli.py:297`).
- #737 exercises real failed/denied resumes and distinguishes restored steps from this attempt’s completed steps (`test_run_outcome_cli.py:316`).
- Production-adapter parity explicitly requires nonempty warnings, preventing vacuous comparison (`tests/test_integration/test_cli_mcp_parity.py:441`).
- Core regression tests provide meaningful confidence; no substantial test bloat was found.
- Spec D1–D4 (`task-184.md:77`), plan rulings/§§2–6 (`implementation-plan.md:7`), AFTER shapes (`show-before-code.md:21`), and accepted deviations (`progress-log.md:791`) were checked.

### `review-agent-ux`

- **Same-area convergence with `review-simplicity`: retain the all-`not_executed` execution block.** It explicitly communicates zero completed steps and which steps never ran. Evidence: `.taskmaster/tasks/task_170/implementation/examples-baseline/invalid__code-missing-result-annotation.json:54`; aggregate duration is omitted without metrics at `src/pflow/execution/formatters/run_outcome.py:164`. This supports plan §3.1 and the question at `progress-log.md:1241`.
- Its assessment supporting status normalization is preserved in the convergent-findings section.
- Exception and action failures share completion/error sections; every diagnostic renders without the former three-error cap; failed-batch details remain visible under text `-p` (`run_outcome.py:446`, `:535`).
- Pause-only gate content and answer commands distinguish pauses from denial; denial reports counts without inviting another answer. Resume and `--only` indicators survive summary suppression (`run_outcome.py:380`, `:424`, `:472`).
- CLI JSON is independent of `-p`; MCP ends with consistent identity fields; partial resolved outputs are explicitly labelled (`src/pflow/cli/commands/run.py:437`; `run_outcome.py:497`).
- Resume lineage, renamed `gate`, denial status, and MCP Returns documentation match the central behavior (`src/pflow/guide/features/resume.md:19`; `approval.md:12`; `src/pflow/mcp_server/tools/execution_tools.py:88`).
- No renderer regression was established across success, exception/action failure, pause, denial, resumed variants, or `--only`.
- The named spec, plan, AFTER shapes, and logged rulings were read and applied; no finding re-litigates those accepted presentation decisions.

### `review-feature-interactions`

These were **static inspections, not executed tests**:

- Non-loop resume × approved/denied/failed has lineage/current-attempt-count coverage (`tests/test_execution/formatters/test_run_outcome.py:383`, `:401`; `tests/test_cli/test_run_outcome_cli.py:396`).
- `--only` × stopped approval gate covers target exclusion from `nodes_skipped` and “did not run” wording (`test_run_outcome.py:447`).
- Batch × continue × all-failed/degraded × `-p` preserves mandatory failed-item details and summary-tier degraded details (`test_run_outcome_cli.py:474`, `:483`).
- Batch × nested failure × CLI/MCP has child-diagnostic integration coverage (`tests/test_integration/test_shell_failure_display.py:555`, `:569`).
- Compile-time failure × identity has finalize-first CLI/MCP coverage (`tests/test_integration/test_cli_mcp_parity.py:532`); non-durable pause normalization is separately covered (`test_run_outcome.py:356`).
- Output precedence remains centralized (`output_utils.py:35`); only successful JSON calls `set_json_output` (`src/pflow/cli/commands/run.py:421`); the UI trailer consumer has an ordering guard (`tests/test_cli/test_run_node.py:599`).
- Spec D1–D4, plan header/§§2–6, ruled AFTER shapes, and deviations were reviewed. Neither finding disputes pause-only gates, warning order, denial’s omitted error block, or token-first paused text (`progress-log.md:791`).

## Coverage

| Lens | Provider | Reported scope and limitations |
|---|---|---|
| `review-simplicity` | codex | Read-only `git diff origin/main...HEAD`; no tests or writes. New outcome/CLI suites read in full; existing large test modules reviewed through changed hunks and relevant surroundings. Not an unqualified full-file completion-gate sign-off. |
| `review-spec-conformance` | codex | Read-only diff at HEAD `3c5a901b`; no tests or writes. Core implementation and new conformance suites read in full; requirement-specific legacy/docs changes and searches reviewed. Full-file reading of every changed legacy test, agent document, and comment-only file was not completed. Generated mirrors, lockfile, excluded captures, and newly appearing untracked `completion-gate.md` were outside review targets. Partial completion-gate review. |
| `review-impact-completeness` | codex | Read-only diff; no tests or writes. Consumer searches covered production, tests, scripts, docs, and agents. Not every changed test/supporting file was read in full. Moderate consumer-map confidence; no exhaustive clearance. |
| `review-silent-failures` | codex | Read-only diff and static tracing; no tests or writes. Full-file reading of every legacy test and ancillary documentation file was not completed. No exhaustive completion-gate clearance. |
| `review-test-fidelity` | codex | Committed diff reviewed; no tests or writes. Ancillary large files inspected through changed hunks and relevant callers rather than every unchanged line. No unqualified full-file sign-off. |
| `review-agent-ux` | codex | Assigned diff slice; read-only, with no tests or workflows executed. Named decision documents read. Runtime confirmation remains the caller’s responsibility. |
| `review-feature-interactions` | codex | Read-only diff and static inspection; no tests or writes. Covered CLI/MCP presentation, resume, gates/loops, `--only`, batch/nested failures, metrics, output routing, and trace finalization. Ancillary agent docs, baseline-harness changes, and migrated tests were not all audited in full. No exhaustive sign-off. |

**Failed-lens gaps supplied:** None (`[]`). All seven supplied lenses produced reviews.

**Execution-evidence limitation:** No supplied lens executed tests or workflows. The spec lens cites previously recorded test/transcript evidence; that is distinct from execution during these reviews. `review-falsifier` was mentioned as a runtime-confirmation handoff, but no output from that lens was supplied, and it was not listed as a failed lens.
