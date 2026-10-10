# Task 120 — progress log

Append-only. Entry format: ORCHESTRATION.md → "Progress-log entry format". Spec → plan → this log is the
resume path for any successor.

## [2026-10-10 23:40] task-planner (Fable) — planning complete (plan + CP-1 checkpoint written; self-review running)
- Did: investigated via six parallel searchers + 14 executed BEFORE probes; wrote `implementation-plan.md`
  (D1–D14, phases P0/PA/PC/PB/PD/PE/PF/PZ) and `diagnostics-checkpoint.md` (CP-1); applied the spec
  corrections listed in plan §2.1 to `task-120.md`.
- Changed: `implementation/implementation-plan.md`, `implementation/diagnostics-checkpoint.md`, `task-120.md`
  (mechanism sentence for the carrier, resume no-reorder, `last_execution_params` already coerced, line drift,
  Dependencies/References).
- Verified: base `285e7b3f` == `origin/main` (`git log -1` both); every §2.2 fact read at file:line or executed
  (probe outputs in the checkpoint §1 BEFORE blocks); `format_param_value` has two production callers;
  `TypeSpec.accepts` has zero callers; `resolve_templates` receives the raw `shared` dict (`engine.py:1748` →
  proxy at `:1755`); no validator rule rejects an input named like a batch alias (grep).  |  Assumed: Task 181
  lands with the kwarg shapes in its plan (plan §0 re-verifies); the parity harness can seed typed inputs
  without a `Row` shape change (PE-9 says what to do if not).
- Deviations/surprises: (1) the carrier is NOT a `TemplateConfig` field — the declared types ride the shared
  store under one reserved key installed like `__pflow_prompt_cache__` (plan D8, rejected alternatives
  recorded; spec Design sentence edited; ADR-0017 wording handed up). (2) `prepare_inputs` checks `required`
  before `default` today, so any direct `compile_workflow` of a defaulted-but-not-`required: false` input
  fails — the runner's default pre-fill hides it and is also the f₂ bug; D5/D6 fix both and harmonise the two
  "required" heuristics. (3) `last_execution_params` already stores coerced values (compile mutates the
  runner's params in place) — spec said "should". (4) `http.params` kept out of the text rule (list leaves are
  legitimate repeated params); `headers` in. (5) D11(f) adds an input-vs-batch-alias validator rule as the
  gap D8 would widen (#730 member). (6) `--validate-only` with values also rejects undeclared extras (free
  with running `prepare_inputs`; #297's parity half). (7) The `child_failure` bundle key `template_diagnostic`
  is generalised to `diagnostic` so the per-item child-input error rides the existing channel.
- Self-checks: plan-mode `deep-review` dispatched through the pflow fan-out on codex (7 lenses:
  plan, architecture-fit, validation-consistency, impact-completeness, feature-interactions, silent-failures,
  agent-ux) → `scratchpads/task-120-plan-review/report.md`; outcome and folded fixes in the next entry.
  test-reflect: n/a (no tests written).
- Next: fold confirmed Critical/Warning fixes into the plan; commit plan + checkpoint + spec + log on the
  feature branch; hand back (CP-1 to be ruled before I1 launches; 181 must be merged first).

## [2026-10-10 23:55] task-planner (Fable) — plan-mode battery folded; ready to commit
- Did: read the 7-lens codex report in full (`scratchpads/task-120-plan-review/report.md`, no failed lens);
  verified every Critical/Warning citation against code (one batched read); folded 18 findings, disputed 1.
- Changed: `implementation-plan.md` (D1 number = JSON-number first; D2/D5 "None is absence" with presence
  in ONE place; D3 no retriable/batch_fatal, masked suggestions; D6 analyzer placeholders + CLI/MCP error
  routing + synthetic contexts; D8 shadowing at the two merge points, runner installs the key, W5 miss
  message; D10 `_validate_child_params` = `prepare_inputs` per item, bundle key compat, dry-run typed per
  item; D11(b) before the early return + cache vars + surface-aware ownership, (e) authored literals only,
  (f) `batch.as`; D14 honest memo note; §9 dispositions; new tests PA-1, PB-8, PC-12/13, PD-1b/1c/6/7,
  PE-6/7/7b), `diagnostics-checkpoint.md` (fixture split runtime-vs-inline, honest §1.5 BEFORE — the probe
  used node `error_action`, which does not continue a batch; `as:`; §1.14 protected-descendant message;
  §1.15 analyzer routing; R4 resolved `pflow settings set-env`; R6 added).
- Verified: F1 `step_scope` owns authored inputs as local for every surface (`data_flow.py:884`); F2 early
  return `validator.py:141`; F3 `operands.py:50` excludes cache, `prompt_cache.py:170-174` → ABSENT; F7/F8
  `ir_schema.py:98,104` (`as`, `error_handling`); F6 `analyze_cache.py:187` catches only FileNotFoundError;
  W3 `execution_service.py:545` RuntimeError wrap; C2 batch memo key `instrumentation.py:214-231` has no
  resolved params — pre-existing (Task 170 follow-up), disputed as not widened; W4 `workflow_output.py:191`
  post-run; S2 `pflow settings set-env`. `origin/main` moved to `ebaa5d1b` (#757) during planning — disjoint.
- Deviations/surprises: the biggest fold is structural — the child boundary IS `prepare_inputs` (one presence/
  null/fallback rule for root and child; the seeding loop over `resolved_defaults` dies), and the typed-root
  map must be stripped at the two context merge points, not up front (six lenses converged on the latter).
- Self-checks: clean after the fold; no open Critical. Not re-run through the fan-out (changes are the
  lenses' own corrections; the completion gate re-reads the integrated code).
- Next: commit plan + checkpoint + spec + log on `feat/task-120-declared-input-types`; hand back (CP-1 R1–R3,
  R5, R6 to rule; 181 merges first; main orchestrator decides planner-implements vs task-orchestrator).
