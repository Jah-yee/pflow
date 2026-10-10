# Task 120 — implementation plan

**Goal.** A workflow input's declared type is decided once, where the value enters, by the declaration of
what receives it — and nothing downstream re-infers it. Wrong-typed values fail with an actionable error.

- **Spec:** `../task-120.md` (every decision DECIDED; (i)–(iii) ruled 2026-10-10).
- **Contract:** `context/adr/0017-120-declared-type-decides-parsing.md` (the rule); ADR-0016 (`env:` text,
  `to_string`); ADR-0006 (validator keeps its own structure walk).
- **Planner:** task-planner (Fable), 2026-10-10, on `285e7b3f` (`origin/main` moved to `ebaa5d1b`, #757 —
  declared output `null` handling — before this plan was committed; disjoint from these surfaces; the task
  orchestrator merges `main` at P0). Plan-mode battery (7 codex lenses) folded — §9.
- **Line numbers** were read on `285e7b3f`. Task 181 builds first on the same resolver arm — §0 lists what to
  re-verify after it merges. Every other citation: re-verify before editing, then edit.

**Read with this plan:** `diagnostics-checkpoint.md` in the same folder — every new or changed message, BEFORE
executed on `285e7b3f`, AFTER drafted. **It is an embedded user checkpoint (CP-1, §7): the build does not
start until it is ruled.** A ruling that changes text changes strings and assertions only.

**Shape.**
- **One PR.** Closes #686, #687, #188 (per-item child coercion). Refs #297 (the validate-only type/extras half
  lands here; the shape-check refactor does not), #742 and #743 (out by ruling — "Refs, not a closing PR").
- **Engine contact** in PC (`runtime/engine/template_resolution.py`, `engine.py`, `batch_executor.py`) and PD
  (`runtime/workflow_executor.py`): lane A, mid-task review after PC and after PE, plan-mode battery mandatory
  (run: §8).
- **No grammar change** in `core/templates.py` (no TS mirror edit); the resolver gains a *rule*, not a token.
- **No trace-format change**: only the value types inside `meta.inputs` change; memo keys miss once. The Task-159
  baseline (`.taskmaster/tasks/task_159/baseline/verify.sh`) is the outer regression net (P0 and PZ).
- **Not platform-sensitive** (no subprocess/path/encoding code). `tests-windows` runs as usual.
- **Web**: comment/doc edits plus one error surface (the run panel shows a typed-input 400). Not design-bearing
  → Opus; verified with `screenshot-pflow-web-ui`.

---

## 0. Build gate and the re-verify list (P0)

**Task 181 merges before this task.** Its plan (`feat/task-181-mcp-code-params-json`, `implementation-plan.md`
D1/D3/D4/D9) changes the same arm this plan edits. P0 re-verifies, by name, and logs each:

1. `core/templates.resolve(value, context, *, auto_parse=False, embedded=False)` and
   `_resolve_string(template, context, auto_parse, embedded)` — the exact kwargs. **This plan adds no kwarg to
   either** (D8); it adds a rule inside `_resolve_string` and `_walk` that reads declared types from the context.
   If 181 landed a different shape (e.g. a policy object), put the typed-root check inside whatever leaf arm
   decides "parse this string" — the rule is the same; log the adaptation.
2. 181's D4 arm (an `as_json` Expression outside embedded code is kept verbatim as an issue) sits BEFORE the
   auto-parse leaf in `_resolve_string`; the typed-root check goes on the auto-parse leaf only. `${v|json}` of a
   typed root renders `to_json(value)` — no parse involved, nothing to do.
3. `template_resolution.py::resolve_templates` after 181 D9: the `inputs:` branch (`:276` today), the dict/list
   branch (`:281-285`), the simple-template-into-container parse (`:290-295`), and the new `embedded` branch.
   181's embedded params are never `inputs`, so D9 here and 181's D9 are disjoint; confirm no shared local.
4. `has_templates(value, *, embedded=False)` — untouched by this plan.
5. `param_mode` returns `"embedded"` as a third value; `parses_leaves` (D9 here) compares nothing against
   `param_mode` — confirm `split_params` still decides `param_mode(...) != "body"` before `has_templates`.
6. `execution/plan.py:1587` — 181 PC may have touched the dry-run resolver path; re-read before D9's edit.
7. `tests/test_integration/test_template_parity.py` `SURFACES` gained `embedded_code`; the rows this plan adds
   (D11) go beside 181's.

Also at P0 (independent of 181), log the result of each:
- `make test` pass/fail set by name; `verify.sh` drift set (expected 76 pass / 11 drift, #680);
  `.taskmaster/tasks/task_170/implementation/examples-baseline/capture.py --check`.
- `grep -rn "format_param_value" src/pflow` — expected production callers: `ui/run_node.py:94`,
  `cli/rerun_display.py:63` (the probe's `format_param_value` at `_probe_impl.py:195` is a *different* function
  from `node_output_formatter`). If a third caller exists, D7 covers it the same way (renderer stays).
- `grep -rn "binds_as_text\|parses_leaves" src/pflow` — expected: definition + `template_resolution.py:19,96,284`
  + two CLAUDE.md rows. D9 deletes `binds_as_text`.
- `grep -rn "\.accepts(" src/pflow` — expected zero (the three docs claiming it is in use are stale, §6).
- `resolve_templates` receives the raw `shared` dict (engine `:1748`, store proxy created at `:1755`), so
  `dict(shared)` at `:253` keeps `__pflow_prompt_cache__`. Confirm the same for the new key (D8) by reading, not
  assuming — `NamespacedSharedStore.__iter__` (`namespaced_store.py:130`) iterates parent keys too.
- Re-run the checkpoint probes (`diagnostics-checkpoint.md` §0) and confirm the BEFORE blocks still match.

---

## 1. The mechanism in one paragraph

`TypeSpec` (`core/types.py`) learns to read text (`parse_text`, the strict ASCII grammar of decision (b)) beside
the `accepts` it already has. One coercer, `core/param_coercion.coerce_declared_input(name, declared_type, value,
*, source)`, applies the grammar to text, `accepts` + the (h) scalar rules to non-text, the lossless rule to
`any` text from a CLI argument, and raises `InputTypeError` (structured: input, declared type, received, source,
accepted spelling) — never a warning. Every entry site calls it: `prepare_inputs` (CLI / MCP / web / resume /
defaults, with the value's SOURCE), the sub-workflow host's `prep` (per item, routable), the analyze paths, and
the validator (declared defaults, literal child inputs). The CLI parser returns raw text. The compiler records the
declared input types on `CompiledWorkflow`; `WorkflowEngine.run` installs them in the shared store under one
reserved key exactly like `__pflow_prompt_cache__`, so every `resolve()` against the store sees them: a reference
whose root is a declared non-`any` input is never JSON-parsed, root-wide (the simple-template leaf and the
mid-path walk both check it). The parent's `inputs:` to a workflow step is handed on unparsed; the child's boundary
types it per item. A code `inputs:` key annotated `str` is handed text. The validator rejects a declared `string`
used as a container, and a path that is certain to miss on a declared root, keyed on the root's active binding.

---

## 2. Investigation record

Markers: **(verified)** read at file:line or executed by the planner on `285e7b3f`; **(S)** a searcher citation
whose reasoning the planner checked but did not re-read.

### 2.1 Spec corrections applied (own spec, within authority — logged)

- Resume needs **no argv reorder**: `_split_target_and_params` (`cli/commands/resume.py:39-56`) parses before
  `preflight_resume`, but target resolution never reads the params; with a raw-text parser nothing depends on
  the order (verified).
- `last_execution_params` **already stores coerced values**: `compile_workflow` keeps the runner's `params` object
  (`compiler.py:900`) and `_prepare_compilation` mutates it in place (`compile_validation.py:193,198`), so
  `_update_metadata` (`runner.py:796-827`) records the coerced dict (verified by reading). PA pins it.
- `optional_input_keys` is built from **code annotations**, not the IR `inputs` (`compiler.py:294-299`); the IR
  input types are in scope one frame up (`_instantiate_nodes_for_workflow`, `compile_workflow`). It remains the
  precedent for "a compile-time set on `TemplateConfig`" (D9's `text_input_keys`), not for the declared-type carrier
  (D8 puts that on `CompiledWorkflow` + the store).
- The Task 120 note is the `binds_as_text` docstring (`template_surfaces.py:60-64`) and `parses_leaves`
  (`template_resolution.py:93-94`), not `:27`.
- Line drift: child seeding `workflow_executor.py:408-422` (comment `:413`); `str(e)` at `:181`; `inputs` must be a
  dict `:727-733`; untyped fallback `:820` (message label only); `ALLOWED_PARAMS` (`:89-94`; there is no
  `RESERVED_PARAMS`); `test_validate_only.py:205-235` (`TestValidateOnlySkipsPrepareInputs`); the web round-trip
  pin is `tests/test_cli/test_run_node.py:507-533`; the `- type: dict` suggestion is
  `type_validation.py:316-321`; `test_compile_once_regression.py:481`.
- Stale-surface line drift: `guide/nodes/shell.md:54`, `guide/features/batch.md:37`,
  `architecture/reference/template-variables.md:621-623`, `core/CLAUDE.md:105-107,199-201`, MCP instruction
  files `:1022-1045` + "Rejects floats" `:1276` / `:1001-1024` + `:1255`.
- `prepare_inputs` **checks `required` before `default`** (`ir_preparation.py:60-71`): an input with a default but
  no `required: false` is "missing" on every direct `compile_workflow` path (verified by executing
  `compile_workflow` on `{g: {type: string, default: 'x'}}` → `SchemaValidationError`). The runner hides it by
  pre-filling defaults (`runner.py:695-700`), which is also the f₂ bug (default beats env). D5/D6 fix both.
- `_validate_child_params` treats a default as satisfying `required` (`workflow_executor.py:815-818`) — the two
  "required" heuristics disagree today; D5 harmonises on "a default satisfies required".

### 2.2 Facts the design rests on (verified unless marked)

- **Every string→typed site in resolution** (S, planner re-read the leaf and walk): `_resolve_string`
  (`core/templates.py:586-618`, parses a SIMPLE template's string value to a container iff `auto_parse`);
  `_walk`/`_get_key`/`_json_container` (`:413-472`, parses a string mid-path when a `Field`/index follows — no
  flag, every caller); `resolve_templates` `:276` (`inputs:` values, hard-coded `auto_parse=True`), `:281-285`
  (dict/list leaves iff `parses_leaves`), `:290-295` (simple string into a registry container type, separate
  `try_parse_json`); `batch_executor.resolve_batch_items` `:119` (inline list, `resolve_nested`) and `:127-130`
  (unconditional `try_parse_json` of a string result, simple or not); `execution/plan.py:1587`
  (`auto_parse=True`, also on a whole-map string template — diverges from the engine); `core/workflow/validator.py:1801`
  (`resolve_nested` over child literal params with `{alias: item}`). `resolve()`'s only kwarg today is
  `auto_parse`; `_evaluate` does not report which `??` operand won.
- **Shadowing is real**: `resolve_templates` merges the step's static `inputs:` (`:258`) and resolved `inputs:`
  (`:402`) into the context, so a later param's `${data}` reads the local binding. `data_flow.step_scope` models
  the same precedence (`StepScope.owner`). The validator's `infer_template_type` checks workflow inputs FIRST
  (`type_checker.py:41-44`) — pre-existing mis-typing when a local key shadows (follow-up, §8).
- **Input boundary**: `coerce_workflow_input` (`param_coercion.py:229-297`) is lenient; non-strings pass every
  type unchecked except `string` (stringified, `json.dumps` for containers); `_coerce_provided_input` returns an
  explicit `None` before coercing (`ir_preparation.py:148-153`); undeclared extras rejected at `:177-228`;
  errors are `(msg, path, suggestion)` tuples collapsed at `compile_validation.py:39-65` (per-input suggestions
  dropped when ≥2). `prepare_inputs` never mutates `provided_params`; `_prepare_compilation` mutates
  `initial_params`. `TypeSpec.accepts` (`types.py:115-131`) has zero callers.
- **Runner**: `_fill_declared_defaults` (`runner.py:695-700`) injects REAL defaults as if supplied (env never
  consulted — executed: `port=abc`/`port=9090` with `default: 8080` → `port=8080` both times); `validate()`
  ignores `params` (`:446-453`, `:471-473`); the run path validates BEFORE compile and the validator reads only
  param KEYS (`path_validation.py:120`), never values (S, grep).
- **Sub-workflow boundary**: supplied child values are never coerced for ANY item — compile-time
  `prepare_inputs` coerces item 0's values into `resolved_defaults`, then `exec` seeds raw `child_params` over
  them (`workflow_executor.py:419-422`); compile is cached per path (`:257-275`). `prep` captures
  `_PREP_RECOVERABLE` (`:28-34`: `ValueError`, `RecursionError`, `FileNotFoundError`, `MarkdownParseError`,
  `WorkflowNotFoundError`) into `{"_prep_error": str(e)}` (`:181`); `exec` short-circuits with no `child_failure`
  (`:377-388`); `post` routes `error_action` and forwards `_pflow_child_failure` when present (`:495-497`). The
  bundle (`_extract_child_failure`, `:630-668`) carries `workflow_path`, `failed_node`, `failures`, `error`,
  optional `template_diagnostic`; `build_error_list` (`execution/executor_service.py:143-157`) reads it. Batch:
  a result-dict failure becomes an error record (`batch_executor.py:467-476`), text shows the first line
  (`batch_errors.py:156-160`); a RAISED exception needs `retriable=False` AND `batch_fatal=False` to fail one item
  under `continue` (`:380-402`); `CompilationError` is always fatal. Executed BEFORE (checkpoint §0.10b): a batch
  of three children with `n: ${item}` over `["7","x","9"]` under `continue` fails all three at the child's code
  node ("expects int but received str") — even `"7"`.
- **Dry-run planner**: `create_planner_shared` (`plan.py:592-593`) does `{**params}` then
  `update(resolved_defaults)` — item 0's coerced values overwrite every item (reverse of the engine).
- **CLI**: `parse_workflow_params` callers `run.py:1053`, `resume.py:56`, `analyze_cache.py:145`,
  `ui/server.py:1017`, `_probe_impl.py:52`; stdin is routed raw (`run.py:991-992`); `display_rerun_commands` /
  `format_rerun_command` have no production caller; `filter_user_params` feeds only the dead
  `ctx.obj["execution_params"]` write (`run.py:1159-1161`, no reader).
- **Web**: form submits strings only (`web/src/api/client.ts:136-141`; server 400s non-strings
  `ui/server.py:1040-1047`), preflight `parse_workflow_params(tokens)` → `WorkflowRunner.preflight`, spawn
  re-parses the same tokens (`:1057,1070`); prefill `read_run_inputs` → `format_param_value`
  (`ui/run_node.py:60-95`); comments at `RunForm.tsx:8-12`, `controlForType.ts:8-9`, `RunPanel.tsx:24-25`
  describe `infer_type`.
- **MCP**: `workflow_execute`/`workflow_plan` pass typed JSON through `validate_execution_parameters` (names,
  size, regexes — no coercion; `null` → `None`); `workflow_validate` takes no params (`execution_tools.py:121-127`).
- **Analyze**: `analyze_cache.py:145` infers types; `analyze()` validates with placeholders; `predict.py:290-324`
  pads with `VALIDATION_PLACEHOLDER`; `:476-489` swallows `SchemaValidationError`/`WorkflowValidationError` into a
  debug log ("prediction skipped"). `context.py:51-53` claims post-coercion parameters — false today.
- **Validator**: Pass 5 returns valid for any input root with a path (`path_validation.py:120-121`); `??` operands
  are `ROOT_ONLY` (`operands.py:22-31`; the enum has only `FIELD_CHECK`/`ROOT_ONLY`); Pass 6 (`type_validation.py:86-109`)
  and Pass 9 (`:403-460`) type a whole-root input from its declaration and let `string` into containers via the
  `"string"` matrix row (`core/templates.py:71-99`); Pass 9's suggestion renders `- type: dict` (`:316-321`),
  invalid for `## Inputs` (schema enum = `CANONICAL_TYPES`, `ir_schema.py:361-365`), pinned wrong at
  `tests/test_runtime/test_template_validation/test_types.py:1502`; `batch.items` and output sources never read
  a declared type; declared defaults are never type-checked; loop `while/until` on a whole-root declared `string`
  is already an error (`runtime/template_validation/validator.py:260-271`). No validator rule rejects an input
  named like a batch alias (grep). Untyped-input default disagrees: `"string"` in `discovery_formatter.py:121`,
  `workflow_save_formatter.py:151,226`; `"any"` in `discovery_formatter.py:205`, `workflow_executor.py:820`.
- **HTTP**: `headers`/`params` are `dict` params (`nodes/http/http.py:20-22`), values passed to `requests`
  untouched (`:60-64,123,126`); executed: a dict or int header value raises `InvalidHeader`; a dict query param is
  mangled to its keys, a LIST query param is legitimate repeated-param syntax.
- **Code annotations**: `extract_code_annotation_type(code, key)` (`python_code.py:192-207`) returns the S1 name
  (`str`, `Optional[str]`, `str | None`, `None | str`, quoted forward refs, generics stripped → `"string"`; a
  non-None union or `Any` → `None`), module scope only — the same helper Pass 9 uses.
- **Store precedent**: `WorkflowEngine.run` saves/installs/restores `__pflow_prompt_cache__` per run
  (`engine.py:887-915`), and `create_planner_shared` installs it too (`plan.py:580-600`). Children get a fresh store
  and their own engine `run` (`workflow_executor.py` → `WorkflowEngine(nested=True).run`).

### 2.3 Cross-task scan (`./scripts/tasks`, 2026-10-10)

- **Task 118** (done): substrate — `param_mode`, `binds_as_text`/`parses_leaves` (replaced here, D9),
  `to_string` as the value-to-text rule (h), `data_flow.step_scope`/`StepScope.owner` (reused in D11),
  `EnvBindingError` (`retriable=False`, `batch_fatal=False`; the precedent for D3), the consumer table
  `test_code_body_consumers.py` (no new param walk here that reaches bodies — the validator pass in D11 walks
  operands the surface list already yields; add a row only if P0 finds otherwise).
- **Task 170** (done): one parser; no `${` regex outside `core/templates` (D8 adds none); the parity corpus is
  the cross-layer pin (D11 rows); `Resolution` channels unchanged.
- **Task 181** (planned, builds first): §0. Its `|json` insert "renders a value's type exactly" — this task's
  typing changes what an insert of a declared input emits (`${count|json}` → `3`, no longer `"3"`); 181's
  task-review note anticipates it.
- **Task 183** (building concurrently): `runtime/engine/gate.py`, `loop_control.py`, `core/gate.py`,
  `workflow_trace.py` (2.10.0), web gate panel — disjoint files. Semantic overlap: none found (this plan reads
  `loop_control.py` only to confirm it inherits the store key, no edit). If 183's `loop_control.py` edit lands
  first, PC's `make test` on the merged result is the check. Serialize engine phases behind 183's merge if both
  are in flight when PC starts (the main orchestrator's call; this plan has no trace change).
- **Task 112** (later): shares `TypeSpec.accepts`/`parse_text` (canonical names; 112 translates registry names
  through `PYTHON_ALIASES_AT_S1` first) and the Diagnostic context keys of D3 — the reconciliation sentence for
  112's top block goes up with the handback (another task's spec; not edited here).
- **Task 121** (later, `pflow test`): will feed YAML-typed mock values into inputs — (h) non-text rules apply.
- **#743** (declared output types): builds after; shares `coerce_declared_input` + `InputTypeError` shape.
  **#742** (YAML literal re-typing): out; nothing here recovers the author's spelling.
- Open issues touching these surfaces: **#746/#747/#748/#749** (approval preview, `__` env names, MCP warnings,
  MCP instruction parity) — not touched; PF edits the two MCP instruction files by hand as the spec requires and
  notes #749. **#735** (code static checks only in prep) — D9's compile-time annotation read uses the existing
  module-scope helper; no new prep-only check. **#730** (shared root namespace) — D11(f) adds the narrowest member
  this task needs (input vs batch alias); the full rule stays #730's.

---

## 3. Decisions

Governing lens at every fork: *"prioritize simplicity of the FINAL code… the right solution the top 10% of
codebases similar to this one would implement… optimized for AI agents to understand and add features to."*

### D1 — The grammar lives beside `TypeSpec` (`core/types.py`)

```python
_INTEGER_TEXT = re.compile(r"-?[0-9]+")                                   # decision (b)
_NUMBER_TEXT = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?")  # a JSON number
_BOOLEAN_TEXT = {"true": True, "false": False, "yes": True, "no": False, "1": True, "0": False}

class TypeSpec:
    def parse_text(self, text: str) -> tuple[bool, Any]:
        """Read ``text`` as this type under the strict ASCII grammar: integer ``-?[0-9]+`` (``007`` → 7);
        number = a JSON number — an int when it has no fraction/exponent, else a float (``007`` is NOT a JSON
        number and is rejected for ``number``; never nan/inf/``1_000``); boolean =
        true/false/yes/no/1/0, case-insensitive; object/array = JSON text of that shape; string = itself;
        any = itself. ``(False, None)`` when the text does not fit. Callers strip surrounding whitespace for
        every type but string (stdin arrives as ``"42\\n"``)."""

    @property
    def accepted_text(self) -> str:
        """One phrase for messages: integer → "a whole number (e.g. 3)"; number → "a number (e.g. 3, 2.5, 1e3)";
        boolean → "true or false (also yes/no, 1/0)"; object → 'a JSON object (e.g. {"a": 1})';
        array → 'a JSON array (e.g. ["a", "b"])'; string → "text"; any → "any value"."""
```
`accepts(value)` (`:115-131`) is unchanged and gains its first callers (D2, D11). `object`/`array` text uses
`json.loads` then a shape check (not `try_parse_json`, which admits bare primitives).

**Rejected:** Python's `int()`/`float()` (`int(" 7\n")`, `int("1_000")`, `float("nan")`, `int("٣")` all pass —
the irreversible loose direction); `try_parse_json` as the number grammar (admits `NaN`/`Infinity` via
`json.loads`).

### D2 — One strict coercer, `core/param_coercion.coerce_declared_input`

```python
InputSource = Literal["argument", "stdin", "call", "recorded", "env", "settings", "default", "parent"]

def coerce_declared_input(name: str, declared_type: str | None, value: Any, *, source: InputSource) -> Any:
    """Type ``value`` by the input's declared type, once, where it enters — or raise ``InputTypeError``.
    Text → the (b) grammar (whitespace stripped for every type but string); ``any`` text from a CLI
    ``argument`` → lossless inference (D2.1), from every other source → itself; a non-text value →
    ``TypeSpec.accepts`` (integer rejects bool, number rejects bool) or, for ``string``, any scalar rendered by
    ``templates.to_string`` (the text ``${x}`` would produce — a boolean renders ``True``). A container into a
    ``string``, and every other mismatch, raises. ``VALIDATION_PLACEHOLDER`` passes through unchanged."""
```
- `declared_type is None` → treated as `"any"` (untyped behaves as `any`, decision (d)).
- **`None` means "no value", never a type error:** the coercer returns `None` unchanged for every type.
  Presence (required/optional, fallbacks) is the CALLER's rule and lives in one place — `prepare_inputs`
  (D5), which both the root and the child boundary (D10) call: a `None`-valued key is dropped before the
  presence check, so MCP `null`, a parent `${up.result}` that is `None`, and `default: null` all mean "not
  provided". D11(a) skips a `default: null`.
- **D2.1 lossless inference** (`any` + `argument` only): `ok, parsed = try_parse_json(text)`; typed iff `ok and
  parsed is not None and json.dumps(parsed, separators=(",", ":")) == text`; else the text. So `true`, `42`,
  `-1`, `2.5`, `[1]`, `{"a":1}` type; `02134`, `1.10`, `0755`, `1e3`, `TRUE`, `yes`, ` 42`, `[1, 2]`, `null`
  stay text (`null` policy: the text `"null"` — `None` means "not provided"). Compact JSON is also what
  `format_param_value` renders for non-strings (D7), so the web prefill round-trip is `format_param_value` →
  coercer for non-`any` types (ruling (iii)).
- Source classes: **infer** — `argument` (CLI token; the web form spawns the CLI, so it is an argument).
  **pass through** — `stdin` (raw text today, stays), `env`, `settings`, `default` (YAML-typed), `recorded`
  (typed), `call` (MCP typed JSON), `parent` (typed by the parent's resolution).
- Deleted: `coerce_workflow_input`, `_COERCION_DISPATCH` and the six `_coerce_to_*` helpers, the stale module
  docstring. `coerce_param_for_node` (node-side dict/list → JSON for `str` params) is unchanged.
- `core/param_coercion` imports `to_string` from `core/templates` (both `core`; `core/templates` already imports
  `core/types`; no cycle — `tests/test_core/test_templates_module.py` subprocess pin stays green).

### D3 — `InputTypeError(PflowError)` in `core/exceptions.py`

```python
class InputTypeError(PflowError):
    """A workflow input's value does not fit its declared type. Raised by the coercer; every boundary
    catches it and carries its Diagnostic (`prepare_inputs` → a `WorkflowValidationError` of N diagnostics;
    the validator rules → the diagnostic itself), so it never crosses a node boundary and needs no
    retriable/batch_fatal attributes."""
    def __init__(self, *, input: str, declared_type: str, received: Any, source: InputSource,
                 path: str | None = None, step: str | None = None, sub_workflow_path: str | None = None): ...
    def to_diagnostics(self) -> list[Diagnostic]: ...   # exactly one; text per source in diagnostics-checkpoint.md
```
- `path` defaults to `inputs.<input>`; `source == "default"` → `inputs.<input>.default`; the parent boundary passes
  `nodes[id=<step>].params.inputs.<input>` + `sub_workflow_path` (merged into context like
  `CompilationError.to_diagnostics` does).
- `received` is rendered through one helper: `security_utils.is_sensitive_parameter(input)` → `<REDACTED>`;
  otherwise `repr`-style text truncated to 80 chars with `…`; a non-text value shows its JSON (`3.0`, `true`,
  `{"a": 1}`). **The suggestion never echoes the value for a sensitive name** — it uses the type's canonical
  example (`count=3`), so a fix line cannot reintroduce a masked secret.
- Context keys (shared with Task 112 — document in `runtime/template_validation/CLAUDE.md` → context-key
  conventions): `category: "validation"`, `path`, `input`, `declared_type`, `received`, `source`, `accepted`
  (= `TypeSpec.accepted_text`), plus `sub_workflow_path`/`sub_workflow_step` at the child boundary (the names
  `_check_required_inputs` already emits). `title = "Invalid input value"`, `source = "validation"`.
- One suggestion, built from the source (checkpoint §1). No `see_also` (there is no guide page for inputs
  specifically; `pflow guide` core covers it — PF adds the type table there).

### D4 — Sources travel as an explicit kwarg, default `"argument"`

`input_sources: Mapping[str, InputSource] | None` is threaded `WorkflowRunner.run/validate/plan/preflight`
(keyword-only, the `resume_source`/`gate_resolver` precedent — `RunnerConfig` stays execution config) →
`compile_workflow(..., input_sources=None)` → `_prepare_compilation` → `prepare_inputs`. A key absent from the
map is an `argument`. Who labels:
- `cli/commands/run.py`: the stdin-routed key → `"stdin"` (set where `_route_stdin_to_params` assigns it).
- `cli/commands/resume.py:343-344`: every key taken from `pf.source.inputs` → `"recorded"`; CLI overrides stay
  `argument`.
- `mcp_server/services/execution_service.py` (`execute_workflow`, `plan_workflow`, `analyze`): every key →
  `"call"`.
- `runtime/workflow_executor.py`: the child's compile gets `{k: "parent" for k in child_params}` (its values
  are already typed by then — the label only matters if a later change moves a check).
- `ui/server.py`: nothing — preflight and spawn are CLI arguments.
- `core/prompt_cache_analysis/analyze.analyze(..., input_sources=None)` (D6).

**Rejected:** a `__pflow_input_sources__` entry inside `initial_params` (the `__env_param_names__` convention) —
metadata hidden in the value dict; the kwarg is typed and visible at every seam.

### D5 — `prepare_inputs` contract (`runtime/compilation/ir_preparation.py`)

```python
def prepare_inputs(workflow_ir, provided_params, settings_env=None, *, input_sources=None
                   ) -> tuple[list[Diagnostic], dict[str, Any], set[str]]:
```
- **Resolution order per declared input:** supplied (a supplied `None` counts as *not provided*) → `os.environ`
  → `settings_env` → `default` → `required` (default `True`) ? error : `None`. (Today `required` is checked
  before `default`; fixing it harmonises with the child boundary, which now IS this function — D10.)
- **The one input boundary.** `prepare_inputs` is called by the root (compile), by the sub-workflow host's
  `prep` per item (D10), by the dry-run planner per item (D10), by validate-only and analyze with placeholders
  for the missing keys (D6). There is no second presence/null/fallback rule anywhere.
- **Every resolved value** (supplied, env, settings, default) goes through `coerce_declared_input` with its
  source; `InputTypeError` becomes a Diagnostic in the returned list (the exception's own, path included).
- Kept: undeclared-extras check (`:177-228`), the empty-required-string check, the `stdin: true` count check,
  the name check — each now builds a `Diagnostic` directly (its suggestion kept) instead of a tuple.
- Returned `defaults` (name kept; the compilation CLAUDE.md already explains it) holds every missing input's
  resolved value and every supplied value the coercer changed (`is not` test as today). `env_param_names`
  unchanged (settings-sourced names).
- `compile_validation._raise_input_validation_errors(diagnostics)` raises
  `WorkflowValidationError(validation_errors=diagnostics)` — one exception type, N diagnostics, each with its own
  path and suggestion; the "Found N input validation errors" collapse is deleted. Callers that catch
  `SchemaValidationError` for this path flip (`grep SchemaValidationError tests/test_runtime/test_prepare_inputs*
  tests/test_cli tests/test_execution`); `predict.py:23-33` already lists both types.
- Idempotent on typed values: `accepts` passes → no change → not in `defaults`. (Resume replay, the child
  compile after D10, and the web preflight all rely on this; PA pins it with a property-style test over every
  type × its accepted values.)

### D6 — Runner: placeholders only; validate-only checks the user's values

- `_fill_declared_defaults` → `_fill_placeholders`: every declared input missing from `params` gets
  `__pflow_declared_<name>__` (never a real default). Effect: the validator still sees every key (Pass 5 needs
  only keys); `compile_workflow` → `prepare_inputs` resolves env → settings → default with the real order (f₂
  fixed); the error names the source because the pre-fill no longer erases it. `_strip_placeholders` unchanged.
- `validate()` (validate-only): after `WorkflowValidator` (placeholders, as today) run
  `prepare_inputs(ir, {**params, **placeholders-for-missing}, input_sources=...)` and append its diagnostics
  (type errors, undeclared extras, empty required strings) — missing required inputs are NOT an error here
  (`test_validate_only_works_without_input_values` stays). `--validate-only` and the run now agree on supplied
  values (spec: #297 parity; the shape-check refactor stays #297's). MCP `workflow_validate` has no params —
  parity is CLI-only; PF says so in `docs/reference/cli/index.mdx`.
- Run path order unchanged: validator → strip → `compile_workflow` (type errors raise `WorkflowValidationError`
  from compile; the CLI already renders it; no resume hint — `has_resumable_step()` is false before any step).
- `preflight()` inherits (UI 400 with the Diagnostic; `/api/run` already maps `PflowError` → 400 with diagnostics).
- Analyze: `analyze(ir, parameters=..., input_sources=...)` FIRST runs `prepare_inputs(ir, {**parameters,
  **placeholders-for-missing}, …)` — omitted inputs stay legal (DD#35, `analyze.py:111`;
  `test_cache_analysis_analyze.py:5261` analyses without its required `article`), supplied bad values and
  undeclared extras raise `WorkflowValidationError`; the coerced SUPPLIED values are merged into the analysis
  map, the placeholders are not (so `context.py:51-53` becomes true). **CLI routing:** the `analyze()` call at
  `analyze_cache.py:187` is wrapped like `parse_workflow_params` is (`_try_or_emit_diagnostic`, or an added
  `except PflowError` → `_emit_error` with the diagnostics) so `--format=json` emits the JSON envelope, not the
  group handler's text. **MCP routing:** `execution_service.py:543-547` lets `PflowError` propagate (today it
  re-raises everything as `RuntimeError("❌ Cache analysis failed…")`), so the structured diagnostic reaches the
  MCP error. `predict.py`'s swallow is untouched: with the check up front it can no longer hide an input error.
  Placeholder padding (`:290-324`) keeps working via the placeholder passthrough.
- **Analyzer synthetic contexts carry the declarations:** `context.py:393,421` and
  `token_estimation.py:474-494` build fresh `{root: value}` maps and resolve against them; each installs
  `DECLARED_INPUT_TYPES_KEY: declared_input_types(ir)` (the helper of D8) so analysis and the run agree on
  root-wide protection (`${data.payload.a}` into JSON text stays unresolved in both).

### D7 — The CLI parser returns raw text

- `cli/param_parsing.parse_workflow_params(args) -> dict[str, str]`: split on the first `=`, no inference.
  `infer_type` stays in the module for ONE caller: `_probe_impl._validate_parameters` calls it explicitly per
  value (node params have registry types, no workflow declarations — ADR-0017 Consequences). `format_param_value`
  stays (web prefill renderer); its docstring becomes "the inverse of the declared-type coercer for non-`any`
  inputs: compact JSON for non-strings, text as is".
- All five `parse_workflow_params` callers change nothing but what they receive; `ui/server.py:1017` keeps
  "preflight builds params exactly as the spawn will" for free (same parser, same coercer).
- Delete `rerun_display.display_rerun_commands`, `format_rerun_command`, `filter_user_params`, the dead
  `ctx.obj["execution_params"]` write (`run.py:1159-1161`), and `tests/test_cli/test_rerun_display.py`'s
  round-trip tests (`:645-711`). If `rerun_display.py` is then empty, delete the module and its `cli/CLAUDE.md`
  row.
- Breaks 3 and 11 (#687: `02134`, `1.10`, `TRUE`, `1e3` on `run`, `resume`, `--only`) close here; stdin and
  argument deliver the same bytes.

### D8 — The resolver rule: declared input types ride the shared store

**Carrier.** `core/ir_schema.declared_input_types(ir) -> dict[str, str]` (every declared input → its canonical
type; untyped → `"any"`); `CompiledWorkflow.input_types` holds the compiler's copy. `core/templates.py` owns
the key:

```python
DECLARED_INPUT_TYPES_KEY = "__pflow_input_types__"   # the store carries its own declarations (D8)
```
Installed where `__pflow_prompt_cache__` is — `WorkflowEngine.run` (`engine.py:887-915`, saved/installed/
restored in the same block; a nested child engine installs its OWN compiled workflow's map into its own fresh
store) and `create_planner_shared` (`plan.py:592+`) — **plus the runner's store itself** right after
`compile_workflow` (beside `shared_store.update(workflow.resolved_defaults)`, `runner.py:352`): the engine's
`finally` restores the OUTER value, and the CLI's `-o <path>` readers (`workflow_output.py:191`,
`variable_exists`/`resolve_value`) and `read-fields` run AFTER the engine returned, so the root store must carry
it on its own. Analyzer synthetic contexts: D6. `_PROPAGATED_KEYS` does not gain it.

**Rule, in `core/templates`:**
- `_resolve_string` simple-template leaf: `if auto_parse and isinstance(value, str) and not
  _declared_typed(context, operand.root)` → `try_parse_json`. `_evaluate` returns the winning operand with the
  value (internal change; a `??` chain is judged by the operand that supplied the value).
- `_walk`: when `_declared_typed(context, root)`, `_json_container` is not applied to string values mid-path
  (root-wide, ruling (i)): `${data.payload.a}` where `payload` is JSON text inside a declared `object` input is
  a MISS, reported through `Resolution.unresolved` as any miss is.
- `_declared_typed(context, root)`: `types = context.get(DECLARED_INPUT_TYPES_KEY); return bool(types) and
  types.get(root, "any") != "any"`. No key → today's behaviour (every direct `resolve()` test and every caller
  that does not install the key is unchanged).
- `has_templates`, `parse`, `Template`, `Resolution`: unchanged. `TemplateResolver.variable_exists`/`resolve_value`
  (raw-path mode) inherit through `_walk`.

**Shadowing (RESOLVE AT START "binding identity").** The map changes exactly where the runtime's bindings
change — at the two merge points, never earlier: when the static `inputs:` enter the context (`:258`) the
static keys leave the map; when the RESOLVED `inputs:` enter (`:402`) the template keys leave it. So while the
`inputs:` VALUES themselves resolve (`:276`), `${data}` in `inputs: {data: ${data}}` still reads the workflow
input `data` and is still protected (#686 would otherwise reopen for a same-named binding annotated `Any`), and
a sibling param resolved after `:402` reads the local, parsed `data`. Loop carry lands in template `inputs:`
via `apply_carry_overrides`, so a carried key becomes local at `:402` (upstream semantics kept). The batch
alias is excluded by D11(f) (the validator rejects an input named like an alias), so per-item contexts need no
edit. The validator mirrors this surface-awareness (D11(b)).

**The miss message (W5).** When a reference rooted in a declared non-`any` input is unresolved because the walk
reached a STRING descendant that was not parsed, `template_errors.classify_unresolved_references`
(`template_errors.py:200-215`, the `path_error` branch) records `"text_not_parsed": "<path to the string>"`,
and the renderer says what happened and what to do (checkpoint §1.14): `data.payload` is text and a declared
input is never re-parsed — nest the object (`{"payload": {"a": 1}}`) or parse it in a code step. Without this
the renderer prints "'data' has no 'payload.a' / Available fields: payload" and no fix.

**181 compatibility.** No new kwarg on `resolve`/`_resolve_string`; `auto_parse` and `embedded` remain the
consumer-side policy, the source-side declaration arrives with the data. The typed-root check sits on the
auto-parse leaf only (§0 item 2).

**Rejected.**
- *A `typed_input_roots` field on `TemplateConfig` threaded into every `resolve()`* (the spec's Design sentence):
  the data is workflow-level, `TemplateConfig` is per node and `None` for template-less nodes, `batch.items`
  resolves from `BatchConfig`, and output sources / loop fields / cache chunks / raw paths resolve with only
  `shared` in hand — five signatures and a per-node copy, and every future resolve site is a silent hole until
  someone remembers the kwarg. The store already carries per-workflow IR facts the resolver needs
  (`__pflow_prompt_cache__`), with the same two installers.
- *Tagging the value* (`str` subclass): ADR-0017.
- *Stringifying what the parent parsed*: ADR-0017 (#687 at a different seam).
- *Keying on names only* (ADR-0017's rejected option): the map carries types, so `any`/untyped keep today's parse.

### D9 — Engine sites adopt the policy (`runtime/engine/`)

- **`parses_leaves(template_config, key, subkey=None) -> bool`** replaces `binds_as_text` + today's
  `parses_leaves` and owns the consumer table:
  ```python
  # (node type, param) whose leaves the resolver hands on as text — the consumer types them:
  # shell.env binds environment text (ADR-0016); an HTTP header value is text by protocol; a workflow
  # step's inputs: are typed by the child's own ## Inputs (ADR-0017).
  _CONSUMER_TYPES_LEAVES = frozenset({("shell", "env"), ("http", "headers"), ("workflow", "inputs")})
  ```
  returns `False` for those pairs and for `subkey in template_config.text_input_keys`; `True` otherwise.
  `template_surfaces.binds_as_text` and `_BINDS_AS_TEXT` are deleted (sole caller was here); the
  `core/workflow/CLAUDE.md:13` row moves to `runtime/engine/CLAUDE.md`. 118's invariant 3 holds: the predicate is
  on `(node_type, key)`, never `key == "env"`.
- **`TemplateConfig.text_input_keys: frozenset[str]`** — for a `code` node, the `inputs:` keys whose
  `extract_code_annotation_type(code, key) == "string"` (so `str`, `Optional[str]`, `str | None`, quoted;
  a union with a container or `Any` is not text — RESOLVE AT START answered by reusing the helper Pass 9 uses).
  Built in `_create_node_and_config` beside `optional_input_keys`. Empty for every other node type (the agent
  node's `inputs: dict` has no per-key annotations → auto-parse kept, source-root protection via D8).
- **`resolve_templates`:**
  - `inputs:` branch: `resolve(v, context, auto_parse=parses_leaves(template_config, "inputs", k))` per key —
    `False` for every key of a `workflow` step (the parent stops parsing; the child types it, D10) and for a code
    `str` key; `True` otherwise (agent, code non-`str` keys).
  - dict/list branch: `auto_parse=isinstance(template, (dict, list)) and parses_leaves(template_config, key)`
    (unchanged shape; `http.headers` now `False`).
  - The separate simple-template-into-container parse (`:290-295`) is **folded into the one `resolve` call**:
    `auto_parse = (dict/list and parses_leaves) or (is_simple_string and expected_type in CONTAINER_TYPES)`.
    `_resolve_string` then decides with the typed-root rule. Delta accepted and tested: `${x}` holding
    `{"a":1}` into a LIST-typed param now reaches `validate_resolved_type` as a dict (was: str) — still an error,
    now the accurate one.
- **`batch_executor.resolve_batch_items`**: inline list → `resolve(items, shared, auto_parse=True).value`
  (as today via `resolve_nested`); string → `resolve(items_template.strip(), shared, auto_parse=True)`; the
  unconditional `try_parse_json` of a string result (`:127-130`) is deleted (a complex template's text result is
  never parsed — the one rule; the schema allows only a whole `${…}` or an array there). Caller keeps the
  "must be a list" check.
- **`execution/plan.py:1584-1595`**: the hand-copied `resolve(..., auto_parse=True)` is replaced by the engine's
  own `resolve_templates(config.template_config, per_item_context, node_id)["inputs"]` (the `_pre_warm_compile_cache`
  precedent, `batch_executor.py:215-219`); when `template_config` is `None` the static `inputs:` are used as
  today. Fallback only with a logged reason: `resolve(raw, ctx)` with `auto_parse=False` (mirrors the `inputs:`
  branch for a workflow step). Then PD types the result per item through `prepare_inputs`. `test_plan_drift.py`
  is the pin.
- **Whole-map `inputs:` (RESOLVE AT START):** a workflow step's `inputs: ${x}` must resolve to a dict; JSON TEXT
  is rejected by `_extract_child_inputs` ("resolved to str, expected dict") — today's runtime behaviour, kept;
  the planner aligns through the point above. The message gains the fix (checkpoint §1.11).
- **`core/workflow/validator.py:1801`**: `resolve_nested(params, {alias: item})` → `resolve(params, context).value`
  (no auto-parse) so literal child values reach `_check_required_inputs` as written (D11(e) coerces them).
- **Inherited with no edit** (the store carries the key): `loop_control.py:144,177`, `output_resolver.py:31,149`,
  `prompt_cache._resolve_chunk_value`, `inject_none_for_optional_inputs`, `instrumentation.py:220` (memo key for
  batch items), every `resolve_templates` caller (`engine.py:1748`, `plan_node.py:144`, `batch_executor.py:219`,
  `plan.py:1533/1706`).
- `http.params` is NOT in the table (a list leaf is legitimate repeated-param syntax; a dict leaf is mangled
  today — follow-up, §8). An int header value crashing in `requests` is pre-existing and separate (§8).

### D10 — The sub-workflow boundary types each item in `prep` (`runtime/workflow_executor.py`)

- **`_validate_child_params` becomes a call to `prepare_inputs`** — the one boundary (D5): `diagnostics,
  updates, _ = prepare_inputs(child_ir, child_params, input_sources={k: "parent" for k in child_params})`;
  `None`-valued keys are dropped first (not provided); on any diagnostic raise
  `WorkflowValidationError(validation_errors=diagnostics)` with each diagnostic's context given
  `path=nodes[id=<self.node_id>].params.inputs.<name>`, `sub_workflow_step`, `sub_workflow_path`; return
  `{**child_params, **updates}` — typed supplied values AND the env/settings/default fallbacks for absent keys,
  resolved **per item** (so item 2 omitting `n` after item 1 supplied it gets the child's `default: 3`, never
  nothing — the cached compile's `resolved_defaults` can no longer be the only source). The extras and
  required checks are `prepare_inputs`'s own; the hand-rolled `"default" not in spec` heuristic goes.
- `_PREP_RECOVERABLE` gains `WorkflowValidationError` (prep raises it only from this call — compile-time
  validation errors are raised in `exec`, wrapped as `CompilationError`, and stay fatal). The prep marker carries
  the structure: `{"_prep_error": str(e), "_prep_diagnostics": [d.to_dict() for d in e.to_diagnostics()],
  "workflow_path": path}`. `exec`'s short-circuit (`:377-388`) builds a `child_failure` bundle
  `{"workflow_path", "failed_node": None, "failures": {}, "error": str(e), "diagnostic": <first dict>}` so the
  structured error rides the existing `_pflow_child_failure` channel into batch error records and
  `build_error_list`. **Bundle key:** the writer uses `diagnostic` for both the template and the input case;
  the reader (`executor_service.py:145`) accepts `diagnostic` OR the legacy `template_diagnostic` — the bundle is
  persisted inside recorded node output (`batch_executor.py:484-486` → `workflow_trace.py` → restored by
  `resume_source.py:1031` → read by `execution_state.py:158-166`/`batch_errors.py:120`), so a pre-120 trace
  resumed after the change must still render its rich fields.
- `exec` seeding: `child_storage` is built from the complete typed `child_params`; the loop seeding
  `resolved_defaults` for absent keys (`:419-421`) is deleted (nothing is absent any more); the KNOWN LIMITATION
  comment goes; #188 closes. The compile-time `prepare_inputs` (item 0, cached per path) still runs inside
  `compile_workflow`; it now finds every key present and typed and changes nothing (idempotence, PA-4). A bad
  child DEFAULT is caught by `prep`'s call per item as a routable error AND statically by D11(a) when the child
  is validated; a bad env value for a child input is routable per item too (environment, named as such).
- Routing: non-batch → `post` returns `error_action` (default `error`), the failure record carries the bundle;
  batch `error_handling: continue` → one error record per bad item with `error` = the message's first line and
  the full Diagnostic in `child_failure.diagnostic`; `fail_fast` → the first error's text. Ruling (ii): a parent
  declared `string` holding `{"a":1}` into a child `obj: object` is parsed by the child's grammar — passes.
- **Dry-run planner mirrors prep:** `_resolve_per_item_sub_workflow_inputs` (`plan.py:1584-1595`) types each
  item's inputs through the SAME `prepare_inputs` call before `_build_plan_with_shared`; a per-item diagnostic is
  reported per item (Task 170's R10 twin: `--dry-run` of a `continue` batch reports item failures instead of
  failing the node) and the item is planned as failed. `create_planner_shared` (`:592-593`) then takes
  `{**params}` with no `resolved_defaults` overwrite of supplied keys (item 0's coerced values never overwrite
  item N). `test_plan_drift.py` pins runtime/planner agreement on typed per-item inputs.

### D11 — Validator rules (`core/workflow/validator.py`, `runtime/template_validation/`)

- **(a) Declared defaults** — `WorkflowValidator._check_input_defaults(workflow_ir)`: for every input with a
  `default`, `coerce_declared_input(name, type, default, source="default")`; a failure is the exception's
  Diagnostic (path `inputs.<name>.default`). Runs under validate-only, save, run, MCP validate.
- **(b) Paths certain to miss on a declared root** — one new pass in `validate_workflow_templates`, placed
  **before the early return at `validator.py:141`** (which fires when no node-param template and no loop exists —
  an output-only workflow whose `source:` is `${s.a ?? "fallback"}` would otherwise skip the pass and emit
  `"fallback"` silently). It walks `operands + output_operands` REGARDLESS of `OperandPolicy` (so `??` operands
  are covered — RESOLVE: the "new silent fallback") **and the `## Cache` chunk vars**, which `iter_template_operands`
  excludes (`operands.py:50`) — read them through `data_flow._cache_var_roots`'s source (the cache block's
  `var_expr`s) so `${s.a}` as a chunk var is an ERROR instead of a silently ABSENT chunk
  (`prompt_cache.py:170-174` collapses the miss to `_CHUNK_ABSENT`). Helper beside `infer_template_type`:
  `declared_root_type(workflow_ir, node, root, *, surface_kind, param_key) -> str | None` — the input's canonical
  type when the root's ACTIVE binding **on that surface** is the workflow input: for a step's own `inputs:`
  VALUES the workflow input owns the root (they resolve before the local exists — D8); for every other surface
  of that step, `data_flow.step_scope(workflow_ir, node).owner(root, has_path=…)` decides (a same-named
  `inputs:` key or the alias owns it → `None`). `any`/untyped → `None`. Rules, each an ERROR with the
  checkpoint's text: a path on `string`/`integer`/`number`/`boolean`; a `Field` on `array`; an
  `Index`/`DynamicIndex` on `object`. `${items[0]}` on an `array` and `${cfg.name}` on an `object` stay legal.
  Pass 5 already returns valid for input roots, so there is no duplicate.
- **(c) Declared `string` into a container target** — in Pass 6 (`type_validation.py:86-90`) and Pass 9
  (`:443-446`): when `declared_root_type(...) == "string"` and the target is in `CONTAINER_TYPES` → ERROR
  (`TYPE_COMPATIBILITY_MATRIX` untouched — its `"string"` row is shared with code `result: str` and child
  outputs). Fix Pass 9's suggestion to the canonical name (`- type: object`, not `- type: dict`;
  `test_types.py:1502` flips).
- **(d) `batch.items: ${v}`** with a declared root whose type is not `array`/`any` → ERROR (same pass as (b),
  surface kind `batch_items`, whole-root operand).
- **(e) Literal child `inputs:`** — `_check_required_inputs` coerces each AUTHORED literal value against the
  child's declared type (`source="parent"`); the Diagnostic path is the one it already uses
  (`nodes[id=X].params.inputs`) plus `.<name>`. "Authored" includes values `_enumerate_child_calls` derives from
  an INLINE `batch.items` list (the author wrote `"x"`; static rejection is right and pre-run); a value that
  comes from a template (`${item}` over a runtime-produced list, `${up.stdout}`) is not checked here — that is
  D10's per-item routable check. The checkpoint's routable fixture therefore produces its items at run time
  (§0), and a second fixture with inline `["7", "x", "9"]` expects the static ERROR.
- **(f) Input vs batch alias** — beside `_reject_reserved_literal_names`: an input named like any step's
  `batch.get("as", "item")` (the AUTHORED field is `batch.as`, `ir_schema.py:98`; `item_alias` is the compiled
  `BatchConfig` name) is an ERROR ("one name, one owner"), and the remedy names `as:`. The gap this change
  widens: the alias already shadows the input in every per-item context; D8 would additionally misapply the
  input's declared type to `${item…}`. Narrow member of #730; the rest stays #730's.
- Loop `while/until` with a path on a declared root is covered by (b); `max_iterations` is untouched.

### D12 — Diagnostics text

`diagnostics-checkpoint.md` holds every shape (CP-1). One builder in `InputTypeError.to_diagnostics`; the
validator rules (b)–(f) build their own Diagnostics with the same context keys. Context-key conventions row in
`runtime/template_validation/CLAUDE.md`.

### D13 — Web and formatters

- `web/src/components/RunForm.tsx:8-12`, `web/src/utils/controlForType.ts:8-9`, `web/src/components/RunPanel.tsx:24-25`:
  comments say "the CLI coerces each token by the input's declared type; `any` infers losslessly". No control
  change (`controlForType` already picks by declared type).
- `ui/run_node.read_run_inputs` docstring (`:60-95`) and `tests/test_cli/test_run_node.py:507-533`: the round-trip
  assertion goes through `coerce_declared_input` per declared type (non-`any`), not `parse_workflow_params`.
- Untyped-input readers unify on `"any"`: `discovery_formatter.py:121`, `workflow_save_formatter.py:151,226`.
- The run panel's 400 for a typed-input error renders the server's `errors[0]` (verify it does — PR #744's
  resume-panel precedent; if the run panel has its own shape, show message + suggestion the same way).

### D14 — No trace-format change; memo keys; persisted bundle key

`meta.inputs` holds typed values (already the resolved store values). No version bump; no new trace field.
Two honest notes: (1) a NON-batch step's memo key includes resolved params, so a step whose param changes type
misses once; a BATCH step's memo key is the raw items template + resolved items + batch config
(`instrumentation.py:214-231`) and ignores non-item params — a warm pre-120 batch memo whose `inputs: {data:
${s}}` now resolves to text can still hit. That is Task 170's recorded follow-up ("batch memo cache serves stale
results when a per-item template's non-item value changes"), pre-existing and not widened here — the hand-back
names it; clearing `~/.pflow/cache` is the user-side remedy. (2) The `child_failure` bundle gains the key
`diagnostic` and the reader accepts the legacy `template_diagnostic` (D10) — recorded node output, not a trace
field. `verify.sh` drift set must equal P0's unless a baseline case carries a lenient-era value — then re-record
that case with the main orchestrator's say-so (log it).

---

## 4. Phases

### Agent assignment (phases ≠ agents)

| Launch | Phases | Tier · effort | Why this boundary |
|---|---|---|---|
| I1 | P0 → PA → PC | Opus · **high** | One contract bottom-up: grammar + coercer (core) then the resolver rule (engine). PC does not depend on PB; PD depends on PC (the parent must stop parsing before the strict child boundary exists, or the 15 in-tree text→child-`string` bindings break mid-build). |
| — | **mid-task review #1** after PC | task orchestrator commissions | engine contact |
| I1 resumed (else fresh Opus · high) | PB → PD | Opus · **high** | PB is wiring (medium on its own) but PD is the sub-workflow seam; whoever holds PA's coercer contract does both. Rotate if I1 is past ~350k. |
| I2 | PE | Opus · **high**, fresh | The validator half; a fresh read of the runtime rule it must mirror is worth the rebuild. |
| — | **mid-task review #2** after PE | task orchestrator commissions | validator/runtime drift |
| I3 | PF | Opus · **medium** | Docs, guide, instruction files, web comments + one screenshot; needs the `pflow ui` slot. |
| — | PZ | task orchestrator | completion gate |

**Per-phase gate:** `make check` + `make test`, then the "FULLY happy?" resume. Direct `test-reflect` for PA
(grammar/coercer tables are easy to fake-pass), PC (resolution arms), PD (batch routing). PF: skip (docs).
Completion adds `make test-all-local`.

**CP-1 (the diagnostics checkpoint) is ruled BEFORE I1 launches** (§7).

---

### P0 — Baseline and re-verify (I1's first step)

Everything in §0, logged by name. Plus the BEFORE probes of `diagnostics-checkpoint.md` §0 re-executed.
**Handoff:** the log holds the baselines and every §0 answer; nothing edited.

### PA — Grammar, coercer, error, `prepare_inputs` (core; no engine)

**Goal:** `coerce_declared_input` exists and is strict; `prepare_inputs` resolves in the right order, coerces
every source, returns Diagnostics; the lenient path is gone.

**Files:** `core/types.py` (D1), `core/param_coercion.py` (D2), `core/exceptions.py` (D3),
`runtime/compilation/ir_preparation.py` + `compile_validation.py` (D5; `compile_workflow` gains
`input_sources`, D4), `core/validation_utils.py` (unchanged; placeholder constant reused), `core/CLAUDE.md`
(Types/coercion section), `runtime/compilation/CLAUDE.md:58-61`.

**Tests to flip (named):** `tests/test_core/test_param_coercion.py` — every `*returns_original` test
(`:233,273,302,308,340,357,364,370,381,387`), the stringify tests `:178-205` (non-string scalars into `string`
now go through `to_string`: `True` → `"True"` stays; a dict into `string` → error), `:250/:261/:267` keep their
accepted spellings, `:439` placeholder stays; `tests/test_runtime/test_prepare_inputs_coercion.py:18,79,134,143,153,163,258,277`
(`:163` "invalid coercion returns original" → raises/diagnostic); `test_settings_env_integration.py:66`
(env over default — now also holds through the runner, PB); `test_prepare_inputs_extras.py`, `test_null_defaults.py`
(a supplied `None` = not provided). Tests asserting `SchemaValidationError` from `compile_workflow` input errors
flip to `WorkflowValidationError`.

**Tests must catch:**
1. **Grammar table** (one row per cell; both accept and reject columns): integer `3`, `-3`, `007`→7, ` 3\n`→3
   (stripped), reject `3.0`, `1e3`, `true`, `1_000`, `٣`, `""`; number `3`→`3` (int), `3.0`→`3.0`, `1e3`→
   `1000.0`, `-0.5`, `0`→`0`, reject `007` (not a JSON number), `nan`, `inf`, `Infinity`, `1_000`, `abc`;
   `None` → `None` for every type (no value, no error); boolean the twelve spellings
   case-insensitive, reject `maybe`, `2`, `""`; object `{"a":1}`, reject `[1]`, `{`, `"x"`; array `[1]`, reject
   `{"a":1}`, `1`; string anything, untouched (` 42` keeps its space).
2. **Non-text table (h):** `string` ← `3`→`"3"`, `True`→`"True"`, `2.5`→`"2.5"`, `{"a":1}`→error, `[1]`→error;
   `integer` ← `3` ok, `True` error, `3.0` error; `number` ← `3`, `2.5` ok, `True` error; `boolean` ← `True` ok,
   `1` error, `"1"` ok (text); `object` ← dict ok, list error; `array` ← list ok, dict error.
3. **`any` lossless (argument):** `true`→`True`, `42`→`42`, `[1]`→`[1]`, `{"a":1}`→dict; `02134`, `1.10`,
   `0755`, `1e3`, `TRUE`, `yes`, `null`, ` 42`, `[1, 2]` → the same text. `any` from `stdin`/`call`/`env`/
   `parent`/`recorded`/`default` → the value as given (`"42"` stays `"42"`).
4. **Idempotence:** for every type and every accepted value `v`: `coerce(coerce(v)) == coerce(v)` (property-style
   over the tables; the resume/child-compile/preflight contract).
5. **Placeholder** passes for every type with no warning (`:439` kept) and no log record at WARNING.
6. **Masking + truncation:** input named `token` with value `abc` → `received == "<REDACTED>"` in context and
   message; a 300-char value → 80 chars + `…`.
7. **`prepare_inputs` order:** `required` + `default`, nothing supplied → the default (not "requires input");
   env set → env wins over default; settings over default; supplied over env; supplied `None` → falls to
   env/default/None; required + `None` and nothing else → "requires input".
8. **Every source labelled:** `argument` (default), `stdin`, `recorded`, `call` via `input_sources`; `env`,
   `settings`, `default` from resolution — assert `context["source"]` and `context["path"]`
   (`inputs.n` vs `inputs.n.default`).
9. **Aggregation:** two bad inputs → two Diagnostics, each with its own path and suggestion (the
   `compile_validation` collapse is gone); through `compile_workflow` → `WorkflowValidationError` with both.
10. **No warning path remains:** `grep -n "logger.warning" core/param_coercion.py` is empty; `caplog` at WARNING
    stays empty for a failing coercion (the error is raised instead).

**Mid-task review:** no (PC's covers PA's contract).
**Handoff:** `compile_workflow` on a bad root input raises `WorkflowValidationError` with D3's Diagnostic; the
runner path still pre-fills defaults (PB fixes); `pflow` CLI still infers (PB).

### PC — The resolver rule and the engine sites · **ENGINE CONTACT** · triggers mid-task review #1

**Goal:** a reference rooted in a declared non-`any` input is never JSON-parsed, root-wide; the parent hands a
workflow step's `inputs:` on unparsed; a code `str` input gets text; `http.headers` leaves stay text; every
auto-parse site is one of the two in `core/templates`.

**Files:** `core/templates.py` (D8: `DECLARED_INPUT_TYPES_KEY`, `_declared_typed`, `_evaluate` returns the
winning operand, `_resolve_string` leaf, `_walk`), `core/ir_schema.py` (`declared_input_types`),
`runtime/engine/types.py` (`TemplateConfig.text_input_keys`; `CompiledWorkflow.input_types`),
`runtime/compilation/compiler.py` (fill both), `runtime/engine/template_resolution.py` (D9; the two merge-point
map rewrites), `runtime/engine/engine.py:887-915` (install/restore the key), `execution/runner.py:352` (install
in the root store), `runtime/engine/template_errors.py:200-215` + `core/diagnostic_render.py` (the W5 branch),
`runtime/engine/batch_executor.py:108-132`, `execution/plan.py:580-600` (`create_planner_shared` install;
`:1584-1595` is PD's), `core/workflow/validator.py:1801`, `core/workflow/template_surfaces.py` (delete
`binds_as_text`), `core/CLAUDE.md` Template language, `runtime/engine/CLAUDE.md:80-81`,
`core/workflow/CLAUDE.md:13`, `runtime/CLAUDE.md:53-56`.

**Tests must catch:**
1. **The leaf rule (`core/templates`, direct):** `resolve("${s}", {"s": '{"a":1}', KEY: {"s": "string"}},
   auto_parse=True).value` is the TEXT; without the key, or with `{"s": "any"}`, it is a dict (presence pair);
   `${s ?? u.out}` where `s` is absent and `u.out` is JSON text → parsed (the winning operand decides); where `s`
   is present → text.
2. **Root-wide walk:** `resolve("${d.payload.a}", {"d": {"payload": '{"a":1}'}, KEY: {"d": "object"}})` is
   unresolved; same without the key resolves `1`; `${d.payload}` → the text; `${arr[0].x}` on a declared
   `array` whose element is a dict → resolves (no string in the path); a declared `any` with JSON text and
   `${v.a}` → resolves (today's traversal parse kept — spec break 8's fix is the CLI side).
3. **Mutation ledger** (apply, run, restore, record): drop the `_walk` check → test 2 red; drop the leaf check →
   test 1 red; drop the install in `engine.run` → the integration rows below red.
4. **`resolve_templates` through a compiled workflow** (`compile_workflow` + `resolve_templates(cfg, shared, id)`
   with the key installed): a code step `inputs: {t: ${s}}` with `s: string` = `{"a":1}` → `t` is text (#686);
   with `t: str` annotation and `t: ${up.stdout}` JSON → text (consumer rule, presence pair: `t: dict` → dict);
   `agent` step `inputs: {t: ${up.stdout}}` → dict (no annotations); a `workflow` step `inputs: {s: ${up.stdout}}`
   → text (the parent stops parsing); `http` `headers: {X: ${up.stdout}}` JSON → text; `http` `params:
   {ids: ${up.list_text}}` → still parsed (not in the table); shell `env:` still text (118 row stays green).
5. **Shadowing:** a step with `inputs: {data: ${up.stdout}}` and a sibling param `${data.a}` where a workflow
   input `data: string` also exists → the sibling reads the local (parsed) value; the workflow input `data`
   referenced from ANOTHER step stays text.
6. **Simple-into-container fold:** `${v}` (string input, JSON object text) into a dict-typed registry param →
   `validate_resolved_type` error naming the declared input (not a dict); `${up.stdout}` JSON into the same param
   → dict (today's behaviour); `${up.stdout}` holding `{"a":1}` into a LIST-typed param → the type error names
   `dict` (the accepted delta).
7. **Batch items:** `items: ${arr}` (declared array, value list) → list; `items: ${s}` (declared string holding
   `["a"]`) → NOT a list → the "must be an array" error (validation rejects it statically in PE; runtime stays
   loud); `items: ${up.stdout}` JSON list text → list; inline `["${s}", "${up.stdout}"]` → `s` text, `up.stdout`
   parsed; a complex template result is never parsed (presence pair with the simple form).
8. **Dry-run parity:** `test_plan_drift.py` green; a new case: batched workflow step with `inputs: {s: ${item}}`
   over JSON-text items — `--dry-run` and the run agree the child receives TEXT (PD makes the child parse it by
   declaration).
9. **Install/restore:** after `engine.run` the key is restored to its prior value (mirror the prompt-cache test);
   a nested child's store holds the CHILD's map, the parent's is untouched after the child returns.
10. **Loop carry** keeps upstream semantics: a carried key sharing a name with a declared string input is local
    (parsed as before).
12. **Post-run readers:** after `runner.run`, `-o d.payload.a` on a declared object `d` whose `payload` is JSON
    text prints "not found" (the runner's store carries the key after the engine's `finally`); `-o d.payload`
    prints the text (presence pair).
13. **The miss message:** `${data.payload.a}` unresolved at run → the rendered text names `data.payload` as
    text that is not parsed and the two remedies (checkpoint §1.14); `context["text_not_parsed"] ==
    "data.payload"`; a plain missing field (`${data.nope}`) keeps today's "has no 'nope'" text (presence pair).
11. `test_template_grammar_seam.py`, `test_import_hygiene.py`, the `core.templates` subprocess pin: unchanged and
    green.

**Real-surface exercise (I1, logged):** the checkpoint probes `a-string` (#686) and `container` now print text /
fail per the AFTER; `uv run pflow` on `examples/nested/deep-research/analyze-source.pflow.md`-shaped parent→child
text binding still runs (pick one of the fifteen in-tree bindings; the child is strict only after PD, so at PC
this proves the parent hands text on).

**Mid-task review #1** (engine contact) on PA+PC's diff — each lens assigned to the phase that introduces the risk:
- `review-impact-completeness` — **PA** (the coercer replaces a shared helper; every caller of
  `coerce_workflow_input`, `binds_as_text`, `parses_leaves`, `resolve_nested`) and **PC** (every string→typed
  site in §2.2 is now one of two).
- `review-silent-failures` — **PA** (`None` = not provided; placeholder passthrough; the deleted warning path)
  and **PC** (root-wide misses must surface through `Resolution.unresolved`, never resolve to the text).
- `review-feature-interactions` — **PC** (batch items, nested children, loop carry, dry-run, memo keys, the
  prompt-cache chunk path, MCP's typed values).
Fixes fold in before PB.

### PB — Entry sites: runner, CLI, MCP, analyze, web preflight

**Goal:** the CLI never guesses; every entry path reaches the coercer with its source; `--validate-only` checks
the user's values; env beats default; analyze fails loudly.

**Files:** `execution/runner.py` (D4 kwargs, D6), `cli/param_parsing.py` + `cli/commands/run.py`, `resume.py`,
`analyze_cache.py`, `_probe_impl.py`, `cli/rerun_display.py` (delete), `ui/server.py` (comment only),
`mcp_server/services/execution_service.py` (D4 labels), `core/prompt_cache_analysis/analyze.py` (D6),
`core/prompt_cache_analysis/context.py:51-53` (now true — reword), `cli/CLAUDE.md:15` and the rerun row,
`execution/formatters/discovery_formatter.py:121`, `workflow_save_formatter.py:151,226` (untyped → `any`).

**Tests to flip (named):** `tests/test_cli/test_direct_execution_helpers.py` (`TestInferType` stays for the
probe; `TestParseWorkflowParams:70-112` → raw strings); `tests/test_cli/test_rerun_display.py` (deleted with the
module); `tests/test_cli/test_validate_only.py:205-235` ("skips prepare_inputs" → "checks supplied values,
tolerates missing"); `tests/test_execution/test_runner.py:617-671` (defaults applied by compile, not by the
runner pre-fill); `tests/test_nodes/test_file/test_delete_file.py:124,155` docstrings (`"false"` stays the
text `false`, still refused — behaviour unchanged, wording fixed; `delete_file.py:90-91` comment likewise).

**Tests must catch:**
1. **#687 through the real CLI** (`CliRunner` + one subprocess for the stdin half): `text=02134`, `1.10`, `TRUE`,
   `1e3`, `{"a":1,"b":[1,2]}` on a `string` input reach a shell `env:` byte-identical; piped stdin agrees;
   `pflow resume <id> text=0099` and `--only step text=0099` deliver `0099`.
2. **Breaks 1, 4, 5, 6, 7:** `type: array` + `tea`, `type: integer` + `3.0`/`1e3`/`true`, `type: boolean` +
   `maybe`, `type: number` + `abc`, `type: object` + `[1,2]` → exit 1 with D3's text; a run with NO annotated
   consumer (`number` + `abc` into a shell env) fails at the boundary (break 1's exit-0 case).
3. **f₂:** `default: 8080` + `port=abc` in the environment → the env error naming the environment variable;
   `port=9090` → 9090 (presence pair); `port=1` argument beats both.
4. **Validate-only parity:** `--validate-only topics=tea count=abc` → both Diagnostics, exit 1; with no params →
   exit 0 (missing required tolerated); an undeclared `BOGUS=x` → exit 1 (the #297 extras half); the same
   workflow's run gives the same messages.
5. **Multi-input text + JSON:** two bad inputs → two `errors[]` entries, each with its own `path`/`suggestions`;
   text shows both blocks; no `resume_command`, no "To resume" line (presence pair: a run that fails at step 2
   does print it).
6. **MCP `workflow_execute`:** `{"count": 3.0}` for an integer → error with `source: "call"` and the JSON-shaped
   fix; `{"count": null}` for a required input → "requires input"; `{"opt": null}` optional → `None`; `"42"` for
   an `any` input stays `"42"` (no inference off the CLI).
7. **Resume replay:** a trace whose `meta.inputs` carries `"abc"` for an integer (write the fixture by hand —
   lenient-era) → the `recorded` error naming `pflow resume <id> count=3`; `"7"` recorded for an integer → replays
   as 7; a scalar recorded for a `string` → text.
8. **Analyze:** `analyze-cache wf count=abc` → the typed error, exit 1, in text AND `--format=json` (the JSON
   envelope, not the group handler's text); `analyze-cache wf` with a required input omitted → analysis runs
   (DD#35, `test_cache_analysis_analyze.py:5261` stays green); MCP analyze returns the structured diagnostic
   (not `RuntimeError("❌ Cache analysis failed…")`); a valid run's `ctx.parameters` holds coerced values;
   `${data.payload.a}` into JSON text inside a declared object is unresolved in the analyzer's token estimate
   exactly as at run time.
9. **UI preflight:** `/api/run` with `count=3.0` → 400 whose `errors[0]` is D3's Diagnostic; `count=3` → spawn.
10. **`last_execution_params`** stores `3` (int) for `count=3` on a saved workflow.
11. `pflow probe` still infers node params (`TestInferType` + one probe test with `limit=3` → int).

**Real-surface exercise (logged):** the checkpoint §0 probe set, re-run — every BEFORE becomes its AFTER.

**Mid-task review:** no (wiring; PZ's falsifier executes every promise here).
**Handoff:** every entry path is strict; the child boundary still seeds raw values (PD).

### PD — The sub-workflow boundary, per item, routable

**Goal:** a child input is typed by the child's `## Inputs` in the host's `prep`, per item, routable by
`error_action` and batch `continue`, with the structured error intact; the dry-run planner no longer lets item
0 overwrite later items.

**Files:** `runtime/workflow_executor.py` (D10), `execution/executor_service.py:143-157` (bundle key
`diagnostic`), `execution/plan.py:592-593`, `runtime/CLAUDE.md` Nested workflows, `runtime/compilation/CLAUDE.md:61-64`
(the "current limitation" sentence goes).

**Tests to flip:** `test_workflow_executor_comprehensive.py:963` (`test_params_as_inputs_basic`: `count: 5`
stays 5 — typed), `:1131/:1155` (required/default harmonisation), `test_compile_once_regression.py:481`
(deepen: a child `n: integer` fed per-item `"7"`, `"8"` → each item's own int; the test today cannot see the
leak), `test_prep_error_action.py:278,354` (the error record carries `child_failure.diagnostic`).

**Tests must catch:**
1. **The spec's named test:** a batch of three children `n: ${item}` over a RUNTIME-produced list
   (`items: ${emit.stdout}`, a shell step printing `["7","x","9"]`) with `batch.error_handling: continue` →
   items 0 and 2 succeed with `n == 7`/`9` (int), item 1 is an error record whose `error` first line is the
   D3 message and whose `child_failure.diagnostic.context` has `input: "n"`, `source: "parent"`,
   `sub_workflow_step: "call"`; sequential AND parallel; `fail_fast` stops at item 1 with the same text; the
   batch exit is DEGRADED, not a `RuntimeError`. (The same with an INLINE list is PE-5's static ERROR.)
1b. **Fallbacks per item (C1):** child `n: integer, default: 3`; items `[{"n": "7"}, {}]` through
   `inputs: ${item}` sequentially → item 0 gets 7, item 1 gets 3 (not nothing; a child `${n ?? 99}` must give
   3). Same with an env value for `n`. Same under parallel.
1c. **Null is absence:** a parent `${up.result}` resolving to `None` for an optional child input → the child
   sees `None` (or its default), no error; for a required one → the "requires input" diagnostic, routable.
2. **Non-batch:** `inputs: {n: "x"}` (literal) is caught by PE statically — so use `n: ${up.stdout}` = `x` →
   `error_action: continue` routes; default routing fails the run with the Diagnostic rendered (text + JSON
   `errors[0].context.path == "nodes[id=call].params.inputs.n"`), no "To resume" hint for a step-1 failure but
   the hint present when a step ran before (presence pair).
3. **Ruling (ii):** parent `s: string` = `{"a":1}` → child `obj: object` receives a dict; child `s: string`
   receives the text (#686's child half; break 10).
4. **Compile cache:** item 0 valid, item 1 invalid, item 2 valid → item 2 still typed (the per-item check does
   not depend on the cached compile); the child's env/default fallbacks still resolve for absent keys on every
   item (a child `limit: integer, default: 3` not supplied → 3 in every item).
5. **Harmonised required:** a child input with `default` and no `required: false`, not supplied → runs with the
   default (both `_validate_child_params` and `prepare_inputs` agree).
6. **Dry-run:** `--dry-run` of the three-item batch plans items 0 and 2 with TYPED inputs (`n` is `7`/`9` in
   the per-item planner shared, matching the run) and reports item 1 as failed with the same message;
   `test_plan_drift.py` green with a new typed-per-item case.
7. **Bundle key:** `build_error_list` renders an input-failure bundle (`diagnostic`), a fresh template-failure
   bundle (`diagnostic`), AND a hand-written legacy bundle carrying `template_diagnostic` (a pre-120 trace
   restored through resume) with the rich fields intact.

**Real-surface exercise (logged):** checkpoint §0 probe `parent-batch` → the AFTER (two successes, one item error,
DEGRADED).

**Mid-task review:** no standalone — PE's review #2 reads PD's runtime beside PE's validator; if the orchestrator
judges PD risky on its own, `review-feature-interactions` on PD's diff (batch × nested × error routing).

### PE — Validator rules and the parity corpus · triggers mid-task review #2

**Goal:** validate-only rejects what the runtime would refuse or silently miss under the new rule; the parity
corpus pins validator ⟷ runtime for every surface.

**Files:** `core/workflow/validator.py` (D11 a, e, f), `runtime/template_validation/type_checker.py`
(`declared_root_type`), `runtime/template_validation/validator.py` (the new pass), `type_validation.py:86-90,316-321,443-446`,
`runtime/template_validation/CLAUDE.md`, `tests/test_integration/test_template_parity.py`.

**Tests to flip:** `tests/test_runtime/test_template_validation/test_types.py:1502` (`- type: object`).

**Tests must catch:**
1. **(a) defaults:** `- default: abc` on `integer` → ERROR at `inputs.n.default` under `--validate-only`, `save`
   and run; `- default: 1.10` on `string` → ok (YAML-typed `1.1` is a scalar into string — #742's domain);
   `- default: true` on `boolean` ok; `- default: [1]` on `object` → ERROR.
2. **(b)** `${s.a}` string, `${n.x}` integer, `${items.name}` array, `${cfg[0]}` object, `${cfg[${i}]}` object →
   ERROR each with the checkpoint text; `${items[0].name}`, `${cfg.name}`, `${v.a}` on `any`, `${u.a}` untyped →
   ok. Also as `??` operands (`${s.a ?? "x"}` → ERROR; `${items[0] ?? "x"}` ok), in `loop.while`, as an output
   `source`, and inside `batch.items`.
3. **(c)** `${s}` into a code `inputs:` key annotated `dict`/`list` → ERROR naming `- type: object`/`array`;
   into a registry dict param → ERROR; `${up.stdout}` into either → ok (matrix unchanged, presence pair);
   `${s}` into `x: str` → ok.
4. **(d)** `batch.items: ${s}` → ERROR; `${arr}`, `${anyv}`, `${up.stdout}` → ok.
5. **(e)** literal `inputs: {n: abc}` → child `integer` → ERROR at `nodes[id=call].params.inputs.n`; `n: "7"` ok;
   `s: '{"a":1}'` → child `string` ok (text stays text); per batch item for inline items.
6. **(f)** input `item` + a batched step with the default alias → ERROR; input `entry` + `batch: {as: entry}` →
   ERROR naming `as:`; renamed → ok.
7. **Shadowing, both directions:** step `inputs: {s: ${up.stdout}}` + sibling `${s.a}` with workflow input
   `s: string` → ok (the active binding is local); the same step's own `inputs: {s: ${s.a}}` → ERROR (the
   VALUE resolves against the workflow input); `inputs: {data: ${data}}` annotated `Any` with `data: string`
   → the runtime leg hands TEXT to the code step (D8's merge-point rule; the #686 reopening case).
7b. **Reachability (F2/F3):** an output-only workflow (literal shell command, `source: ${s.a ?? "x"}`) → ERROR
   (the pass runs before the early return); a `## Cache` chunk var `${s.a}` with `s: string` → ERROR; the same
   two with `s: any` → ok.
8. **Parity rows** (validator outcome / runtime outcome, through the harness's real entries; `declared_inputs`
   per row): `param ${s}` string JSON-text → `Ok`/`Resolves(text)`; `param ${s.a}` → `Error`/`Unresolved`;
   `param ${d.payload.a}` (object, payload text) → `Ok`/`Unresolved` (the converse direction holds: reported, not
   silent); `param ${v.a}` any → `Ok`/`Resolves(1)`; `batch_items ${s}` → `Error`/`Raises`; `batch_items ${arr}`
   → `Ok`/`Resolves(list)`; `loop_while ${s.a}` → `Error`/`Raises`; `output_source ${s.a}` → `Error`/`Raises`;
   `sub_inputs s: ${s}` (child string) → `Ok`/`Resolves(text)`; `sub_inputs obj: ${s}` (child object, text
   `{"a":1}`) → `Ok`/`Resolves(dict)` (ruling ii); `param ${s ?? "x"}` → `Ok`/`Resolves(text)`;
   `param ${s.a ?? "x"}` → `Error`/`Resolves("x")` (the silent fallback the validator exists to catch — row
   comment says so). Add `consumer="code:str"` if the harness lacks it.
9. The direct runtime driver (`_input_values`, `:355-364`) seeds inputs TYPED through `coerce_declared_input` so a
   row's runtime leg sees what a run would.

**Mid-task review #2** on PC+PD+PE: `review-validation-consistency` — introduced by **PC/PD** (runtime parsing and
the child boundary changed) and mirrored by **PE**; target: `runtime/template_validation/*`,
`core/workflow/validator.py` vs `core/templates.py::_resolve_string/_walk`, `template_resolution.py`,
`workflow_executor.py::_validate_child_params`.

**Handoff:** validate-only and run agree on every parity row; `make test` green.

### PF — Guide, docs, instruction files, web comments, CLAUDE.mds

**Goal:** no shipped text promises auto-parse for declared inputs or CLI type inference; the type table is the
home of decision (b); the two MCP instruction copies match the guide; the searcher def knows the new names.

**Edits (verified sentences, §6):**
- `src/pflow/guide/core.md:437-470` — "Simple templates automatically parse JSON strings" becomes the rule:
  `${step.output}` text that is JSON is parsed when it enters a structured param or a non-`str` code input;
  `${input}` is whatever the input's declared type says, never re-parsed; the `'42\n'`→42 and `'true'`→true rows
  (false today) go. `:661-675` type table — the (b) grammar per type, "integer: rejects 3.0, 1e3, true; accepts
  007", `number`, `boolean` spellings, `any`: "lossless inference from a CLI argument; MCP values as sent".
  `:298` `any`/untyped sentence.
- `src/pflow/mcp_server/resources/instructions/mcp-agent-instructions.md:1022-1045,1276` and
  `mcp-sandbox-agent-instructions.md:1001-1024,1255` — the same two edits, by hand (note #749).
- `src/pflow/guide/nodes/code.md:64` — "a `str` annotation receives the text as is; declare `dict`/`list` to have
  JSON text parsed". `guide/nodes/shell.md:54` — drop "typed first (`007` → `7`)"; the `inputs:`-map parse
  sentence becomes "a workflow input keeps its declared type everywhere; an upstream output routed through an
  `inputs:` map is JSON-parsed unless the key is annotated `str`". `guide/features/batch.md:37` — "a declared
  `array` input or an upstream list / JSON-array text". `guide/nodes/file.md:28` stays true.
- `docs/reference/cli/index.mdx:152-158` — type inference paragraph → "each `name=value` is read by the input's
  declared type; `--validate-only` with values checks them (CLI only — MCP `workflow_validate` takes no
  parameters)". `docs/reference/nodes/code.mdx:104-110`, `docs/how-it-works/template-variables.mdx:90-123`
  (add one sentence: references rooted in a declared input are never re-parsed), `docs/reference/nodes/index.mdx:67`
  (one sentence: "unless the value comes from a declared input").
- `src/pflow/core/CLAUDE.md:105-107,199-201`, `core/templates.py:43-46`, `architecture/reference/template-variables.md:621-623`
  (`TypeSpec.accepts` now has callers — state the real split: `parse_text` for text, `accepts` for values);
  `runtime/compilation/CLAUDE.md:58-66`, `runtime/engine/CLAUDE.md:80-81`, `runtime/CLAUDE.md:53-56`,
  `cli/CLAUDE.md:15` (+ delete the rerun row), `core/workflow/CLAUDE.md:13` (row moved), `runtime/template_validation/CLAUDE.md`
  (context keys; the new pass).
- `src/pflow/core/param_coercion.py` docstrings (PA wrote them; PF greps each distinctive phrase across `src/`
  and the CLAUDE.mds before committing).
- `architecture/core-concepts/data-type-coercion.md:67-146` — rewrite the inventory to the two sites + the input
  boundary; drop the deleted-file citations.
- `web/src/components/RunForm.tsx:8-12`, `web/src/utils/controlForType.ts:8-9`, `web/src/components/RunPanel.tsx:24-25`
  (D13).
- `.claude/agents/pflow-codebase-searcher.md:129` — add `coerce_declared_input`, `InputTypeError`,
  `DECLARED_INPUT_TYPES_KEY`, `parses_leaves`; fix the row that points code-annotation extraction at
  `data_flow.py`/`type_validation.py` (it lives in `nodes/python/python_code.py`). Then `make sync-claude-assets`.
- `context/CONTEXT.md`: propose (not write) the noun **Declared type** — "the type an `## Inputs` entry (or a
  code `inputs:` annotation, or `env:`) fixes for a value where it enters; never re-inferred downstream" — for
  the main orchestrator.

**Real-surface exercise:** `screenshot-pflow-web-ui` — open the run form of a workflow with `integer`/`boolean`/
`array` inputs, submit `count=3.0` → the panel shows the typed-input error text; submit `count=3` → the run
starts; re-open the run and confirm prefill shows `3`/`true`/`["a"]` for non-`any` inputs. Kill the server by
PID; declare `dev servers: none`. Also `uv run pflow guide` renders; `tests/test_docs/*` green;
`scripts/check_mdx_fences.py` passes (pre-commit).

**Mid-task review:** no.

### PZ — Completion (task orchestrator)

1. Merge `origin/main`; `make check`; `make test-all-local`; `verify.sh` drift set == P0's (or the logged
   re-record); `capture.py --check` clean.
2. Walk the spec's Verification list on the real surface (§6 matrix) through `uv run pflow`, the MCP server
   (`workflow_execute` with a typed JSON value), the web form (PF's screenshots), resume and a child.
3. **Code-mode `deep-review`** on the full branch (sensitive paths: engine, `mcp_server` touched → full floor):
   `review-silent-failures`, `review-impact-completeness`, `review-feature-interactions`, `review-test-fidelity`;
   `review-validation-consistency` (validator + runtime twin); `review-agent-ux` (every message in the
   checkpoint + guide/docs); **`review-simplicity`** and **`review-spec-conformance`** (completion-gate only);
   `review-falsifier` last, direct launch, with the spec and the conformance lens's Requirement Inventory.
4. Close-out: spec `## Status: done` + `## Completed`; `create-task-review` (inheritors: #743 shares
   `coerce_declared_input` + `InputTypeError`; Task 112 shares `TypeSpec.accepts`/`parse_text` + the context keys;
   Task 121 feeds typed mock values through the same boundary; Task 181's insert now renders declared inputs
   typed); `create-pr` — "Closes #686, Closes #687, Closes #188; Refs #297 — not a closing PR; Refs #742, #743 —
   not closing PRs". Check `gh pr view --json closingIssuesReferences`.
5. Hand-back note for the user — behaviour changes with no diagnostic: (a) `type: any` CLI tokens like `02134`
   now stay text (was int); (b) `[1, 2]` with a space for an `any` input stays text until a structured consumer
   parses it; (c) a `number` input renders `3` not `3.0` for integer text; (d) `${data.payload.a}` into a JSON-text
   descendant of an `object` input is now unresolved (root-wide); (e) `http.headers` JSON-looking values stay
   text (were parsed, then crashed in `requests`).

---

## 5. Verification matrix (spec → evidence)

| Spec line | Evidence |
|---|---|
| Breaks 1, 4, 5, 6, 7 — actionable error at input time | PA-1/2, PB-2, PB real-surface |
| Break 2 (#686) — declared `string` stays text into code `inputs:` | PC-4, PE-3/8, PB-1 |
| Break 3 / 11 (#687) — CLI, resume, `--only` byte-exact | PB-1 |
| Break 8 — `any` + `02134` stays text (lossless) | PA-3, PB-6 (MCP `"42"` stays) |
| Break 9 — `${v.a}` on a `string` is a validation error (also `??`) | PE-2/8 |
| Break 10 — child boundary typed per item | PD-1/3, PE-8 `sub_inputs` rows |
| Break 12 — invalid declared default rejected | PE-1, PB-4 |
| f₂ — env beats default; error names the source | PB-3, PA-7/8 |
| `--validate-only` with values agrees with the run, defaults included | PB-4, PE-1 |
| Upstream-output auto-parse unchanged; the fifteen text→child-`string` bindings keep working | PC-4/7, PD-3, the real-surface run at PC |
| MCP / web / resume / child deliver the same typed value | PB-6/7/9, PD-3, PE-9 |
| Resume idempotent; lenient-era value names the override | PA-4, PB-7 |
| No trace-format change; Task-159 baseline | P0 + PZ `verify.sh` |

---

## 6. Stale-surface inventory

Listed in PF with corrected lines (§2.1). "Already false today" (fix regardless): `guide/core.md:447,456-457`
(all-JSON-types / `'42\n'`→42); `core/CLAUDE.md:105-107`, `core/templates.py:43-46`,
`architecture/reference/template-variables.md:621-623` (`TypeSpec.accepts` in use); `prompt_cache_analysis/context.py:51-53`
(post-coercion); `compile_validation.py:157-160` docstring (returns a 4-tuple); `runtime/compilation/CLAUDE.md:58`
("does not mutate" — true of `prepare_inputs`, not of `_prepare_compilation`); `python_code.py:198-199`
(annotation scope claim — note only, #735's area).

---

## 7. Embedded checkpoints (flagged — plan them as hand-backs)

- **CP-1 — diagnostics, show before code (`diagnostics-checkpoint.md`).** Drafted by the planner with the BEFORE
  executed. **The build does not start until it is ruled.** Rulings that change structure: R1 (title wording)
  strings only; R2 ("source" phrasing per source) strings only; R3 (whether the (c) container error also names
  `??` explicitly) strings only; R4 (the settings fix command text) — the implementer verifies the exact
  `pflow settings` subcommand; R5 (truncation length 80) a constant.
- **CP-2 — coordination, not the user.** Task 181 merged before I1 launches (§0). PF needs the `pflow ui` slot.
  Task 183 in flight: serialize PC/PD behind its merge if both touch the engine concurrently (main orchestrator).

---

## 8. Risks, unverified, follow-ups

**Unverified (P0 closes each):** 181's final shapes (§0); that `dict(shared)` in `resolve_templates` keeps
`__*__` keys for the new one as it does for `__pflow_prompt_cache__`; that no trace reader consumes the bundle
key `template_diagnostic` (grep says none); whether the parity harness can seed typed inputs for the direct
runtime driver (PE-9) without changing its `Row` shape (if not, add `declared_inputs` typing to `_input_values`).

**Accepted costs:** `[1, 2]` (spaced) for an `any` CLI token stays text until a structured consumer parses it;
a `${d.payload.a}` into a JSON-text descendant of a declared `object` input is unresolved (ruling (i)); a
whole-map `inputs: ${x}` holding JSON text is rejected (today's runtime behaviour, now with the fix in the
message); `--dry-run` does not run the per-item child check (documented).

**Follow-ups to file at the merge seam (verified, not built):**
- Batch memo keys ignore non-item params (`instrumentation.py:214-231`) — a warm pre-120 batch memo can serve
  a dict where a fresh run now hands text (D14 note; Task 170's recorded follow-up; pre-existing, not widened).
- `type_checker.infer_template_type` types a sibling param's `${v.a}` from a workflow input `v` even when the
  step's own `inputs.v` shadows it (`:41-44`); `declared_root_type` (D11) handles the new pass only.
- A simple template of a container source into a code `x: str` (or `${count}` integer into `x: str`) validates
  through the matrix (stringification) but the simple template preserves the type → runtime TypeError (spec
  battery S4; pre-existing; not widened here).
- `http.headers` with an int/float value crashes in `requests` (`InvalidHeader`); `http.params` with a dict leaf
  is mangled to its keys (list leaves are legitimate) — the text rule covers only `headers`.
- #297's remaining half: move root shape checks into `WorkflowValidator`, one message per violation across the
  three layers.
- #730 / #300: the full one-name-one-owner rule (this task adds only input-vs-alias).
- Task 112 top-block reconciliation sentence (handed up): "Both checkpoints use `TypeSpec` on canonical names —
  `parse_text` for text, `accepts` for values; 112 translates registry names through `PYTHON_ALIASES_AT_S1` first
  — and build Diagnostics with the shared context keys `input|param`, `declared_type`, `received`, `accepted`,
  `path`."
- ADR-0017 wording (amend only through the main orchestrator): the carrier is name→type on the shared store
  (`__pflow_input_types__`, installed like `__pflow_prompt_cache__`), not a name set on `TemplateConfig`; the
  rejected "by NAME" option's objections (any/untyped, shadowing) are what the type map and the per-step
  shadow rule answer.

---

## 9. Plan-mode battery (2026-10-10) — dispositions

Seven codex lenses through the pflow fan-out (`scratchpads/task-120-plan-review/report.md`, exit 0, no failed
lens). Each finding verified against code by the planner before folding:
- **Confirmed, folded:** F1 shadowing stripped too early (D8 merge points; D11(b) surface-aware;
  PC-5/PE-7); F2 early return skips output-only refs (D11(b) placement; PE-7b); F3 cache chunk vars (D11(b);
  PE-7b); F4 null at direct callers (D2/D5 "None is absence", D10 via `prepare_inputs`; PD-1c); F5 analyzer
  rejects omitted inputs (D6 placeholders; PB-8); F6/W3 analyzer error routing CLI + MCP (D6; PB-8); F7 inline
  items are authored literals (D11(e); checkpoint fixture split; PD-1); F8 `batch.as` (D11(f); PE-6); F9
  analyzer contexts (D6; PB-8); F10 `number` is JSON-number first (D1; PA-1); C1 per-item fallbacks (D10 =
  `prepare_inputs`; PD-1b); W1 bundle key compatibility (D10/D14; PD-7); W2 dry-run typed per item (D10; PD-6);
  W4 post-run `-o` readers (D8 runner install; PC-12); W5 miss message (D8; PC-13; checkpoint §1.14); S1
  suggestions never echo a sensitive value (D3); S2 `pflow settings set-env` (checkpoint R4).
- **Disputed:** C2 (batch memo served across the change) — pre-existing: the batch memo key never included
  non-item params (Task 170 task-review follow-ups); not widened by this task; the D14 claim is corrected and
  the hand-back names the user-side remedy.
