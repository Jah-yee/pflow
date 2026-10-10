# Task 183 — Implementation Plan: loop gates show "iteration N of up to M"; the web panel offers "Approve all remaining"

Planner: Opus (user capacity ruling for this launch; protocol unchanged). Base: `2464e43c` (`origin/main` after
#719/#690 landed; the branch was fast-forwarded from `706b292c` during planning — citations below re-verified on
`2464e43c`). Spec: `../task-183.md` (corrected in place by this planner — provenance in the progress log).
Show-before-code artifact: `pause-surfaces-before-after.md` (this folder; BEFORE executed). Self-review: plan-mode
`deep-review`, 7 lenses, dispositions in the progress log.

**User rulings — RULED 2026-10-07** (user: *"yes go ahead with this but use opus instead of fable"*): **R1 = yes** (build the
bulk hint line) · **R2 = (a)** · **P4 tier = Opus** (user's per-launch word; still the specialist `task-phase-implementer`
hand-off with the plan's look/feel bounds and `screenshot-pflow-web-ui` verification). Original text kept below for provenance:
- **R1 — CLI/MCP bulk hint** (agent-ux S1): add one line to the pause output of a LOOP APPROVAL gate naming
  `--approve yes --auto-approve <step>`? Not in the spec. Planner recommends **yes** (see §6). Default: not built.
- **R2 — "Approve all remaining" when the cap is unknown** (`max_iterations: null` on a loop gate — uncapped, or
  a cap the gate can't know). Options: (a) show it, tooltip names the bound ("until the loop's condition stops it");
  (b) hide it; (c) show it with no special copy. Planner recommends **(a)**. Default: (a); the P4 checkpoint
  shows it so the user can still flip it.

## 1. The mechanism in one paragraph

`GateRequest` (ADR-0009 payload, `core/gate.py`) gains one display-only field, `max_iterations: int | None`,
beside Task 179's `iteration`. The engine's gate builders (`runtime/engine/gate.py`) fill it from a new pure
function `loop_control.declared_loop_cap(config, shared)`: the step's literal cap; or its `${template}` cap
resolved against the store — unless the template REFERENCES the loop step's own output or `${__iteration__}`;
else `None` ("unknown" / no author cap — the engine's 100-visit guard is never shown). Nothing is threaded out of
the walk; `loop_caps` is untouched. Because `GateRequest.to_dict()` is what the trace writes (the gate pause
line's `request`, the trailer's `gate_request`), the field reaches every dict surface with no plumbing: CLI JSON,
`/api/gate`, the answer-required diagnostic. Text goes through ONE Python helper,
`core/gate.py::loop_position(iteration, max_iterations) -> str | None` (`"iteration 2 of up to 3"` /
`"iteration 2"` / `None`; the clause is dropped when `iteration > max_iterations`), called by the three Python
renderers; the web eyebrow uses a TS twin; both are pinned against one shared case table. Trace format 2.8.0 →
**2.9.0** (additive). Separately, `POST /api/resume` gains `auto_approve: bool` → argv `--approve yes
--auto-approve <paused step>`, and the gate panel shows **Approve all remaining** on loop approval gates.

## 2. Investigation record (verified; searcher citations spot-checked by the planner)

### 2.1 Where the cap lives and why the gate derives it (engine contact)
- `GateRequest.iteration` is set from `shared.get("__iteration__")` at `runtime/engine/gate.py:88-90` (approval,
  pre-exec, called `engine.py:1351-1357`) and `:162-164` (escalation, post-exec, called `engine.py:1563-1564`,
  before `should_reenter`). Both receive the ROOT store (the namespaced proxy is built later, `engine.py:1395`).
  — read directly.
- `loop_caps` is a local of `run()` (`engine.py:935-936`), memoized lazily in `should_reenter`
  (`loop_control.py:273-276`) after iteration 1; empty on resume. `_execute_node` has no access to it. — read.
- `LoopConfig` (`runtime/engine/types.py:47-53`): `max_iterations: int | None` (literal, compile-validated
  `1..MAX_NODE_VISITS`, `compiler.py:433-439, 507-560`) XOR `max_iterations_template: str | None`.
  `resolve_loop_cap` (`loop_control.py:165-180`) returns the literal, resolves the template via
  `TemplateResolver.resolve_template` (never raises; an absent reference returns the template text, which
  `_coerce_runtime_cap` rejects with `LoopConditionError`), or returns `MAX_NODE_VISITS`.
- A cap template MAY reference the loop step's own output (`data_flow.py:131-132`) or `${__iteration__}`
  (`data_flow.py:454-457`; `test_gate_pause.py:819-827` uses `max_iterations: ${__iteration__}`). On the walk's
  FIRST entry into the loop, the only referenceable store values that change before the first `should_reenter`
  are the loop step's own namespace and `__iteration__` (`namespaced_store.py:61-71`; other dunder keys are
  unreferenceable, `core/types.py:218-227`) — so a template referencing neither resolves identically at the gate
  and at the engine's memo point.
- **`??` defeats store-key hiding** (silent-failures lens, EXECUTED): with the own key removed,
  `${gated.result.n ?? 2}` resolves to the fallback 2 while the engine memoizes 5; `${__iteration__ ?? 3}` shows 3
  while the engine stops after 1. "Unknown" is therefore decided from the template's REFERENCES:
  `parse(template).references` yields every `Reference` with its `root`, `??` operands and dynamic-index inner
  keys included (`core/templates.py:262-264, 294-295`). Planner-checked: `${gated.result.n ?? 2}` → root `gated`;
  `${cfg[${gated.k}].x}` → roots `cfg`, `gated`; `${__iteration__ ?? 3}` → root `__iteration__`.
- **Per-run counter and cap** (feature-interactions lens): `loop_counts` is never reset when a back edge returns
  to a loop step (`engine.py:962`), and `loop_caps` is per run. Task 179 pins the continuing count (K fails at 3,
  on-error handler re-enters, gate pauses at 4 — `test_gate_pause.py:898-953`). With `max_iterations: 3` that
  gate would read "iteration 4 of up to 3" → D4 drops the clause when `iteration > cap`. A back edge that RE-RUNS
  an upstream step the cap template reads can make the derived cap differ from the memoized one — display-only,
  documented, not engineered (fixing the memo is an engine behaviour change). Also accepted: a body mutating a
  dict input in place (`python_code.py:705` passes the same objects).
- **Latent bug the new call site would widen:** `_coerce_runtime_cap`'s float branch is a bare `int(raw)`
  (`loop_control.py:188-189`) → `ValueError` on NaN, `OverflowError` on ±inf (JSON `Infinity` parses to inf).
  Today that crashes `should_reenter` after iteration 1; called from the gate it would crash the gate itself.
- `__iteration__` is never present for a gate on a non-loop step: sub-workflow children don't inherit it
  (`workflow_executor.py:145-165` `_PROPAGATED_KEYS`), batch and loop are mutually exclusive
  (`compiler.py:409-416`), `approval:` on batch steps is rejected (`gate_validation.py:17-21`).
- The dry-run planner builds no `GateRequest`; it already calls `resolve_loop_cap` and catches
  `LoopConditionError` (`execution/plan.py:942-947`). Its ⏸ footer and the run-start "will pause at approval
  gate(s)" warning name ids only. Out of scope; unchanged.

### 2.2 Trace (format change)
- `TRACE_FORMAT_VERSION = "2.8.0"` at `runtime/workflow_trace.py:44`, comment block `:33-43`. Gate pause line:
  `line["request"] = request.to_dict()` (`:677-678`; key `request`, not `gate_request`); top-level `iteration`
  opt-in (`:685-686`). Trailer: `agg.update(self.pause_request)` (`:1086-1096`), `pause_request` built at
  `engine.py:1638-1641` as `{"paused_node_id", "gate_request": request.to_dict()}`.
- `to_dict()` is `asdict` → the new field lands in both places automatically (`null` for non-loop gates,
  exactly like `iteration`). NOT mirrored to the gate line's top level (that key exists for the resume reader's
  per-iteration fold; `max_iterations` has no reader).
- Version pins: the constant, the comment, and `tests/test_runtime/test_trace_format_2_2.py:26-27`
  (`test_format_version_is_2_8_0`). Everything else compares against the constant or is fixture data on purpose
  (`test_resume_source.py` 2.8.0 fixtures still hold: 2.9 ≥ (2,8)). Consumers gate on `startswith("2.")`;
  `resume_source._predates_lossy_marker` (`:689`) compares `(major, minor) < (2, 8)` — 2.9 and 2.10 correct.
- Interning only replaces strings ≥1 KB (`trace_io.py:16, 82-122`); ints pass through. `_sanitize_for_json` never
  touches gate lines/trailer. `TraceFixtureBuilder` has no gate support; no test pins a `gate_request` key set.
- **Task-159 baseline** (`verify.sh`): diffs CLI stdout/stderr/exit only, never trace files; no case uses gates.
  Expected drift from this task: none from code; `12-real-world-lyrics-generator/04-guide-auto-detect` already
  drifts on the base. Base results in the progress log (re-captured after the #719 fast-forward).

### 2.3 Pause surfaces (each gets a test — spec "One field, every surface")
| Surface | Renderer today | Change |
|---|---|---|
| Non-TTY pause text (`run.py:694`) | `format_gate_lines` (`gate_prompt.py:216-239`) | `Loop iteration 1 of up to 3` |
| MCP pause text (`execution_service.py:255`) | `format_gate_lines` | same |
| Answer-required error (`exceptions.py:1582`; `context.gate` = `masked_gate_dict` `:1601`) | `format_gate_lines` | same; `context.gate.max_iterations` |
| TTY approval/escalation header + flag echo (`gate_prompt.py:121,145,156`) | `_iteration_suffix` (`:126-128`) | ` — iteration 2 of up to 3` |
| `resume list` text (`resume.py:459`) | inline f-string | `approval · iteration 2 of up to 3` |
| `resume list` JSON (`resume.py:432-443`) | dict | `+ "max_iterations"` beside `"iteration"` |
| CLI `--output-format json` pause doc (`run.py:668-687`) | `masked_gate_dict` | rides through (no code change) |
| `GET /api/gate` (`server.py:1508`) | `masked_gate_dict` | rides through (no code change) — the web panel's ONLY input: test it |
| Web eyebrow (`GateCallout.tsx:105`) | inline JSX | `· iteration 2 of up to 3` |
- `PausedRun` (`resume_source.py:1026`, built only in `list_paused_runs` `:1098`; reads `iteration` at `:1135`,
  int-guarded at `:1147`) needs `max_iterations` too.
- NOT gate position (unchanged): `⤷ Resumed from … (iteration 3)` (`success_formatter.py:558-559`) and the dry-run
  resume header (`plan_formatter.py:51`) — the resume ENTRY position.
- **Existing tests — what happens to each (review-corrected):**
  - Pass on both sides (prefix substrings, guard nothing about the cap): `test_paused_cli.py:417, 425, 454, 460`,
    `test_gate_prompt.py:362`. **Tighten them in place** to full lines (+ the new key) instead of adding parallel
    tests (test-fidelity S1).
  - **Will FAIL — expected; rewrite to the new text, never weaken:**
    `tests/test_mcp_server/test_execution_workflow.py:349` (`"Gate:\n  Loop iteration 1\n"`; the trailing `\n`
    no longer matches on the capped `_LOOP_GATE_WF`); `web/src/components/GateCallout.test.tsx:100` and the
    Task 179 loop-chain test in `web/src/views/GraphView.test.tsx` (~`:1596-1635`, `findByText("code · greet ·
    iteration 1|2")`) — Testing Library's default matcher reads an element's OWN text nodes, so D9's span breaks
    them. Re-pin on the `.gate-eyebrow` element's exact `textContent` (`toBe`, the pattern
    `GateCallout.test.tsx:107-108` already uses). A `/iteration/` regex or `{exact:false}` is NOT acceptable — it
    passes on `of up to 3` and voids the "no limit" checks; the GraphView test is the guard that the pinned second
    attempt re-shows the NEXT iteration.

### 2.4 `/api/resume` and the panel
- `_parse_resume_body` (`server.py:1157-1217`) → `(run, approve, choose, force)`; already 400s `approve`+`choose`
  with the house shape `{"error": …}`; docstring records two deliberate server-stricter-than-CLI rules. It ignores
  unknown keys. `resume` handler (`:1220`; its docstring's `Body:` line `:1223` states the full body): pre-flight
  closure `_resume_preflight` (`:1261-1269`) calls `preflight_resume(...)` and **discards `pf`**;
  `_resume_cli_args(run_target, approve, choose, force)` (`:1281-1291`).
- `ResumeSource.paused_node_id` (`resume_source.py:99`) is the paused step, written as `gate_exc.request.node_id`
  (`engine.py:1638-1639`) — the same id the resolver compares for `--approve` and `--auto-approve`
  (`gate_prompt.py:84-91`). Pre-flight with an `approve` answer already refuses an escalation (`wrong_flag`,
  `resume_source.py:781` → 409 `answer_required`) and a non-paused source (`not_paused`, `:826`). Nested gates
  never pause (`engine.py:1614` `not self.nested`), so `paused_node_id` is always a top-level step.
- CLI: `_approval_answer` (`resume.py:107-124`) refuses `--approve no` + `--auto-approve <paused>`; nothing else
  validates `--auto-approve` (accepted beside `--choose`; unknown ids accepted). `--auto-approve` matches by step
  id FLAT across the workflow tree and across later visits (`gate_prompt.py:65-66, 89-91`). EXECUTED on the base:
  `pflow resume <tok> --approve yes --auto-approve gated` at iteration 2 ran iterations 2–3 and completed;
  effects file 3 lines (`pause-surfaces-before-after.md` §3). Pinned already by
  `test_paused_cli.py:477` (`test_approve_yes_with_auto_approve_runs_gated_loop_to_completion`).
- Web: approval footer `.gate-foot > .gate-actions > [Deny][Approve]` (`GateCallout.tsx:121-141`);
  `useResumeAnswer.submit(answer, force)` spreads `ResumeAnswerPayload = {approve?, choose?}`
  (`resumeAnswer.tsx:17, 45-54`) into `resumeRun(req)` (`api/client.ts:190-217`, JSDoc body rules `:180-189`); the
  stale/side-effect ack re-sends `refusal.retry` with `force` (`resumeAnswer.tsx:167`) — an added field rides along.
- CSS: `.node-callout` is a fixed 320px wide in FLOW units (`index.css:2283-2302`) → ~296px of row width at any
  window size; a narrow window changes the camera, not the row. `.gate-actions` is `flex; justify-content:
  flex-end; gap 8px`, no wrap (`:2630-2634`). `.gate-approve, .gate-primary` is the accent fill, commented "the
  one affirmative per surface" (`:2651-2661`); Deny is the plain `.gate-btn`. Deny + Approve + "Approve all
  remaining" at 600 weight + 14px side padding is ~330px → **does not fit one row**: a real design decision.
- `src/pflow/ui/CLAUDE.md` has NO `/api/resume` / `/api/gate` contract section — the contract lives in `server.py`
  docstrings (and ADR-0009's Task-176 amendment, `:17`, lists the body as `{run, approve?, choose?, force?}`).
- Shared Python↔web fixture precedent: `web/src/test/fixtures/contracts/*.json` (GENERATED, drift-checked by
  `test_react_flow_contract_fixtures.py`). Vitest imports JSON from `web/src`; pytest can read `web/src` files.
- `screenshot-pflow-web-ui` skill: no window-size input; `click.pflow.md` does one real click per run (it really
  POSTs `/api/resume`). The #714 lane's resize→navigate→measure workflow was a scratch file and is gone; its
  fixtures survive at `/Users/andfal/projects/pflow/scratchpads/session-11/issue-714/falsifier-wf/`
  (`f2-esc-many.pflow.md` = a free real escalation via `mcp-chrome-devtools-evaluate_script`).

### 2.5 Cross-task scan (`./scripts/tasks`, 2026-10-06)
- Shipped substrate: Task 179 (iteration on `GateRequest`, trace 2.8.0, `PausedRun.iteration`), Task 176 (the
  bridge: `/api/gate`, `/api/resume`, `useResumeAnswer`), Task 171 (durable pause), #714/PR #718 (`.gate-foot`),
  #719 (#690: resume preflight + refusal text; landed during planning, citations re-verified). Their reviews'
  claims used here were re-verified against code (§2.1–2.4).
- Unbuilt overlap: **Task 180** (resume identity — per-step hashes in the trace meta line) also bumps the trace
  format and touches `runtime/resume_source.py`; builds serialize, the second to land takes the next minor
  number (D6). **#720** (≥1 KB gate strings arrive as blob refs) — every fixture keeps gate strings under 1 KB.
  Task 118/181 planners: disjoint (template resolver, shell node, MCP params). Nothing else relevant.

## 3. Decisions (all resolved; R1/R2 above are the user's)

**D1 — How the gate learns the cap: derive it at the gate; nothing is "written at loop entry". (Engine.)**
`loop_control.declared_loop_cap(config: NodeConfig, shared: dict[str, Any]) -> int | None`:
```python
loop_config = config.loop_config
if loop_config is None:
    return None                                    # non-loop step
if loop_config.max_iterations is not None:
    return loop_config.max_iterations              # literal: the compile-time constant
template = loop_config.max_iterations_template
if template is None:
    return None                                    # no author cap — never show the visit guard
if any(ref.root in (config.node_id, "__iteration__") for ref in parse(template).references):
    return None                                    # depends on the loop body → unknown (?? operands included)
try:
    return resolve_loop_cap(loop_config, shared, config.node_id)
except LoopConditionError:
    return None                                    # unresolvable / out of range → unknown
```
(`parse` is already imported in `loop_control.py`.) Docstring: display-only (never read by the walk or resume;
`should_reenter` stays the one cap decision); "the author's cap as knowable from outside the loop body"; why
"unknown" is decided by REFERENCES (`??` falls through to its fallback when a key is absent); the per-run
back-edge limit (§2.1). Don't restate this in CLAUDE.md files — point at the docstring.
- Options considered: (a) **this**; (b) resolve the real cap at loop entry and stash it in a new `__…__` store
  key — changes WHEN the engine resolves a template cap (behaviour change), mints a reserved key, still needs a
  resume path; (c) thread `loop_caps` into `_execute_node` — two signatures for a display value, still empty at
  iteration 1 and on resume; (d) literal-only (`None` for every template — review-plan S1): simplest, but drops
  the documented `${template}` cap (`loop.md:96`) for a 3-line reference check. (a) has no walk state, works at
  iteration 1 and on resume, and every literal cap is the compile-time constant. Reversible: one pure function.
- First draft hid keys with a store copy; the silent-failures lens broke it by execution with `??` — replaced.
- Accepted edges: under `--only` a loop target runs ONE iteration but a TTY prompt reads `iteration 1 of up to 3`
  (gates cannot pause under `--only`; `iteration 1` is already shown today); a back edge that re-runs an upstream
  step the cap template reads (§2.1).

**D2 — Fix `_coerce_runtime_cap`'s non-finite float (gap this task would widen).** Float branch: `if not
math.isfinite(raw)` → `LoopConditionError` (same message family as the non-numeric arm) before `int(raw)`.
`declared_loop_cap` then needs only `LoopConditionError`; the planner and `should_reenter` get a structured error
instead of a bare crash. (ORCHESTRATION "A gap your change is about to widen is yours to close" — say so in the
PR body.)

**D3 — Field shape (orchestrator default kept):** flat `max_iterations: int | None = None` on `GateRequest`, after
`iteration`, comment mirroring `iteration`'s ("display-only — resume never reads it"). JSON: **`null`, not absent,
not 0** — for a non-loop gate, an uncapped loop, and an unknown templated cap — identical to `iteration`'s `null`
(spec corrected: it said "absent"). Records written before this task lack the key; every reader treats absent as
`null`. Tests assert `d["max_iterations"] is None` by SUBSCRIPT, never `.get(...)` (`.get` passes on pre-change
code and on an implementation that omits the key). Both builders take `max_iterations: int | None = None` and
EVERY `GateRequest(...)` construction in them passes it (approval's non-dict-params branch `core/gate.py:80`,
escalation's string-marker branch `:94` — silent-failures S2). Name = the authoring key; no CONTEXT.md noun
changes (CONTEXT already says a Loop is "capped by a maximum").

**D4 — One Python renderer.** `core/gate.py::loop_position(iteration: object, max_iterations: object) -> str | None`
beside `option_labels` (a display rule shared by every gate renderer lives beside the payload). Rules: `iteration`
not an `int` → `None`; `max_iterations` an `int` AND `iteration <= max_iterations` → `f"iteration {iteration} of
up to {max_iterations}"`; else `f"iteration {iteration}"`. (`iteration > max_iterations` happens on a back edge
into the loop, or a resume with a lowered cap — `rounds=1` input override, `--force` after editing a literal down;
"iteration 4 of up to 3" is never printed.) Callers: `format_gate_lines` → `[f"Loop {pos}"]`; `_iteration_suffix`
→ `f" — {pos}"` (keeps its name and three call sites); `resume.py` GATE column → `f"{kind_label} · {pos}"`. The
inline guards (`gate_prompt.py:128` and `resume.py:459` use `is not None`; `gate_prompt.py:229` uses `isinstance`)
go away with it.

**D5 — `pflow resume list`.** `PausedRun.max_iterations: int | None = None`; `list_paused_runs` reads
`gate_request.get("max_iterations")` with the same int guard as `iteration`. JSON row gains `"max_iterations"`
immediately after `"iteration"` (agent contract; same null semantics). Text column via `loop_position`.

**D6 — Trace 2.9.0.** Constant `"2.9.0"`; comment block gains: *2.9.0 (Task 183, additive) adds `max_iterations`
inside the gate payload (the pause line's `request` and the trailer's `gate_request`): the loop's author cap as
known at the gate, display-only; `null` for non-loop gates, uncapped loops and caps not knowable outside the loop
body.* Rename/re-pin `test_format_version_is_2_8_0` → `_2_9_0`. **If Task 180 merges first and takes 2.9.0, this
task takes the next free minor (2.10.0) and its comment entry follows Task 180's.**

**D7 — `/api/resume` contract.** Body field `auto_approve` (optional). All checks in `_parse_resume_body`, before
any I/O, house shape `{"error": …}`:
- unknown top-level keys → `Unknown field(s): <names> — expected run, approve, choose, force, auto_approve.`
  (silent-failures S1: a raw caller's `autoApprove` must not silently become a one-iteration approve; "no silent
  no-ops");
- non-bool → `Field 'auto_approve' must be a boolean.` (mirrors `force`);
- `true` with `approve: "no"` → `Field 'auto_approve' requires approve: "yes" — it pre-approves this step's
  remaining iterations, which contradicts denying it.`;
- `true` with `choose` → `Field 'auto_approve' applies to approval gates only — escalations cannot be
  pre-answered.`;
- `true` with no answer → `Field 'auto_approve' requires approve: "yes".`
`false`/absent → today's behaviour exactly. On a non-loop approval gate it is accepted (CLI parity; "loop gates
only" is a UI rule). Server-stricter than the CLI (which accepts `--auto-approve` beside `--choose`) — add it to
`_parse_resume_body`'s recorded asymmetries; update the `resume` docstring's `Body:` line (`:1223`).
Mechanics: `_parse_resume_body` returns `auto_approve` as a 5th element; the pre-flight closure returns
`pf.source.paused_node_id`; `_resume_cli_args(run_target, approve, choose, force, auto_approve_step: str | None)`
appends `["--auto-approve", step]` after `--approve yes` when given. If `auto_approve` is true and the id is not a
`str` (unreachable after a passing approve pre-flight, §2.4), return a 400 `{"error": …}` and do not spawn.

**D8 — Shared case table, hand-authored.** `web/src/test/fixtures/loop-position.json` — beside, not inside, the
GENERATED `contracts/` dir. Rows `{"id", "gate": {…}, "text"}`: `capped` (1, 3 → `iteration 1 of up to 3`);
`null-cap` (2, `null` → `iteration 2`); `old-record` (2, key ABSENT → `iteration 2`); `non-loop` (`null`, 3 →
`null`); `empty` (both absent → `null`); `past-cap` (4, 3 → `iteration 4`). A pytest in
`tests/test_execution/test_gate_prompt.py` (the gate-renderer tests; `core/gate.py` has no test module) asserts
`loop_position(gate.get("iteration"), gate.get("max_iterations")) == text` per row; a vitest asserts the TS twin
the same. Both assert the row count (6) and the id set, so an empty/truncated file cannot pass. Rejected: a
generator + drift test — a 6-row rule doesn't earn one; both sides reading one file IS the pin.

**D9 — Web panel (design-bearing; the Fable phase settles the look within these bounds).**
- TS twin `loopPosition(iteration, maxIterations): string | null`, exported from `GateCallout.tsx` beside
  `optionLabel` (the existing twin of `core/gate.py::option_labels` lives there — same precedent), returning the
  exact Python text (plain spaces); `undefined` and `null` behave alike. The eyebrow wraps it in a span with
  `white-space: nowrap` (replaces the inline NBSP; same no-stranding intent; text stays byte-equal to the fixture).
- `GateRequest.max_iterations?: number | null` (`web/src/types.ts`); `ResumeAnswerPayload` and `resumeRun`'s
  `req` gain `auto_approve?: boolean`; `resumeRun`'s JSDoc body rules gain "`auto_approve` only with `approve:
  "yes"`". Test fixtures mirror the wire: `APPROVAL` (`GateCallout.test.tsx:23-37`) gains `max_iterations: null`;
  a key-absent payload stays as the explicit old-record pin.
- **Approve all remaining** renders iff `req.kind === "action_approval" && typeof req.iteration === "number"`
  (R2 may add `&& typeof req.max_iterations === "number"`), inside `.gate-foot`, and submits
  `answer.submit({ approve: "yes", auto_approve: true })`; disabled while submitting like its siblings. Label is
  exactly "Approve all remaining" (spec: never a count). Shown at every loop iteration including the last.
- Approve stays THE accent-filled primary and keeps its place; the bulk action is visibly affirmative but
  secondary (no second accent fill — `index.css:2651`'s rule); Deny stays quiet. A `title` tooltip states the TRUE
  scope of `--auto-approve` — flat by step id across the workflow tree and later visits (§2.4): e.g. "Approve this
  and every later approval of a step named '<step>' in this run (including inside sub-workflows)"; on a
  `max_iterations: null` loop it names the bound ("until the loop's condition stops it") per R2(a). No confirm
  dialog (Approve is one click too; the label is explicit) — the user may ask for one at the checkpoint.
- The row does not fit three buttons in ~296px: the Fable implementer chooses the layout (wrap, a second row, or
  another arrangement) against P4's acceptance criteria. `.gate-actions` keeps no fixed button-count assumption.
- `web/src/components/CLAUDE.md` gains the show rule + "Approve is the one accent fill".

**D10 — Stale surfaces.**
- Guide: `approval.md:34` (pause names `Loop iteration 2 of up to 3`; the browser's Approve all remaining),
  `:53` (panel answers), `ui.md:36`, `resume.md:44, 54`; ONE sentence (in `approval.md:34` or `resume.md:54`):
  `max_iterations: null` on a loop gate means no limit is known at the pause — the loop runs until its condition
  stops it (at most the engine's visit guard), and `--auto-approve` / Approve all remaining approves all of them;
  the bulk approval is by step NAME (flat across sub-workflows, as `approval.md:53` already says for the flag).
- Docs: `docs/reference/cli/index.mdx:117`, `docs/how-it-works/approval-gates.mdx:56`. Keep `approval.md:45`,
  `approval-gates.mdx:44` and `docs/reference/cli/index.mdx:135` ("deliberately no approve-everything flag" /
  "no approve-all form") true — the new action is per-step; add a half-sentence where it reads as a contradiction.
- Instruction files: `src/pflow/ui/CLAUDE.md` (one line: `/api/resume` `auto_approve` → `--auto-approve <paused
  step>`; the contract lives in the docstring); `web/src/components/CLAUDE.md` (D9); `src/pflow/runtime/engine/CLAUDE.md`
  gate section (one line: the payload's `max_iterations` comes from `declared_loop_cap`, display-only — point,
  don't restate). `.claude/agents/pflow-codebase-searcher.md`: no change (no new node/command).
- **ADRs: no new ADR; two one-line amendments, proposed in the hand-back for the main orchestrator to confirm**
  (architecture-fit S1, impact-completeness W3): ADR-0010's Task-179 amendment (the payload is "additive-only from
  here") gains `max_iterations` — "the author cap as knowable outside the loop body; may be `null` while the engine
  enforces a cap" — so nobody "fixes" `declared_loop_cap` toward `should_reenter`; ADR-0009's Task-176 amendment
  (`:17`, body `{run, approve?, choose?, force?}`) gains `auto_approve?` — deliberately a bool the server resolves to
  the ONE paused step, not the CLI's id list (keeps "approval bypass is per-node" true). If confirmed, P3 writes them.

## 4. Phases

Agent economics: **P1–P3 are one Opus `task-phase-implementer` launch** (same tier, each builds on the last, the
Python side end to end). **P4 is a separate launch (tier change: design-bearing UI)**. P5 is the task
orchestrator's.

### P0 (first step of P1) — baseline
If `origin/main` moved past `2464e43c`: merge it first and re-verify the `resume_source.py` / `exceptions.py` /
`server.py` citations above. Then `make test` + `make check` (record pass/fail by name); `cd web && npx vitest run
&& npx tsc --noEmit`. The Task-159 baseline drift set for the current base is in the progress log (re-capture if
main moved).

### P1 — The cap on the gate payload (engine + core + trace) — **ENGINE CONTACT, TRACE FORMAT**
- Goal: every gate raised by a loop step carries `max_iterations` per D1/D3; D2; trace 2.9.0 (D6).
- Files: `src/pflow/runtime/engine/loop_control.py` (`declared_loop_cap`, D2), `src/pflow/core/gate.py` (field,
  both builders, `loop_position` — D4's helper lands here so P2 only wires it), `src/pflow/runtime/engine/gate.py`
  (both gate functions pass `max_iterations=declared_loop_cap(config, shared)`), `src/pflow/runtime/workflow_trace.py`,
  `tests/test_runtime/test_trace_format_2_2.py`; tests in `tests/test_runtime/test_loop_control.py` and
  `test_gate_trace.py` / `test_gate_pause.py` (real engine runs).
- Model: **Opus**, effort **medium** (fully specified; the seam reasoning is done here).
- Tests must catch:
  1. Approval gate at **iteration 1** of a `max_iterations: 3` loop: the gate pause line's `request` AND the
     trailer's `gate_request` both carry `max_iterations == 3` (real engine run, pre-exec — fails if the cap were
     read from `loop_caps`).
  2. Escalation gate in a capped loop carries the cap — once with a dict marker and once with a STRING marker
     (the second `GateRequest(...)` branch, D3).
  3. Uncapped loop → `request["max_iterations"] is None` (subscript) with `iteration == 1` (proves the medium).
  4. Non-loop gate → both keys present and `None` (subscript).
  5. `max_iterations: ${rounds}` from a workflow input → the resolved int at iteration 1.
  6. Body-dependent caps → `None`, asserted where a wrong implementation would NOT coincidentally pass: (a)
     `${<step>.result.n}` at **iteration 2's** approval pause (own output now in the store) and at iteration 1's
     ESCALATION (post-exec); (b) `${<step>.result.n ?? 2}` with a body returning `n: 5` → `None` at every pause,
     and the loop still runs 5 iterations (effects count — display never changes behaviour); (c)
     `${__iteration__ ?? 3}` → `None`.
  7. A resumed run's gate at iteration 2 carries the cap (`loop_caps` is empty on resume).
  8. Back edge past the cap: the recovered-failure shape of `test_gate_pause.py:898-953` with `max_iterations: 3`
     → the gate at iteration 4 carries `max_iterations == 3` and `iteration == 4` (rendering drops the clause —
     asserted in P2 via the case table's `past-cap` row and one real-run text assertion).
  9. `_coerce_runtime_cap(nan / inf / -inf)` → `LoopConditionError`; `declared_loop_cap` on such a template → `None`
     (the gate does not raise).
  10. `TRACE_FORMAT_VERSION == "2.9.0"`.
- Handoff: `make test` + `make check` green; scenarios pinned; nothing renders the cap yet.
- **Triggers mid-task review** (engine + trace + gate semantics): **`review-silent-failures`** (a display value
  that can raise at the gate or silently disagree with `should_reenter`) and **`review-feature-interactions`**
  (loop × gate kinds × resume × back edges × `--only` × sub-workflow hosts × templated caps), scoped to P1's files.
  The task orchestrator runs it at the end of the P1–P3 launch (P2/P3 only consume the field; a P1 finding that
  reshapes it would also touch P2, which is cheap). Lenses belong to P1, which introduces the risk.

### P2 — One renderer, every Python surface
- Goal: all Python pause surfaces render via `loop_position` (D4); `resume list` carries the cap (D5).
- Files: `src/pflow/execution/gate_prompt.py` (`_iteration_suffix`, `format_gate_lines`),
  `src/pflow/runtime/resume_source.py` (`PausedRun`, `list_paused_runs`), `src/pflow/cli/commands/resume.py` (text
  column + JSON key); tests: `tests/test_execution/test_gate_prompt.py`, `tests/test_cli/test_paused_cli.py`,
  `tests/test_cli/test_resume_list_cli.py`, `tests/test_mcp_server/test_execution_workflow.py`; the shared table
  `web/src/test/fixtures/loop-position.json` + its pytest (D8).
- Model: **Opus**, effort **medium**. Same launch as P1.
- Tests must catch — **tighten the existing tests in place** (§2.3) and add only the twins; every positive asserts
  the FULL line, paired with an absence twin:
  1. Non-TTY pause: tighten `test_paused_cli.py:417, 425` to `"   Loop iteration 1 of up to 3\n"` / `… 2 of up to
     3\n`; NEW uncapped twin: `"   Loop iteration 1\n"` present AND `of up to` absent.
  2. `test_loop_gate_position_reaches_every_pause_surface` (`test_paused_cli.py:441`) tightened: JSON pause
     `gate_request["max_iterations"] == 3`; `resume list` text `approval · iteration 2 of up to 3` (full cell);
     `rows[0]["max_iterations"] == 3`; answer-required message `Loop iteration 2 of up to 3` and
     `context.gate["max_iterations"] == 3`. Non-loop JSON pause → `gate_request["max_iterations"] is None`.
  3. MCP: rewrite `test_execution_workflow.py:349` to `"Gate:\n  Loop iteration 1 of up to 3\n"` (expected
     failure, §2.3).
  4. TTY: synthetic `GateRequest` header + echo `— iteration 2 of up to 3` (tighten `test_gate_prompt.py:362`);
     real-CLI echo added to `test_paused_cli.py:477`: assert the ITERATION-2 line `✓ Gate 'gated' — iteration 2 of
     up to 3 approved via --approve yes` (iteration 3 = the cap, so "3 of up to 3" passes a renderer that prints
     `of up to {iteration}` — test-fidelity S4).
  5. **Old record**: produce a real pause, strip `max_iterations` from the trailer's `gate_request` in the trace file
     (the realistic 2.8.0 shape) → `resume list` text `approval · iteration 2` with no `of up to`, JSON
     `rows[0]["max_iterations"] is None`, answer-required error `Loop iteration 2` with no `of up to`.
  6. Past the cap: a real run of the P1-8 back-edge shape shows `Loop iteration 4` (and no `of up to`).
  7. The shared case table drives `loop_position` (row count + ids, D8).
  8. IF R1 = yes: the bulk hint line appears for a loop approval pause (CLI + MCP + answer-required, one helper
     beside `format_resume_answer_command`) and is absent for a non-loop approval and a loop escalation.
- Handoff: `make test` + `make check` green; `bash scratchpads/task-183/capture.sh p2` (gitignored; recreate from
  `pause-surfaces-before-after.md` if missing) shows the AFTER text.
- Mid-task review: no (the P1 review covers the producer; renderer/test fidelity is a completion-gate lens).

### P3 — `/api/resume` `auto_approve` + Python-side docs
- Goal: D7; plus D10's guide/docs/CLAUDE.md/ADR lines that don't depend on the panel's look.
- Files: `src/pflow/ui/server.py` (`_parse_resume_body`, the pre-flight closure, `_resume_cli_args`, both
  docstrings), `tests/test_cli/test_ui_interaction_server.py`, `src/pflow/ui/CLAUDE.md`,
  `src/pflow/runtime/engine/CLAUDE.md`, `src/pflow/guide/features/{approval,resume}.md`,
  `docs/reference/cli/index.mdx`, and the ADR-0009/0010 one-liners if confirmed (D10).
- Model: **Opus**, effort **medium**. Same launch as P1–P2.
- Tests must catch (reuse `TestResumeEndpoint`'s real-paused-trace fixtures; `_LOOP_GATE_WF` at `:1174-1209`):
  1. `{run, approve: "yes", auto_approve: true}` on a real paused loop gate → the exact argv list ending
     `["--approve", "yes", "--auto-approve", "gated"]` (like `:1253-1264`). (The CLI half — that this argv
     finishes the loop — is already pinned by `test_paused_cli.py:477`; no separate end-to-end test.)
  2. `auto_approve: false` and absent → argv identical to today (no `--auto-approve`).
  3. 400 + `popen.assert_not_called()` for each D7 refusal: with `approve: "no"`, with `choose`, with no answer,
     `"true"` (string), an unknown key (`autoApprove`) — extend `test_shape_errors_are_400_before_any_io`.
  4. `auto_approve: true` + `force: true` → both flags in argv (the ack retry path).
  5. `auto_approve: true` on a non-loop approval gate → spawned with `--auto-approve <step>` (CLI parity).
  6. `auto_approve: true` + `approve: "yes"` on a paused ESCALATION → the existing 409 `answer_required`, no spawn.
  7. `/api/gate` carries the field (test-fidelity W1 — the panel's only input): add
     `body["gate_request"]["max_iterations"] == 3` to `test_loop_pause_payload_carries_the_iteration` (`:1027`) and
     `["max_iterations"] is None` beside the non-loop assertion (`:1024`).
- Handoff: `make test` + `make check` green; implementer writes the P1–P3 log entry and hands back.
- Mid-task review: no (thin, fully tested mapping; `review-impact-completeness` covers the contract at completion).

### P4 — Web panel: the limit in the eyebrow, "Approve all remaining" in the foot — **DESIGN-BEARING UI**
- **Tier: Fable, pending the user's per-launch word** (the user approved Opus for #714 only; the main orchestrator
  asks at launch). Effort **high**. Fresh `task-phase-implementer` launch (tier change). Apply R2's ruling.
- Use case: a human in the browser is approving a gated loop; at each pause they see where in the loop they are
  and how far it can go ("iteration 2 of up to 3"), and either approve this one iteration (Approve, as today) or
  the rest of the loop in one click (Approve all remaining) and watch the run finish.
- Look/feel intent: the panel stays #718's panel. The position joins the eyebrow in its existing type — no badge,
  no colour. Approve keeps its place and remains the ONE accent-filled affirmative; "Approve all remaining" reads as
  affirmative but secondary, clearly distinct from Deny; nothing about the non-loop or escalation panel changes.
  The footer still reads as one calm answer area (one row, or a deliberate two-row arrangement), not a toolbar.
- Files: `web/src/types.ts`, `web/src/components/GateCallout.tsx` (`loopPosition`, eyebrow span, bulk button),
  `web/src/components/resumeAnswer.tsx` (`ResumeAnswerPayload`), `web/src/api/client.ts` (`resumeRun` req type +
  JSDoc), `web/src/index.css` (`.gate-actions` layout, the secondary-affirmative style, eyebrow span),
  `web/src/components/GateCallout.test.tsx`, **`web/src/views/GraphView.test.tsx`** (re-pin the loop-chain eyebrow
  test, §2.3), `web/src/components/CLAUDE.md`, guide `ui.md:36` + `approval.md:53` +
  `docs/how-it-works/approval-gates.mdx:56` browser wording.
- Tests must catch (vitest; eyebrow assertions are exact `textContent` `toBe` on `.gate-eyebrow`, never regex):
  1. Eyebrow `code · gated · iteration 2 of up to 3` (capped); `code · gated · iteration 2` for `max_iterations:
     null` AND for a payload without the key; `shell · deploy` for a non-loop gate. Re-pin
     `GateCallout.test.tsx:100` and the GraphView loop-chain test the same way (`… · iteration 1` → `… · iteration
     2` across the two pauses, their payloads updated to carry a cap where that strengthens them).
  2. Bulk button present for a loop approval gate (inside `.gate-foot`); absent for a non-loop approval (Approve
     present) and a loop ESCALATION (Answer present). If R2 = (b): absent for `max_iterations: null` too.
  3. Click → `resumeRun` called with exactly `{run: "r1", approve: "yes", auto_approve: true}`; pins the new
     attempt; all footer buttons disabled while in flight.
  4. Stale-workflow ack after a bulk click retries `{run: "r1", approve: "yes", auto_approve: true, force: true}`.
  5. Plain Approve still sends exactly `{run: "r1", approve: "yes"}` (no `auto_approve` key).
  6. `loopPosition` over every row of `loop-position.json` (row count + ids).
  7. CSS pin (jsdom has no layout): whatever rule keeps the answer controls inside the row is asserted via the
     `cssRule` helper (`GateCallout.test.tsx:306-312`), as #718 pinned `.gate-foot`.
- **Visual acceptance criteria** (real browser via `screenshot-pflow-web-ui`; kill stale `pflow ui` servers and
  `make ui-build` first; free port; stop the server by PID — only PIDs whose argv carries this worktree path):
  - Every answer button (Deny, Approve, Approve all remaining) fully inside the viewport AND the callout's clip
    rect AND topmost at its own centre (`elementFromPoint`), at **1440×900 and 760×560**, for a short preview and a
    long (<1 KB, #720) code preview; the ✕ stays reachable.
  - No button label truncated, clipped, or wrapped mid-word; `.gate-foot` has no horizontal overflow.
  - Approve is still the only accent-filled button and keeps its position relative to Deny.
  - The eyebrow shows `iteration N of up to M` on one line, or wraps only BETWEEN the step id and the position.
  - Non-loop approval and loop escalation footers are visually unchanged (side-by-side shots).
  - The skill has no window-size input: write a scratch resize → navigate → measure workflow (chrome-devtools
    `resize_page` or equivalent) under `scratchpads/task-183/`, as #714's lane did; keep its JSON beside the shots.
- Real-browser verification (the review evidence; one real click per `click.pflow.md` run):
  1. Capped 3-iteration gated loop (`_LOOP_GATE_WF` shape): pause → eyebrow `iteration 1 of up to 3` → click
     **Approve all remaining** → new run id from `/api/runs` → success banner; effects file `wc -l` = **3**
     (presence) and `pflow resume list` shows no pending pause for it.
  2. Fresh run: click **Approve** → the panel re-appears reading `iteration 2 of up to 3`.
  3. BEFORE (origin/main build) and AFTER shots for: loop gate with an author cap; without one; a non-loop gate; an
     escalation inside a loop (an `mcp-chrome-devtools-evaluate_script` step with `loop:` returning an escalation
     marker <1 KB — pattern `/Users/andfal/projects/pflow/scratchpads/session-11/issue-714/falsifier-wf/f2-esc-many.pflow.md`;
     a `code` escalation cannot pause durably); the narrow window.
- **EMBEDDED USER CHECKPOINT (handback)**: after the AFTER shots and measurements the implementer STOPS; the task
  orchestrator hands back the before/after pairs (paths) + measurement JSON + one line per design choice to rule
  on (button layout; the secondary style; tooltip copy incl. the flat-by-name scope; R2's show rule if not yet
  ruled; no confirm dialog). Resume on the ruling; re-shoot what changed. Not mergeable without it.
- Handoff: vitest + `tsc --noEmit` + `make check` green; shot + measurement paths in the log; ruling logged.
- Mid-task review: no (the screenshots are the evidence; the completion gate covers the code).

### P5 — Completion (task orchestrator)
- `make check`, `make test-all-local`, `cd web && npx vitest run && npx tsc --noEmit`, and
  `.taskmaster/tasks/task_159/baseline/verify.sh` — the drift set must equal the base's (progress log); a
  guide-text case that drifts because it prints an edited guide section is regenerated deliberately and said so.
- Real-surface runs in the log: `bash scratchpads/task-183/capture.sh after` reproduces every AFTER block of
  `pause-surfaces-before-after.md` (diff the redacted output against `out/before2`: only loop-position lines differ,
  plus the R1 line if ruled yes).
- If `main` moved: merge it, re-run the gate, re-check the trace version against Task 180 (D6).
- Completion-gate `deep-review` (code mode; engine + trace + UI): `review-falsifier` (direct, last — promises = the
  spec's Verification rows), `review-spec-conformance`, `review-simplicity`, `review-test-fidelity`,
  `review-silent-failures`, `review-agent-ux` (pause text, JSON key, 400 messages), `review-impact-completeness`
  (every `GateRequest`/`gate_request` consumer; the `/api/resume` contract and its client).
  `tests-windows` CI is blocking (no platform-sensitive code expected).
- `create-task-review` → `create-pr` with "Closes #656"; "Refs #720 — not a closing PR". PR body states D2 as a
  widened-gap close. Spec `## Status` → done + `## Completed` in the same PR.

## 5. Verification matrix (spec → evidence)

| Spec promise | Positive evidence (fails on pre-change code) | Phase |
|---|---|---|
| One click finishes a gated 3-iteration loop in the browser | real click → success banner + effects file 3 lines | P4 |
| Single Approve still advances one | real click → panel re-shows `iteration 2 of up to 3` | P4 |
| `max_iterations: 3` shows `iteration 1 of up to 3` everywhere | P2-1..4 (+ P3-7 `/api/gate`) + vitest 1; `capture.sh after` | P2/P3/P4 |
| No `max_iterations` shows `iteration 1` (no safety limit) | P1-3, P2-1 twin, vitest 1 | P1/P2/P4 |
| Non-loop gate unchanged, no bulk action | P1-4, P2-2, vitest 1–2, screenshots | P1/P2/P4 |
| Iteration 1's gate shows the cap | P1-1 (pre-exec, real engine) | P1 |
| `auto_approve` + `approve: no` / malformed → 400 before spawn | P3-3 | P3 |
| Old records render today's text | P2-5 (stripped real trailer), vitest 1 (no key), `old-record` row | P2/P4 |
| Escalation in a loop: position shown, no bulk action | P1-2, `format_gate_lines` test, vitest 2, screenshot | P1/P2/P4 |

## 6. Risks and follow-ups
- **Trace-number race with Task 180** (D6): the second to merge renumbers. The main orchestrator should add one
  line to Task 180's spec ("2.9.0 may be taken by Task 183") — that spec lives outside this worktree.
- **R1 recommendation (CLI/MCP bulk hint)**: agent-first — the pause output is where an agent decides; today it
  learns the bulk path only from the guide, so it relays each iteration to its human as a new pause (the CLI form
  of the 30-click problem). Proposed line, loop approval gates only, from one helper beside
  `format_resume_answer_command`: `To approve this and every remaining iteration of 'gated' (only with your human's
  OK): pflow resume <token> --approve yes --auto-approve gated`. Shown as PROPOSED in
  `pause-surfaces-before-after.md`.
- Sibling gaps, not fixed here (one line each in the task-review): `GateNotInteractiveError`'s "pre-approve ONLY
  this gate: `--auto-approve=<step>`" suggestion (`core/exceptions.py:1122`) under-states scope for a loop step
  (approves every iteration); the screenshot skill's missing window-size input; dry-run ⏸ footer shows no position.
