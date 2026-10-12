# Task 184 — show before code: the one Run outcome document (USER CHECKPOINT CP-1)

> Status: **awaiting ruling**. Every BEFORE below was **executed on today's code** (main `05884642`,
> isolated HOME, scratch workflows `ok` / `fail-action` / `fail-exc` (HTTP timeout to a black-hole
> address) / `gate` (three shell steps, the third `approval: required`) / `gate-fail` (same, third exits 1)).
> AFTER is what the plan builds. Rule once, the plan's §3 "Document shape" and §4 "Renderers" are the
> binding text; this file is the evidence they were shown first.

## The one rule

> **A run ends once. One function turns the `ExecutionResult` into one document; `status` is a field,
> not a different document.** Everything a run has regardless of how it ended is always there —
> `execution_id` + `trace_path` (when the trace streamed to disk), `workflow`, `success`, `status`,
> `execution` (the step table, `nodes_executed` = steps completed in THIS attempt, lineage when resumed),
> `duration_ms` / `total_cost_usd` / `metrics` (when the run got far enough to have a collector),
> `warnings`, `advisories`, `diagnostics`, `errors`. By status only: `result`, `error`, `gate`,
> `resume_command`. A key the run has no value for is **absent, never `null`** — that rule binds the document's own
> optional keys; values that mean something by `null` keep it (`total_cost_usd: null` is "cost unknown / subscription-billed",
> a `?? null` output is `null`, the gate payload's `question`/`recommendation`/`iteration` are the canonical `GateRequest`).

## Key × status matrix (AFTER)

| Key | success / degraded | failed | paused | denied | Source |
|---|---|---|---|---|---|
| `success`, `status`, `workflow` | ✓ | ✓ | ✓ | ✓ | result / caller metadata |
| `execution_id`, `trace_path` | ✓ when streamed | ✓ when streamed | ✓ (always streamed — a pause needs the disk) | ✓ when streamed | `result.trace.trace_path` ≠ None (so `--no-trace` and a mid-run stream fault → both absent) |
| `execution` {`duration_ms`, `nodes_executed`, `nodes_total`, `steps`, `cache_hits`?, `only_node`+`nodes_skipped`?, `resumed_from`+`nodes_restored`+`resume_entry_node`+`resume_entry_iteration`?} | ✓ | ✓ | ✓ | ✓ | `build_execution_steps` + `__execution__` — one source for text and JSON |
| `duration_ms`, `total_cost_usd` (+ pricing tri-state keys), `metrics` | ✓ | ✓ **(new on exception failures)** | ✓ (new) | ✓ (new) | the metrics collector — now carried on the exception return path too |
| `warnings`, `advisories`, `diagnostics` | ✓ | ✓ (new: `warnings`/`advisories` split) | ✓ (new split) | ✓ (new split) | surfaced diagnostics (WARNING + INFO), split by severity; `diagnostics` = all of them + `errors` |
| `errors` (list) | `[]` | ✓ | `[]` (a pause carries no error) | ✓ (the gate diagnostic) | `result.errors`, printed form |
| `error` (summary string) | — | ✓ | — | ✓ | first error's message / "N errors" |
| `result` | ✓ outputs | only the partial resolved outputs of an output-resolution failure (#754) | — | — | unchanged rules |
| `gate` | — | — | ✓ | ✓ | the masked `GateRequest` dict (same shape both; `node_id` inside) |
| `resume_command` | — | ✓ when resumable (`has_resumable_step`) | ✓ the answer command | — | one rule in the builder |
| **dropped** | top-level `nodes_executed` (attempted count), `metrics.workflow.nodes_executed` (= `len(node_timings)`, derivable) | | `paused_node_id` (= `gate.node_id`), `gate_request` → `gate` | | D2 ruled; no consumer reads either (verified: 4 success-run tests + one docs example) |

## 1. Success — CLI JSON

BEFORE (executed; keys): `success, result, status, workflow, warnings, advisories, diagnostics, duration_ms, total_cost_usd, nodes_executed, metrics, execution` — **no `execution_id`, no `trace_path`** (#695).

AFTER:
```json
{
  "success": true,
  "status": "success",
  "workflow": {"action": "unsaved", "name": "…/ok.pflow.md"},
  "execution_id": "4877c802-b764-4909-a3db-4ddfa2456e70",
  "trace_path": "/…/.pflow/debug/workflow-trace-4cc2313f-ok-20261011-184803-581191.json",
  "result": {"verdict": "two-value"},
  "errors": [],
  "warnings": [],
  "advisories": [],
  "diagnostics": [],
  "duration_ms": 16.43,
  "total_cost_usd": 0.0,
  "metrics": {"workflow": {"duration_ms": 15.76, "cost_usd": 0.0, "tokens_input": 0, "tokens_output": 0, "tokens_total": 0, "models_used": [], "node_timings": {"one": 4.2, "two": 3.7}}, "total": {"…unchanged…"}},
  "execution": {"duration_ms": 16.43, "nodes_executed": 2, "nodes_total": 2, "steps": ["…unchanged…"]}
}
```
Delta: `+execution_id +trace_path +errors:[]`, `-nodes_executed` (top level), `-metrics.workflow.nodes_executed`.
Text mode and `-p` unchanged (the trace line stays in the stderr summary; `-p` still prints only the data).

## 2. Failure by exception (HTTP timeout) — CLI JSON + text

BEFORE (executed): keys `success, status, error, errors, diagnostics, workflow, execution, execution_id, resume_command`. **No `metrics`/`duration_ms`/`total_cost_usd`**, `execution.duration_ms: null`, every step `duration_ms: 0`; **no `warnings`/`advisories`**. Text: no `❌ Workflow failed after Xs` line (#699).

AFTER:
```json
{
  "success": false,
  "status": "failed",
  "workflow": {"action": "unsaved", "name": "…/fail-exc.pflow.md"},
  "execution_id": "cb334f9d-…",
  "trace_path": "/…/workflow-trace-1c400127-fail-exc-….json",
  "error": "Request to http://10.255.255.1:9/ timed out after 1 seconds. …",
  "errors": [{"severity": "error", "message": "…", "source": "runtime", "title": "Execution Failed", "node_id": "slow-fetch", "context": {"category": "execution_failure"}}],
  "warnings": [],
  "advisories": [],
  "diagnostics": ["…same objects as errors…"],
  "duration_ms": 1021.7,
  "total_cost_usd": 0.0,
  "metrics": {"workflow": {"duration_ms": 1020.9, "cost_usd": 0.0, "…", "node_timings": {"one": 4.1, "slow-fetch": 1004.2}}, "total": {"…"}},
  "execution": {"duration_ms": 1021.7, "nodes_executed": 1, "nodes_total": 2, "steps": [{"node_id": "one", "status": "completed", "duration_ms": 4.1, "cached": false}, {"node_id": "slow-fetch", "status": "failed", "duration_ms": 1004.2, "cached": false}]},
  "resume_command": "pflow resume cb334f9d-…"
}
```
Text (stderr) BEFORE → AFTER:
```
  one... ✓ 0.0s                              one... ✓ 0.0s
  slow-fetch... ✗ Failed                     slow-fetch... ✗ Failed
                                             ❌ Workflow failed after 1.022s        ← new
Error: Execution Failed                      Error: Execution Failed
Request to … timed out …                     Request to … timed out …
  At: node 'slow-fetch'                        At: node 'slow-fetch'
Workflow trace saved: …                      Workflow trace saved: …
To resume from the failed step: pflow resume … To resume from the failed step: pflow resume …
```
The action failure (shell `exit 1`) looks the same AFTER, except `nodes_executed` no longer appears twice with two values (BEFORE: top-level `2`, `execution.nodes_executed` `1`).

## 3. Paused — CLI JSON + text

BEFORE (executed): `{success:false, status:"paused", execution_id, paused_node_id, gate_request:{…}, resume_command, errors:[], diagnostics:[]}`. No `trace_path`, no `workflow`, no `execution`, no metrics, no `warnings`/`advisories`.

AFTER:
```json
{
  "success": false,
  "status": "paused",
  "workflow": {"action": "unsaved", "name": "…/gate.pflow.md"},
  "execution_id": "4877c802-…",
  "trace_path": "/…/workflow-trace-5a0f13ff-gate-….json",
  "errors": [],
  "warnings": [],
  "advisories": [],
  "diagnostics": [],
  "duration_ms": 9.8,
  "total_cost_usd": 0.0,
  "metrics": {"…"},
  "execution": {"duration_ms": 9.8, "nodes_executed": 2, "nodes_total": 3, "steps": [{"node_id": "one", "status": "completed", …}, {"node_id": "two", "status": "completed", …}, {"node_id": "three", "status": "not_executed", …}]},
  "gate": {"node_id": "three", "node_type": "ShellNode", "kind": "action_approval", "preview": {"command": "echo \"three-value\""}, "question": null, "options": [], "recommendation": null, "iteration": null, "max_iterations": null},
  "resume_command": "pflow resume 4877c802-… --approve yes|no"
}
```
Delta: `gate_request` → **`gate`** (the denied document already uses `gate` for the same dict), `paused_node_id` folded into `gate.node_id`; `+trace_path +workflow +execution +metrics +warnings +advisories`.
Text unchanged: `Paused at 'three'. Resume token: <id> (exit 4)` on stdout; gate lines, warnings/advisories, `To answer: …` on stderr.

## 4. Denied (after a resume) — CLI JSON + text

BEFORE (executed): `{success:false, status:"denied", error, errors:[gate diag], diagnostics, gate}` — no identity, no `execution`, no lineage. Text: `✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)` — reads as "nothing ran" (#737).

AFTER:
```json
{
  "success": false,
  "status": "denied",
  "workflow": {"action": "unsaved", "name": "gate"},
  "execution_id": "9c0e…",
  "trace_path": "/…/workflow-trace-5a0f13ff-gate-….json",
  "error": "Denied at gate 'three'.",
  "errors": [{"severity": "error", "message": "Denied at gate 'three'.", "title": "Gate denied", "node_id": "three", "source": "runtime", "context": {"category": "gate", "gate": {"…"}}}],
  "warnings": [], "advisories": [], "diagnostics": ["…the same gate diagnostic…"],
  "duration_ms": 3.1, "total_cost_usd": 0.0, "metrics": {"…"},
  "execution": {"duration_ms": 3.1, "nodes_executed": 0, "nodes_total": 3, "steps": [{"node_id": "one", "status": "not_executed", …}, {"node_id": "two", "status": "not_executed", …}, {"node_id": "three", "status": "not_executed", …}], "resumed_from": "b86616ed-…", "nodes_restored": 2, "resume_entry_node": "three", "resume_entry_iteration": 1},
  "gate": {"node_id": "three", "…"}
}
```
Text AFTER:
```
✗ Denied at gate 'three'. Workflow stopped cleanly before the step ran. Steps completed: 0 of 3. (exit 3)
  ⤷ Resumed from b86616ed-… at 'three' — 2 upstream steps restored        ← new
```
The count stays "this attempt's completed steps" (engine rule: restored steps are not executed); the lineage line beneath is what makes `0 of 3` truthful. A fresh (non-resumed) denial reads `Steps completed: 2 of 3.` as today. A denial renders no gate preview, no `To answer:` and no "approve every remaining iteration" hint — a human's no is final (today's behaviour, now stated as the rule).

## 5. Failed after a resume — CLI JSON + text

BEFORE (executed): JSON has `execution.nodes_executed: 0`, steps one/two `not_executed`, **no `resumed_from`/`nodes_restored`** (contradicts `guide/features/resume.md:21`); text has the `❌` line but **no `⤷ Resumed from` line**.

AFTER: `execution` gains `resumed_from`, `nodes_restored: 2`, `resume_entry_node: "three"`, `resume_entry_iteration: 1` (the same block the success document already carries); text gains `  ⤷ Resumed from <id> at 'three' — 2 upstream steps restored` right under the `❌` line.

## 6. MCP `workflow_execute` text — rendered from the same document

BEFORE (executed) — three bespoke texts:
```
# success                                    # failure (raised RuntimeError)           # paused
✓ Workflow completed in 0.022s               Error: Execution Failed                   ⏸ Workflow paused at 'three' — a human decision is required.
                                             Command failed with exit code 1: boom
Workflow output:                               At: node 'two'                          status: paused
                                               Shell details: …                        execution_id: 7fd14e02-…
two-value                                                                              paused_node_id: three
                                             Trace: /…/workflow-trace-….json           trace_path: /…/workflow-trace-….json
execution_id: 12ff8aa0-…                                                               resume_command: pflow resume 7fd14e02-… --approve yes|no
trace_path: /…/workflow-trace-….json
                                                                                       Gate:
                                                                                         command:  echo "three-value"
```
Failure has no metrics/cost and no `execution_id:`; paused drops the run's warnings.

AFTER — one renderer, one layout for every status: completion line → mode lines (`⤷ Ran only…` / `⤷ Resumed from…`) → batch / shell-stderr blocks → cost → errors (every error; no "first 3" cap) → `Outputs that resolved before the failure:` (when any) → `Warnings:` / `Advisories:` → `Workflow output:` (success) → `Gate:` block (paused/denied) → identity block.
```
# failure (raised RuntimeError)                        # paused
❌ Workflow failed after 0.019s                        ⏸ Workflow paused at 'three' — a human decision is required.

Error: Execution Failed                                Warnings:                       ← new (was dropped)
Command failed with exit code 1: boom                  <warning text>
  At: node 'two'
  Shell details: …                                     Gate:
                                                         command:  echo "three-value"
status: failed
execution_id: 32547276-…                               status: paused
trace_path: /…/workflow-trace-….json                   execution_id: 7fd14e02-…
resume_command: pflow resume 32547276-…                trace_path: /…/workflow-trace-….json
                                                       resume_command: pflow resume 7fd14e02-… --approve yes|no
```
Success keeps its text (`{name} was executed` line, `Workflow output:`), gaining only `status: success` in the identity block. The `paused_node_id:` line goes — the header `⏸ Workflow paused at 'three' — …` names the step on every pause (that header is now the PAUSED completion line, so it cannot be dropped by a layout change) and the JSON has `gate.node_id`. A cost line appears on failure when LLM calls ran. A failure raised before any step ran (a missing required input is caught at compile time) still shows `execution_id:`/`trace_path:` on BOTH channels — the CLI finalizes the trace before building the document, as MCP already does.

## Questions that need your ruling (each has a recommendation)

- **Q1 — `-p` on non-success statuses.** Today `-p` hides the stderr summary on success but on a failure
  still prints warnings/advisories (and on a pause the warnings). Proposed: one rule for every status —
  `-p` hides the *summary tier* (completion line, cost, shell-stderr block, warnings/advisories, trace
  line) and always prints the *must-act tier* (the error block, a FAILED run's batch item errors, the gate
  block + `To answer:` on a pause, `To resume…`, the `⤷` mode lines, the denied line). **Recommendation: the
  one rule** (it is what "-p = minimal stderr" means; a `-p` agent that wants warnings reads them from
  `--output-format json`; a failed batch's item diagnoses stay visible because they are the error).
  Alternative: keep today's per-status exceptions (more code, same contract as now).
- **Q2 — MCP text identity block on every status** (`status:` / `execution_id:` / `trace_path:` /
  `resume_command:` at the end), dropping the paused `paused_node_id:` line and the failure text's
  "first 3 errors" cap. **Recommendation: yes** — one greppable block for every ending; an agent fixing a
  workflow needs every error, not three. Alternative: keep paused's current key order and the cap.
- **Q3 — `errors` is always a list** (empty on success and on a pause), while `error` (the summary
  string) appears only when there are errors. The spec wrote "`errors` + `error` (failed)"; the paused
  document already ships `errors: []` on purpose so agents branching on `success == false` can iterate it.
  **Recommendation: always a list** — the D1 spirit (one shape) and the existing paused contract.
- **Q4 — stderr trace line moves into the summary for every status** (one emission site, rendered from the
  document's `trace_path`), which in `--output-format json` mode prints it *before* the JSON payload
  instead of after. Streams are unaffected; only the terminal interleaving changes. **Recommendation:
  yes** (one site; `-p` suppresses it as today). Alternative: keep the `finally`-block echo for non-text-
  success paths (two sites, as today).

Out of scope by ruling and left as is: the trace trailer's own `nodes_executed` (counts attempted
top-level visits; the web UI reads it — the spec scopes D2 to the document), `--dry-run`'s plan document
(a plan has no run, so no run identity exists to add), the `registry_run` probe's error text (#748).
