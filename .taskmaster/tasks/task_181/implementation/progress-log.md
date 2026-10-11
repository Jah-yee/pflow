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

## [2026-10-11 14:10] implementer I1 — PB embedded code: classification, validator policy, graph/canvas, Pass 6, registry_run
- Did: D2 (`param_mode` → `"embedded"` by tool-name suffix + param), D3 surface consumer (`TemplateSurface.mode`; `templates()` yields the `embedded_code` view), D4 validator half (misplaced insert = §5 ERROR on every non-embedded surface, bare output sources through the normalizer, log line `Found N template error(s)`), D5 (§7a hidden / §7b near-miss ERRORs on embedded surfaces), D6 (`data_flow.embedded_references` detector + `_validate_embedded_references` consumer: §4a ERROR per (param, input) instead of unused-input, §4b/§4c one WARNING per param, §4d WARNING), D8 (`refs_with_path_in`/`source_refs_in(…, embedded=)`, `_add_ref_edges(embedded=)` per top-level param, `RFParam.mode`, `_param_is_dynamic(value, mode)`, Pass 6 skip), D9's `registry_run` bullet; regenerated the four React Flow contract fixtures.
- Changed: `core/workflow/template_surfaces.py`, `core/workflow/data_flow.py` (detector; `_BATCH_INDEX_OWNER`/`_ITERATION_OWNER` constants promoted from 118's literals so root kinds map by constant), `core/workflow/validator.py` (bare output-source roots), `core/workflow/graph/{scope,build}.py`, `graph/renderers/react_flow.py`, `runtime/template_validation/{validator,type_validation}.py`, `mcp_server/services/execution_service.py`, `web/src/types.ts` (`ParamMode`, `mode?`), `web/src/test/fixtures/contracts/*.json` (regenerated — 52× `"mode": "template"`, 18× `"mode": "body"`, trailing commas; nothing else). New tests: `tests/test_integration/test_embedded_code_consumers.py` (classification rows + one row per consumer through its own entry, each with an insert presence half), `tests/test_integration/test_embedded_code_diagnostics.py` (§4/§5/§7 through `WorkflowValidator.validate`, and the CLI for §4a/§4b and the cache var); new helper `tests/shared/mcp_tool.py` (registers `mcp-<server>-<tool>` like `mcp sync` does; stubs only `MCPConnectionPool.call_tool` / `MCPNode._exec_async` / `_load_server_config`).
- Verified: `make check` rc 0; `make test` 10867 passed + 1 xfailed (baseline 10813 after PA); web `tsc` rc 0, vitest 845 passed. Every checkpoint probe reproduces its AFTER verbatim through `uv run pflow --validate-only` (§2 p1 valid; §3/§4a p2, p5; §5 p3; §4b p7; §3 p8 valid; §7a p12); §7a-JS, §7b, §4c, §4d, the plural 4b and Q2's per-input ERRORs reproduce through the tests. **Mutation ledger** (byte-copy restore, counted failures, over the two new files + the contract-fixture drift test): M1 `templates()` drops the view → 10 red (§4a rows, data_flow/pass_5/pass_8/issue_pass consumer rows); M2 `_add_ref_edges` drops the flag → 1 (graph_build row); M3 Pass 6 skip dropped → 1 (pass_6 row); M4 canvas ignores embedded → 1 (canvas row); M5 bare roots not added to the unused-input union → 5 (every §4a row: "instead of" lost); M6 no misplaced-insert check → 6; M7 bare output source not normalized in the Issue pass → 1; M8 output-source roots lexical again → 2; M9 no hidden-insert check → 2; M10 no near-miss check → 3; M11 quoted insert undetected → 1; M12 step scope ignored → 3; M13 declared `const` name ignored → 2; M14 `param_mode` never embedded → 32. | Assumed: the `registry_run` row's runtime leg — phase-gated `xfail(strict=True, raises=AssertionError)` until PC (its run reaches template resolution, which PC wires); its PB-observable half was executed: the run's error names `${a}` and `${PFLOW_TEST_X}` unexpanded, with no "Missing environment variable".
- Deviations/surprises:
  - **Rulings applied as ruled (12:00):** Q1 §4d text; Q2 one §4a ERROR per (param, input); Q3 nouns + `root_kind` ids; Q4 plural head/closing; Q5 `const` name (author's declared name, else last field/root, `-`→`_`); Q6 eval fix for a whole-value input, bare output-source head/fix; D2 ordered tuple; `mode?`; bare output-source roots through the normalizer.
  - **The table is public `EMBEDDED_CODE`, not `_EMBEDDED_CODE`:** the validator renders the §5 list from it. PE's searcher-doc line should name `template_surfaces.EMBEDDED_CODE`.
  - **§4b on a QUOTED bare reference** (not enumerated by the checkpoint): its `→` composes the ruled quote-aware fix — `To insert it, replace '${x}' (the quotes too) with ${x|json} — the value arrives already quoted: const …`. Plan D6 requires the fix to be quote-correct; no new phrasing beyond the ruled pieces.
  - **Warnings render on stderr** (the CLI's convention; the checkpoint's AFTER blocks were captured `2>&1`). The CLI test asserts stdout `✓ Workflow is valid` and the warning block on stderr.
  - **`_validate_malformed_templates` hit C901**, so its per-value branch moved to `_template_diagnostic` (one diagnostic per value, unchanged behaviour).
  - **Bare coalesce output sources** (`source: x ?? s.stdout`) no longer get the false "non-existent source 'x ?? s'" (D4's routing; pinned by `test_a_bare_coalesce_output_source_names_real_roots`).
  - **§6 / D7 is still PC:** p6's suggestion line reads `${nod.result}` (no `|json`) until PC's validator sites (`data_flow.py` did-you-mean, `path_validation.py`, and the `batch_item_validation.py:126` note) land.
  - The screenshot workflows now fail validation as predicted (§4a) — converted at the end of PC per the 12:00 phase-order change.
- Self-checks: fully happy with one doubt resolved — I first asserted the 4b CLI warning on stdout (the probe captures merged streams); fixed to stderr after reading the real split. test-reflect: not directed for PB (the plan assigns PB the mutation ledger) — the ledger above kills every site; each absence row has a presence pair in the same medium (consumer rows' insert halves; `test_a_batch_alias_is_in_scope_only_on_the_batched_step`; §7 "embedded-only" vs the embedded rows; 4a presence `test_4a_presence_pair…`).
- Next: PC (engine wiring D9, D7 rebuilt fixes incl. `batch_item_validation.py:126`, `trace_report`, parity corpus D11, real chrome-devtools run), then the four screenshot sites.

## [2026-10-11 16:40] implementer I1 — PC runtime + diagnostics (engine contact), and the four screenshot sites
- Did:
  - **D9 runtime:** `split_params` makes an embedded param a template param only when `has_templates(value, embedded=True)`. Otherwise it is static, so `$${` and JavaScript's own `${…}` stay intact. `resolve_templates` gets an embedded branch: `resolve(template, context, embedded=True)`, `is_simple_template = False`.
  - **D7 runtime:** `classify_unresolved_references` marks an insert's outer operands `as_json` and keeps `coalesce_expr` without the suffix. A new `diagnostic_render.written_reference(ref, text)` renders every rebuilt `${…}` and the error summary line. It is used for the header, coalesce, did-you-mean, peer-fix and all-unavailable lines.
  - **D7 validator:** `TemplateOperand.as_json`. `_shown_as_inserts` shows insert-only references as `${x|json}` in Pass 5 (path) and Pass 8 (batch item) diagnostics; this covers `batch_item_validation.py:126` and §6's Error 2. Data flow's mis-cased-input did-you-mean takes `as_json`.
  - **D9 `trace_report`:** reads paths through `TemplateResolver.extract_variables` (the grammar).
  - **D11:** an `embedded_code` parity surface, 12 `EMBEDDED_ROWS` and 8 `MISPLACED_INSERT_ROWS` (D4's table), built by the preferred route. The corpus sink is registered as `mcp-corpus-evaluate_script`, server `corpus` is added through `MCPServerManager`, and the sink records `function`. The end-to-end leg runs every `Ok` row with no MCP server.
  - **Docs:** `runtime/engine/CLAUDE.md` Parameters.
  - **The four sites (moved here by the 12:00 ruling):**
    - `click.pflow.md`: three inserts, and its caveat removed;
    - `hover.pflow.md`: one insert;
    - the screenshot `SKILL.md` caveat removed, then `make sync-claude-assets` (`.agents/` mirror updated).
- Changed:
  - `src/pflow/runtime/engine/{template_resolution,template_errors}.py`, `runtime/engine/CLAUDE.md`;
  - `src/pflow/core/{diagnostic_render,trace_report,templates}.py`: `templates.py` loses `TemplateResolver.TEMPLATE_EXTRACT_PATTERN` (see deviations);
  - `src/pflow/core/workflow/data_flow.py` (did-you-mean `as_json`);
  - `src/pflow/runtime/template_validation/{operands,validator}.py`;
  - `tests/test_integration/test_template_parity.py`, `tests/fixtures/template_corpus/nodes/producer.py` (sink records `function`);
  - new `tests/test_runtime/test_embedded_code_runtime.py`; tests added to `test_embedded_code_diagnostics.py` (§6 CLI, did-you-mean, Pass 8 ×2) and `test_core/test_trace_report.py` (one);
  - deleted `tests/test_runtime/test_template_extract_pattern.py` (deletion unstaged — the orchestrator commits);
  - the screenshot example workflows, `.claude/skills/screenshot-pflow-web-ui/SKILL.md` + `.agents/` mirror.
- Verified:
  - **Gates:** `make check` rc 0. `make test` 10909 passed (PB 10867 + 1 xfail; +54 new, −12 for the deleted pattern file; the PB xfail is removed and the `registry_run` row now passes). Web vitest 845 passed, tsc rc 0. The parity corpus is 397/397.
  - **Real surface (chrome-devtools, executed):** `uv run pflow <scratch>/probes/real-run.pflow.md title="Don't Stop" flag=true`. The steps are new_page (`data:` URL) → page id → evaluate_script `() => ({t: ${title|json}, on: ${flag|json}, lit: \`${1 + 1}\`, d: \`$${5}\`})` → close_page.
    - Output: `{"t": "Don't Stop", "on": true, "lit": "2", "d": "$5"}` — exactly the plan's expectation.
    - The trace's `template_resolutions.function` is `{"template": "() => ({t: ${title|json}, on: ${flag|json}, lit: \`${1 + 1}\`, d: \`$${5}\`})", "resolved": "() => ({t: \"Don't Stop\", on: true, lit: \`${1 + 1}\`, d: \`$${5}\`})"}`.
  - **All seven screenshot workflows** (`click`, `hover`, `inspect`, `live-reload`, `screenshot`, `visual-invariants`, `shared/open-and-settle`) print `✓ Workflow is valid` under `uv run pflow --validate-only`, with no warnings. No "single-quoted JS" / "double quotes inside" caveat text remains in `examples/ .claude/ .agents/ docs/ src/pflow/guide/`. The click/hover real runs need the `pflow ui` slot and stay PE's.
  - **§6 reproduces verbatim** through the CLI (Error 2 now `${nod.result|json}`).
  - **Mutation ledger** (byte-copy restore, counted failures over the five affected test files):
    - R1 `split_params` ignores embedded → 4 red (3 parity runtime rows + `test_bare_javascript_routes_static…`);
    - R2 the embedded branch of `resolve_templates` dropped → 13;
    - R3 `written_reference` ignores `as_json` → 4;
    - R4 classify drops `as_json` → 4;
    - R5 `coalesce_expr` keeps the suffix → 1 (the chain test);
    - R6 validator inserts shown bare → 3 (§6, Pass 8 ×2);
    - R7 data-flow suffix dropped → 1;
    - R8 `registry_run` expands embedded code → 1 (the `mcp_expansion` row);
    - R9 `trace_report` reads the raw expression text → 1;
    - R10 `TemplateOperand` never `as_json` → 3.
  - | Assumed: nothing beyond the bullets below.
- Deviations/surprises:
  - **D11's `${ghost.x|json}` row:** the plan expected `Raises (compile data flow)`; the code gives `Unresolved`. The compiler's data-flow pass runs with `check_inputs=False` and returns `None` for an unknown root ("could be a runtime param"), so a run that skipped validation reports the miss. The row is `Unresolved(("${ghost.x|json}",), forbid=("${ghost.x}",))`. The validator half (`Error`) is as planned. A bare template param behaves the same way today.
  - **D7 mechanism (validator half):** the plan says "the validator sites read `as_json` from the Expression they already hold". They do not: Pass 5 and Pass 8 work on reference strings through ~10 functions. So `as_json` is marked once at its source (`operands._operands`) and applied once per pass (`validator._shown_as_inserts`). The fix replaces exact `${raw}` text in the message, suggestions and `context.template`.
    - Limitation: a suggestion that rebuilds a different path (`for example ${nod.output_key}`, an available-fields list) is not suffixed.
    - Runtime fixes use the structured `as_json` key and are all suffixed.
  - **`unresolved_references[]` gains `"as_json": true`, present only when true** (additive to CLI/MCP JSON; documented in `classify_unresolved_references`). This keeps every existing ref-dict assertion unchanged.
  - **Deleted `TemplateResolver.TEMPLATE_EXTRACT_PATTERN` and its test file.** The plan said "unchanged", but `trace_report` was its last consumer. The deletion test applies (no caller left) and the facade has no external users. `tests/test_runtime/test_template_extract_pattern.py` pinned only the regex.
  - **Not testable here:**
    - PC-4's "`inject_none_for_optional_inputs` leaves embedded params alone": `optional_input_keys` exist only for code nodes (`compiler.py:347`, from Python annotations), so an MCP step never has any.
    - PC-7's "on a miss, `cause` names the insert": `--dry-run` validates first, and every insert miss is a validation error (validated: `WorkflowValidationError` on `${ghost.x|json}`).
    - The dry-run test asserts the planner resolves an embedded step with no template error (R2 kills it).
  - **For Task 120's P0 — where the `embedded` flag is consulted.** Unchanged since PA:
    - `core/templates.resolve`: picks `embedded_code(parse(value))` for a string leaf and passes the flag down the dict/list recursion;
    - `core/templates._resolve_string`: one guard, `segment.as_json and not embedded`;
    - `TemplateResolver.has_templates`.
    - PC adds one caller-side decision in `runtime/engine/template_resolution.py`: `split_params` and `resolve_templates`, both keyed on `param_mode(node_type, key) == "embedded"`. 120's leaf-policy carrier would subsume the bool at those two calls.
  - **Trace format unchanged** (D12): `template_resolutions` already carries `{template, resolved}`, as the real run shows.
- Self-checks: fully happy, with these doubts resolved:
  - (a) Does the dry-run test discriminate? R1 does not kill it — legitimately, because a bare `${a}` is Text in the view either way. R2 does kill it, and R1 is caught by three other rows. Kept.
  - (b) Did the e2e leg really run through an `mcp-` type? Yes: the `StaticLiteral` e2e assertion compares the sink's received `function` with the template, and the compile path requires the `corpus` server (executed: without `add_server`, compile fails "MCP server not found for node type: mcp-corpus-evaluate_script").
  - (c) `_shown_as_inserts` mutates freshly built diagnostics in place, before dedup. That is safe, but it is a string rewrite; the docstring names the limit.
  - test-reflect (directed): every new PC test is killed by at least one of R1–R10 or by PA's M1/M2/M8. Nothing was deleted. Deepened: the ghost row's `forbid=("${ghost.x}",)` and the coalesce test's `"|json ??" not in message` (each paired with an exact positive assertion in the same message). The `registry_run` row lost its phase gate and is killed by R8.
- Post-handback "fully happy?" (orchestrator-directed): `_shown_as_inserts` weighed against the simplicity lens and **kept**.
  - The cleaner shape — the operand carrying its rendered form — is not a contained change. Pass 5 takes bare reference strings and renders them in 13 `${template}`/`${base_var}` f-strings (counted) across its builders in `path_validation.py`, which also use the same string for `parse_path` logic. Pass 8's builders take `ref.raw` too. Threading a display form means rewriting those signatures for a display-only concern.
  - The rewrite is what stays local: one function, applied at the two call sites, limited to references written only as inserts (so it cannot misrender a bare use), and killed by R6/R10.
  - Recorded as a candidate for the mid-task review's simplicity read. No code change.
- Next: hand back for the mid-task review (plan §4 PC: validation-consistency, impact-completeness, silent-failures, feature-interactions). PD waits on it. PE keeps:
  - the guide, docs, `mcp describe` / context-builder snippets and instruction files;
  - the searcher-doc line, which should name `template_surfaces.EMBEDDED_CODE`;
  - the click/hover real runs.

## [2026-10-11 18:20] implementer I1 (gate-runner) — mid-task review of PA–PC: findings and dispositions; ONE finding handed back
- Did: dispatched `workflows/review/run-review-lenses.pflow.md`, provider codex, on `git diff 5ab179fc..69f30eec`.
  - Five lenses, each with its own target (spec + plan + ruled checkpoint + the 12:00 Q1–Q6 extensions; silence = gap): `review-validation-consistency`, `review-impact-completeness`, `review-silent-failures`, `review-feature-interactions`, and `review-simplicity` aimed only at `_shown_as_inserts` and `written_reference`.
  - Backgrounded to `.taskmaster/tasks/task_181/implementation/review-midtask.out` (untracked; kept for the record) and waited in-turn. 249 s; coverage 5/5 lenses produced output, no gaps.
  - Read the report in full. Verified every Critical by reproducing it against the code.
- Findings and dispositions:
  1. **Bare output source with a dynamic index + `|json`** (Critical; 3 lenses). **CONFIRMED, FIXED.**
     - Repro: `normalize_output_source("up.items[${i}]|json")` returned the text unwrapped, so the run published `up.items[0]|json`, and the Issue pass checked only bare sources without `${`.
     - Fix: `normalize_output_source` wraps when `${source}` parses as ONE whole Expression (simple or a JSON insert). The Issue pass checks every output source's normalized form for a misplaced insert (`bare` = the author did not write the `${}`).
     - Tests: parity row `misplaced_insert_output_bare_dynamic_index` (validator Error + runtime `OutputResolutionError`) and `test_a_bare_dynamic_index_output_source_insert_is_the_error`. Mutations V1 (wrap only simple) → 3 red; V2 (bare-only check) → 2 red.
  2. **Validator suggestions that rebuild a DIFFERENT path lose `|json`; mixed bare/insert use of one path suppresses the rewrite** (Critical from impact-completeness, Warning from 3 others; simplicity proposes the redesign). **CONFIRMED — NOT FIXED, HANDED BACK (importance 3).**
     - Examples: Pass 5 `Change ${up.stdot|json} to ${up.stdout}`, Pass 8 `Use ${item.response}`, available-fields lists, `context.similar_names`.
     - This is a gap against ruled §6 ("every template and every suggestion keeps `|json`"). Closing it is a design choice across ~50 `${…}` render sites in `path_validation.py` / `batch_item_validation.py` (counted), so it is not a contained fix. Options below.
  3. **Near-miss inserts with an inner `}`** — `${{}|JSON}`, `${rows[${i}]|JSON}` (Critical; 2 lenses). **CONFIRMED, FIXED.**
     - Repro: the Issue ends at the first `}` (`${{}`), so `near_miss_insert` found nothing.
     - Fix: new `templates.balanced_template(source, start)` (the brace-balanced `${…}`). `near_miss_insert(source, issue)` now reads that and returns `(as written, meant)`. The validator's private `_balanced` was deleted, so one helper has one home.
     - Tests: two new near-miss rows (explicit written/meant columns) and `test_a_near_miss_around_inner_braces_is_the_error`. Mutation V3 → 3 red.
  4. **Hidden insert inside another Expression's literal operand** — `` `${"${ghost.value|json}"}` `` (Critical; silent-failures). **CONFIRMED, FIXED.**
     - Repro: `finditer` consumed the outer match.
     - Fix: `hidden_inserts` tries every `${` opening (overlapping). The §7a container is any non-Text segment spanning the insert, so the message says "inside another '${…}'", not "'$${…}'".
     - Tests: hidden-insert rows (`` `${"${x|json}"}` ``, `$${a[${i}]|json}`) and `test_an_insert_inside_a_bare_expression_literal_is_the_error`. Mutations V4 (non-overlapping) → 2 red; V7 (container = Issues only) → 1 red.
  5. **A multi-root bare expression reports only its first root** — `` `${a ?? b}` `` (Warning; 2 lenses). **CONFIRMED, FIXED.**
     - Fix: `embedded_references` yields one record per in-scope root, so each unused input gets its own §4a ERROR (Q2) and leaves the generic unused report. `_bare_reference_warning` dedupes fixes per expression, and singular/plural follows distinct expressions; the ruled singular and Q4 plural texts are unchanged.
     - Tests: `test_4a_every_input_of_a_coalesce_gets_its_own_error`, `test_4b_a_coalesce_of_two_scoped_roots_lists_both_owners_and_one_fix`. Mutations V5 → 2 red; V6 (plurality by record count) → 1 red.
  6. **`trace_report` scans a failed embedded param's `template_resolutions` with the ordinary view, so a bare JS `${other.missing}` can draw a "key not found" suggestion; the report also shows the insert's path without `|json`** (Warning; 2 lenses). **CONFIRMED, SKIPPED (importance 2).**
     - The report cannot apply the embedded policy: a trace node event carries only the class name (`node_type: "MCPNode"`, executed on the real-run trace), not the IR type `param_mode` needs.
     - The case is narrow: `template == resolved` means every insert in the param stayed unresolved (permissive mode), and the JS name must be rooted at a step id with the field missing. The effect is one extra report suggestion, never a wrong run.
     - The `${path}` it prints is a path description, not a paste-able fix.
     - D9's headline (an unresolved insert names `up.missing`, not `missing|json`) holds and is tested.
  7. **`registry_run` success drops the §4d warning** (Critical; silent-failures). **SKIPPED — pre-existing, not this task's.**
     - Task 118's task-review already records "MCP `registry_run` success never forwards validation warnings (pre-existing…)".
     - The finding is true for every warning class, not one introduced here. Follow-up for the merge seam.
  8. **Suggestion: extend the consumer/parity matrix.** Taken where it guards a fixed bug: bare dynamic-index output source (row), multi-root expressions (2 tests), overlapping hidden insert, inner-brace near-miss. The "identifier-shaped JS in failed traces" row is not added (#6 skipped). "Corrections to different paths" waits on #2.
  - **Simplicity, verified clean by the lens:** `written_reference` earns its keep (several callers share the suffix decision); `TemplateOperand.as_json` is useful provenance. Its one finding is #2.
- Changed:
  - `src/pflow/core/templates.py` (`hidden_inserts` overlap-aware; `balanced_template`; `near_miss_insert(source, issue) -> (written, meant)`);
  - `src/pflow/runtime/output_resolver.py` (`normalize_output_source`);
  - `src/pflow/runtime/template_validation/validator.py` (Issue-pass output sources, §7a container, near-miss call, `_bare_reference_warning`);
  - `src/pflow/core/workflow/data_flow.py` (per-root records);
  - tests: `test_core/test_templates.py`, `test_integration/test_embedded_code_diagnostics.py` (+5), `test_integration/test_template_parity.py` (+1 row).
- Verified: `make check` rc 0; `make test` 10920 passed (PC 10909; +11). Mutation ledger V1–V7 above, each a counted failure, restored from byte copies. | Assumed: nothing.
- Deviations/surprises:
  - #1 also changes `normalize_output_source` for runtime callers. The only newly wrapped shapes are whole-expression JSON inserts (an `is_simple` wrap ⊂ one-whole-Expression; the difference is exactly `as_json`). The full corpus and suite are green.
  - The fixes kept the ruled message texts. #5's plural head is Q4's form, and its singular head with two owners uses Q3's nouns joined with "and".
- **HANDED BACK — #2, options (importance 3: a validator-wide design choice, closing a gap against ruled §6):**
  - **(A) Thread `as_json` through Pass 5 / Pass 8 (RECOMMENDED).**
    - `validate_template_paths` takes `(raw, as_json)` pairs; Pass 8 keeps `TemplateOperand`.
    - One render primitive (`diagnostic_render.written_reference`, already there) at every builder site — the original path, changed paths, available fields and `similar_names`.
    - Deletes `_shown_as_inserts`, `_insert_references` and the workflow-wide "insert-only" rule; mixed use resolves naturally because each operand renders its own form.
    - Cost: signature churn across ~12 builders / ~50 render sites; reversible; mechanical; existing tests unaffected with `as_json` defaulting to False.
    - It is the shape the simplicity lens named as the simplest final code.
  - **(B) Broaden the rewrite:** per diagnostic, suffix every `${…}` rooted at the insert's root. Small, but still a post-hoc string rewrite, still workflow-wide for mixed use, and it guesses at intent.
  - **(C) Accept the gap:** only changed-path suggestions stay bare; the original reference, messages and runtime fixes keep `|json`. Record it for the user as a deviation from §6.
  - My recommendation: (A), built by me now as a contained follow-up phase before PD. My window is healthy.
- Self-checks: fully happy with the six dispositions. The doubt is #2 itself, handed back rather than absorbed. test-reflect: every review-fix test is mutation-killed (V1–V7); no shallow test was added; nothing was deleted.
- Next: the orchestrator rules on #2 (A/B/C). Then, if (A), I build it with tests and re-run R6/R10 plus the new mutations.

## [2026-10-11 18:40] task orchestrator — ruling on mid-task finding #2: option (A)
- Did: read the 18:20 dispositions (6 fixed/skipped with reasons — accepted, incl. #6 skip and #7 as a merge-seam follow-up already in 118's review). Ruled #2 = **(A) thread `as_json` through Pass 5 / Pass 8**, render every rebuilt `${…}` via `written_reference`, delete `_shown_as_inserts` / `_insert_references`.
- Why within my authority (importance 2, not 3): (A) is the shape that *meets* the user's ruled §6 ("every suggestion keeps `|json`"); no user-visible fork remains, it is internal and reversible. (B) keeps a post-hoc string rewrite; (C) would deviate from a ruling — that one would have needed the user.
- Committed the mid-task fixes as one commit (review-midtask.out stays untracked).
- Next: I1 builds (A) with tests + mutations; then fresh I2 on PD.

## [2026-10-11 19:30] implementer I1 — review finding #2, ruling (A): references rendered at the source; the rewrite deleted
- Did: built ruling (A).
  - **One primitive.** `diagnostic_render.written_reference(text, *, as_json=False)`. The runtime renderer calls it through a tiny `_inserted(ref)`, because a quoted dict lookup cannot sit inside a 3.10 f-string.
  - **Pass 5 (`path_validation.py`).** `validate_template_paths` takes `(raw, as_json)` pairs. A keyword `as_json` threads through `validate_template_path`, `validate_namespaced_output`, `_batch_results_index_error`, `create_template_diagnostic` and the node-reference / path / simple / enhanced / batch / batch-inner builders.
    - `validate_nested_path` and `check_type_allows_traversal` now receive the reference already written. That removes their two `startswith("${")` guesses.
  - **Pass 8 (`batch_item_validation.py`).** It keeps the `TemplateOperand` and passes `as_json`. Its dedupe key is `(path, as_json)`.
  - **Deleted:** `validator._shown_as_inserts`, `_insert_references` and the workflow-wide "insert-only" rule.
- **Shape chosen, as the ruling asked:** a bool keyword per builder, not a value type. A value type would ride the same path; every builder still renders with it and still needs the raw text to parse. The bool keeps signatures readable, and `as_json=False` defaults leave every untouched caller's output unchanged.
  - The diff is about +170/−160 in five files.
  - The final code has no post-hoc rewrite. Each `${…}` a builder prints goes through `written_reference`; the bare ones are deliberate.
- **Which renders stay bare, on purpose:**
  - root mentions (`'${nod}' is neither…`, `Required input '${x}'`), matching the ruled §6 text;
  - references the fix sends elsewhere: `items: ${n.results}` (batch items) and "pass `${n.results}` to a code node".
  - Everything shown or suggested in the author's place is rendered: the original reference, changed paths (`Change ${up.exit_cod|json} to ${up.exit_code|json}`), `Or use` / `Try` / `Use`, available-field lists, `similar_names` and `context.template`.
- Changed:
  - `src/pflow/core/diagnostic_render.py`
  - `src/pflow/runtime/engine/template_errors.py` (call shape)
  - `src/pflow/runtime/template_validation/{path_validation,batch_item_validation,validator}.py`
  - `tests/test_integration/test_embedded_code_diagnostics.py` (+4 tests)
- Verified:
  - `make check` rc 0; `make test` 10923 passed (+3 vs the mid-task fixes).
  - §6 still renders verbatim (p6 probe).
  - **Mutation ledger** (counted failures; restored from byte copies):
    - W1 = R6 re-run (Pass 5 renders bare) → 3 red: §6, changed-path, mixed-use;
    - W2 (the changed path rendered bare) → 2;
    - W3 (Pass 8 renders bare) → 3;
    - R10 re-run (`TemplateOperand` never `as_json`) → 6;
    - W4 (Pass 5 dedupes by path only) → 3.
  - Every new test has a presence pair in the same medium: the bare twin's suggestion, in the same workflow for Pass 8.
- Deviations/surprises:
  - **Mixed use in Pass 5 dedupes at display.** Pass 5's "Node 'up' … does not output 'exit_cod'." names the producer, not the consumer. So two consumers of one missing path (a bare prompt and an insert) now produce two diagnostics with identical messages and different suggestions, which `deduplicate_diagnostics` collapses to the first — the bare one — on the CLI (executed).
    - The structured diagnostics are each correct (`test_pass_5_mixed_use_renders_each_reference_in_its_own_form`, pre-dedup).
    - Pass 8 names the consumer step, so both show there.
    - Making both visible in Pass 5 would mean new message text on an existing non-ruled diagnostic; not done. The visible outcome equals the pre-(A) one, and the structure is now right.
  - The finding's example `stdot` reaches Pass 5's "Try …" branch (no similar path); the tests use `exit_cod`, which reaches the "Change … to …" branch.
- Self-checks: fully happy. The one doubt — the Pass 5 display dedupe on mixed use — is resolved as documented above, not absorbed silently. test-reflect: W1–W4 + R10 kill every new test; no shallow test; nothing deleted.
- Next: back to the orchestrator; PD/PE not started.

## [2026-10-11 02:11] implementer I2 — PD web: one `${…}` walk (`templateTokens`), param modes on every reader, #683
- Did: built D10. `scan.ts:templateTokens(text, mode)` is the one TS walk (mirror of `_tokenize`; `"embedded"` = `embedded_code`; `"body"` = one text token); `templateRefs` derives from it; `paramTextReads` reads `param.mode`. `parseTemplate(text, mode)` / `refMatchesHighlight` (parsed operands), `batchItems.ts` (alias substitution over tokens; an insert enters as `JSON.stringify`), `sourceDecorate.ts:refSegments` all go through it. `param.mode` is threaded to WorkflowNode `ParamValue` (chips), ParamBlock's `CodeBlock`, the per-item preview, `CodeBlock` → `ExpandableBox` → modal, and `markRefs`. `isCodeBody` deleted.
- Changed: `web/src/graph/{scan,sourceDecorate}.ts`, `web/src/utils/{format,batchItems,highlight}.ts`, `web/src/components/{CodeBlock,ReadPanel}.tsx`, `web/src/components/nodes/WorkflowNode.tsx` (`ParamValue` exported for its test); tests `graph/scan.test.ts`, `graph/sourceDecorate.test.ts`, `utils/{format,batchItems,highlight}.test.ts`, `components/ParamBlock.test.tsx`, new `components/nodes/WorkflowNode.test.tsx`; `web/src/graph/CLAUDE.md`, `web/src/utils/CLAUDE.md`.
- Verified:
  - **Gates:** `npm run typecheck` rc 0; `npm test` 56 files / 905 passed (baseline 55 / 845; +60, 0 failures); `make check` rc 0; `make test` 10923 passed (= baseline 10923; no Python touched).
  - **Python-vs-TS differential (executed, scratch, not committed):** Python `parse()` + `embedded_code()` dumped for 485 sources (test_templates `FUZZ` + `SHAPES`, `GRAMMAR_ROWS`, every parity-corpus template, the PA-6 view source, the real-run JS) vs `templateTokens(…, "template" | "embedded")`: every Expression/Issue span, `asJson`, operands and refs (root + fields) equal — 0 diffs over 332 tokens (93 Issues, 26 embedded inserts). The comparison was shown live (a first run with key-order-sensitive compare reported 199 "diffs").
  - **Mutation ledger** (`npx vitest run --reporter=json`, counted failures, byte-copy restore): M1 embedded reads as template → 9 red; M2 embedded keeps every expression → 8; M3 body reads as template → 2; M4 escape read as an opening → 17; M5 `parseTemplate` back on the old escape-blind regex → 23; M6 `refSegments` escape-blind → 4 (every tier); M7 `refMatchesHighlight` back to `split("??")` → 2; M8 insert substituted via `fullValue` → 2; M9 insert substituted outside embedded → 1; M10 `substitute` ignores mode → **0 — equivalent mutant** (`aliasPath`'s asJson-vs-mode gate already confines substitution to inserts in embedded code; body never reaches `substitute`); M11 chips drop mode → 1; M12 ReadPanel batch drops mode → 2; M13 per-item `CodeBlock` drops mode → 1; M14 main `CodeBlock` drops mode → 2; M15 modal drops mode → 1; M16 `markRefs` drops mode → 1; M17 read scan drops mode → 4; M18 TS `JSON_INSERT` dropped → 27; M19 Issues as refs → 3; M20 batch escape-blind → 2.
  - **UI acceptance** (`pflow ui --no-open --port 8781`, `make ui-build`, chrome-devtools MCP pinned 1.10.1; workflow `scratchpad/t181pd/embedded-ui.pflow.md`: `up` (stdin `${user}`), `probe` = evaluate_script with a ```` ```javascript function ```` fence holding `${up.stdout|json}`, `` `${a + b}` ``, `${user.name}`, `` `$${price}` ``; `per-person` = batched evaluate_script with inline `- function: |` holding `${item.name|json}` and `` `${item.id}` `` over items Ann/7, Bo/8; `--validate-only` valid with the two §4b warnings). DOM read by a scratch probe workflow (`scratchpad/t181pd/dom-probe.pflow.md`, itself using `${click|json}`):
    1. Canvas: `probe.function` chips = `["up.stdout|json"]`, `per-person.function` = `["item.name|json"]`; no chip for the JS. Shots `/tmp/pflow-shots/t181pd/embedded-ui-advanced-LR-none-per-person-12-20261011-020956.png` (chip `item.name|json`, then `` `${ite… `` as plain text) and `…-probe-2-20261011-020750.png` (the probe row's chip lands past the row's width and the row's existing overflow ellipsis clips it; the DOM read is the evidence).
    2. Edges: payload `e3 n1→n2 input_name=function` (up.stdout) and `e2 n0→n1 stdin`; nothing from `user` to `probe`. `visual-invariants`: `passed`, contract 4 / dom 5 (the extra is `io-flow:`), no missing, no bad extras.
    3. Read panel: only `${up.stdout|json}` is teal (DOM `teal: ["${up.stdout|json}"]`); shot `…-probe-3-20261011-020806.png`.
    4. Source pane (no param mode, read as a Template): fence line 37 `${up.stdout|json}` teal, line 38 `${a + b}` plain (an Issue), line 39 `${user.name}` teal, line 40 `$${price}` plain; inline line 52 `${item.name|json}` and `${item.id}` both teal. Shots `…-probe-1-7-20261011-020902.png`, `…-per-person-1-8-20261011-020911.png`. Documented in `web/src/graph/CLAUDE.md`.
    5. Batch preview: items read `() => ["Ann", \`${item.id}\`]` / `() => ["Bo", …]`, no teal in either; the raw value teals only the insert. Shot `/tmp/pflow-shots/t181pd/batch-preview.png` (via `click.pflow.md`, `selector='.batch-expand'`).
  | Assumed: nothing about the shipped behaviour; the per-tier source-pane rows hold for the real shiki tier by the same `refSegments` path (asserted on the mock tiers + seen in the screenshots).
- Deviations/surprises:
  - **D10's source-pane premise is false on this code:** a ```` ```javascript function ```` fence has no grammar (`fenceGrammar` → null), so it teals like the inline form; both teal pflow-shaped `${…}` (`${user.name}`, `${item.id}`) and leave Issues/escapes plain. The CLAUDE.md limit states what is true, not D10's "fence shows no teal".
  - **`isCodeBody` is replaced by passing the mode, not by `=== "body"` gates:** `templateTokens(…, "body")` reads nothing, so `paramTextReads` and ReadPanel lost their gate lines entirely.
  - **`RFParam.mode` stays optional** (`mode?: ParamMode`): production code is identical either way (every reader's `mode` parameter defaults to template), and requiring it would add `mode: "template"` to ~85 hand-built test literals. The two old kind/name-keyed tests (scan "code bodies", ParamBlock body) were rewritten as mode-keyed rows; the kind → mode decision is Python's and tested there.
  - **`BatchItems.tsx:47` takes no mode:** it renders a batch ITEM's field, not a param's text, so it reads as text without a param (template) — D10 listed it among param renderers.
  - **Behaviour changes beyond embedded code (intended, grammar-faithful):** an Issue (`${ x }`, `${a + b}`) in a Template param is no longer a chip/teal/substitution anywhere; the batch preview no longer substitutes `${ item.x }`; it does substitute hyphenated names (`${item.first-name}`, the grammar's `IDENT`); a misplaced `${item.x|json}` in a Template param is kept as written in the preview (the run keeps it, D4).
  - **#683 is closed for its body (the three grammar copies), not for its comment's second clause** — the preview renders `true`/`null` where a shell command receives `True`/empty (`templates.to_string`). D10 does not cover it, and a faithful mirror needs simple-vs-complex and `binds_as_text` knowledge. Recommend: keep #683 open for that clause or file it separately.
  - **One stale Python line outside PD's files (not edited — orchestrator's call):** `src/pflow/core/workflow/template_surfaces.py:29` says "TypeScript mirror: web/src/utils/format.ts::isCodeBody — change both together." There is no TS mirror now; suggested edit: delete the line (the web reads `RFParam.mode`).
  - **Not moved onto the walk:** `graph/flow.ts:bindingParam`'s `v.includes("${")` — a presence check gated on an existing contract edge whose `input_name` is that dict key, not a decoration reader; it can only misattribute when two dict params share a key and one holds only an escape. Left as is.
- Self-checks: fully happy — doubts raised: (a) the differential is the only cross-language proof and lives in scratch; a committed version needs a Python-generated fixture plus a Python drift test (outside PD's files) — candidate follow-up, recommended alongside Task 170's same uncommitted check; (b) the probe row's chip is clipped by the row's existing overflow ellipsis (18 chars of leading code plus the chip exceed the row) — pre-existing row behaviour, not this phase's. test-reflect (directed): the SHAPES table can only pin a slice, so the mirror claim rests on the differential (executed, 0 diffs) — table kept as the in-tree guard (M4/M18 kill it); deepened `refMatchesHighlight` with the `gen.res` boundary row and the literal-operand row; added the tiling invariant across all three modes (lost/overlapping text would pass `show()` only if the slices still reassembled); M10 documented as equivalent rather than covered by a test; nothing deleted — every absence row has its presence twin in the same medium (template-mode chips/teal/reads/substitution beside each embedded/body/escape row).
- Tooling postmortem (screenshot skill): worked well — `screenshot`/`click`/`visual-invariants` against a non-default port and an absolute scratch `workflow=` path; `focus=<node>` opens the ReadPanel, so check 3 needed no click. Items for disposition:
  - **S — `visual-invariants.pflow.md` input properties use `* ` bullets** (8 lines), which the parser reads as description text, so `out_path` (documented `required: false` + default) is required: the skill's own example command (`… url=… -p -o verdict`) fails with "Workflow requires input 'out_path'". Same on `origin/main`. Fix: `- ` bullets (or make the parser accept `*`, which `sourceDecorate.ts:KEY_RE` already colours as a key).
  - **M — no DOM-text reader in the suite:** `inspect` returns geometry only, so "which chips / teal spans exist" needed a hand-written probe workflow (open-and-settle + one evaluate_script). A `read.pflow.md` taking a CSS selector and returning text/class lists would cover every decoration check.
  - **S — a param row's overflow ellipsis clips a chip that does not fit**, so a screenshot cannot show a chip the DOM has; worth a line in the skill ("assert chips via the DOM, not pixels").
- Next: hand back; PE not started. `dev servers: none` (the 8781 server, PID 39384, stopped).
- Post-handback "fully happy?" (orchestrator-directed): no code change.
  - (a) `mode?` stays optional. Requiring it changes no reader: every reader passes `param.mode` into a `mode` parameter that keeps its `"template"` default for text that has no param (the source pane, run values, item fields). It would only tighten the type and add `mode: "template"` to ~85 test literals.
  - (b) Executed a scan of every in-tree `.pflow.md` (`examples/`, `workflows/`; 72 parse, the 8 that fail are `examples/invalid/`): **0 Issues** in any Template param, so no example loses a chip or teal to the Issue change. **One escape**: `examples/nodes/agent/claude-schema.pflow.md:93` `*Review cost: $${review.llm_usage.cost_usd}*` — the run writes the literal `${review.llm_usage.cost_usd}` (executed via `templates.resolve`). The old UI drew a chip there, which was the #683 false claim; the new UI shows the literal text the run sends. This is a pre-existing example bug (the author meant `$` + the value), not a UI regression. It is outside PD's files; the fix is to keep the dollar sign apart from the reference (e.g. `USD ${…}`), for the orchestrator to route.

## [2026-10-11 03:00] task orchestrator — PD verified + committed (`416a0416`); dispositions; PE routed to I2
- Verified: I2's PD entry + "fully happy?" (clean; `mode?` kept optional with reason; no in-tree example regresses). Gates as logged (web 905, `make test` 10923). UI slot: granted to I2 on port 8781 (not 8765 — reuse-if-up would serve another checkout); stopped at handback.
- Dispositions of I2's items:
  - stale `template_surfaces.py:29` "TypeScript mirror: …isCodeBody" → fix in PE.
  - #683 second clause (preview shows `true`/`null` where sh receives `True`/empty) → not D10; follow-up for the merge seam; PR says `Refs #683` for that clause unless main files it separately.
  - D10's fence premise was wrong → `web/src/graph/CLAUDE.md` states the true behaviour (accepted).
  - Committed Python-vs-TS differential → follow-up candidate (merge seam), alongside Task 170's same uncommitted check.
  - `examples/nodes/agent/claude-schema.pflow.md:93` `$${…}` (pre-existing, unrelated to this task) → merge-seam follow-up, not this PR.
  - Tooling postmortem: (S) `visual-invariants.pflow.md` `*` bullets make `out_path` required → **fix in this PR (PE)**; (S) chips clipped by row ellipsis → one skill line in PE ("assert decorations via the DOM, not pixels"); (M) no DOM-text reader workflow → issue at merge seam (not built here).
- Rotation: I1 is past ~600k cumulative (plan: rotate past ~350k) → PE goes to I2 (holds the rule + screenshot tooling; ~265k).
- Next: I2 on PE.

## [2026-10-11 02:30] implementer I2 — PE: snippets, guide, docs, instruction files, screenshot tooling
- Did: built PE (§4 PE plus the §5 inventory) and the 03:00 additions.
  - **Snippets:** `pflow mcp describe` and the component context share two new helpers in `registry/context_builder.py`. `param_note` appends `(JavaScript, sent as written; insert a pflow value as ${x|json})` to an embedded param's line. `snippet_placeholder` shows `() => ${previous-step.response|json}` for it. Describe lazy-imports both.
  - **Guide:** `guide/nodes/mcp.md` gains "Code Passed to a Tool" and a one-sentence pointer in its "JSON string" paragraph; `guide/core.md` gains one line under "Template Variable Complete Reference".
  - **Docs:** `docs/reference/nodes/mcp.mdx` gains "Code passed to a tool". `docs/how-it-works/template-variables.mdx` loses "JavaScript template literals work the same way" and gains "JavaScript passed to an MCP tool", with a link.
  - **Architecture:** `architecture/reference/template-variables.md` adds the JSON insert to the grammar list and to "Node parameters", and gains a new section, "Embedded Code (JavaScript in MCP Tool Params)".
  - **Instruction files:** `runtime/template_validation/CLAUDE.md`, `core/workflow/CLAUDE.md`, `core/workflow/graph/CLAUDE.md`, and the searcher doc's location map.
  - **Stale line:** deleted `template_surfaces.py:29`.
  - **Screenshot tooling:** `visual-invariants.pflow.md` input bullets changed `*` → `-`; one SKILL.md line says chips and teal spans are asserted through the DOM, not pixels. Then `make sync-claude-assets`.
- Changed:
  - `src/pflow/cli/commands/mcp.py`, `src/pflow/registry/context_builder.py`, `src/pflow/core/workflow/template_surfaces.py`;
  - `src/pflow/guide/{core.md,nodes/mcp.md}`; `docs/reference/nodes/mcp.mdx`, `docs/how-it-works/template-variables.mdx`; `architecture/reference/template-variables.md`;
  - `src/pflow/runtime/template_validation/CLAUDE.md`, `src/pflow/core/workflow/CLAUDE.md`, `src/pflow/core/workflow/graph/CLAUDE.md`;
  - `.claude/agents/pflow-codebase-searcher.md` and `.codex/` mirror; `.claude/skills/screenshot-pflow-web-ui/SKILL.md` and `.agents/` mirror;
  - `examples/real-workflows/screenshot-pflow-web-ui/visual-invariants.pflow.md`;
  - tests: two new rows in `tests/test_integration/test_embedded_code_consumers.py`, describe and component context. Both use the real registry via `register_mcp_tool`. Each asserts exact lines, and the same tool's `label` param keeps the plain reference as the presence pair.
- Verified:
  - **Gates:** `make check` rc 0 (includes the asset-sync check and `check_mdx_fences`). `make test` 10925 passed (baseline 10923, +2). Web untouched.
  - **Mutations** (counted failures, byte-copy restore): P1 `param_note` never notes → 2 red; P2 placeholder ignores embedded → 2; P3 describe passes no node type → 1 (describe); P4 component context passes no node type → 1 (context).
  - **The 03:00 checks:**
    - PC's four sites are in place (`click.pflow.md:81-83`, `hover.pflow.md:56` use `|json`). No "single-quoted JS" / "double quotes inside" / "template literals work the same way" text remains in `docs/`, `src/pflow/guide/`, `examples/`, `.claude/` or `architecture/`.
    - The MCP instruction resources hold no JavaScript or `$${` content (checked, not stale).
  - **Real surface** (`pflow ui --port 8781`, PID 63394, stopped):
    - `click.pflow.md` with `selector='button' text="Don't exist"`: exit 1 with the workflow's own `click target not found: 12 elements match selector "button", none with text "Don't exist" (texts: ["","advanced","beautiful",…])` — no JS SyntaxError (#550).
    - The same with `text="beautiful"`: exit 0, it clicks (shot `/tmp/pflow-shots/t181pd/click-hit.png` shows the density switched to beautiful).
    - `hover.pflow.md`: `row_name=command` on `conditional-branching` → `{"ringedNodes": 0, "haloedEdges": 0}`; it is a body row with no edges. `row_name=function` on the PD acceptance workflow → `{"ringedNodes": 1, "haloedEdges": 1}`, the insert's edge from `up`.
    - `--validate-only` on all seven screenshot workflows (`click`, `hover`, `inspect`, `live-reload`, `screenshot`, `visual-invariants`, `shared/open-and-settle`): each `✓ Workflow is valid`, no warnings.
    - `visual-invariants.pflow.md url=… -p -o verdict`, **without `out_path`** (the skill's own example form): exit 0, `passed: true`.
    - `uv run pflow mcp describe mcp-chrome-devtools-evaluate_script`: `- function: str (required) (JavaScript, sent as written; insert a pflow value as ${x|json}) - A JavaScript function declaration…`, and the snippet `- function: () => ${previous-step.response|json}` (`pageId: value`, `args: ${previous-step.response}` unchanged).
  - **Guide/docs examples:** the guide's `check-title` fragment and the docs' were each wrapped in a scratch workflow that declares their inputs. Both `--validate-only` ✓ valid, no warnings. The architecture example's resolution was executed (`resolve(…, embedded=True)` gives ``() => ({title: "Don't Stop", label: `${a + b}`})``).
  - **The #722 clause** is verified, not assumed: `validate_execution_parameters({"function": "() => eval(${gen.code|json})"})` → `(False, 'Suspicious pattern detected: eval\s*\(')`. It applies at `run_registry_node` (`execution_service.py:680`) over params. `execute_workflow` checks only input values, so `eval(` written in a workflow's step is not refused there.
  - | Assumed: nothing beyond the bullets.
- Deviations/surprises:
  - **Plan's guide bullet "`$${` … the opposite of a shell command, where it is an escape" is false after Task 118.** In a shell command `$${` is a validation error (`guide/nodes/shell.md:51`). The guide contrasts instead with templated params ("pflow's escape only in a templated param (a prompt, `stdin`)").
  - **One snippet rule, not two copies:** describe and the context builder each carried the same placeholder ladder. PE edits both, so the ladder moved to `context_builder.snippet_placeholder`, and the param note to `param_note` — one home each.
  - **An existing test caught a legacy param shape:** `test_workflow_manager_integration::test_context_builder_lists_saved_workflows` passes params with `name`, not `key`, so `_format_single_param_line`'s `key` is the dict itself. The note is computed only for a string key (commented at the site).
  - **The docs harness checks none of the new examples.** They are fragments (no `## Steps`), and the harness skips `mcp-*` blocks anyway. They were validated by hand (above); a future edit to them has no CI guard. The plan's `_BARE_VAR_RE` note is moot: the harness already collects bare names from parsed references (Task 118).
  - **Guide placement:** the new section sits after the whole "Choosing Tools for Deterministic Steps" section (its Slow calls and Server lifetime paragraphs included), before "Node Creation Pattern". The plan's `:107-115` points mid-section.
  - `context/CONTEXT.md` not edited (R8 nouns are the main orchestrator's).
- Self-checks: fully happy; one doubt kept open — the hand-validated guide/docs fragments have no CI guard (above). test-reflect: not needed — two exact-line tests through the real registry, killed by P1–P4, each with a same-output presence pair (`label`'s plain reference).
- Next: hand back. `dev servers: none`.

## [2026-10-11 02:40] task orchestrator — PE verified + committed (`04fc8a57`); main merged; PZ gates + spec Verification walked
- Did: committed PE; merged `origin/main` (#765 #764 #770 #771) cleanly; `make install`. Gates on the merged tree (outputs kept in orchestrator scratch, not committed): `make check` RC 0; `make test-all-local` 11002 passed, 2 skipped; `verify.sh` 74 pass / **13** drift / 0 harness errors; `capture.py --check` 29 examples, 5 differing.
- Verified:
  - verify.sh: the 12 P0 drift cases + ONE new `03-analyze-cache-modes/07-json-error-envelope-unknown-workflow` — its diff is "Workflow … not found" → "No file at: …" / "Check your working directory" = #771 (`a4d4a6df`, merged from main tonight), not this task (no template/MCP content in the case). capture: the same 5 `error-handling/*` examples as P0 (#754's `"result": {}`).
  - **Spec Verification, real surface** (`uv run pflow` → live chrome-devtools `evaluate_script`, batched, alias `item`, input named `user`; probe in orchestrator scratch `t181/orch/verify.pflow.md`): output `{"u": "js-user", "s": "3", "i": "9", "p": "Total: $5", "t": "Don't Stop", "o": {"a": [1, 2]}, "in": {"name": "pflow-user"}, "it": "first", "on": true}` — JS's own `${user.name}`/`${a + b}`/`${item.id}` reached the tool unchanged and evaluated in JS; `$${price}` arrived with both dollar signs (JS rendered `$5`); `Don't Stop` a valid string literal; boolean `true`; object literal. Validate prints the §4b plural WARNING (ruled Q4 shape). `${nod.result|json}`: `--validate-only` and the run both fail with "Node 'probe' references non-existent node 'nod' in parameter 'function'" (agree). Screenshot workflows: PE's runs (02:30 entry).
- Deviations/surprises: verify.sh drift 12 → 13, explained above (not a trace-format change; this task did not touch the trace format).
- Next: commission the code-mode deep-review gate (fresh Opus gate-runner — I1 ~640k and I2 ~380k are both past the rotation point); falsifier launched by me after the reading battery's fixes land.

## [2026-10-11 02:52] gate-runner G1 — completion gate (code-mode deep-review): 14 findings — fixed 9, skipped 5, handed back 0
- Did: dispatched `workflows/review/run-review-lenses.pflow.md`, provider codex, on `git diff origin/main...HEAD` at `87119e6c`; backgrounded to `implementation/review-gate.out` (untracked), waited in-turn (494 s, 11/11 lens runs produced output, no failed lenses). Read the report in full; verified every Critical/Warning against code by execution where cheap; fixed, tested, mutation-checked.
  - **Lenses and partition** (every target named spec + plan + ruled checkpoint + the 12:00 Q1–Q6 / 18:40 option-(A) rulings + ADR-0016, "silence = coverage gap", and listed the settled items): `review-silent-failures` ×2 (Python grammar/validator/runtime; `web/`), `review-test-fidelity` ×2 (Python tests; web tests + contract fixtures), `review-validation-consistency` ×2 (validator vs runtime twin; Python grammar/graph vs the TS mirror + its readers), `review-agent-ux` (messages, `mcp describe`/context snippets, guide/docs/instruction files); whole diff: `review-impact-completeness`, `review-feature-interactions`, `review-simplicity`, `review-spec-conformance`. `review-falsifier` not launched (orchestrator's, after these fixes).
  - **Coverage:** every lens reported; each self-declares "changed hunks + callers, not every touched file read end-to-end" (standard caveat, not a failed lens). Every lens addressed the checkpoint, Q1–Q6, option (A) and ADR-0016 explicitly; none re-opened a settled item without new evidence (C7 below re-raises the 19:30 mixed-use limit and says so — no new evidence).
  - **Requirement Inventory** (for the falsifier): 70 rows, `implementation/review-gate-spec-conformance.out` (the lens's raw output, extracted from the fan-out trace `~/.pflow/debug/workflow-trace-9177e18b-run-review-lenses-20261011-022957-851660.json`; untracked). Its two non-MET rows (#36 MISSING, #39 PARTIAL) are C6 and C2/C3 below — both fixed.
- **Findings and dispositions** (C = convergent, K = Critical, W = Warning, S = Suggestion):
  1. **C1 — near-miss detection misses a quoted `}`** (`${"}"|JSON}`, `${a ?? "}"|JSON}`; Critical ×2, Warning ×1). CONFIRMED (executed: `near_miss_insert` → None; embedded resolution sends it verbatim). FIXED: `templates.balanced_template` skips a whole `"…"` string (one regex, `_BRACE_OR_STRING`); an unterminated quote degrades to the old brace count. Tests: two `near_miss_insert` rows (written/meant). Verified through the CLI (§7b text, `→ Write ${"}"|json}`). Mutation = the pre-fix code: both rows red.
  2. **C2 — reserved-name diagnostics drop `|json`** (`${__index__.x|json}` → "Use bare `${__index__}`"; 4 lenses). CONFIRMED (executed). FIXED: `_reserved_internal_key_diagnostic` takes `as_json`; the shown template and every suggested reference render via `written_reference` (`${__index__|json}`, `${item|json}`, `${item.field|json}`, `${__iteration__|json}`, "Only `${__index__|json}`…"). The `checker.result ?? 0` seed stays bare (it belongs to another step). Test `test_a_reserved_name_inside_an_insert_is_corrected_as_an_insert` (3 cases + the bare presence pair in an llm prompt). Mutation G2 (call drops `as_json`) → 1 red.
  3. **C3 — the no-declared-inputs diagnostic drops `|json`** (`…like ${node_id.field}`; 3 lenses). CONFIRMED (executed). FIXED with S3 below: the three undefined-input branches render the author's reference, the suggestion and `context.template`/`similar_names` via `written_reference`. Test `test_an_undeclared_input_inside_an_insert_is_corrected_as_an_insert` (+ bare pair). Mutation G3 → 1 red. Real CLI: `→ … like ${node_id.field|json}.`
  4. **C4 — TS `\w` (ASCII) vs Python `\w` (Unicode) in `_IDENT`** (`${item.café|json}` gets no chip/teal/preview). CONFIRMED by reading; SKIPPED — pre-existing in Task 170's grammar copy (`origin/main:web/src/graph/scan.ts:58`), display-only; closing it means choosing one identifier alphabet for both languages (a grammar decision). Follow-up: add the row to the merge-seam "committed Python↔TS differential" follow-up the orchestrator already holds.
  5. **C5 — `\s` differs between Python and JS** (`|<U+FEFF>json`, `|<U+0085>json`). CONFIRMED by reading; SKIPPED — same class as C4: `_JSON_INSERT` copies the existing `??` spacing convention, which has the identical mismatch on main; inputs need invisible Unicode separators. Same follow-up.
  6. **C6 — the guide omits the ruled §4d limit** ("`` `Hello ${name|json}` `` is not detected; the guide says so"; spec-conformance #36 MISSING). CONFIRMED. FIXED: one sentence in `guide/nodes/mcp.md`'s quotes bullet — what it sends (`Hello "Ann"`) and the fix (assign to a constant, interpolate it, as the example's `label` does). Docs-only; no test (the guide harness covers rendering, `make check` green).
  7. **C7 — Pass 5 mixed bare/insert use: display dedupe keeps only the bare fix** (Warning, agent-ux). SKIPPED — settled: I1's 19:30 deviation, accepted with option (A); the lens names it as that logged limit and brings no new evidence. Effect is a two-pass fix loop, never a wrong fix.
  8. **K1 — `scan.test.ts` nested embedded row cannot fail** (`{x: "${a.out|json}", y: "${a.out}"}` dedupes to `out` either way). CONFIRMED (mutation: nested leaves read as template → the old row stayed green). FIXED: distinct paths (`a.out.inserted|json` / `a.out.bare`, expect `out.inserted`). Mutation (nested leaves read in template mode) → the new row red (the old one did not go red). Test-only, no UI surface changed.
  9. **W1 — ReadPanel's JSON display hides a dict leaf's ref** (`env: {X: '${up.stdout ?? "fallback"}'}` serializes `\"`, the strict walk reads an Issue, so the selected-edge mark is lost; the old loose regex marked it). CONFIRMED by reading (`ReadPanel.tsx:107` `fullValue` → `JSON.stringify`; `format.ts` LITERAL rejects `\"`). SKIPPED (importance 2) — a display regression limited to the selected-edge mark on a dict param whose leaf has a quoted coalesce fallback; the fix is a leaf-aware serializer (tokenize each leaf, carry spans through `JSON.stringify`) — a design choice plus a screenshot-verified web change, out of a gate's fix budget. **Recommend a follow-up issue** (web: decorate dict params per leaf, before JSON serialization).
  10. **W2 — `ParamValue` collapses whitespace before tokenizing** (a raw TAB inside a quoted literal becomes a valid expression → a chip). CONFIRMED by reading (`WorkflowNode.tsx:121`). SKIPPED — needs a raw control character inside a quoted pflow literal (which the grammar rejects) inside embedded code; display-only. Tokenize-then-collapse is the right order; fold into W1's follow-up.
  11. **W3 — module-scoped `registry` fixture is built before `isolate_pflow_config`** (`test_embedded_code_consumers.py:56`; reads the real `~/.pflow/registry.json`). CONFIRMED (pytest builds module-scoped fixtures before function-scoped autouse ones). FIXED: function scope (the isolated registry). 22 tests green.
  12. **S1 — scope ownership recovered from prose** (`_OWNER_KINDS` reverse-maps owner prose to a kind; `_root_kind`). CONFIRMED. FIXED: `StepScope.names` maps name → `ScopeKind`; `StepScope.kind()` is the structured answer; `owner()` renders prose from one `_OWNER_PHRASES` table. Deleted `_OWNER_KINDS`, `_root_kind`, `EmbeddedRootKind` (now `ScopeKind`), two owner constants. Task 118's body diagnostics are byte-identical (its suite green). Mutations G4 (`kind()` never "step") → 8+ red in `test_code_body_leftovers.py`; G5 (wrong phrase) → 3 red.
  13. **S2 — unused node plumbing** (`_bare_reference_warning(refs, node)` never read `node`). CONFIRMED. FIXED: dropped the argument, the node map and `_validate_embedded_references`' `workflow_ir`.
  14. **S3 — case corrections build `|json` by hand** (`data_flow.py:357`). CONFIRMED. FIXED with C3 (`written_reference` is now the only renderer there).
  - **Verified clean**, per lens: silent-failures (Python; web), impact-completeness, feature-interactions (batch/branching/nested/loops/cache/approval/dry-run/MCP/output), test-fidelity (Python), validation-consistency (Python; grammar/UI except C4/C5/W2), agent-ux (ruled text matches verbatim incl. Q1), simplicity (no Warning), spec-conformance (inverse pass: no unrecorded addition). Listed for completeness; no action.
- Changed: `src/pflow/core/templates.py` (`balanced_template`), `src/pflow/core/workflow/data_flow.py` (reserved/undefined-input rendering; `ScopeKind`), `src/pflow/runtime/template_validation/validator.py` (S2), `src/pflow/guide/nodes/mcp.md` (C6); tests `test_core/test_templates.py` (+2 rows), `test_integration/test_embedded_code_diagnostics.py` (+2 tests), `test_integration/test_embedded_code_consumers.py` (fixture scope), `web/src/graph/scan.test.ts` (one row).
- Verified: `make check` rc 0; `make test` 10953 passed (baseline captured on `87119e6c` before any edit: 10949; +4 new, 0 failures); `make test-all-local` 11006 passed, 2 skipped (PZ: 11002); web `npm run typecheck` rc 0, `npm test` 56 files / 905 passed. Real CLI (`uv run pflow --validate-only`, scratch probes, chrome-devtools registered locally): C1's §7b error and C2's `${__index__|json}` / `${item|json}` fixes print as above; C3's `… like ${node_id.field|json}.` | Assumed: W1/W2's visual effect (read, not driven in a browser — no web production code changed).
- Deviations/surprises:
  - The data-flow undefined-input messages now quote the author's reference as written (`'${Repo|json}'`), not only the suggestion — option (A)'s rule ("everything shown or suggested in the author's place is rendered") applied to the last builders that predated it. Ordinary-template output is byte-identical (no `as_json` → unchanged), so no snapshot or verify.sh case can move.
  - The `__index__`/`__iteration__` path messages now print the reference as written (`${__index__[0]}`), where the old code rebuilt `${__index__.[0]}` from a `lstrip(".")` remainder.
  - S1 touches Task 118's `StepScope` (shipped): `names` values change from prose to kinds. Every `scope.names` reader outside `owner()` uses keys only (checked: the env-name `taken=` set and the fuzzy-match `known` set).
  - Doubt kept, not fixed: the embedded `__index__` fix reads "Use bare `${__index__|json}`…" — "bare" there means "without a field", while the guide uses "bare" for "not an insert". The paste-able part is correct; rewording an existing non-ruled line was out of scope.
- Self-checks: fully happy with the 9 fixes; the open doubt is the "bare" wording above. W1 is the one finding I'd want the orchestrator to disposition (follow-up issue vs fix now with UI verification). test-reflect: every new/changed test is mutation-killed (pre-fix C1 run, G2–G5, K1's mutation); each absence half has a same-medium presence pair (the bare llm twins); nothing deleted.
- Next: orchestrator launches `review-falsifier` with the spec + `implementation/review-gate-spec-conformance.out`; disposition W1 (+W2) and the C4/C5 differential follow-up.

## [2026-10-11 03:10] implementer I3 — gate findings W1 + W2 (web): dict params read per leaf; chips tokenize before collapsing
- Did: **W1** — `format.ts:parseTemplate(value: unknown, mode)` is now the segments of `fullValue(value)`: a string reads as before; a dict/list reads each string VALUE leaf through `templateTokens` before serialization (keys stay text, as `scan.ts:stringLeaves` reads values only) and emits each segment JSON-escaped, so the segments' text is byte-identical to `fullValue`'s JSON. A ref segment now carries its parsed `operands` (`TemplateSegment` is a union; `refMatchesHighlight(segment, ref)` reads them — the reparse of a `${body}` wrapper is gone, and it is what lets a JSON-escaped body still match). `CodeBlock`'s `code` prop takes the value (`unknown`, shown via `fullValue`), so the main block, the ⛶ modal (passes `code` through) and the per-item preview all go through the one `parseTemplate` call; `ParamBlock` passes `param.value`, and `resolveBatchItems` returns the per-item value structured (no longer pre-serialized text). **W2** — `ParamValue` tokenizes `param.value.trim()` first, then collapses whitespace in each text segment.
- Changed: `web/src/utils/{format,batchItems,highlight}.ts`, `web/src/components/{CodeBlock,ReadPanel}.tsx`, `web/src/components/nodes/WorkflowNode.tsx`, `web/src/utils/CLAUDE.md` (parseTemplate line); tests `utils/format.test.ts`, `utils/batchItems.test.ts`, `components/ParamBlock.test.tsx`, `components/nodes/WorkflowNode.test.tsx`.
- Verified:
  - **Gates:** `npm run typecheck` rc 0; `npm test` 56 files / 918 passed (baseline 56 / 905; +13, 0 failures); `make ui-build` ok; `make check` rc 0; `make test` 10953 passed (= G1's baseline; no Python touched).
  - **Tests:** a dict leaf `${up.stdout ?? "fallback"}` is one ref, highlight-matched by `up.stdout`; the `$${up.stdout}` escape leaf and a `${k}` key stay text; embedded mode keeps only `${x|json}` in a leaf (bare JS `${user.name}` plain); byte-identity rows (nested, escapes/controls/U+2028/emoji/`é` literal, top-level list, Issue + unterminated escape, scalar, null) assert the shown text `=== fullValue(value)` AND the expected refs; ParamBlock with `highlightRef="up.stdout"`: exactly one `.ref-mark` (`${up.stdout ?? \"fallback\"}`), box text `=== fullValue(env)`, the modal marks it too. W2: `${up.stdout ?? "a<TAB>b"}` → no chip, `"a b"` → chip; multi-line text around a chip collapses to `["Say hi to ", " now"]`.
  - **Mutation ledger** (`npx vitest run --reporter=json`, byte-copy restore, scratch `i3/mut.py`): M1 dict read as its JSON text (the pre-fix behaviour) → 6 red; M2 keys tokenized → 10; M3 leaf text not re-escaped → 7; M4 ParamBlock hands CodeBlock the JSON text (pre-fix call) → 5; M5 modal gets the JSON text → 1; M6 per-item value serialized → 3; M7 collapse before tokenizing (pre-fix W2) → 1; M8 no trim → 1; M9 text not collapsed → 1; M10 `refMatchesHighlight` checks only the first operand → **0 at first** — a PD-era gap (no row had the ref as a non-first operand); added `other.x ?? gen.result` → 1 red.
  - **UI acceptance** (`pflow ui --no-open --port 8782`, scratch `i3/env-fallback.pflow.md`: `up` → `greet` with `env: {X: ${up.stdout ?? "fallback"}, LITERAL: $${up.stdout}}`, plus `echo-back` with a multi-line `stdin` holding `${up.stdout ?? "a b"}` and a TAB; ran: `hello / ${up.stdout}`). DOM read by scratch `i3/dom-probe.pflow.md`:
    1. Edge `e1` selected (EdgePanel): `marks: ['${up.stdout ?? \"fallback\"}']`, box text = the JSON, `modalMarks` same; shot `/tmp/pflow-shots/t181i3/env-fallback-advanced-e1-i3a-20261011-030551.png` (the whole coalesce span marked; `$${up.stdout}` plain).
    2. Read panel (`focus=greet`): no marks, no teal — the dict is `lang: json`, which `CodeBlock` never teals (shiki owns it; unchanged from `origin/main`); shiki-highlighted. Shot `…-greet-i3b-20261011-030554.png`.
    3. Canvas: `echo-back` row `lit:"Say hi to " · chip "up.stdout ?? \"a b\"" · lit:" now"`; shot `…-echo-back-i3e-20261011-030653.png`.
  | Assumed: the shiki-swap path for a dict with an escaped leaf behaves as on main (JSON grammar splits at `\"`, so `markRefs` lands 0 of 1 marks and the count rule keeps the plain, marked paint — observed `shikiHosts: 0` with the edge selected).
- Deviations/surprises:
  - **"Teal" does not apply to dict params** (W1 and the brief named it): `paramLanguage` gives every object `json`, and `CodeBlock` teals only markdown/plain values — on main too. W1's real loss was the selected-edge mark; that is what the tests and screenshots pin. No look/feel change made.
  - **Interface changes beyond the two named sites:** `TemplateSegment` became `{text, isRef:false} | {text, isRef:true, operands}` and `refMatchesHighlight` takes a segment (4 call sites); `CodeBlock.code` is `unknown`; `ResolvedBatchItem.value` is `unknown`. Needed because inside JSON a ref's shown body (`up.stdout ?? \"fallback\"`) is not its parseable body. `code` kept its name to avoid a ~24-site rename; the prop comment states it holds a value.
  - **The JSON leaves are located by a JSON-string regex over `fullValue`'s output** (a `:`-followed string is a key), not a second serializer; the byte-identity rows + M2/M3 guard it.
  - **Not changed:** `BatchItems.tsx:39` (a batch item's field — no param, no mode, no highlight; renders text as before).
  - **Real `~/.pflow` is polluted (not mine; for the orchestrator):** `~/.pflow/mcp-servers.json` (mtime 02:42 today) has `"chrome-devtools": {"command": "true"}` instead of the pinned `chrome-devtools-mcp@1.10.1` entry I2 used at 02:09, and `~/.pflow/registry.json` (rewritten 03:05, while the falsifier ran) describes `mcp-chrome-devtools-evaluate_script` as "Test tool evaluate_script" with no `pageId` — so every screenshot workflow fails with "Unknown parameter 'pageId'". I did NOT touch it (a concurrent agent may depend on it); I ran the skill workflows under an isolated `HOME=<scratch>/i3/home` with the pinned registration synced there. The user's real entry needs restoring (`pflow mcp add … @1.10.1` + `pflow mcp sync chrome-devtools`), and whatever wrote a stub into the real config (a probe or a test missing `isolate_pflow_config`) should be found.
- Self-checks: fully happy with the fix; doubts: (a) `code: unknown` under the name `code` is a naming wart (rename is mechanical, deferred); (b) a dict with an escaped leaf, while its edge is selected, keeps the plain (un-colored) JSON paint — pre-existing count-rule trade-off, same as main. test-reflect (directed): every new row mutation-killed (M1–M9); deepened `refMatchesHighlight` with the non-first-operand row (M10 was an equivalent-looking survivor); the W2 collapse row is the presence twin of the TAB absence row; batchItems dict rows now assert the structured value (simpler, was `JSON.parse(r.value)`); nothing deleted.
- Tooling postmortem (screenshot skill): worked — `screenshot` with `focus=e1` captures edge selection; a 40-line probe workflow (open-and-settle + one evaluate_script) read marks/teal/chips/modal. Friction: (S) the polluted global registration above cost the most time — the skill could check `pflow mcp describe mcp-chrome-devtools-evaluate_script` for `pageId` before running and say "registration stale/stubbed"; (S) `pflow mcp describe` prints `Server: chrome / Tool Name: devtools-evaluate_script` for `chrome-devtools` (hyphenated server name split wrongly — display only); (M) repeated: a DOM-text reader workflow (I2's item) would have replaced my probe.
- Next: hand back. `dev servers: none` (8782 server PID 32276 stopped; port verified down).

## [2026-10-11 03:20] task orchestrator — G1 gate outcome dispositioned; W1/W2 fixed (I3); the user's ~/.pflow MCP config repaired
- G1 (02:52): 9 fixed / 5 skipped / 0 handed back — skips accepted (C4/C5 → the Python↔TS differential follow-up; C7 settled; W1/W2 → NOT a follow-up: a regression this branch introduced, so fixed now by I3, 03:10). G1's "bare `${__index__|json}`" wording doubt: kept — the line predates this task ("Use bare `${__index__}`"), the paste-able part is correct; rewording changes ordinary output for no observed confusion.
- I3 (03:10) verified: entry read; gates green; UI driven with screenshots; deviations (no teal on JSON dicts — on main too; mark was the regression) accepted. Self-check doubts (`code: unknown` name; escaped-leaf paint) are pre-existing/cosmetic — accepted.
- **Incident — our test wrote into the user's real `~/.pflow`.** `tests/shared/mcp_tool.register_mcp_tool` (PB) adds an MCP server + registry entry; `test_embedded_code_consumers.py` called it from a MODULE-scoped fixture, which pytest builds before the function-scoped autouse `isolate_pflow_config` — so each `make test` from PB until G1's W3 fix overwrote the real `chrome-devtools` entry with `{"command": "true"}` and registered a stub `mcp-chrome-devtools-evaluate_script` (no `pageId`). Observed by I3 (mtime 02:42 = G1's baseline `make test` on `87119e6c`).
  - Repaired (damage repair to the pre-task state, documented recipe in the screenshot skill): backed up the corrupted files to orchestrator scratch (`t181/orch/*.corrupt.json`), ran `uv run pflow mcp add '{"chrome-devtools": {"command": "npx", "args": ["-y", "chrome-devtools-mcp@1.10.1", "--headless=true"]}}'` → 30 tools discovered/registered; `evaluate_script` params now include `pageId`. No other `command: "true"` server and no `Test tool`/`mcp-corpus-*` registry entry remain.
  - Verified the fix holds: mtimes of `~/.pflow/mcp-servers.json` + `registry.json` unchanged across a run of all four embedded-code test files + the parity corpus (478 passed).
  - Exposure: any sibling worktree's chrome-devtools run between 02:42 and 03:20 saw the stub. Handback names it.
- Next: commit I3; falsifier report → G1 for evaluation.

## [2026-10-11 03:30] gate-runner G1 — falsifier report evaluated: 3 findings — fixed 2, skipped 1, handed back 0
- Did: read `implementation/review-falsifier.out` in full; re-ran its W1/W2 probes with its isolated HOME (`<scratch>/t181/falsifier/home`); verified, fixed with tests written red first, mutation-checked.
- Findings and dispositions:
  1. **W1 — a dynamic child (`workflow: ${which}`) sends a stale `'${selector}'` as JavaScript and exits 0.** CONFIRMED: reproduced as a red test before any edit (`test_a_dynamic_child_with_an_input_used_only_bare_fails_before_the_tool_is_called` — the run succeeded and the stubbed tool was called). Cause: the §4a ERROR lived in the template validator, which `WorkflowExecutor._validate_and_compile_child` never runs. FIXED as the orchestrator proposed, following 118's body-leftover precedent (task-review invariant 6). **Data flow now owns the embedded-code report**; the compiler's data-flow check (`check_inputs=False`, errors only) refuses the child.
     - `data_flow._validate_embedded_code(workflow_ir)` is called once from `validate_data_flow`. It holds the §4a ERROR **and** the §4b/§4c/§4d WARNINGs, plus their message builders, moved verbatim from `runtime/template_validation/validator.py` (−200 lines there).
     - **Deviation from the orchestrator's suggested split** (data flow = ERROR, template validator = WARNINGs): splitting needs the same "used elsewhere" predicate in both modules, so one decides and the other mirrors it. Moving the whole consumer gives one detector and one consumer. A WARNING on the compile-only path is dropped anyway: compile raises on errors only. Ruled text is unchanged; every §4 CLI test is green unedited.
     - **One answer to "is this input used?"** is the new `data_flow.template_reads(workflow_ir)`: every surface (embedded code = its inserts), a carry's index sources, cache vars, output sources read as the runtime reads them, plus body-leftover roots. It reproduces the template validator's old 4-way union. The validator now calls `template_reads(...) | bare embedded roots` for the unused-input check.
     - Deleted: `_extract_cache_templates_for_unused_check` / `_surface_references` (its test now asserts `template_reads` holds the cache var).
     - Not done: dynamic children still skip full template validation (the orchestrator forbade widening the engine path). §7a/§7b hidden and near-miss inserts in a dynamic child still reach the tool verbatim, but that failure is loud (a JS Reference/SyntaxError) and was already listed as held in the falsifier's report ("dynamic-child run-time outcomes as ruled in D4").
     - Real surface: the falsifier's own `n/parent_dynamic.pflow.md selector="#main" which=…/child.pflow.md` (isolated HOME) now fails before the tool with the ruled §4a text plus `Sub-workflow: …/child.pflow.md`.
  2. **W2 — the body-leftover fix for `${x|json}` in a shell/code body binds `${x|json}` in `env:`/`inputs:`, which validation rejects (§5).** CONFIRMED (executed on the falsifier's `m/shell_body`, `m/code_body`). Cause: `BodyReference.reference` was `Expression.raw`, which after D1 carries the suffix.
     - FIXED at the source: new `Expression.bare_raw` (`raw` without `|json`). `_leftover` uses it, so the fix reads `- env: {X: ${x}}` … replace `${x|json}` with "$X", and `- inputs: {x: ${x}}`.
     - The same property replaces the two hand-written `raw[: raw.rindex("|")].rstrip()` copies (validator §5 fix, runtime `classify_unresolved_references`): one rule, three call sites.
     - Test `test_a_json_insert_left_in_a_body_is_bound_without_its_suffix_and_the_fix_validates` (in `test_code_body_leftovers.py`) asserts the exact fix line, then applies it (shell and code) and checks it validates clean. Its presence pair is the old suffixed binding validating to the §5 ERROR.
  3. **S1 — `|json`-shaped text that is not an insert** (`${[1, "a"]|json}`, `${title|json|json}`, `${row["full name"]|json}`) passes validation and fails at the tool. CONFIRMED by reading (`near_miss_insert` claims only end-trim + case, R4). SKIPPED, agreeing with the orchestrator:
     - the failure is loud (a JS SyntaxError naming the text);
     - it is outside R4's ruled scope;
     - a diagnostic would need unruled message text (no "meant" form exists to suggest).
     - Recorded as a known limit for the task-review.
- Changed:
  - `src/pflow/core/templates.py` (`Expression.bare_raw`);
  - `src/pflow/core/workflow/data_flow.py` (`template_reads`, `_validate_embedded_code` + builders, `_leftover`);
  - `src/pflow/runtime/template_validation/validator.py` (consumer and cache extractor removed; unused-input via `template_reads`);
  - `src/pflow/runtime/engine/template_errors.py` (`bare_raw`);
  - `src/pflow/runtime/template_validation/CLAUDE.md`, `src/pflow/core/workflow/CLAUDE.md` (where the report and the used-set live);
  - tests: `test_runtime/test_embedded_code_runtime.py` (+1, dynamic child), `test_integration/test_code_body_leftovers.py` (+1), `test_core/test_cache_block_parser.py` (mechanism assertion re-pointed).
- Verified:
  - `make check` rc 0; `make test` 10955 passed (+2); `make test-all-local` 11008 passed, 2 skipped.
  - All seven screenshot workflows `--validate-only` ✓.
  - **Mutation ledger** (byte-copy restore, counted):
    - W1a: `validate_data_flow` drops `_validate_embedded_code` → 14 red, the dynamic-child test included;
    - W1b: `template_reads` skips output sources → red (`test_a_bare_coalesce_output_source_names_real_roots`);
    - W1c: skips cache vars → red (`test_inputs_referenced_only_in_cache_not_flagged_unused`);
    - W1e: no body roots → red (`test_consumer_skips_a_body_and_still_reads_env[unused_input]`);
    - W1d: a carry's own reference counted → 0 red. Equivalent in practice: a carry may only reference its loop node, so its own reference never roots at an input. Kept the old rule rather than test a dead branch.
    - W2a: `_leftover` back to `raw` → 1 red;
    - W2b: `bare_raw` returns `raw` → 9 red (§5 fix rows, the coalesce fix, the body-binding test).
  - | Assumed: nothing about shipped behaviour; the compile-path `CompilationError` carries the ruled message verbatim (asserted).
- Deviations/surprises:
  - The whole embedded report moved to data flow, not only the ERROR (reason above).
  - A §4a ERROR is no longer suppressed by the Issue pass's early return. A workflow with both a malformed template and an input used only bare now shows both errors, where it showed only the malformed one. These are two separate mistakes, so it is still one diagnostic per mistake. No ruled text covered the combination.
  - §4 diagnostics now also appear on paths that run data flow without template validation (`WorkflowValidator.validate` with `extracted_params=None`, the compiler).
- Self-checks: fully happy.
  - Doubt checked: is `template_reads` exactly the old union? The three killed mutations pin its three non-param members (outputs, cache, bodies); the param/batch/loop member is pinned by the whole unused-input suite. The one surviving mutant (W1d) is dead in practice.
  - test-reflect: both new tests have same-medium presence pairs (the converted child runs and the tool receives `"#main"`; the suffixed binding is the §5 error). Nothing deleted beyond the moved code.
- Next: orchestrator.

## [2026-10-11 03:40] task orchestrator — gate closed; task-review written; spec done
- Did: accepted G1's falsifier evaluation (03:30: W1 fixed by moving the embedded-code report to data flow per 118 invariant 6 — the whole report, not my suggested split, for one detector; W2 fixed via `Expression.bare_raw`; S1 skipped as a known limit) and committed it (`245d1497`). Wrote `task-review.md`; spec `## Status: done`, `## Completed: 2026-10-11`.
- Verified (final committed tree, `origin/main` unchanged since the 02:40 merge): `make check` RC 0; `make test-all-local` 11008 passed, 2 skipped; web `npm run typecheck` + `npm test` 918 passed. Real `~/.pflow`: `mcp-servers.json` untouched since the 03:20 repair; `registry.json` was rewritten once at 03:33 (core-node entries now point at this worktree's `src/` — pflow's normal core-node refresh when a checkout's sources change; content clean: no stub/test entries, `evaluate_script` has `pageId`); re-running `make test-all-local` and `make check` leaves it untouched (mtime equal before/after).
- Deviations/surprises: none beyond the entries above.
- Self-checks: all phases verified with "fully happy?" + test-reflect resolved per entry; tooling postmortem items dispositioned (03:00); every gate finding dispositioned (18:20, 02:52, 03:20, 03:30).
- Next: `create-pr`.
