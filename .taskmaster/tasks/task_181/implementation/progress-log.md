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
