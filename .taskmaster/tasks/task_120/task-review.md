# Task 120 Review: Declared Input Types Are Honoured — Strict at the Boundary, Never Re-Inferred

## Metadata
- Built 2026-10-11 on `feat/task-120-declared-input-types` from the Fable planner's plan (CP-1 ruled 2026-10-10). Main was merged in five times, the last at `e0f3af7d`. The PR is opened at close-out and closes #686, #687, #188 and #790 (#790 is pre-existing on main, folded in by ruling). #297, #742 and #743 are Refs only. Not a trace-format change.
- Who built what, orchestrated by the task orchestrator:

  | Agent (Opus) | Work |
  |---|---|
  | I1 | P0, PA, PC, mid-review #1 |
  | I2 | PB, PD |
  | I3 | PE, mid-review #2 |
  | I4 | PF and the web run form, plus the settings label and checkbox fixes |
  | G1 (gate-runner) | 9-lens completion gate + falsifier evaluation |
  | I5 | PG: the W1/H1/#790 rulings plus its targeted re-review |

- Where things are recorded:
  - Contract: ADR-0017. The main orchestrator amends it with the binding-provenance sentence (below).
  - Journey, every ruling, mutation ledgers and dispositions: `implementation/progress-log.md`. Orchestrator entry headers between the PE acceptance and the close-out carry invented clock labels; their order is right, see its 17:30 entry.
  - Ruled message text: `implementation/diagnostics-checkpoint.md`, as amended by the user-checkpoint ruling in the log (D1–D5).

## Read First — the load-bearing block
- **What exists now:** a workflow input's value is typed ONCE, where it enters, by its `## Inputs` type, through one coercer. A value that doesn't fit is an `Invalid input value` Diagnostic naming its source. Wherever a reference's root is a declared non-`any` input, the value is never JSON-parsed again. That holds root-wide, for every consumer, and for any name bound to such an input by a single whole reference. The CLI never guesses types; `any` infers losslessly from CLI and web-form text only.
- **Read these first:**
  - `core/param_coercion.py`: `coerce_declared_input`, `InputSource`.
  - `core/types.py`: `TypeSpec.parse_text` (the strict grammar).
  - `core/exceptions.py`: `InputTypeError` and `.located()`; `DeclaredInputTextError`; `declared_text_reason` / `declared_text_fix`.
  - `runtime/compilation/ir_preparation.py`: `prepare_inputs`, `_fallback_value`, `check_supplied_inputs`.
  - `core/templates.py`: `DECLARED_INPUT_TYPES_KEY`, `_declared_typed`, `PROTECTION_ONLY`, `bound_declaration`, `batch_item_declaration`, `bind_declared`, `declared_text_stop`, `declared_text_misses`.
  - `runtime/engine/template_resolution.py`: `parses_leaves`, `_CONSUMER_TYPES_LEAVES`, `_bind_locally`.
  - `runtime/workflow_executor.py`: `type_child_inputs`.
  - `core/workflow/declared_inputs.py`: `declared_root`, `declared_input_diagnostics`.
- **Invariants that must NOT break:**
  1. **Every value entry goes through `prepare_inputs` with its true `InputSource`.** The entries are: root compile, each call's child `prep` (`type_child_inputs`), each dry-run item, validate-only and analyze (`check_supplied_inputs`). An entry left unlabelled defaults to `argument`, and two things break:
     - an `any` value from MCP or the parent gets re-inferred (`"true"` → `True`);
     - the error says "from the command line".

     That defect class was found twice: prediction re-compiles, then the dry-run nudge. `AnalysisContext.input_sources` carries the labels through re-entry.
  2. **Presence, `None` and fallbacks live in ONE function** (`prepare_inputs`). A supplied `None` and `default: null` both mean "not provided". The order is: supplied → env → settings → default → required? error.
     - At the CHILD placement, a required input without a default takes no env/settings fallback (ruling H1).
     - `_fallback_value` deep-copies every default (#790).
     - The validator's `_check_required_inputs` mirrors both rules. A second presence rule anywhere re-splits static vs run time.
  3. **The never-re-parse rule is data in the store, not a kwarg.** `__pflow_input_types__` is installed per run by `WorkflowEngine.run` (before the prompt-cache map is built; restored in `finally`), by the runner's root store (post-run `-o` readers), and by `create_planner_shared`.
     - Any context without the key silently restores the old parsing.
     - A new synthetic context that resolves input roots must install it. The analyzer's `context.py` / `token_estimation.py` do; they need no binding mirror, because they never resolve step `inputs:` keys or aliases.
  4. **The map is rewritten exactly at the runtime's two `inputs:` merge points** (`_bind_locally`), never earlier, and per item by `bind_batch_item`.
     - A step's own `inputs:` VALUES resolve while the workflow input still owns the root. Rewriting earlier reopens #686 for `inputs: {data: ${data}}`.
     - A binding inherits only via `bound_declaration`: a single whole non-`|json` Expression, read from the AUTHORED template. Under a loop that is the carry template from round 2 (`carry_effective_config` rewrites `template_params`), so nothing extra is needed for carry.
     - This is binding provenance. It is NOT value tagging, which ADR-0017 rejects. A node output never inherits.
  5. **A declared-text miss is never "absent".**
     - `??` never falls past it: `_evaluate` checks `declared_text_stop`, recursive over dynamic indexes.
     - Loop conditions, inline batch items and `## Cache` chunks raise `DeclaredInputTextError` via `declared_text_misses`. Each of those consumers otherwise reads "unresolved" as "stop / keep literal / drop chunk".
  6. **`parses_leaves` is a predicate on `(node_type, key)`** (`_CONSUMER_TYPES_LEAVES`: `shell.env`, `http.headers`, `workflow.inputs`) **plus code keys annotated `str`** (`TemplateConfig.text_input_keys`, read at compile time). It is never a check of `key == "env"` (Task 118's invariant 3). `http.params` stays parsed, because a list leaf is legitimate repeated-param syntax.
  7. **The validator mirrors the runtime binding by binding** (`declared_root` over `_declared_scope`). This covers the alias bound first, a step's `inputs:` keys for its other params, a carried key only when round 1 and the carry template agree, and an inline alias only when every element's entry agrees (`_agree`).
     - Certain-miss rules live in `validate_data_flow` (`core/workflow/declared_inputs.py`), so the compiler enforces them for run-time-chosen children too (Task 181's invariant 5).
     - The parity corpus pins validator ⟷ runtime.
  8. **Every new message shows values through `security_utils.redact_for_display`** (nested sensitive keys, including inside JSON text). Quoted values and fix lines are capped at 80 characters. A fix line never echoes a masked value: it falls back to the type's canonical example.

## What Was Built (actual vs. planned)
Phases ran P0 → PA → PC → PB → PD → PE → PF, then the gate, then **PG** (plan §10, added after the gate by user ruling). Deviations that matter, each ruled in the log:
- **Carrier.** Declared types ride the store under one reserved key, installed like `__pflow_prompt_cache__`. The spec's `TemplateConfig` field was rejected (plan D8). Task 181's `embedded` stays a consumer-side bool, so there is no second flag.
- **The child boundary IS `prepare_inputs`, per call in `prep`, and is routable** (`type_child_inputs`; `_PREP_RECOVERABLE` gained `WorkflowValidationError`). The old seeding over item 0's `resolved_defaults` is deleted, which closes #188.
  - The `child_failure` bundle carries a `diagnostics` LIST. A child with two bad inputs keeps both.
  - The reader (`executor_service.build_subworkflow_diagnostics`) still accepts the legacy `template_diagnostic`, because the bundle persists inside traces that resume restores.
- **The runner pre-fills placeholders, never real defaults** (`_fill_placeholders`). This fixed f₂ (env loses to its own default) and is what lets errors name their source.
- **Settings values are labelled `settings`, not `env`.** `pflow run`/`resume`/the MCP server copy settings.env into `os.environ` at startup, so the boundary asks the injector (`llm_config.is_settings_injected`) rather than comparing values.
- **Beyond the plan, each closing a silent pass the change would otherwise open:**
  - Shape and declared-text runtime errors when a parse is folded into one `resolve` call (a wrong-shape container used to pass `validate_resolved_type`).
  - `DeclaredInputTextError`, and `??` not falling past a declared-text miss.
  - `-o` and AUTO JSON output never re-parse an input's own value (`TemplateResolver.reads_declared_input`).
  - The validator's whole-map `inputs: ${m}` (d)-twin.
  - Input-vs-batch-alias rejection (a narrow member of #730).
- **PG (user rulings, after the gate):**
  - **W1 → A:** binding provenance, as above.
  - **H1 → B:** a required child input comes from the parent.
  - **#790:** defaults are deep-copied.
  - Also fixed: a pre-existing `--dry-run` crash on a per-item child batch (also on `origin/main`). Pinned by `test_plan_keeps_every_item_of_a_child_per_item_batch_when_one_cannot_resolve` and `test_plan_reports_every_item_when_no_child_per_item_survives`.
- **Not built (ruled):**
  - The §1.5 clause "(here `${item}` resolved to 'x')" (D1=B). The host sees only resolved params; see #792, which also covers the loop-carry `At:` path.
  - Run-form-specific wording (D4, #777).
  - `create_planner_shared`'s `resolved_defaults` overwrite stays, because `predict.py` relies on it. The item-0 leak was fixed at its source instead: no planner child compile coerces per-item values.
- **Deleted:** `coerce_workflow_input` and its six `_coerce_to_*` helpers; `cli/rerun_display.py` (no production reader); `template_surfaces.binds_as_text`; `_validate_child_params`; CLI type inference for workflow inputs. `infer_type` survives for `pflow probe` only.

## Patterns & Anti-Patterns
- **Source-side declarations travel with the data; consumer-side policy stays on the call.** `auto_parse` and `embedded` say what a consumer wants. The store key says what the value IS. Every future `resolve()` site inherits the rule for free, which a kwarg could never guarantee.
- **One boundary function, many callers, each labelled.** Root, child, dry-run, validate-only and analyze all call `prepare_inputs`, so a new entry point is "call it with the right `InputSource`". `InputTypeError.located(step=, sub_workflow_path=, resumed_run=)` places a diagnostic at the catching boundary, never by post-editing rendered text.
- **Close the class at the one site every consumer shares.** `??` and declared-text checks live in `_evaluate` and `declared_text_misses`; redaction lives in `redact_for_display`. The user's standing rule: every "fixed" names the class it closes.
- **Mutation-check every guard, with a working harness.** Restore by content, set `PYTHONDONTWRITEBYTECODE=1`, purge `__pycache__` before and after, and count failures. A same-second, same-size restore leaves the mutant's bytecode live, so kills become fake. This was caught at PA and re-run.
- **Anti-patterns rejected:**
  - Python `int()`/`float()` as the grammar (accepts `" 7\n"`, `1_000`, `nan`, `٣`).
  - `try_parse_json` as the number grammar (admits NaN/Infinity).
  - Tagging values with a `str` subclass (ADR-0017).
  - A `typed_input_roots` kwarg threaded through every resolve signature.
  - Rewriting the map up front instead of at the merge points.
  - Post-fixing `<run-id>` into a rendered suggestion.
  - A validator that reads env (validation would depend on the shell; top-level `--validate-only` is deliberately env-blind, D6).

## Gotchas & Non-Obvious Coupling
- **Phase order is load-bearing.** Strict child compile without "the parent stops parsing `inputs:`" is red: JSON text from an LLM reaches a child `string` as a dict. PA alone failed 2 tests and PC fixed them. Any refactor that splits these must keep them together.
- `compile_workflow(ir, reg, {})` does not mutate an EMPTY caller dict (`initial_params or {}` makes a new one). `last_execution_params` sees typed values only for non-empty params.
- `prepare_inputs` used to check `required` before `default`. A default now satisfies `required`; the child boundary and the validator agree (including `default: null` = no default).
- `check_supplied_inputs` reports only problems whose path is a supplied name, so a declaration problem both layers see is reported once. The undeclared-extras check runs AFTER the per-input loop, which fixes the output order (`topics` then `BOGUS`).
- `analyze()` now refuses undeclared parameters. 15 analyzer fixtures had to declare their inputs; real workflows must too.
- A child with no `## Outputs` no longer leaks its default-filled inputs to the parent (`${call.limit}` used to read a child default).
- `WorkflowValidationError` in `_PREP_RECOVERABLE` also makes a saved child that fails to load routable (`WorkflowManager.load` raises it).
- Two node-type spellings exist: `workflow` and legacy `pflow.runtime.workflow_executor`. Use `template_surfaces.WORKFLOW_NODE_TYPES`; three older single-spelling checks are #786.
- `docs` harness `tests/test_docs/test_guide_example_validation.py` injects every bare `${name}` as an input. It now skips batch aliases, because the alias rule flagged correct guide examples.
- **Real-HOME traffic:** the review fan-out (`workflows/review/run-review-lenses.pflow.md`) runs under the real HOME by design. Any pflow run rescans `~/.pflow/registry.json` with the running checkout's paths. That path churn is benign, with MCP entries intact. An MCP entry changing or vanishing is the hard-stop class (Task 181's module-fixture gotcha). A suspected test writer (`tests/test_cli/test_ui.py` `TestLazyImportBoundary`) is routed to its own issue.
- A Task-159 guide case (`12/04-guide-auto-detect`) moves on ANY `pflow guide` text change. Re-record only that case, and name every cause.

## Integration Points
- **Shares this task's primitives:**
  - **#743** (declared OUTPUT types): `coerce_declared_input` and the `InputTypeError` shape. H3's evidence (an output sourced from a `string` input is re-parsed in JSON output) is on the issue.
  - **Task 112:** `TypeSpec.parse_text`/`accepts` on canonical names (translate registry names through `PYTHON_ALIASES_AT_S1` first) and the context keys.
  - **Task 121:** feeds typed mock values through the same boundary; the non-text (h) rules apply.
- **Contracts changed:**
  - **CLI:** `parse_workflow_params` returns raw text.
  - **Signatures:** `prepare_inputs` returns `list[Diagnostic]` and takes `input_sources`/`step`/`sub_workflow_path`/`resumed_run`. `WorkflowRunner.run/validate/plan/preflight` and `compile_workflow` take `input_sources` (+ `resumed_run`).
  - **Store:** reserved key `__pflow_input_types__`.
  - **Bundle:** `child_failure.diagnostics` (list).
  - **Diagnostic context keys:** `input`, `declared_type`, `received`, `source`, `accepted`; plus `sub_workflow_step`/`sub_workflow_path` at the child boundary, and `unresolved_references[].text_not_parsed`/`unparsed_text`.
  - **Analyze:** `analyze()` rejects undeclared params and raises `WorkflowValidationError`. MCP analyze propagates it.
  - **Memo keys:** one-time misses where a value's type changed. The batch memo key ignores non-item reads (#675; Task 120's declaration-change trigger is posted there).
- **ADR-0017 amendment (main orchestrator writes it):** "…and a reference whose root is a declared non-`any` input is never JSON-parsed downstream, nor is a name bound to one by a single whole reference — a step `inputs:` key or a batch alias, read from the authored template (a carried key from its carry template), never from the value."
- **Follow-ups filed:**

  | Issue | What |
  |---|---|
  | #777 | Run-form source wording |
  | #778 | Screenshot skill: form fill, `scroll_to` |
  | #785 | JSON `-o` miss is an empty success |
  | #786 | Workflow-type spellings |
  | #789 | Parallel `fail_fast` empty `Executor error:` |
  | #791 | `analyze-cache` JSON merges input errors |
  | #792 | Host can't name the authored template or carry key |

  Also: the evidence comment on #675, and the routed real-HOME test writer.
- **Known limits (verified, not built):** in `loop.while`, inline `batch.items` and `## Cache` chunks, a typo miss on a PRESENT root (`${d.nope}`) still reads as absent. That is pre-existing; only declared-text misses are loud.

## Tests That Matter
- `tests/test_core/test_param_coercion.py`: the grammar table, the non-text (h) table, lossless `any`, idempotence over every type × accepted value, masking, 80-char caps, `accepted` per value form.
- `tests/test_runtime/test_prepare_inputs_coercion.py` + `test_runtime/test_workflow_executor/test_child_input_boundary.py`: resolution order, source labels, per-item child typing seq/parallel, routing, the bundle (current and legacy key), H1, #790.
- `tests/test_core/test_templates_declared_inputs.py` + `tests/test_runtime/test_declared_input_resolution.py`: leaf and walk rules, the winning `??` operand, merge-point shadowing, `TestABindingKeepsItsInputsProtection`, alias provenance, carry rounds, loop/batch/chunk raises, prompt-cache setup order, post-run `-o`. These are mutation-verified (PC 23, mid-review #1, G1 17, PG 33).
- `tests/test_integration/test_declared_input_entry_points.py`: every real entry path (CLI, stdin subprocess, resume and `--only`, MCP execute/analyze, analyze-cache text+JSON, settings label as `e2e`).
- `tests/test_runtime/test_template_validation/test_declared_input_rules.py` + `tests/test_core/test_workflow_validator_declared_inputs.py`: rules (a)–(f), `??` operands, cache vars, output-only workflows, run-time-chosen children, binding mirrors.
- `tests/test_integration/test_template_parity.py` (`DECLARED_INPUT_ROWS` + PG binding rows) and `tests/test_execution/test_plan_drift.py` (typed per-item, rejected-item reporting). Run these first when touching resolution or the planner.

## Breaking changes (no external users; all ruled)
- **Wrong-typed values now fail at the boundary** (exit 1) instead of warning. Validate-only and analyze check supplied values and reject undeclared extras.
- **`any`/untyped CLI tokens stay text unless they read back identically:**
  - `02134`, `1.10`, `TRUE`, `1e3` and a spaced `[1, 2]` stay text;
  - `42`, `true`, `[1]` are typed.
- **`integer` and `number`:** `integer` rejects `3.0`/`1e3`/`true`; `number` given `3` renders `3`.
- **Declared inputs are never re-parsed:**
  - `${d.payload.a}` into JSON text inside a declared `object` is unresolved, with a reason, and `??` does not fall past it;
  - a rebound alias or `inputs:` key keeps the protection;
  - `http.headers` values stay text.
- **Child workflows:** a required child input no longer reads env/settings, and a child's default-filled inputs no longer leak to the parent.
- **Warm memo caches** miss once where a value's type changed.

---
*Distilled from the implementation context of Task 120. The chronological journey lives in `implementation/progress-log.md` — this review is the durable forward-reference, not a re-narration of it.*
