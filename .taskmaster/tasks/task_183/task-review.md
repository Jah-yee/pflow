# Task 183 Review: Approval Gates in Loops — "Iteration N of up to M" and "Approve All Remaining"

## Metadata
- Implemented 2026-10-10 → 2026-10-11 on `feat/task-183-loop-gate-approve-all` (main `f0b39c5c` merged in). Planner: Opus (user capacity ruling). Orchestrator: Opus.
  - Implementer A (Opus) built P1–P3, then ran the completion gate.
  - Implementer B (Opus, on the user's per-launch word instead of Fable) built P4 and the `/api/gate` node-type fold.
- Closes #656. Trace format **2.9.0 → 2.10.0** (additive; Task 180 took 2.9.0 first).
- Follow-ups filed: **#763** (two concurrent resumes of one token both run; bulk approve multiplies the duplicated side effects) and **#762** (screenshot skill: window size, wait-for, reusable control measurement).
- ADR-0009/0010 one-line amendments (`auto_approve?`, `max_iterations`) were written on `main` by the main orchestrator, not on this branch.
- Rulings, deviations and every review disposition: `implementation/progress-log.md`. Ruled text: `implementation/pause-surfaces-before-after.md` (CLI/MCP) and `implementation/p4-checkpoint.md` (web, with shot paths). Gate reports: `implementation/reviews/`.

## Read First — the load-bearing block
- **What exists now:** a gate raised by a loop step carries `max_iterations` beside `iteration`. Its value is the author's cap as it can be known at the gate. It is display-only and `null` when unknown.
  - Every pause surface renders `iteration N of up to M` through one Python helper and one TS twin, both pinned to a shared case table.
  - A loop APPROVAL pause also prints a `--auto-approve` hint (CLI, MCP, answer-required error).
  - `POST /api/resume` accepts `auto_approve: true`, which spawns `--approve yes --auto-approve <paused step>`.
  - The web gate panel offers **Approve all remaining** on loop approval gates.
  - `GET /api/gate` serves `node_type` as the display tag (`code`, `shell`, `mcp`).
- **Read these first:**
  - `runtime/engine/loop_control.py::declared_loop_cap`, plus the NaN/inf arm of `_coerce_runtime_cap`.
  - `core/gate.py`: `GateRequest.max_iterations`, `loop_position`.
  - `execution/gate_prompt.py::format_bulk_approve_hint`.
  - `ui/server.py`: `_parse_resume_body`, `_parse_auto_approve`, `_resume_cli_args`, the pre-flight closure in `resume`, the `gate` endpoint's `node_type_tag` projection.
  - `web/src/components/GateCallout.tsx`: `loopPosition`, `shownCap`, `approveAllTitle`.
  - `web/src/test/fixtures/loop-position.json`.
- **Invariants that must NOT break:**
  - **`max_iterations` is display-only.** Only renderers and `list_paused_runs` read it; `should_reenter` stays the one cap decision.
    - The gate's value is a different derivation: `null` for a body-dependent cap the engine still enforces after iteration 1.
    - Reading it on the walk or in resume forks cap decisions. Task 179's "one reader of position" holds the same way.
  - **"Unknown" is decided by the template's REFERENCES, never by hiding store keys.**
    - `declared_loop_cap` returns `None` when any `parse(template).references` root is the loop step itself or `__iteration__`. That set includes `??` operands and dynamic-index inner keys.
    - Key-hiding was the first draft and was broken by execution. `??` falls back to its default when the key is absent, so the gate showed `of up to 2` while the engine ran 5.
  - **`declared_loop_cap` must never raise.** The escalation gate runs post-exec, so any non-`LoopConditionError` escaping there reaches the node's generic except arm and writes a second error record. `_coerce_runtime_cap` now refuses NaN/±inf with `LoopConditionError` (before, a bare `ValueError`/`OverflowError`), and `declared_loop_cap` catches only that.
  - **Never print "iteration 4 of up to 3."**
    - `loop_position` (and the TS `shownCap`) drop the clause when `iteration > max_iterations`.
    - This happens because a back edge into a loop step continues the per-run count, and because a resume can lower a templated cap.
    - The web tooltip shares `shownCap`, so it never says "at most 3" beside iteration 4.
  - **The Python and TS renderers are pinned to ONE case table** (`loop-position.json`, 6 rows). Both tests assert the row count and the id set, so a truncated file fails. Change the rule → change the fixture → both suites move together.
  - **`null`, not absent, on every new payload.** Records written before 2.10.0 lack the key, and every reader treats absent as `null`. Tests assert by subscript (`d["max_iterations"] is None`). `.get()` passes on pre-change code.
  - **The trace's `node_type` is the class name; display surfaces map it.** `/api/gate` projects via `node_type_tag`, the same render-seam pattern as `ui/run_node.py`.
    - Readers dispatch on the class name (`core/trace_tree.py`, `node_type_display.is_model_node_type`).
    - Do not "fix" the engine to put the IR type in the payload: `NodeConfig` has no IR type; `TemplateConfig.node_type` is `None` for an untemplated node; MCP IR types are longer than `MCPNode`.
  - **`auto_approve` is a bool the server resolves to the ONE paused step** (`pf.source.paused_node_id` from pre-flight), never a client-supplied id list. This keeps "approval bypass is per-node" true (ADR-0009 amendment).

## What Was Built (actual vs. planned)
The plan's P1–P4 shipped as written, plus one fold. These deviations carry knowledge:
- **Trace 2.10.0, not 2.9.0** (the plan's D6 conditional; Task 180 merged first). `resume_source._predates_lossy_marker` compares `(int, int)` tuples, so "2.10" orders correctly. No consumer compares versions as strings.
- **Answer-required error shape (ruled).** The R1 hint is a SECOND structured `suggestions` entry. On loop approval pauses only, the renderer therefore shows the house numbered list (`To fix this: 1. Answer with: … 2. To approve this and every remaining iteration…`) instead of `→ Answer with:`. JSON/MCP consumers get the hint as its own entry. To flip it, change one line in `core/exceptions.py`.
- **Hint placement:**
  - MCP puts it directly under `resume_command:`.
  - It is NOT in the `--output-format json` pause document or `resume list`. Those carry `max_iterations` + `paused_node_id`, which is enough to compose it.
- **`/api/resume` refusals are tested against a REAL paused token.** The plan said to extend `test_shape_errors_are_400_before_any_io`. Its bodies use a bogus `run`, which 4xx at pre-flight anyway, so an `autoApprove`/`"true"` row passed with the check deleted (measured). `_parse_resume_body` was split (`_parse_auto_approve`, `_auto_approve_contradiction`) for ruff C901 rather than suppressed.
- **Unknown top-level `/api/resume` keys are now a 400.** This is new strictness for any raw caller: `autoApprove` must not silently become a one-iteration approve.
- **Web design (user ruled keep-as-built):**
  - Layout: `[Deny] [Approve]` keep their row; **Approve all remaining** spans the pair's width on a second row (`.gate-actions-loop` grid). The callout is a fixed 320px in FLOW units, so three buttons never fit one row at any window size.
  - Style: an accent-TINTED fill. Approve stays the only accent fill.
  - Tooltip: states the flat-by-step-NAME scope (sub-workflows included) and the bound.
  - Shown on uncapped loops too (R2 (a)). No confirm dialog.
  - The show rule's `kind === "action_approval"` conjunct was dead (the button lives only in the approval branch) and was deleted. The escalation-absence test is the guard.
- **The `/api/gate` node-type fold.** Live eyebrows read `PythonCodeNode · gated` on `main` too (web tests assumed `code`). The long name wrapped the new clause onto a second line. The main orchestrator ruled a fold. Its proposed engine-side fix rested on a non-existent `NodeConfig.node_type`, so the render-seam projection was built instead (reasoning in the log). The trace, CLI JSON, MCP and the TTY prompt keep the class name.
- **Guide correction from the P1 mid-task review.** An own-output cap shows `null` at the gate, but the engine resolves and enforces it after iteration 1. The guide no longer says such a loop "runs until its condition stops it".
- **Not built:**
  - the concurrent-resume fix (#763; the `resume` docstring now states the race truthfully);
  - the screenshot-skill gaps (#762), except a Troubleshooting note on `navigate_page`'s `type` param.

## Patterns & Anti-Patterns
- **Derive a display value at the producer from compile-time config plus the store it already holds.** Don't thread walk state (`loop_caps`) out to it. That is what makes iteration 1 (the engine has not memoized the cap yet) and a resumed attempt (`loop_caps` is empty) correct without new plumbing.
- **One renderer per language plus a hand-authored shared case table** that both test suites read and count. A 6-row rule does not earn a generator and drift test. Both sides reading one file IS the pin.
- **The server is a thin argv mapper over the CLI verb.**
  - Every server-stricter rule is recorded in `_parse_resume_body`'s docstring as a deliberate asymmetry. The CLI accepts `--auto-approve` beside `--choose`; the server 400s.
  - The step id comes from pre-flight, never from the body.
- **Payload assertions use `toStrictEqual` on `mock.calls[n][0]`.** `toHaveBeenCalledWith` ignores `undefined`-valued keys and cannot prove "no `auto_approve` key".
- **Eyebrow assertions are exact `textContent` on `.gate-eyebrow`.** Testing Library's default matcher reads an element's OWN text nodes, and the position span splits them. A `/iteration/` regex passes on `of up to 3` and voids the no-cap checks.
- **Anti-pattern:** absence probes for the hint on the bare `--auto-approve`. The run-start warning already prints `--auto-approve=gated`, so probe the hint's full `--approve yes --auto-approve <step>` pair, beside a presence assertion in the same output.

## Gotchas & Non-Obvious Coupling
- **The shown cap can differ from the enforced one in three accepted, display-only cases:**
  - A back edge that re-runs an upstream step the cap template reads. Executed: shows `of up to 5` on what is actually the final iteration.
  - `--only`, which runs one iteration while a TTY prompt reads `of up to 3`.
  - Own-output caps: the gate shows no clause, but the engine enforces the cap from iteration 1's output.
  - All three are recorded in `declared_loop_cap`'s docstring and plan D1.
- **Concurrent resumes of one token both run (#763, pre-existing).**
  - `_find_consuming_attempt` sees a newer attempt only once its trace exists. A sequential second answer is refused.
  - With `auto_approve`, the duplicate re-runs EVERY remaining iteration (falsifier: 6 effects for a 3-iteration loop, via two CLI resumes or two POSTs).
  - In a single tab the answer buttons are `disabled` while submitting; the race needs two tabs or agents, or a raw caller.
- **`--auto-approve` matches by step NAME, flat across sub-workflows and later visits.** So "Approve all remaining" also pre-approves a same-named child gate. The tooltip and `approval.md` say so. `GateNotInteractiveError`'s "pre-approve ONLY this gate" suggestion still under-states this for a loop step (sibling gap, not fixed).
- **A templated cap on resume depends on seeding.** If `${prep.result}` stopped being restored, `should_reenter` fails first with `LoopConditionError`. The P1-7 pin specifically guards a gate-side store mismatch, which a literal cap can never show.
- **A fresh worktree has no `web/node_modules`.** `npx vitest`/`tsc` fail with module-not-found until `cd web && npm ci`.
- **Task-159 baseline:** this task adds no drift. Its set, measured before the last main merge, was byte-identical to the base's 11 cases. After #759, `12-real-world-lyrics-generator/04-guide-auto-detect` drifts on #759's shell-timeout guide text (commented on #680).

## Integration Points
- **Trace 2.10.0:** `max_iterations` inside the gate payload, both on the gate pause line's `request` and in the trailer's `gate_request`. It is not mirrored to the gate line's top level; that key exists only for the resume reader's per-iteration fold.
- **CLI/agent contract:**
  - `resume list --output-format json` rows gain `max_iterations` right after `iteration`.
  - The `--output-format json` pause document's `gate_request` and the answer-required `context.gate` carry it.
  - The answer-required `suggestions` gain a second entry on loop approval pauses.
- **`PausedRun.max_iterations`**, int-guarded like `iteration`.
- **Web bridge:**
  - `POST /api/resume` body `{run, approve?, choose?, force?, auto_approve?}`; unknown keys → 400.
  - `auto_approve: true` requires `approve: "yes"`. On a paused escalation it hits the existing 409 `answer_required`. On a non-loop approval it is accepted (CLI parity; "loop gates only" is a UI rule).
  - `GET /api/gate` `node_type` is a display tag.
  - TS: `GateRequest.max_iterations?`, `ResumeAnswerPayload.auto_approve?`, `resumeRun` JSDoc body rule.
- **`_coerce_runtime_cap`** NaN/inf → `LoopConditionError` now also reaches `should_reenter` and the dry-run planner, which already catches it.

## Tests That Matter
Each was mutation-verified by the implementers (counted failures in the log).
- `tests/test_runtime/test_gate_trace.py::TestGateLoopCap`:
  - iteration-1 literal cap on the line AND the trailer;
  - escalation with dict and string markers;
  - uncapped `null`;
  - input template;
  - own-output at iteration 2's approval and at the post-exec escalation (an iteration-1 approval would pass by accident);
  - `??` over own output, asserted at all 5 pauses with effects = 5;
  - `??` over `__iteration__`.
- `test_gate_pause.py`:
  - `test_loop_approval_after_first_iteration_pauses_with_position`: a SEEDED upstream template cap across three attempts.
  - `test_back_edge_past_the_cap_carries_the_cap_beside_the_continuing_count` (4, 3).
- `test_loop_control.py`: the `declared_loop_cap` reference/unresolvable tables and `test_runtime_cap_non_finite_float_raises_structured`.
- `test_paused_cli.py`:
  - `test_loop_gate_position_reaches_every_pause_surface` (JSON, the whole `resume list` cell, the answer-required line plus hint plus `context.gate`);
  - `test_old_record_without_the_cap_renders_the_bare_iteration` (key stripped from a REAL trailer);
  - `test_uncapped_loop_gate_shows_the_bare_iteration`;
  - `test_back_edge_past_the_cap_drops_the_cap_clause`;
  - the auto-approve chain's iteration-2 echo (`2 of up to 3`, so a renderer printing `of up to {iteration}` fails).
- `test_gate_prompt.py`: `test_loop_position_follows_the_shared_case_table` and `test_bulk_approve_hint_only_for_a_loop_approval`.
- `test_ui_interaction_server.py`:
  - the `test_auto_approve_*` family (exact argv; a 400 before any spawn on a real paused token; `force` plus both flags; non-loop accepted; escalation 409);
  - `/api/gate` `max_iterations` and `node_type == "code"`/`"shell"` on real paused traces.
- Web: `GateCallout.test.tsx` (exact eyebrow per case; the bulk button's presence matrix; the exact click payload with every button disabled in flight; plain Approve carries no `auto_approve` key; the ack retry keeps `auto_approve` + `force`; the case table; the CSS row pin) and the `GraphView.test.tsx` loop chain (exact second-iteration eyebrow across two pauses).

## Breaking changes (agent/raw-caller facing)
- `POST /api/resume` now rejects unknown top-level keys (400 naming them and the expected set).
- `GET /api/gate`'s `gate_request.node_type` is the display tag, not the class name. The web panel is the only in-repo consumer.

---
*Distilled from the implementation context of Task 183. The chronological journey lives in `implementation/progress-log.md` — this review is the durable forward-reference, not a re-narration of it.*
