# Task 183 — pause surfaces, BEFORE / AFTER (show-before-code)

BEFORE blocks were **executed on `706b292c`** (re-check: the #719 fast-forward to `2464e43c` touched no pause
renderer) by `scratchpads/task-183/capture.sh before2`
(gitignored; isolated `HOME`; fixtures `scratchpads/task-183/wf/{capped,uncapped,templated,plain}.pflow.md`,
the `capped` loop is Task 179's `_LOOP_GATE_WF` plus a `done` step). Tokens/paths redacted.
Section 12 (TTY prompt) renders through the real `gate_prompt` functions with a synthetic
`GateRequest` — the prompt needs a terminal. AFTER blocks are **drafted** (the code does not exist
yet); the completion phase re-runs the same script as `capture.sh after` and must reproduce them.

Only the loop-position line changes. Everything else in each block is shown for context and stays
byte-identical.

## The rule (one Python helper, one TS twin, one shared fixture)

| `iteration` | `max_iterations` | text |
|---|---|---|
| 1 | 3 | `iteration 1 of up to 3` |
| 2 | `null` / absent (no author cap, or cap not knowable at the gate) | `iteration 2` |
| 4 | 3 (a back edge into the loop continues the count; or a resume with a lowered cap) | `iteration 4` |
| `null` / absent (non-loop gate) | any | *(no position)* |

`max_iterations` is the author's cap as known at the gate: a literal → that number; a
`${template}` → resolved against the store, unless it **references the loop step's own output or
`${__iteration__}`** (a cap that depends on the loop body is unknown → `null`); no `max_iterations`
→ `null` (the engine's visit guard is never shown). JSON carries the key on every new payload
(`null` when unknown / non-loop); records written before this task lack it and render as `null`.

---

### 1. Non-TTY pause (`pflow wf.pflow.md </dev/null`), loop with `max_iterations: 3`

BEFORE
```
Paused at 'gated'. Resume token: <token> (exit 4)

   Loop iteration 1
   code:    iteration: int\nmarker: str\nwith open(marker, ...
   inputs:  {"iteration": 1, "marker": "..."}

To answer: pflow resume <token> --approve yes|no
```
AFTER
```
Paused at 'gated'. Resume token: <token> (exit 4)

   Loop iteration 1 of up to 3
   code:    iteration: int\nmarker: str\nwith open(marker, ...
   inputs:  {"iteration": 1, "marker": "..."}

To answer: pflow resume <token> --approve yes|no
```
PROPOSED, pending user ruling R1 (not in the spec) — one extra line for a LOOP APPROVAL gate only
(non-loop approvals and escalations unchanged), on the CLI pause, the MCP pause and the answer-required error:
```
To answer: pflow resume <token> --approve yes|no
To approve this and every remaining iteration of 'gated' (only with your human's OK): pflow resume <token> --approve yes --auto-approve gated
```

### 2. Resume without an answer (`pflow resume <token>`) — `ResumeAnswerRequiredError`

BEFORE
```
Error: Paused gate needs an answer

This run is paused at an approval gate on step 'gated' and needs an answer.

  Loop iteration 1
  code:    ...
  inputs:  ...
  At: node 'gated'

  → Answer with: pflow resume <token> --approve yes|no
```
AFTER — the one line becomes `  Loop iteration 1 of up to 3`; the diagnostic's `context.gate`
(JSON) gains `"max_iterations": 3`.

### 3. Flag echo on resume (`--approve yes`, then `--approve yes --auto-approve gated`)

BEFORE
```
✓ Gate 'gated' — iteration 1 approved via --approve yes
...
✓ Gate 'gated' — iteration 2 approved via --approve yes
✓ Gate 'gated' — iteration 3 pre-approved via --auto-approve=gated
```
AFTER
```
✓ Gate 'gated' — iteration 1 of up to 3 approved via --approve yes
...
✓ Gate 'gated' — iteration 2 of up to 3 approved via --approve yes
✓ Gate 'gated' — iteration 3 of up to 3 pre-approved via --auto-approve=gated
```
(The `⤷ Resumed from <token> at 'gated' (iteration 2)` line is the resume ENTRY position — a
different concept, unchanged.)

### 4. `pflow resume list` (text)

BEFORE
```
TOKEN                                 WORKFLOW  PAUSED AT  GATE                    AGE
<token>  capped    gated      approval · iteration 2  0s
```
AFTER
```
TOKEN                                 WORKFLOW  PAUSED AT  GATE                               AGE
<token>  capped    gated      approval · iteration 2 of up to 3  0s
```

### 5. `pflow resume list --output-format json` (row)

BEFORE
```json
{ "paused_node_id": "gated", "gate_kind": "action_approval", "iteration": 2, "paused_at": "...", ... }
```
AFTER — one new key beside `iteration`, same `null` semantics:
```json
{ "paused_node_id": "gated", "gate_kind": "action_approval", "iteration": 2, "max_iterations": 3, "paused_at": "...", ... }
```

### 6. `--output-format json` pause document → `gate_request`

BEFORE
```json
{ "node_id": "gated", "node_type": "PythonCodeNode", "kind": "action_approval", "preview": {...},
  "question": null, "options": [], "recommendation": null, "iteration": 1 }
```
AFTER
```json
{ "node_id": "gated", "node_type": "PythonCodeNode", "kind": "action_approval", "preview": {...},
  "question": null, "options": [], "recommendation": null, "iteration": 1, "max_iterations": 3 }
```
A non-loop gate: `"iteration": null, "max_iterations": null`. (`GET /api/gate` serves the same dict.)

### 7. Loop with no `max_iterations` — UNCHANGED

```
   Loop iteration 1
```
(`max_iterations: null`; the engine's 100-visit guard is never shown.)

### 8. Loop with `max_iterations: ${rounds}` (`rounds=3`)

BEFORE `   Loop iteration 1` → AFTER `   Loop iteration 1 of up to 3`

### 9. Non-loop approval gate — UNCHANGED

```
Paused at 'notify'. Resume token: <token> (exit 4)

   command:  echo hello

To answer: pflow resume <token> --approve yes|no
```

### 10. MCP pause response (`workflow_execute` → `ExecutionService.execute_workflow`)

BEFORE
```
⏸ Workflow paused at 'gated' — a human decision is required.
...
Gate:
  Loop iteration 1
  code:    ...
```
AFTER — `  Loop iteration 1 of up to 3`.

### 11. TTY prompt (interactive run)

BEFORE
```
⏸  Approval required: gated (PythonCodeNode) — iteration 2
⏸  Escalation from impl — iteration 2:
```
AFTER
```
⏸  Approval required: gated (PythonCodeNode) — iteration 2 of up to 3
⏸  Escalation from impl — iteration 2 of up to 3:
```
Non-loop prompts unchanged (`⏸  Approval required: notify (ShellNode)`).

### 12. Escalation inside a loop, pause output / MCP / answer-required error

BEFORE
```
Loop iteration 2
Which approach?
1. small (rec)
2. large
```
AFTER — first line `Loop iteration 2 of up to 3`. No bulk action anywhere for escalations.

### 13. Web gate panel (eyebrow + footer) — screenshots come from the UI phase

BEFORE: eyebrow `code · gated · iteration 2`; footer `[Deny] [Approve]`.
AFTER: eyebrow `code · gated · iteration 2 of up to 3`; footer for a LOOP APPROVAL gate gains
**Approve all remaining** beside Approve (Approve stays the one accent-filled action). Non-loop
gates and escalations: footer unchanged. Before/after screenshots are the UI phase's user
checkpoint.

### Old records (written before this task — no `max_iterations` key)

Every surface renders today's text (`Loop iteration 2`, `approval · iteration 2`, eyebrow
`· iteration 2`); `resume list --output-format json` reports `"max_iterations": null`.
