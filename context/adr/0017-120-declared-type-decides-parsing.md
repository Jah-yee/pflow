# A value's type is decided once, by the declaration of what receives it — never re-inferred

pflow auto-parses JSON-looking text when a template resolves (`core/templates._resolve_string`:
a simple `${x}` whose value is a string is passed through `try_parse_json` when `auto_parse` is on,
and a dict/list param's string leaves likewise), so that `${fetch.stdout}` from a shell step can feed
a code step's `dict` input without ceremony. The same parse re-typed values that were already
declared: a `type: string` workflow input holding `{"a":1}` arrived at a code node as a dict (#686),
and the CLI guessed a type for every `key=value` token before the workflow's declarations were
known (`cli/param_parsing.infer_type`: `02134` → `2134`, #687). Task 120 decides: **the type of a
value is fixed once, where it enters, by the declared type of what receives it** — a workflow
input's `## Inputs` type, a code step's `inputs:` annotation, a shell step's `env:` (text, ADR-0016)
— and a reference whose root is a declared non-`any` input is never JSON-parsed downstream. The
parent therefore stops auto-parsing a sub-workflow step's `inputs:`; the child's declaration types
each value at its own boundary. Upstream step outputs keep today's auto-parse: their producers' declarations (`stdout: str`, a code
`result: str`) are deliberately NOT treated as a type to preserve, and the guide's promise about them stands —
except where the CONSUMER declares text (a child `string` input, a code `str` annotation, `env:`). The
protection is root-wide: a string descendant of a declared `object`/`array` input is never re-parsed either
(user ruling 2026-10-10, Task 120 decision (i)).

## Considered Options

- **Exempt declared inputs by NAME on the resolver** (the compiler passes the input names) —
  rejected: `type: any` and untyped inputs rely on the traversal parse (`${data.a}` on a piped
  JSON string), a node's own `inputs:` keys can shadow a same-named input in the resolution context,
  and only `string` actually needs the rule once every other declared type is typed at the boundary.
  The exemption is keyed on "root is a declared `string` input".
- **Tag the VALUE at entry** (a `str` subclass the resolver recognises) — rejected: it leaks through
  pass-through outputs (`result: str = s`), so `${code.result}` would silently stop auto-parsing; and every
  JSON round trip (trace, memo cache) drops the tag, so each re-entry point (resume, cache hit) must restore it
  — possible, but a second mechanism to keep in step with the declarations that already carry the information.
- **Stringify what the parent already parsed** so a child `string` input still gets text — rejected:
  `json.dumps` re-spaces and re-escapes the author's bytes (`{"b": 1.10}` → `{"b": 1.1}`), which is
  #687 again at a different seam.
- **Extend Task 118's `parses_leaves(template_config, key)`** (new arguments, wire the `inputs:` branch to
  it) — not chosen: as it stands it decides per PARAM, is not consulted on the `inputs:` branch where #686
  lives, and cannot see a leaf's reference root; extending it means passing the reference into an engine-side
  predicate the resolver in `core/templates` would call back — the policy belongs beside the leaf rule it
  governs. Its own comment (`core/workflow/template_surfaces.py`) names the replacement as the intended direction.

## Consequences

- `${input}` and `${step.stdout}` now differ: a reference rooted in a declared non-`any` input is never
  re-parsed, while an upstream output is — unless its consumer declares text. The guide
  (`guide/core.md` "Simple templates automatically parse JSON strings") and both MCP instruction
  copies say the opposite today and change with the task.
- A sub-workflow caller passing an LLM or shell output into a child `string` input no longer depends
  on whether that text happens to look like JSON (fifteen in-tree bindings have that shape).
- The CLI's `key=value` parser returns raw text for every workflow-input command; type inference
  survives only for `type: any` / untyped inputs (lossless: typed only when the result reads back as
  the same text) and for `pflow probe`'s node params, which have no declaration.
- Task 181's `${x|json}` and this rule share the one leaf-policy carrier on `core/templates.resolve`.
