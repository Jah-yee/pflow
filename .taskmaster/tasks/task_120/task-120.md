# Task 120: Declared Input Types Are Honoured — Strict at the Boundary, Never Re-Inferred

## Description

A workflow's `## Inputs` declare a type for each input, but today that type is consulted once,
leniently, and then forgotten: a value that cannot be coerced only logs a warning and passes
through; the CLI guesses a type for every token before the declarations are known; and every
later hop re-guesses the type from the value. Make the declared type hold at every boundary a
value crosses: decide the type once, where the value enters, from the declaration of what receives
it; fail with an actionable error; never re-infer it downstream.

## Status
not started

## Priority

medium

## Roadmap

next

> **Rewritten 2026-10-07 against main `45e15e2e`** from a seven-lens spec battery plus a six-lens
> cross-model pass (ledger: `scratchpads/session-12/task-120-spec-battery.md`, local), then a context-free
> cross-model re-read of the rewrite (folded; its three decisions (i)–(iii) RULED 2026-10-10, below). The
> decisions in the Decisions section are **DECIDED** by the user on 2026-10-07. Task 118 Part 2 is merged (`1d393487`); launch-ready for a
> planner, in coordination with Task 181 (same resolver arm — 181 builds first and adds an `embedded` leaf policy; this
> task's planner designs ONE policy carrier that subsumes it, never a second flag).
> Owns #686 and #687 (user ruling 2026-10-06).

## Problem

The rule (user ruling 2026-10-06): *a declared input type is honoured at every boundary the value
crosses.* Executed on `b2cd92e3` — `--validate-only` printed "✓ Workflow is valid" for 1–3 and 9:

1. `type: array` given `topics=tea` → run: `WARNING: Cannot parse string as JSON array`, then
   `batch items must be an array, got str`. `type: boolean` given `maybe` → warning, then the code
   node fails `expects bool but received str`. A `type: number` given `abc` with no annotated
   consumer: warning, **exit 0**, the string flows on.
2. **#686** — `type: string` given `{"a":1}` or `[1,2]` reaches a code node as dict / list. Same
   through byte-exact stdin and through MCP `workflow_execute`.
3. **#687** — `type: string` given `02134` arrives as `2134` (CLI and web UI only; MCP is intact);
   `true` → `"True"`; JSON text is re-spaced.
4. `type: integer` silently accepts `3.0`, `3.5`, `1e3`, `true`.
5. `type: boolean` given `0` / `1` arrives as int, no warning.
6. `type: number` given `007` → 7, `1e3` → 1000.0.
7. `type: object` given `[1,2]` → a list, no warning (non-string values are never checked);
   `type: array` given `{"a":1}` likewise.
8. `type: any` given `02134` → int, `{"a":1}` → dict.
9. `${v.a}` on a `type: string` input validates and resolves.
10. A sub-workflow's supplied inputs are coerced once at the child's first compile, but execution then
    overwrites them with the raw supplied values (`workflow_executor.py:~419-433`): a child `s: string` given
    `{"a":1}` receives a dict; `n: integer` given `"7"` receives the string.
11. `pflow resume <id> zip=02134` and `--only … zip=0099` deliver `2134` / `99` — the same CLI
    parse as #687 on two more commands (`resume_source` seeds node outputs only; inputs come from
    the invocation).
12. An invalid declared `## Inputs` **default** is never REJECTED (it is pre-filled, then leniently coerced like
    a supplied value): `- default: abc` on an
    `integer` passes `--validate-only` and runs; `- default: 1.10` on a `string` arrives as `'1.1'`
    because YAML re-types the literal before pflow sees it.

**Out of this task** (ruled 2026-10-07): the YAML re-typing of literals in node params and defaults
(`1.10` → `1.1`, `0755` → `493` in a flow map, `02134` → `1116` read as octal) happens in the
parser, in two re-typers that disagree (`_coerce_yaml_scalar` for one-line bullets, PyYAML for flow
and block YAML), and no later layer can see the raw text. It is its own issue, **#742**. This task checks defaults against their declared type (break 12
above) but does not try to recover the author's spelling.

## The rule, in one sentence (DECIDED)

A value's type is decided **once, where it enters**, by the declared type of what receives it — a
workflow input's `## Inputs` type (CLI argument, stdin, env, settings, `default:`, MCP, the web form,
a sub-workflow's `inputs:`, a resume replay), a code step's `inputs:` annotation, a shell step's
`env:` (Task 118: text) — and **nothing downstream re-infers it**: a reference whose root is a
declared non-`any` input is never JSON-parsed again.

## Decisions (DECIDED 2026-10-07 — user: *"go ahead with all abc as proposed"* on this revised set)

- **(a) Fail, never warn**, when a value cannot be coerced to its declared type. Exit 0 with a
  wrong-typed value is the bug. (A consequence of the 2026-10-06 ruling, stated for completeness.)
- **(b) Accepted text, strict ASCII grammar**, one home beside `TypeSpec` (`core/types.py`):
  `integer` = `-?[0-9]+`; `number` = a JSON number (so `1e3` and `3.0` are numbers, `nan`/`inf`/`1_000` are not; integer text yields an `int`); `boolean` = today's set `true/false/yes/no/
  1/0`, case-insensitive (`param_coercion._coerce_to_boolean` is the current behaviour; a `0`/`1`
  text is a boolean ONLY for a declared `boolean` — node params such as `confirm_delete` are
  untouched); `object`/`array` = JSON text of that shape; surrounding whitespace is stripped before
  matching a TYPED parse (stdin arrives as `"42\n"`) — never from a declared `string`'s value, and never from the
  spelling (d)'s lossless comparison reads back. Loose is the irreversible direction; the grammar may widen
  later.
- **(c) A declared `string` used as a container** (`${v.a}`, `batch.items: ${v}`, into a code
  `x: dict`) is a **validation error** — including as a `??` operand. Relaxing later is cheap.
- **(d) `type: any` and untyped inputs: lossless inference from TEXT sources only.** A CLI / web-form
  token is typed only when the result reads back as the same text (`true`, `42`, `[1]` become typed;
  `02134`, `1.10`, `0755` stay strings). MCP and sub-workflow callers pass typed JSON, which is left
  as it arrives. An input with no `type:` behaves as `any` (today's readers disagree — unify on `any`).
- **(e)+(f) One rule: the consumer's declared type decides parsing.** The parent **stops auto-parsing
  a workflow step's `inputs:`**; the child's own boundary coerces each value from its `## Inputs` type,
  per batch item, as a routable error. A code step's `inputs:` key annotated `str` receives the raw
  text (the annotation is read at compile time, not in the node's `prep`). Upstream-output
  auto-parse everywhere else is unchanged.
- **(f₂) The env-var-loses-to-its-own-`default:` bug is IN scope** — the default pre-fill that causes
  it is also what erases a value's source, which the error must name; the web-UI preflight and the
  CLI run disagree on it today (`PORT=abc` + `default: 8080` → UI 400, CLI succeeds).
- **(h) A non-string value arriving for a declared type** (MCP JSON `123` for a `string`; a parent's
  `int` into a child `string`; a YAML-typed default): a `string` accepts any **scalar**, rendered by
  `core/templates.to_string` (the same text `${x}` produces in a string — Task 118's rule, so a
  boolean renders `True`); `integer` accepts `int` (not `bool`); `number` accepts `int` or `float` (not `bool`, as `TypeSpec.accepts` already rules);
  `boolean` accepts `bool`; `object`/`array` accept their own shape; a container into a `string`
  and everything else is an error. **(g) folds in here**: the `True`-vs-`true` difference between
  `to_string` surfaces (command, prompt, `env:`) and JSON surfaces (stdin, `## Cache` chunks,
  `${x|json}`) is recorded, not changed.

**DECISION FOR THE USER (default: out):** declared **output** types are unchecked today
(`## Outputs` `type: integer` accepts `'seven'`, session-12 dogfood). The same rule applies, but it
is a new boundary with its own readers (`describe`, the web UI, sub-workflow `## Outputs`). Default:
out of this task — filed as **#743** (builds after this task, sharing its coercer); the planner builds nothing for it.

## Design (constraints the plan must satisfy; the HOW is the planner's)

**One strict coercer**, `declared type + value → typed value | diagnostic`, replacing the log-and-
return branches of `core/param_coercion.coerce_workflow_input` (`:116-209`): text goes through the
(b) grammar, a non-text value through (h), `None` is an error for a required input and stays `None`
for an optional one (today `_coerce_provided_input` returns `None` before coercing, so MCP `null`
bypasses every check). The `VALIDATION_PLACEHOLDER` passthrough stays (`predict.py:315` pads with it).

**Every entry site calls it** — the inventory (impact-completeness, session-12; re-verify lines):
- `prepare_inputs` (`runtime/compilation/ir_preparation.py` — the only site that changes a value by
  its declared type today) for CLI / MCP / web / resume-replay values **and for declared defaults**,
  which `runner.py:~682` pre-fills as if supplied — the coercer must learn the value's SOURCE
  (argument, stdin, env, settings, default, recorded run) so the error can say it; this is where (f₂)
  is fixed.
- The sub-workflow boundary **per item, in `prep`** (`WorkflowExecutor._validate_child_params`,
  which raises a recoverable `_prep_error` routable by `error_action` and batch `continue`) — NOT in
  the child's compile-time `prepare_inputs` (`_validate_and_compile_child` wraps that as a fatal,
  unroutable `CompilationError`, runs once per cached compile, so only item 1 would be checked). The
  compile-time call coerces the child's defaults only and must be idempotent on already-typed values.
- `--validate-only` with supplied params (#297 parity): the check runs on the USER's params on BOTH
  validation paths — `WorkflowRunner.validate` (`validate_with_placeholder_inputs`) and the run path's
  validation step — before `_fill_declared_defaults` adds `__pflow_declared_<name>__` sentinels. MCP `workflow_validate`
  takes no params, so parity is CLI-only (say so in the docs).
- The analyze paths (`analyze_cache.py:~145`, MCP analyze): check the supplied params with the
  coercer and fail LOUDLY before prediction — today `predict.py:~479` swallows `SchemaValidationError`
  and silently marks every LLM prediction skipped, so (a) would turn a visible warning into silence.

**The CLI never guesses a workflow input's type.** `cli/param_parsing.parse_workflow_params` returns
raw strings for all five workflow-input callers (`run.py`, `resume.py` — which today parses argv
before the target is known, reorder it — `analyze_cache.py`, `ui/server.py` preflight + spawn, which
must build params exactly as the run it spawns); the (d) lossless inference lives in the coercer's
`any`/untyped branch; `_probe_impl.py` has registry param declarations but no WORKFLOW-input declarations and today calls the shared
`parse_workflow_params` — it must explicitly keep the old inference path when that parser changes. The
web re-run prefill (`ui/run_node.read_run_inputs` → `format_param_value`) is the inverse of today's
inference — keep the round-trip true.

**The resolver's no-re-parse rule is a per-reference policy inside `core/templates.resolve`**
(`_resolve_string` holds the leaf rule: `auto_parse and isinstance(value, str)` → `try_parse_json`),
keyed on "this reference's root is a declared non-`any` input" — **root-wide** (ruling (i)): a string
descendant of a declared `object`/`array` input (`${data.payload}` holding JSON text) stays text too; `any`/untyped
keep today's traversal parse. The declared-input names and types reach the resolver on `TemplateConfig` (precedent: `optional_input_keys`, built
at `compiler.py:~320`). Task 118's `parses_leaves(template_config, key)` is **per param and is not
consulted on the `inputs:` branch** (`template_resolution.py:~272`, the #686 site) — the comment at
`core/workflow/template_surfaces.py:27` says Task 120 *replaces* it; do that, do not grow it.
**Every auto-parse site adopts the one policy**: `template_resolution.py` `inputs:` branch (`~272`),
dict/list leaves (`~280`), simple-template-into-container (`~289`); `batch_executor.py` inline items
(`~119`, `~126-130`); the dry-run planner's hand-copied `resolve(..., auto_parse=True)` at
`execution/plan.py:~1587` (plan/run parity is pinned by `test_plan_drift.py`); the validator's child
enumeration (`core/workflow/validator.py:~1801`); path traversal (`core/templates.py:~413-425`).
**Coordinate with Task 181**: its plan adds a leaf policy (`embedded`) on the same `resolve()` /
`_resolve_string` arm — one policy carrier, not two; whichever lands second adapts.

**The code-step `str` annotation is read at compile time** into `TemplateConfig` (the node reads it
only in `prep`, after the resolver has parsed; precedent `compiler.py:~320`). RESOLVE AT START:
which annotations count as text (`str`, `str | None`, `Optional[str]`; a union with a container
does not). The agent node's `inputs:` hits the same branch — same rule.

**The validator** implements (c) keyed on the reference's ROOT KIND at `template_validation/
type_checker.py:~41-44` — never by editing `TYPE_COMPATIBILITY_MATRIX` (`core/templates.py:~89`),
whose `"string"` row is shared with code `result: str` outputs and child `## Outputs`. Surfaces:
Pass 5 paths (`path_validation.py:~120`, break 9's real gate), Pass 6, Pass 9, `batch.items`, output
sources, loop fields, and `??` operands (`ROOT_ONLY` today — a field path on a declared SCALAR input (`string`/`integer`/`number`/`boolean`), a field name on a declared
`array`, or an index on a declared `object` is CERTAIN to miss, so those are checked even there (`any` and
untyped are never checked; `${items[0] ?? "x"}` on an `array` stays legal); otherwise `${v.a ?? "x"}` becomes a new silent
fallback). Literal child `inputs:` values are checked statically in `_check_required_inputs`;
declared defaults are checked at validation (path `inputs.<name>.default`); the dry-run planner's
item-1-defaults-overwrite-every-item bug (`plan.py:~592`) is fixed alongside, since (e)+(f) makes it
fire on every coerced key.

**The error is a Diagnostic** built at the point of detection (Task 147 precedent; shared context
keys with Task 112 — NOT `TypeSpec`, which rejects 112's Python-style names), with `path`, `input`,
`declared_type`, `received` (masked via `security_utils.mask_sensitive_value` for sensitive-named
inputs, truncated when long), `source`, `accepted`. When several inputs fail, each keeps its own
suggestion and path (today `compile_validation.py:~55` collapses them). A pre-execution failure
prints no resume hint and emits no `resume_command` (already true: both gate on
`has_resumable_step`); a CHILD-input failure inside a host step may keep it — resume overrides are a
real remedy there. **EMBEDDED USER CHECKPOINT (show-before-code):** the planner drafts BEFORE (executed)
/ AFTER for every message shape — the boundary error (argument), its env / settings / `default:` /
recorded-run variants, the child-input error, the (c) container error, the (c) path-on-non-object
error, the multi-input aggregate, the JSON `errors[]` shape — and hands them back before the build.

**Resume** replays recorded `meta.inputs` through the coercer: it must be idempotent (property test);
an old trace holding a lenient-era value the NEW coercer rejects fails with an error that names the
`name=value` override (values it accepts — `"7"` for an `integer`, a scalar for a `string` under (h) — replay
fine). No trace-format change (only value types in `meta.inputs` change; memo keys miss once).

## RESOLVE AT START (from the context-free cross-model re-read, 2026-10-07 — constraint stated, mechanism the planner's)

- **Binding identity, not names.** A node's own `inputs:` keys are merged into the resolution context and can
  shadow a workflow input of the same name (`template_resolution.py:~251,~396`, while `type_checker.py:~41`
  checks workflow declarations first). The no-re-parse policy applies to the ACTIVE binding of a reference's
  root, so a local `inputs.data: ${fetch.stdout}` keeps output semantics even when a workflow input `data`
  exists. Say how the carrier tells them apart (a name set alone cannot).
- **Whole-map `inputs:`.** "The parent stops auto-parsing a workflow step's `inputs:`" means the VALUES of a
  dict-form `inputs:`. A whole-param `inputs: ${fetch.stdout}` holding a JSON object is parsed into the map
  today (the simple-template-into-container branch, `template_resolution.py:~285`) and the child requires a
  dict (`workflow_executor.py:~731`): keep outer-map parsing, or reject the form with a diagnostic — state which.
- **Lossless inference is executable.** Name the candidate parser, the canonical renderer and the exact
  comparison (`param_parsing` renders compact JSON, `templates.to_string` spaced JSON with `True`), the `null`
  policy, and the SOURCE classes that infer (CLI token, web-form token) vs pass through (MCP, sub-workflow, YAML
  default, recorded run, env/settings, stdin — classify each). The coercer's signature therefore carries the
  source, not only `declared type + value`.
- **Agent `inputs:`** has only an outer `dict` declaration (`agent_node.py:~31`), no per-key annotations: state
  its rule (source-root protection only, upstream-output parsing kept) without implying annotations exist.
- **Child compile.** The compile-time `prepare_inputs` also resolves env/settings/default fallbacks for the
  child: a "defaults-only" mode must keep that; the per-item `prep` check runs before it. `_validate_child_params`
  raises `ValueError` and `prep` keeps only `str(e)` (`workflow_executor.py:~179`) — the structured Diagnostic
  must survive the recoverable path.
- **HTTP `headers` / `params` string maps** carry the same JSON-parse hazard `env:` had (a header value that
  looks like JSON is parsed into a dict) — Task 118 handed it to this task's policy (118 plan §10). State whether
  the consumer-declares-text rule covers them (recommended: yes — an HTTP header value is text by protocol).
- **Task 112's hand-off** says both checkpoints call `TypeSpec.accepts` (`task-112.md:11`); this spec says share
  context keys, not `TypeSpec`. Reconcile in 112's top block at start (112 checks Python-style S1/S2/S3 names
  that `TypeSpec` rejects — translate, or a sibling checker), never two divergent type engines.

## Decisions (i)–(iii) raised by the re-read (DECIDED 2026-10-10 — user: *"yes go ahead with all these recommendations"*, each presented in plain language with the recommendation below)

- **(i) Root-wide or string-only protection.** The DECIDED rule says a reference rooted in a declared non-`any`
  input is never re-parsed; the Design section narrowed it to `string` roots ("every other declared type is
  already typed") — but an `object` input can hold a JSON-looking STRING descendant (`{"payload": "{\"a\":1}"}`),
  and `${data.payload}` / `${data.payload.a}` parse it today. **Root-wide**: the descendant stays text (the ruled
  sentence; one rule). **String-only**: descendants of object/array inputs keep auto-parse. Recommendation:
  **root-wide** — it is the sentence you ruled; the Design narrowing was the orchestrator's error. **DECIDED: root-wide**
  (the Design section now says so).
- **(ii) A declared `string` crossing into a child's declared `object`.** (c) makes a declared string used as a
  container a validation error; (e)+(f) says the child's declaration coerces each incoming value. Parent
  `s: string` = `{"a":1}` → child `obj: object`: reject statically, or let the child's boundary parse the text?
  Recommendation: **the child boundary parses it** — a declared boundary coerces text by its own type exactly
  as a CLI token does; (c) governs the resolver and in-workflow consumers, not a declared boundary. **DECIDED: the child boundary parses it.**
- **(iii) The web re-run of an `any` input.** Under (d) the web form infers; an MCP-supplied `any` string `"42"`
  re-run from the form becomes `42` (`format_param_value` renders both as `42`). Options: carry typed values
  through prefill and submission (a form-encoding change), or narrow the round-trip and parity promises to
  non-`any` types. Recommendation: **narrow the promise** — `any` means "don't check", and a typed form encoding
  is cost without an observed problem. **DECIDED: narrow the round-trip and parity promises to non-`any` types.**

## Constraints

- **Engine contact** (`runtime/engine/template_resolution.py`, `workflow_executor.py`, `core/
  templates.py`): plan-mode deep-review is mandatory. **Builds after Task 118 Part 2 merges** (same
  resolver lines; 118's hand-off artifacts are PR #723, its plan and progress log — its task-review
  is written at Part 2's end). **Coordinate with Task 181** (same `_resolve_string` arm).
- **Tests that pin today's leniency flip deliberately and are named in the plan**:
  `tests/test_core/test_param_coercion.py` `*returns_original` and `:178-199` (stringify);
  `tests/test_runtime/test_prepare_inputs_coercion.py:18,153,163`; `test_validate_only.py:192-195`
  ("`prepare_inputs` not called"); `test_rerun_display.py:645-709` and `test_run_node.py:511-532`
  (the inference round-trip). Keep `test_param_coercion.py:439` (placeholder).
- **New tests the plan must name**: a batch of sub-workflows with a type error under `continue`;
  typed-input parity across CLI / MCP / web / resume / child; `--dry-run` vs runtime per-item child
  inputs; parity-corpus rows for the declared-root rule (`test_template_parity.py`).
- **Stale surfaces** (verify each): `guide/core.md:437-470` (auto-parse promised for inputs) and
  `:661-675` (type table says "integer: Rejects floats" — the natural home for (b)); BOTH MCP
  instruction copies (`mcp_server/resources/instructions/mcp-agent-instructions.md:~1017-1040`,
  `mcp-sandbox-agent-instructions.md:~1000-1020`); `guide/nodes/code.md:64` ("declare dict/list not
  str" flips); `guide/nodes/shell.md:64`; `guide/features/batch.md:35`; `guide/core.md:298` (`any`);
  `docs/reference/cli/index.mdx:152-158`, `docs/reference/nodes/code.mdx:104`,
  `docs/how-it-works/template-variables.mdx:90-92`, `docs/reference/nodes/index.mdx:67`;
  `src/pflow/core/CLAUDE.md:104-107,198-200` and `core/templates.py:43-46` and `architecture/
  reference/template-variables.md:618-619` (all claim `TypeSpec.accepts` is in use — it has zero
  callers); `runtime/compilation/CLAUDE.md:58-66`, `runtime/engine/CLAUDE.md:79-80`,
  `runtime/CLAUDE.md:53-56`, `cli/CLAUDE.md:15`; `prompt_cache_analysis/context.py:51-53`;
  `param_coercion.py:236-262`; `web/src/components/RunForm.tsx:8-12`, `web/src/utils/
  controlForType.ts:8-9`, `RunPanel.tsx:24-25,59-61`; `architecture/core-concepts/
  data-type-coercion.md:67-146` (cites deleted files; no entry for the input boundary).
- `display_rerun_commands` / `format_rerun_command` (`rerun_display.py:31-95`) have no production
  readers — delete rather than adapt. `last_execution_params` (`runner.py:~798`) should store the
  coerced values, as the trace does.
- **ADR-0017** (the parse rule) is written with this spec; the planner amends it only through the
  main orchestrator.

## Dependencies

Builds after Task 118 Part 2 (PR #723 + `.taskmaster/tasks/task_118/implementation/` are the
hand-off until its task-review exists). Coordinates with Task 181 (its plan on branch
`feat/task-181-mcp-code-params-json`). Read first: Task 170's task-review, ADR-0006, ADR-0016,
ADR-0017, issues #686 #687 #297 #188 in full (body + comments), Task 112's top block.

## Verification (intent)

Breaks 1–12 each become an actionable error at validation or input time, or a correctly typed value,
per the decisions — except break 8 under (d), where `02134` on `type: any` STAYS a string by the
lossless rule (that is the fix). `--validate-only` with supplied inputs and the run agree, defaults
included. Upstream-output auto-parse (`${x.stdout}` as batch items, `${x.stdout.field}`) is
unchanged, and the fifteen in-tree bindings of an LLM/shell output into a child `string` input keep
working whatever the text looks like. The MCP, web-form, resume and child entry points deliver the
same typed value for the same input.

## References

- Battery ledger (local): `scratchpads/session-12/task-120-spec-battery.md`; issues #686, #687,
  #297, #188; #742 (YAML literal re-typing, out of scope); #743 (declared output types, out of scope).
