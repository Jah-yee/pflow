# Task 181 — implementation plan

**Goal.** In code handed to MCP tools, a bare `${…}` is the embedded language, and a pflow value
enters only as `${x|json}`.

- **Spec:** `../task-181.md`.
- **Contract:** `context/adr/0016-118-code-bodies-untemplated-env-binding.md`.
- **Upstream contract-to-be:** Task 118's plan (branch `feat/task-118-shell-env-binding`).
- **Planner:** task-planner (Opus by user ruling), 2026-10-06, on `ebf7cab2`.
- **Line numbers** were read on `ebf7cab2`. **Re-verify before editing**: Task 118 rewrites several
  of the same files first.

**Read with this plan:** `diagnostics-checkpoint.md` in the same folder. It lists every new or
changed message, with the BEFORE executed and the AFTER drafted (revised after the plan battery),
and poses rulings R1–R6 and R8. **It is an embedded user checkpoint: the build does not start until
it is ruled** (CP-1, §7).

**Shape.**
- **One PR.**
- **Engine contact** in phase PC (`runtime/engine/template_resolution.py`). That makes this lane A,
  serialized behind Task 118, with a mid-task review after PC.
- **Grammar change** in `core/templates.py`, with the TypeScript mirror `web/src/graph/scan.ts`
  changed in the same phase (PA).
- **No trace-format change** (D12).
- **Not platform-sensitive.** There is no subprocess, path or encoding code. `tests-windows` runs as
  usual.

---

## 0. Build gate: Task 118 Part 2 must be merged first

This plan reuses Task 118's classification and does not reshape it. Task 118 ships in two PRs (its
plan §4.0):
- **Part 1** adds only `binds_as_text` and `TemplateConfig.node_type`.
- **Part 2** adds `ParamMode` / `param_mode`, `template_params(node)`, `split_params(…, node_type)`,
  the per-step scope rule of its leftover check (D5 step 1), the unused-input coupling ("one
  mistake, one diagnostic"), and the web `isCodeBody`.

Part 2 is held until the user rules on a release. **181 builds after Part 2 merges.**

**Fallback if 181 has to build earlier.** 181 introduces `ParamMode = Literal["template",
"embedded"]`, `param_mode`, `split_params(…, node_type)` and the step-scope helper, in exactly the
shapes 118's D1/D5 specify (minus `"body"`), and 118 Part 2 rebases onto them. That is a cross-task
ordering call for the main orchestrator, not this plan.

**Re-verify at build (P0).** Each is a named check. A mismatch is a hand-back, not an adaptation:
1. `param_mode(node_type: str | None, key: str) -> ParamMode` exists in
   `core/workflow/template_surfaces.py`. It is a function, not a table looked up at call sites, and
   its callers compare `== "body"` (118 D1).
2. `TemplateConfig.node_type` exists and the compiler fills it (118 D2).
3. `split_params(params, expected_types, node_type)` exists and consults `param_mode` before
   `has_templates` (118 PB).
4. The step-scope rule of 118 D5 step 1 lives in **one named helper**. Log its name.
   - 118's `body_references` is shell/code-specific (Issues with an in-scope leading name, `$${` →
     ERROR, the Python AST), so it is **not** reused whole. Only the scope rule is reused (D6).
   - The main orchestrator is asked to have 118 deliver the helper by name (hand-back).
5. The unused-input pass has 118's "add these roots to used" hook (`runtime/template_validation/validator.py`
   `_validate_unused_inputs` and its caller). Log where it lives.
6. `web/src/utils/format.ts::isCodeBody(kind, name)` exists. Log where it is called (118 PE).

**Conflict stop condition (from the launch packet).** If 118's classification cannot take a third
mode without reshaping its callers, STOP and hand back with the evidence. On the plan as read, it
can: `"embedded"` is a third answer on the same axis (how pflow reads a param's `${…}`), and every
118 caller that asks `== "body"` correctly treats an embedded param as not a body.

---

## 1. The mechanism in one paragraph

The one parser learns one suffix: `${x|json}` (also after a Coalesce or a Dynamic index) parses as
an `Expression` with `as_json=True`. Its value enters text as a JSON literal (`templates.to_json`)
and is never type-preserving. Task 118's `param_mode(node_type, key)` gains a third answer,
`"embedded"`, for four JavaScript params of MCP tools, matched by tool-name suffix (D2). For an
embedded param every reader uses one policy view of the same parse,
`templates.embedded_code(template)`: only the `as_json` Expressions stay Expressions, and every
other span (a bare `${…}`, an Issue, a `$${`) becomes Text **cut verbatim from the source** (D3).
- The **validator** gets the view through `TemplateSurface.templates()`.
- The **runtime** gets it through `resolve(…, embedded=True)` and `has_templates(…, embedded=True)`.
- The **graph** gets it through `refs_with_path_in(…, embedded=…)`.
- The **web** reads `param.mode`.

On every other surface an `as_json` Expression behaves like an Issue: a validation ERROR that names
where `|json` is allowed, and kept verbatim at run time (D4). Inserts the view cannot see (inside
`$${…}` or a JavaScript `${…}`) and near-miss spellings are validation ERRORs (D5). A pflow name
written bare inside embedded code is an ERROR when it is a workflow input used nowhere else (in
place of the unused-input error), and a WARNING otherwise; an insert left inside quotes warns (D6).

---

## 2. Investigation record

How to read the markers:
- **(verified)** — read at file:line or executed by the planner on `ebf7cab2`.
- **(S)** — a `pflow-codebase-searcher` or review-lens citation whose reasoning the planner checked
  but did not re-read.

### 2.1 The parse and its consumers

**Grammar locations** in `core/templates.py` (verified):
- the grammar: `:152-182`;
- `_EXPRESSION_AT` `:175`;
- `_SCAN` `:182` (the escape alternative comes first; brace-balanced, one nesting level);
- `Expression` `:255-264`, `Template` `:279-310`, `is_simple` `:297-306`;
- `_resolve_string` `:586-618`, `to_string` `:621-647`;
- `TEMPLATE_PATTERN` `:682` (group 1 = the expression), `SIMPLE_TEMPLATE_PATTERN` `:683`;
- `has_templates` `:693-698` (an uncached `_tokenize`; it may run on resolved values).

**`Expression.raw` must include `|json`** (S):
- `tests/test_core/test_template_grammar.py:244-245` asserts `source[span] == "${" + raw + "}"`.
- `markdown_parser.py:1774-1775` asserts the `## Cache` chunk name equals `raw`.
- `template_errors.py:140` searches the template for `"${" + raw + "}"`.
- `execution/plan.py:1592` prints `${raw}`.

`classify_unresolved_references` (`:162`) re-parses `${raw}` and gets the same Expression back.

**What prints operand text without the suffix (the D7 fix)** (S): diagnostics that rebuild `${…}`
from **operand** text (`Reference.raw`, which never carries the suffix).
- `template_errors.py:197` (`var`), `:178` (`coalesce_expr` — rendered mid-chain as
  `${a ?? b|json ?? peer.f}`, which is invalid grammar).
- `diagnostic_render.py:467, 529, 542-551, 579`.
- `data_flow.py:344` (did-you-mean).
- `path_validation.py:467-474`.

Pasting any of these fixes into embedded code produces bare JavaScript.

**`is_simple` consumers** (S): `template_resolution.py:269`, `loop_control.py:132`,
`engine.py:152`, `output_resolver.py:40,90`, `data_flow.py:615`,
`template_validation/validator.py:250,394,523`, `type_validation.py:329,627`. A JSON insert is never
simple (D1), which every one of these handles. If it were simple, the engine's container auto-parse
(`template_resolution.py:272-277`) would turn the JSON text back into a dict.

**`Template.escaped`** (S): read only at `templates.py:310` and `test_templates.py:98,109`. It is
**unchanged by this plan** (D5 does not need escape spans).

**Lexical `TEMPLATE_PATTERN` users** (S): `prompt_refs.py:61-63,133-137`,
`token_estimation.py:464-488`, `trace_loading.py:559-564`, `discrepancy/predict.py:374-379`. They
split group 1 on `??` and take the root lexically. All but `predict.py` read LLM text. A
non-capturing suffix keeps their group 1 a clean expression.

`trace_report.py:523-536` uses the loose `TEMPLATE_EXTRACT_PATTERN` (S). It would report "key
`missing|json` not found" for an unresolved insert, so PC switches it to `parse()` operands.

**Grammar meta-tests:**
- Rules A and B of `tests/test_core/test_template_grammar_seam.py` (no `${` regex outside
  `core/templates`).
- The reassembly and every-`${`-covered invariants (`test_template_grammar.py:219-247`; counts
  `covered == 82`, `len(GRAMMAR_ROWS) == 76`).
- The fuzz set (`test_templates.py:193-204`, `14*14 + 40`).

New rows change those counts.

### 2.2 Who reads a param's `${…}`

| Reader | How | Sees `templates()`? |
|---|---|---|
| Issue pass `_validate_malformed_templates` (`runtime/template_validation/validator.py:615-637`, messages `:640-674`). **Returns early** (`:82-92`) and logs "Found N malformed template(s)" | `templates()` → `.issues` | yes |
| data flow `_validate_node_params` (`core/workflow/data_flow.py:789-822`). Also run by the compiler (`compile_validation.py:132`, keeps ERRORs only) | `templates()` → `.references` | yes |
| operands → Pass 5, Pass 8, unused inputs (`operands.py:50-74`; `validator.py:95-126, 555-612`) | `templates()` → `.expressions` | yes |
| path_validation source-file hint (`:384-390`) | `templates()` | yes |
| Pass 6 (`type_validation.py:60-150`) | raw `has_templates` + `extract_variables` | **no** — D8 skips embedded params |
| graph edges: `build.py:586` → `_add_ref_edges` (`:511-555`, extractor at `:532`) → `scope.refs_with_path_in` (`scope.py:22-36`); `_params_strings` yields the nearest dict key (`:852-881`) | raw parse | **no** — D8 |
| canvas `react_flow._param` / `_param_is_dynamic` (`:306-313`, `:473-483`) | raw parse | **no** — D8 |
| `web/src/graph/scan.ts::paramTextReads` (`:129-150`) and the three web regex readers | own tokenizer | **no** — D10 |
| runtime `split_params` / `resolve_templates` (`template_resolution.py:89-120, 215-393`) | raw | **no** — D9 |
| MCP `registry_run` (`mcp_server/services/execution_service.py:731-736`): `expand_env_vars_nested(…, raise_on_missing=True)` over all params | env-var regex | **no** — D9 |
| `predict.py:362-380` `_node_templates_touch` | regex | LLM-only effect; unchanged |
| `pflow mcp describe` usage snippet (`cli/commands/mcp.py:1002`) and the agent context (`registry/context_builder.py:683`) | emit `- function: ${previous-step.response}` — teaches the bare form | PE |

Runtime facts (S):
- `MCPNode` does no template work (`nodes/mcp/node.py:178-201`).
- File loading covers only `FILE_RESOLVABLE_PARAMS` (`core/file_resolver.py:38-46`).
  `browser_run_code_unsafe.code` can be file-loaded (`- code: ./x.js`) and the embedded rule then
  applies to the loaded text; `function` and `initScript` cannot.
- `--validate-only`, the run, MCP `workflow_validate`/`workflow_execute`, save and dry-run all call
  the full `WorkflowValidator` first. The web `/api/run` preflight is compile-only and then spawns
  `pflow run`. A dynamic child (`workflow: ${path}`) gets only `validate_ir` + `compile_workflow`
  (`workflow_executor.py:284-310`).
- Batch per-item resolution for a non-workflow node goes through the engine's `_execute_single_node`
  (`engine.py:1745-1760`). `batch_executor.py:219` is the sub-workflow pre-warm and returns early
  for MCP nodes.
- A standard dry-run step resolves at `plan_node.py:144`. `PlanEntry` carries no params, so dry-run
  never prints resolved values.

### 2.3 The MCP side

- **Type string.** It is `mcp-{server}-{tool}` (`mcp/registrar.py:121`), and neither part is
  normalized. Server names may contain `-`. A JS `function` param registers as `str`
  (`mcp/discovery.py:322, 342-371`) (S).
- **Code-bearing params in this machine's registry** (executed against `~/.pflow/registry.json`):
  `evaluate_script.function` and `navigate_page.initScript` (chrome-devtools,
  chrome-devtools-isolated); `browser_evaluate.function` and `browser_run_code_unsafe.code`
  (playwright, playwright-isolated). `mcp-neon-run_sql.sql` exists too. It is SQL, so it is outside
  the JavaScript criterion (D2).
- **In-tree sites: exactly four** (verified). They are `click.pflow.md:83-85` and `hover.pflow.md:56`
  in `examples/real-workflows/screenshot-pflow-web-ui/`, plus the caveats at `click.pflow.md:17-18`
  and `.claude/skills/screenshot-pflow-web-ui/SKILL.md:34-35`. The other five workflows there hold
  no `$` in their JavaScript. These examples are excluded from
  `tests/test_docs/test_example_validation.py` (`:15-21`, `65-66`).

### 2.4 The web

- `RFNode.kind` is the raw IR type string (`build.py:103` → `react_flow.py:240` → `types.ts:218`).
  `RFParam` is `{name, value, is_dynamic, source}` (`react_flow.py:53-57`, `types.ts:158-165`) (S).
- `scan.ts`: grammar copies at `:57-67`; a private `templateRefs` at `:89-108` (refs only, no
  segments); `paramTextReads` at `:129-150`, which is kind-blind (S).
- `$$`-blind readers (#683):
  - `utils/format.ts:9` `parseTemplate`. Its callers: `WorkflowNode.tsx:117-137` chips;
    `CodeBlock.tsx:46,61,83-100` teal (on when `lang` is null — every MCP param); `highlight.ts:91-123`;
    and `refMatchesHighlight` (`:34-39`, which splits raw text on `??`).
  - `graph/sourceDecorate.ts:32` (both tiers).
  - `utils/batchItems.ts:26`, called via `ReadPanel.tsx:74`.
- The per-item preview blocks are `ReadPanel.tsx:115-119` and `BatchItems.tsx:47`, plus
  `ExpandableBox`'s modal. They render substituted text in a `CodeBlock` with `lang = null`, so the
  teal is on (S).
- `format.ts:4` already exports `interface TemplateSegment {text, isRef}` (S). The new TS type takes
  a different name (D10).
- `web/CLAUDE.md:42-43`: "Python owns graph facts; TS owns visual policy" (S).

### 2.5 Baselines (executed on `ebf7cab2`)

The BEFORE captures of every message are in `diagnostics-checkpoint.md` (probes `p1`–`p12`). P0
records `make test`, `verify.sh` and `capture.py --check`, by name.

### 2.6 Cross-task scan (`./scripts/tasks`, 2026-10-06)

- **Task 118** (pending, builds first): the substrate (§0).
- **Task 170** (done): one parser, one surface list, two channels, grammar only in `core/templates`
  with `scan.ts` changed in the same step. Invariants 1–8 of its task-review hold.
  - Invariant 1 holds for `parse()`; `embedded_code()` is a policy view and is documented as one.
  - Invariant 3 holds: `has_templates(embedded=True)` stays on `_tokenize`.
- **Task 120** (pending): disjoint code. But `|json` is the first rendering that shows a value's type
  exactly, so 120's typing rulings change what an insert emits. That goes in the task-review note.
- **Task 167** (later, LSP): the view keeps source and spans; nothing to do.
- **Task 182** (then): ruff/shellcheck only; no JavaScript.
- **Task 178** (then, MCP SDK 2.x): disjoint files.
- **Task 152** (then): renames `registry_run` → `probe`. D9's skip is independent of the name.
- **Issue #683** (open): closed by PD (D10).

### 2.7 Spec corrections on this branch

The spec's open questions now carry a "Resolved at planning" block pointing here. The build
dependency is narrowed to Task 118 **Part 2**.

---

## 3. Decisions

Governing lens, applied at each fork: *"prioritize simplicity of the FINAL code… the right
solution the top 10% of codebases similar to this one would implement… more simple code that is
optimized for AI agents to understand and add features to."*

### D1 — Grammar: one optional suffix on the Expression; `raw` includes it; never simple

`core/templates.py`:

```python
_JSON_INSERT = r"\s*\|\s*json"   # `${x|json}`, `${a ?? "d" | json}` — spaces like `??` (R5)
_EXPRESSION_AT = re.compile(rf"\$\{{({_EXPRESSION})({_JSON_INSERT})?\}}")

@dataclass(frozen=True, slots=True)
class Expression:
    operands: tuple[Operand, ...]
    raw: str                    # the text inside `${…}`, `|json` included
    span: tuple[int, int]
    as_json: bool = False       # a JSON insert: the value enters text as a JSON literal
```

**How the match is read.**
- `_expression_at` splits operands from group 1. `raw` is group 1 plus group 2 (or ""), and
  `as_json` is true when group 2 matched.
- The suffix applies to the **whole** expression:
  - `${a ?? "x"|json}` gives the JSON of the first operand that resolves.
  - `${a[${i}].b|json}` works. `|json` inside `[…]` stays an Issue.
  - `${a ?? "x|json"}` is a literal, not an insert.
  - `${x|json }` and `${ x|json}` are Issues, like `${ x }`. D5 catches them in embedded code.

**Resolution behaviour.**
- `Template.is_simple` is `False` when its sole Expression has `as_json`.
- `to_json(value) -> str` sits beside `to_string`. It is `json.dumps(value, ensure_ascii=False)`;
  on `TypeError`/`ValueError` it falls back to `json.dumps(to_string(value), ensure_ascii=False)`
  (R6). Text is never re-parsed.

**Patterns.**
- `TemplateResolver.TEMPLATE_PATTERN` gains the suffix **non-capturing**, so group 1 stays the
  expression.
- `SIMPLE_TEMPLATE_PATTERN` does not gain it.
- `TEMPLATE_EXTRACT_PATTERN` is unchanged.

**Rejected alternatives.**
- **A general filter position `|<name>`.** On embedded code `${flags|mask}` is legal JavaScript (a
  bitwise or). Each word pflow claims is reserved inside JavaScript, so a second insert word later
  silently changes existing JavaScript. The exact word is the door kept narrow. The hand-back
  proposes recording this in ADR-0016.
- **`raw` without the suffix.** It breaks the reassembly invariant and the consumers in §2.1.

### D2 — The classification: `param_mode` answers `"embedded"` for four JavaScript params

`core/workflow/template_surfaces.py` (118's function, plus one mode and one table):

```python
ParamMode = typing.Literal["template", "body", "embedded"]

# (tool, param) of MCP tools whose param is JavaScript another process runs. JavaScript only:
# a JSON insert is a JavaScript literal (SQL/Python params need their own rule). Matched on the
# tool-name suffix of `mcp-<server>-<tool>` because the server name is user-chosen; a JavaScript
# tool missing here stays a Template (safe), a same-named non-JS tool is read as embedded code (the
# bare-reference check reports it).
_EMBEDDED_CODE: frozenset[tuple[str, str]] = frozenset({
    ("evaluate_script", "function"),
    ("navigate_page", "initScript"),
    ("browser_evaluate", "function"),
    ("browser_run_code_unsafe", "code"),
})
```

`param_mode` returns `"embedded"` when `node_type` starts with `"mcp-"` and ends with `f"-{tool}"`
for some `(tool, key)` in the table. Its docstring is the one home of the three mode definitions.
Table membership is ruling **R1**.

**Callers compare modes, not booleans** (`== "body"`, `== "embedded"`). In `core/workflow` and
above, the mode is carried as a `ParamMode`. Only `core/templates.py` takes a bool `embedded`,
because it cannot import from `core/workflow` (layering).

**Rejected alternatives.**
- **A schema heuristic.** It switches typo detection off on params that are not code.
- **An author marker.** New workflow grammar for a four-row table.
- **Registry metadata.** The walks see only the IR.

### D3 — One policy view: `embedded_code(template)`

```python
def embedded_code(template: Template) -> Template:
    """How embedded code reads a parse: only the `${…|json}` Expressions are pflow's.
    Every other span — a bare `${…}`, an Issue, a `$${` — is Text cut verbatim from the
    source (an escape is not collapsed). A policy view: unlike `parse()`, its Text may hold `${`."""
```

**Construction.** It is built from the inserts in `template.expressions` and the source gaps
between their spans, with `escaped=False`. It keeps `template.source`, is linear, and is uncached.
It lives in `core/templates.py` because the validator, runtime and graph all call it.

**Consumers, and only these:**
- **`TemplateSurface`** gains `mode: ParamMode = "template"`, set by `iter_node_surfaces` from
  `param_mode(node.get("type"), key)`. `templates()` yields `embedded_code(parse(text))` when
  `mode == "embedded"`. Every surface consumer marked "yes" in §2.2 inherits the policy with no
  edit.
- **`resolve(value, context, *, auto_parse=False, embedded=False)`.**
  - On a string it uses `embedded_code(parse(value))` when `embedded`.
  - The flag passes down the dict/list recursion.
  - `_resolve_string` takes `embedded` too (D4).
- **`TemplateResolver.has_templates(value, *, embedded=False)`.** It stays on the uncached
  `_tokenize` (it may see resolved values). When `embedded`, it is true iff some string leaf's view
  holds an Expression. So an escape-only or bare-only value is static, and `$${` stays `$${`.
- **`scope.refs_with_path_in(value, *, embedded=False)`** and its aliases (D8).
- **The web mirror** (D10).

### D4 — `|json` outside embedded code: an Issue in all but name (R2)

**At run time.** `_resolve_string(template, context, auto_parse, embedded)` gets one new arm: an
`as_json` Expression with `embedded` off is kept as written and its source text is added to
`Resolution.issues`. Update the `Resolution` docstring (`templates.py:535-541`: "`issues` holds
`Issue.raw` of every Issue" becomes "…and every misplaced JSON insert") and `core/CLAUDE.md` "Two
channels".

**Run-time outcome per surface** (when a workflow skips validation; every CLI, MCP and web entry
validates first). The corpus records the honest outcome; no new engine branch is planned:

| Surface | Outcome | Corpus outcome |
|---|---|---|
| node param | strict failure (the issues path) | `Raises` / `Unresolved` |
| `batch.items` (string) | refuses ("resolved to None…") | `Raises` |
| `batch.items` (inline list) | the literal becomes an item (`resolve_nested`) | `Resolves([...])` — as the existing `batch_items_inline_malformed_element_520` row |
| `loop.while` / `loop.until` | reads as false (non-simple) | `Resolves(False)` — as `loop_while_complex_shape` |
| `loop.max_iterations` | `LoopConditionError` | `Raises` |
| output source | `OutputResolutionError` | `Raises` |
| `## Cache` var | chunk dropped | `Absent()` |

**At validation.** The Issue pass reports the first `as_json` Expression on any surface whose mode
is not `"embedded"`, using checkpoint §5's message. The fix line is the author's text with the
suffix stripped, built from the Expression span and its group-1 text (`raw` minus the suffix). The
list of allowed places is rendered from `_EMBEDDED_CODE`, sorted.

**Output sources.** A bare `x|json` source has no `${`, so `templates()` skips it, but the runtime
wraps it. The Issue pass therefore checks output-source surfaces through
`output_resolver.normalize_output_source`, as `operands.iter_output_source_operands:60-62` already
does. `WorkflowValidator._validate_output_sources` (`core/workflow/validator.py:571-578`) routes its
no-`${` branch through the same normalizer, so a bare `x|json` does not also get "non-existent node
'x|json'" (one mistake, one diagnostic).

**The log line.** `validator.py:88-91`'s log line becomes `Found {n} template error(s)`, because it
now counts placement errors too.

**Rejected.** Honouring `|json` at run time everywhere: a compile-only run would then run what
validation rejects.

### D5 — Inserts the view cannot see, and near-miss spellings (R4)

Both are checked in the Issue pass, on embedded surfaces only. Both are ERRORs, and the early
return makes each the sole error, as checkpoint §7 shows. Two helpers live in `core/templates.py`,
where a regex over the grammar is allowed:

```python
def hidden_inserts(template: Template) -> tuple[tuple[int, int], ...]:
    """Spans of `${…|json}` matches in the source that the parse did not produce as Expressions —
    inserts swallowed by a `$${…}` escape or by an Issue (`${${x|json} + 1}`)."""

def near_miss_insert(issue: Issue) -> str | None:
    """The insert an Issue was probably meant to be: its inner text with the ends trimmed and the
    word after the last `|` lower-cased, if that parses as a JSON insert; else None."""
```

**`hidden_inserts`.** It runs `_EXPRESSION_AT.finditer` over `template.source`, keeps matches with
the suffix group, and drops those whose start equals a visible Expression's span start. A match
inside `$${count|json}` starts one character into the escape, so it is found. No AST change is
needed: `Template.escaped` stays as it is.

**Messages.** The ERROR text for each case is in checkpoint §7a and §7b. On an embedded surface the
pass parses `template.source` (a cache hit) for both helpers, because the view has no Issues.

### D6 — Bare pflow names in embedded code; quoted inserts (R3: "instead of")

**One detector**, `embedded_references(workflow_ir) -> list[EmbeddedReference]`, sits in
`core/workflow/data_flow.py` beside 118's step-scope helper. For every param with
`param_mode(...) == "embedded"`, it parses each string leaf (the raw parse) and yields:
- each Expression **without** `as_json`, any of whose `.references` (the dependency view) has a
  root in the step's scope, as defined by 118's D5 step 1 rule (§0 check 4);
- each `as_json` Expression whose span is immediately wrapped in matching `'…'` or `"…"`.

Each record carries `node_id`, `param`, the reference text, `root`, `root_kind`, `quoted`,
`whole_value` and `replacement`, where `replacement` is the paste-able fix.

**The consumer** is the template validator, beside `_validate_unused_inputs`
(`runtime/template_validation/validator.py:555-612`). It runs in one function after the "used" set
is computed. **Severity is decided per record, in order:**
1. **ERROR (§4a)** for a bare reference whose root is a declared workflow input not otherwise used.
   That input is removed from the generic unused-input report, through 118's "add to used" hook
   (§0 check 5). One ERROR per param, at `nodes[id=X].params.<param>`.
2. **WARNING (§4b/§4c)** for every other bare in-scope reference. One per param; it lists them in
   source order, with one `→` per reference and the closing "your JavaScript variable" line. When
   the param value is exactly one bare reference, the `→` is the `eval` form (R7).
3. **WARNING (§4d)** for a quoted insert.

Context for each: `{"category": "template_error", "path": …, "embedded_references":
[{reference, root_kind, replacement}]}`.

**Why in the template validator, not data flow:** the ERROR needs the used-input set. The
template validator runs on every validating entry. On the compile-only path, a WARNING would be
dropped anyway (`compile_validation.py:132-139`).

**Fix wording** must be correct whether the reference sits inside a JS string or template literal
(checkpoint §4). The fix says "where a JavaScript value goes, outside any quotes or `…`" with a
`const` example. The quote-aware branch fires only when the span is immediately wrapped in matching
quotes.

**Rejected.**
- **"Alongside"** (the draft): its first numbered fix deletes the input, after which the bug is
  silent.
- **Flagging Issues with an in-scope leading name** (118's shell rule): `${count + 1}` is ordinary
  JavaScript.

### D7 — Diagnostics that rebuild `${…}` keep `|json`

When an unresolved or misspelled reference came from an `as_json` Expression, every rebuilt
template and every fix carries the suffix:
- the runtime "Unresolved variables" line;
- did-you-mean, and the `??` suggestion (the suffix goes at the end of the chain, never mid-chain);
- the validator's `data_flow.py:344` and `path_validation.py:467-474`.

**Mechanism.** `classify_unresolved_references` gets the Expression (not only its operands' raw
text) and records `as_json` on each ref. The renderers (`diagnostic_render.py:467, 529, 542-551, 579`)
append `|json` when it is set. The validator sites read `as_json` from the Expression they already
hold.

**Placement.** This touches the engine-adjacent renderer → PC.

### D8 — Graph, canvas and Pass 6: Python decides, the payload carries the mode

**Graph edges.**
- `scope.refs_with_path_in(value, *, embedded=False)` applies `embedded_code` per string leaf.
- `_add_ref_edges` (`build.py:511-555`) takes `embedded` as a keyword. `_add_one_input_consumer_edges`
  (`:586`) passes `param_mode(raw_node.get("type"), key) == "embedded"` per **top-level** param.
  It iterates the params itself and calls `_params_strings` per param, because `_params_strings`
  yields the nearest dict key.
- An insert draws an edge; a bare JS `${…}` draws none.

**Canvas payload.**
- `react_flow.RFParam` gains `mode: ParamMode` (`"template"` default), set by `_param` from
  `param_mode(node.kind, name)`. `_param_is_dynamic(value, mode)` uses the view.
- `types.ts` `RFParam` gains `mode: "template" | "body" | "embedded"` in the same phase.
- Regenerate the contract fixtures with `uv run python -m tests.fixtures.react_flow_contracts._generate`.
- **The web reads `param.mode`**. There is no TS copy of `_EMBEDDED_CODE`. 118's
  `isCodeBody(kind, name)` becomes `param.mode === "body"` at its call sites and is deleted.

**Pass 6** (`type_validation.py:76-114`) skips params whose mode is `"embedded"`, with a one-line
reason: an embedded param's value is always text, so an insert's source type is irrelevant. This
honours ADR-0016's "every param walk consults the classification" rather than relying on the
`str`-accepts-everything matrix row.

**`core/workflow/graph/CLAUDE.md:53-54`** ("Scope extraction must match runtime grammar and skip
escaped templates") gains "and an embedded param's view".

### D9 — Runtime (engine contact)

`runtime/engine/template_resolution.py`:
- **`split_params(params, expected_types, node_type)`.** After 118's body check, an `"embedded"`
  param is a template param iff `has_templates(value, embedded=True)`. Otherwise it is static,
  coerced as today: a `str` stays itself and `$${` stays intact.
- **`resolve_templates`.** For a key with `param_mode(template_config.node_type, key) == "embedded"`:
  - `resolution = resolve(template, context, embedded=True)` (no `auto_parse`);
  - `is_simple_template = False`.

  Unresolved inserts reach the existing `resolution.ok` branch. `last_resolutions` records the
  template and the JavaScript sent.
- **Callers** (all inherit): the engine's `_execute_single_node` (`engine.py:1745-1760`, also the
  batch per-item path for MCP nodes), `plan_node.py:144` (dry-run), and the sub-workflow paths
  (`batch_executor.py:219`, `execution/plan.py:1533/1706`).
- **`mcp_server/services/execution_service.py:731-736`** (`registry_run`). Env expansion skips
  params whose `param_mode(...)` is in `("body", "embedded")`. 118 skips `"body"`; JavaScript's
  `${a}` is not an environment variable either.
- **`core/trace_report.py:523-536`** reads `parse()` operands instead of `TEMPLATE_EXTRACT_PATTERN`.
  That way an unresolved insert's path is `up.missing`, and bare JS is not read as a path.

### D10 — The web (#683 closes here)

**One segmenting walk.** `scan.ts` exports it, and every TS reader of `${…}` goes through it:

```ts
export type TemplateToken =
  | { kind: "text" | "escape" | "issue"; start: number; end: number }
  | { kind: "expression"; start: number; end: number; asJson: boolean; refs: Ref[]; operands: string[] };
export function templateTokens(text: string, mode: ParamMode = "template"): TemplateToken[]
```

- **`templateTokens`** is `templateRefs`' loop turned into tokens (mirroring `_tokenize`), with
  `_JSON_INSERT` copied into `EXPRESSION_AT`.
  - `"embedded"` keeps only `asJson` expressions (mirroring `embedded_code`).
  - `"body"` yields one `text` token.
  - `templateRefs` is derived from it. `ParamMode` is exported from `types.ts`.
- **`paramTextReads`** passes `param.mode`.
- **`format.ts::parseTemplate(text, mode = "template")`** builds on `templateTokens` and keeps
  returning its existing `TemplateSegment {text, isRef}` (`format.ts:4`, unchanged name). The
  callers get escape-awareness (#683) and the mode for free.
  - **Every caller that renders a param's text passes `param.mode`:** `WorkflowNode.tsx` `ParamValue`,
    `ParamBlock`'s `CodeBlock`, the per-item preview `ReadPanel.tsx:115-119`, `BatchItems.tsx:47`,
    and `ExpandableBox`'s modal.
  - **Text without a param** (the source pane) uses `"template"`.
  - **`refMatchesHighlight`** compares parsed operands, so highlight `gen.result` marks
    `${gen.result|json}`.
- **`batchItems.ts`** substitutes only expression tokens whose single operand is rooted at the
  alias, replacing its own body regex at `:31`. An `asJson` one substitutes `JSON.stringify(value)`.
  Whitespace differs from Python's `{"a": 1}`; that is a display-only difference, and a comment
  says so.
- **`sourceDecorate.ts::refSegments`** builds on `templateTokens(text)`: expressions are teal and
  escapes are literal (#683).
  - The source pane has no param mode. After 118, a fenced ```` ```javascript function ```` block
    shows no teal (non-markdown fence), while an inline `- function: |` block teals pflow-shaped
    `${…}` through `refSegments`.
  - This is a documented limit in `web/src/graph/CLAUDE.md`. Re-check both forms at PD against
    118's shipped behaviour.
- **Rejected:** a TS copy of `_EMBEDDED_CODE`.

### D11 — Validate/run parity rows (`tests/test_integration/test_template_parity.py`)

A new `SURFACES` entry, `embedded_code`: node `s` of type `mcp-corpus-evaluate_script` with a
`function: str` param.

**Registration — the preferred route keeps the end-to-end leg.** Register that type in
`_corpus_registry` against the corpus **sink** class with an interface declaring `function: str`,
and add the server `corpus` through `MCPServerManager` in the same fixture. Compilation injects
`__mcp_*` params for any `mcp-` type (`compiler.py:89-123`; config isolated by
`tests/conftest.py:370-390, 451-465`). The harness's e2e leg (`:1981-1987`) then runs the Ok rows
through `WorkflowRunner` with no MCP server.

**Fallback.** If the sink cannot accept the injected params, use the MCPNode entry shape
(`tests/test_nodes/test_mcp/test_source_line_sidecar.py:104-132`) and skip e2e for this surface as
for `cache`. Log which route was taken.

| Template in `function` | Validator | Runtime |
|---|---|---|
| `const t = ${p.out_str\|json};` | `Ok()` | `Resolves('const t = "<json>";')` |
| `${p.out_bool\|json}` (whole value) | `Ok()` | `Resolves("true")`, a `str` |
| `` `${a + b} ${x}` `` (no pflow `x`) | `Ok()` | `StaticLiteral()` |
| `` `Total: $${price}` `` | `Ok()` | `StaticLiteral()`, both dollar signs |
| `${ghost.x\|json}` | `Error("non-existent node 'ghost'")` | `Raises(...)` (compile data flow) |
| `` `$${p.out_str\|json}` `` | `Error("sits inside '$${")` | `StaticLiteral()`. Validator-only rule; the row comment says why |
| `` `${${p.out_str\|json} + 1}` `` | `Error("sits inside another")` | `StaticLiteral()`. Same |
| `${p.out_str\|json }` | `Error("not a pflow insert")` | `StaticLiteral()`. Same |

The misplaced rows on the other surfaces follow D4's table.

### D12 — No trace-format change

- `template_resolutions` already records `{template, resolved}`.
- A converted param moves from static params to template params: one memo-cache miss per such step.
- No version bump.
- The Task-159 baseline is the outer regression net. No case contains MCP code, so the expected
  result is P0's drift set.

---

## 4. Phases

### Agent assignment (phases ≠ agents)

| Launch | Phases | Tier · effort | Why this boundary |
|---|---|---|---|
| I1 | P0 → PA → PB → PC | Opus · **high** | One contract built bottom-up (grammar → policy → engine). Each phase builds on the previous one, with seam logic throughout. |
| — | mid-task review after PC | the task orchestrator commissions it | Engine contact; the validate/run contract is complete only at PC. |
| I2 | PD | Opus · **high**, fresh | A different stack (TS) and a refactor of the one TS walk; needs the `pflow ui` slot. Not design-bearing: a JS `${…}` simply stops being decorated as a reference. Uses the specialist `task-phase-implementer` hand-off. |
| I1 resumed (else a fresh Opus · medium) | PE | Opus · medium | Docs and conversion belong to whoever holds the rule. Rotate if I1's window is past ~350k. |
| — | PZ | task orchestrator | Completion gate. |

**Per-phase gate:** `make check` + `make test`, then the "FULLY happy?" resume. PD also runs
`npm run typecheck` + `npm test` in `web/`. Direct the PA and PC implementers to `test-reflect`:
grammar rows and resolution arms are easy to fake-pass. Completion adds `make test-all-local`.

---

### P0 — Baseline (I1's first step)

- Record in the progress log, **by name**:
  - the `make test` pass/fail set;
  - the `.taskmaster/tasks/task_159/baseline/verify.sh` drift set;
  - the result of `.taskmaster/tasks/task_170/implementation/examples-baseline/capture.py --check`.
- Run the six §0 checks and log each.
- Grep `src/`, `tests/`, `examples/`, `workflows/` and `docs/` for `|json` and for
  `mcp-*-evaluate_script` / `browser_evaluate` / `navigate_page` / `browser_run_code` types, and log
  the hits.
- Re-run the checkpoint probes and confirm the BEFORE blocks still match. 118 may have changed the
  shared layout.
- **Handoff:** all of the above is in the log.

### PA — The grammar: `${x|json}` parses and resolves  ·  grammar change (Python + TS mirror)

**Goal:** `${x|json}` is an Expression on every surface, resolution inserts JSON text, and the
policy view and the helpers exist. Nothing else about the language changes.

**Files:**
- `src/pflow/core/templates.py`:
  - D1;
  - D3's `embedded_code`, `resolve(embedded=)`, `has_templates(embedded=)`;
  - D4's `_resolve_string` arm and the `Resolution` docstring;
  - D5's `hidden_inserts` / `near_miss_insert`.
- `web/src/graph/scan.ts`: the grammar copy only — `_JSON_INSERT` into `EXPRESSION_AT`, and
  `templateRefs` reads an insert's refs.
- `web/src/graph/scan.test.ts` parity rows, and their Python twins in
  `tests/test_core/test_graph_build.py:1347+`.
- `tests/test_core/test_template_grammar.py` (`GRAMMAR_ROWS` and the counted invariants).
- `tests/test_core/test_templates.py` (`SHAPES` gains `as_json` rows; `test_views`; fuzz).
- `src/pflow/core/CLAUDE.md` Template language: the JSON insert; `embedded_code` is a policy view
  whose Text may hold `${`; the issues channel also carries misplaced inserts.

**Decisions:** D1, D3 (core functions), D4 (resolve arm), D5 (helpers). The TS segmenting refactor
belongs to PD. PA keeps its TS change to the grammar copy so the mirror rule ("same step") holds.

**Mid-task review:** no; it is covered after PC.

**Tests must catch:**
1. **Grammar rows**, each with all six `GRAMMAR_ROWS` columns: `${x|json}`, `${x | json}`,
   `${a.b[0]|json}`, `${a[${i}].b|json}`, `${a ?? "d"|json}`, `${a ?? "x|json"}` (a literal, **not**
   an insert), `${x|jsn}` (Issue), `${x|json }` (Issue), `${ x|json}` (Issue), `$${x|json}`
   (escape), `${x||json}` (Issue). TS is identical.
2. **The reassembly invariant** holds (`raw` includes the suffix).
3. **Undoing the encoding.**
   - `resolve("${x|json}", {"x": "{\"a\":1}"}, auto_parse=True, embedded=True).value` is the
     **string** `"{\"a\":1}"` JSON-encoded, not a dict.
   - `parse("${x|json}").is_simple is False`.
   - Mutation to record: make `is_simple` ignore `as_json`, and this test goes red.
4. **Values** (with `embedded=True`), each mapping to its insert:

   | Value | Insert |
   |---|---|
   | `"Don't Stop"` | `"Don't Stop"` |
   | `True` | `true` |
   | `None` | `null` |
   | `3` | `3` |
   | `{"a": [1, 2]}` | `{"a": [1, 2]}` |
   | `"é"` | `"é"` |
   | `"42\n"` | `"42\n"` (text stays a string) |
   | a `set` | the JSON string of its text |

   A coalesce whose first operand is absent gives the literal's JSON.
5. **Outside embedded code it is an Issue at run time.** `resolve("say ${x|json}", {"x": 1})` has
   value `"say ${x|json}"`, `issues == {"${x|json}"}` and an empty `unresolved`. Mutation: delete
   the arm, and the test goes red.
6. **The view.** Source: `` `${a + b}` $${p} ${user.name} ${t|json} '${x}' ``.
   - `embedded_code(parse(src))` has exactly one Expression (`t`), and its Text segments re-join to
     the source with the insert span removed.
   - `resolve(src, {"t": "it's", "user": {"name": "N"}}, embedded=True)` replaces only the insert.
   - **Presence pair:** the same call without `embedded` does replace `${user.name}`.
7. **Static routing.** With `embedded=True`, `has_templates` is False for `` `$${p}` `` and for
   `${user.name}`, and True for `${t|json}`. With `embedded=False` the first two are True.
8. **`hidden_inserts`.**
   - Finds inserts in: `` `cost: $${count|json}` ``, `$${foo ${x|json}}`, `` `${${x|json} + 1}` ``.
   - Finds none in `${x|json}`, `` `$${price}` `` or `${a + b}`.
   - Spans are correct.
9. **`near_miss_insert`.** Rows `${x|json }`, `${ x|json}`, `${x|JSON}` give `${x|json}`, `${x|json}`,
   `${x|json}`. Rows `${x|jsn}`, `${a + b}`, `${ x }` give `None`.
10. **Lexical pattern.** `TemplateResolver.TEMPLATE_PATTERN.search("${a.b|json}").group(1) == "a.b"`,
    and `SIMPLE_TEMPLATE_PATTERN` does not match it.
11. **TS parity.** `${gen.result|json}` reads `gen.result`; `${gen.result|jsn}` reads nothing. Mirror
    these rows in `test_graph_build.py::test_refs_with_path_in_reads_the_template_parse`.
12. The grammar seam meta-test passes unchanged.

**Handoff:** the language knows JSON inserts. Mid-way, a non-embedded insert passes the validator
but refuses at run time; PB closes this. No PR here.

### PB — Embedded code: the classification, the validator, the graph

**Goal:**
- On the four params, a bare `${…}` is invisible to every pflow check and edge, and an insert is a
  checked reference.
- A misplaced `|json`, a hidden insert, and a near-miss spelling are each an ERROR.
- A bare in-scope name is either an ERROR (an otherwise-unused input) or a WARNING.
- A quoted insert warns.

**Files:**
- `core/workflow/template_surfaces.py`: D2; `TemplateSurface.mode`; the `templates()` view.
- `runtime/template_validation/validator.py`:
  - the Issue pass: D4, D5 and the log line;
  - the unused-input pass plus the D6 consumer.
- `core/workflow/data_flow.py`: D6 detector.
- `core/workflow/validator.py:571-578`: D4 output sources.
- `runtime/template_validation/type_validation.py`: D8 Pass 6.
- `core/workflow/graph/scope.py`, `build.py`, `renderers/react_flow.py`: D8.
- `web/src/types.ts`: the `mode` field only.
- The regenerated contract fixtures.
- `mcp_server/services/execution_service.py:731-736`: D9's last bullet.
- Tests.

**Decisions:** D2, D3 (surface consumer), D4 (validator half), D5 (checks), D6, D8. Message text:
checkpoint §4, §5, §7 **as ruled** (CP-1).

**Mid-task review:** covered after PC. The lenses below are assigned to PB as the phase that
introduces the validator policy.

**Tests must catch:**
1. **Classification.**
   - `"embedded"`:
     - `mcp-chrome-devtools-evaluate_script` / `function`;
     - `mcp-chrome-devtools-isolated-evaluate_script` / `function`;
     - `mcp-playwright-browser_run_code_unsafe` / `code`.
   - Not embedded:
     - `…-evaluate_script` / `args`;
     - `mcp-x-evaluate_scripts` / `function`;
     - `evaluate_script` / `function` (no `mcp-`);
     - `shell` / `function`;
     - `None`.
2. **A consumer still reads bare JS.** One table, with one row per §2.2 consumer, each called
   through **its own entry point**. Each row puts a bare reference in an embedded param that the
   consumer WOULD report, and uses the same text as `${…|json}` as the presence half:

   | Consumer | Bare reference | Insert (presence half) |
   |---|---|---|
   | data flow `${ghost.x}` | nothing | non-existent node |
   | Pass 5 `${p.nope}` | nothing | reported |
   | Pass 8 `${item.nope}`, batched | nothing | reported |
   | Issue pass `${a + b}` | nothing (on an llm prompt: the malformed ERROR) | — |
   | Pass 6, registry type `command: int` stub | nothing | — |
   | graph edge from `${p.stdout}` | no edge | one edge, labelled `function` |
   | `RFParam` | `is_dynamic` False, `mode == "embedded"` | `is_dynamic` True |

   **Mutation ledger** — make each change below, confirm its rows go red, and record the outcome:
   - drop the view in `templates()`;
   - drop the flag in `_add_ref_edges`;
   - drop the Pass 6 skip.
3. **Misplaced insert.**
   - `${x|json}` gives the §5 ERROR with the right `path` in each of these places: an llm `prompt`,
     `batch.items`, `loop.while`, an output `source` (both the `${…}` and the bare `x|json` form, the
     latter with **no** second "non-existent node" error), and a `## Cache` var.
   - The fix line strips the suffix from `${a ?? "d" | json}`.
   - `--validate-only` output shows `Found 1 template error(s)`.
4. **Hidden and near-miss inserts** (checkpoint §7a/§7b), each as **the only** error:
   - `` `cost: $${count|json}` ``;
   - `` `${${count|json} + 1}` ``;
   - `${title|json }`;
   - `${title|JSON}`.

   Presence pairs:
   - `` `cost: $${count}` `` (no insert) gives only the unused-input error.
   - The same texts on a non-embedded param give no §7 error.
   - An unbalanced `$${` gives nothing new.
5. **Bare names** (checkpoint §4):
   - **4a:** `'${selector}'` gives the ERROR with the quote-aware fix, and **no** unused-input
     error. Removing the bare reference brings the unused-input error back (presence pair).
   - **4a unquoted:** `${user.name}` inside a template literal gives the "outside any quotes" fix.
   - **4b:** `${item.id}` on a batched step gives the WARNING with the "spaces" line, and
     `${ item.id }` clears it.
   - **Step ids:** a step id with a path (`${fetch.result}`) warns; a bare step id (`${fetch}`) does
     not.
   - **No hit:** `${a + b}`, `${i}` (no pflow `i`), and `${x|json}` produce nothing. A non-batched
     step's `${item.x}` beside a batched step produces nothing.
   - **Grouping:** two references give one warning listing both, in source order.
   - **4c:** a whole-value `${gen.code}` gives the `eval` fix.
   - **4d:** `'${selector|json}'` gives the quoted-insert WARNING, and `${selector|json}` gives none.
   - Assert the rendered text through `--validate-only` for 4a and 4b, and the JSON
     `embedded_references[].replacement` for 4a.
6. **`registry_run`.** An embedded param holding `` `${a} ${b}` `` with no env var `a` reaches the
   node unchanged (no "Missing environment variable"). A non-embedded param still expands
   `${PFLOW_TEST_X}`. Stub only at the MCP boundary.
7. **Contract fixtures** regenerate with `mode` on every param and nothing else changed (the diff is
   bounded).

**Handoff:** checkpoint §4, §5, §6 (Error 1/2 shape) and §7 reproduce through
`uv run pflow --validate-only` on the inline probes.

### PC — Runtime and its diagnostics  ·  ENGINE CONTACT  ·  **triggers the mid-task review**

**Goal:**
- The tool receives the source text with each insert replaced.
- A bare `${…}` and `$${` are sent as written.
- An unresolved insert fails like any reference, and every rebuilt fix keeps `|json`.

**Files:**
- `runtime/engine/template_resolution.py` (D9).
- `runtime/engine/template_errors.py` + `core/diagnostic_render.py` + `core/workflow/data_flow.py:344`
  + `runtime/template_validation/path_validation.py:467-474` (D7).
- `core/trace_report.py:523-536` (D9).
- `tests/test_integration/test_template_parity.py` (D11, and D4's other-surface rows).
- Runtime tests.
- `runtime/engine/CLAUDE.md` (Parameters: an embedded param is static unless it holds an insert, and
  is resolved with `embedded=True`).

**Decisions:** D7, D9, D11. D4's runtime half is already in PA; PC proves it through the engine.

**Tests must catch:**
1. **Parity corpus:** every D11 row and every D4 table row, validator and runtime, through the
   harness's real entries.
2. **The engine path, not just `resolve`.** Compile a workflow with an `mcp-corpus-evaluate_script`
   step and call `resolve_templates(config.template_config, shared, …)`:
   - `function` resolves to the expected JavaScript;
   - in a step whose `function` holds only bare JS, `function` is in `static_params` with `$${`
     intact.
3. **Batch.** A batched embedded step with `${item.title|json}` and items `["Don't", "x"]`, driven
   through the **engine's** `_execute_single_node` path (not `batch_executor.py:219`) with
   `MCPNode` execution stubbed at the pool/tool-call boundary. The per-item resolved `function` texts
   carry `"Don't"` and `"x"`.
4. **Unresolved insert, strict mode.** The error reads
   `Unresolved variables in parameter 'function': ${up.missing|json}`.
   - Its did-you-mean is `${up.result|json}`.
   - A coalesce suggestion ends in `|json`.
   - **Presence pair:** the same miss in a bare template param shows no suffix.
   - Permissive mode records the miss and the step runs.
   - `inject_none_for_optional_inputs` is `inputs`-only; confirm an embedded param is unaffected.
5. **No auto-parse.** A whole-value `${p.out_dict|json}` resolves to JSON **text**. The container
   auto-parse at `:272-277` never fires.
6. **Trace.** `last_resolutions["function"] == {"template": <source>, "resolved": <JS>}`. `pflow
   report` on an unresolved insert names path `up.missing` (D9's trace_report switch).
7. **Dry-run.** `--dry-run` of a workflow with an embedded step produces no `template_error` entry.
   On a miss, `cause` names the insert. `PlanEntry` carries no params, so do not assert printed
   values.

**Real-surface exercise.** This needs Chrome via the chrome-devtools MCP, and no `pflow ui`.
1. Build a probe workflow: `new_page` with a `data:text/html,…` URL, then `evaluate_script` with
   `` () => ({t: ${title|json}, on: ${flag|json}, lit: `${1 + 1}`, d: `$${5}`}) ``.
2. Run it with `title="Don't Stop"` and `flag=true`.
3. Expect the result `{"t": "Don't Stop", "on": true, "lit": "2", "d": "$5"}`.

If the server cannot start in the build environment, hand back. Do not skip the run.

**Mid-task review** (yes: engine contact, and the validate/run contract is complete here). Run it
on PA–PC's diff, with each lens assigned to the phase that introduced the risk:
- **`review-validation-consistency`** — **PB** (validator policy) against **PC** (the runtime
  twin). Target: validator files + `template_resolution.py` + `core/templates.py::_resolve_string`.
- **`review-impact-completeness`** — **PA** (the AST and grammar change). It must cover every
  consumer of `Expression.raw`, `is_simple`, `TEMPLATE_PATTERN` and the issues channel, and every
  reader of params' `${…}`.
- **`review-silent-failures`** — **PB** (the view hides references by design). It must cover
  unconverted forms, hidden and near-miss inserts, quoted inserts, and static/template routing.
- **`review-feature-interactions`** — **PB/PC**. It must cover batch, nested and dynamic children,
  output sources, the cache block, `registry_run`, and memo keys.

Fixes fold in before PD.

**Handoff:** `make test` is green and the real probe run's output is in the log.

### PD — Web (specialist hand-off; not design-bearing)  ·  closes #683

**Use case.** An author reads an `evaluate_script` step on the canvas, in the read panel, and in a
batch preview.
- `${title|json}` appears as a pflow reference: a chip, teal, an edge from its producer, and item
  substitution in a batch preview.
- The JavaScript's own `${a + b}`, `${user.name}` and `$${price}` appear as plain code: no chip, no
  teal, no edge, no substitution.
- Everywhere, `$${x}` is literal (#683).

**Files:**
- `web/src/graph/scan.ts`: D10 `templateTokens`; `templateRefs` derived from it; `paramTextReads`
  reads `param.mode`.
- `web/src/utils/format.ts`: `parseTemplate(text, mode)`; `refMatchesHighlight`; delete 118's
  `isCodeBody` in favour of `param.mode`.
- The callers named in D10.
- `web/src/utils/batchItems.ts`.
- `web/src/graph/sourceDecorate.ts:32`.
- Their tests.
- `web/src/graph/CLAUDE.md`: the mirror rule now covers `templateTokens`/`embedded_code`, plus the
  source-pane limit.
- `web/src/utils/CLAUDE.md`: template text tokens → `scan.ts::templateTokens`.

**Decisions:** D10. **Mid-task review:** no.

**Tests must catch:**
1. **Tokens mirror `_tokenize`.** A table in the spirit of `SHAPES`, covering the kinds and spans of:
   text, escape (balanced and unbalanced), expression (`asJson` both ways), issue.
2. **Embedded mode.** `templateTokens(src, "embedded")` for the PA-6 source gives one expression.
   With `paramTextReads` and `mode: "embedded"`, `${gen.result|json}` reads `gen.result` and
   `${gen.result}` reads nothing. With `"template"`, the bare one reads (presence pair).
3. **#683, per surface.** `$${x}` is literal in `parseTemplate`, `refSegments` and
   `resolveBatchItems`. For each, assert against the same text with `${x}` decorated or substituted
   (presence pair).
4. **Batch preview.** In an embedded param with `${item.name|json}` and a JS `${item.id}`:
   - the insert becomes `"Ann"`, and the JS one is untouched;
   - in the **per-item preview block** (`ReadPanel.tsx:115-119`) the leftover `${item.id}` is **not**
     teal, while the insert's substitution is shown;
   - a template param still substitutes and teals as today.
5. **Highlight.** `refMatchesHighlight` marks `${gen.result|json}` for highlight `gen.result` and for
   `gen`.
6. Existing web tests that use a JS-looking `${…}` in a non-embedded param still pass (template
   mode).

**Acceptance.** Drive this with the `screenshot-pflow-web-ui` skill and screenshot every item.

The test workflow:
- an `up` step;
- an `mcp-chrome-devtools-evaluate_script` step whose `function` holds `${up.stdout|json}`,
  `` `${a + b}` ``, `${user.name}` (input `user`) and `` `$${price}` ``;
- a batched evaluate_script step with `${item.name|json}` and a JS `${item.id}`.

The checks:
1. On the canvas, the `function` row has one chip (`up.stdout`) and none for the JS.
2. The edge from `up` lands on `function`, and there is no edge for `user`.
3. In the read panel only the insert is teal.
4. In the source pane, check both the fence form and the inline form against D10's documented limit.
5. In the batch preview, `"Ann"` replaces the insert, and `${item.id}` stays and is not teal.

**The `pflow ui` server slot is shared.** Ask the main orchestrator for it before starting, use a
free port, stop the server by PID, and declare `dev servers: none` at hand-back.

**Handoff:** `npm run typecheck`, `npm test` and `make test` are green, and the screenshots are in
the log.

### PE — Conversion, guide, docs, instruction files

**Goal:** the four in-tree sites use `${x|json}`. No shipped text teaches the quote caveat, or `$${`
for JavaScript in a code param. The rule is findable where agents look.

**Files and exact edits:**

*The four sites and their caveats*
- **`examples/real-workflows/screenshot-pflow-web-ui/click.pflow.md:83-85`:**
  `const sel = ${selector|json};`, `const text = ${text|json};`,
  `const measureId = ${measure_id|json};`. Delete the caveat at `:17-18`.
- **`hover.pflow.md:56`:** `const name = ${row_name|json};`.
- **`.claude/skills/screenshot-pflow-web-ui/SKILL.md:34-35`:** delete "Selectors interpolate into
  single-quoted JS: use double quotes inside." Then run `make sync-claude-assets`.

*Where agents read before writing a step* (they read these before the guide)
- **`cli/commands/mcp.py:1002`** (`pflow mcp describe`) and **`registry/context_builder.py:683`**:
  when `param_mode(tool type, param) == "embedded"`:
  - emit `- function: () => ${previous-step.response|json}`;
  - append to that param's line: `(JavaScript, sent as written; insert a pflow value as ${x|json})`.
  - Add a test for each.

*Guide*
- **`src/pflow/guide/nodes/mcp.md`:** add a short section "Code passed to a tool" after
  "Whole-program tools" (`:107-115`). It covers:
  - which params are embedded code;
  - the rule: sent as written; `${x|json}` inserts a JavaScript value of the value's own type, with
    no quotes around it, where a value goes;
  - text holding JSON (shell `stdout`) is a string, so use `JSON.parse(${x|json})`;
  - `$${` is sent as written. This is the opposite of a shell command, where it is an escape;
  - `${ x }` (with spaces) marks a JavaScript variable that shares a pflow name;
  - `eval(${gen.code|json})` for a generated program (R7);
  - `|json` is accepted only there.

  Also, `:304` ("MCP JSON string parameters") gains one sentence pointing at `${x|json}` for
  JavaScript.
- **`src/pflow/guide/core.md`**, "Template Variable Complete Reference" (`~:430`): add one line, "In
  JavaScript passed to an MCP tool, `${…}` is JavaScript; see `pflow guide mcp` for `${x|json}`."

*User docs and architecture*
- **`docs/reference/nodes/mcp.mdx`:** the same content as the guide section, shorter.
- **`docs/how-it-works/template-variables.mdx:330`:** "JavaScript template literals work the same
  way" becomes "in a code param of an MCP tool, `${…}` is JavaScript and `$${` is sent as written;
  values go in as `${x|json}`", with a link. Add `|json` to the syntax reference with its one allowed
  place.
- **`architecture/reference/template-variables.md`:** the grammar section gains the insert. 118 also
  edits this file, so rebase, do not overwrite.

*Instruction files*
- **`src/pflow/runtime/template_validation/CLAUDE.md`:**
  - the Issue-pass bullet gains misplaced, hidden and near-miss inserts;
  - the unused-input bullet gains the embedded-code ERROR;
  - an embedded param's surface yields the view;
  - correct the stale claim at `:29` that every template check walks `iter_template_surfaces`.
    Pass 6 and the graph scope helpers read params themselves; name them.
- **`src/pflow/core/workflow/CLAUDE.md`:** the third mode (one line; the docstring owns it).
- **`src/pflow/core/workflow/graph/CLAUDE.md:53-54`:** per D8.
- **`.claude/agents/pflow-codebase-searcher.md`:** add `templates.embedded_code` and
  `template_surfaces._EMBEDDED_CODE` to the location map, then run `make sync-claude-assets`.

*Not edited here*
- **`context/CONTEXT.md`:** R8's proposals go up for the main orchestrator.

*Before committing*
- Grep each new CLAUDE.md sentence's distinctive phrase across `src/pflow/` and the CLAUDE.mds.

*Docs-example harness*
- **`tests/test_docs/test_guide_example_validation.py:107`:** `_BARE_VAR_RE` misses `${x|json}`.
  Either every new fenced example declares its inputs, or the harness collects names from parsed
  operands (118 PC already moves it to parsed names; build on that).

**Real-surface exercise.** This needs the `pflow ui` slot and Chrome.
- Run `click.pflow.md` with `text="Don't exist"` (#550's repro). It fails with the workflow's own
  "click target not found … none with text \"Don't exist\"", not with a JS SyntaxError.
- Run it again with a matching text; it clicks.
- Run `hover.pflow.md` once.
- `uv run pflow --validate-only` on all seven screenshot workflows: each is valid with no warning.
- `uv run pflow mcp describe mcp-chrome-devtools-evaluate_script` shows the new snippet.

**Tests must catch:** `tests/test_cli/test_guide.py`, `tests/test_docs/*`, and the new
describe/context-builder tests pass.

**Mid-task review:** no. This phase is docs plus two output strings; `make check` and the tests are
the gate.

### PZ — Completion (task orchestrator)

1. **Gates.** Merge `origin/main`, then run:
   - `make check`;
   - `make test-all-local`;
   - `verify.sh` — the drift set must equal P0's;
   - `capture.py --check` — clean.
2. **Real surface.** Walk the spec's Verification list one line at a time (§6), through
   `uv run pflow`.
3. **Code-mode `deep-review`** on the full branch. The sensitive path (engine) means the full floor:
   - `review-silent-failures`, `review-impact-completeness`, `review-feature-interactions`,
     `review-test-fidelity`;
   - `review-validation-consistency` (target: the validator + its runtime twin);
   - `review-agent-ux` (target: the messages + guide/docs + describe);
   - **`review-simplicity`** and **`review-spec-conformance`**;
   - `review-falsifier` last, as a direct launch, given the spec and the conformance lens's
     Requirement Inventory.
4. **Close-out.**
   - Set the spec's `## Status` to `done` and add `## Completed`.
   - Run `create-task-review`. It states what each successor inherits:
     - Task 120: the insert renders a value's type exactly, so its typing rulings change what is
       emitted.
     - Task 167: spans and the view.
     - Anyone adding an embedded tool or an insert word: ADR-0016.
   - Run `create-pr` with "Closes #550" and "Closes #683". Add "Refs #621 — not a closing PR" unless
     Task 118 already closed its shell half, in which case write "Closes #621". Add "Refs #620".
5. **Hand-back note for the user** — behaviour changes with no diagnostic, or with a new one:
   - A saved workflow under `~/.pflow/workflows/` with a bare `'${x}'` in an embedded param now
     fails validation. That is §4a, and the fix is named.
   - A workflow that wrote `$${…}` in JavaScript (as the old docs taught) now sends a `$` followed by
     the interpolation, with no diagnostic. No in-tree or local saved workflow does this.
   - A paused or failed run of a converted workflow resumes only with `pflow resume --force`,
     because the content hash changes.

---

## 5. Stale-surface inventory (file:line on `ebf7cab2` — re-verify)

**Edited in PE:**
- `click.pflow.md:17-18, 83-85`; `hover.pflow.md:56`.
- `.claude/skills/screenshot-pflow-web-ui/SKILL.md:34-35`, plus the `.agents/` mirror.
- `cli/commands/mcp.py:1002`; `registry/context_builder.py:683`.
- `guide/nodes/mcp.md:107-115, 304`; `guide/core.md:~430`.
- `docs/reference/nodes/mcp.mdx`; `docs/how-it-works/template-variables.mdx:330` + the syntax
  section.
- `architecture/reference/template-variables.md`.
- `runtime/template_validation/CLAUDE.md:29-34` + its unused-input bullet.
- `core/workflow/CLAUDE.md`; `core/workflow/graph/CLAUDE.md:53-54`.
- `.claude/agents/pflow-codebase-searcher.md`.

**Edited in other phases:**
- `core/CLAUDE.md` Template language + Two channels (PA).
- `runtime/engine/CLAUDE.md` (PC).
- `web/src/graph/CLAUDE.md`, `web/src/utils/CLAUDE.md` (PD).

**Checked, not stale:**
- The two MCP instruction resources (`src/pflow/mcp_server/resources/instructions/*.md`): no MCP
  code-param content. Their shell fences are Task 118's.
- The other five screenshot workflows.
- `guide/core.md:460-469` (a shell escape hatch, which is Task 118's).
- `scripts/check_mdx_fences.py:84-92`, which already guards `${…}` prose in MDX.

---

## 6. Verification matrix (spec → evidence)

| Spec Verification line | Evidence |
|---|---|
| `` `${user.name}` `` and `${a + b}` reach the tool unchanged, in a batch with alias `item` and with an input `user` | PA-6, PB-2/5, PC-2/3, D11 rows, PC real run |
| `${title\|json}` with `Don't Stop` → a valid JS string; boolean → `true`; object → object literal | PA-4, PC-1/2, PC real run |
| `${nod.result\|json}` is a validation error; `--validate-only` and the run agree | D11 `ghost` row; PB-2; checkpoint §6 through the CLI |
| The in-tree screenshot workflows drop the caveat and still run (four sites) | PE edits + real runs |
| `` `Total: $${price}` `` reaches the tool with both dollar signs | PA-6/7, D11 row, PC real run (`d: "$5"`) |

---

## 7. Embedded checkpoints (flagged — plan them as hand-backs)

- **CP-1 — diagnostics, show before code.** **Built by the planner and revised after the plan
  battery. Not yet ruled.**
  - The file is `diagnostics-checkpoint.md`, rulings R1–R6 and R8 (R7 is a note). The build starts
    only after the rulings are logged in the progress log.
  - A ruling that changes text changes strings and assertions only. The structural ones:
    - **R1** changes the D2 table.
    - **R2 "honour everywhere"** deletes D4's runtime arm and its corpus rows.
    - **R3 "alongside"** moves D6's ERROR back to a WARNING and drops the unused-input coupling.
    - **R8** renames `"embedded"` / `embedded_code` / `as_json` if a different noun is ruled.
- **CP-2 — coordination, not the user.**
  - The build waits for Task 118 Part 2 (§0).
  - PD and PE need the `pflow ui` slot.
  - PC's and PE's real runs need the chrome-devtools MCP server (Chrome). If the build environment
    cannot start it, hand back.

---

## 8. Risks, unverified, follow-ups

**Unverified:**
- That 118 lands in the shapes its plan describes (the §0 checks).
- Whether the corpus sink can accept the injected `__mcp_*` params (D11 has a fallback).
- Whether chrome-devtools reports a thrown JS error as `isError`.

**Accepted costs:**
- **Legitimate JavaScript that shares a pflow name in scope** warns until the author writes
  `${ x }`.
- **A generated whole program** needs the `eval` form (R7).
- **The source pane** may teal a pflow-shaped `${…}` inside an inline `- function: |` block (D10).
- **An insert inside a longer template literal** (`` `Hello ${name|json}` ``) is not detected as
  "inside quotes".
- **Integers above 2^53** lose precision in JavaScript. That is JavaScript's `Number`, and nothing
  flags it.

**Follow-ups to file at the merge seam (not built):**
- **`registry_run`'s `validate_execution_parameters`** rejects any param text containing `eval(` or
  `exec(` (`mcp_server/utils/validation.py:52-64`). That blocks ordinary JavaScript and the R7 form,
  on that path only.
- **`KIND_COLORS["mcp"]` and `KIND_ICON.mcp`** never match an `mcp-…` kind. This is a searcher
  inference, not checked in a browser.
- **`pflow mcp describe`** mis-splits a hyphenated server name (`Server: chrome`).
- **`_CODE_BLOCK_TAG_TO_PARAM`** (`markdown_parser.py:104-120`) is dead code.
- **Widening `|json` to JSON bodies** (http `body`, `write-file` content) when a user asks; #550
  mentions this.
