# Task 183 — progress log

Append-only. Entry format: ORCHESTRATION.md → "Progress-log entry format".

## [2026-10-06 23:40] task-planner (Opus, user capacity ruling) — planning complete, plan under self-review
- Did: investigated the gate/loop-cap/trace/pause-surface/bridge seams (core/gate.py, runtime/engine/gate.py,
  loop_control.py, execution/gate_prompt.py, GateCallout.tsx read directly; four parallel searchers for trace
  side, cap semantics, pause renderers, web+server), executed the BEFORE pause surfaces, wrote
  `implementation-plan.md` + `pause-surfaces-before-after.md`, corrected the spec in place.
- Changed: `task-183.md` (gate_prompt path is `execution/`, not `core/`; the gate pause line's payload key is
  `request`; "cap written at loop entry" → the gate derives it, with the NaN/inf coercion gap stated; the
  `/api/resume` 400s also cover "no answer" and are server-stricter than the CLI; the server pre-flight closure
  discards the `ResumePreflight` it needs), `implementation/implementation-plan.md`, `implementation/pause-surfaces-before-after.md`.
- Verified: base `706b292c` == `origin/main` at launch (`origin/main` later moved to `ebf7cab2`, docs-only for
  Tasks 181/112 — not this task's surface); `make install` ok. BEFORE surfaces EXECUTED via
  `scratchpads/task-183/capture.sh before2` (gitignored; isolated HOME). `pflow resume <tok> --approve yes
  --auto-approve gated` on the paused step finishes the loop (3 effects) — the mapping `/api/resume` will spawn
  already works in the CLI. Task-159 `verify.sh` on the base: **75 pass / 12 drift / 0 errors** — drifted:
  02-validator-errors/{03-prompt-cache-on-shell-node, 05-subworkflow-references-parent-chunk};
  03-analyze-cache-modes/{05-trace-from-trace, 06-no-trace-autoload, 07-autoload-prefers-success,
  08-autoload-failed-only, 09-autoload-rejected-names-file}; 04-warning-catalog/{03-cache.invalid-on-non-llm,
  09d-cache.prewarm-disabled-below-min, 09e-cache.conditional-warmup-recommended};
  10-live-recordings/03-gemini-translation; 12-real-world-lyrics-generator/04-guide-auto-detect. P5 compares
  against THIS set.
- Deviations/surprises: (1) the orchestrator's framing "cap written at loop entry" is replaced by derive-at-gate
  (plan D1 — no walk state, works at iteration 1 and on resume); (2) the latent NaN/inf crash in
  `_coerce_runtime_cap` would reach the gate through the new call — closed in-task (D2); (3) Deny + Approve +
  "Approve all remaining" do not fit the callout's ~296px row (fixed 320px in flow units, any window size) —
  the layout is a real design call for the Fable phase; (4) existing loop-text tests assert substrings that
  still pass after the change — new tests must pin full lines; (5) `src/pflow/ui/CLAUDE.md` has no
  `/api/resume` contract section — the contract lives in `server.py` docstrings.
- Self-checks: plan-mode deep-review launched (mandatory: engine + trace).
- Next: fold review findings, commit, hand back.

## [2026-10-07 00:45] task-planner (Opus) — plan self-review (plan-mode deep-review, MANDATORY: engine + trace)
- Did: 7 direct lenses (fan-out is code-mode only): review-plan, architecture-fit, silent-failures,
  impact-completeness, feature-interactions, test-fidelity, agent-ux. 0 Critical. Plan rewritten with every
  confirmed fix; spec corrected twice more.
- Changed: `implementation-plan.md` (rewrite), `pause-surfaces-before-after.md` (past-cap row, R1 PROPOSED line,
  null wording), `task-183.md` (null-not-absent for the new field — was "absent" — and the renderer-guard sentence).
- Verified: branch fast-forwarded `706b292c` → `2464e43c` (#719/#690 landed mid-planning; review-plan W4); every
  `resume_source.py`/`exceptions.py`/`server.py` cite re-checked on it (PausedRun now `:1026`, `list_paused_runs`
  `:1098`, answer-required `:1530/1582/1601`); Task-159 `verify.sh` on `2464e43c`: 75 pass / 12 drift, the SAME
  12 cases as on `706b292c` (list in the entry above). `parse(t).references` roots checked by execution for `??`,
  dynamic-index and `__iteration__` templates.
- Dispositions (all Confirmed unless noted):
  - silent-failures **W1 (executed repro)**: `??` makes store-key hiding resolve to the fallback (shows 2, engine
    uses 5) → D1 now decides "unknown" from `parse(template).references` roots; P1-6 gains `??` cases.
    W2 (flat `--auto-approve` reaches same-named child gates) → tooltip/guide state the true scope (D9/D10).
    S1 unknown body keys → 400 (D7). S2 both `GateRequest(...)` branches per builder pass the field (D3, P1-2).
  - feature-interactions W1 / agent-ux S3: per-run counter past the cap on a back edge or lowered-cap resume →
    `loop_position` drops the clause when `iteration > cap` (D4, `past-cap` row, P1-8, P2-6). Scenario B
    (back edge re-runs an upstream cap source) documented, not engineered. S1 tooltip scope → D9.
  - architecture-fit W1 / agent-ux W1 / review-plan W2: spec said "absent", plan/`asdict` say `null` → spec fixed.
    S1 ADR-0009/0010 one-line amendments → D10, proposed for the main orchestrator to confirm. S2 Task 180 spec
    line → hand-back (outside this worktree).
  - impact-completeness W1/W2 + test-fidelity W2/S2 + review-plan W1: MCP `:349`, `GateCallout.test.tsx:100` and
    GraphView's loop-chain test WILL fail (span + trailing `\n`) → §2.3 corrected; exact `textContent` re-pins;
    GraphView.test.tsx added to P4. W3 ADR-0009 body + `resume` docstring `Body:` line → D7/D10. Suggestions
    (cli/index.mdx:135, client.ts JSDoc, fixture mirrors the wire, TS twin beside `optionLabel`) → folded.
  - test-fidelity W1 `/api/gate` untested → P3-7. S1 tighten existing tests in place; P3 end-to-end dropped
    (`test_paused_cli.py:477` already pins the CLI half). S3 P1-6 asserts at iteration 2 / post-exec. S4 echo
    asserted at iteration 2. S5 subscripts. S6 row count + ids.
  - agent-ux S1 (CLI/MCP bulk hint) → **user ruling R1** (not in spec; recommend yes). review-plan W3
    (bulk action on unknown-cap loops = the spec's "count they cannot see") → **user ruling R2** (recommend (a)).
    S2 (`GateNotInteractiveError` scope wording) → sibling gap. S4 → D10 guide sentence. S5 → D7 messages.
  - review-plan S1 (literal-only cap) → Disputed: the reference check is 3 lines and keeps the documented
    `${template}` cap (`loop.md:96`); recorded as option (d) in D1. S2 test-module location → D8/P1. S3 → D7.
- Self-checks: fully happy with the plan as revised; residual unknowns are the two user rulings (R1, R2) and the
  P4 layout, which the embedded checkpoint covers.
- Next: commit plan + spec + log on the feature branch; hand back (R1, R2, Fable word for P4, ADR one-liners,
  Task 180 spec line).
