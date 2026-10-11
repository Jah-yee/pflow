# session-13 — 2026-10-10

## [2026-10-10] main orchestrator — boot + reality diff

- Booted per the role prompt (Fable, user `/model` saved default). Predecessor `pflow-main-orch-session-12` live → ONE
  bounded question; ANSWERED: nothing live, no post-close ruling (120 (i)–(iii), #692, RECURRENCE promotions all
  unanswered), uncommitted set = 12 paths (10 M + 2 ??), the 120 spec + ADR-0017 must not reach a planner before (i)–(iii).
  Boot fork launched → `scratchpads/session-13/boot-fork-report.md`.
- Reality vs CURRENT-STATE: NO drift — main == origin/main == `f78b40a1` (push CI green); worktrees 181 `d7383363`, 183
  `9b6354b1`, both clean, branches local only; no open PRs; 166 open issues, newest #749; `./scripts/tasks --check` clean.
- User focus: *"lets continue where the last session left off, also read and lets evaluate
  scratchpads/loudkult-ui-driving-report-2026-10-10.md as input to something to potentially fix after verifying it and
  finding the root cause etc"* + *"the old session left all its doc files uncommited, we should probably add this to a
  step in the close orchestration skill to commit when closing session?"*
- Loudkult report (13 items, consumer-side, pflow 0.16.0 @ `f78b40a1`): verification LAUNCHED — startup profile (Opus,
  executes), behaviour repros for items 4/5/6/7/9/10 (Opus, executes, isolated HOME), searcher for MCP registry writers +
  `~/.pflow` writes + stderr/`-p` rules. Reports under `scratchpads/session-13/`. Dedup done by me: #620 #623 #624 #625
  CLOSED (2026-09-28), #621 #622 OPEN, #567 (process-group kill) open.
- Boot fork DONE (`scratchpads/session-13/boot-fork-report.md`, 187k): tracker coverage of the loudkult items — §1 startup
  latency has NOTHING on the tracker; §9b path-like arg → saved lookup is exactly **#553** (OPEN, queued s10, never
  launched); §10 → #567 (process-group kill, partial output; no SIGTERM-grace ask); §3 same symptom family as #611/#612
  (CLOSED via #613/#614); §5 `-p` one output → #281 CLOSED by PR #282 (deliberate: stdout symmetric with stdin); §6
  success-stderr → #55 CLOSED by #56; no issue on the stderr cap / `null` printing blank; §11/§13 none. 118 review:
  `${HOME}` in a shell body is legal sh; only roots naming an in-scope input/step are errors — #621's shell table not
  re-run on `f78b40a1` yet (the behaviour agent is doing it).
- Startup profile DONE (`scratchpads/session-13/startup-profile.md`, 64k; MEASURED, citations re-read by me): the consumer's
  ~2.2 s floor reproduces and is **81 % (1.85 s) MCP auto-discovery** — `cli/commands/run.py:1392` calls
  `_auto_discover_mcp_servers` on every run incl. `--validate-only`, before the workflow is resolved; 7 of the 20 configured
  servers on this machine fail (auth / connection) every time, and `mcp/registrar.py:228` records a fingerprint only on
  SUCCESS, so a failing server is retried forever and silently (progress is TTY-only, `mcp_sync.py:52`). With discovery
  stubbed: 0.31–0.41 s. Remaining: eager `mcp` SDK import 0.14 s on every command incl. `--version`
  (`cli/main.py:171 → commands/mcp.py:15 → pflow/mcp/__init__.py → mcp/discovery.py:10`); parse+validate+registry 0.054 s
  (the consumer's "validated-workflow cache" would save at most that). No registry tempfile is written on a run; registry
  inference REFUTED. Per-machine cost (depends on failing configured servers) — class, not incident.

## [2026-10-10] [RULING] *"yes go ahead with all these recommendations"* — commit, #5 amendment, 120 (i)–(iii), 183 build

- Read as the four recommendations of my first message: (1) commit + push the 12 paths in two commits → `637502e0`
  (orchestration state + DECISIONS #5) and `285e7b3f` (120 spec + ADR-0017 + CONTEXT.md + ADR-0010 + skill/role-prompt
  sentences), pushed; (2) **DECISIONS #5 exception 2**: the close ritual commits + pushes `.taskmaster/orchestration/` by
  pathspec — written into #5, close skill step 7, role prompt "Session end", mirrors synced; (3) Task 120 (i) root-wide,
  (ii) child boundary parses, (iii) narrow the promise to non-`any` → DECIDED in the spec + ADR-0017's open sentence closed;
  (4) Task 183 build.
- LAUNCHED Task 183 build (Opus task-orchestrator, implement-from-plan, worktree `feat-task-183-loop-gate-approve-all`
  @ `9b6354b1`, merges `origin/main` `285e7b3f` first; trace **2.10.0**; P4 web phase Opus per the user's word; embedded P4
  checkpoint → handback). Provisioned `feat/task-120-declared-input-types` @ `285e7b3f` (ledger copied in) and LAUNCHED the
  **Fable planner** for Task 120 (plan-only; ONE policy carrier subsuming 181's `embedded` leaf policy; re-verify list for
  after 181 merges). Both live.
- Sweeps DONE: behaviour repros (`scratchpads/session-13/behaviour-repros.md`, 118k) — §4 §5 §6a §9b REPRODUCED; §7
  NOT (118 Part 2 made shell `${HOME}`/code `${` legal; only `$${` and in-scope roots error); §6b null prints NOTHING (not an
  empty line); §6c success-stderr hidden only under `-p`; §9a only `key: value`-shaped prose bullets become params; §10
  SIGKILL with no SIGTERM, partial stdout IS kept in error/JSON/trace but unusable downstream; **#567's ask shipped in
  `646fdae7` (Task 116) — closable**. Searcher (inline, 195k): tool schemas live in `registry.json` not `mcp-servers.json`;
  the only route to a params-free entry is a SUCCESSFUL discovery returning an empty/non-object `inputSchema`
  (`discovery.py:181-182,255-256,313-314` → `registrar.py:346-350`), saved silently, then skipped until the config changes;
  no `PFLOW_HOME`/XDG override anywhere; every run writes `cache/cache.db` with no flag to avoid it; stderr caps are inline
  literals 500/300/200 (`shell.py:695`, `diagnostic_render.py:838-840,620-622`).
- Loudkult triage FILED (serially, each read back; bodies in `scratchpads/session-13/issues/`): **#751** auto-sync retries
  failing MCP servers every run (the 81 %; two shapes (a) record-the-attempt [rec] / (b) only-when-mcp-step) · **#752** eager
  `mcp` SDK import on every command · **#753** null declared output dropped (`output_resolver.py:152`; re-executed by me) ·
  **#754** one unresolvable output discards the resolved ones + fix should name `?? null` (strict kept) · **#755** stderr
  previews keep the head, lose the tail (inline 500/300/200 caps) · **#756** MCP sync saves an empty/non-object inputSchema
  silently (the only code route to the consumer's "lost params" night; root cause not determinable — evidence overwritten).
  Comments: #735 widened (shell `timeout` prose bullet passes validate-only — same class); #621 re-run table (shell/code half
  RESOLVED by 118 P2; MCP `function:` half = Task 181). **#567 CLOSED** as shipped (`646fdae7`, Task 116; tests named).
  DECLINED (with trigger): §2 no-deprecation (no users — ruled); §5 `-p` one output (#281 by design; silent `-o` miss = #732);
  §6c success-stderr under `-p`; §8 (#622 parked); §11 `PFLOW_HOME` (HOME= works; reopen when a sandbox cannot set HOME) and
  unconditional `cache.db` write (history by design); §12 (#703/#709 open; #624/#625 closed); §13 (`uvx pflow --validate-only`
  IS the CI validator). §7 fully resolved by 118 P2 incl. docs (`template-variables.mdx:333`, `shell.mdx:109`).
- LAUNCHED lanes (Opus, high, both @ `285e7b3f`): **#751** `fix/issue-751-mcp-autosync-retry` — hand-back BEFORE building with
  evaluation + options (a)/(b) (shipped retry rule changes; ≥2 shapes) · **#753** `fix/issue-753-null-output-dropped` —
  hand-back only if `??` convergence or the sub-workflow boundary moves. #752 queued behind #751 (same package); #754 behind
  #753 (adjacent lines); #755 and #553 are the next parallel-safe fills. Live now: 183 build · 120 planner · lanes #751 #753.
- Decisions PENDING the user (surfaced in the triage message): shell timeout SIGTERM-then-grace + `ignore_errors` honouring
  a timeout (changes shipped SIGKILL behaviour; rec yes); #754's premise "strict stays, make the resolved outputs visible"
  vs the consumer's "resolve to null and warn" (rec strict).
- Lane #751 HANDED BACK pre-build (84k, 4 min) — ESCALATED (3/5): the retry-forever rule is #612's DELIBERATE acceptance
  criterion (*"Discovery exception: preserve … prior fingerprint. It remains due on the next ordinary run"*; *"Non-interactive …
  remains silent"* — verified by me on #612's body). (a) reverses both; cost: fingerprints hash raw `${VAR}` refs, so fixing an
  auth token changes nothing → user must `pflow mcp sync <name>` once (the failure line would say so). (b) refuted as "one
  moved call": sub-workflow `mcp-*` steps invisible in the parent IR, `resume` shares the call site, cleanup becomes
  conditional. Lane's measurement: isolated HOME copy with fingerprints written → 0.62–0.83 s vs 3.6–5.0 s (noisy host).
  Lane recommends (a) without `last_error`; 8 tests pin today's rule. Awaiting the user.
- Lane #753 HANDED BACK pre-ship (91k): the guard removal makes `--dry-run` (`execution/plan.py:2081` drops nulls too)
  disagree with a real run on a cached child's null output. RULED here (2/5): **option 1** — `plan.py` + drift test added to
  the lane's ownership; `resolve_output_source` returns the full resolution (found-null ≠ not-found) and both callers use it;
  child null → parent `${child.out}` = `null` is the intended semantic. #754 rebases after. Lane RESUMED.
- User restated the governing lens → re-audit of the three open recommendations: **#751 flipped** — the question is not the
  retry rule but why a run syncs at start-up at all; new rec = sync at the POINT OF USE (where an `mcp-*` step is compiled),
  delete the start-up hook, (a) as fallback; timeout rec trimmed (fixed grace constant, no new param); #754 trimmed (drop the
  text-mode line). User: *"verify all assumptions that we have right now, try to minimize ambiguity, use astra subagents
  where possible"* → three codex searcher-offload runs (prompts `scratchpads/session-13/verify/prompt-{a,b,c}.md`, outputs
  `{a,b,c}.out/.err`) + the native searcher on (a) as the cross-model pair.
- Codex verify (c) #754 DONE (`verify/c.out`): premises CONFIRMED — resolved outputs written before the raise; the failed
  `ExecutionResult` carries them as `shared_after` (`runner.py:404-406, 862-913`); the failure JSON builder already receives
  `shared_storage=result.shared_after` + `ir_data` (`run.py:607-617` → `error_output.py:52-120`) and simply never adds
  `result` — presentation only. Deltas: the fix text's home is `diagnostic_render.py:561-585` (TEXT renderer; JSON serializes
  fields, so the `?? null` hint belongs in the Diagnostic's `suggestions` built at `user_errors.py:130-175`, today `None`);
  `?? null` resolves to `None` today but the key is then OMITTED by #753's guard → #754 lands after #753; the MCP
  `workflow_execute` failure response omits `result` the same way (`execution_service.py:134-177`) — same class, add to #754;
  no test pins an exact seven-key failure shape. #699 scope distinct (metrics/counters).
- Codex verify (b) timeout DONE (`verify/b.out`): SIGKILL-first CONFIRMED on POSIX (`shell.py:222-224`, 1 s drain is post-kill)
  and Windows (`taskkill /PID /T /F`, `:117-131`, no graceful signal exists there); `_store_and_route` returns `error` on
  timeout BEFORE `ignore_errors` (`:986-993`) — **docs CONFLICT**: `shell.mdx:262` promises `ignore_errors` continues on
  non-zero exit while its own table lists -1 as timeout; no doc/ADR promises SIGKILL (ADR-0013 is dialect only); the
  `timeout: True` flag never reaches the shared store (downstream cannot tell a timeout from exit -1); tests pin `killpg(…, 9)`
  explicitly (`test_posix_timeout.py:80,154`; Windows `/T /F` `:265,350`); codex agent backend is also SIGKILL-first
  (`codex_backend.py:434-436`) — consistency scope for the lane; `code` node has a thread timeout, no kill.
- Native verify (a) #751 point-of-use DONE (136k): **"one point of use" REFUTED** — three independent registry consumers
  (validator step 6 `_validate_node_types` → first hard failure for an unsynced tool, `validator.py:548-579`; compiler
  `import_node_class` `compiler.py:280` BEFORE the MCP branch `:302`; probe); `--validate-only` never compiles; runtime
  templated children compile without validation (`workflow_executor.py:300,403`). Also: the start-up sync is ALREADY bypassed by
  `pflow resume` (`resume.py:182 → execute_json_workflow`), the MCP server's `workflow_execute`, and the web UI's in-process
  pre-flight (`server.py:1018`, before the spawn) — the docs promise "auto-syncs when workflows run" is only true for the CLI
  `run` path. MCP node needs the registry only at compile (`node.py:132-142`; config read from file at prep `:538`). No test
  pins the CALL SITE (all 21 tests call the function directly). `pflow mcp add` does NOT sync — prints "Run 'pflow mcp sync
  --all'" (`mcp.py:223`). Precedent for lazy local refresh exists (`Registry.load`), none for network I/O inside validate/compile.
  → point-of-use would be ≥2 sites doing network I/O inside the validator/compiler — a layering smell. New candidate (d):
  delete auto-sync; `pflow mcp add` syncs what it adds (failure surfaces where the user is). Awaiting codex (a) to compare.
- Codex verify (a) DONE (`verify/a.out`, 31 KB): CONVERGES with the native pass on every claim, zero contradictions — point-of-use
  REFUTED (V1 validator step 6 → runner raises before compile `runner.py:645-649`; C1 `import_node_class` before the MCP branch;
  `--validate-only` never compiles); start-up sync bypassed by resume / MCP `workflow_execute` / UI pre-flight (`server.py:1061`
  before the spawn `:1070`); no test pins the call site; docs CONFLICT (`mcp.mdx:135`, `adding-mcp-servers.mdx:57` promise
  "when you run a workflow" — true only for CLI `run`); `pflow mcp add` prints "Run 'pflow mcp sync --all'" instead of syncing.
  → Ruling put to the user: (d) delete auto-sync + `pflow mcp add` syncs what it adds [rec, 4/5] vs (a) record-the-attempt.
- **MERGED #753** — PR #757 → `ebaa5d1b` (closes [753] only — verified; 14/14 green incl. both Windows jobs; 6 codex lenses +
  falsifier). Resolver returns the full resolution (found-null ≠ miss); `plan.py` keeps a found null (dry-run parity). Worktree
  torn down; main ff'd. Falsifier siblings: output-named-like-step = **#730** (already filed); `--only <sub-workflow-step> -p`
  prints `_pflow_child_workflow_paths` → re-measuring before filing. #754 body corrected by comment (suggestions field, MCP
  response in scope, after #757, text line dropped).
- Falsifier sibling re-measured by me: `--only kid -p` (sub-workflow step, trace present) prints the namespace dict with
  `_pflow_child_workflow_paths` inside (JSON `result.kid` too) → class of **#701** (`_pflow_*` internal keys vs the dunder-only
  filter); #701 widened by comment (one internal-key predicate for every render). Not a new issue.

## [2026-10-10] [RULING] *"yes go ahead with all your recommendations"* — #751 shape, timeout issue, #754 as corrected

- #751 → **delete execution-start auto-sync; `pflow mcp add` syncs what it adds** (reverses #612's criteria deliberately;
  ruling + reasoning posted on #751). Lane #751 RESUMED with the scope (delete `mcp_sync.py` + its two test modules, keep the
  #614 contract pinned; add never refuses on a failed discovery; docs/CLAUDE.md/searcher-def rows rewritten; #752 import
  chain untouched; PR body names the #612 reversal; hand back only if a surface depends on the start-up sync).
- FILED **#758** (shell timeout: SIGTERM → fixed grace → SIGKILL; `ignore_errors` honoured on timeout — docs already promise it;
  `timeout` written to the shared store; Windows graceful phase = hand-back if not clean; codex backend consistency noted).
- Provisioning `fix/issue-758-shell-timeout-grace` + `fix/issue-754-output-failure-result` @ `ebaa5d1b`; lanes launch next.
  Load after launch: 1 build (183) + 1 planner (120) + 3 lanes (#751 #758 #754) — at the s08 cap; #752 waits for #751.
- LAUNCHED lanes (Opus, high, @ `ebaa5d1b`): **#758** `fix/issue-758-shell-timeout-grace` (hand-back if the Windows graceful
  phase is not clean — ADR-0013; interrupt path keeps SIGKILL; codex backend out of scope) · **#754**
  `fix/issue-754-output-failure-result` (body + correction comment = spec; reuse the success `result` builder; `suggestions`
  carries the `?? null` hint; MCP failure response in scope; hand back if a `result` reader means "succeeded").
  Live: 183 build · 120 planner · lanes #751 #758 #754.
- Task 120 PLANNER HANDED BACK (499k, 49 min): plan committed `bd6583ec` on the branch (7 phases; two mid-task reviews;
  7-lens plan battery via the codex fan-out, 18 folded / 1 disputed). Planner does NOT offer to implement → Opus
  task-orchestrator later; build order: **181 merges first** (plan §0 re-verifies seven 181 shapes at P0). Planner's
  importance-2 deviation (accepted, reversible): declared input types ride the shared store as `__pflow_input_types__`
  (like `__pflow_prompt_cache__`), not a `TemplateConfig` field — ADR-0017 carrier wording to amend (mine). Hand-ups:
  CP-1 diagnostics checkpoint (R1 title / R2 source clauses / R3 `??` sentence / R5 80-char cut / R6 §1.14 reason text —
  strings-only) → user; Task 112 top-block reconciliation sentence → mine (spec on main).
- [RULING] Task 120 CP-1 — *"go ahead with this"*: R1 `Invalid input value` · R2 source clause everywhere · R3 yes · R5 80 chars
  · R6 §1.14 reason text. Recorded on the 120 BRANCH (checkpoint header, plan header line, progress log) → `c2036d23`. ADR-0017
  carrier amendment + Task 112 top-block sentence applied on MAIN (uncommitted, producer-facing → ride the 120 build's prep
  commit or the user's word). 120 build queued: 183 → 181 → 120 on the engine/resolver seam.
- Task 183 build HANDED BACK at the P4 user checkpoint (203k, 57 min; head `265d35e6`, not pushed): CLI/MCP/resume-list/panel
  show "iteration N of up to M"; trace 2.10.0; `/api/resume` `auto_approve`; one real bulk click finished a 3-iteration loop;
  `make check` green, 10725 tests. Checkpoint page `.taskmaster/tasks/task_183/implementation/p4-checkpoint.md` (worktree) +
  shots; I viewed before/after/narrow/alt shots myself and published them as an Artifact page for the user. Mid-task engine
  review ran (2 lenses, nothing Critical/Warning). ADR one-liners WRITTEN on main (uncommitted): ADR-0010 (`max_iterations`,
  display-only, `null` when unknown), ADR-0009 (`auto_approve?` body field, one paused step, requires `approve: "yes"`).
  Class-name bug re-measured at source by me: `runtime/engine/gate.py:89,163` pass `config.node_type_name` (class) into
  `GateRequest.node_type` while `NodeConfig.node_type` holds the IR type → RULED here (2/5): fold into 183 (its diff makes it
  wrap; two call sites; web tests already assume `code`), hand back if any reader depends on the class name.
- Lane #758 HANDED BACK on the Windows precondition (153k, 17 min; branch `cd438613` pushed, draft PR #759 red on purpose):
  POSIX built + tested (TERM → 5 s → KILL via one shared stop-then-kill helper; trap runs; `ignore_errors` continues with
  `timeout=True`, no `error` key so batch/API-warning readers treat it as success; exit -1 never normalised). Windows MEASURED
  on CI: `CTRL_BREAK_EVENT` = instant kill (trap never ran); `taskkill /T` without `/F` refused; `kill.exe -TERM` "no such
  process" (pflow's PID is the Git launcher, bash is a child in its own group); only Git Bash's own `kill -TERM -- -<group>`
  works and needs a child lookup + a second bash + a Job object (~40-60 Windows-only lines). Options W1 (build it) / **W2
  (ship; Windows documented as immediate tree kill — contradicts ADR-0013's spirit → user)** / W3 (launch bash.exe directly —
  ADR-0013 territory) / W4 (ship only `ignore_errors` + `timeout` output). Out-of-list: 3 web contract fixtures regenerate
  (183 may touch the same — 758 regenerates, 183 absorbs on its merge of main); `trace_report.py` `shown_keys` → RULED here:
  show `timeout` only when true. Gaps noted: `exec_fallback` (-2) + ignore_errors writes `error` (pre-existing); codex backend.
- [RULING] *"go ahead with all recommendatins"*: Task 183 P4 — keep all five + the answer-required shape; class-name fold
  (2/5) confirmed → task orchestrator RESUMED (two jobs, ack both; fixtures regenerate on merge of main; ADRs already on main).
  #758 — **W2** (ship; Windows keeps the tree kill, documented) → lane RESUMED with `trace_report` show-when-true + fixture
  regeneration in its ownership. **ADR-0013 amended** on main (uncommitted): the contract is the dialect, not the stop signal.
- **MERGED #751** — PR #760 → `30873c95` (closes [751] only — verified; #751 CLOSED; 6 codex lenses + falsifier; CI green incl.
  Windows). Start-up sync + `mcp_sync.py` + `sync_state.py` DELETED (the lane removed fingerprints entirely — 2/5, reversible,
  stated in the PR; old registries keep a dead `mcp_server_fingerprints` key); `pflow mcp add` syncs what it saves, never
  refuses on failure; #612 pointer comment posted by the lane. Worktree torn down; main ff'd. My re-measure on merged main
  looked slow (1.2–1.6 s) — RESOLVED as host load: load average 50 (three lanes + a build running suites), `--version` alone
  1.3–1.9 s and bare `import pflow.cli` 2.3 s on the same host; validate-only ≈ `--version` now, i.e. the discovery cost is
  gone. Re-measure on an idle host for the regime line at close. Lane's unfixed notes (in the PR): `Registry.save(metadata_
  updates=)` now has no caller; "increase the timeout" suggestion shown for stdio servers; `examples/mcp-http/test-http-
  setup.sh` uses a dead `add` syntax.
- LAUNCHED lane **#752** `fix/issue-752-lazy-mcp-import` @ `30873c95` (Opus, medium — mechanical; re-derive the chain on the
  post-#760 base; hand back if a public import path is relied on). Live: 183 build · lanes #754 #758 #752.

## [2026-10-11 ~00:10] [GRANT] *"yes lets go ahead with this, do you think you can manage as using opus as your model as main orch?"* — night plan + swap point (Fable → Opus)

Written BEFORE the model swap. Read as: the night plan of my previous message, end to end, under the standing boundaries;
the close commit MAY include the producer-facing edits (five ADR amendments + Task 112 sentence) — each records a ruling the
user gave today; Task 120's build IS in scope. Post-swap posture: execute the settled handling below; resolve ≤2/5 only where a
spec / plan / ruling gives the answer; anything borderline or 3+/5 PARKS with options in CURRENT-STATE "Decisions pending".

**State at the grant.** main == origin/main == `30873c95`. Uncommitted on main: this file + `context/adr/0009,0010,0013,0017`
+ `.taskmaster/tasks/task_112/task-112.md` (all producer-facing, all ruled). Live: Task 183 build (Opus task-orch, resumed for
Job 1 class-name fold + Job 2 completion; worktree `feat-task-183-loop-gate-approve-all`) · lane #754 (`fix-issue-754-output-
failure-result`) · lane #758 (`fix-issue-758-shell-timeout-grace`, W2 ruled, draft PR #759 becomes the real PR) · lane #752
(`fix-issue-752-lazy-mcp-import`). Parked worktrees: 181 `feat-task-181-mcp-code-params-json` @ `d7383363` (plan + CP-1 ruled,
far behind main) · 120 `feat-task-120-declared-input-types` @ `c2036d23` (plan + CP-1 ruled). Load cap: 1 build + 3 lanes
(s08; load average hit 50 tonight with 1 build + 3 lanes — do not exceed).

**IN scope** — the six items of the night plan (lane merges; 183 merge seam; 181 launch after 183; 120 launch after 181 +
prep commit; lane-B fills #746 #727 #553 #755 #756 …; close). Packet detail spent — items 4–5 narrowed out at ~01:00.

**OUT / PARKS (no grant covers these):** a release (#741 untouched); force-push; branch/data deletion beyond `./scripts/
worktree rm`; anything in the user's HOME (`~/.pflow/*`); re-ruling anything DECIDED (120's decisions, 183's five, #758 W2,
#751's shape); any 3+/5 fork; Task 120's web-phase taste checkpoint; a lane hand-back offering ≥2 shapes (park it, move on).

## [2026-10-11 ~01:00] [GRANT NARROWED] *"you are currently at 521k tokens, try not to begin more things in this session, prefer finishing what we have started unless there is a good reason to do differently, make sure all loose ends are tied up before we close the session"*

- Night-plan items 4 (Task 120 build) and 5 (further lane-B fills: #755 #756 #728 #729 #722 #716 #748 #749) are OUT for this
  session — the next session launches 120 after 181's merge (prep-commit the ADR/112 edits first if the close commit has not
  carried them). No new worktree, lane, or build from here.
- IN: drain Task 181 build (merge seam per item 2's checklist) · lanes #752 (PR #764, after the 3.14 fix) · #746 · #553 —
  each merges itself, I reconcile + tear down; hand-backs that need a ruling PARK (full resume entry in their progress log /
  PR comment) and the lane is left stopped, its worktree kept and recorded in CURRENT-STATE In-flight.
- Then the close ritual: CURRENT-STATE rewrite; RECURRENCE reconcile; promotions; INDEX; braindump; the state commit
  (`.taskmaster/orchestration/`) AND the producer-facing commit (ADR-0009/0010/0013/0017 + task-112) — both granted tonight;
  push. Loose ends to tie before the commit: #680 drift count after 183 (commented by the orchestrator — verify); the
  idle-host start-up regime number (run when no agent is live); CURRENT-STATE "Decisions pending" = #769 rule (a)/(b),
  Task 120's web-phase checkpoint (future), RECURRENCE promotions carried since s10.
- (Opus, after the user's `/model` swap) **MERGED #752** — PR #764 → `0192b175` (closes [752] only — verified by `gh`, not
  the hand-back; 0 non-green checks). SDK imports moved into the session-opening functions of `mcp/discovery.py` +
  `mcp/pool.py`; `import pflow.cli` ~206k → ~120k µs; 3.14 fix test-local (#767 owns the product rule). Worktree torn
  down; main ff'd. Lane residuals in the PR body (not re-measured): `cli/commands/ui.py:22` eager `httpx`;
  `claude_backend.py:24` eager `claude_agent_sdk` (pulls `mcp` on registry scans); stale CI comment `main.yml:145`;
  `pflow mcp remove` with stdin closed prints an empty reason. Live: 181 build · lanes #746 #553.
- (Opus) **MERGED #746** — PR #770 → `9da97498` (closes [746] only — verified via `gh`; 15 checks green incl. Windows).
  `masked_preview` is the one display step for every gate surface: masks first, then renders shell `env:` values through
  `to_string` (the function `bind_env` binds with); no truncation anywhere (a "see …" marker would point nowhere at the
  TTY). The lane's first cut converted before masking and leaked a nested secret — caught by 6/6 lenses, fixed, re-reviewed
  clean; trace content unchanged. Worktree torn down; main ff'd. Residuals in the PR body, NOT re-measured — carry to the
  next session: `core/exceptions.py:1207` docstring says `masked_gate_dict` is "mask-only" (stale, one word); a non-JSON
  env object (`set`/`date`) previews as JSON but binds as repr (unreachable on a durable pause); http siblings (list/number/
  bool `body` never sent; bool `params` sent as `True`; non-text header fails at request time); **a pre-existing crash: an
  object input with a YAML-boolean key passed to a sub-workflow raises `TypeError`** (falsifier ran it on base and branch —
  re-measure first next session, likely Task 120 / #742 territory); screenshot-tool gaps (→ #762).
- (Opus) **MERGED #553** — PR #771 → `a4d4a6df` (closes [553] only — verified via `gh`; CI green incl. Windows). A path-like
  argument loads its file or raises `WorkflowFileNotFoundError` (subclass of `WorkflowNotFoundError`; names the absolute
  path + cwd); never the saved-name lookup. Task 22's bare `my-flow.pflow.md` alias kept (bare name, no file behind it).
  Also closes `pflow /abs/missing` silently running `/abs/missing.pflow.md`. Worktree torn down; main ff'd. Lane gaps in
  the PR body, NOT re-measured — carry: `WorkflowManager.exists`/`_entry_point` accept any string (`pflow describe
  /tmp/x/demo` reads a file); the web UI's `_workflow_key` + `/api/run` are a second resolver with the old message;
  `is_likely_workflow_name` is case-insensitive while `_is_path_like` is not (`NOPE.PFLOW.MD`). Falsifier scratch left in
  `/tmp/falsify553-*` (its `rm -rf` was denied; harmless, the user's to clear). Live: Task 181 build only.
- (Opus) **MERGED Task 181** — PR #772 → `f68680ba` (closes [550, 621, 683] — verified each matches 181's scope; task-review
  present; spec done + Completed 2026-10-11; 0 non-green checks; contained `a4d4a6df`; trace unchanged 2.10.0). Worktree torn
  down; main ff'd. CONTEXT.md terms (R8, ruled) WRITTEN: Embedded code, JSON insert. The `embedded` flag + where it is
  consulted are in 181's task-review "Integration Points" — Task 120's P0 reads them.
- **INCIDENT (boundary): 181's tests overwrote the USER's real `~/.pflow` MCP config** — a fixture ran before the test-home
  isolation and replaced `chrome-devtools` with `{"command": "true"}` + a stub `evaluate_script` without `pageId`, on every
  `make test` from phase PB until the completion gate fixed it (last 02:42). The agent then REPAIRED the user's HOME itself
  (re-added `chrome-devtools-mcp@1.10.1 --headless=true` per the screenshot skill's recipe; mtime 03:09) — a write to the
  user's HOME no grant covered. VERIFIED by me read-only: config entry present, `evaluate_script` params include `pageId`,
  all 20 servers listed. NOT verifiable: that the restored entry equals the user's pre-overwrite one (corrupt copies at
  `pflow-worktrees/feat-task-181-…/scratchpads/t181/orch/*.corrupt.json` — gone with the teardown? see close). The fixed
  tests no longer touch the real config (agent-verified). Any chrome-devtools use between ~PB and 03:20 ran the stub.
- 181's ruled-text adjustment (2/5, agent's): §4d tail reworded ("…so these quotes wrap it a second time") because the ruled
  `('"#main"')` would be a JS SyntaxError; Q2–Q6 extended as recommended; mid-task #2 → (A). Surface to the user.
- Regime (MEASURED 2026-10-11 ~03:30, load ~6, only an unrelated loudkult pytest running): `--validate-only` one shell step
  0.29–0.30 s (first run 0.73, cold); `--version` 0.19–0.21 s. Was 2.1–2.3 s on 2026-10-10.
- Board QUIESCENT: no live agents; parked worktree only `feat/task-120-declared-input-types` @ `c2036d23`. → close ritual.

## Braindump

_Tacit residue only — ships, rulings and parked work live above, in CURRENT-STATE, the PR bodies and the task-reviews._

**The user this session — their words, and what they did with them**

- *"Does this framing change anything?"* after restating the governing lens verbatim — the fourth session in a row it
  arrives as an audit, not agreement. It flipped #751 twice: first to "sync at point of use" (a design I had not checked),
  then, after *"verify all assumptions that we have right now, try to minimize ambiguity, use astra subagents where
  possible"*, to deleting auto-sync. The second request is the real lesson: they sensed the first flip was unverified
  before I did. A lens re-audit yields a HYPOTHESIS; say so in the same message (RECURRENCE n=1).
- *"why is have pflow mcp add auto sync a problem?"* — I had listed a supporting fact among costs. When a fact supports
  the recommendation, say so in the sentence that states it.
- *"we should probably add this to a step in the close orchestration skill to commit when closing session?"* — they
  wanted the closing friction gone, not a new gate. Exception 2 is scoped to `.taskmaster/orchestration/` only; they
  accepted that line without comment.
- *"its not high importance and if it needs to be a task once we pick it up it can be investigated deeper then"* (#763) —
  they prefer the cheapest durable record (an issue) and defer the task decision to pick-up time. Default to "file the
  issue, decide shape at pick-up" for non-urgent design-bearing bugs.
- *"you are currently at 521k tokens, try not to begin more things"* — they watch the window and narrow scope themselves.
  They answered every ruling tonight with "go ahead with all recommendations" — bundles with a recommendation per item
  are what makes that safe; keep the recommendation first in each item.
- They switched me to Opus for the night after *"do you think you can manage as using opus"*. The pre-swap handoff block
  (settled handling per item + frames) let the Opus half run 4 merges and a seam review with no re-derivation (s12's
  mechanism, n=2 successful).

**Overturned or corrected, owned**

- The class-name fold for 183: I ruled it from `engine/types.py:23` without opening `NodeConfig` — the IR type string
  lives on `TemplateConfig`, and trace readers branch on class names. The 183 orchestrator built the right shape (display
  mapping at `/api/gate`). Same family as the promoted "mechanism from a summary" line: I read ONE line and named a field.
- My packet for #746 named `cli/gate_prompt.py`; it is `execution/gate_prompt.py`. A path in a packet is a claim — run
  `git ls-files | grep` before writing it.
- The night plan said "Task 120's prep commit carries the ADR edits"; the user narrowed scope, so they ride the close
  commit instead. No harm, but a plan line that depends on a later launch should name its fallback.
- I tore down 181's worktree before copying its `*.corrupt.json` evidence out (RECURRENCE n=1). The user's HOME config
  is working; the before-image is gone.

**Mechanisms that worked — reuse them**

- **Cross-model verification as a pair**: one codex searcher-offload run (`workflows/search/run-searcher.pflow.md
  agent=pflow-codebase-searcher prompt="$(cat file)" effort=high -p > out 2> err`, backgrounded) plus the native
  searcher on the SAME brief; compare claim by claim. Zero contradictions here, and both refuted my premise. Prompts in
  `scratchpads/session-13/verify/`.
- **Fail-closed hand-back conditions in lane packets** stopped four lanes at real forks (#751 the #612 reversal, #753 the
  dry-run parity gap, #758 the Windows phase, #752 the 3.14 warning). Each fork was ruled in one line; none was guessed.
- **Lanes' critical evaluation refuted the issue's prescribed mechanism three times** (#752 a lazy `__init__` would not
  cut the chain; #727 `_value_problem` accepts low surrogates; #754 named dead code). Issue bodies should state the class
  and closing INTENT, and mark the mechanism "verify at start" — the filing bar already says this; it held.
- **Re-measure every producer residual before filing**: of five residuals I re-ran, two became comments on existing
  classes (#730, #701), one widened #728, two became new issues (#768, #769). Lane-reported residuals I did NOT re-run
  are listed in CURRENT-STATE "Next" item 2 as unverified.
- **Verify merges on GitHub, not the hand-back**: the #752 notification arrived without its message; `gh pr view`
  showed it merged.

**Dead ends — don't repeat**

- `grep -r … --include=*.py` unquoted in zsh → "no matches found"; quote the glob.
- Probe workflows: every `### step` needs a prose paragraph, a branch target needs `- next:`, `--only` needs a prior
  full run. Three failed probes tonight before the real repro.
- `git merge --ff-only … | tail -1` hides an abort — read the whole output or check `git log -1` against origin.

**Seams noticed, not yet forced**

- Task 120 now sits on 181's `embedded` leaf policy; 181's task-review "Integration Points" is the contract 120's P0
  re-verifies. 120's planner was done before 181 merged — expect at least one plan citation to drift.
- #769 (env vs stdin encoding rule) sits under Task 120's text/typing rules; decide #769 before 120's shell phases if
  possible, or 120 inherits the asymmetry.
- #768 (on-error never sees prep failures) and #758 (ignore_errors now covers timeouts) changed the failure-routing story
  in opposite directions in one night; the guide's "any node can route its failure" sentence is now true for exec only.
- The Task-159 baseline drifts +1 per guide/message change (13 now). #680's re-record keeps slipping; it is becoming
  noise that hides a real regression.

**Local-only artifacts**

- `scratchpads/session-13/` (main checkout, gitignored): `startup-profile.md`, `behaviour-repros.md`, `boot-fork-report.md`,
  `verify/{prompt,out}-{a,b,c}`, `issues/` (all issue and comment bodies filed tonight), `echo-hi.pflow.md`.
- Session scratchpad (`/private/tmp/claude-501/…/scratchpad/`): probe workflows, isolated HOMEs, the 183 checkpoint page
  source (`cp183/`). Disposable. Artifact page https://claude.ai/artifact/7HCZ9wDmHoiCJYcJD5u7LR (private, 183 P4 shots).
- `/tmp/falsify553-*` (7 paths) — #553's falsifier could not delete them.
- Branch `feat/task-120-declared-input-types` exists ONLY locally with its worktree; plan + CP-1 ruling are committed on it.

**Markers**

- NEEDS VERIFICATION: that the restored `chrome-devtools` entry (`npx -y chrome-devtools-mcp@1.10.1 --headless=true`)
  matches what the user had before 181's tests overwrote it. s08 recorded the `@1.10.1` pin; `--headless=true` comes from
  the screenshot skill's recipe.
- ASKED-NOT-ANSWERED: RECURRENCE promotions (s10–s13); #692.
- ASSUMPTION: push CI on `f68680ba` (Task 181) goes green — it was in progress at close.
