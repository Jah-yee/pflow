# CURRENT-STATE.md (last verified: 2026-10-12, session-15 close — main @ origin/main `a7ba08de`, push CI green)

_Living state header — the ONE mandatory session-start read (~80-line budget; state + pointers
only). Rewritten at close/park (ORCHESTRATION "Artifacts and ownership"); work done outside a
numbered session appends a dated `## Outside-session — folded at next rewrite` block at the top,
which the next boot folds. How-it-got-here: latest `sessions/session-NN.md` (+ the previous three
braindumps); routing: `sessions/INDEX.md`. Every claim here is a pointer to verify, not a fact._

## Process

- Session-15 ran Fable, then **Opus** from the user's `/model` swap (saved as default); routing unchanged (DECISIONS #24, now
  carrying the user's "fixes are not taste" line). Searcher default = the codex offload (astra) paired with execution before any
  filing (the user, s14 + s15).
- Uncommitted producer-facing edit (needs the user's word, DECISIONS #5): `.claude/skills/deep-review/SKILL.md` (+ `.agents/` twin) —
  dogfood briefs `env -u` provider keys.

## In flight — nothing live; ONE parked worktree (local branch, clean, nothing built)

- **#801** (value-based secret scrub) — `fix/issue-801-value-scrub` @ `61625533`. PARKED on the user's Decisions 1–4 (secret-set
  source A/B/C · min length 8/6 · scrub scope whole-document vs diagnostics · lane file scope); the park comment on #801 holds the
  options + evidence + resume steps. Resume = a replacement lane in that worktree (merge main first).

## Next session, recommended order (NOT yet user-agreed)

1. Rule #801 → resume it (first on the `cli/commands/run.py` serial queue).
2. `run.py` serial queue after #801: #806 (text helpers) → #807 (resume attempt view; now carries M8/P11b) → #821 member 2 (trace
   finalized on every exit + Ctrl-C waits for the body thread) → #847 (`--help` description / output types) → #850 (header before
   validation) → the redundant `run.py:816-830` name check (#817 residual; no issue — fold into the next run.py lane).
3. Parallel-safe fills (verify ownership at pick-up): #846 probe exit code · #842 template error names the consumer · #841 HTTP error
   body (redact before excerpting) · #832 MCP union params · #835 MCP step-key collisions · #838 · #848 · #849 · #851 · #852 · #855
   (author-side reserved names) · #834 code-step output on exception · #836 · #837 · #839.
4. UI follow-ups (Opus — fixes): callout overlays as obstacles (#822 residual; file first, verify) · F4 run-panel items (user's call).

## Decisions pending the user

- #801 Decisions 1–4 (above). · **#833** settings env exported to every shell step: A stop exporting / B fix the doc (A's premise
  unverified). · **#843** JSON failure doc cap (rec a). · **#845** save + code-file siblings (rec warn). · **#844** resume-child
  never-started — both closing options change a documented contract. · **#828** gate in a sub-workflow (engine → task-shaped).
- F3(b): should `--approve no` skip the "file edited since pause" refusal? — the user: decide next session.
- F4 (demo studio): transient all-pending panel / no RunProgress for CLI runs / badge excludes restored — file or not.
- **MCP server future (parity vs removal)** — the user is waiting for more information; Task 152 and Task 178's server half HELD
  (s15 22:50 ruling, operative wording in the session log). The MCP CLIENT (nodes, discovery, describe) is unaffected.
- Carried: the release (v0.16.0 + ~45 commits; changelog workflow fixed by #741); #802/#803/#805 shapes; #692 (low).

## Do not re-raise (declined, with the trigger that reopens each)

- pr-closer / RELEASE-BLOCK / batched releases / docs-PR lane / automatic PR review / cross-task knowledge base — never.
- #665 (`save --force`), #697 (trace 0644) — reopen when saved-library use becomes real.
- Consumer reports (s13 + s15): deprecation windows / `requires-pflow`, `-p` multi-output (#281), `PFLOW_HOME` — s13 triggers;
  `## Failures` section / per-step exit propagation, refusal API for code steps, `key=@file`, project-local MCP registry, MCP server
  version record, auto-loading `./file` for MCP params — reopen when a SECOND consumer hits it. Output `keys:` lives on #743.
- PyPI yank — closed (the user, s15). Execution-start MCP auto-sync — deleted (#751).

## Regime facts (dated — re-measure, never inherit)

- 2026-10-12: suite ~11,794 (`make test`); `baseline-oracle` runs the Task-159 oracle AND the Task-170 examples capture (both required).
- 2026-10-12: open issues 185 (newest #855). Load 70–183 with 1 build + 3 lanes + verification/offload agents (s14 peaked 86).

## Watch list (non-obvious, easy to miss)

- **Exit codes changed (#815):** 2 = wrong call (engine never started), 1 = run failed, 3 denied, 4 paused, 130 interrupt — baselines
  and tests that pin exit codes moved with it.
- **The run document's JSON shape changed (Task 184):** top-level `nodes_executed`, `checkpoint`, `paused_node_id`, `gate_request` gone.
- **User actions (their HOME, not ours):** `pflow mcp sync` to pick up corrected MCP param types (#811); stale uvx env
  (`uv cache clean pflow-cli`). The user's own shell exports GEMINI/OPENAI keys — isolated-HOME agents must `env -u` them.
- The test suite redirects HOME for the whole session (#793) — push/`gh` with the normal HOME.
- Agents' abandoned probe shells can block `./scripts/worktree rm` (s15: a `ugrep` hung on stdin 18 min) — inspect argv/cwd, kill only
  PIDs naming the worktree. Agents can also drop probe files at the MAIN checkout root (s15: 15 `e*.pflow.md`, moved to
  `scratchpads/session-15/stray-root-probes/`).
- MCP stdio shims + `anyio>=4.5` exist only for Task 178 to delete. `stash@{0}` (Task 125 WIP) is the user's — never `git stash`.
- Agent defs/skills in the MAIN checkout are read live by agents launched from the session — committed or not.
