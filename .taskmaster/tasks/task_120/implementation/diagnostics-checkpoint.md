# Task 120 — diagnostics checkpoint (CP-1, show before code)

> **RULED 2026-10-10 — user: *"go ahead with this"* on the five recommendations presented in plain language by the main
> orchestrator.** R1 = `Invalid input value` (distinct title, category stays `validation`) · R2 = the source clause on every
> message, as tabled in §1.2 · R3 = yes, the `??` operand sentence · R4 = resolved (`pflow settings set-env`) · R5 = 80
> characters, `<REDACTED>` for sensitive names · R6 = the §1.14 reason text with its two remedies. The AFTER blocks below
> are the contract; the build may start (plan §7).

Every new or changed user-facing message, with the BEFORE **executed** on `285e7b3f` (2026-10-10) and the AFTER
drafted. Rulings R1–R5 at the end. **The build does not start until this file is ruled** (plan §7). Text in the
AFTER blocks is the contract the tests assert against (structured fields first — `context["path"]`,
`context["source"]`, `suggestions` — never substrings of prose unless the test is about rendering).

## 0. Probe workflows (re-run at P0; `uv run pflow -p <file> …`)

All inputs use `### name` headings; every step has a description paragraph. `$P` is a scratch directory.

```
typed.pflow.md      ## Inputs: topics (array, required) · count (integer, default 3) · flag (boolean, default false)
                    ### show (code) inputs: topics/count/flag → annotations list/int/bool → result: str
a-string.pflow.md   ## Inputs: text (string, required) · ### show (code) inputs: text → `text: str` → result = type+repr
a-echo.pflow.md     ## Inputs: text (string, required) · ### echo (shell) env: TEXT: ${text} · command: printf '%s' "got:$TEXT"
container.pflow.md  ## Inputs: v (string, required) · ### show (shell) env: A: ${v.a}, B: ${v.b ?? "fallback"} · printf '%s %s' "$A" "$B"
bad-default.pflow.md ## Inputs: n (integer, default: abc) · ### show (shell) env: N: ${n} · printf 'n=%s' "$N"
envdef.pflow.md     ## Inputs: port (integer, required: false, default: 8080) · ### show (shell) env: P: ${port} · printf 'port=%s' "$P"
anyin.pflow.md      ## Inputs: data (any, required) · ### show (code) `from typing import Any; data: Any` → result = type+repr
child.pflow.md      ## Inputs: s (string, required) · n (integer, required) · ### show (code) `s: str; n: int` → result
parent.pflow.md     ### emit (shell) printf '%s' '{"a":1}' · ### call (workflow ./child.pflow.md) inputs: s: ${emit.stdout}, n: "7"
parent-batch.pflow.md ### emit (shell) printf '%s' '["7","x","9"]' · ### call (workflow ./child.pflow.md)
                    batch: {items: ${emit.stdout}, error_handling: continue} · inputs: s: hello, n: ${item}
parent-inline.pflow.md ### call (workflow ./child.pflow.md) batch: {items: ["7","x","9"], error_handling: continue} · inputs: s: hello, n: ${item}
```
(`error_handling` is the batch's own continuation key — a node-level `error_action: continue` does not continue
a batch. The planner's first probe used `error_action`, so its §1.5 BEFORE shows fail-fast output; P0 re-runs
both fixtures as written here.)

## 1. Message shapes

### 1.1 Boundary error — CLI argument (breaks 1, 4, 5, 6, 7)

**BEFORE** (`typed.pflow.md topics=tea --validate-only` then run):
```
✓ Workflow is valid
Input 'topics' expects list but received str

Suggestions:
  - Change the type annotation to: topics: str
  - Or convert the input value to list
  - Or use `Any` to accept any type: topics: Any
  At: node 'show'
To resume from the failed step: pflow resume 202f1052-…
```
(`count=3.0` → "expects int but received float"; `count=abc` with no code consumer → `WARNING: Cannot coerce
'abc' to integer`, the string flows on, exit 0.) The error blames the code annotation and offers a resume of a
run that never started a step.

**AFTER** (validate-only AND run, same text; exit 1; no resume line, no `resume_command`):
```
Error: Invalid input value

Input 'topics' is declared `- type: array` but received 'tea' from the command line.
  At: inputs.topics

  → Pass a JSON array (e.g. ["a", "b"]): topics='["tea"]'
```
Per type, the arrow line is `→ Pass <accepted_text>: <name>=<example>` where the example is the smallest fix of the
received value when one is obvious (`count=3` for `3.0`; `flag=true` for `maybe` → `flag=true`), else the
type's canonical example.

### 1.2 Source variants (same shape; the "from …" clause and the fix line change)

| Source | "… received 'x' …" clause | Fix line |
|---|---|---|
| `stdin` | `from stdin` (received shows the text with `\n` escaped: `'42\n'` is accepted — stripped — so this fires only for genuinely bad text) | `→ Pipe a whole number (e.g. 3), or pass count=3 on the command line` |
| `env` | `from the environment variable count` | `→ export count=3, or pass count=3 (an argument wins over the environment)` |
| `settings` | `from settings.env` | `→ pflow settings set-env count 3, or pass count=3` (verified: `pflow settings set-env`) |
| `default` | **different sentence**: `The default of input 'count' is 'abc' but its type is \`- type: integer\`.` At: `inputs.count.default` | `→ Change the default to a whole number (e.g. \`- default: 3\`), or the type to \`- type: string\`.` |
| `recorded` | `recorded by the run being resumed` | `→ Override it: pflow resume <id> count=3` |
| `call` (MCP) | `in the call's parameters` | `→ Pass a whole number: "count": 3` |
| `parent` (child boundary) | **different sentence**, §1.5 | |

**BEFORE for `default`** (`bad-default.pflow.md --validate-only` then run):
```
✓ Workflow is valid
WARNING: Cannot coerce 'abc' to integer
n=abc          (exit 0)
```
**BEFORE for `env`** (`port=abc` and `port=9090` exported, `envdef.pflow.md`): `port=8080` both times — the
default wins and the environment is never read (f₂). **AFTER:** `port=9090` → `port=9090`; `port=abc` → the env
row above, exit 1.

### 1.3 Multi-input aggregate

**BEFORE** (two bad inputs at compile): one message `Found 2 input validation errors:\n  • 'count' - …\n  • 'flag' - …`,
path `inputs`, suggestion "Fix all validation errors above before compiling the workflow" (each input's own
suggestion dropped).

**AFTER:** two full blocks (§1.1 shape), each with its own `At:` and `→`; JSON `errors[]` has two entries.

### 1.4 JSON shape (`--output-format json`, and MCP `workflow_execute`)

**BEFORE** (a missing required input, for the envelope):
```json
{"success": false, "status": "failed", "error": "Workflow requires input 'topics': Topics",
 "errors": [{"severity": "error", "message": "…", "source": "validation", "title": "Validation Error",
             "context": {"category": "validation", "path": "inputs.topics"}, "category": "validation", "path": "inputs.topics"}],
 "diagnostics": [ … same … ], "workflow": {"action": "unsaved", "name": "typed.pflow.md"}}
```
**AFTER** (one typed-input error; the envelope is unchanged, the entry gains the shared context keys):
```json
{"severity": "error",
 "message": "Input 'count' is declared `- type: integer` but received '3.0' from the command line.",
 "source": "validation", "title": "Invalid input value",
 "suggestions": ["Pass a whole number: count=3"],
 "context": {"category": "validation", "path": "inputs.count", "input": "count", "declared_type": "integer",
             "received": "3.0", "source": "argument", "accepted": "a whole number (e.g. 3)"}}
```
`received` is `<REDACTED>` when the input name is sensitive (`token`, `api_key`, …, `security_utils`), and cut to
80 characters with `…` when long (R5). No `execution_id`/`resume_command` keys (pre-execution failure).

### 1.5 Child-input error (break 10; per item, routable)

**BEFORE** (`parent-batch.pflow.md`; executed with node-level `error_action: continue`, which does not continue a
batch, so this shows fail-fast at item 0 — under `batch.error_handling: continue` every item fails the same
way and the batch raises "all 3 items failed"; P0 re-executes) — every item fails, including `"7"`, because
supplied child inputs are never coerced; the whole batch dies:
```
Type: RuntimeError

Batch 'call' errors:
  [0] Sub-workflow failed at …/child.pflow.md (node 'show'): Input 'n' expects int but received str
      item: '7'
      In step 'call' sub-workflow: Input 'n' expects int but received str

      Suggestions:
        - Change the type annotation to: n: str
        …
To resume from the failed step: pflow resume 5dd09e0a-…
```
**AFTER** — items 0 and 2 succeed (`n` is `7`, `9`); item 1 is one error record; the run is DEGRADED:
```
Batch 'call' completed with 1 failed item (continue):
  [1] Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared `- type: integer`.
      item: 'x'
      At: nodes[id=call].params.inputs.n
      → Pass a whole number from the parent (here ${item} resolved to 'x').
```
**Inline items are authored literals** (`parent-inline.pflow.md`): `"x"` is caught STATICALLY — `--validate-only`
and the run both print the §1.6-shaped error `Step 'call' passes 'x' to input 'n' of ./child.pflow.md, declared
\`- type: integer\`. At: nodes[id=call].params.inputs.n` before anything runs; the routable per-item path above is
for values the run produces.

Non-batch (default `error_action`): the same sentence as the run's error, `At: nodes[id=call].params.inputs.n`,
`Sub-workflow: ./child.pflow.md`, and — because a step before `call` may have run — the resume line stays when
`has_resumable_step()` is true (resume overrides are a real remedy there). JSON: `context` carries `input`,
`declared_type`, `received`, `source: "parent"`, `path`, `sub_workflow_path`, `sub_workflow_step`.

### 1.6 (c) — a declared `string` used as a container

**BEFORE** (`container.pflow.md v='{"a":1}'`): `✓ Workflow is valid`; the run prints `1 fallback` — `${v.a}`
re-parsed the string; `${v.b ?? "fallback"}` fell through silently.

**AFTER** (validation ERROR; `--validate-only`, `save`, run agree):
```
Error: Validation Error

Input 'v' is declared `- type: string`, so `${v.a}` cannot read a field of it — a string input is never
JSON-parsed.
  At: nodes[id=show].params.env.A

  → Declare `- type: object` if 'v' holds a JSON object, or reference `${v}` whole.
```
For the `??` operand (R3): same message for `${v.b ?? "fallback"}` plus one sentence: `As a ?? operand the
fallback would always win.`

Container target (code `inputs:` annotated `dict`, a registry dict param, `batch.items`):
```
`${v}` feeds inputs.data (annotated dict), but input 'v' is declared `- type: string` and is never JSON-parsed.
  At: nodes[id=show].params.inputs.data
  → Declare `- type: object` for 'v', or annotate `data: str` to receive the text.
```
`batch.items: ${v}` → "`batch.items` needs a list; input 'v' is declared `- type: string` and is never
JSON-parsed. → Declare `- type: array` for 'v'."

### 1.7 (c) — a path certain to miss on a declared root

```
Input 'items' is declared `- type: array`; `${items.name}` names a field, but an array has only indexes
(`${items[0].name}`).
Input 'cfg' is declared `- type: object`; `${cfg[0]}` indexes it, but an object has only fields (`${cfg.name}`).
Input 'count' is declared `- type: integer`; `${count.x}` cannot read a field of a number.
```
Each `At:` the surface path; each `→` names the whole-root form or the matching accessor. `any`/untyped roots
are never checked (today's traversal parse stays for them).

### 1.8 Pass 9 suggestion fix (pre-existing wrong text, same site)

**BEFORE:** `Or change the workflow input declaration for 'v' to '- type: dict' (currently str)` — `dict` is not
a legal `## Inputs` type (the schema rejects it with "Use 'object'").
**AFTER:** `… to '- type: object' (currently string)`.

### 1.9 Input named like a batch alias (D11 f)

```
Input 'item' has the same name as the batch alias of step 'call' — inside that step `${item…}` is the batch
item, never the input.
  At: inputs.item
  → Rename the input, or set `as: entry` under the step's `batch:` and update its item references.
```
(The authored field is `batch.as`; `item_alias` is the compiled name and is not valid IR.)

### 1.10 Resume of a lenient-era trace

```
Error: Invalid input value

Input 'count' is declared `- type: integer` but received 'abc' recorded by the run being resumed.
  At: inputs.count

  → Override it: pflow resume 5dd09e0a-… count=3
```

### 1.11 Whole-map `inputs:` that is JSON text (message gains its fix; behaviour unchanged)

**BEFORE:** `Workflow node's 'inputs:' resolved to str, expected dict of child inputs.`
**AFTER:** `Step 'call': 'inputs:' resolved to text, expected a map of child inputs. If the text is JSON, have the
producing step emit a structured value (code \`result: dict\`) or list the inputs as keys under 'inputs:'.`

### 1.12 `--validate-only` with values (new; #297's type/extras half)

```
$ pflow typed.pflow.md topics=tea BOGUS=1 --validate-only
Error: Invalid input value
Input 'topics' is declared `- type: array` but received 'tea' from the command line.
  At: inputs.topics
  → Pass a JSON array (e.g. ["a", "b"]): topics='["tea"]'

Error: Validation Error
Unknown input 'BOGUS' — not declared by this workflow.
  At: inputs.BOGUS
  → Available inputs: topics, count, flag
```
(exit 1; with no values at all: `✓ Workflow is valid` as today.)

### 1.13 `any` inputs (no message — behaviour)

**BEFORE** (`anyin.pflow.md`): `02134` → `int:2134`, `1.10` → `float:1.1`, `[1, 2]` → `list:[1, 2]`.
**AFTER:** `02134` → `str:'02134'`, `1.10` → `str:'1.10'`, `42` → `int:42`, `true` → `bool:True`,
`{"a":1}` → `dict:{'a': 1}`, `[1, 2]` → `str:'[1, 2]'` (lossless: the spaced text does not read back).

### 1.14 A reference that reaches JSON text inside a declared `object`/`array` input (ruling (i), root-wide)

**BEFORE** (`data` declared `object`, value `{"payload": "{\"a\":1}"}`, step reads `${data.payload.a}`): resolves
`1` — the string descendant is re-parsed mid-path.

**AFTER** (unresolved; strict mode fails the step; today's renderer would say only `'data' has no 'payload.a' /
Available fields: payload`, which is true and useless — so the message gains the reason):
```
Error: Template Resolution Failed

Unresolved variables in parameter 'env': ${data.payload.a}
  → 'data.payload' is text ('{"a":1}') — a declared input is never JSON-parsed, so there is no field 'a' to
    read. Nest the object in the input (`{"payload": {"a": 1}}`), or parse the text in a code step
    (`json.loads(payload)`).
```
JSON/context: `text_not_parsed: "data.payload"` beside the existing `unresolved_references` entry. A plain
missing field (`${data.nope}`) keeps today's text.

### 1.15 Analyzer surfaces (same §1.1 text; routing is what changes)

`pflow analyze-cache wf count=abc` → §1.1's error in text, and with `--format=json` the JSON envelope of §1.4
(not the group handler's plain text). MCP `workflow_analyze` with `{"count": "abc"}` → the structured
diagnostic (not `RuntimeError("❌ Cache analysis failed: …")`). `pflow analyze-cache wf` with a required input
omitted still analyses (DD#35).

## 2. Rulings

- **R1 — title.** `Invalid input value` for every boundary error (argument, stdin, env, settings, default,
  recorded, call, parent). Alternative: reuse `Validation Error`. Recommendation: the distinct title — an agent
  greps it; the category stays `validation`.
- **R2 — source clauses** as tabled in §1.2. Alternative: omit the clause for `argument`/`call` (the caller
  supplied it). Recommendation: keep it everywhere — one sentence shape, and resume/MCP/CLI logs read the same.
- **R3 — `??` operand sentence** ("As a ?? operand the fallback would always win"). Recommendation: yes.
- **R4 — settings fix command.** `pflow settings set-env <name> <value>` (verified against `pflow settings
  --help`). No ruling needed.
- **R5 — truncation at 80 characters** of `received`, `…` appended; sensitive names → `<REDACTED>` in the
  message AND the fix line uses the type's canonical example (never the value). Recommendation: 80.
- **R6 — the §1.14 reason text** for a protected JSON-text descendant. Alternative: keep today's bare
  "has no 'payload.a'" line. Recommendation: the reason + two remedies — the old line is true but gives an
  agent nothing to do.
