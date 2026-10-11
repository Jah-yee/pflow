# Task 183 — P4 user checkpoint: the gate panel's "Approve all remaining"

> **RULED 2026-10-11** — user: *"go ahead with all recommendations"*: all five choices kept as built
> (layout under the pair; orange-tinted style; both tooltip wordings; shown on uncapped loops; no confirm
> dialog); the answer-required numbered-list shape stays. The class-name eyebrow (last section) was folded
> into this task by the main orchestrator (2/5): the gate payload's `node_type` becomes the IR type.

Built and verified at `17039162`. Every shot below comes from that code, taken after the latest
ruling (2026-10-07: R1 = yes, R2 = (a), web phase on Opus). **Stale shots: 0.** No ruling or
code change has landed since they were taken, and the Python side has not changed since P3.

Shots root: `/Users/andfal/projects/pflow-worktrees/feat-task-183-loop-gate-approve-all/scratchpads/task-183/shots/`
(`before/` = origin/main's panel, `after/` = this branch; same file names; each PNG has a
measurement JSON beside it).

## What the user sees

| Case | Before | After |
|---|---|---|
| Loop gate, `max_iterations: 3` | `before/capped-1440x900.png` | `after/capped-1440x900.png` |
| Same, narrow window (760×560) | `before/capped-760x560.png` | `after/capped-760x560.png` |
| Loop gate, no `max_iterations` | `before/uncapped-1440x900.png` | `after/uncapped-1440x900.png` |
| Long code preview | `before/long-preview-1440x900.png` | `after/long-preview-1440x900.png` |
| Non-loop gate (unchanged) | `before/plain-1440x900.png` | `after/plain-1440x900.png` |
| Escalation inside a loop (no bulk action) | `before/escalation-loop-1440x900.png` | `after/escalation-loop-1440x900.png` |

The eyebrow now reads `… · gated · iteration 1 of up to 3` (no clause when the loop has no
limit). On loop approval gates, **Approve all remaining** appears under `[Deny] [Approve]`.
The non-loop and escalation footers measure byte-identical before and after, at both window sizes.

Real clicks, in the browser:
- **Approve all remaining**, clicked once, finished the 3-iteration loop. The effects file has
  3 lines, the run succeeded, and nothing is left paused (`after/verify-bulk-click-1440x900.png`,
  `after/verify-bulk-success-1440x900.png`).
- **Approve**, clicked once, ran one iteration. The panel came back reading
  `iteration 2 of up to 3` (`after/verify-single-click-1440x900.png`).

Measured at 1440×900 and 760×560, with short and long previews:
- Every button and the ✕ sit inside the window and the panel, and nothing covers them.
- No label is cut off or wrapped.
- Approve is still the only solid-orange button.

## For the user to rule on (recommendation: keep each as built)

1. **Layout:** "Approve all remaining" sits on its own row under `[Deny] [Approve]`, as wide as
   that pair. Approve stays where it is on every other gate, and the bulk action reads second.
   The cost: the footer is about 42px taller, so the code/inputs preview scrolls a little sooner.
   *Alternative:* bulk row above the pair (`alt/alt-bulk-above-capped-1440x900.png`).
2. **Style:** orange-tinted fill, orange border, orange text. It reads as an approve action
   without competing with Approve. *Alternative:* plain fill with orange text
   (`alt/alt-quiet-style-capped-1440x900.png`). It is calmer, but sits close to Deny.
3. **Tooltip** (shown on hover):
   - With a cap: *"Approve this and every later approval of a step named 'gated' in this run,
     including inside sub-workflows. This loop runs at most 3 iterations."*
   - With no known cap: *"… including inside sub-workflows. No limit is known for this loop — it
     runs until its condition stops it."*
4. **Shown on loops with no limit too** (R2 = (a), as ruled). See `after/uncapped-1440x900.png`.
5. **No confirm dialog.** One click, like Approve. The label and tooltip say what it does.

## Also user-visible: the agent hint on "Paused gate needs an answer" (CLI)

R1's extra line on this error turns the single `→ Answer with:` line into the CLI's usual
numbered list. This happens only on loop approval pauses:

```
To fix this:
  1. Answer with: pflow resume <token> --approve yes|no
  2. To approve this and every remaining iteration of 'gated' (only with your human's OK): pflow resume <token> --approve yes --auto-approve gated
```

The orchestrator ruled this shape at 2/5: JSON/MCP readers get the hint as its own suggestion.
To keep the old `→ Answer with:` line instead, change one line in `core/exceptions.py`.

## Seen in the shots, not caused by this task

The eyebrow shows the Python class name (`PythonCodeNode · gated`, `MCPNode · review`), not the
node type (`code`, `mcp`). It does the same on origin/main (see the BEFORE shots). The web tests
assume `code`. Because the class name is long, the new position wraps onto a second line
starting with `·` at this panel width. No issue exists for it yet. Recommendation: file a
GH-issue lane (the fix is probably mapping the type name on the server or in the panel).
It is out of scope here.
