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

## [2026-10-10] main orchestrator — CP-1 RULED
- Did: relayed the diagnostics checkpoint to the user in plain language (one before/after example + the five rulings with
  recommendations); user: *"go ahead with this"*.
- Changed: `diagnostics-checkpoint.md` header (RULED block), plan header line, this log.
- Verified: R1 `Invalid input value` · R2 source clause everywhere · R3 yes · R5 80 chars + `<REDACTED>` · R6 §1.14 reason text.
  R4 already resolved. | Assumed: nothing.
- Deviations/surprises: the planner's `__pflow_input_types__` carrier deviation was accepted by the main orchestrator (2/5,
  reversible); ADR-0017's carrier wording and Task 112's top block were amended on MAIN (uncommitted) — not on this branch.
- Next: build launches (Opus task-orchestrator, implement-from-plan) after Task 181 merges; P0 re-verifies 181's shapes.

## [2026-10-11 11:10] task-orchestrator (Opus) — bootstrap (implement-from-plan)
- Did: read packet `scratchpads/session-14/packet-task-120.md`, ORCHESTRATION.md, spec, plan, checkpoint (RULED), this log,
  Task 181 + Task 118 task-reviews; merged `origin/main` `752b7ebc` → `f6a789ed` (no conflict); `make install` clean.
- Verified: 181's integration note — `embedded` is a bool kwarg on `resolve`/`_resolve_string`/`has_templates`, decided by
  `param_mode(...) == "embedded"` at `split_params`/`resolve_templates`. Plan D8 adds NO kwarg (declared types ride the
  store), so "one carrier, never a second flag" holds: `auto_parse`/`embedded` stay consumer-side, declarations are
  source-side data. Read `workflow_executor.py:166-181,376-388,484-497`: the host catches `_PREP_RECOVERABLE` itself into a
  `_prep_error` marker and routes it via `post`'s `error_action` — a node-internal path, unlike #768's shell prep raise
  (engine-level). Packet claim 1 is EXECUTED at P0 by I1 (a child with a bad input under `error_action`), not assumed.
- Deviations/surprises: packet says the verify.sh drift set is 12–13 today (plan §0 said 11, #680 re-record lane live) —
  compare SETS at P0 vs PZ.
- Next: launch I1 (Opus · high) with P0 → PA → PC.

## [2026-10-11 11:45] I1 (Opus) — P0 baseline + re-verify (nothing edited)
- Did: plan §0 items 1–7 against merged `f6a789ed`; baselines; §0 greps; `dict(shared)` key read; checkpoint §0 BEFORE probes
  re-executed (isolated HOME `scratchpads/task-120/probes/home`); orchestrator claim 1 EXECUTED.
- Changed: nothing in tree. Scratch (gitignored): `scratchpads/task-120/{baseline-make-test.txt, baseline-verify.txt,
  baseline-capture.txt, probes/}`.
- Verified:
  - §0.1 `resolve(value, context, *, auto_parse=False, embedded=False)` and `_resolve_string(template, context, auto_parse,
    embedded)` exact (`core/templates.py:653,694`). Shape delta: the simple-template leaf is its own function
    `_resolve_simple(template, context, auto_parse)` (`:681-691`) — the typed-root check goes THERE (the only auto-parse leaf).
    §0.2 181's D4 arm (`segment.as_json and not embedded`, `:709`) is in `_resolve_string`'s complex loop, disjoint from the
    simple leaf (an insert is never `is_simple`). §0.3 `resolve_templates`: `inputs:` branch `:279`
    (`resolve(v, context, auto_parse=True)`), embedded branch `:281-285`, dict/list `:287-293`, simple-into-container
    `:296-302`; static `inputs:` merge `:258-261`, resolved merge `:391-392`; locals (`resolution`, `resolved_value`,
    `is_simple_template`) are per-branch assignments, nothing 181-specific shared. §0.4 `has_templates(value, *,
    embedded=False)` `:803`. §0.5 `split_params` still `mode != "body" and has_templates(...)` (`template_resolution.py`
    split_params loop). §0.6 `execution/plan.py:1587` unchanged (`resolve(raw_inputs_template, per_item_context,
    auto_parse=True)`). §0.7 parity `SURFACES` has `embedded_code` (`test_template_parity.py:633`).
  - Greps: `format_param_value` callers `ui/run_node.py:94`, `cli/rerun_display.py:63` (+ the unrelated
    `node_output_formatter.format_param_value` used by `_probe_impl.py:195`) — as planned. `binds_as_text|parses_leaves`:
    definition `template_surfaces.py:85`, `template_resolution.py:19,90,96,292`, `core/workflow/CLAUDE.md:14`,
    `runtime/engine/CLAUDE.md:82`, plus a comment in `runtime/engine/types.py:23`. `\.accepts(` in src: zero.
  - `dict(shared)` keeps a `__*__` key: engine passes the raw store to `resolve_templates` (`engine.py:1748`, proxy built
    after at `:1755`); for a `NamespacedSharedStore`, `__iter__` yields parent keys (`namespaced_store.py:141-143`) and
    `__getitem__` reads `__*__` at root (`:83-86`) — the new key survives either way (read, not executed).
  - Baselines: `make test` 10955 passed / 0 failed (no failing list). `verify.sh` **74 pass / 13 drift / 0 errors** — set in
    `baseline-verify.txt` (02/03, 02/05, 03/05–09 incl. 07-json-error-envelope, 04/03, 04/09d, 04/09e, 10/03, 12/04).
    `capture.py --check`: **29 examples, 5 differing at baseline** (all `examples/error-handling/`: coalesce-mixed-absent-
    failed, failed-node-direct-reference, source-line-heavy-offsets, source-line-multi-output, typo-on-failed-node — the
    `result: {}`/output-failure shape, i.e. #757's declared-output change, pre-existing).
  - Checkpoint §0 BEFOREs all reproduce: typed `topics=tea` validate-only ✓ valid then code-node "expects list" + resume
    line; `count=3.0` → "expects int but received float"; `count=abc` → `WARNING: Cannot coerce`; a-string `{"a":1}` → dict
    error, `02134` → `str:'2134'`, `true` → `str:'True'`; container → `1 fallback`; bad-default ✓ valid, run `n=abc` exit 0;
    envdef `port=abc`/`port=9090` → `port=8080` both; anyin `02134`→int, `1.10`→float, `[1, 2]`→list; parent → child `s`
    gets a dict; parent-batch (`error_handling: continue`) → all 3 items fail incl. `"7"`, `RuntimeError`; parent-inline
    validate-only ✓ valid, run all fail. No drift vs the checkpoint.
  - **Claim 1 (executed, child `child-req` with required `s`,`n`; parent passes `inputs: ${mk.result}` = `{"s":"hello"}` so
    `_validate_child_params` raises in prep): IT ROUTES.** `on-error: rescue` → `call ✗ Failed`, `rescue ✓`, DEGRADED,
    warning `Node 'call' failed — on-error → 'rescue'`. Batch `error_handling: continue` over `[{s,n},{s},{s,n}]` → items 0/2
    succeed, item 1 one error record ("Child workflow … is missing required inputs:"), run DEGRADED. Default routing → run
    fails with the child-input message, exit 1. `error_action: continue` (non-batch) → the host returns action `continue`;
    with no `continue` edge the engine fails "no successor edge matches" — routing by action string works as designed (and
    the progress line shows `call ✓` for that case — pre-existing display quirk, not this task's). The host's own
    `_prep_error` marker path is NOT #768's engine-level prep bypass.
  | Assumed: nothing for P0.
- Deviations/surprises: verify drift is 13 (plan said 11) and capture has 5 pre-existing diffs — PZ compares SETS against
  these files. `_resolve_simple` split (above) is the only 181 shape delta; plan §0.1's adaptation rule covers it.
- Self-checks: n/a (no code). test-reflect: n/a.
- Next: PA.

## [2026-10-11 12:40] I1 (Opus) — PA (grammar, coercer, error, prepare_inputs)
- Did: D1 `TypeSpec.parse_text` + `accepted_noun`/`accepted_text`/`example_text`; D2 `coerce_declared_input` +
  `InputSource` + `_infer_lossless` (lenient `coerce_workflow_input`, `_COERCION_DISPATCH` and the six `_coerce_to_*`
  deleted); D3 `InputTypeError` (one Diagnostic, checkpoint §1 text per source); D5 `prepare_inputs` → `list[Diagnostic]`,
  new order supplied → env → settings → default → required, `input_sources` kwarg; `compile_workflow(...,
  input_sources=)`; `_raise_input_validation_errors` (the collapse) deleted — compile raises one
  `WorkflowValidationError` carrying N diagnostics.
- Changed: `core/{types,param_coercion,exceptions}.py`, `runtime/compilation/{ir_preparation,compile_validation,
  compiler}.py`, `core/CLAUDE.md` (Types/coercion), `runtime/compilation/CLAUDE.md` (input boundary paragraph; the
  child-limitation sentence left for PD). Tests: `test_core/test_param_coercion.py` (coerce_workflow_input section
  replaced by the PA-1…6/10 tables + error tests), `test_runtime/test_prepare_inputs_coercion.py` (`:163` flipped to a
  diagnostic; new `TestResolutionOrder`, `TestEverySourceIsLabelled`, `TestEachProblemIsItsOwnDiagnostic`),
  `test_prepare_inputs_extras.py` + `test_settings_env_integration.py` (tuple → Diagnostic access, no semantic change),
  `test_compiler_interfaces.py` (`SchemaValidationError` → `WorkflowValidationError`; the two debug-log assertions
  "Applying default value…" replaced by `resolved_defaults` assertions — the log line is gone), `test_plan_drift.py`
  `missing-input` row → `WorkflowValidationError` + an added diagnostics-equality assertion (str() of both paths is now
  the same summary, so the old `str` equality alone proved nothing).
- Verified: `make check` green. `make test`: 11267 passed, **2 failed** — `test_cache_analysis_per_id_emission.py::
  {test_predict_cache_keys_includes_sub_workflow_nodes, test_analyze_cache_emits_discrepancy_for_sub_workflow_node_via_
  subprocess}` (see deviations; resolved by PC — re-checked there). Mutation ledger (apply/run/restore, PA tests): drop
  the strip → red; lossless returns any parse → red; string accepts containers → red; drop the `<REDACTED>` mask → red;
  fix line built from a sensitive value → red; default only for optional (old order) → red; settings before env → red;
  number accepts `1e999`→inf → red; placeholder not passed through → red; supplied `None` not treated as absent → red.
  Through `compile_workflow`: two bad inputs → one `WorkflowValidationError`, two diagnostics; supplied `"3"`/`"yes"`
  typed in place in `initial_params` + `resolved_defaults`.  |  Assumed: CLI/runner rendering of the new error (PB
  exercises the real surface; the runner still pre-fills defaults and the CLI still infers until PB).
- Deviations/surprises:
  1. **PA alone is not green**: the child's compile-time `prepare_inputs` (item 0 values, `_compile_sub_workflow`) became
     strict here, and today the parent JSON-parses a workflow step's `inputs:` — so a parent `${draft.response}` holding
     JSON text reaches a child `draft: string` as a dict → container-into-string error. The plan's ordering note foresaw
     this for PD-before-PC; PA triggers it too. PC's D9 (parent stops parsing) fixes it; no change to PC's instructions.
  2. `InputTypeError(name=…)` not `input=…` (no builtin shadowing); `path` derived from source/step instead of a kwarg
     (default → `inputs.<n>.default`, parent+step → `nodes[id=…].params.inputs.<n>`, else `inputs.<n>`) — one rule, no
     caller can pass a contradictory path.
  3. Checkpoint conflict §1.1 vs §1.4: §1.1's stated per-type rule (`→ Pass <accepted_text>: <name>=<example>`) is
     implemented, so §1.4's JSON suggestion reads `Pass a whole number (e.g. 3): count=3`, not `Pass a whole number:
     count=3`. The `call` row keeps its ruled form (`Pass a whole number: "count": 3`). Strings only (importance 1).
  4. `recorded` fix line says `pflow resume <run-id> count=3` — the coercer cannot know the run id. **PB must supply it**
     (resume.py knows it): a small kwarg/threading, or a post-fix of that suggestion; flagged, not decided here.
  5. `parent` sentence: implemented with `step`/`sub_workflow_path` kwargs (checkpoint §1.5 text); the "(here ${item}
     resolved to 'x')" clause needs the parent's template text, which only PD's call site has — PD adds it. Without a
     step the parent source falls back to "…received 'x' from the calling workflow."
  6. Lossless inference (D2.1) is stricter than the plan's sketch in three places: a JSON-string token (`"x"` with quotes)
     stays the text (the plan's comparison would strip the quotes); `-Infinity` stays text (`allow_nan=False`); and the
     comparison uses `ensure_ascii=False` so `["é"]` types (the plan's `json.dumps` default would keep it text).
  7. An unknown/empty declared type (only reachable by bypassing the schema) behaves as `any`, like untyped; `object`/
     `array` text rejects `NaN`/`Infinity` (not JSON); `number` rejects `1e999` (overflows to inf); whitespace stripped is
     ASCII only (decision (b) "strict ASCII").
  8. One unexplained red during the mutation batch (an unmutated run reported `1 failed`); 9 clean re-runs since —
     treated as a host-load flake, noted.
- Self-checks: fully-happy + test-reflect (directed): resolved in the [15:10] self-checks entry (PA ledger re-run clean; no PA test deleted).
- Next: PC.

## [2026-10-11 14:05] I1 (Opus) — PC (resolver rule + engine sites) · ENGINE CONTACT
- Did: D8 — `templates.DECLARED_INPUT_TYPES_KEY` + `_declared_typed`; the `auto_parse` leaf (`_resolve_simple`) skips a
  declared root, judged by the winning `??` operand (`_evaluate` now returns it); `_walk` rebuilt on one `_step` and
  skips mid-path parsing under a declared root (root-wide); `unparsed_declared_text` (W5 reason); `ir_schema.
  declared_input_types`; `CompiledWorkflow.input_types` filled by the compiler and installed/restored by
  `WorkflowEngine.run` (beside the prompt-cache map), `create_planner_shared`, and the runner's root store. D9 —
  `parses_leaves(cfg, key, subkey)` + `_CONSUMER_TYPES_LEAVES` (`shell.env`, `http.headers`, `workflow.inputs`) +
  `TemplateConfig.text_input_keys` (code keys whose annotation reads `string` via `extract_code_annotation_type`);
  `binds_as_text`/`_BINDS_AS_TEXT` deleted; `_bind_locally` at the two context merge points; the
  simple-into-container parse folded into the one `resolve` call; `resolve_batch_items` on the one rule (separate
  `try_parse_json` deleted); `validator._enumerate_child_calls` resolves without auto-parse; W5 —
  `classify_unresolved_references` path_error gains `text_not_parsed`/`unparsed_text`, rendered with the §1.14 reason.
- Changed: `core/{templates,ir_schema,diagnostic_render}.py`, `core/workflow/{template_surfaces,validator}.py`,
  `runtime/engine/{engine,types,template_resolution,template_errors,batch_executor}.py`, `runtime/compilation/
  compiler.py`, `execution/{runner,plan}.py`; CLAUDE.mds: `core` (Template language bullet), `core/workflow` (row
  removed), `runtime/engine` (parses_leaves paragraph), `runtime` (reserved-key row + traversal sentence). Tests: new
  `tests/test_core/test_templates_declared_inputs.py` (PC-1/2 + W5 helper), new `tests/test_runtime/
  test_declared_input_resolution.py` (PC-4/5/6/7/9/10/12/13), `test_plan_drift.py::
  test_plan_and_engine_hand_a_batched_child_the_same_text_inputs` (PC-8); flipped `test_batch_node.py::
  test_json_object_fails_with_type_error` ("got str" → "got dict": JSON-object text is now parsed like any simple
  template's, then fails the shape check) and `test_node_wrapper_json_parsing.py::test_wrong_json_type_raises_error`
  (see deviation 1).
- Verified: `make check` green; `make test` **11317 passed, 0 failed** (PA's two reds now green, as predicted).
  `capture.py --check` 29 / 5 differing — the same 5 as P0. `verify.sh` (pre-#680 base) drift SET identical to P0's 13.
  **P0's verify.sh numbers are pre-#680 base, superseded** (orchestrator: main is 87/87 after `5a93929d`; PZ compares
  against the green base). Mutation ledger (PC tests): `_walk` parses under a declared root → red; leaf parses a
  declared root → red; engine.run install dropped → red (the nested child `t: string` row); runner root-store install
  dropped → red (`-o` row); `_bind_locally` at the resolved merge → red; at the static merge → red; `("workflow",
  "inputs")` / `("http", "headers")` removed → red each; `text_input_keys` ignored → red; planner per-item
  `auto_parse=True` → red; W5 reason dropped → red; declared-input message dropped → red; shape error dropped → red.
  Real surface (`uv run`-equivalent `.venv/bin/pflow`, isolated HOME): `parent-int` (emit `{"a":1}` → child `s: string`,
  `n: 7`) → child receives `str:'{"a":1}' int:7` (BEFORE: a dict); `a-string text=' {"a":1}'` → `str:' {"a":1}'`;
  `obj-miss` → the §1.14 reason (output below); in-tree `examples/nested/document-processor.pflow.md` (parent→child
  `string` binding) runs (`HELLO`); `examples/core/stateful-loop-tournament.pflow.md` (looped child, carried array)
  runs (`Winner: ada`). `-o d.payload.a` on a declared object → "output key 'd.payload.a' not found. 'd.payload' is a
  string…"; `-o d.payload` → the text.  |  Assumed: MCP paths inherit through the runner (not driven here — PB).
- Deviations/surprises:
  1. **Silent-failure fix beyond the plan**: folding the simple-into-container parse made a well-formed JSON array into a
     dict param (or the reverse) reach `validate_resolved_type`, which returned None for a wrong-shape container — the
     plan's "still an error, now the accurate one" was false. Added `build_shape_error_message` (wrong container shape)
     and `build_declared_text_error_message` ("reads input 'v', declared `- type: string` — a declared input is never
     JSON-parsed … declare `- type: object`", PC-6's "names the declared input"); the old wording called well-formed
     JSON "malformed".
  2. **Mid-build CLI state (until PB):** the CLI still infers, so `pflow wf text='{"a":1}'` on a declared `string` now
     fails at the boundary ("received {"a": 1} from the command line") — before, it was stringified (re-spaced). PB's raw
     parser fixes it; one PR, so main never sees it. Same for the checkpoint probes `a-string`/`container`: they hit
     the boundary error, not the AFTER text, until PB.
  3. `execution/plan.py` per-item inputs: took the plan's logged-fallback form `resolve(raw, ctx)` (auto_parse off), not
     a `resolve_templates(...)["inputs"]` reuse — `resolve_templates` raises in strict mode on an unresolved item, while
     this function reports a per-item WARNING; reusing it would need a try/except around a second error shape. PD types
     each item through `prepare_inputs`. (The plan put `:1584-1595` under PD but PC-8 needs the parse rule; I changed
     only the parse flag.)
  4. W5 placement: `text_not_parsed` lives on the `unresolved_references[]` entry (not the diagnostic's top context),
     with `unparsed_text` (the text, `<REDACTED>` for a sensitive root) so the renderer can build the nest example from
     the real value. Rendered:
     `→ 'd.payload' is text ('{"a":1}') — a declared input is never JSON-parsed, so there is no field 'a' to read.`
     `  Nest the object in the input (`{"payload": {"a": 1}}`), or parse the text in a code step (`json.loads(payload)`).`
  5. PC-6's third row tests the array-into-dict direction (same code path as dict-into-list).
- Self-checks: fully-happy + test-reflect (directed): resolved in the [15:10] self-checks entry (2 deleted, 1 replaced, 1 added).
- Next: mid-task review #1 (engine contact) on PA+PC; then PB → PD. Open items handed to PB: the `recorded` fix line's
  `<run-id>` (PA deviation 4); `prompt_cache_analysis/context.py:52` still names the deleted `coerce_workflow_input`
  (PB rewords it per D6). To PD: the parent fix-line clause "(here ${item} resolved to 'x')" (PA deviation 5).

## [2026-10-11 15:10] I1 (Opus) — PA + PC self-checks (directed: fully-happy + test-reflect)
- Did: reviewed the PA+PC diff for loose ends; applied `.claude/commands/test-reflect.md` to every PA/PC test written or
  flipped; re-ran both mutation ledgers on a fixed harness.
- Changed: tests only — `test_core/test_templates_declared_inputs.py`, `test_runtime/test_declared_input_resolution.py`,
  `test_execution/test_plan_drift.py` (one test added). No `src/` change.
- Verified: `make check` green; `make test` 11319 passed, 0 failed. **The mutation harness had a real flaw**: it restored
  the file with `mv`, so a same-second, same-size restore (the env/settings swap mutant) left the MUTANT's `.pyc` valid.
  Later "kills" in the same batch could have been that stale mutant, which also explains PA's unexplained red (PA
  deviation 8, now RESOLVED: not a flake). Fixed the harness (`PYTHONDONTWRITEBYTECODE=1`, purge the module's `.pyc`
  before and after, no `-x`, counted results), purged every `__pycache__` in `src/` and `tests/`, and re-ran both
  ledgers. **PA: 16/16 killed** (counts 1–14 failed each), adding three new mutants: a quoted JSON string is typed;
  `any` is inferred from every source; a failed coercion passes its value through. **PC: 23/23 killed**, adding: a `??`
  chain judged by any operand rather than the winner; the engine restore dropped; `inputs:` leaves always parsed; the
  container fold dropped; inline batch items not parsed; complex-template batch text re-parsed; the per-item store
  dropping the key (sequential AND parallel); the compiler not filling `input_types`; the planner install dropped.
- Self-checks: fully-happy — doubts raised and resolved:
  (a) **The planner's `create_planner_shared` install had NO test** (its mutant survived, 108 passed). Added
  `test_plan_cache_key_reads_a_declared_input_as_the_run_does`: run once with a cached code step reading a declared
  `string` that holds JSON text, then plan → `cached`. Without the install, the planner hashes a dict and predicts a
  re-execution. Mutant now killed.
  (b) The wrong-shape error (PC deviation 1) now also fires for a real dict/list VALUE (not only parsed text) going into a
  param declared with the other container type — before, it passed silently. Surveyed the node interfaces:
  `http.body` is `dict|str` (a union, never checked), and the other container params would fail inside the node anyway.
  Kept.
  (c) `validator._enumerate_child_calls` no longer parses: an inline batch item holding JSON TEXT under a whole-map
  `inputs: ${item}` is now reported as a shape error statically. The runtime already rejected it ("resolved to str,
  expected dict"), so validator and runtime now agree. No test pins this yet; it is PE's literal-child-values area
  (PE-5), flagged for PE.
  (d) `TemplateResolver.resolve_nested` has no remaining `src/` caller (the facade stays, by `core/CLAUDE.md`'s
  "permanent facade" rule). Noted, not removed.
  test-reflect (directed):
  - deleted `TestTheLeaf::test_complex_templates_are_text_either_way` (pre-existing behaviour with no key; duplicates
    the template suite).
  - deleted `TestConsumerAndSourceRules::test_shell_env_stays_text` (Task 118's `test_shell_env_binding` already pins
    `env:` as text, mutation-verified).
  - replaced `test_loop_carry_keeps_upstream_parsing`: a carried value's root is the producing step, never the declared
    input, so the map could not affect the test. The carry lands on the same resolved-`inputs:` merge point that
    `TestShadowing::test_a_steps_resolved_inputs_key_is_local_for_its_siblings` kills.
  - added in its place `test_every_batch_item_store_carries_the_declarations` (sequential × parallel × `string`/`any`
    presence pair, real run) — the per-item `dict(shared)` copies are where protection would silently drop, and both
    copy sites are mutation-killed.
  - deepened two shadowing rows (the first version could not see `_bind_locally` — the local value was already a dict,
    so the mid-path parse never ran). Now the local holds JSON text one level down; both merge points are killed.
  - kept unchanged and mutation-verified: the grammar / typed-value / lossless / idempotence / placeholder / error tables
    (PA) and the leaf, walk, W5, consumer, structured-param, install/restore, `-o` and parity rows (PC).
- Next: hand back; mid-task review #1, then PB.

## [2026-10-11 15:30] task-orchestrator — PA+PC accepted; committed; main merged
- Did: read I1's P0/PA/PC/15:10 entries; accepted deviations PA 2–7 and PC 1, 3–5 (all ≤2/5, plan-consistent); committed PA+PC
  as one commit `d9d90332` (PA alone is red on 2 tests — PC fixes them); merged `origin/main` (#680 `5a93929d`, #741
  `90dc9b01`) → `f8ebc68f`.
- Verified: on `f8ebc68f` `make check` exit 0; `make test` 11330 passed; Task-159 `verify.sh` **87 passed / 0 drifted / 0
  harness errors** (the post-#680 green base — PA+PC introduce no baseline drift; PZ compares against 87/87).
- Deviations/surprises: PC deviation 1 adds two runtime messages outside CP-1 (wrong container shape; "reads input 'v',
  declared `- type: string`") — closes a silent pass the plan's fold would otherwise open (ORCHESTRATION "a gap your change
  widens"); carried to the user at the PF screenshot checkpoint as new text. CLI temporarily stricter until PB (one PR).
- Self-checks: I1 fully-happy + test-reflect (directed) done — see [15:10]; mutation harness bytecode-reuse bug found and
  fixed by I1, both ledgers re-run clean (PA 16/16, PC 23/23).
- Next: mid-task review #1 (engine contact) on PA+PC, gate-run by I1 (it holds the code); then a FRESH Opus implementer
  for PB → PD (I1 at ~480k tokens, past the plan's ~350k rotation point).

## [2026-10-11 16:20] I1 (Opus) — mid-task review #1 (engine contact) on PA+PC, gate-runner
- Did: dispatched the pflow fan-out (codex) with three lenses, each with its own target per plan §4 PC, over `git diff
  f6a789ed..d9d90332` → `scratchpads/task-120/mid-review-1.md` (exit 0, 328 s, Coverage: 3/3 lenses received, no failed
  lens). Read the report in full; verified each finding against code; fixed all 6 with tests.
- Changed: `core/{templates,exceptions,diagnostic_render,prompt_cache}.py`, `runtime/engine/{engine,loop_control,
  batch_executor,template_resolution}.py`, `execution/{plan,formatters/success_formatter}.py`, `runtime/CLAUDE.md`
  (consumer rule); tests in `tests/test_runtime/test_declared_input_resolution.py`.
- Dispositions:

  | # | Lens · sev | Finding (verified at) | Disposition |
  |---|---|---|---|
  | 1 | impact · Critical → **Warning** | `-o <path> --output-format json` re-parses the selected value (`success_formatter.py:234` `parse_json_or_original`) — a declared input's `"1.10"` emits `1.1` | **Fixed**: `TemplateResolver.reads_declared_input(raw_path, ctx)` (raw-path facade, beside `variable_exists`); the formatter skips the parse for a declared root. Downgraded: one output surface, explicit `-o` into an input. Test: real CLI, `object` → `"1.10"` with `any` → `1.1` as the presence half. |
  | 2 | impact · Warning | Prompt-cache map built BEFORE the declarations are installed (`engine.py` run; `plan.py:600`) — prewarm model resolution reads unprotected | **Fixed**: engine installs the map first, then builds, and restores it if the build raises (the trace/prompt-cache installs keep "build first"); planner reordered. Tests: build sees `{"s": "string"}` (engine and planner); a raising build leaves the outer map in place. |
  | 3 | silent · Critical | Cache chunk `${d.payload.rules}` into declared-object text → `_CHUNK_ABSENT` → chunk + prose silently dropped (`prompt_cache.py:170-174`) | **Fixed, different fix**: loud ONLY for the declared-text miss, at the one renderer `render_cache_chunks` (both the hash and the prepare sites); an absent branch is still skipped; the analyzer's direct `_resolve_chunk_value` use is unchanged (offline analysis). |
  | 4 | silent · Critical | Inline `batch.items: ["${d.payload.a}"]` keeps the literal (`batch_executor.py:118` took `.value`) | **Fixed**: the same check in `resolve_batch_items` (both branches); an unresolved inline item for an ABSENT node stays literal as before (pinned). |
  | 5 | silent · Critical | `loop.while: ${d.payload.again}` → unresolved → `None` → loop stops "normally" (`loop_control.py:145`) | **Fixed**: `evaluate_loop_condition` raises for the declared-text miss before the absent→stop rule; a real field of the same input still drives the loop (presence row). |
  | 6 | feature-interactions · Warning | The type-error message blames the first declared `??` operand, not the winner (`template_resolution._declared_input_read`) | **Fixed**: judged by the winning operand via `lookup` (a literal winner → not declared). Three-row test (upstream wins / literal wins / declared wins), both mutants killed. |
  | S1 | impact · Suggestion | Add regressions for JSON-mode `-o` and prewarm setup | **Done** (rows 1, 2). |

  Mechanism for 3–5 (one rule, three consumers): `templates.declared_text_misses(resolution, ctx)` (data only) +
  `exceptions.DeclaredInputTextError(PflowError)` (`retriable = False`; `raise_for(resolution, ctx, where=, node_id=)`)
  + `exceptions.declared_text_reason(...)` — the ONE home of the §1.14 reason text, now also used by the W5 renderer
  (`diagnostic_render._format_unparsed_text`). Message, e.g. `Node 'step' loop condition reads ${d.payload.again}:
  'd.payload' is text ('…') — a declared input is never JSON-parsed, so there is no field 'again' to read.` + the fix as
  the suggestion.
- Verified: `make check` green; `make test` **11340 passed, 0 failed**. Mutation (fixed harness, counted): each fix's
  guard removed → 1 failed each (loop raise, batch raise, chunk raise, `-o` guard, engine except-restore, engine install
  moved after the build, planner install moved after the build, the blame's `lookup` and literal-winner branches). |
  Assumed: the prewarm scenario's token thresholds (pinned through the build's store view, not a real prewarm token
  count).
- Deviations/surprises: a NEW exception class (`DeclaredInputTextError`) is my call (importance 2: reversible, one rule,
  narrow trigger); the alternative — reusing `LoopConditionError` for loops and vanilla `ValueError`s at the batch and
  chunk sites — splits one rule across three error shapes and adds vanilla exceptions. **Not widened (pre-existing class,
  follow-up for the orchestrator):** those three consumers still read ANY other miss on a PRESENT root (a typo like
  `${d.nope}` in `loop.while`, inline items or a chunk) as absent — silent before this task too; PE's validator covers
  the statically certain shapes only.
- Self-checks: fully-happy: clean — the one judgment call is above. test-reflect: not separately directed for the review
  fixes; every new row is mutation-verified, each with its presence half.
- Next: hand back (no commits); then PB.

## [2026-10-11 16:35] task-orchestrator — mid-task review #1 dispositions accepted; rotate to I2 for PB → PD
- Did: read [16:20]; accepted all six dispositions. Ruled I1's `DeclaredInputTextError(PflowError)` (2/5, reversible):
  ACCEPTED — one rule, one structured error (root CLAUDE.md "raise PflowError subclasses"); the completion gate's
  simplicity lens re-judges where `declared_text_reason` lives.
- Follow-up recorded for the task-review (pre-existing, NOT widened, not built): `loop.while`, inline `batch.items` and
  `## Cache` chunks read ANY other miss on a PRESENT root (`${d.nope}` typo) as absent — silent before this task.
- Rotation: I1 at ~557k tokens → fresh Opus · high I2 for PB → PD, briefed from plan + this log + I1's successor list
  (recorded below so it survives I1).
- I1's successor brief (beyond `<run-id>`, the "(here ${item} resolved to 'x')" clause, `context.py:52`): child inputs
  arrive as TEXT at run time until PD (parent stopped parsing; child compile types item 0 only, `exec` seeds raw values
  over it); default errors are labelled `argument` until PB's placeholder change; thread `step`/`sub_workflow_path`
  into `prepare_inputs` as kwargs rather than rebuilding diagnostics; `compile_workflow(ir, reg, {})` does not mutate an
  empty caller dict (PB-10 needs non-empty params); mutation testing: `PYTHONDONTWRITEBYTECODE=1` + purge `.pyc`; fixture
  traps: a declared `## Outputs` name equal to a step id overwrites `shared[step]`, the LLM mock's text response is JSON
  text; zsh does not word-split unquoted `$VAR`.
- Next: commit review fixes; launch I2.

## [2026-10-11 17:40] I2 (Opus) — PB (entry sites: runner, CLI, MCP, analyze, web preflight)
- Did: D7 `parse_workflow_params` → raw text (`infer_type` kept for `pflow probe` only); D6 `_fill_declared_defaults` →
  `_fill_placeholders` (never a real default — f₂ fixed); `validate()` checks the supplied values; D4 `input_sources`
  on `WorkflowRunner.run/validate/plan/preflight` → `compile_workflow` → `prepare_inputs` (CLI stdin → `stdin`, resume
  replays → `recorded`, MCP → `call`); `analyze(..., input_sources=)` types supplied values first and raises
  `WorkflowValidationError`; analyzer synthetic contexts carry `DECLARED_INPUT_TYPES_KEY`; `rerun_display.py` + its
  tests + the dead `ctx.obj["execution_params"]` write deleted; untyped-input hints → `any`; context.py:52 reworded.
- Changed: `cli/{param_parsing,commands/run,commands/resume,commands/analyze_cache,commands/_probe_impl}.py`,
  `cli/rerun_display.py` (deleted), `execution/runner.py`, `execution/formatters/{discovery,workflow_save}_formatter.py`,
  `runtime/compilation/{ir_preparation,compile_validation,compiler,__init__}.py`, `core/exceptions.py`
  (`InputTypeError.resumed_run` + `located()`), `core/prompt_cache_analysis/{analyze,context,token_estimation}.py`,
  `mcp_server/services/execution_service.py`, `ui/{server,run_node}.py`, `nodes/file/delete_file.py` (comment);
  CLAUDE.md: `cli` (rows), `runtime/compilation` (check_supplied_inputs sentence); `.claude/agents/{pflow-codebase-searcher,
  review-agent-ux}.md` + codex sync. Tests: new `tests/test_integration/test_declared_input_entry_points.py` (PB-1…8, 10;
  42 incl. one `e2e` real pipe); UI run/resume preflight rows in `test_ui_interaction_server.py` (PB-9); probe row in
  `test_probe.py` (PB-11); flipped `test_direct_execution_helpers.py` (parser → text; `TestFormatParamValue` moved here
  from the deleted file), `test_validate_only.py` (`TestValidateOnlyChecksSuppliedValuesOnly`),
  `test_prepare_inputs_extras.py` (`TestValidateOnlyGap` → `TestValidateOnlyCatchesRootExtras`, #297 half closed),
  `test_run_node.py` round trip (now parser → `prepare_inputs`, + a `02134` string row), `test_workflow_resolution.py`
  (`test_type_inference_for_parameters` → `test_parameters_reach_execution_as_the_text_typed`), docstrings in
  `test_runner.py`, `test_meta_inputs.py`, `test_run_tailer.py`, `test_delete_file.py`, `test_prepare_inputs_coercion.py`.
- Verified: `make check` rc 0; `make test` **11324 passed** (baseline 11340 − the deleted `test_rerun_display.py` + new
  rows); Task-159 `verify.sh` **87/0/0**. Mutation ledger (harness: content restore, `PYTHONDONTWRITEBYTECODE=1`, pyc
  purged before/after, counted): 23/23 killed after two additions — parser infers; probe stops inferring; real defaults
  pre-filled; validate skips the supplied check; no supplied-path filter; stdin unlabelled; resume unlabelled; resume
  labels overrides `recorded` (survived → added `test_an_override_is_a_command_line_argument…`); run id not threaded;
  `located` drops it; UI resume unlabelled / no run id; MCP unlabelled; MCP analyze re-wrapped; analyze skips the check /
  keeps raw values; synthetic store / both per-ref resolvers without declarations (two survived → added the
  `resolve_ref_value[_in_workflow]` row); CLI analyze `PflowError` unrouted; envelope message from `str(e)`; duplicate
  `Suggestion:` line; extras-before-per-input order. Real surface (isolated HOME `scratchpads/task-120/probes/home`,
  `.venv/bin/pflow`): §1.1 `typed topics=tea` validate-only AND run → the §1.1 block, exit 1, no resume line; §1.3 two
  blocks; `count=007 flag=YES` → `int:7 bool:True`; §1.2 env `port=abc` → env row, `port=9090` → 9090, `port=1` beats env;
  default `abc` → the default sentence at `inputs.n.default` (run); `text=02134|1.10|TRUE|1e3|{"a":1,"b":[1,2]}| 42` →
  byte-identical, piped stdin agrees; stdin `abc` → the stdin row; §1.13 any `02134`→str, `1.10`→str, `42`→int,
  `true`→bool; §1.10 lenient-era trace (hand-edited `meta.inputs.count="abc"`) → `Override it: pflow resume <real id>
  count=3`, and that command (with `count=4`) completes; resume `zip=0042` → `0042`; MCP `{"count": 3.0}` → "in the
  call's parameters" + `"count": 3`; `{"topics": null}` → requires input; §1.12 `topics=tea BOGUS=1 --validate-only` →
  both, in the checkpoint's order; §1.15 analyze-cache text + `--format=json` envelope (message + fix), required input
  omitted → analyses; MCP analyze → `WorkflowValidationError`.  |  Assumed: the web form's spawn (`/api/run` driven via
  the test client only — the spawn argv carries the raw token, pinned).
- Deviations/surprises:
  1. **Run-id threading** (PA dev 4): `resumed_run` kwarg on `compile_workflow` → `_prepare_compilation` →
     `prepare_inputs`, and `InputTypeError.located(resumed_run=)` builds the placed copy where the boundary catches it —
     the coercer's signature stays `(name, type, value, *, source)`. The runner derives the id from `resume_source` (run,
     plan); `preflight(..., input_sources=, resumed_run=)`. Rejected: post-fixing a `<run-id>` placeholder in the
     rendered suggestion (string surgery on frozen diagnostics, two catch sites). PD reuses `located()` for
     step/child-path/template (importance 2).
  2. **UI resume pre-flight labels its replay too** (`ui/server.py` resume arm: `input_sources` all `recorded` +
     `resumed_run`) — the plan said "nothing" for `ui/server.py`, which is right for `/api/run` (arguments) but the
     resume arm replays recorded values; unlabelled, an `any` recorded `"42"` would be inferred there and a lenient-era
     error would say "from the command line". Pinned (UI test + 2 mutants).
  3. **One stdin routing site**: `execute_json_workflow`'s second `_route_stdin_to_params` was a no-op on both callers
     (run pre-routes; resume passes no stdin) — deleted; `_route_stdin_to_params` returns the routed name;
     `execute_json_workflow(..., input_sources)` is the explicit channel (resume passes its `recorded` map).
  4. **`check_supplied_inputs`** (new, `ir_preparation`): `prepare_inputs` over the supplied values with placeholders
     for the rest — the one helper behind `validate()` and `analyze()`. It returns only problems whose path is a
     supplied name, so a declaration problem both layers see (two `stdin: true`) is reported once (pinned). Also moved
     the undeclared-extras check AFTER the per-input loop in `prepare_inputs` (checkpoint §1.12 order: `topics` then
     `BOGUS`) — affects run output order too.
  5. **`analyze()` refuses undeclared parameters** (D6) — 15 analyzer tests passed params their IR never declared
     (`items`, `content`, `concept`, `source`): fixtures now declare them (production-shaped; a real workflow must).
     `test_sub_workflow_projection_node_ref_does_not_resolve_from_root_parameter`'s premise (an undeclared root param
     colliding with a node id) is now refused up front — rewritten to assert that refusal + keep its memo-sourcing
     assertion with a declared param.
  6. **analyze-cache JSON envelope**: the input-error path puts each diagnostic's message and first fix in
     `error.message` / `error.suggestion`; `_emit_error` no longer echoes a duplicate `Suggestion:` line when a rendered
     `stderr_text` is given (affects no prior caller). My first cut routed every `_try_or_emit_diagnostic` error the same
     way and drifted Task-159 case `03/07-json-error-envelope-unknown-workflow` (suggestion added) — reverted to keep the
     old path byte-identical; baseline back to 87/0/0. `_analyze_or_emit` extracted (ruff C901).
  7. **Files outside PB's list, forced by the deletion/parser**: `.claude/agents/{pflow-codebase-searcher,
     review-agent-ux}.md` (+ `make sync-claude-assets`) dropped `cli/rerun_display.py` (else `test_agent_references`
     fails — PF still owns the searcher def's new-names edit); `test_run_node.py` round trip + `ui/run_node.py` docstring
     (D13 — the parser change broke the pin); `test_workflow_resolution.py`'s inference test.
  8. Analyzer limit: the workflow-scoped per-ref resolver applies the ROOT's declarations only to root parameters; a
     child's analysis parameters are the parent's resolved values, which nothing types in analysis (PD types them at run).
  9. For PE/PZ, observed not changed: checkpoint §1.13 `[1, 2]` on an `any` input shows `list` (not `str:'[1, 2]'`) in the
     `anyin` probe because its code step's `data: Any` input auto-parses an `any` root (plan §8 accepted cost (b)); the
     boundary keeps it text. `bad-default`/`container` `--validate-only` stay ✓ until PE (D11 a/b).
- Self-checks: fully-happy + test-reflect: pending orchestrator direction.
- Next: PD.

## [2026-10-11 18:55] I2 (Opus) — PD (the sub-workflow boundary, per item, routable)
- Did: D10 — `workflow_executor.type_child_inputs(child_ir, child_params, *, step, sub_workflow_path)`: the child input
  boundary, called in `prep` for EVERY call (each batch item) = `prepare_inputs` with `parent` labels, the step placement
  and settings.env; raises `WorkflowValidationError` (one Diagnostic per problem). `_validate_child_params` deleted; the
  `exec` seeding loop over the cached compile's `resolved_defaults` + the KNOWN LIMITATION comment deleted (#188);
  `_PREP_RECOVERABLE` += `WorkflowValidationError`; the prep marker carries `_prep_diagnostics`, `exec`'s short-circuit
  builds a `child_failure` bundle from them; bundle key `diagnostics` (list) for input AND template failures, reader
  also takes the legacy `template_diagnostic`; a diagnostic already placed at the parent step is not re-wrapped
  "In step '…' sub-workflow:". `prepare_inputs(step=, sub_workflow_path=)` (private `_Caller`) places every problem
  at `nodes[id=<step>].params.inputs.<name>` and names the child in missing/unknown-input messages. Planner: each batch
  item typed through the same function (`_resolve_per_item_sub_workflow_inputs`), a non-batch child typed before its
  compile, a batch child compiled on type-shaped placeholders; child compiles (runtime + planner) labelled `parent`.
- Changed: `runtime/workflow_executor.py`, `runtime/compilation/{ir_preparation,compile_validation}.py`
  (`_load_settings_env` → public `load_settings_env`), `core/exceptions.py` (`located(step=, sub_workflow_path=)`;
  `parent` fix line uses `accepted_noun` per checkpoint §1.5), `execution/{executor_service,plan}.py`; CLAUDE.md:
  `runtime` (Nested workflows), `runtime/compilation` (limitation sentence → `type_child_inputs`), `execution` (planner
  limits); `.claude/agents/review-validation-consistency.md` (+ codex sync; named the deleted method). Tests: new
  `tests/test_runtime/test_workflow_executor/test_child_input_boundary.py` (PD-1 seq×parallel, 1b env/settings/default
  seq×parallel, 1c, 2, 3, 4, 5, 7); `test_plan_drift.py` +3 (PD-6 typed per item against the run's memo, bad item 0 under
  `continue`, non-batch placed message) and the per-item test's new signature (now asserts `n` typed `7`);
  `test_compile_once_regression.py` + `test_each_batch_item_is_typed_by_the_child_on_its_own` (the deepening — the
  string test cannot see a leak); flipped `test_workflow_executor_comprehensive.py` (missing/extras/no-decl/None-inputs/
  required true|false → structured diagnostics via prep or `type_child_inputs`), `test_prep_error_action.py:156,219,276,352`
  (+ bundle paths), `test_workflow_executor.py:204`, `test_failed_node_invariant.py:1887` (writer key); docstrings in
  `test_integration.py`, `test_workflow_name.py`.
- Verified: `make check` rc 0; `make test` **11342 passed**; `make test-e2e` 54 passed / 2 skipped; Task-159 `verify.sh`
  **87/0/0**. Mutation ledger (same harness): 15/15 killed after two additions — prep skips typing; input error not
  recoverable; marker drops diagnostics; exec builds no bundle; labelled `argument`; no step placement; no per-call
  fallbacks; placed diagnostic re-wrapped; legacy key unread; writer back to the old key; planner skips per-item typing;
  settings not consulted per call; child message says "this workflow"; planner batch compiles with item 0 and non-batch
  planner untyped (both survived → added the bad-item-0 and placed-message plan rows, now killed). Real surface (isolated
  HOME): §0 `parent-batch` → items 0/2 run (`7`/`9`), item 1 one error record with the §1.5 sentence, `At:
  nodes[id=call].params.inputs.n`, `Sub-workflow: ./child.pflow.md`, run DEGRADED exit 0; `parent` (emit `{"a":1}` → child
  `s: string`, `n: "7"`) → `str:'{"a":1}' int:7`; a non-batch bad value → the §1.5 non-batch block, exit 1, resume hint
  kept; `--dry-run` of the batch with a cached emitter → `show 1/3 would execute` (items 0/2 cached against the run's
  memo) + the item-1 WARNING with the same sentence; `parent-inline` runtime → per item, routable.  |  Assumed: nothing
  beyond the checkpoint gaps below.
- Deviations/surprises:
  1. **NEEDS YOUR CALL — the §1.5 clause "(here ${item} resolved to 'x')" is NOT built.** PA dev 5 / the handoff said PD's
     call site has the template text; it does not: the engine sets `node.params` to the RESOLVED map before `prep`
     (`engine.py::_execute_single_node`), the raw templates live only on `TemplateConfig`, which the node never sees.
     Options: (A) the compiler stamps the authored `inputs:` on the `WorkflowExecutor` instance (beside `node_id`,
     `compiler.py` ~5 lines + `InputTypeError(template=)` + one test) — outside PD's file list; (B) ship without the clause
     (the sentence already shows the received value and the path names the step's `inputs:` key). Recommendation: **B**
     (importance 2) — the clause repeats what the message and `At:` already say; A adds a node-type-specific compile stamp
     for one sub-clause. Today's fix line: `→ Pass a whole number from the parent.`
  2. **Batch-record rendering repeats the headline** (`[1] Step 'call' passes …` then the same sentence again above `At:`)
     — `execution/formatters/batch_errors.py::_format_child_failure_lines` renders every child diagnostic's message
     under the item headline (pre-existing shape: other child failures repeat it with a provenance prefix). The §1.5
     AFTER shows it once. A 3-line fix (skip a rendered first line equal to the headline) is in a file outside PD's list
     — not made; handed up (importance 1).
  3. **Bundle key `diagnostics` (a list), not the plan's single `diagnostic`** — a child with two bad inputs has two
     Diagnostics; one key would drop the second from JSON/MCP (silent-failure class). The reader still takes the legacy
     `template_diagnostic` (pinned). Importance 2, decided here.
  4. **`create_planner_shared` NOT changed** (plan D10: drop the `resolved_defaults` overwrite). Executed reasoning:
     `stages/discrepancy/predict.py:479-480` compiles a COPY of walker-resolved child params and relies on that overwrite to
     type them, so dropping it would mis-key predictions. The item-0 leak is fixed at its root instead: no planner child
     compile coerces per-item values any more (batch → placeholders, whose `resolved_defaults` are empty; non-batch → typed
     inputs, also empty; per-item values typed by `type_child_inputs`). Pinned by the PD-6 memo-parity row and the D12 mutant.
  5. **A batch child compiles on type-shaped placeholders in the planner** (new `_prepare_sub_workflow(per_item=True)`;
     `_effective_child_inputs` folded away; untyped/`any` placeholder is now the placeholder string, not `None`, which the
     strict boundary would read as a missing required input). A bad item 0 under `continue` is a per-item WARNING, as at
     run time (the R10 twin); an item that fails its types is still planned with its resolved values (the existing "Runtime
     will reject this item" convention keeps the per-item output zip intact) — so the plan counts its child cost.
  6. **Child-boundary messages name the child**: `./child.pflow.md requires input 'n': …` / `Unknown input 'x' — not
     declared by ./child.pflow.md.` (root text unchanged: `Workflow requires input …`, `… by this workflow.`). Replaces
     the deleted `Child workflow '…' is missing required inputs: … You provided: …` text; the suggestion lists the inputs.
  7. **`WorkflowValidationError` in `_PREP_RECOVERABLE` also routes a saved child that fails to load**
     (`WorkflowManager.load` raises it, `manager.py:287`) — the plan said prep raises it only from the boundary. Now
     consistent with a file child's `MarkdownParseError`, already recoverable; comment says so. Not separately tested.
  8. PD-2's "no resume hint for a step-1 failure": not asserted — `has_resumable_step()` is true for ANY failed step
     (`workflow_trace.py:1557`), and the checkpoint keeps the hint for child-input failures; the no-hint half is PB's
     pre-execution row.
  9. Settings.env is loaded per call (`load_settings_env`, ~8 µs uncached on an empty settings file — measured).
- Self-checks: fully-happy + test-reflect: pending orchestrator direction.
- Next: hand back (decisions: dev 1 clause A/B; dev 2 formatter tweak).

## [2026-10-11 19:40] I2 (Opus) — PB + PD self-checks (directed: fully-happy + test-reflect) and the ruled formatter fix
- Did: PD dev 2 (authorized) — `batch_errors._format_child_failure_lines(..., headline)` drops a child diagnostic's
  message line when it IS the item's `[idx]` headline and dedents its detail lines, so a batch record reads as §1.5
  (`[1] <sentence>` / `item:` / `At:` / `Sub-workflow:` / `→`); PD dev 1 = B (clause not built) pinned as today's fix
  line. Then the two self-checks below.
- Changed: `execution/formatters/batch_errors.py`, `execution/plan.py` (per-item WARNING `source="planner"`, like its
  sibling warnings); tests: `test_child_input_boundary.py`, `test_declared_input_entry_points.py`,
  `test_param_coercion.py` (parent-boundary row asserts `Pass a whole number from the parent.`).
- Verified: `make check` rc 0; `make test` **11342 passed**; `verify.sh` **87/0/0**. Mutants (same harness, counted):
  headline repeated → 1 failed; stdin label kept when an argument wins → 1 failed; runner params not typed in place
  (`last_execution_params` raw) → 1 failed; inputs exposed as child outputs → 1 failed. Real CLI: `parent-batch` record now
  `[1] Step 'call' passes 'x' …` / `item: 'x'` / `At: nodes[id=call].params.inputs.n` / `Sub-workflow: ./child.pflow.md`
  / `→ Pass a whole number from the parent.` — sentence once.  |  Assumed: nothing.
- Deviations/surprises:
  1. **Behaviour change found in self-check (kept, now pinned):** without declared `## Outputs`, a child's store is
     mirrored back minus its INPUTS (`_expose_child_outputs`, `workflow_executor.py:613`). Before PD, an input resolved
     from its default was seeded outside `child_params`, so `${call.limit}` exposed the child's default; now every
     resolved input is in `child_params` and stays unexposed — consistent with "excluding child inputs" (runtime/CLAUDE.md)
     and with the planner's mirror (also reads the typed complete inputs). Test
     `test_a_childs_fallback_inputs_are_inputs_not_outputs` (presence: the child's step output IS exposed).
  2. The once-only rule compares against the untruncated headline line; a provenance-wrapped child failure never equals
     its headline, so every other child-failure kind renders unchanged (pinned by the presence half: an in-child shell
     failure still prints `In step 'call' sub-workflow: Command failed with exit code 1`).
- Self-checks: fully-happy — raised and fixed: the input-exposure change above (pinned); planner per-item warning
  `source` aligned with its siblings; `--only` row asserted a substring (now exact); the stdin label had no row for an
  argument beating stdin (added). Claims re-checked: PB mutant count corrected to 23/23 in its entry; nothing else I would
  not stake. test-reflect (directed): PB — deepened `test_an_only_run_delivers_the_override_byte_identical` (exact
  output), added `test_an_argument_beats_stdin_and_is_labelled_an_argument` (killed its mutant), kept the seven
  `test_the_run_exits_1_with_the_typed_input_error` rows deliberately (they are the spec's breaks 1/4/5/6/7 on the real
  CLI, plan §5's evidence for PB-2 — the grammar itself is PA's table; `ratio=abc` is the no-consumer case), kept the rest
  (each mutation-killed in the PB ledger, absence rows paired). PD — deleted
  `test_a_child_input_with_a_default_is_satisfied_without_required_false` (duplicated the named test's `limit` default,
  which also lacks `required: false`) and `TestTheBundleRendersEveryShape::test_an_input_failure_is_rendered_as_placed`
  + the `current`-key template row (hand-built bundles for what the real CLI rows and `test_failed_node_invariant` cover
  end to end; legacy-key row kept as `TestTheLegacyBundleKey` — only a hand-written bundle has that shape); deepened
  `test_fail_fast_stops_at_the_bad_item_with_the_same_message` (per-item marker files: item 0 ran, item 2 never did —
  the old test could not see whether the batch stopped); added the once-only render row and the exposure row; kept the
  rest (D-ledger 15/15).
- Next: hand back.

## [2026-10-11 19:50] task-orchestrator — PB+PD accepted; rulings logged; committed
- Did: read I2's [17:40]/[18:55]/[19:40]; accepted PB devs 1–9, PD devs 3–9.
- Rulings: PD dev 1 — **B** (2/5): the CP-1 §1.5 clause "(here ${item} resolved to 'x')" is NOT built (the node sees
  resolved params in `prep`; adding it needs a compile-time stamp of the authored `inputs:` for one sub-clause). The
  parent fix line reads `→ Pass a whole number from the parent.` **This is a deviation from user-ruled text — carried
  to the PF screenshot checkpoint for the user to overrule (A stays a cheap follow-on).** PD dev 2 — authorized (1/5):
  `batch_errors.py` prints the §1.5 sentence once.
- Noted for the task-review: a child with no `## Outputs` no longer leaks its default-filled inputs back to the parent
  (`${call.limit}` read a child default before PD; consistent now with "a child's inputs are never outputs"; dry-run
  agrees; pinned by I2).
- Verified: I2's `make check` rc 0, `make test` 11342 passed, `verify.sh` 87/0/0 (re-run by me at commit time below).
- Next: commit PB+PD; fresh Opus · high I3 for PE (I2 at ~665k tokens); mid-task review #2 after PE.

## [2026-10-11 13:30] I3 (Opus) — PE (validator rules and the parity corpus)
- Did: D11(a) `WorkflowValidator._check_input_defaults` (each `default:` through `coerce_declared_input(source="default")`);
  D11(b)+(d) `template_validation/validator.py::_validate_declared_input_reads` + `_surface_reads` (every surface incl.
  output sources and cache vars, every operand incl. `??`, placed BEFORE the early return), binding by
  `type_checker.declared_root_type`; D11(c) `type_validation._declared_text_into_container` in Pass 6 and Pass 9
  (matrix untouched) + Pass 9 suggestion in canonical names; D11(e) `_check_literal_input_types` in
  `_check_required_inputs` (reuses `InputTypeError.located(step=, sub_workflow_path=)`, path `<inputs_path_root>.<name>`
  + `batch_item_index`); D11(f) `_reject_inputs_named_like_batch_aliases`. Parity harness: seeded store typed through
  the coercer (PE-9) AND carrying `DECLARED_INPUT_TYPES_KEY`; `sub_inputs` driver now applies the child boundary
  (`_drive_sub_inputs` → `type_child_inputs`); `Row.child_type`; `drive_runtime` captures a cache-render raise; 18
  `DECLARED_INPUT_ROWS`.
- Changed: `core/workflow/validator.py`, `runtime/template_validation/{type_checker,validator,type_validation}.py`,
  `runtime/template_validation/CLAUDE.md` (two Find rows, the declared-input paragraph, context keys `input`,
  `declared_type`, `received`, `source`, `accepted`). Tests: new `tests/test_runtime/test_template_validation/
  test_declared_input_rules.py` (PE-2/3/4/7/7b), new `tests/test_core/test_workflow_validator_declared_inputs.py`
  (PE-1 incl. CLI validate-only + run + save, PE-5, PE-6, I1's whole-map JSON-text item pin), `test_template_parity.py`
  (PE-8/9); flipped `test_types.py:1502` (`'- type: object' (currently array)`, exact); outside the list (forced):
  `tests/test_docs/test_guide_example_validation.py`, `tests/test_execution/test_plan_batch_sub_workflow.py` (devs 1–2).
- Verified: `make check` rc 0; `make test` **11431 passed** (baseline 11344). Mutation ledger (`scratchpads/task-120/pe/
  mutate.py`: content restore, `PYTHONDONTWRITEBYTECODE=1`, every `__pycache__` purged before/after, counted): **22/22
  killed** — binding ignores step scope; inputs values read the local key; pass MOVED after the early return (3);
  `??` operands skipped (3); cache vars skipped; output sources skipped; batch.items rule; field-on-array; index-on-
  object; Pass 6 rule; Pass 9 rule; Pass 9 display names; defaults unchecked (5); alias rule; alias ignores `as:`;
  literal child values unchecked; templates typed statically; item path not placed (survived first → added
  `test_an_inline_item_that_is_the_inputs_map_is_blamed_on_that_item`); harness without declarations (10); harness
  untyped seeding; harness `sub_inputs` without the child boundary. Real surface (isolated HOME, `.venv/bin/pflow`):
  BEFORE `bad-default`/`container`/`parent-inline --validate-only` → ✓ valid (I2 dev 9); AFTER `bad-default
  --validate-only`, run, `n=4` run, `pflow save` → the §1.2 default block at `inputs.n.default`, exit 1; `container
  v='{"a":1}'` validate-only AND run → the two §1.6 blocks (the `??` one with R3's sentence); the same file declared
  `object` → runs `1 fallback` (presence); `parent-inline` validate-only and run → the §1.5 sentence at
  `nodes[id=call].params.inputs.n`. In-tree scan (`pe/scan_examples.py`: every `.pflow.md` under `examples/`,
  `tests/fixtures/`, the Task-159 baseline, `workflows/` — 186 files) → **0 hits** (scanner presence-checked on the
  probes: 4 hits). Task-159 `verify.sh`: **86 passed / 1 drifted / 0 errors** — `12-real-world-lyrics-generator/
  04-guide-auto-detect`: the `pflow guide` text gained `COOKIE` in the masking-words list (`guide/nodes/shell.md`, from
  main's #716 `3a7643c8`, merged at `6ec068c4`); PE touches no guide file — not re-recorded.  |  Assumed: MCP
  `workflow_validate` inherits (same `WorkflowValidator`; not driven).
- Deviations/surprises:
  1. **Docs harness fixed, docs untouched:** `test_guide_example_validation._validate` injects every bare `${name}` as
     an input — batch aliases included — so (f) flagged 3 guide/docs blocks (`item`, `filename`, `page`). The examples
     declare no such input; the harness now skips each batched step's alias.
  2. `test_plan_batch_sub_workflow_non_list_items_surfaces_error` declared `items: string` as `batch.items` — now a (d)
     error; input switched to `any` so it still pins the planner's own non-list report.
  3. **D11(a) placement (decided, 2/5): `WorkflowValidator` only, not `validate_data_flow`.** 181 invariant 5 is for
     reports whose absence at compile is SILENT; a used bad default already fails loudly at the boundary (root compile,
     PD's per-item child `prep`). In data flow a dynamic child's bad-but-supplied default would become a fatal,
     unroutable `CompilationError`. Statically known children get it through the recursive validate. Reversible.
  4. **NEEDS YOUR CALL (2/5) — (b) lives where the plan put it (template validator), so a child chosen at run time
     (`workflow: ${…}`, compile-only) does not get it.** Most of its misses are loud at run time, but `${s.a ?? "x"}`
     (fallback), `loop.while: ${s.a}` on plain text (stops), a cache var on plain text (chunk dropped) stay silent
     there. Options: (A) leave it (rare: dynamic child + typed-input authoring bug); (B) move the pass into
     `validate_data_flow` (the 181/118 invariant pattern; data flow already has `step_scope`). Recommendation: A now,
     B as a follow-up if the gate's validation-consistency lens agrees.
  5. **Checkpoint §1.11 is not built (not PE's file):** the host still says `Workflow node's 'inputs:' resolved to str,
     expected dict of child inputs.` (plan D9: "the message gains the fix"; `workflow_executor.py`). My pin matches
     `'inputs:' resolved to` so it survives the rewording.
  6. Parity rows beyond the plan's list: `code:str`, a declared string into the `sink: dict` param (Raises), two
     SILENT runtime rows the validator exists for (`loop_while` plain text → `Resolves(False)`; cache var plain text →
     `Absent`), JSON-text cache var → `Raises(DeclaredInputTextError)`, `any` cache var → resolves. `output_source
     ${txt.a}` → `Raises(OutputResolutionError)` as planned. Row inputs are named `txt`/`d`/`data`/`arr` — the harness's
     consumer is node `s`, and an input `s` collides with it.
  7. Message text beyond the checkpoint's samples (shape per §1.6/§1.7): index-on-string `cannot index it` + fix
     `Declare - type: array …`; scalar `cannot read a field of a number|a boolean` / `cannot index …`, fix `Reference
     ${n} whole.`; array field fix `Index it first (${items[0]…}), or reference ${items} whole.`; object index fix `Read a
     field (${cfg.<field>}), or declare - type: array if 'cfg' holds a list.`; (c) registry form `` `${s}` feeds param
     'headers' (type dict), but input 's' … `` + `Declare - type: object for 's'.`; (d) for non-string types drops "and
     is never JSON-parsed"; (f) suggests `as: entry` (or `as: <alias>_item` when the alias IS `entry`). (e)
     diagnostics carry `node_id` like their sibling validator errors, so text renders `At: node 'call',
     nodes[id=call]…` (the runtime per-item record has no node prefix).
  8. (e) path for a whole-map `inputs: ${item}` item follows the extras convention (`batch.items[N].inputs.<name>`).
- Self-checks: fully-happy + test-reflect: pending orchestrator direction.
- Next: hand back; mid-task review #2 (`review-validation-consistency`) on PC+PD+PE.

## [2026-10-11 13:45] I3 (Opus) — PE self-checks (directed: §1.11 build, fully-happy, test-reflect)
- Did: built checkpoint §1.11 (authorized): `WorkflowExecutor._extract_child_inputs` now raises `Step 'call': 'inputs:'
  resolved to text, expected a map of child inputs. If the text is JSON, have the producing step emit a structured value
  (code `result: dict`) or list the inputs as keys under 'inputs:'.` for a str; `Step 'call': 'inputs:' resolved to
  <type>, expected a map of child inputs.` otherwise (`This step` without a node id); still `ValueError` (prep's
  recoverable set routes it — comment at the site). Self-check found and closed its static twin (below).
- Changed: `runtime/workflow_executor.py`; `runtime/template_validation/validator.py` (`_declared_batch_items` →
  `_declared_whole_root`, now also for a sub-workflow step's whole-map `inputs:`; `_WORKFLOW_TYPES`) + its CLAUDE.md
  Find row. Tests: `test_child_input_boundary.py::TestAWholeMapInputs` (text → exact §1.11 message through a real run;
  presence: a `result: dict` producer runs the child, `7 3`); `test_workflow_executor_comprehensive.py::
  test_inputs_non_dict_raises_shape_error` flipped to the exact list-form text; my bare-engine pin in
  `test_workflow_validator_declared_inputs.py` tightened to the exact §1.11 sentence; new
  `TestAWholeMapInputsFromADeclaredInput` (string → ERROR at `nodes[id=call].params.inputs`; object → valid).
- Verified: `make check` rc 0; `make test` **11432 passed**; Task-159 `verify.sh` 86/1/0 — the same single drift
  (`12/04-guide-auto-detect`, main's COOKIE), nothing new. Real CLI (isolated HOME): a shell step printing
  `{"s":"hi","n":7}` into `inputs: ${mk.stdout}` → exit 1 with the §1.11 text. In-tree rescan (186 files, the new
  phrase added) → 0 hits. Mutation ledger re-run in full on the final tree (same harness, counted): **24/24 killed** —
  the 21 of [13:30] (re-run; M7's pattern re-pointed after the rename) + whole-map rule dropped (1 failed), whole-map
  text given the generic message (2), a dict whole-map refused (36).  |  Assumed: nothing new.
- Deviations/surprises:
  1. **Correction to [13:30]:** that entry says "22/22 killed"; the ledger then had 21 mutants (M1–M21, M3 being the
     move). All 21 were killed; the count was wrong, the claim of zero survivors stands.
  2. **Fully-happy found a validate/run divergence §1.11 exposed:** `inputs: ${m}` on a sub-workflow step with `m`
     declared `string` passed `--validate-only` (the workflow node has no registry param types, so Pass 6 never sees
     it) and then failed at run time with §1.11. Closed in the (d) branch, which already did the same job for
     `batch.items`: a whole declared root that is not an `object` there is an ERROR (`A sub-workflow step's whole
     `inputs:` needs a map; input 'm' is declared `- type: string` and is never JSON-parsed.` → `Declare - type: object
     for 'm'.`). Importance 2, reversible, PE's own pass. Not widened: whole-map text from an UPSTREAM output still
     passes validation and fails at run time (unchanged since before this task; the engine never parsed it).
  3. Other doubts checked and dismissed: `ref in expression.operands` compares by value (an inner index ref equal to an
     operand is not a real shape); the scan used `validate(path, {})` and broken baseline fixtures short-circuit at
     structure (they are broken on purpose); the real-HOME traces timestamped during my run are another project's
     (`loudkult`), none mine.
- Self-checks: fully-happy — 1 wrong claim corrected (dev 1), 1 divergence closed (dev 2), rest clean.
  test-reflect (directed): deepened `TestShadowing::test_a_same_named_any_binding_still_receives_the_text` →
  `test_a_same_named_binding_reads_the_input_and_receives_its_text` (its validator half could not fail; it now also
  requires the `dict`-annotated twin to be the (c) ERROR at `params.inputs.data` — kills M2, which the old version did
  not see; the runtime half duplicates PC's resolver test but stays as the plan's end-to-end leg); deleted parity row
  `declared_string_into_code_str` (text either way via `text_input_keys` — PC's rule, already pinned there; nothing
  PE-specific could fail it); deleted `TestDeclaredDefaults` row `null-is-no-default` (the coercer returns `None`
  unchanged, so the guard it named could not be caught by it). Kept, each mutation-killed: the seven-row miss table
  (one row per type branch and segment class — DynamicIndex is its own class), the any/untyped/index-on-array valid
  rows (the absence half paired with the misses in the same medium), the (c)/(d)/(e)/(f) rows, the reachability pair,
  and the remaining 16 parity rows (validator AND runtime outcome each; the two silent-runtime rows are the reason the
  rules exist).
- Next: hand back; available to gate-run mid-task review #2.

## [2026-10-11 20:40] task-orchestrator — PE accepted; committed; review #2 commissioned
- Did: read I3's [13:30]/[13:45]; accepted devs 1–3, 5–8 and the self-check's added (d)-twin rule (whole-map
  `inputs: ${m}` on a declared non-`object` → validation ERROR; 2/5, mirrors the runtime §1.11 refusal).
- Rulings: dev 4 (declared-read pass absent for run-time-chosen children) — **A for now** (2/5); posed explicitly to
  mid-task review #2; B (move into `validate_data_flow`) if the lens agrees. Dev 5 — I3 authorized on
  `workflow_executor.py` for §1.11 (done).
- Cross-task (routed to the main orchestrator in my report): Task-159 case `12/04-guide-auto-detect` drifts on
  `origin/main` itself since #716 `3a7643c8` (COOKIE in the guide's masking list; never re-recorded). Verified: our
  `src/pflow/guide/` and `.taskmaster/tasks/task_159/` are byte-identical to `origin/main`. PZ treats that case as main's.
- Next: commit PE; I3 gate-runs mid-task review #2 (validation-consistency on PC+PD+PE).

## [2026-10-11 14:40] I3 (Opus) — mid-task review #2 (PC+PD+PE), gate-runner
- Did: pflow fan-out (codex, cross-model), launched from the worktree root, with 2 lenses each given its own target over
  `git diff origin/main...cafdada0`: `review-validation-consistency` (validator ⟷ runtime seam + the MANDATORY
  placement question) and `review-feature-interactions` (PD's batch × nested × error-routing seam) →
  `scratchpads/task-120/mid-review-2.md` (exit 0; Coverage 2/2, no failed lens; read in full). Verified every finding
  against code; all 9 confirmed and fixed, each with a regression test that a mutant proves.
- Changed: NEW `core/workflow/declared_inputs.py` (`declared_input_diagnostics` = the certain-miss pass + the alias rule,
  and `declared_root_type`, moved out of `runtime/template_validation/{validator,type_checker}.py` and
  `core/workflow/validator.py`); `core/workflow/data_flow.py::validate_data_flow` calls it; `core/workflow/
  template_surfaces.py` `WORKFLOW_NODE_TYPES`; `runtime/template_validation/type_validation.py` (import);
  `runtime/engine/template_resolution.py::parses_leaves`; `runtime/compilation/ir_preparation.py::
  _check_undeclared_extras`; `core/workflow/validator.py::_enumerate_child_calls` (+ `_reads_only`); `execution/plan.py::
  _resolve_per_item_sub_workflow_inputs`; `execution/executor_service.py::build_subworkflow_diagnostics`; CLAUDE.md
  `core/workflow` (row) and `runtime/template_validation` (the declared-input paragraph re-pointed, Find row moved).
  Tests: `test_workflow_validator_declared_inputs.py` (+`TestTheCompilerEnforcesTheRules` ×3,
  `TestEnumerationKeepsWhatItCannotKnow`), `test_declared_input_rules.py` (+whole-map shadowing pair),
  `test_child_input_boundary.py` (+framework key, long spelling, repeated-id provenance), `test_plan_batch_sub_workflow.py`
  (+nested rejected item); parity: harness `_raised` shows a `CompilationError`'s wrapped diagnostics; 6 rows now
  `Raises("CompilationError", <rule text>)` (the runtime leg compiles first, and the compiler now refuses them), the two
  `*_json_text` loop/cache rows deleted (identical to their plain-text twins once compile refuses both); fixtures that
  declared `string` placeholders but read fields: `test_template_integration.py` ×3 → `any`.
- Dispositions:

  | # | Lens · sev | Finding (verified at) | Disposition |
  |---|---|---|---|
  | C1 | VC · Critical | Run-time-chosen child bypasses the certain-miss pass: compile runs only data flow (`compile_validation.py:105`); `??` fallback / loop stop / cache drop silent (`templates.py:573` backstop sees JSON text only) | **Fixed = B** (posed question; lens recommends B, I agree): pass moved into `validate_data_flow` via `declared_inputs.py`; template-validator call deleted (no duplicate on the root path — pinned: one error). Test: real run, `workflow: ${which}` child with `${s.a ?? "fallback"}` → fails with the rule text; `object` twin runs → `1`. |
  | C2 | VC · Critical | Alias prohibition also compile-unreachable (`validator.py:448`); a dynamic child's `${item.a ?? …}` silently falls back | **Fixed**: moved beside the pass in `declared_inputs.py`. Test: `compile_workflow` refuses `item` input + batch. |
  | C3 | VC · Critical | `pflow.runtime.workflow_executor` spelling still parses child input values (`template_resolution.py:105`) | **Fixed**: `parses_leaves` keys both spellings via the new shared `WORKFLOW_NODE_TYPES` (also used by the pass). Test: both spellings hand `{"a":1}` text to a child `string`. Severity read as Warning (legacy spelling), fixed anyway. |
  | W1 | VC · Warning | Whole-map `inputs: ${bindings}` binds run-time keys; a sibling `${s.a}` may read the local (`template_resolution.py:468`); validator rejected it | **Fixed**: `declared_root_type` returns `None` for a step's other params after a string `inputs:`; the `inputs:` expression itself still reads the input (presence pair). |
  | W2 | FI · Warning | Child boundary exempted `_pflow_*`/`__*__` keys (`ir_preparation.py:151`) — `{"n":7,"__loop_active__":1}` reached child storage | **Fixed**: the exemption applies only at the root boundary (`caller.step` unset); a parent's every undeclared key is refused. Test: real run → `Unknown input '__loop_active__' — not declared by ./child.pflow.md.` |
  | W3 | VC · Warning | Inline enumeration resolved `${count ?? "bad"}` to its fallback; (e) rejected a run-valid value (`validator.py:1854`) | **Fixed**: enumeration keeps any `inputs:` value that reads a non-alias root as its template (`_reads_only`). Test + presence (a real inline literal still errors). |
  | W4 | FI · Warning | A type-rejected item's child was planned on the bad value; a nested sub-workflow batch over it put an ERROR in the plan (`plan.py:1630/1691`) | **Fixed**: a rejected item's child is planned on type-shaped placeholders (`_placeholder_child_inputs`). Test: 3-level plan, run DEGRADED-continues, plan has the item WARNING and no ERROR (first test version survived its mutant — rebuilt with the nested *workflow* batch the lens described; now killed). |
  | W5 | FI · Warning | Once-only suppression matched any diagnostic whose `sub_workflow_step` equals the parent step — reused ids across levels dropped the outer provenance (`executor_service.py:165`) | **Fixed**: suppress only diagnostics captured directly in THIS bundle. Test: `parent.call → middle.call → grandchild` → `In step 'call' sub-workflow: Step 'call' passes 'x' …` (once wrapped). |
  | S1 | VC · Suggestion | Placement recommendation B, with costs (no duplicate, intentional fatal compile error, unconditional under `check_inputs=False`, defaults stay put) | **Accepted** = C1's fix; defaults (D11 a) stay in `WorkflowValidator` as ruled. |

  Found while fixing (not a lens finding): a misplaced `${x|json}` in `batch.items` gave two errors once the pass ran
  outside the template validator's Issue early-return — the pass now skips a non-embedded JSON insert (the Issue
  pass's one error; `test_embedded_code_diagnostics` pins it).
- Verified: `make check` rc 0; `make test` **11437 passed**; Task-159 `verify.sh` 86/1/0 (the same main-owned COOKIE
  drift only); in-tree rescan 186 files → 0 hits; `container` probe → same two errors (the stray `WARNING: Template
  validation found 2 errors` log line is gone with the move). Mutation (same harness): R1–R9 + R1b **10/10 killed**
  (pass not in data flow 33; alias not in data flow 3; whole-map owned 1; long spelling 1; child framework exemption 1;
  enumeration guesses 1; rejected item on its value 1 (after the test rebuild); deeper placement unwrapped 1;
  misplaced insert double-reported 1; §1.11 generic text 2).  |  Assumed: MCP `workflow_validate`/`workflow_plan`
  inherit (same validator/planner; not driven).
- Deviations/surprises: (1) B done (authorized by the orchestrator on lens agreement) plus the alias rule moved with
  it (C2, same reason, 2/5). (2) Parity rows' runtime legs for the certain misses now read `CompilationError` — the
  "silent at run time" rows no longer exist because the compiler refuses those workflows; the resolver's own
  behaviour stays pinned by PC's `test_declared_input_resolution.py`. (3) 3 `test_template_integration` fixtures
  declared `string` placeholders and read their fields — invalid under the rule; switched to `any`. (4) Follow-up for
  the completion gate's simplicity lens: the pre-existing copies of the workflow-type set remain (`core/workflow/
  validator.py` ×3, `graph/build.py`, `runtime/compilation/{compiler,node_loader}.py`, `resume_preflight.py`,
  `template_validation/validator.py`) — only my two sites use `WORKFLOW_NODE_TYPES`. (5) `.claude/agents/
  pflow-codebase-searcher.md` does not name `core/workflow/declared_inputs.py` yet — PF's.
- Self-checks: fully-happy — the W4 test first passed on the old code (caught by its mutant, rebuilt); the
  misplaced-insert double report found and fixed; rest clean. test-reflect: not separately directed; every new row is
  mutation-killed with its presence half.
- Next: hand back.

## [2026-10-11 21:50] task-orchestrator — review #2 dispositions accepted; committed; PF next
- Did: read I3's review-#2 entry (its header timestamp reads 14:40 — I3's clock labels drift; order in this file is
  authoritative); accepted all 9 dispositions; the posed question resolved **B** (lens + I3 agree): the certain-miss pass
  and the input-vs-alias rule now live in `core/workflow/declared_inputs.py`, run inside `validate_data_flow` (compiler
  enforces them for run-time-chosen children).
- For the completion gate: `WORKFLOW_NODE_TYPES` is used by two new sites only; older copies of the workflow-type set
  remain (simplicity lens). PF adds `core/workflow/declared_inputs.py` to the searcher def.
- Next: commit; fresh Opus · medium I4 for PF (docs/guide/instruction files/web comments + run-form screenshots) →
  embedded USER checkpoint (screenshots + before/after) before PZ.

## [2026-10-11 14:18] I4 (Opus) — PF (guide, docs, instruction files, web comments, CLAUDE.mds, web run-form real surface) + CP evidence
- Did: rewrote every stale surface against the code (not the plan): the auto-parse section and type table (decision (b)
  grammar per type, `any` lossless, the source-naming `Invalid input value` sentence, "omitted `type` = `any`", "default
  must fit") in `guide/core.md` AND both MCP instruction copies (by hand, same three edits + the code-node rule + the
  batch `items` row); `guide/nodes/{code,shell}.md`, `guide/features/{batch,sub-workflows}.md`; four docs pages;
  `architecture/core-concepts/data-type-coercion.md` inventory rewritten to the built points (0 boundary, 1 traversal,
  2 `auto_parse` leaf + consumer table, 3 serialize-for-`str`, 4 display, 5 removed LLM parse; the deleted
  `runtime/wrappers/*` citations gone); `architecture/reference/template-variables.md`, `core/templates.py:43-46`,
  `core/CLAUDE.md` (the `TypeSpec.accepts`-in-use claims → `coerce_declared_input`); web comments; searcher def; then
  drove the web run form (below) and wrote `scratchpads/task-120/pf/evidence.md`.
- Changed: `src/pflow/guide/{core.md,nodes/code.md,nodes/shell.md,features/batch.md,features/sub-workflows.md}`,
  `src/pflow/mcp_server/resources/instructions/{mcp-agent,mcp-sandbox-agent}-instructions.md`,
  `docs/reference/cli/index.mdx`, `docs/reference/nodes/{code,index}.mdx`, `docs/how-it-works/template-variables.mdx`,
  `architecture/core-concepts/data-type-coercion.md`, `architecture/reference/template-variables.md`,
  `src/pflow/core/{CLAUDE.md,templates.py}` (comment), `src/pflow/core/workflow/CLAUDE.md` (a blank line PC left inside
  the Task table split it in two — removed), `src/pflow/runtime/compilation/compile_validation.py` (`_prepare_compilation`
  docstring said a 2-tuple, returns 4; plan §6 item), `web/src/{components/RunForm.tsx,components/RunPanel.tsx,
  utils/controlForType.ts,api/client.ts}` (comments only), `.claude/agents/pflow-codebase-searcher.md` (+ `.codex` sync).
- Verified: every guide/doc sentence checked against code or executed — `coerce_declared_input` table run in-process
  (`007`→7 integer, `3.0`/`true` rejected for MCP integer, `1e3` number→1000.0, `any` `007`/`null` stay text,
  `[1,2]`→list, ` 7\n` stdin→7, string keeps spaces); a real parse probe (`pf/wf/parse-probe.pflow.md`): upstream
  `'42\n'` into an `inputs:` map stays `str:'42'` (the old guide rows `'42\n'`→42 / `'true'`→true were false — replaced
  by one correct row), JSON object text → dict, a `str`-annotated key → str, a declared `string` → str, an `any` → dict;
  `extract_code_annotation_type`: `str`, `str | None`, `Optional[str]` → text, `str | dict`/`Any` → not. `uv run pflow
  guide` renders; `tests/test_docs` + `tests/test_mcp_server` 157 passed; web `vitest run` 918 passed; `make check` rc 0
  (MDX fence check passed); `make test` **11437 passed** (= baseline; no test changed).
  **Web real surface** (one `pflow ui` from this worktree, port 8791, PID 71527 (uv wrapper 71523), isolated HOME
  `pf/home`, bundle rebuilt with `make ui-build`), workflow `scratchpads/task-120/pf/typed-form.pflow.md`
  (`count` integer required · `flag` boolean default false · `topics` array required), driven by
  `pf/drive-run-form.pflow.md` (reuses the skill's `shared/open-and-settle`, real HOME for the chrome-devtools MCP):
  `count=3.0` → no launch, panel shows `Input 'count' is declared `- type: integer` but received '3.0' from the command
  line.` + `Pass a whole number (e.g. 3): count=3` (= the server's `errors[0]` message + suggestion) — shot 01;
  `count=3.0 topics=tea` → two error blocks, each with its fix — shot 04; `count=3 flag=true topics=["a"]` → launched,
  overlay pinned to run `d71409bf…` "Run success", trace `meta.inputs` `{"count": 3, "flag": true, "topics": ["a"]}`,
  step output `count=int:3 flag=bool:True topics=list:['a']` — shot 02; re-open → "load inputs from" that run →
  fields `3` / `true` / `["a"]` (`/api/run-inputs` returned the same tokens) — shot 03; presence pair: the Defaults
  state of the same form reads `""` / `false` / `""` — shot 00. Shots in `scratchpads/task-120/pf/shots/`
  (`00-run-form-defaults-before-load.png`, `01-count-3.0-typed-input-error.png`, `02-count-3-run-launched.png`,
  `03-rerun-prefill-from-run-d71409bf.png`, `04-two-typed-input-errors.png`). Server killed by PID; port 8791 free;
  both PIDs gone. | Assumed: nothing in the docs beyond what the probes show; MCP `workflow_validate` "takes no
  parameters" taken from the spec + PB (not re-driven).
- Deviations/surprises:
  1. **NEEDS A CALL (src fix outside PF) — the ruled `settings` source text is unreachable.** `pflow run`
     (`cli/commands/run.py:1373`), `pflow ui` (`ui.py:446`) and the MCP server (`mcp.py:732`) run
     `llm_config.inject_settings_env_vars()` at startup, copying settings.env into `os.environ`;
     `ir_preparation._fallback_value` reads `os.environ` first, so a settings value is labelled `env` ("from the
     environment variable port", fix "export port=3 …") — executed in evidence a3. Pre-existing twin, not widened: on main
     too, a settings-sourced input never reached `settings_names` → `__env_param_names__` (`runner.py:849`, the trace's
     always-redact set) under `pflow run`. Fix sketch (importance 2, ~5 lines + one test): `_fallback_value` treats a name
     in `llm_config._settings_injected_env_vars` (expose a public accessor) as `settings`. Not made — outside PF's files.
  2. The plan's "fix the searcher row that points code-annotation extraction at `data_flow.py`/`type_validation.py`":
     no such row exists in `.claude/agents/pflow-codebase-searcher.md` (grepped `.claude/agents`, the CLAUDE.mds) — nothing
     to fix; the new row names `nodes/python/python_code.py::extract_code_annotation_type` instead.
  3. Beyond the plan's list, same stale class: `web/src/api/client.ts:128` (`infer_type` comment), the MCP copies' batch
     `items` row, and a `guide/features/sub-workflows.md` bullet (the child types each value per call/item; an `any` child
     input receives the parent's value as passed — a behaviour change worth stating; verified in `coerce_declared_input`'s
     `any` branch: only `argument` infers). `guide/nodes/code.md` gained one sentence (a declared `string` into a
     `dict`/`list` annotation is the same type-mismatch error). Not touched: `releases/*-context.md` (history),
     ADR-0017's `infer_type` BEFORE sentence (ADR — main orchestrator's), `python_code.py:198-199` (#735's).
  4. **UX observations from the screenshots, for the user checkpoint (not fixed; text is CP-1's domain):** (a) a web-form
     error says "from the command line" and the fix is CLI syntax (`count=3`) — the form spawns the CLI, so source =
     `argument` is technically right but reads oddly in a form; (b) the message's backticks (`` `- type: integer` ``)
     render literally in the panel (pre-existing for all diagnostics); (c) headless Chrome shows a number input's
     `3.0` as `3,0` (locale) — the value sent is `3.0`; screenshot artefact. The panel needed `scrollIntoView` for the
     error to be visible (it sits below the fold of the panel) — layout pre-existing, no change made.
  5. No `web/` behaviour change was needed: `RunForm` already renders every `errors[]` entry's `message` + each
     `suggestions[]` line (D13 bullet satisfied as-is), so no vitest added.
  6. Evidence observations (in `evidence.md`, not changed): the batch header is the formatter's `Batch 'call' errors:`
     (ruled `… completed with 1 failed item (continue):`); validator rows render `At: node 'x', nodes[id=x]…`; §1.7's
     array/object hints read `${items[0]}` / `${cfg.<field>}` (ruled `${items[0].name}` / `${cfg.name}`); §1.12 lists
     available inputs sorted; MCP `workflow_execute` surfaces the rendered text in its pre-existing `RuntimeError` wrap,
     not the §1.4 JSON entry; a stray `WARNING: Template validation found 1 errors` log line still precedes Pass 6/9
     errors.
- Self-checks: fully-happy — one-home rule: the new `coerce_declared_input` pointer sits in `core/templates.py` (code
  site) and `core/CLAUDE.md` (rule owner) as a pointer, not a restated invariant; the guide's grammar table is the one
  user-facing home and both MCP copies mirror it verbatim (diffed equal before editing; same script applied to all
  three). test-reflect: not needed — docs/comments phase, no test added.
- Tooling postmortem (screenshot skill): worked well — `shared/open-and-settle` reused as a sub-workflow by absolute
  path; `-p` stdout = just the result. Friction: (S) no workflow fills or submits a form (`click` is one synthetic click,
  no typing) — wrote `scratchpads/task-120/pf/drive-run-form.pflow.md` (native value setters + `input`/`change`
  events, optional run-picker load, submit, reads errors/fields); candidate for the skill (M if generalised to any
  panel form). (S) `fullPage` screenshots do not reach content inside a scrolled panel — the run-form error was clipped
  until the driver `scrollIntoView`'d it; a `scroll_to` selector on `screenshot`/`click` would close it. (S) headless
  Chrome's locale renders number inputs with a decimal comma (`3,0`) — set `--lang=en-US` in the registration or note
  it. (known) out paths must live under `/tmp`, then copied.
- Next: hand back — decision 1 (settings label fix), the UX items in 4, and the CONTEXT.md noun; then the user
  checkpoint (screenshots + `scratchpads/task-120/pf/evidence.md`), then PZ.

## [2026-10-11 14:24] I4 (Opus) — authorized fix: the `settings` source label (PF dev 1)
- Did: `ir_preparation._fallback_value` labels an environment value `settings` when startup copied it out of settings.env
  — signal: the injector's own record (`llm_config._settings_injected_env_vars`, exposed as `is_settings_injected`),
  preferred over the `os.environ[name] == settings_env[name]` equality the orchestrator sketched (the injector never
  overwrites an exported name and records exactly what it set, so the record is unambiguous where equality is not).
  The `settings_names` → `__env_param_names__` set is left as before for such values (explicit guard + comment).
- Changed: `src/pflow/core/llm_config.py` (`is_settings_injected`), `src/pflow/runtime/compilation/ir_preparation.py`;
  test `tests/test_integration/test_declared_input_entry_points.py::TestASettingsValueIsLabelledSettings` (2 rows, real
  `python -m pflow.cli` subprocesses, function-scoped HOME, `PYTEST_CURRENT_TEST` stripped so injection runs).
- Verified: new test red before the fix (said "from the environment variable port"), green after; mutant "label
  `settings` whenever the name is in settings.env" killed by the presence row (exported `port=xyz` + setting `abc` →
  "received 'xyz' from the environment variable port", no "settings.env"). Real CLI under the isolated HOME: evidence a3
  re-run and `scratchpads/task-120/pf/evidence.md` updated (settings sentence + `pflow settings set-env port 3, or pass
  port=3`; presence block). `make check` rc 0; `make test` **11439 passed** (11437 + 2).
- Deviations/surprises: (1) **correction to my PF entry, dev 1:** the injection sites are `pflow run`
  (`run.py:1373`), `pflow resume` (`resume.py:328`) and the MCP server (`mcp_server/main.py:42`); `ui.py:446` (TTS) and
  `mcp.py:732` (`mcp find`) are unrelated commands — the web form is covered because it spawns `pflow run`.
  (2) **Follow-up (not changed, as ruled):** a settings value copied into the environment still stays out of
  `__env_param_names__`, the trace's always-redact set (`runner.py:849`) — pre-existing on main.
- Self-checks: fully-happy — clean. test-reflect: not separately directed; both rows mutation-relevant (red pre-fix;
  presence row kills the equality mutant).
- Next: hand back.

## [2026-10-11 22:40] task-orchestrator — PF accepted; settings label fix accepted; committed
- Did: read I4's [14:18]/[14:24]; viewed shots 01 and 03 myself (error text + prefill match the server's `errors[0]` and
  the trace). Accepted devs 2–6; the settings-label fix (authorized 2/5) uses the injector's record — better than my
  equality sketch.
- Tooling postmortem dispositions (screenshot skill): (1) no form fill/submit workflow → **issue** (proposed to the main
  orchestrator in my handback; I4's `scratchpads/task-120/pf/drive-run-form.pflow.md` is the seed); (2) `fullPage`
  misses content inside a scrolled panel (`scroll_to` selector) → **same issue**; (3) headless Chrome decimal-comma
  locale on number inputs → **note in that issue**, not fixed here; (4) `/tmp` out paths → **drop** (known, documented).
- Follow-ups for the task-review (pre-existing, not widened): settings values copied into `os.environ` stay out of the
  trace's always-redact set (`runner.py:849`); web-form errors say "from the command line" with CLI-syntax fixes (the
  form spawns the CLI) — carried to the user checkpoint.
- Next: commit; draft the user checkpoint page from I4's shots + `evidence.md`; hand back (embedded USER checkpoint)
  BEFORE the completion gate.

## [2026-10-11 22:55] task-orchestrator — PARKED on the embedded USER checkpoint (PF screenshots + message evidence)
- State: phases P0, PA, PC, PB, PD, PE, PF all built, self-checked, committed; mid-task reviews #1 and #2 done and folded.
  Head `42660f09` (local; nothing pushed). `make check` rc 0; `make test` 11439 passed; Task-159 `verify.sh` 86/1/0 — the
  one drift (`12/04-guide-auto-detect`, COOKIE) is main's own since #716 (our guide + baseline byte-identical to
  `origin/main`). No `pflow ui` server running (I4 killed PID 71527/71523; port 8791 free).
- Checkpoint page (drafted by me, for the main orchestrator to publish): `scratchpads/task-120/checkpoint-pf.md`;
  evidence `scratchpads/task-120/pf/evidence.md`; shots `scratchpads/task-120/pf/shots/00…04`. Staleness: 0 respects
  (shot 01's text re-executed on `42660f09`, identical).
- Decisions asked: D1 §1.5 clause (rec B, built), D2 `(e.g. 3)` suggestion form (rec accept), D3 unruled messages (rec
  accept), D4 web-form "from the command line" wording (rec ship; web-form source as follow-up issue), D5 no-diagnostic
  behaviour changes (FYI).
- Exact resume point: on the ruling — (1) apply any text change the ruling makes (D1=A → compiler stamps the authored
  `inputs:` on the WorkflowExecutor + `InputTypeError` template clause + test; D4=(b) → only if ruled into THIS task);
  (2) `git fetch` + merge `origin/main`, `make check` + `make test`; (3) commission the completion gate (plan §4 PZ.3:
  code-mode deep-review full floor via the pflow fan-out — silent-failures, impact-completeness, feature-interactions,
  test-fidelity, validation-consistency, agent-ux, simplicity (incl. `WORKFLOW_NODE_TYPES` copies + where
  `declared_text_reason` lives), spec-conformance; then `review-falsifier` launched DIRECTLY by me, last), gate-runner =
  a fresh Opus review-evaluator (I1–I4 windows are large) packeted with spec + plan + this log; (4) `make
  test-all-local`, verify.sh vs 87/87-minus-main's-COOKIE-case, `capture.py --check` vs P0's 5; (5) spec Status done +
  Completed; `create-task-review`; `create-pr` with closing keywords for #686 and #687 ONLY (packet: #188, #297, #742,
  #743 are "Refs … — not a closing PR"); check `closingIssuesReferences`.
- Next: hand back to the main orchestrator.

## [2026-10-11 14:40] I4 (Opus) — authorized fix: run-form checkbox alignment (user-reported, pre-existing `686b27f6c`)
- Did: cause confirmed — `.run-field` is a column flex (`index.css`), default `align-items: stretch`, and the unclassed
  checkbox `<input>` (`RunForm.tsx`) stretched to the row width, drawing its glyph centred. Gave it `run-field-checkbox`
  (`align-self: flex-start; margin-inline: 0`). Alignment only — no element moved, no other rule touched.
- Changed: `web/src/components/RunForm.tsx` (className), `web/src/index.css` (one rule + one-line why),
  `web/src/components/RunForm.test.tsx` (the existing control-mapping test asserts the class — a class pin, no jsdom
  layout claim).
- Verified: screenshot skill's `open-and-settle` via `scratchpads/task-120/pf/drive-run-form.pflow.md` (now also returns
  label/control rects per field), same workflow `typed-form.pflow.md`, Defaults state. Before (current bundle):
  `scratchpads/task-120/pf/shots/05-checkbox-before.png` — label left 477 px, checkbox box left 481 px, width 260 px
  (row-wide, glyph centred ≈611 px). After (`make ui-build`, server killed and restarted):
  `scratchpads/task-120/pf/shots/06-checkbox-after.png` — checkbox left **477 px = label left 477 px**, width 13 px;
  text/textarea controls unchanged (477 / 267 px both shots). Web `vitest run` 918 passed; `make check` rc 0;
  `make test` 11439 passed. Server (PIDs 96014, then 97222, port 8791, isolated HOME) killed by PID; none left.
- Deviations/surprises: none — alignment alone looks right, no layout proposal needed. (The "Run failed · 0 nodes" badge in
  both shots is the overlay following the newest run in `pf/home`, unrelated to this change.)
- Self-checks: fully-happy — clean. test-reflect: not needed — one class assertion as directed.
- Next: hand back.

## [2026-10-11 23:30] task-orchestrator — USER CHECKPOINT RULED; checkbox fixed; resuming to PZ
- Ruling (user via main orchestrator, 2026-10-11): D1 → **B** (as built); D2 → accept; D3 → accept as shipped; D4 →
  **(a)** ship as is, follow-up filed as **#777** (source clause names the surface the value entered through; the run
  form is a labelable source); D5 → accepted. Closing keywords: **#686, #687, #188** (spec line ~314: #188 closed by the
  per-item child boundary); #297, #742, #743 → "Refs — not a closing PR".
- User instruction for the rest of the build and the gate (verbatim): *"we should always strive to close bug classes
  rather than bugs if that makes sense. And if anything is unclear we should resolve that ambiguity first before
  comitting, and we should resolve all assumptions."* → every gate disposition "fixed" names the CLASS it closes; every
  log `Assumed:` still open at PZ is verified or handed back before `create-pr`.
- **Packet claim 1 (`_prep_error` routing vs #768): VERIFIED** — executed by I1 at P0 under an isolated HOME (see the
  [11:45] P0 entry): a host prep-raised child-input error routes via `on-error:` (handler ran, DEGRADED), fails ONE item
  under batch `error_handling: continue` (items 0/2 succeed), and fails the run under default routing (exit 1). Re-proven
  on the built code by PD's real-surface `parent-batch`/non-batch runs ([18:55]) and `test_child_input_boundary.py`.
- User-reported checkbox misalignment (shots 00/01/03): blame `686b27f6c` (pre-task); fixed by I4 as alignment only
  (`run-field-checkbox`: `align-self: flex-start`) — before/after `scratchpads/task-120/pf/shots/05-checkbox-before.png` /
  `06-checkbox-after.png`; measured checkbox left 481→477px = label left 477px (I4 [14:40]); I viewed 06.
- Tooling postmortem issue filed: **#778** (form-fill workflow, scroll_to, locale).
- Next: commit; merge `origin/main`; gates; assumption audit; completion gate.

## [2026-10-11 15:26] G1 (Opus, fresh review-evaluator) — completion gate: code-mode deep-review on `origin/main...986dad54`
- Did: one pflow fan-out (codex, cross-model), launched from the worktree root, backgrounded to
  `scratchpads/task-120/gate/report.md` (exit 0, 711 s; per-lens raw extracted from the run's trace to
  `gate/raw.json`); read in full; verified every finding against code (file:line read or executed under an isolated
  HOME); fixed 15, disputed 1, 4 handed back (below). Assumption audit (a)–(e) executed.
- **Lens partition** (targets: `gate/lenses.json`; every target named the 3-dot diff, the settled set — ADR-0006/0016/0017,
  DECIDED ledger, rulings (i)–(iii), the ruled checkpoint, the [23:30] rulings — and "silence is a gap"). Cross-cutting,
  WHOLE diff: `impact-completeness` (deleted helpers, `__pflow_input_types__` consumers, bundle key, string→typed sites,
  entry labels, signature changes), `feature-interactions` (batch seq/parallel × nested × loops × routing × dry-run × memo
  × `## Cache` × MCP × resume × web), `simplicity` (candidates (a)–(h) named), `spec-conformance` (spec + plan + log;
  Requirement Inventory mandated). Dimension, scoped: `silent-failures` → param_coercion, templates, exceptions,
  ir_preparation, engine/{template_resolution,batch_executor,loop_control,engine}, workflow_executor, prompt_cache,
  execution/{plan,runner}, prompt_cache_analysis/*; `validation-consistency` → validator, declared_inputs, data_flow,
  template_validation/* vs templates, template_resolution, type_child_inputs, prepare_inputs/check_supplied_inputs
  (incl. validate-only with values); `agent-ux` → every message site + guide/** + both MCP copies + docs/architecture
  pages; `test-fidelity` → the diff's test files; `concurrency-safety` → per-item child typing, engine install/restore,
  batch store copies, `is_settings_injected`, planner install.
- **Coverage: 9/9 lenses received, 0 failed.** Several lenses self-declared partial file reading (spec-conformance
  most): the falsifier gets the inventory. Requirement Inventory saved verbatim:
  `scratchpads/task-120/gate/requirement-inventory.md` (full lens output: `gate/spec-conformance-full.md`).
- **Dispositions** (every "fixed" names the class it closes; tests mutation-checked with the fixed harness
  `gate/mutate.py`: content restore, `PYTHONDONTWRITEBYTECODE=1`, all `__pycache__` purged before/after, counted):

  | # | Lens(es) · sev | Finding (verified at) | Disposition |
  |---|---|---|---|
  | F1 | impact+FI+silent · W | Re-entry into the boundary loses labels: prediction compiles `analyze()`'s typed params as `argument`, so an MCP `any` `"true"` is re-inferred `True` → false `key_mismatch` (`predict.py:479`); dry-run nudge `analyze()` unlabelled (`runner.py:639`) | **Fixed — class: every internal re-entry carries the labels the values entered with.** Enumerated ALL boundary callers (`compile_workflow`/`prepare_inputs`/`check_supplied_inputs`/`analyze`): the two unlabelled re-entries were these. `AnalysisContext.input_sources` travels with `parameters` (both `build` sites in `analyze`); prediction re-compiles the root with them and a child as `parent` (as the runtime does) — covers `diagnose.py`'s fallback too; `plan()` passes its labels to the nudge. Test `test_prediction_types_a_call_value_as_the_run_did` (real run → engine key → analyze: no `key_mismatch` for `call`; presence: `argument` labels DO mismatch for `"true"`, not for `"02134"`). M4/M5 killed; **M6 (nudge) and M15 (trace-misalignment ctx rebuild) survive — unobservable today** (the nudge loads no trace, the rebuild never re-predicts); kept as correct-by-construction, unpinned. |
  | F2 | FI+silent · C | `declared_text_misses` ignores dynamic-index refs: `loop.while: ${d.flags[${d.payload.index}]}` stopped "normally", inline item kept literal (executed: loop `success=True`) | **Fixed — class: every consumer that reads "unresolved" as "absent" sees a declared-text miss at ANY depth.** `templates.declared_text_stop` (recursive over `index_sources`) is the one home; `declared_text_misses` (loop, inline batch, cache chunk) and `_evaluate` read it. Tests: loop rows, inline-batch row with resolving-index presence half. M2 killed (2). |
  | F3 | silent · C | `${d.payload.again ?? false}` resolves to the fallback — loop stops, output emits null, param gets the fallback (`templates.py:635`; executed) | **Fixed — class: `??` never falls past a declared-text miss, for every consumer** (one site, `_evaluate`: the chain ends unresolved, so node params render the W5 reason, loop/batch/chunk raise `DeclaredInputTextError`, outputs fail). Real absence still falls through; the text itself is still found (presence rows). Same class, adjacent site: output failures offered "write `${… ?? null}`" for a declared-text miss — a fix that cannot work — now excluded (`user_errors._optional_field_suggestions`; plain missing field keeps it, presence row). M1 (3), M3 (2) killed. |
  | F4 | FI+VC · W | Static enumeration guesses: whole-map `inputs: ${bindings ?? item}` and `${item.n ?? "bad"}` over an item `"${payload}"` resolve to fallbacks, then (e) rejects a run-valid workflow (`validator.py:1823`) | **Fixed — class: enumeration types only values whose every dependency is known** (`_known_here`: reads only the alias, and a `??` never falls past a template the item holds), dict-form AND whole-map. Tests: both shapes validate clean AND run successfully; presence: the written-literal twins still error. M7, M8 killed. |
  | F5 | VC · C | (i) literal `inputs: {n: null}` passes validation, run fails "requires input"; (ii) a required child input supplied only by env/settings is refused statically but accepted at run time | (i) **Fixed — class: the static presence check uses the boundary's rule "a null is no value"** (`_check_required_inputs` `supplied_keys`); test pins validate AND run verdicts. M9 killed. (ii) **HANDED BACK (H1)** — executed: static child + `n` exported → validation error; run-time-chosen child + `n` exported → runs, child gets `7`; `origin/main`'s `_validate_child_params` refused both. Plan D5/D10 decision. |
  | F6a | impact · W | JSON AUTO output re-parses a declared input's text (`text=true` → `true`, `{"a":1}` → dict; executed) | **Fixed — class: an output surface that selects a declared input's own value never re-parses it** (explicit `-o` was fixed at mid-review #1; AUTO now: root hit + `reads_declared_input`, identity-checked against the namespace fallback). Test with presence half (a step's JSON stdout still parsed). M10 killed. DECLARED outputs sourced from an input are #743's boundary (H3 note). |
  | F6b | silent · W | `-o d.payload.a --output-format json` → empty `result`, success | **HANDED BACK (H2)** — pre-existing class (executed: `-o d.nope` identical); the diff routes more paths into it. |
  | F7a | conformance · W | guide + both MCP copies: "`default` (only when required: false …)" — D5 makes a default satisfy a required input | **Fixed** (3 files, identical text); claim executed (`prepare_inputs` on `{n: integer, default: 3}` → `n=3`, no error). |
  | F7b | agent-ux · W | "Surrounding whitespace is ignored for every type but `string`" — `any` keeps ` 42` | **Fixed** (3 files); executed `' 42'` any→`' 42'`, integer→42, string→`' 42'`. |
  | C1 | test-fidelity · C | `test_the_workflow_input_is_still_protected_in_another_step` never resolved the shadowing step | **Fixed (deepened)**: both steps resolve against ONE store (`get` asserts its local parse, `show` the input's text). M14 (`context = shared`) killed — it survived the old test. |
  | W1 | VC · W | Alias rule's rename `next(...)` over 3 fixed names → `StopIteration` (executed: validate-only "Type: StopIteration") | **Fixed — class: the free-name search is unbounded** (`chain(…, count(2))`; the only fixed-candidate `next(` in `src/` — grep). Row: all short names taken → `as: item_item2`. M11 killed. |
  | W2 | agent-ux · W | `headers: ${d.payload}` on a declared object → "Fix: declare `- type: object` for 'd'" (already is; executed) | **Fixed — class: the declared-text param error names the remedy for text INSIDE an input** (nest / `json.loads`), keeping the whole-input text (PC dev 1, accepted). Remedy split to one home `exceptions.declared_text_fix` (W5 renderer, `DeclaredInputTextError`, this message). Sensitive roots masked (row). M12 (2), M13 killed. |
  | W3 | agent-ux · W | sub-workflows guide: a bad value "fails only that item" — authored inline literals fail validation | **Fixed** (literal vs run-produced split). |
  | W4 | test-fidelity · W | `TestASettingsValueIsLabelledSettings` spawns real CLIs without `e2e` (tests/CLAUDE.md:30) | **Fixed** (`@pytest.mark.e2e`; `-m e2e` 3 passed incl. both, `-m "not e2e"` excludes them). |
  | S1 | simplicity · S | `execute_json_workflow`'s `stdin_data` unused | **Disputed**: read at `cli/commands/run.py:378` (`_cleanup_temp_files(stdin_data, …)`, the binary-stdin temp file). |
  | S2 | simplicity · S | Fold the workflow-type set copies onto `WORKFLOW_NODE_TYPES` | **Handed back as a follow-up (H4)** — the copies in the diff's reach agree; grep found three pre-existing single-spelling checks outside this task (`guide/__init__.py:301`, `prompt_cache_analysis/sub_workflow_walker.py:268`, `core/workflow/validator.py:946`) — the real class, not this task's diff. |
  | S3 | impact · S | parity tests for auto-output + prediction | **Done** (F1, F6a tests). |
  | S4 | conformance · S | final-head PZ evidence | This entry: gates below. |
  | Gap | conformance (inventory) | UNPINNED: MCP JSON text → declared `string`; container-union annotation | **Pinned** (regression guards — would pass pre-gate): `TestMcpCallsPassTypedJson::test_json_text_for_a_declared_string_reaches_the_step_as_text` (presence: `any` parsed), `test_a_union_with_a_container_or_any_is_not_text`. M16, M17 killed. Not pinned: per-binding execution of the fifteen in-tree text→child-`string` bindings (LLM-backed; the mechanism `("workflow","inputs")` is mutation-pinned and PE's 186-file scan found 0 hits). |
  | Clean | concurrency-safety; simplicity (a)–(h) otherwise | — | Recorded clean by the lenses (report "Verified clean"). |

- Changed: `core/{templates,exceptions,user_errors}.py`, `core/prompt_cache_analysis/{analyze,context}.py`,
  `.../stages/discrepancy/predict.py`, `core/workflow/{validator,declared_inputs}.py`,
  `execution/{runner,formatters/success_formatter}.py`, `runtime/engine/{template_errors,template_resolution}.py`,
  `guide/{core.md,features/sub-workflows.md}`, both MCP instruction copies, Task-159 case
  `12-real-world-lyrics-generator/04-guide-auto-detect/expected-stdout.txt` (re-recorded: ONLY that case drifted, ONLY
  from the W3 sentence); tests in `test_declared_input_resolution.py`, `test_workflow_validator_declared_inputs.py`,
  `test_declared_input_entry_points.py`, `test_cache_analysis_per_id_emission.py`.
- **Assumption audit** (drivers in `scratchpads/task-120/gate/audit/`, isolated HOME):
  - (a) MCP `workflow_validate` inherits the declared-default and declared-read rules — **VERIFIED (executed)** via
    `ExecutionService.validate_workflow`: bad default → the §1.2 default block at `inputs.n.default`; `${v.a}`/`${v.b ??
    "fallback"}` on a declared string → both §1.6 errors (R3 sentence on the `??` one); alias → §1.9; object path valid.
  - (b) MCP `workflow_plan` inherits per-item typing and the map — **VERIFIED (executed)**: batch child over `["7","x","9"]`
    → item-1 WARNING with full context (`batch_item_index: 1`, path, source `parent`); execute then plan a cached code step
    reading a declared `string` holding JSON text → step got `str`, plan `cached`/`hash_match`.
  - (c) MCP `workflow_validate` takes no parameters — **VERIFIED (read)**: `mcp_server/tools/execution_tools.py:121-127`
    (only `workflow`), `services/execution_service.py:364` `runner.validate(workflow, {})`; doc `docs/reference/cli/index.mdx:154`.
  - (d) prewarm thresholds — **VERIFIED, with a correction to the framing**: model resolution reads the store after the map
    is installed (`engine.py:895-900`, pinned by `test_prompt_cache_setup_sees_the_declarations`); the token-threshold
    pre-flight builds `AnalysisContext(workflow_ir={})` (`engine.py:378`), so its declared map is `{}` — AND
    `resolve_ref_value` never resolves a workflow-input root there (`context.py:269-279`). Executed: `${d.payload.a}`,
    `${d.k}` (plain field) under `object` and `any` all come back unresolved, prewarm never disabled. The empty map is
    therefore unobservable. Pre-existing limitation (not this task's): the prewarm pre-flight never measures an input's value.
  - (e) other open items: bundle-key readers — **VERIFIED** one reader, `executor_service.build_subworkflow_diagnostics`
    (`:149-151` legacy fallback), used by `batch_errors.py:124`; no web reader (grep). PB's "web spawn via test client only"
    — closed by PF's real-form run (log [14:18]). Plan §8's accepted cost "`--dry-run` does not run the per-item child
    check" is stale — PD built it and (b) executed it.
- Verified: baseline before edits `make test` 11439 passed / 0 failed. After: `make check` rc 0; `make test` **11456
  passed** (+17 new rows, −2 moved to e2e, C1 replaced in place); `make test-e2e` 56 passed / 2 skipped; `make
  test-all-local` **11512 passed / 2 skipped**; Task-159 `verify.sh` **87 passed / 0 drifted / 0 errors** after the one
  permitted re-record. Mutation ledger: 15 killed / 2 survived-and-explained (M6, M15) + gap pins M16, M17 killed. Real
  CLI (isolated HOME): `??` and dynamic-index loop conditions → `Node 'step' loop condition reads ${d.payload.…}: 'd.payload'
  is text…`; alias with all short names taken → `as: item_item2`; JSON auto output `text=true` → `"true"`; headers on a
  descendant → nest / `json.loads` fix.  |  Assumed: nothing new. **Real-HOME note:** the fan-out (as at both mid-reviews)
  wrote its own trace `~/.pflow/debug/workflow-trace-9dbaf964-run-review-lenses-20261011-144317-944570.json`; every
  probe ran under an isolated HOME. `~/.pflow/registry.json` was rewritten at 15:11 with MAIN-checkout paths, by
  another session.
- Deviations/surprises: (1) F3 changes `??` semantics in the resolver for one case (a walk into a declared input's JSON
  text ends the chain unresolved). It applies the principle accepted at mid-review #1 (a declared-text miss is "never an
  absent value") to the fallback operator. Without it, ruling (i) opens a silent fallback the spec forbids ("otherwise
  `${v.a ?? "x"}` becomes a new silent fallback"). Importance 2, reversible, one site. The falsifier should attack it.
  (2) `declared_text_fix` split out of `declared_text_reason`: same text, now with one more caller. (3) F4's first cut
  (refuse any item holding a template) would have dropped the static key checks for items with templated leaves.
  Narrowed to `??` chains, the only shape where a static miss turns into a false literal.
- Self-checks: fully-happy: (a) M6/M15 survive: unobservable today, stated rather than padded with a contrived test.
  (b) The two gap pins are regression guards (pass on the pre-gate code), labelled as such. (c) The output `?? null`
  suggestion fix was not a lens finding: I found it while verifying F3 on the real surface (same class). test-reflect:
  not separately directed; every new row was mutation-checked with a presence half.
- Next: hand back. H1 (child required input from env/settings), H2 (JSON `-o` miss), H3 (#743 note), H4 (workflow-type
  spelling follow-up) need the orchestrator; then the falsifier with `gate/requirement-inventory.md`.
  - Addendum (H3 evidence, executed): a declared output `source: ${text}` over `text: string` = `true` → `--output-format
    json` emits `"out": true` (`success_formatter.collect_declared_outputs` → `parse_json_or_original`); text mode prints
    the text. Same class as F6a, but the reader is a declared OUTPUT's — #743's boundary by ruling; not changed.

## [2026-10-12 00:20] task-orchestrator — completion gate (reading battery) accepted; falsifier launched
- Did: read G1's [15:26] entry; accepted 15 fixes (each names its class), S1 disputed (verified `run.py:378`), the
  assumption audit (a)–(e) VERIFIED. Committed `a0528d02`. Launched `review-falsifier` directly (last, on `a0528d02`)
  with the spec, `scratchpads/task-120/gate/requirement-inventory.md`, the ruled checkpoint and the [23:30] rulings →
  `scratchpads/task-120/falsifier/report.md`.
- Dispositions of G1's hand-backs: F3 (`??` never falls past a declared-text miss) — ACCEPTED (2/5; the spec's "no new
  silent fallback"; the falsifier's first target). H2 → filed **#785** (pre-existing class; stderr warning recommended).
  H3 → evidence commented on **#743** (declared-output reader, that issue's boundary). H4 → filed **#786** (single-spelling
  workflow-type checks). **H1 (3/5) → user escalation**, bundled with any falsifier escalation into ONE handback: a
  REQUIRED child input supplied only by env/settings — static child refused at validation, run-time-chosen child accepted
  (main refused both); options A (validator honours env — environment-dependent validation), **B (required child input
  with no default must come from the parent; env/settings fill only optional child inputs — matches main, static ==
  dynamic; recommended)**, C (document the mismatch).
- Open: `~/.pflow/registry.json` rewritten 15:11 with MAIN-checkout paths by another session (G1 observation; not ours).
- Next: falsifier report → G1 evaluates it → bundle H1 + any 3+/ambiguous falsifier item → hand back.

## [2026-10-11 16:13] G1 (Opus) — falsifier report evaluated (`scratchpads/task-120/falsifier/report.md`, on `a0528d02`)
- Did: re-executed every item with the falsifier's wrappers (`falsifier/p.sh` branch, `pm.sh` main; isolated HOME
  `falsifier/home`) and drivers in `scratchpads/task-120/gate2/`; fixed W2, S1, S2, S5, S6 with tests; W1, S3, S4, O1
  and the two main-broken items dispositioned below (no code).
- Dispositions:

  | # | Sev | Verified | Disposition |
  |---|---|---|---|
  | W1 | W | Executed: `alias3` validate-only ✓, then `each` parses the item's JSON text while `direct` fails; `agent2` prompt `doc.a=1` from declared string `v` | **Handed back (user, beside H1)** — options below. Not fixed, as instructed. |
  | W2 | W | Executed: `secfield` printed `hunter2SECRET` in the reason + nest example (6 JSON copies); MCP `{"s": {"password": …}}` printed it in `received` and the fix line | **Fixed — class: every new message renders a value through the repo's display-redaction convention.** One primitive `security_utils.redact_for_display(names, value)`: `<REDACTED>` when any name on the path is sensitive, else `redact_sensitive` — also inside JSON object/array TEXT (bytes kept when nothing is redacted). Routed: `InputTypeError._shown` (`received`, message, context), the fix line (falls back to the canonical example whenever anything was hidden), and `exceptions.shown_declared_text` (path-aware) — the one display rule for the §1.14 reason, `DeclaredInputTextError`, `unparsed_text` (template_errors) and the declared-text param error. Re-run: secret count 0 in text and JSON on both repros. N1–N4 killed. |
  | S1 | S | Executed: MCP 400-key object → 5 802-char fix line | **Fixed — class: a fix line or example never carries more of the value than the message's 80-char cap** — `_fix_example` (every source) and `declared_text_fix`'s nest example fall back to the generic form past 80 chars; the nest example is also withheld when it would carry a redaction (it exists to be pasted). Re-run: longest line 211. N5–N7 killed. |
  | S2 | S | Executed: child env error says `or pass port=3`; following it → `Unknown input 'port'` | **Fixed — class: at a sub-workflow boundary the "pass it instead" half names the calling step's `inputs:`** (env AND settings; `InputTypeError._passed`): `export port=3, or pass \`port: 3\` under step 'call' \`inputs:\` (a passed value wins over the environment)`. Root text unchanged. N8 killed. |
  | S3 | S | Executed: `analyze-cache … --format=json` → one `error` with two messages joined by `\n`, no `path`/`input` | **Follow-up, not now**: the fix changes the analyze-cache envelope contract (`format_version` 5.0, single `error` object). Recommend an issue for an additive `errors[]` beside `error`; the text surface and MCP already keep each input's diagnostic separate. |
  | S4 | S | Executed: `loopp start=9` carry error placed at `params.inputs.n` | **Handed back**: the clean fix needs the carried-key set on the host node — a compile-time stamp of the same shape the user declined for the §1.5 clause (D1=B). Options: A stamp carried keys on the `WorkflowExecutor`, path `nodes[id=run].loop.carry.n` from iteration 2; B leave (the message names the input and value; the carry is in the workflow). Rec **B**, revisit together with D1-A if ever. |
  | S5 | S | Executed: MCP `{"b": 1}` → `accepted: "true or false (also yes/no, 1/0)"` | **Fixed — class: `accepted` describes the form the value came in** — the text grammar for text, the typed values (`accepted_noun`) for a typed value. N9 killed. |
  | S6 | S | Executed: `ptok` → message `<REDACTED>`, next line `item: 'sk-ITEMSECRET'` (also JSON `item_summary`) | **Fixed — class: a batch record never re-prints a value its child-input message masked** (`batch_executor`: the item summary's text becomes `<REDACTED>` when the bundle's diagnostic shows `received: <REDACTED>`; identity fields kept). Presence row: a plain-named input keeps `item: 'sk-SECRET'`. N10 killed. |
  | O1 | obs | Executed: `i=abc … --validate-only b=true` ✓, the run exits 1 with the env-source error | **No change (by design, D6).** View for H1: validate-only is env-blind at the root, so H1-A (validator honours env for child inputs) would make child validation env-dependent while root validation is not — a second inconsistency; it supports H1-B. |
  | main-1 | pre-existing | Reproduced on branch AND main: `w/pff2.pflow.md` (6 shell items, `parallel: true`, `max_concurrent: 2`, `fail_fast`, item `b` exits 1) → `[3] Executor error:` `[4] Executor error:` `[5] Executor error:` with no message | To file (orchestrator). Evidence line: "Parallel `fail_fast`: items cancelled after the first failure are reported as `Executor error:` with an empty message (`w/pff2.pflow.md`, identical on `origin/main`)". |
  | main-2 | pre-existing | Reproduced on branch AND main: `w/pmut.pflow.md` + `w/cmut.pflow.md` (child `o: object`, `default: {"k": 1}`, code mutates `o["seen"]`), batch `[1, 2, 3]` → `seen` 1, 2, 3 | To file. Evidence line: "A container `default:` is one shared object across child calls — a child that mutates it leaks into later items (`seen` 1→2→3; identical on `origin/main`)". Fix site on this branch: `ir_preparation._fallback_value` returns the IR's default object itself (`:84-85`) — copy a container default per resolution. |

- **W1 options (for the user, beside H1).** What happens: the rule keys on the reference ROOT's active binding
  (`templates._declared_typed`). A step `inputs:` key bound to `${v}` (the value resolves protected — text) or a batch
  alias over `${rows}` is a new root that is not in the map, so `${doc.a}` / `${item}` into a container parse the text.
  - **A — binding provenance at the two binding sites.** A step `inputs:` key or batch alias whose value is ONE whole
    reference rooted in a declared non-`any` input inherits that root's protection. Sites: `_bind_locally` keeps the
    name in the map with the root's type instead of dropping it; the per-item store adds `alias → <root type>` when
    `batch.items` is such a reference. Mirrors needed in the planner's per-item context and the validator
    (`declared_root_type` / `step_scope`): rules (b)/(c) apply to the new name, and an alias is protection-only
    because the element type is unknown. ADR-0017 text touched: the decision sentence "a reference whose root is a
    declared non-`any` input is never JSON-parsed" gains "…or a name bound to one by a single reference", and
    Considered Options ¶1's "the per-step shadow rule (a step's own `inputs:` key wins)" gains the provenance
    exception. The rejected "Tag the VALUE" stays rejected: this is binding provenance resolved from the authored
    template, and a node output never inherits it. Cost: engine contact (`template_resolution`, `batch_executor`),
    planner and validator, so a plan and a targeted re-review.
  - **B — by design; correct the promise.** Protection follows the reference root (ADR-0017's literal sentence); a
    rebinding takes the new name's semantics. Fix the overclaim "`${input}` … at every step" in `guide/core.md:454`
    and both MCP copies (`:1037` / `:1016`). Docs only.
  - **C — validator-only.** Flag statically a step `inputs:` key bound to a declared `string`/scalar that is then read
    with a path or into a container (the only certain shapes). Runtime unchanged; a rebound `object`/`array`
    descendant's text still parses.
  - Blast radius (`gate2/scan_w1.py` → `gate2/scan_w1.txt`, 172/186 parseable in-tree workflows): 168 rebindings
    (155 step `inputs:` keys, 13 batch aliases). 11 read the new name with a path, all `${item.text}` over a declared
    `array` of objects. A does not change those (the elements are already objects), so **0 in-tree behaviour changes**.
  - **Recommendation: A.** It is what the user's ruled sentence says ("decided once … nothing downstream re-infers
    it"), the in-tree blast radius is zero, and it avoids the value tagging ADR-0017 rejected. Build it in this task
    under a targeted re-review. If the PR must go now: B's doc correction now and A as the immediate follow-up.
- Changed: `core/{security_utils,exceptions}.py`, `runtime/engine/{template_errors,batch_executor}.py`; tests:
  `test_core/test_param_coercion.py` (+7 rows), `test_runtime/test_declared_input_resolution.py` (+3),
  `test_runtime/test_workflow_executor/test_child_input_boundary.py` (+2, with a `_values_under` JSON walker).
- Verified: `make check` rc 0; `make test` **11469 passed** (11456 + 13); Task-159 `verify.sh` **87/0/0** (no guide text
  changed this round; run because message text did); mutation ledger `gate2/mutants.json` **10/10 killed** (same
  harness: content restore, `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` purged before/after, counted). Real surface:
  W2 repros → 0 secret occurrences (text + JSON + MCP), S1 longest line 211, S2 new fix line, S6 `item: <REDACTED>`.
  |  Assumed: nothing.
- Deviations/surprises: (1) `redact_for_display` extends `redact_sensitive`'s convention into JSON TEXT, which its
  docstring had scoped out ("a secret inside a free-text string has no key to match"). JSON text has keys, and the new
  messages quote JSON text, so this is a narrow, additive extension (importance 2). Free text stays the accepted
  boundary. (2) The S6 fix masks the item line only when the child's message masked, which keeps the pre-existing
  item summarizer's behaviour everywhere else.
- Self-checks: fully-happy: (a) the first S6 test version tripped on the parent's auto-output (it legitimately holds
  the item), so it was narrowed to `item_summary`; (b) two guards first had no test (the nest-example cap and the
  redaction exclusion), so a direct row was added before the ledger. test-reflect: not separately directed; each row
  has a presence half.
- Next: hand back. W1 and H1 go to the user; S3, S4 and the two main-broken items go to the orchestrator.

## [2026-10-12 01:10] task-orchestrator — PARKED on user escalation (H1 + W1); falsifier evaluated
- State: head `8730db0f` (after this entry's commit, one more). Completion gate reading battery (9/9 lenses) + falsifier
  done and evaluated by G1 ([15:26], [16:13]); all fixes committed (`a0528d02`, `8730db0f`). G1's last gates:
  `make check` rc 0, `make test` 11469 passed, Task-159 `verify.sh` 87/0/0; `make test-all-local` last run at
  `a0528d02` (11512 passed / 2 skipped) — re-run at close-out. No `pflow ui` server running.
- Dispositions this step: falsifier W2/S1/S2/S5/S6 FIXED (classes in [16:13]); S3 → **#791**; S4 + the D1 clause →
  **#792** (host never sees its authored `inputs:`/carry keys); main-broken items → **#789** (parallel fail_fast empty
  `Executor error:`), **#790** (container default shared across calls; fix site `ir_preparation._fallback_value`); O1 by
  design (D6).
- Asked of the user (ONE handback): **H1 (3/5)** required child input supplied only by env/settings — rec **B** (must
  come from the parent; env/settings fill only optional child inputs; matches main; O1 supports it). **W1 (3/5)** a
  declared input rebound to a batch alias or a step `inputs:` key regains JSON parsing — options A (binding provenance at
  `_bind_locally` + per-item alias; planner + validator mirrors; ADR-0017 sentence amended; 0 in-tree behaviour changes
  per `scratchpads/task-120/gate2/scan_w1.txt`), B (by design; correct "at every step" in guide + both MCP copies), C
  (validator-only flag) — rec **A in this task** (engine contact → a plan addendum + targeted re-review), fallback B now +
  A follow-up. Optional ask: fold #790 (one `deepcopy` at the boundary this task rebuilt) into this PR?
- Exact resume point: on the rulings — (1) H1: if B, G1-or-fresh Opus implements in `prepare_inputs`'s child caller
  (`_Caller`/`type_child_inputs`) + validator `_check_required_inputs` parity + tests; (2) W1: if A, I write a short plan
  addendum (sites, mirrors, ADR-0017 wording for the main orchestrator), a fresh Opus implementer builds it, then a
  targeted re-review (`validation-consistency` + `feature-interactions` on that diff) and a re-run of the falsifier's W1
  probes; if B, doc edits in guide/core.md + both MCP copies + re-record `12/04-guide-auto-detect` if it moves; (3) merge
  `origin/main`, `make check` + `make test-all-local`, verify.sh, `capture.py --check` vs P0's 5; (4) spec Status done +
  Completed; `create-task-review`; `create-pr` closing #686, #687, #188 (Refs #297, #742, #743 — not closing PRs);
  check `closingIssuesReferences`.

## [2026-10-12 01:40] task-orchestrator — H1/W1/#790 RULED; main merged; plan addendum §10 (PG)
- Ruling (user via main orchestrator, 2026-10-11, recommendations accepted): **H1 → B**; **W1 → A in this task** (plan
  addendum + targeted re-review on the W1 diff; one-line ADR-0017 amendment text goes in my completion hand-back);
  **#790 → fold** (PR closes it, stated as pre-existing). Closing keywords: #686, #687, #188, #790; #297/#742/#743 Refs.
- Did: merged `origin/main` (#787 `714df226` one printed Diagnostic form, #780 anyio, #779 MCP discovery) → `dfd47816`.
  Conflict only in `.claude/agents/review-agent-ux.md` (+ codex sync): the rerun-display row (module deleted here) dropped,
  main's Security-utils wording kept. Gates on the merge: `make check` rc 0, `make test` 11478 passed (4 third-party
  starlette warnings). Wrote plan §10 (D15 W1 binding provenance, D16 H1, D17 #790) — `ed8d637b`.
- Pending coordination: lane #783 re-records `12/04-guide-auto-detect` + fixes `verify.sh`; if it lands before my next
  merge, re-run `regenerate.sh` on that case after merging so this branch's guide re-record wins.
- Next: fresh Opus · high I5 for PG (+ its targeted re-review as gate-runner).

## [2026-10-11 17:19] I5 (Opus) — PG (D15 W1 binding provenance, D16 H1 required child inputs, D17 #790 fresh defaults) · ENGINE CONTACT · + its targeted re-review as gate-runner
- Did, per decision:
  - **D15.** One pure rule in `core/templates.py` beside `DECLARED_INPUT_TYPES_KEY`: `bound_reference` (the authored
    value IS one whole single-operand, non-`|json` Expression), `bound_declaration(authored, declared)` (whole root →
    the root's map entry; a path → `PROTECTION_ONLY = "protection-only"`, a map VALUE, one constant, no second key;
    anything else → `None`, local), `batch_item_declaration(items_template, index, declared)` (inline element by its
    own text; any item of a whole reference → `PROTECTION_ONLY`), `bind_declared(store, entries)` (rebinds names in a
    step's/item's own copy; `None` removes). Runtime: `template_resolution._bind_locally(context, authored)` at BOTH
    merge points (static inputs → all literal → local; resolved `inputs:` → per key from `template[k]`, which under a
    loop is the carry template from round 2 because `carry_effective_config` rewrites `template_params` — so the
    loop-carry mechanism needs nothing extra; whole-map `inputs: ${m}` → every key local, as before);
    `batch_executor.bind_batch_item(item_store, parent_store, batch_config, item, index)` (alias + `__index__` + the
    alias entry computed against the PARENT's map, i.e. where `batch.items` resolved) at the compile prewarm and the
    per-attempt site; the planner's three per-item contexts (item 0, per-item `inputs:`, child-per-item) call it on a
    copy of the planner store (the old set-then-pop on the shared store is gone). Validator mirror:
    `declared_inputs.declared_root(...) -> (type, inputs) | None` (renamed from `declared_root_type`; CLAUDE.md rows
    updated) over `_declared_scope`: workflow inputs, the alias bound first, a step's `inputs:` keys for its other
    params, a carried key only when round 1 and the carry template agree, an inline alias only when every element's
    entry agrees (`_agree`); `PROTECTION_ONLY` → `None`. `_declared_reads` emits one error per input behind a name;
    `type_validation._declared_text_into_container` reads the same helper. Messages name the input through the
    binding: `Input 'v' (as 'doc') is declared …` / fix `… if 'v' holds …`, context `input: v`.
    Analyzer synthetic contexts (`prompt_cache_analysis/context.py:178`, `token_estimation.py:483`): **no mirror** —
    they resolve only declared-input roots (parameters) and node ids (memo) (`resolve_ref_value`, `context.py:255-283`;
    `build_shared_store_for_refs`), never a step's `inputs:` key or a batch alias (the alias is only a per-item
    position marker there). The VC lens concurred.
  - **D16.** `ir_preparation._fallback_value(…, caller)`: at the child placement (`caller.step`) a `required` input
    whose default is absent or `null` takes no fallback → the child-named "requires input" error, with the remedy
    `Pass it under step 'call' \`inputs:\` (a required sub-workflow input is never read from the environment or
    settings)` (`_Caller.required_fix`; root unchanged, no suggestion there). Validator `_check_required_inputs` now
    reads `default: null` as no default (`get("default") is not None`, the boundary's rule) — static == run time.
  - **D17.** `_fallback_value` returns `copy.deepcopy` of a declared default. Grep of `"default"` reads in the boundary
    and validator paths: `_fallback_value` is the only site that hands a default to a run (`validator._check_input_defaults`,
    `path_validation`, describe/graph formatters only read it).
- Docs: the ONE sentence in `guide/core.md`, both MCP instruction copies (identical): "A step's `inputs:` key or a batch
  alias bound to one whole reference to such an input (`doc: ${input}`, `items: ${input}`) keeps that protection; a
  binding with `??` or text around the reference is parsed like a step output." D16 in `guide/features/sub-workflows.md`.
  CLAUDE.md: `runtime/engine`, `core`, `core/workflow`, `runtime`, `runtime/compilation`, `runtime/template_validation`.
  `docs/how-it-works/template-variables.mdx:125` left (still true: it speaks of a reference rooted in an input).
  Task-159 `verify.sh`: 1 drift, only `12/04-guide-auto-detect`, only my sub-workflows line → re-recorded with
  `run-case.sh … --write` (+1 line); re-run **87/0/0**.
- Changed: `core/{templates.py,workflow/declared_inputs.py,workflow/validator.py}`, `runtime/engine/{template_resolution,
  batch_executor,template_errors}.py`, `runtime/compilation/ir_preparation.py`, `runtime/template_validation/type_validation.py`,
  `execution/plan.py`, guide ×2 + MCP ×2, 6 CLAUDE.md, Task-159 case `12/04` expected-stdout; tests:
  `test_runtime/test_declared_input_resolution.py`, `test_runtime/test_template_validation/test_declared_input_rules.py`,
  `test_integration/test_template_parity.py` (+7 rows; `_drive_batch_param` now builds the item store with
  `bind_batch_item`), `test_execution/test_plan_drift.py`, `test_runtime/test_workflow_executor/test_child_input_boundary.py`.
- Tests flipped: **none** — no existing test asserted env/settings satisfying a required child input (full suite green
  after D16; grep of env-using child tests found only root/defaulted cases), and no test pinned W1's parse. Touched, not
  flipped: `test_plan_and_engine_hand_a_batched_child_the_same_text_inputs` (engine side now builds its item store with
  `bind_batch_item` instead of a hand-made dict). New: `TestABindingKeepsItsInputsProtection` (6 binding shapes +
  same-named), `test_a_batch_alias_is_protected_by_where_its_items_came_from` (seq/par), `test_a_protected_item_into_a_
  container_param_says_where_the_text_came_from`, `test_a_carried_key_is_protected_in_round_one_and_local_once_carried`,
  `test_the_parallel_compile_prewarm_reads_item_zero_as_the_run_does`; `TestABindingCarriesTheDeclaration` (6);
  parity rows `bound_declared_string_field`, `bound_declared_object_descendant`, `bound_node_output_is_local`,
  `bound_coalesce_is_local`, `alias_of_a_declared_array`, `alias_of_a_declared_array_path`, `alias_inline_follows_each_element`;
  drift `test_plan_and_run_refuse_a_walk_into_a_batch_items_declared_text` (×4), `test_plan_keeps_every_item_of_a_child_
  per_item_batch_when_one_cannot_resolve`, `test_plan_reports_every_item_when_no_child_per_item_survives`; D16 ×6
  (incl. `default: null` both verdicts), D17 seq/par.
- **Mutation ledger** (`pg/mutate.py` = G1's harness: content restore, `PYTHONDONTWRITEBYTECODE=1`, every `__pycache__`
  purged before/after, kill = counted failures; `pg/mutants*.json|txt`): **33 killed / 0 surviving**. P1-P20 (D15: drop
  provenance, second merge, path→type, `??` inherits, alias whole/inline, `bind_batch_item` map, per-attempt site, prewarm
  site, the 3 planner sites, protection-only message, validator unanimity/carry/inputs-param/naming/alias/container),
  D16a-f, D17, Z1-Z3 (planner zip/report), R1-R4 (review fixes). First pass had 4 survivors → each resolved: P9 (parallel
  worker binding) was redundant with the per-attempt binding → **deleted the redundant site**; P10 (prewarm) → new test
  where the prewarm would compile a child the run never calls; P11/P13 → sharpened drift assertions per mode.
- **Re-review** (pflow fan-out, codex, 2 lenses with per-lens targets `pg/lenses.json`, scope `git diff 151d703a`
  incl. uncommitted; run under an isolated HOME + isolated `CODEX_HOME` symlinked to the auth/config; report
  `pg/review.md`, read in full; **coverage 2/2**, 290 s):

  | # | Lens · sev | Finding (verified) | Disposition |
  |---|---|---|---|
  | C1 | VC · C | Inline alias `["${s}", "${t}"]` (both `string`): validator dropped the alias (unanimity compared input AND type), run protects each item → `${item.a}` certain miss, validator silent (read `_item_binding`; my own test encoded it) | **Fixed — class: the mirror is certain exactly when every case shares one ENTRY, whatever inputs supply it** (`_agree` keys on the entry, keeps every input; `_declared_reads` emits one error per input, each certain for its items; carry agreement uses the same `_agree`). Test rewritten (`…_of_one_type_is_checked_for_each_input`: two errors s/t; `${s}`+`${n}` none; literal none). R1-R3 killed. |
  | C2 | FI · C | Batch memo key = config + items only, so a declaration change (`rows: any`→`array`) serves the stale per-item result | **Handed back — #675's class.** Executed: on the PRE-PG source a batched `y: ${s}` with `s: any`→`string` already serves stale `dict` (`pg/w/memo2.pflow.md`), and a VALUE change of `s` is stale too (#675 itself). PG adds the alias as one more read the key misses. #675's closing mechanism ("the key covers every resolved input the item execution reads") closes it; it changes every batch node's memo key, so not in PG. Note for #675: Task 120 (PC, and now D15) made a DECLARATION change alter item semantics — a new dimension of that issue. |
  | W1 | FI · W | All items of a child-per-item batch rejected → empty roll-up drops every per-item diagnostic (my zip fix had turned a crash into silence) | **Fixed — class: every per-item planner rejection reaches the plan, whether or not a child plan survives** (`_aggregate_batch_child_plans` empty branch keeps `extra_diagnostics`). Test + R4 killed. |
  | Clean | both | Whole-root/path/`??`/text-around/same-named/carry/whole-map/D16/D17/analyzer scope/nested isolation/seq-par-retry-prewarm/output readers | Recorded clean by the lenses (read-only; they executed nothing — my tests/probes cover execution). Lens "testing limitations": retries and resumed loops have no PG-specific test — by construction (`_run_batch_item_once` rebinds from the parent map every attempt; a resumed loop resolves through `carry_effective_config` at its saved iteration, read `loop_control.py:96-119`); no discriminating test exists to add. |
- **W1 probes** (`falsifier/p.sh`, isolated HOME; `pg/w1-before.txt` → `pg/probes-final.txt`): `alias3` — `each` and
  `direct` now both fail `Input 'x' expects dict but received str` (before: `each` parsed); `agent2` — validate-only
  `Input 'v' (as 'doc') is declared \`- type: string\`, so \`${doc.a}\` cannot read a field of it…` (before ✓ + `doc.a=1`),
  and the resolver leaves `${doc.a}` unresolved (`TestABindingKeepsItsInputsProtection`); `agent` (same-named) refused;
  `alias2` `${item.payload.a ?? "fb"}` now fails like `alias`'s `${rows[0].payload.a ?? "fb"}` (before: `item=1`);
  `pmut` → `seen` 1,1,1 + again 1 (before 1,2,3); D16 run-time child with `n` exported → each item refused with the
  remedy, static twin refused at validation.
- **Scans**: G1's `scan_w1.py` on the built code — byte-identical to `gate2/scan_w1.txt` (168 rebindings, static).
  New `pg/scan_w1_impact.py` (the BUILT `bound_declaration`/`batch_item_declaration`): 169 inheriting bindings, 20 reads
  of a bound name — 11 `${item.text}` over arrays of objects (verify.sh feeds `{"text": …}` objects; a field of a dict,
  no parse), 1 `${item}` into a workflow step's `inputs:` (always text), 8 `cwd: ${repo_dir}` (a `str` param, never
  parsed) → **0 behaviour changes**. New `pg/scan_w1_validate.py`: `--validate`-equivalent over all 186 in-tree
  workflows, built vs pre-PG source (`git archive 151d703a` on `PYTHONPATH`, isolated HOME) → **identical** (326 lines),
  re-run after the review fixes → identical.
- Verified: baseline `make test` 11478 passed (orchestrator); after: `make check` rc 0; `make test` **11528 passed /
  0 failed** (before test-reflect; test-reflect then deleted 1 test and deepened 1 — both files re-run green, 108
  passed; full suite NOT re-run after, see the HOME note); `verify.sh` 87/0/0; mutation 33/33.  |  Assumed: nothing
  open — analyzer scope, retries and resumed loops verified by reading (cited above).
- **REAL-HOME WRITE — STOP/hand-back item:** `~/.pflow/registry.json` was rewritten at **17:14:53** with THIS worktree's
  node paths, inside my final `make test` window (17:14:44–17:15:28). Nothing I ran pointed pflow at the real HOME
  (probes via `p.sh`, scans/fan-out with `HOME=` set, the fan-out's own trace landed in `pg/home`); the global `pflow`
  alias uses the MAIN checkout, so a worktree-path registry implies a process importing this worktree under the real
  HOME — most likely a non-e2e test that spawns a fresh interpreter without HOME isolation (lead, read only:
  `tests/test_cli/test_ui.py:1205` runs `python -c "import pflow.cli.commands.ui"` with the inherited env; conftest
  patches `Registry`'s default path in-process only). Not attributed by experiment — I did not re-run `make test` to
  avoid writing again. Other sessions (loudkult `act`/`screenshot`/… traces) also write `~/.pflow/debug` concurrently.
- Deviations/surprises: (1) **Validator messages name the input through a binding** (`Input 'v' (as 'doc')`, fix and
  `context.input` = `v`) — §10 said "the existing rules then fire"; firing with the binding's name would tell an agent
  to declare a type on an input that does not exist. New user-visible text → needs your ruling (show-before-code).
  (2) **A protection-only runtime type error has its own message**: `Parameter 'output_schema' expects dict but
  ${item} is text taken from a declared input — a declared input is never JSON-parsed.` + the text remedies — the
  existing one would print `declared \`- type: protection-only\`` and "declare object for 'item'". Same ruling.
  A canonical-type binding at run time still reads "reads input 'doc', declared `- type: string`" — reachable only past
  the validator's (c) rule, so left. (3) `declared_root_type` → `declared_root` returning `(type, inputs)`.
  (4) `_check_required_inputs`: `default: null` is no default (closes a static/run mismatch inside D16's class).
  (5) **Planner, pre-existing on `origin/main` (read): a child-per-item batch with any item failing its params crashed
  `--dry-run` (`zip() … shorter`)** — exposed by the D15 drift test; fixed (empty output slot per skipped item; a
  skipped child's problem becomes a per-item WARNING; the empty roll-up keeps diagnostics — W1). (6) The parallel batch
  worker's own alias assignment removed (redundant with the per-attempt binding). (7) C2 → #675 (above).
- Self-checks: fully-happy — doubts raised and resolved: the inline alias unanimity was wrong (C1, fixed); the zip fix
  briefly silenced an all-rejected batch (W1, fixed); two planner/prewarm sites were unpinned (now pinned). Remaining
  doubt: the real-HOME registry write (handed back). test-reflect (directed): **deleted**
  `test_a_bound_whole_read_is_the_inputs_text` (a `str` prompt is never parsed with or without D15 — it could not
  fail); **deepened** `test_a_binding_that_carries_no_type_is_not_checked` (presence half: the same `${doc[0]}` read
  through a typed binding errors); labelled `test_a_named_child_refuses_the_same_omission_statically` a regression
  guard (passes on pre-PG code; the static verdict §10 asked to keep pinned). Every other new test is mutation-killed.
- Next: hand back — rulings on deviations (1)(2); the real-HOME write; C2/#675 routing; ADR-0017 line in the handback.

## [2026-10-12 02:30] task-orchestrator — PARKED: real-HOME write reported by I5 (packet stop condition); PG committed unverified-by-me
- Did: read I5's [17:19] entry; committed PG as-is (D15 W1 binding provenance, D16 H1, D17 #790, re-review fixes C1/W1,
  guide sentence + the one-case re-record of `12/04-guide-auto-detect`) so nothing is lost while parked. I did NOT re-run
  `make test` (it is the suspected writer). `origin/main` NOT yet merged (#783 `e0f3af7d` pending — acknowledged: after
  merging, re-run `regenerate.sh` on `12/04-guide-auto-detect` so this branch's guide text wins on top of #784's
  recording, run the fixed `verify.sh` once, and name both causes in the PR body).
- Stop condition (packet §Claims 3): I5 observed `~/.pflow/registry.json` (REAL home) rewritten at 17:14:53 with THIS
  worktree's paths inside its final `make test` window (17:14:44–17:15:28). Every probe of I5 ran under an isolated HOME;
  its fan-out ran with a separate HOME/CODEX_HOME. Read by me (not executed): I5's lead
  `tests/test_cli/test_ui.py:1203-1207` (`TestLazyImportBoundary`, pre-existing since `0b246c3d` Task 94, not in this
  diff) runs `subprocess.run([sys.executable, "-c", "import … pflow.cli.commands.ui"])` with the inherited environment —
  whether that environment carries the isolated HOME, and whether the import writes the registry, is UNVERIFIED.
  Current `ls -la ~/.pflow/registry.json` → mtime **17:19** (after I5's window — another writer exists too; G1 saw a
  15:11 rewrite with MAIN-checkout paths, "another session"). Earlier fan-outs (mid-reviews #1/#2, G1) ran `uv run pflow
  workflows/review/run-review-lenses.pflow.md` under the real HOME by the skill's design — any such run rescans/rewrites
  the registry with the running checkout's paths.
- Also asked: C2 (batch memo key covers items only — #675; Task 120 adds a trigger: a declaration change alters what each
  item receives) — rec: leave to #675, append Task 120's trigger as evidence; two new message shapes (validator names the
  source input through the binding `Input 'v' (as 'doc') is declared …`; protected item/path binding into a container
  param `… but ${item} is text taken from a declared input …`) — rec accept; two out-of-§10 changes accepted at 2/5
  (pre-existing `--dry-run` crash on a per-item child batch fixed; validator treats `default: null` as no default —
  static == run-time).
- Exact resume point: on the ruling about the real-HOME write — (1) if a test is the writer: fix it in this PR only if
  ruled (it is pre-existing), else proceed; (2) merge `origin/main` (#783), regenerate `12/04`, `make check` +
  `make test` + `make test-all-local`, fixed `verify.sh` (all 87 ran), `capture.py --check` vs P0's 5; (3) spec Status
  done + Completed; `create-task-review`; `create-pr` closing #686 #687 #188 #790 (Refs #297 #742 #743); check
  `closingIssuesReferences`; `gh pr checks` incl. `tests-windows`.

## [2026-10-11 17:30] task-orchestrator — real-HOME ruling applied; main merged; final gates green; close-out
- **Timestamp correction:** my task-orchestrator entries headed 20:40 → 02:30 (and "2026-10-12") carry invented clock
  labels — the real clock was ~13:xx–17:2x on 2026-10-11 (`date` now: 17:29). Their ORDER in this file is correct;
  read their headers as sequence labels, not times. Implementers' headers are their own clocks.
- Ruling (main orchestrator): the real `~/.pflow/registry.json` rewrite is the registry's own path re-scan when another
  checkout runs pflow (MCP entries intact) — benign class; (a) the suspected test writer is ROUTED to its own issue, not
  this PR; (b) tests resumed — a real-HOME touch is logged by mtime, an MCP entry changing/vanishing stays a hard stop.
  Smaller: C2 → evidence posted on **#675** (read back); I5's two new message shapes ACCEPTED (2/5); the two
  out-of-§10 changes ACCEPTED, named in the PR body as pre-existing-on-main with their pinning tests.
- Did: merged `origin/main` `e0f3af7d` (#783, fixed `verify.sh`, `baseline-oracle` CI job) → `7a125a09`, no conflict;
  `regenerate.sh 12-real-world-lyrics-generator/04-guide-auto-detect` → no change (the merged recording already carries
  BOTH causes: this task's guide text + #775's `COOKIE`). Spec `## Status: done`, `## Completed: 2026-10-11`.
- Verified (final head before the close-out commit): `make check` rc 0; `make test-all-local` **11588 passed, 2 skipped**
  (4 third-party starlette warnings); fixed `verify.sh` **87 passed / 0 drifted / 0 harness errors** (all cases ran);
  `capture.py --check` → 29 examples, **12 differing — byte-identical output to the same check run on a clean export of
  `origin/main` `e0f3af7d`** (so 0 differences are this task's; P0's 5 + 7 from main's #787 flattened-copy removal etc.;
  main's Task-170 capture baseline is stale — routed up). Real HOME: `registry.json` mtime 17:24:38 → 17:26:28 across
  `make test-all-local`; MCP tool counts unchanged (chrome 59, heptabase 20, hokuz 2, notebooklm 53, playwright 62,
  resend 106, sentry 8); the 11 built-in paths point at the main checkout — benign class per ruling.
- Assumptions: none open — the [11:45]…[17:19] `Assumed:` items are resolved by G1's audit (a)–(e), PF's real-form run,
  and I5's entry ("Assumed: nothing" after its own verification); I5's real-HOME lead is routed, not assumed.
- Next: `create-task-review`; `create-pr` closing #686 #687 #188 #790 (Refs #297 #742 #743).
