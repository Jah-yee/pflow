# Template Validation Package

`validate_workflow_templates` checks templates before execution. Its production
caller is `core/workflow/validator.py::WorkflowValidator`; compilation does not
run these passes.

## Find the check

| Symptom or change | Owner |
|---|---|
| Malformed template (the one Issue pass), unused input, unread step `inputs:` key, loop condition | `validator.py` |
| Which references a pass checks, and how (the operand classifier) | `operands.py` |
| Where templates live in the IR (params, `batch.items`, loop, carry, outputs, cache) | `core/workflow/template_surfaces.py` |
| Missing node output/path, diagnostic field suggestions | `path_validation.py` |
| Parameter type, code-input annotation | `type_validation.py` |
| `${item.field}` against inferred item structure | `batch_item_validation.py` |
| Type inference (compatibility: `core/templates.py::is_type_compatible`) | `type_checker.py` |
| A declared `string` into a container param/annotation | `type_validation.py::_declared_text_into_container` (Passes 6, 9) |
| Index into declared structure, dotted display, safe display | `utils.py::descend_index`, `dotted_parts`, `sanitize_for_display` |
| Output metadata or child workflow output discovery | `validator.py::extract_node_outputs`, `_resolve_child_workflow_outputs` |
| Paths shown by node-output formatters | `utils.py::flatten_output_structure` |

Malformed syntax returns early before semantic template checks. Unknown node
types are deliberately skipped by `_register_node_outputs_from_registry`:
the outer workflow validator owns their diagnostic. Raising here replaces a
useful unknown-type error with a validator exception.

## One enumeration, one Issue pass, one classifier

- The Issue pass, the operand classifier and data flow walk
  `iter_template_surfaces`; a new template-bearing location is added there, never
  as another walk. Passes 6 and 9 (below) and the graph's edge emitter
  (`core/workflow/graph/build.py`, via `template_params`) read params themselves
  and ask `param_mode` — inspect them too.
- `_validate_malformed_templates` is the ONE Issue pass: an Issue (an unescaped
  `${` that opens no Expression) is an ERROR on every surface, cache prose
  included. Any future tolerance (which Issues are errors on which surface) is
  decided there only; `parse()` has no mode. It also owns JSON-insert placement:
  a `${x|json}` outside embedded code (output sources included) is an ERROR
  naming where `|json` is allowed; in embedded code, an insert the view cannot
  see (inside `$${…}` or another `${…}` — `templates.hidden_inserts`) or a
  near-miss spelling (`near_miss_insert`) is an ERROR.
- `operands.iter_template_operands` yields every Reference in params,
  `batch.items` and loop fields, a dynamic index's inner refs included, tagged
  `FIELD_CHECK` or `ROOT_ONLY`. Pass 5 and Pass 8 field-check `FIELD_CHECK`
  only (a `??` operand may miss its field at runtime and fall through); Pass 8 also
  filters by node id, since batch nodes may share an alias. `ROOT_ONLY` roots
  are checked by `core/workflow/data_flow.py`, over the same surfaces.
- Output sources: `operands.iter_output_source_operands` parses each as the
  runtime resolves it (`output_resolver.normalize_output_source` — a bare `n.x`
  is `${n.x}`). Their roots are `WorkflowValidator._validate_output_sources`'s;
  Pass 5 field-checks their `FIELD_CHECK` node-output paths only (a whole-node
  `n` source is legal), and all of them count toward unused inputs.
- A carry value's own reference and cache vars have their own passes (one
  diagnostic per mistake). What counts an input as used — every surface, cache vars
  and output sources included — is `core/workflow/data_flow.py::template_reads`, the
  one answer for unused-input accounting. A carry may only reference the loop
  node itself, but its dynamic-index sources (`${s.lst[${i}]}`) are ordinary reads:
  `iter_template_operands` and data_flow check them (`Reference.index_sources`).
  Feeding cache vars to path validation produces two diagnostics for one mistake.
- Literal operands are not references. `TemplateResolver.is_literal_operand`
  is a coarse first-character check for already-parsed operands, not a
  literal validator.

Type and code-annotation passes (6, 9) read params independently through
`TemplateResolver.extract_variables` — Pass 6 over `template_params`, so a code
body never reaches it, and it skips embedded code (always text); they do not
consume the operand iterator. When adding a
template-bearing location, inspect those passes too.

A code body (`template_surfaces.param_mode` → `"body"`) is not a surface: no pass
here reads it. Leftover `${…}` and `$${` in a body are `core/workflow/data_flow.py`'s
("Code bodies"); their in-scope roots count as used (`template_reads`).

Embedded code (`"embedded"`) is a surface whose `templates()` yields the
`embedded_code` view, so every pass above sees only its JSON inserts. Bare pflow
names and quoted inserts in it are reported by `core/workflow/data_flow.py`
("Embedded code"), not here — the compiler runs data flow, so a child chosen at run
time gets them too. Here the bare roots only count as used, so an input used only
bare gets data flow's ERROR naming `|json` instead of the unused-input error.

## Output metadata and limits

`extract_node_outputs` builds the metadata consumed by the passes.
Read it for the shape rather than introducing a second metadata recipe.
`is_batch_output` controls batch path behavior; `is_batch_item` and
`is_inputs_context` record provenance, not pass-selection logic.

Batch `results` contains successes only. In continue mode, path validation blocks
positional indexing into it because positions no longer identify original items.
Child workflow outputs are resolved separately at validation time.

User parameters allow deep access without validating their runtime structure;
known node output structures receive traversal checks. Do not turn this into a
promise that all runtime paths have been validated.

## Diagnostic producers

Construct `Diagnostic` at detection sites, retaining the structured path,
suggestions, and available fields. Rendering belongs to `core/diagnostic_render.py`.

| Context key | Purpose |
|---|---|
| `category` | Validation/template-error title selection |
| `path` | Authoring location, e.g. `nodes[id=X].params.field` |
| `node_type` | Node type context |
| `similar_names` | Suggested matches; producer limits to five |
| `available_fields`, `available_fields_total` | Available values and full count |
| `available_fields_label` | Explicit noun such as outputs/inputs; omission becomes generic “fields” |
| `template` | Reference carried to structured consumers |
| `input`, `declared_type` | The declared workflow input a rule is about, and its canonical type (shared with the input boundary and Task 112) |
| `received`, `source`, `accepted` | Input-boundary errors only (`InputTypeError`): the value as shown (masked, cut at 80), where it entered, the accepted spelling |

Do not populate keys that trigger another subsystem's blocks: compiler `phase`,
runtime `exception_type`, HTTP `raw_response`, MCP `mcp_error`, parser `line`, or
shell `shell_command`/`shell_stdout`/`shell_stderr`. The shell block checks key
presence: even `shell_command=None` triggers it.

Ordinary WARNING/INFO output is compact, but context is **not universally ignored**.
`_format_warning_or_info_diagnostic` renders template-error warnings with
`unresolved_references` structurally and cache warnings from selected context.
Check that dispatch before relying on a context field to appear in text; do not
flatten rich template diagnostics into canned message/suggestion strings.

## Views over one parse, paths, and type boundaries

`core/templates.py::parse()` is the one tokenizer; every check here is a view
over it. Root, forward-reference and unused-input accounting read the dependency
view; type passes read the value view (`core/CLAUDE.md` → **Template language**).

Paths are walked as `parse_path` segments, never `str.split('.')` (dots inside
a dynamic index are not separators). An index — `[N]` or `[${…}]` — descends
by `utils.descend_index` in both Pass 5 and `infer_template_type`: batch
`items` or a list field's `structure` is the element; `any` indexes to an
unknown element; a string indexes only as a JSON array at runtime (WARNING).

Type compatibility is `core/templates.is_type_compatible` (template flow, not a
literal-value check): string → dict/list is allowed because runtime parses JSON
containers, string → numeric/bool is not; a source union needs every member to
fit, a target union any. Parameterized collections compare outer types only.

**A declared input is never re-parsed** (ADR-0017). The certain misses that rule
creates (a path on a scalar, a non-`array` `batch.items`, …) and the input-vs-batch-alias
rule are NOT here: they live in `core/workflow/declared_inputs.py`, run by
`validate_data_flow`, because the compiler must enforce them too (a child chosen at run
time is only compiled, and those misses are silent at run time). This package's one rule
is the container check (Passes 6, 9): keyed on the reference's ROOT through
`declared_inputs.declared_root`, never on the matrix (whose `string` row is shared
with code `result: str` and child outputs, which ARE parsed).
