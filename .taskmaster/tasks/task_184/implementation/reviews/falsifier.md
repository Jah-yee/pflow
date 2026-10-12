# review-falsifier — Task 184 completion gate (run on HEAD 3c5a901b + G1's uncommitted fixes, 2026-10-12)

Verbatim report relayed by the task orchestrator. Probe files: session scratchpad `fz/` (not in repo).

Verdict: no Critical. 18 of 19 promises HELD on the real CLI/MCP paths (common keys, absent-never-null with producer nulls
surviving, errors-list, identity iff trailer incl. ENOSPC/read-only faults and 5 parallel runs, compile-time identity on both
channels, #699 metrics + ❌ line, one nodes_executed, lineage on every resumed ending, -p JSON invariance, one trace line, tiers,
gate PAUSED-only, paused token first, exit codes + success⇔exit 0, CLI↔MCP parity, piped stdin, warm cache, --report/-o/saved).

## Warning (BROKEN edge promise, NOT a regression — origin/main identical)
A gate inside a sub-workflow child is recorded as a `completed` step on the failed run.
Repro: parent `prep` → step `call` (`./gchild.pflow.md`, whose only step `inner` has `approval: required`), non-TTY,
`--output-format json` → exit 1, status failed, error "Step 'inner' requires a human approval decision…", but
`execution.steps`: prep completed, call completed (duration_ms 0), nodes_executed 2; text progress shows `call...` with no ✗.
Cause (falsifier's read): `_execution_block` (`run_outcome.py:166-170`) relabels only `gate.node_id` and only for paused/denied;
this is a non-durable gate under FAILED naming the child's `inner`, not `call`. Contrast: child failing by exception → `call`
failed; parallel-batch child gate → `each` not_executed.

## Observations (not promises of this task)
- Pre-run CLI error documents (file not found, piped input unroutable, newer attempt exists) carry only
  {success,status,error,errors,diagnostics,workflow} — no warnings/advisories (plan §3.5 scopes them out).
- Non-durable gate after a trace write fault: fallback text lists --no-trace/inline/--only/unsupported position as cause —
  none applies (main identical).
- Resuming a saved workflow reports `workflow.action: "unsaved"` (fresh named run says `reused`); resume.py metadata untouched
  by this branch; main not checked.

## Not attacked
Escalation pause (`--choose`, needs agent node), paid-LLM `total_cost_usd: null` tri-state, tests-windows, web UI, a non-write
exception raised out of `finalize()` itself (G1 logged as pre-existing/assumed).
