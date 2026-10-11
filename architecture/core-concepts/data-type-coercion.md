# Data Type Coercion in pflow

How pflow handles JSON parsing and type conversion as data flows between nodes.

## Navigation

**Related Documents:**
- **Templates**: [Template Variables](../reference/template-variables.md) — syntax, resolution, validation
- **Shared Store**: [Shared Store Pattern](./shared-store.md) — how nodes communicate
- **Node Design**: [Simple Nodes](../features/simple-nodes.md) — node architecture
- **Implementation**: `src/pflow/core/json_utils.py` — shared parsing utility

---

## Overview

### The Problem

Nodes produce different output types. Shell nodes write stdout as strings. HTTP nodes may return parsed JSON. LLM nodes return text. But downstream consumers often need a different type — a dict to access fields, a list to iterate over, a string to embed in a prompt.

### The Design Philosophy

> **Producers store raw values. Consumers declare types. The system bridges the gap.**

This follows the same pattern used by every well-designed LLM orchestration system:

- **LangChain**: Output parsers are explicit, separate components attached to chains
- **Vercel AI SDK**: Structured output declared via `output` schema property on `generateText()`
- **n8n**: Separate "Output Parser" nodes sit between LLM and downstream nodes
- **pflow's LiteLLM adapter**: `AdapterResponse.text` carries raw text unless an `output_schema` explicitly asks pflow to parse it

None of these systems speculatively parse output. Parsing is always driven by an **intent signal** — the consumer declaring what it needs, or the user explicitly requesting structured access.

---

## Design Principles

### 1. Producers store what they produce

Nodes write their natural output type. Shell nodes store stdout (string). LLM nodes store the response (string). HTTP nodes store the body. No node should speculatively parse its own output "in case" a downstream consumer needs it differently.

### 2. Parsing requires an intent signal

The system only converts types when something signals that conversion is needed:

| Intent Signal | Example | Who signals? |
|--------------|---------|-------------|
| Dot notation in template | `${node.stdout.field}` | Workflow author |
| Target node declares type | Interface says `param: dict` | Node developer |
| Batch items declaration | `items: ${node.output}` | Workflow author |
| Inline structured object | `{"data": "${node.stdout}"}` | Workflow author |
| Declared workflow input type | `## Inputs` `- type: object` | Workflow author |

### 3. Guards prevent false positives

Every auto-parse point has safety guards:
- **Container-only**: Only parse to `dict`/`list`, never to primitives (prevents numeric string coercion like Discord snowflake IDs)
- **Size limit**: 10MB max via `json_utils.py`
- **First-char check**: Quick rejection if string doesn't start with `{`, `[`, `"`, etc.
- **Simple template only**: Complex templates like `"prefix ${var}"` always stay as strings

### 4. Display-layer parsing is read-only

Parsing at the CLI output boundary (for pretty-printing) never affects data flow. It's purely presentational.

---

## Complete Auto-Parse Inventory

Every location in pflow where automatic JSON parsing or type coercion occurs. A value's type is decided once, where it
enters, by the declared type of what receives it; nothing downstream re-infers it (ADR-0017).

### Point 0: The Workflow Input Boundary (DECLARED)

**Location**: `src/pflow/core/param_coercion.py` — `coerce_declared_input()`, called by
`runtime/compilation/ir_preparation.py::prepare_inputs` (root workflow; `check_supplied_inputs` for `--validate-only`
with values and cache analysis) and `runtime/workflow_executor.py::type_child_inputs` (a sub-workflow, per call and per
batch item).

**When it fires**: Once per workflow input, whatever the source — CLI argument, stdin, environment, settings.env,
`default:`, MCP call, a parent workflow's `inputs:`, a resumed run's recorded value.

**Intent signal**: The `## Inputs` `type:`. Text reads through the strict grammar `TypeSpec.parse_text`
(`core/types.py`); a typed value must satisfy `TypeSpec.accepts`, except that a `string` takes any scalar as
`to_string` renders it. `any`/untyped: a CLI argument is inferred losslessly (typed only when it reads back as the same
compact JSON); every other source is kept as given. The CLI parser (`cli/param_parsing.parse_workflow_params`) infers
nothing.

**Guards**: A value that does not fit raises `InputTypeError` (a Diagnostic naming the source) — never a warning.

### Point 1: Template Traversal

**Location**: `src/pflow/core/templates.py` — `_json_container()` (called by the path walk `_walk` / `_step`)

**When it fires**: User writes `${node.stdout.field}` — dot notation on a string value.

**Intent signal**: The dot notation is an explicit declaration: "I want to access a field inside this value." If the
value is a string, the system tries to parse it as JSON to enable traversal.

**Guards**: Only parses to `dict`/`list`. Primitives (int, float, bool) are never parsed — preserves numeric strings.
Never under a reference whose root is a declared non-`any` workflow input (root-wide: a JSON-text descendant of an
`object` input stays text; `unparsed_declared_text` names it in the miss).

**Example**:
```
# Shell node outputs: shared["stdout"] = '{"items": [1,2,3], "count": 3}'
# Template: ${shell-node.stdout.count}
# Result: 3 (parsed on demand, original string untouched)
```

### Point 2: The `auto_parse` Leaf

**Location**: `src/pflow/core/templates.py` — `_resolve_simple()` under `resolve(..., auto_parse=True)`; the caller
decides `auto_parse` per consumer in `src/pflow/runtime/engine/template_resolution.py::resolve_templates` and
`runtime/engine/batch_executor.py::resolve_batch_items`.

**When it fires**: A simple template (`${var}` as the entire value) resolves to JSON object/array text, and the consumer
wants structure: a value in a step's `inputs:` map, a string leaf of a dict/list param, a param whose interface type is
`dict`/`list`, or `batch.items`.

**Intent signal**: The consumer. `parses_leaves` says no for the text consumers in `_CONSUMER_TYPES_LEAVES` (`shell.env`,
`http.headers`, a workflow step's `inputs:` — the child's own boundary, Point 0, types those) and for a code `inputs:`
key whose annotation is `str` (`TemplateConfig.text_input_keys`, read at compile time).

**Guards**: Simple templates only (`"prefix ${var}"` stays a string). Only parses to containers. Never parses a value
whose supplying operand is rooted in a declared non-`any` input (the source-side rule, read from the store key
`DECLARED_INPUT_TYPES_KEY`). A well-formed container of the wrong shape for its param is an error, not a pass-through.

**Why it exists**: Without this, `{"body": "${shell.stdout}"}` where stdout is `'{"key":"value"}'` would produce
`{"body": '{"key":"value"}'}` — double-encoded.

### Point 3: Serialize for a `str` Param

**Location**: `src/pflow/core/param_coercion.py::coerce_param_for_node` (called by `resolve_templates` and
`split_params`)

**When it fires**: A resolved `dict`/`list` reaches a param whose node interface declares `str`.

**Guards**: Only that direction; every other value passes through.

### Point 4: Display Layer

**Location**: `src/pflow/execution/formatters/success_formatter.py` (`parse_json_or_original`)

**When it fires**: At the output boundary, when displaying workflow results. An explicit `-o <path>` into a declared
input is not re-parsed (`TemplateResolver.reads_declared_input`).

**Impact**: Read-only. Never affects the shared store or downstream nodes.

### Point 5: LLM Node JSON Auto-Parsing (REMOVED)

**Location**: `src/pflow/nodes/llm/llm.py` — `_strip_code_block()` (replaces removed `parse_json_response`)

**What was removed**: The `parse_json_response` method that speculatively attempted `json.loads()` on every LLM
response. It caused a data-loss bug where prose responses containing JSON code blocks had the prose discarded.

**What remains**: `_strip_code_block()` strips markdown code block fences when the entire response is a single code
block. The return value is always a string.

---

## How They Interact

```
Workflow input (any source)
    │
    └── Point 0: typed once by its declared type — or InputTypeError
    │
    ▼
Shared store ──── step outputs stored raw
    │
    ▼
Template resolution (resolve_templates / resolve_batch_items)
    │
    ├── Root is a declared non-`any` input?  → value as typed; never parsed (Points 1 and 2 skip it)
    ├── Dot notation ${node.stdout.field}?    → Point 1: parse on demand for traversal
    ├── Simple ${var} into a structured consumer that parses? → Point 2
    └── Otherwise: value as-is
    │
    ▼
Point 3: dict/list into a `str` param → JSON text
    │
    ▼
Node input ... (node executes) ...
    │
    ▼
Point 4: output display (read-only)
```

---

## Shared Infrastructure: json_utils.py

The parse points use the shared utility at `src/pflow/core/json_utils.py`:

### `try_parse_json(value) -> tuple[bool, Any]`

Two-value return pattern distinguishing three cases:
- `(True, {"key": "value"})` — parsed successfully to dict
- `(True, None)` — parsed successfully to JSON null
- `(False, "original string")` — parse failed, original returned

### `parse_json_or_original(value) -> Any`

Convenience wrapper for when you don't need to distinguish success from failure. Used by the display layer.

### Performance Guards

- **First-char check**: Rejects strings not starting with `{`, `[`, `"`, `t`, `f`, `n`, `-`, or digit
- **Size limit**: 10MB default (configurable), prevents memory exhaustion
- **Empty string rejection**: Returns immediately

---

## Known Limitations & Tech Debt

1. **The `auto_parse` leaf (Point 2)** has no schema signal from most consumers. Could surprise users if `${shell.stdout}` happens to be valid JSON but they wanted the raw string in an inline object. Mitigated by the container-only guard, the text consumers in `_CONSUMER_TYPES_LEAVES`, and a code input annotated `str`.

2. **No caching of parsed JSON**. The same string may be parsed multiple times if referenced in multiple templates. Acceptable for MVP (parsing is <1ms vs node execution 100-1000ms). Consider caching if profiling shows this as a bottleneck.

3. **LLM node fix complete**. `parse_json_response` was removed and replaced with `_strip_code_block()` (code fence stripping only, no JSON parsing). See `scratchpads/json-parse-bug/bug-report.md` for the original bug analysis.

4. **Task 66 (Structured Output)** will add explicit schema-driven JSON parsing for LLM nodes. This is the proper solution for "I want guaranteed JSON from an LLM" — declaring a schema, not hoping the heuristic works.

---

## See Also

- [Template Variables Reference](../reference/template-variables.md) — full template syntax and resolution rules
- [Shared Store Pattern](./shared-store.md) — how nodes communicate through the shared store
- `src/pflow/core/json_utils.py` — shared JSON parsing utility (source of truth for parsing logic)
- `src/pflow/runtime/CLAUDE.md` — runtime module documentation (engine and template resolution)
- `scratchpads/json-parse-bug/bug-report.md` — the bug that prompted this documentation
