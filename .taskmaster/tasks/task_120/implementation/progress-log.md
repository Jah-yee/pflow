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
