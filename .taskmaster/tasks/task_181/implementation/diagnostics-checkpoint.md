# Task 181 — diagnostics checkpoint (show before code)

> **RULED 2026-10-07** — user: *"181: all yes"* on the main orchestrator's plain-language relay. R1 (four params), R2,
> R3 ("instead of"), R4 (7a + 7b), R5, R6 (`json.dumps`, default separators, `ensure_ascii=False`), R8 (nouns
> "Embedded code" / "JSON insert" — CONTEXT.md written by the main orchestrator at merge) — ALL as recommended.
> This file is the ruled text.

Every message this task adds or changes, the rule that decides when each fires, and the run-time
text the MCP tool receives. **BEFORE** blocks are verbatim output of today's code (`ebf7cab2`,
macOS, `uv run pflow --validate-only <probe>`; run-time text comes from
`pflow.core.templates.resolve`, executed — no MCP server needed, no paid call). **AFTER** blocks
are drafts — nothing is built — in the renderer's real layout (ERRORs print first as
`Error N: Title` / message / `At:` / `→` fix; WARNINGs follow as indented `⚠ [step] …` lines with
their `→` lines, as in the §4 BEFORE). Probes are reproduced inline (each step and input also
carries the one-line description the parser requires; omitted here). The drafts were reviewed by
the plan battery (agent-ux, silent-failures, validation-consistency lenses) and revised.

**Rulings asked: R1–R6 and R8. R7 is a note.**

---

## 1. Where the rule applies — the code-bearing set (R1)

A param is **embedded code** when the step's type is `mcp-<server>-<tool>` and `(tool, param)` is
one of these **JavaScript** params (the membership criterion: a param whose text another process
runs as JavaScript — `|json` produces JavaScript/JSON literals, so a SQL or Python param would
need its own rule):

| Tool (any server name) | Param | Seen where |
|---|---|---|
| `evaluate_script` | `function` | chrome-devtools; the in-tree screenshot workflows; #550 |
| `navigate_page` | `initScript` | chrome-devtools (registered locally) |
| `browser_evaluate` | `function` | playwright (registered locally) |
| `browser_run_code_unsafe` | `code` | playwright; #621 |

Matched as a suffix of the type string (`mcp-` prefix, `-<tool>` suffix): the server name is
user-chosen (`chrome-devtools`, `chrome-devtools-isolated`, `playwright-isolated` are all
registered here). **Failure modes:** a JavaScript tool not in the table stays strict — today's
behaviour, the author escapes with `$${` (safe). A different server's tool that shares one of
these names *and* the param name is treated as embedded code: its bare `${x}` passes through, and
§4 reports any in-scope root (loud, not silent).

**R1 — accept the four?** *Recommended: yes.* Adding a tool later silently changes what an
existing bare `${x}` in it means. Adding it now changes nothing, because none of the last three is
used in this repo. Alternative: only `evaluate_script.function`, the one observed in use.

---

## 2. A value goes into JavaScript — `${title|json}`

Probe `p1`: input `title` (string); step `click`, `type: mcp-chrome-devtools-evaluate_script`,
`- function: |` → `() => { const title = ${title|json}; return title; }`.

**BEFORE** (rejected — `|` is not in the grammar):

```
ERROR: Found 1 malformed template(s)
✗ Validation failed (1 error):

Error 1: Template Error

Malformed template syntax: found 1 '${' but only 0 valid template(s).
  At: node 'click', nodes[id=click].params.function

  → '${title|json}' is not a valid template. A reference is ${node.field}: index a list as items[0] (not items.0), close every '${' with '}', and write '$${' for a literal '${'.
```

The in-tree form instead (`const t = '${title}';`), resolved today with `title = "Don't Stop"`,
gives `const t = 'Don't Stop';`, a JavaScript SyntaxError inside the tool (#550). A boolean today
gives `const on = ${flag};` → `const on = True;`.

**AFTER:** `✓ Workflow is valid`. The tool receives the value as a JavaScript value **of the
value's own type**:

| Value in pflow | Text inserted |
|---|---|
| `"Don't Stop"` | `"Don't Stop"` |
| `true` / `null` / `3` | `true` / `null` / `3` |
| `{"a": [1, 2]}` | `{"a": [1, 2]}` |
| `"é ✓"` | `"é ✓"` (not `é`) |
| a shell step's `stdout` `42\n` (text) | `"42\n"` — a string; the guide shows `JSON.parse(${up.stdout\|json})` for JSON text |

**R6 — the JSON text form.** *Recommended:* `json.dumps(value, ensure_ascii=False)`. That means
default separators (`{"a": [1, 2]}`, the spacing `${x}` already gives a dict inside a string) and
non-ASCII kept readable. A value JSON cannot encode (a set, bytes) falls back to the JSON string of
its ordinary text form, as `to_string` already does. A text value is never re-parsed, so JSON text
stays a string. Alternative: `ensure_ascii=True`, which gives pure-ASCII output and is harder to
read in traces.

**R5 — spacing.** *Recommended:* `${title | json}` is accepted (`??` already tolerates spaces
around it). Near-misses (`${title|json }`, `${ title|json}`, `${title|JSON}`) get §7b's error
rather than reaching JavaScript verbatim. `${title|jsn}` is not flagged: in JavaScript it is a
bitwise or.

---

## 3. JavaScript's own `${…}` passes through untouched

Probe `p2`: input `user` (object); step `read`:
`` () => { const a = 1, b = 2; return `${a + b} ${user.name}`; } ``.

**BEFORE:**

```
ERROR: Found 1 malformed template(s)
✗ Validation failed (1 error):

Error 1: Template Error

Malformed template syntax: found 2 '${' but only 1 valid template(s).
  At: node 'read', nodes[id=read].params.function

  → '${a + b}' is not a valid template. A reference is ${node.field}: index a list as items[0] (not items.0), close every '${' with '}', and write '$${' for a literal '${'.
```

Without the `${a + b}` the workflow is valid today, and at run time `${user.name}` is **silently
replaced** by the pflow input. That is the collision ADR-0016 records.

**AFTER:** both template literals reach the tool exactly as written. Because `user` is a pflow
input whose only use is this bare `${user.name}`, §4a's ERROR fires.

Probe `p8` (`` () => { const price = 5; return `Total: $${price}`; } ``):
- **BEFORE:** valid, and the tool receives `` `Total: ${price}` ``. The escape collapses, so
  JavaScript prints `Total: 5`.
- **AFTER:** valid, and the tool receives `` `Total: $${price}` `` unchanged, so JavaScript prints
  `Total: $5`. Everything outside a `${…|json}` is sent as written.

---

## 4. A pflow name written bare inside embedded code (R3)

The detector finds every `${…}` in embedded code that parses as a pflow reference (not an insert)
whose root is in **this step's scope**:
- a declared workflow input;
- a key of the step's own `inputs:`;
- the batch alias or `__index__` (on a batched step);
- `__iteration__` (on a looped step);
- a step id, but only when a field follows it (`${fetch.result}`, never a bare `${fetch}`).

It never fires on `${a + b}`, on a `${i}` that is not a pflow name, or on `${x|json}`.

Today's warning layout (probe `p11`, executed):

```
✓ Workflow is valid
  ⚠ [s] Nested access on 'str' requires valid JSON at runtime. Non-JSON strings cause 'Unresolved variables' error.
    → Ensure the value is valid JSON at runtime.
```

**4a — ERROR, instead of the unused-input error, when a declared input is used nowhere else.**
This is the unconverted in-tree form. Probe `p5`: input `selector`, `const sel = '${selector}';`.

**BEFORE:** `✓ Workflow is valid`, and an apostrophe in the value breaks the JavaScript at run
time.

**AFTER** (the input is not reported as unused; this one error replaces that report):

```
✗ Validation failed (1 error):

Error 1: Template Error

Input 'selector' is never inserted: its only use, '${selector}' in 'function', is JavaScript text that pflow sends to the MCP tool unchanged.
  At: node 'click', nodes[id=click].params.function

  → Replace '${selector}' (the quotes too) with ${selector|json} — the value arrives already quoted: const sel = ${selector|json};
```

When the reference is not wrapped in quotes (probe `p2`'s `${user.name}`, inside a template
literal), the fix line is:
`→ Put ${user.name|json} where a JavaScript value goes, outside any quotes or `…`: const name = ${user.name|json};`

**4b — WARNING for every other in-scope name.** The root might be the author's own JavaScript
variable, so this is not an error. Probe `p7`: a batched step whose JavaScript uses its own arrow
parameter `item`, `` () => [{id: 7}].map((item) => `${item.id}`) ``.
- **BEFORE:** valid, and at run time `${item.id}` is silently replaced by the batch item's `id`.
- **AFTER:** valid, sent unchanged, plus:

```
✓ Workflow is valid
  ⚠ [rows] ${item.id} in 'function' is JavaScript: pflow sends it unchanged, so the batch item is not inserted.
    → To insert it, put ${item.id|json} where a JavaScript value goes, outside any quotes or `…`: const id = ${item.id|json};
    → If 'item' here is your JavaScript variable, the code is correct — write ${ item.id } (spaces inside the braces) to clear this warning.
```

Several matches in one param give one warning: the message lists them in source order, followed by
one `→` line each and the closing "your JavaScript variable" line.

**4c — the whole param is one bare reference** (`- function: ${gen.code}`; see R7). The WARNING
names the only form that works:
`→ A program produced by a step is text, not code: run it with eval — () => eval(${gen.code|json})()`

**4d — WARNING: an insert left inside quotes** (`const sel = '${selector|json}';`). This is the
likely half-converted form. It is valid JavaScript but sends `'"#main"'`.

```
  ⚠ [click] '${selector|json}' in 'function': the insert is already a quoted JavaScript value, so these quotes become part of the text ('"#main"').
    → Remove the quotes around it: ${selector|json}
```

The check looks only at the characters immediately outside the insert (matching `'…'`, `"…"`).
An insert inside a longer template literal (`` `Hello ${name|json}` ``) is not detected; the guide
says so.

**R3 — accept the rule, the wording, and "instead of"?** *Recommended: yes.* That gives one
diagnostic per mistake, the model Task 118 uses for leftovers in shell bodies. The draft first
proposed reporting the old unused-input error alongside a warning; the review showed its first
numbered fix, "Remove unused declarations", deletes the input, after which the bug goes silent.
Alternative: flag every grammar-shaped `${…}` regardless of scope. That catches a misspelled input
name, but warns on most JavaScript template literals.

---

## 5. `|json` anywhere else (R2)

Probe `p3`: step `ask`, `type: llm`, `- prompt: Echo ${x|json}`.

**BEFORE:**

```
ERROR: Found 1 malformed template(s)
✗ Validation failed (1 error):

Error 1: Template Error

Malformed template syntax: found 1 '${' but only 0 valid template(s).
  At: node 'ask', nodes[id=ask].params.prompt

  → '${x|json}' is not a valid template. A reference is ${node.field}: index a list as items[0] (not items.0), close every '${' with '}', and write '$${' for a literal '${'.
```

**AFTER** (it parses now, so the message says what it is and where it is allowed; the validator's
first log line is reworded because "malformed" is no longer true for every error it counts):

```
ERROR: Found 1 template error(s)
✗ Validation failed (1 error):

Error 1: Template Error

${x|json} is accepted only in JavaScript passed to an MCP tool: the 'function' param of an mcp-<server>-evaluate_script or mcp-<server>-browser_evaluate step, 'initScript' of mcp-<server>-navigate_page, 'code' of mcp-<server>-browser_run_code_unsafe.
  At: node 'ask', nodes[id=ask].params.prompt

  → Remove '|json': write ${x}. A dict or list is already inserted as JSON text.
```

The suggestion is the author's text with the suffix removed (`${a ?? "d" | json}` → `${a ?? "d"}`;
on an output `source` written bare, `x|json` → `x`). The same error appears on every surface that
is not embedded code (`batch.items`, a loop condition, an output `source`, a `## Cache` variable).
On a loop condition the existing loop-shape error also fires, as it does for any non-simple
condition today.

**Run time, for a workflow that skips validation** (a dict IR compiled directly, or a dynamic
child): a misplaced insert is treated like an Issue. Outcomes per surface:
- a node param fails in strict mode;
- `batch.items` and an output source fail;
- a loop condition reads as false;
- a `## Cache` chunk is dropped.

These are today's outcomes for an Issue on those surfaces. Every CLI, MCP and web entry validates
first, so none of them sees this.

**R2 — accept?** *Recommended: yes.* Alternative: honour `|json` at run time everywhere and reject
it only in the validator. That is one fewer branch, but `--validate-only` and a compile-only run
would then disagree.

---

## 6. A mistyped reference inside an insert — probe `p6`: `- function: () => ${nod.result|json}`

**BEFORE:** §5's malformed-template error (not grammar yet).

**AFTER:** today's unknown-node errors, exactly as a bare `${nod.result}` gets them now (probe
`p9`, executed below). The only difference is that every template and every suggestion keeps
`|json`: a suggestion like `Did you mean ${nodes.result}` would paste back as bare JavaScript, so on
an insert it reads `${nodes.result|json}`.

```
WARNING: Template validation found 1 errors
✗ Validation failed (2 errors):

Error 1: Validation Error

Node 'click' references non-existent node 'nod' in parameter 'function'.
  At: node 'click', nodes[id=click].params.function

  Available nodes (showing 1 of 1):
    - click

Error 2: Template Error

Template variable ${nod.result|json} has no valid source — '${nod}' is neither a workflow input nor a node ID in this workflow.
```

The run reaches the same errors (the run path validates first; for a dict IR, the compiler's own
data-flow check reports Error 1). At run time, an unresolved insert (for example, from a step on a
skipped branch) reports `Unresolved variables in parameter 'function': ${up.missing|json}`, and
its did-you-mean and `??` fixes carry `|json`.

---

## 7. An insert pflow cannot see (R4)

### 7a. Inside `$${…}` or inside a JavaScript `${…}`

Probe `p12`: input `count` (number), `` () => `cost: $${count|json}` ``. The author wants a
dollar sign followed by the value, but pflow reads `$${` as an escape. The same thing happens to
`` `${${count|json} + 1}` ``, which pflow reads as one unrecognised `${…}` that swallows the
insert.

**BEFORE:** the input is unused because the escape swallowed it, and the tool would receive
`` `cost: ${count|json}` `` (a JavaScript ReferenceError):

```
WARNING: Found 1 unused inputs
✗ Validation failed (1 error):

Error 1: Validation Error

Declared input(s) never used as template variable: count
  At: inputs

  → Remove unused declarations from '## Inputs' or reference them in a node parameter.
```

**AFTER.** This is the only error: template-syntax errors end template validation early, so the
unused-input report does not also appear.

```
ERROR: Found 1 template error(s)
✗ Validation failed (1 error):

Error 1: Template Error

${count|json} in 'function' sits inside '$${…}', which pflow sends to the MCP tool as written — so the value is never inserted.
  At: node 'cost', nodes[id=cost].params.function

  → Insert it where a JavaScript value goes, outside any '${…}': const count = ${count|json}; — then use count in the JavaScript.
```

For the JavaScript `${…}` case the message reads `… sits inside another '${…}' ('${${count|json} + 1}'), which pflow sends …`.

### 7b. A near-miss spelling

Probe: `const t = ${title|json };`. Today this is a malformed-template ERROR. Under the new rule
it would be JavaScript and reach the tool verbatim (a SyntaxError).

**AFTER:**

```
Error 1: Template Error

'${title|json }' in 'function' is not a pflow insert (a space before '}'), so it would be sent to the MCP tool as JavaScript, unchanged.
  At: node 'click', nodes[id=click].params.function

  → Write ${title|json}
```

The check fires for an unrecognised `${…}` in embedded code that becomes an insert once the
whitespace at its ends is trimmed and the word after its last `|` is lower-cased. The `(…)` reason
names the difference (`a space after '${'`, `'JSON' must be lower-case`).

**R4 — accept 7a and 7b?** *Recommended: yes.* The spec requires 7a, and 7b closes the same hole
for typos.

---

## 8. Notes

**R7 (note): a whole program can no longer come from an upstream step.** Today
`- function: ${gen.code}` works (an LLM writes the JavaScript). Under the settled rule a bare `${…}`
is JavaScript:
- `${gen.code}` is sent as that literal text;
- `${gen.code|json}` sends a string literal, not a program.

Nothing in this repo or in the issues does this. The working form is
`- function: () => eval(${gen.code|json})()`, which the guide and §4c show. That form is refused on
one path: MCP `registry_run` rejects any param containing `eval(`, a pre-existing rule filed as a
follow-up. A page's Content-Security-Policy may also forbid `eval`. A whole-value exception would
restore the old behaviour syntactically but contradicts the ruling "a bare `${…}` is always the
embedded language", so it is not planned.

**R8 (ruling, because the noun reaches the wire contract `RFParam.mode` and the code):** nouns for
`context/CONTEXT.md`, where "filter" is an avoid-word. Proposed, for the main orchestrator to write:
- **Embedded code** — the program text of an MCP tool param that another process runs as
  JavaScript (`evaluate_script`'s `function`). It is sent as written; a `${…}` in it belongs to
  JavaScript, except a JSON insert. _Avoid_: code param, script param, raw param, code body (that
  is the shell/code-step term).
- **JSON insert** — `${x|json}`: a template expression whose value enters the text as a JSON
  literal (`"Don't Stop"`, `true`, `null`, `{"a": 1}`) rather than as plain text, so it is
  quote-safe in JavaScript. Accepted only in Embedded code. _Avoid_: filter, pipe, encoder.
- **Template** — amend (beside Task 118's "A Code body is never a Template"): "In Embedded code
  only JSON inserts are Template expressions."
- **Issue** — append: "In Embedded code a `${…}` that is not a JSON insert is JavaScript, not an
  Issue."

Code names follow the ruled nouns: `ParamMode` value `"embedded"`, `templates.embedded_code`,
`Expression.as_json`.

**Behaviour changes with no diagnostic** (for the hand-back to the user):
- A workflow that followed the current docs and wrote `$${…}` in JavaScript to get a JavaScript
  `${…}` now sends `$${…}`, which is a `$` followed by the interpolation. No in-tree or saved
  workflow on this machine does this.
- A JSON insert of text that holds JSON (shell `stdout`) is a JavaScript string, not an object.
