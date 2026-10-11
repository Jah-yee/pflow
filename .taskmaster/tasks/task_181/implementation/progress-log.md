# Task 181 — progress log

## [2026-10-06 23:30] task-planner — planning complete, CP-1 pending the user

- **Did:** investigated with 4 searchers and wrote `implementation-plan.md` and
  `diagnostics-checkpoint.md`, then ran the mandatory plan-mode battery and folded in every
  confirmed finding. The battery was review-plan, architecture-fit, validation-consistency,
  impact-completeness, silent-failures, feature-interactions and agent-ux, all direct launches.
- **Changed:**
  - the spec: open questions answered by pointer; dependency narrowed to Task 118 Part 2;
  - `implementation/implementation-plan.md`;
  - `implementation/diagnostics-checkpoint.md`;
  - this log.
- **Verified:**
  - BEFORE probes p1–p12 executed with `uv run pflow --validate-only` and with
    `templates.resolve` on `ebf7cab2`;
  - the local registry lists the four JavaScript code params;
  - the Issue-pass early return at `runtime/template_validation/validator.py:82-92` and the
    `pflow mcp describe` placeholder at `cli/commands/mcp.py:1002` were read directly.
- **Deviations/surprises:**
  - **The battery reversed the draft's R3 recommendation.** "Alongside" put a
    "Remove unused declarations" fix first, which deletes the input and silences the bug. The
    recommendation is now "instead of", matching Task 118's "one mistake, one diagnostic".
  - **The battery found three silent holes the draft missed:**
    - an insert swallowed by an Issue (`${${x|json} + 1}`);
    - near-miss spellings (`${x|json }`);
    - a quoted insert (`'${x|json}'`).
  - **The draft's escape check could not find its own headline case.** It sliced the escape body
    and so missed `$${count|json}`. It is replaced by a source scan, `hidden_inserts`, which also
    removes the planned `Template.escapes` AST change.
  - **The "runtime refusal on every surface" claim was false.** Loop conditions read false and
    cache chunks drop. D4 now carries the honest table.
  - **Rebuilt suggestions dropped `|json`.** Fixed in a new D7.
  - **`pflow mcp describe` teaches the bare form.** Added to PE.
- **Self-checks:** the architecture-fit lens found no one-way door that a roadmap task would have
  to reverse. Every Critical was either a message-design issue (folded in) or a wrong plan claim
  (corrected against code).
- **Next:** the user rules on CP-1 (R1–R6, R8). The build waits for Task 118 Part 2 to merge (plan
  §0). The task orchestrator's first act is to find the ruling entry below; if it is absent, do not
  build.

## [2026-10-07] main orchestrator — CP-1 RULED (the ruling entry the task orchestrator looks for)
- Did: relayed `diagnostics-checkpoint.md` to the user in plain language (what the task does, the seven rulings, the two
  silent behaviour changes, the eval/#722 dependency); user: *"181: all yes"*.
- Changed: checkpoint header, plan §CP-1 line, spec "Resolved at planning" note, this entry.
- Verified: R1 four params · R2 error elsewhere · R3 error-instead-of / warning · R4 7a+7b · R5 spaces · R6 json.dumps
  default separators ensure_ascii=False · R8 nouns. | Assumed: nothing.
- Deviations/surprises: none. Note for the build: #722 (MCP `registry_run` rejects `eval(`) is open — the §4c/R7 eval form
  is refused over MCP until it lands; the guide text should not promise it works over MCP before then.
- Next: build after Task 118 Part 2 merges; the task orchestrator re-verifies 118's shipped `param_mode` shapes (P0).

## [2026-10-11 00:00] task orchestrator — bootstrap; 118 Part 2 shapes pre-checked
- Did: merged `origin/main` (`d0463878`) into the branch (clean, merge `24386bfe`); `make install` green; read ORCHESTRATION, spec, plan, checkpoint header, 118 + 170 task-reviews, #621 (latest comment: shell/code half closed by 118 Part 2; the MCP `function:` half is this task's).
- Verified (grep on the merged tree): `ParamMode = Literal["template","body"]` + `param_mode` + `_BODIES` + `template_params` + `code_bodies` (`core/workflow/template_surfaces.py:24-58`); `split_params(…, node_type)` checks `param_mode != "body"` before `has_templates` (`runtime/engine/template_resolution.py:127`); `parses_leaves` at `:90`; `step_scope` / `StepScope.owner(root, *, has_path)` (`core/workflow/data_flow.py:859-897`); unused-input hook = `| body_reference_roots(workflow_ir)` in `validate_workflow_templates` (`runtime/template_validation/validator.py:113-119`); web `isCodeBody` (`web/src/utils/format.ts:146`, called `scan.ts:139`, `ReadPanel.tsx:76`); chrome-devtools MCP registered locally.
- Deviations/surprises: plan §0 check 1 says callers compare `== "body"`; shipped callers compare `!= "body"` (`template_surfaces.py:47`, `react_flow.py:312`, `execution_service.py:701`, `template_resolution.py:127`, `file_resolver.py:103` uses `== "body"`). Same effect for a third mode (embedded is "not a body" → still a template param) — no decision changes; I1 confirms in P0.
- Next: launch I1 (Opus · high) on P0 → PA → PB → PC; mid-task review after PC.

## [2026-10-11 09:30] implementer I1 — P0 baseline
- Did: captured the baselines, ran the six §0 checks on the shipped 118 Part 2 shapes, grepped for prior `|json` / embedded-tool use, re-ran the checkpoint probes.
- Changed: plan §0 check 1 (citation fix in place, marked "re-verified 2026-10-11 on 24386bfe"); this log.
- Verified:
  - **`make test`:** 10726 passed, 0 failed (58.5 s). **`make check`:** green (rc 0).
  - **`verify.sh`:** 75 pass / 12 drift / 0 harness errors. Drift set by name: `02-validator-errors/03-prompt-cache-on-shell-node`, `02-…/05-subworkflow-references-parent-chunk`, `03-analyze-cache-modes/05-trace-from-trace`, `03-…/06-no-trace-autoload`, `03-…/07-autoload-prefers-success`, `03-…/08-autoload-failed-only`, `03-…/09-autoload-rejected-names-file`, `04-warning-catalog/03-cache.invalid-on-non-llm`, `04-…/09d-cache.prewarm-disabled-below-min`, `04-…/09e-cache.conditional-warmup-recommended`, `10-live-recordings/03-gemini-translation`, `12-real-world-lyrics-generator/04-guide-auto-detect` (the ~12 the main orchestrator expected).
  - **`capture.py --check`:** 29 examples, 5 differing — all pre-existing on main (each JSON failure gains `"result": {}`, from #754's partial-outputs fix): `error-handling/coalesce-mixed-absent-failed`, `failed-node-direct-reference`, `source-line-heavy-offsets`, `source-line-multi-output`, `typo-on-failed-node`. PZ compares against this set.
  - **§0 checks** (all hold; no decision changes):
    1. `param_mode(node_type: str | None, key) -> ParamMode`, `ParamMode = Literal["template","body"]`, `_BODIES` — `core/workflow/template_surfaces.py:24-38`. Callers compare `!= "body"` (`template_surfaces.py:47` `template_params`, `react_flow.py:312`, `execution_service.py:701`, `template_resolution.py:127`); `file_resolver.py:103` uses `== "body"`.
    2. `TemplateConfig.node_type: str = ""` (`runtime/engine/types.py:23`), filled by the compiler (`compiler.py:348`).
    3. `split_params(params, expected_types, node_type=None)` (`template_resolution.py:100`), body check before `has_templates` (`:127`).
    4. Step-scope helper: **`data_flow.step_scope(workflow_ir, node) -> StepScope`** + **`StepScope.owner(root, *, has_path)`** (`data_flow.py:858-897`). `body_references` is sh/Python-specific — reuse the scope rule only.
    5. Unused-input hook: the union passed to `_validate_unused_inputs` in `validate_workflow_templates` (`runtime/template_validation/validator.py:113-119`, `| body_reference_roots(workflow_ir)`); `_validate_unused_inputs` at `:575`.
    6. `isCodeBody(kind, name)` at `web/src/utils/format.ts:146`; called `web/src/graph/scan.ts:139`, `web/src/components/ReadPanel.tsx:76`; `sourceDecorate.ts:62` mentions it in a comment only.
  - **Greps:** no `${…|json}` anywhere in `src/ tests/ examples/ workflows/ docs/` (only CLI `text|json` option prose). Embedded-tool types: the four planned sites only (`click.pflow.md:83-85`, `hover.pflow.md:56`); other hits are prose/tests with no `${` in a code param (`guide/nodes/mcp.md:113`, `test_source_line_sidecar.py:34`, `test_result_format_json_block.py:3`, `test_screenshot_settle_workflow.py:3`).
  - **Checkpoint probes** p1, p2, p3, p5, p6, p7, p8, p9, p12 re-run with `uv run pflow --validate-only` (scratchpad `t181/probes/`): every BEFORE block matches the checkpoint verbatim. Runtime BEFOREs re-executed with `templates.resolve`: `Total: ${price}` (escape collapsed), `'Don't Stop'`, `True`.
  - Re-verified moved citations I will edit: `execution_service.py` env expansion is `:693-704` (plan says 731-736); validator early return `:80-92`; `_validate_output_sources` `core/workflow/validator.py:594`; Pass 6 `_check_string_template_types` `type_validation.py:75`. | Assumed: the remaining plan line numbers drift without shape change — re-checked per phase before each edit.
- Deviations/surprises:
  - Plan §0's `== "body"` is `!= "body"` in the shipped code (fixed in place; no decision changes — an embedded param stays in `template_params`, which is what D3's surface consumer needs).
  - **Sequencing hazard for PD (orchestrator's call, not mine):** from PB on, `click.pflow.md` and `hover.pflow.md` FAIL validation on this branch (§4a ERROR: `selector`/`text`/`measure_id`/`row_name` are used only as bare `'${x}'` in `function`). The screenshot skill documents both workflows (`SKILL.md:15-40`). PD's acceptance drives the skill; if it needs `click`/`hover`, the four-site conversion (PE's first bullet) must land before PD. The other five screenshot workflows are unaffected (no `${` in their JavaScript).
- Self-checks: fully happy — baseline only; test-reflect: not needed — P0 writes no tests.
- Next: PA (grammar + `embedded_code` + `resolve(embedded=)` + D5 helpers + `scan.ts` grammar copy).

## [2026-10-11 10:40] implementer I1 — PA grammar: `${x|json}` parses and resolves
- Did: D1 grammar (`_JSON_INSERT`, `Expression.as_json`, `raw` keeps the suffix, never simple, `to_json`), D3 core (`embedded_code`, `resolve(…, embedded=)`, `TemplateResolver.has_templates(…, embedded=)`), D4 resolve arm, D5 helpers (`hidden_inserts`, `near_miss_insert`), the `scan.ts` grammar copy.
- Changed: `src/pflow/core/templates.py`; `src/pflow/core/CLAUDE.md` (Two channels + a JSON-insert bullet); `web/src/graph/scan.ts` (`JSON_INSERT` into `EXPRESSION_AT`); tests `test_core/test_template_grammar.py` (11 rows; counts 76→87 rows, 82→93 opens), `test_core/test_templates.py` (4 SHAPES rows, `test_views` line, fuzz `|json` token + 8 fixed rows → `15*15 + 48`, new "JSON inserts and the embedded-code view" section), `test_core/test_graph_build.py` (4 `refs_with_path_in` rows), `web/src/graph/scan.test.ts` (4 parity rows).
- Verified: `make check` rc 0; `make test` 10813 passed (baseline 10726; +87 new, 0 failures); `web/` `npx vitest run` 55 files / 845 tests green, `npm run typecheck` rc 0 (needed `npm ci` in the worktree's `web/` — it had no `node_modules`; no lockfile change). Seam meta-test (`test_template_grammar_seam.py`) passes unchanged. **Mutation ledger** (byte-copy restore, each a counted failure): M1 `is_simple` ignores `as_json` → 10 red (`test_views`, every value row); M2 delete the D4 arm → `test_a_json_insert_outside_embedded_code_is_kept_as_written_like_an_issue`; M3 view keeps every Expression → `test_the_embedded_view_keeps_only_json_inserts…`; M4 `has_templates` ignores `embedded` → fuzz + `test_has_templates_in_embedded_code…`; M5 near-miss keeps case → `${x|JSON}` row; M6 `hidden_inserts` keeps visible ones → `${x|json} $${y|json}` row; M7 `ensure_ascii=True` → non-ascii row; M8 `to_string` for inserts → apostrophe row; M9 `raw` drops the suffix → SHAPES; M10 TEMPLATE_PATTERN suffix capturing → `findall` assertion; M11 TS `EXPRESSION_AT` without the suffix → 2 `scan.test.ts` rows. | Assumed: nothing beyond the plan.
- Deviations/surprises:
  - **`_resolve_string` hit ruff C901 (11 > 10)** with the D4 arm, so its simple-template branch moved to a new `_resolve_simple` (no behaviour change). **For Task 120's P0 — where the `embedded` flag is consulted:** `resolve` (picks `embedded_code(parse(value))` for a string leaf; passes the flag down the dict/list recursion), `_resolve_string` (one guard: `segment.as_json and not embedded` → verbatim + issues channel; otherwise an insert is `to_json`), `TemplateResolver.has_templates` (reads `embedded_code(_tokenize(s))`). `_resolve_simple` never sees it (an insert is never simple).
  - `near_miss_insert` also right-trims the expression before `|` so the suggestion is canonical (`${ a ?? "d" | Json }` → `${a ?? "d"|json}`); the plan's rows are unchanged by this.
  - The JSON-text row (`'{"a":1}'` → `"{\"a\":1}"`) and coalesce/dynamic-index rows were added beyond the plan's value table — they pin "text is never re-parsed" and "the suffix covers the whole expression" at the resolver.
  - Mid-way state as the plan says: a non-embedded `${x|json}` now passes the validator (it is an Expression) but refuses at run time; PB closes it.
  - `TemplateResolver.resolve_coalesce("x|json")` (no `src/` caller) evaluates the operand and ignores the suffix — left as is; it is a value lookup, not a resolution.
- Self-checks: fully happy — the one doubt (does any `findall` consumer see a second group?) became a test. test-reflect (directed): DEEPENED `test_the_lexical_patterns_read_an_insert_as_its_expression` (it only caught a missing suffix; now asserts `findall` returns strings — M10 kills it); every other new test was mutation-killed above (M1–M9, M11); nothing deleted — no new test is a duplicate or absence-only (the view test's absence half has `test_embedded_resolution_fills_only_the_insert`'s presence pair).
- Post-handback "fully happy?" (orchestrator-directed): clean, no code change. Re-checked these:
  - `Expression(` has one constructor site (`_expression_at`).
  - `hidden_inserts` / `near_miss_insert` edges hold (an Issue-swallowed insert inside an index, `$$${`, an unclosed near-miss).
  - Executed a `## Cache` with `${x|json}` (fenced): `--validate-only` reports valid plus the unused-chunk warning, with no crash. That is the planned mid-way state; PB's misplaced check covers `cache_var`.
  - **Note for PC (D7):** `runtime/template_validation/batch_item_validation.py:126` also rebuilds `${ref.raw}` from operand text. It is not in D7's list; check it there (as a batched `${item.x|json}` miss).
- Next: PB (classification, validator policy, graph/canvas, Pass 6, `registry_run`).

## [2026-10-11 11:20] implementer I1 — STOP before PB: message text the ruled checkpoint does not determine (resume state)
- Did: before writing any PB code I listed every message PB emits and checked it against `diagnostics-checkpoint.md` and the code. PB has **no edits** on disk. The tree is P0 + PA, uncommitted: `make check` rc 0, `make test` 10813 passed, web vitest 845 passed + tsc rc 0.
- **Why stop:** the launch packet makes "any ambiguity in message text vs the ruled checkpoint" a stop condition. One ruled message cannot be rendered as written (Q1). Five more are ruled for one case only, and the variants need text that was never ruled (Q2–Q6). Each question below has ONE recommendation. Text-only answers change strings and assertions (plan §7), not structure. "Go with the recommendations" lets me build PB → PC straight through.
- **Q1 — §4d (an insert left inside quotes) cannot be rendered as ruled.** The ruled line is `… so these quotes become part of the text ('"#main"').` The `'"#main"'` part needs the input's run-time value, which validation does not have. Also, with double quotes the result is not quoted text: `"${selector|json}"` sends `""#main""`, which is a JavaScript SyntaxError. **Recommend:** `'${selector|json}' in 'function': the insert is already a quoted JavaScript value, so these quotes wrap it a second time.` Keep the fix line as ruled: `→ Remove the quotes around it: ${selector|json}`.
- **Q2 — §4a when one param holds several inputs used nowhere else.** This is the real in-tree case: `click.pflow.md`'s `function` holds `selector`, `text` and `measure_id`. Plan D6 says "one ERROR per param", but the ruled head names a single input (`Input 'selector' is never inserted: …`). **Recommend:** one ERROR per (param, input), each with its own ruled-shape head and fix, so the author fixes all of them in one pass. Every one of those inputs leaves the unused-input report, as D6 rules.
- **Q3 — §4b's noun for root kinds other than the batch item.** The only ruled form is `… so the batch item is not inserted.` **Recommend** these nouns: `the batch item`, `the batch index`, `the loop iteration`, `workflow input 'x'`, `this step's inputs: key 'x'`, `the output of step 'x'`. `root_kind` in `context.embedded_references[]` takes the matching id: `batch_item`, `batch_index`, `iteration`, `input`, `inputs_key`, `step`.
- **Q4 — §4b with several references in one param.** The structure is ruled (one warning; references in source order; one `→` each; one closing line), but the head is ruled only in the singular. **Recommend:**
  - Head: `${item.id} and ${fetch.result} in 'function' are JavaScript: pflow sends them unchanged, so the batch item and the output of step 'fetch' are not inserted.` With three or more references, separate them with commas plus a final "and".
  - One ruled `→ To insert it, put ${…|json} where …` line per reference.
  - Closing line: `→ If 'item' or 'fetch' here is your JavaScript variable, the code is correct — write it with spaces inside the braces (${ item.id }) to clear this warning.`
  - The singular stays verbatim as ruled.
- **Q5 — the variable name in the `const` examples.** The ruled §4a example is `const sel = ${selector|json};`, which is the author's own `const sel = '${selector}';`. The other ruled examples use the reference's last name: `const name = ${user.name|json};` (§4a unquoted), `const id = …` (§4b), `const count = …` (§7a). **Recommend:** use the author's declared name when the reference (with its quotes) is the whole right-hand side of `const|let|var NAME =`. Otherwise use the last field name, or the root when there is no field, with `-` → `_`. This reproduces every ruled example.
- **Q6 — two small variants.**
  - **(a) An input whose only use is a whole-value bare reference** (`- function: ${code}`): **recommend** the §4a ERROR head with §4c's `eval` fix line.
  - **(b) A bare output `source: x|json`** (§5): **recommend** the head shows how the runtime reads it, `${x|json} is accepted only …`, and the fix is written bare, `→ Remove '|json': write x. A dict or list is already inserted as JSON text.`
- **Decisions I will make unless told otherwise.** None changes the ruled text.
  - **D2's table becomes an ordered tuple, not a `frozenset`.** The §5 list of allowed places then renders in the ruled order (`'function'` of evaluate_script/browser_evaluate, then `initScript`, then `code`). The plan's "sorted" would reorder it.
  - **`types.ts` gets `mode?: ParamMode`; absent means template.** About 150 test literals build an `RFParam` without it, so a required field would make PB edit every web fixture. The wire always carries the field, and PD may tighten the type.
  - **D4 routes `_validate_output_sources`' bare (no-`${`) branch through `normalize_output_source`.** It then reads roots from the parse. This also fixes a bug that exists on main today (executed): a bare coalesce `source: x ?? n.stdout` gets a false `Output 'o' references non-existent source 'x ?? n'.`
- **Checkpoint fact, corrected; no ruling needed.** §5 says "On a loop condition the existing loop-shape error also fires". The code says otherwise: the Issue pass returns early (`runtime/template_validation/validator.py:80-92`) before `_validate_loop_conditions` (`:168`), so only the §5 ERROR appears, the same as for any Issue in a loop condition today. PB's test will assert that.
- Verified: the §4d claim was checked by reasoning about the JavaScript grammar (`""#main""` is a SyntaxError). The bare-coalesce output-source false error was executed against `WorkflowValidator._validate_output_sources`. The loop-shape ordering was read at `validator.py:80-92` and `:168`. | Assumed: none of Q1–Q6 changes PB's structure (detection, severities and paths are all ruled).
- Deviations/surprises: the stop itself. Everything else is listed above.
- Self-checks: n/a (no PB work); PA's are in its entry.
- **Resume:** with the answers, build PB as planned (plan §4 PB; D2, D3 surface consumer, D4, D5, D6, D8, D9's `registry_run` bullet), then PC. P0's PD sequencing hazard still stands.

## [2026-10-11 12:00] task orchestrator — rulings on I1's Q1–Q6 (importance 2, reversible: strings/assertions only); P0+PA committed
- Did: read I1's P0/PA/STOP entries and the PA `templates.py` diff; "fully happy?" on PA → clean. Ruled Q1–Q6 and the three default choices, all **as I1 recommended** — they extend the user's CP-1 ruling to cases it did not enumerate, change strings only (plan §7), and are reversible. Recorded here so the task-review can name them; the user sees them via the handback.
  - **Q1 (corrects ruled §4d text):** the ruled tail `('"#main"')` needs a run-time value validation never has, and with `"…"` the result is a JS SyntaxError, not text. Head becomes `'${selector|json}' in 'function': the insert is already a quoted JavaScript value, so these quotes wrap it a second time.`; fix line as ruled. This is the one deviation from ruled text — flag it in the task-review.
  - Q2 one ERROR per (param, input); Q3 the six nouns + `root_kind` ids; Q4 plural head/one `→` per ref/closing line; Q5 `const` name rule; Q6(a) §4a head + §4c eval fix; Q6(b) bare-source head/fix — all as recommended.
  - D2 table an ordered tuple; `types.ts` `mode?: ParamMode` (PD may tighten); output-source bare branch through `normalize_output_source` — accepted.
- **Phase-order change (importance 1):** PE's "four sites and their caveats" block (`click.pflow.md`, `hover.pflow.md`, the screenshot SKILL.md caveat + `make sync-claude-assets`) moves to the end of PC: once PB lands those workflows fail validation, and PD's screenshot driving uses them. The rest of PE stays in PE.
- Next: resume I1 on PB → PC (+ the four sites); D7 also covers `batch_item_validation.py:126` (I1's own note).
