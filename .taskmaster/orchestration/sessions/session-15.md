# session-15 — 2026-10-11

## [2026-10-11 22:20] main orchestrator — boot + reality diff

- Booted per the role prompt (Fable, user `/model` saved default). Predecessor `pflow-main-orch-session-14` live (idle) → ONE
  bounded question sent (answer pending at this write). Boot fork → `scratchpads/session-15/boot-fork-report.md` (pending).
- Reality vs CURRENT-STATE: NO drift — main == origin/main == `5b39ec21`; push CI green on `5b39ec21` (run 38171241238);
  no open PRs; newest issue #807; worktrees `feat-task-184-run-outcome` @ `aa96b450` (clean, plan + CP-1-RULED.md present,
  5 behind main) and `fix-issue-799-batch-child-failure-redaction` @ `05884642` (uncommitted `batch_errors.py` +
  `test_json_diagnostic_redaction.py`, matches the park comment; 5 behind main); `./scripts/tasks --check` clean; load ~5;
  no processes rooted in worktrees.
- User focus: continue where session-14 left off, carefully deciding the highest value / leverage work.
- A searcher is extracting the 184 plan's per-phase file list (mechanical, for collision analysis against lane fills — I do
  not read the plan).
- Predecessor ANSWERED: nothing beyond the file. Boot fork DONE (`scratchpads/session-15/boot-fork-report.md`, 217k).
- MEASURED collision (grep on main `5b39ec21`): `compact_batch_error_detail`/`compact_batch_output_value` (the compactor #799 B
  splits) are called from `success_formatter.py` (184 P1 `git mv`s it to `run_outcome.py`) and `error_formatter.py` (184 P1
  deletes it) → #799 must merge BEFORE 184's P1; 184's P0 (`runner.py`) is disjoint. Also used by `trace_report.py:1188`,
  `workflow_output.py:113`, `workflow_executor.py:689-693` (the waived line).
- Fill candidates vs the 184 plan file list (searcher-extracted): #795 disjoint; #722 disjoint (its 4 callers in
  `execution_service.py` only call `validate_execution_parameters`; the deletion is inside `mcp_server/utils/validation.py`);
  #801 file-disjoint but the top-level `error` string is the document builder's → after 184; #755 names
  `runtime/engine/error_context.py:77-78` (a constant) → needs the user's engine-exclusion waiver; #802/#806/#807 touch
  `cli/commands/run.py` (184 P2) → after 184; #803/#805 task-shaped.
- Task 152 spec: header refreshed (s14 post-close) but the BODY is stale (April mapping table, tool count 11 vs 13 measured,
  `cli/resources/guide/` paths, moot Task-77 section); Phase 3 A/B undecided with no RESOLVE AT START block; 184's hand-off
  (structured MCP response = 152's question) has no receiving line → NOT planner-ready; refresh is mine this session.
- PROPOSED to the user (3/5, awaiting the word): launch 184 build (predicate: P1 waits for #799's merge) + lanes #799 (B) ·
  #795 · #722; hold #801 until 184 merges; #755 next fill pending the waiver; 152 planner withdrawn until its spec is refreshed.

## [2026-10-11 22:50] [RULING] the user approved the launch set; Task 152 parked on a strategic question

- The user accepted the recommendations (184 build · #799 B · #795 · #722; #801 held until 184; #755 engine-constant waiver;
  yank question closed). Task 152 WAITS — operative wording: *"right now using the cli works good and we've seen no
  indication users would prefer an mcp, so we are waiting for more information before deciding wheter parity or removing
  mcp is the right call"* → the MCP SERVER's future is an open strategic question; 152 (parity) and 178's server half are
  on hold behind it; the MCP client (nodes, discovery, probe) is unaffected.
- My call (2/5, visible): #722 is an MCP-server fix → #755 (waived, CLI-facing, disjoint from 184) takes the third lane now;
  #722 is the next fill after #799 merges. Reversible in one word.
- Commit gate (DECISIONS #5): nothing producer-facing uncommitted on main (only this session file) → lanes branch from
  verified `origin/main` `5b39ec21`. Provisioned sequentially: `fix/issue-795-examples-baseline-net`,
  `fix/issue-755-stderr-preview-tail` (both @ `5b39ec21`). 184 and #799 reuse their parked worktrees (both 5 behind; packets
  order `git merge origin/main` first — MEASURED delta pasted into #799's packet; code in it from PR #800 + #798).
- Packets written into each worktree's `scratchpads/session-15/` (verified: `grep -c` = 1 each). 184's packet carries the
  fail-closed predicate (P1 waits for `gh issue view 799 --json state` = CLOSED; 90-min hand-back), the CP-1 record-first act,
  F20 + `ui/server.py` notes, the #801 seam claim, the #795 CI-net claim; #799's the ruling, the waiver line, the measured
  caller list, and the "184 waits for you — keep it small" collision; #795's the hand-back-before-building on deletion;
  #755's the one-line engine waiver + the #801 purity note.
- LAUNCHED (Claude, all `model: opus`, `effort: high`): Task 184 task-orchestrator (implement-from-plan) · lane #799 (replacement
  lane in the parked worktree, option B) · lane #795 · lane #755. Load: 1 build + 3 lanes = the cap. Queue: #722 after #799
  merges; #801 after 184 merges; #802/#806/#807 after 184; #803/#805 shape at pick-up.
- **MERGED #755** — PR #808 → `1d1bdf9c` (closes [755] only — verified via `gh`; 15/15 checks incl. Windows + `baseline-oracle`;
  6 codex lenses + falsifier). One `head_tail_preview` (100 head + 300 tail + omitted-count marker) at the four sites incl. the
  waived engine constant (`max_stderr_len` param removed — no caller passed it); JSON unchanged; baseline 0/87 drift; rule line
  in `core/CLAUDE.md`. Worktree torn down; main ff'd. Residuals (lane-reported, NOT re-run): a FIFTH site
  `success_formatter.py:639` (exit-0 stderr warning keeps first 300 chars; falsifier hit `curl … | cat`) → Task 184's P1 file,
  relay with its resume; `batch_errors.py:162` cuts a previewed string to 200 chars after the marker → #799's file, relayed to
  the live lane as a claim; #806 indent loss seen, left alone.
- **MERGED #799** — PR #809 → `93798a80` (closes [799] only — verified via `gh`; CI green incl. both Windows jobs + MCP smoke;
  6 codex lenses + 2 follow-up reviews + falsifier). Option B built: printing names unchanged (`compact_batch_*` now redact
  `child_failure` by POSITION not shape — shape detection leaked a bundle-shaped body), runtime calls the raw
  `archive_batch_output_value` (the waived line); trace byte-identical to base; name-keyed `failures` kept (redacting by name
  crashed on a step named `auth`); ratchet pins raw-to-runtime. Worktree torn down; main ff'd. Residual 1 (EXECUTED by the
  lane): unrecognised shapes (`-o each.errors`, declared `${each.errors}`, parent exposing child batch output) still print raw →
  RULED here (2/5): not recursive compaction; the whole-document pass at 184's emit seam = #801's mechanism (comment on #801).
  Residual 2 (#755's marker cut) left; 3 empty `API Response:` header; 4 siblings unchecked with a secret.
- 184 P1 UNBLOCKED: addendum `scratchpads/session-15/addendum-p1.md` in its worktree (predicate measured, F20 PROVISIONAL A —
  plan's current behaviour, user ruling pending; #755's fifth site in its P1 file; #799 residual 1 = scope note; two text-tier
  observations from the consumer-report evaluation). Resuming the orchestrator.

## [2026-10-11 ~23:40] [RULING] the user accepted the recommendations on merged + new issues; verify with astra before filing

- Read as: F20 → A (184 addendum updated, orchestrator RESUMED for P1); file the stdin-rule issue (closes the #666 question too)
  and the exit-code issue (after 184, at its status→exit seam); file `__file__` for file-loaded code steps, `mcp describe`
  array-of-object flattening (after re-execution), the dev-install `--version` facet; widening comments on #732 #804 #806 #743
  #740; #804 (widened) takes the next lane slot. Operative wording: *"make sure there are no assumptions and amibiguity before
  we file, prefer using pflow astra searchers to verify"* → six astra offload briefs launched (`scratchpads/session-15/verify/
  prompt-*.md` → `out-*.md`), an Opus agent re-executes `mcp describe` with a real test server; the native searcher's earlier
  mechanism pass is the cross-model pair for stdin/-o/describe/exit/version.
- LAUNCHED lane **#722** `fix/issue-722-mcp-input-blocklist` @ `93798a80` (Opus, high; the approved queued fill; hand back if any
  sink evaluates an input value; 184's `execution_service.py` untouched). Live: 184 (P1) · lanes #795 #722 · one slot held for #804.
- Consumer-report evaluation DELIVERED (verification: `scratchpads/session-15/consumer-report-verify.md`, all 9 executed claims
  held; mechanism pass: 5 cites corrected incl. `--help` "No description" = dead code, docs exit-code table omits 3/4). Declined
  per s13 triggers: deprecation/`requires-pflow`, `-p` multi-output, `PFLOW_HOME`. Declined new (trigger: a second consumer):
  `## Failures` section, per-step exit propagation, refusal API, `key=@file`, project-local registry, MCP server version record.
- Verification DONE: six astra offload passes (`scratchpads/session-15/verify/out-*.md`) + two executed re-runs (`mcp-describe-
  verify.md` with a real stdio server; `dup-verify.md`) — all converge with the native pass; corrections folded: "unknown-input
  error never lists inputs" REFUTED (lists when no fuzzy match); `describe`/`--help` already share one renderer (defect in the
  `--help` caller); `__file__` needs `_source_line`-style plumbing (compiler drops `_source_files`); the exit-code split must key on
  PHASE (engine started or not) — diagnostic category misclassifies `NodeError`/loop errors/child-workflow validation; stdin fix
  needs the Windows `FILE_TYPE_DISK` detector too; timeout text prints 2× (+ header), not 3×.
- FILED serially (each read back): **#811** `mcp describe` flattens array-of-object params + invalid snippet placeholders (sync-time
  structure loss; MCP client side) · **#812** two version helpers / editable-install `+g<sha>` display-only (registry comparison
  keeps the plain version) · **#813** file-loaded code step has no `__file__` (mirror `_source_line` plumbing) · **#814** stdin rule
  (owner ruling recorded; reverses two Task 115 choices on purpose; subsumes #666; after 184 — `run.py`) · **#815** exit 2 for
  pre-run errors at 184's status→exit table (after 184). Comments: #804 widened (members a–e + discovery_formatter; decision (a)
  working ruling), #732 widened (repeated `-o`, bare tokens), #743 (output keys = its design question), #740 (guide file-ref
  sentence, stdin strip doc, docs exit table), #806 (reason 2×, timeout 2×, warnings after error, wrong step tag), #666 (→ #814).
- Provisioned `fix/issue-804-input-usage-one-helper` @ `93798a80`; packet verified; LAUNCHED lane **#804** (Opus, high; (a) as the
  working ruling; member (d) last and only if 184 merged). Live: 184 (P1) · lanes #795 #722 #804 = the cap.
- **MERGED #795** — PR #810 → `1789a67a` (closes [795] only — verified via `gh`; CI green incl. both Windows shards, run 38177538148;
  5 codex lenses + falsifier). Net KEPT, not deleted (evaluated: the Task-159 oracle touches one example; nothing else checks
  on-error/coalesce/output-resolution/retry/nested run JSON); `capture.py --check` is a step in the required `baseline-oracle` job
  (+25 s); per-example stdin isolated (the #783 class — `echo junk |` had made 28/29 differ); exit 0/1/2 like `verify.sh`;
  manifest.json is the list; OS/arch normalised (falsifier caught a Darwin-recorded capture that would have failed on ubuntu);
  11 re-recorded + 1 deleted (`typo-on-failed-node` — the issue's list was wrong: #704 deleted that example); README + examples/
  CLAUDE.md row; 8 harness tests. Worktree torn down; main ff'd. SHARED TOOLING CHANGED → text deltas sent to 184, #804, #722
  with the producer rule verbatim. Residuals (lane-reported): no every-example-is-listed check (49 exclusions); offline examples
  never listed (`nested/document-processor`, `examples/invalid/` fixtures); `capture.py` outside `make check` like the 159 harness.
  Host load 68–70 at this merge (above the ~40 launch ceiling; #804 launched before I saw it) → RECURRENCE host-load at close.
- Lane #804 HANDED BACK pre-build (122k, 10 min): class ~2× the issue — six more readers of `required` alone (`context.py:144`,
  `context_builder.py:783-818`, `path_validation.py:432-455`, `graph/build.py:190` IOPort → web UI `*`, `summary.py:80-100`
  `suggested_run_command` in ~50 Task-159 cases, `validator.py:1974`); the remedy text reaches MCP + the web run form verbatim
  (#777 class); (a) exact-case is POSIX-only (Windows `os.environ` is case-insensitive). ESCALATED (3/5: A packet scope / B close
  the class [rec] / C task; remedy (i) CLI-shaped + source clause [rec] / (ii) neutral). RULED here (3/5, settled by the user's
  standing "close bug classes" + accepted recommendations — surfaced to the user to overrule): **B + (i)**; ownership widened by
  name; fail-closed: UI change confined to the `IOPort.required` computation (else hand back → Fable UI phase) + screenshot
  verification; every baseline re-record diff = the placeholder line only; one predicate derived from `ir_preparation.py:93-134`
  (`default: ""` = required). No case claim in any text. Lane RESUMED.
- **MERGED #722** — PR #816 → `8e2a9b3e` (closes [722] only — verified via `gh`; CI green; 6 codex lenses 0 findings + falsifier:
  `__import__("os").system(...)` through inputs/env/registry_run/probe created no marker). Regex blocklist deleted; structural
  checks kept; guide sentence in `guide/nodes/mcp.md` deleted (+ 1 baseline case re-recorded, two-line diff — outside ownership,
  disclosed); parity test MCP vs CLI. Worktree torn down; main ff'd. Finding (EXECUTED by the lane): callers can override
  internal `_pflow_*` keys — `pflow a/main.pflow.md _pflow_workflow_file=<dir b>/x.pflow.md` loaded a child from dir b (the
  name check rejects only `__x__`; `runner.py:301` `setdefault` keeps a pre-injected value by design for internal callers);
  `_pflow_depth`/`_pflow_stack` bypass NOT run → verification launched before filing. Other residuals: two "security" comments
  in `execution_service.py:259,267` (184's file); `mcp_server/utils/errors.py` unused re-export; 1 MB limit MCP-only.
- Host load back to ~17 → launching the two disjoint fills: #813 (`__file__`) and #812 (version). #811 HELD: #804's widened
  ownership includes `registry/context_builder.py`, which #811 also edits → after #804. #814/#815 after 184.
- Provisioned `fix/issue-813-code-step-file-provenance` and `fix/issue-812-one-version-helper` @ `8e2a9b3e`; packets verified.
  LAUNCHED lanes **#813** (Opus, high; hand back before building if the fix needs `runtime/engine/instrumentation.py` — evaluate
  the node-attribute route first) and **#812** (Opus, high; display-only suffix; registry never sees it). Live: 184 (P1) · lanes
  #804 #813 #812 = the cap. `_pflow_*` override: Opus re-execution agent + astra pass running before any filing.
- `_pflow_*` verification DONE (Opus re-execution `pflow-keys-verify.md` + astra pass `verify/out-pflowkeys.md`, converged): the
  override is real on CLI and MCP; depth/stack forgery is stopped by the cycle check (CLI strings crash with a bare TypeError; an
  MCP int depth lifts the top-level depth cap); NO production caller pre-injects `_pflow_workflow_file` — the runner's `setdefault`
  comment is stale. FILED **#817** (one shared name predicate gains the prefix → CLI, MCP, UI and declared names; `setdefault` →
  assignment; after 184 + #804). Read back.

## [2026-10-12 00:40] Consumer-report evaluation — durable disposition (for the next main orchestrator)

- A sibling project that dogfoods pflow (never named in this repo) produced a 420-line report: a "native workflow signature" ask
  plus 11 friction items, each reproduced by its authors on `5b39ec21`. Evaluated this session by: a 9-claim re-execution
  (all held), a native mechanism pass (5 cites corrected), six astra offload passes, two real-server/duplication re-executions.
  Full map: `scratchpads/session-15/consumer-report-disposition.md` (gitignored — the ISSUES are the durable record).
- Outcome in one line: 7 new issues (#811 #812 #813 #814 #815 #817 + the #804 widening carrying the headline), 6 widening
  comments (#804 #732 #743 #740 #806 #666), 1 refuted claim, 9 declines (3 by the s13 triggers, 6 new with "a second consumer"
  as the trigger). Two user rulings recorded in issue bodies: the stdin rule (#814) and exit 2 for pre-run errors (#815).
- What the next orchestrator must know: the report's headline (a hand-written contract card because `describe` is incomplete)
  is #804's class — its lane is live under option B; the JSON form of describe belongs to Task 117 (refresh its spec when it is
  picked up); output KEYS belong to #743's design; stdin + exit codes + `_pflow_*` + text helpers + resume view all queue on
  `cli/commands/run.py` behind Task 184 → ONE at a time (order: #801 → #815 → #814 → #806 → #807 → #817).

## [2026-10-12 00:45] Pre-swap handoff (Fable → Opus) — written, then EXECUTED by the Opus half (settled handling per live agent,
authority lines, the run.py serial queue, end-of-night dogfood + close); cut at close as spent — every item landed or is in CURRENT-STATE.

## [2026-10-12 01:05] Second external report — demo-production studio (web Viewer + narration) — FIRST PASS only

- File: `~/projects/video-generation/projects/pflow-teaser/pflow-findings.md` (NOT `projects/pflow-teaser/`; append-only, newest
  last; 7 findings on `1789a67a`). The user: *"the next main orch should read both files itself as well"* — both reports are READ
  IN FULL by the next orchestrator, not inherited from this triage. Astra mechanism pass launched → `verify/out-teaser.md`
  (read it before acting; the native pair not yet run). UI items are Fable-routed (web UI = first-class product) and need the
  screenshot skill — none launched (load 183; the swap).
- First-pass dispositions (dedup done against open issues; nothing filed):
  - **F1** caption card (`.node-callout`, 320 px) clipped under the left rail when the pane ≤1250 px — UI BUG, HIGH for the demo;
    no open issue. Needs a screenshot repro (window ≤1250 CSS px, `pflow ui focus … --say`). Candidate lane; Fable per routing
    → the user's per-launch word.
  - **F2** `pflow ui frame` pans without a highlight — design ask (a transient ring / `--highlight`); Task 174 territory; UI/taste
    → user decision (they produce the demo).
  - **F3** stale paused run: (a) `resume list` lacks a workflow filter / path / start time in JSON → **#734** (widen with this
    evidence); (b) `--approve no` refused "file edited since the run paused — use --force" — a DENY executes nothing, so the Task
    180 edit check should not gate it → design question (3/5, user); (c) ">60 s to deny" — **NOT reproduced in the trace**: the
    cited trace (`…78ef1a4a-expense-report-20261012-000848…`, JSONL, 8 records) shows 4 cached steps and `final_status: denied,
    duration_ms 1780.96` → the engine took 1.8 s; the wait was outside the run (host load during takes? startup?) → re-measure
    with `time` on a quiet machine before any filing. Its "Steps completed: 0 of 9" = #737 / Task 184 (owned).
    `--discard` ask = a cheap deny; falls out of (b).
  - **F4** run panel "all pending + Running" while the CLI paused with cached steps; badge "Run success · 5 nodes" vs 9 steps —
    UNVERIFIED by them; the badge count is the trace trailer's `nodes_executed` (184 leaves the trailer's count out of scope) →
    probe needed (gated run with cached upstream, watch the panel). Candidate issue after a probe.
  - **F5** source checkout serves a stale Viewer bundle silently — the recorded gotcha class ("reuse-if-up probe serves old code");
    a warn when `web/src` is newer than `src/pflow/ui/static/` (or a `make` build) → small dev-tooling issue after the astra pass
    says how the bundle is located/built.
  - **F6** `--say` cards accumulate; no scripted dismiss (`clear-captions` / `--say --replace`) → UI feature, Task 174 territory →
    user decision.
  - **F7** gate panel shows an `env:` value as a JSON blob → doc hint in `guide/features/approval.md` ("human-readable text on
    stdin") → #740-class doc member after reading the renderer.
- Decisions for the user at pick-up: F1 lane on Fable? F2/F6 build (UI features for the demo)? F3(b) deny without `--force`?
- [RULING] on the demo-studio items — operative wording on routing: *"falbe is not needed when its just fixes, falbe is for taste
  and designining"* → a UI BUG FIX routes Opus (lane B floor), Fable stays the taste/design trigger (consistent with ORCHESTRATION
  Model routing's "unsettled look/feel judgment, not the file location"; third user instance after s11 #714 and s12 120-PF →
  propose at close: the wording into DECISIONS #24's row). F1 → Opus lane after a screenshot repro. F2 + F6 → the user accepted
  building them (one narration-surface issue + Opus lane; packet constraint: REUSE the existing `focus` highlight visual for
  `frame --say` and the existing callout-close path for `--replace`/clear — if no reusable visual exists, hand back: that is a
  design question → Fable → the user's word). F3(b) deny-without-`--force` → *"not sure, lets decide next session"* (parked).

## [2026-10-12 ~01:30] Opus half (user `/model` swap; saved as default) — executing the pre-swap handoff

- Lane #813 HANDED BACK pre-PR (two commits, not pushed): `__name__ = "__main__"` (my accepted call) lets a file-loaded script's
  `if __name__ == "__main__": sys.exit(main())` silently end the run (exit 0, 0 bytes, downstream never runs; argparse → exit 2
  parsing pflow's argv) — main succeeds. RULED here (strictly-safer narrowing of my own call, within the handoff authority):
  **A** — leave `__name__` as on main, add `__file__` only. Lane RESUMED (full `make test` re-run, PR, merge). Underlying bug
  (the code node does not catch `SystemExit`; inline `sys.exit(0)` already kills main silently) → Opus re-execution agent
  launched before filing.
- SystemExit verified (Opus agent `sysexit-verify.md` executed + astra `verify/out-sysexit.md`, converged; astra added member 2:
  the CLI skips trace finalization on ANY escaping BaseException, Ctrl-C included). FILED **#821** (member 1 at the worker's `exec`
  only — never around `future.result()`; member 2 a finalize-on-every-exit at the CLI boundary, after 184). Read back.
- Demo-studio astra pass DONE (`verify/out-teaser.md`): F1 mechanism CONFIRMED (TD callout placed `rect.x-320-28`, no clamp, narration
  disables frame-on-mount, `focus` fits the node only); F2 CONFIRMED + a reusable visual exists (`hover-mark` = the focus ring without
  selection); **F6 mostly REFUTED — `pflow ui clear-focus <wf>` already dismisses all cards + stops audio** (only a caption-only
  dismiss is missing) → a guide line, not a lane — the user's approval rested on "no scripted dismiss", so reported back, not built;
  F3(a) `resume list --output-format json` EXISTS with workflow_path (no filter, no start time → #734); F3(b) deny still runs the
  restored-step edit check (only the gated-step definition check is skipped) — parked; F3(c) preparation before a deny is real
  (validate + compile + restore) but no 60 s cause visible; F4 badge "5 nodes" = by design (restored excluded), "all pending +
  Running" unexplained; F5 CONFIRMED (no source-age check; `make install` does not build the bundle; `make ui-build` does);
  F7 CONFIRMED (one generic formatter JSON-dumps objects; guide has no stdin-for-humans hint).
- Three lanes opened PRs: #818 (#804), #819 (#812), #820 (#813) — self-merging after CI. Load ~6. Verification agent launched for
  F1 screenshot repro + F4 panel probe + F3(c) timing (own port, rebuilt bundle, isolated HOME).
- **MERGED #804** — PR #818 → `f74e2202` (closes [804] only — verified via `gh`; 16/16 checks; 6 codex lenses + falsifier). Option B:
  one `input_usage`/`usage_arguments` + placeholder table in `core/types.py`; required ⇔ `required` not false AND default None or
  `""`; every surface (describe, --help, MCP describe, save, skills, find, both LLM contexts, template hint, web `IOPort.required`,
  analyze-cache command, static + runtime sub-workflow fallback) reads it; missing-input remedy with source clause; parity test with
  a literal table. Fail-closed held: UI = `IOPort.required` + 2 tests only (before/after shots); 58 baseline re-records verified
  placeholder-only + a 59th (guide sentence, separate commit, named) — ACCEPTED here (2/5: same mechanism as #722's guide re-record,
  disclosed). Behaviour changes stated: a child `required` + `default: ""` must come from the parent; untyped inputs show `any`.
  Worktree torn down; main ff'd; text delta sent to 184 (59 cases moved → merge main before re-recording; member (d) offered).
  Residuals: (d) `--help` heading/description (184's file); `execution_tools.py:244` `param=<value>` (184's); stale comments in
  `web/src/graph/io.ts`; **settings `--help` says settings env is "not injected implicitly" but a settings `GITHUB_TOKEN` reached an
  undeclared shell step (falsifier; `llm_config.py:245-247` copies settings env into `os.environ`)** → re-execute before filing;
  `validator.py:1974` label.
- Provisioned `fix/issue-811-mcp-describe-param-structure` @ `f74e2202`; evidence copied; LAUNCHED lane **#811** (Opus, high; reuse
  #804's placeholder table). Live: 184 · lanes #812 (PR #819) #813 (PR #820) #811.
- Demo-studio verification DONE (`teaser-verify.md`): F1 VERIFIED worse than reported (card's left edge −240 px at 1200, −140 px at
  1400, fits ~1680; I viewed the 1400 shot — caption reads "ow: five steps…"); F3(c) REFUTED (0.9–1.4 s wall; startup ≈ the gap);
  F4 PARTIAL (transient all-pending 0.4–1.2 s; CLI-launched runs show no RunProgress in follow-newest; badge excludes restored by
  design); F5 bundle fresh tonight. FILED **#822** (F1, Opus lane) · **#823** (F2 reuse-only + the clear-focus guide line) · **#824**
  (F5) · comments #734 (F3a) #740 (F7). F4 NOT filed (UI polish; user's demo — ask). Disposition table appended to
  `scratchpads/session-15/consumer-report-disposition.md`. #822/#823 launch when slots free (one live `pflow ui` at a time).
- Lane #811 HANDED BACK pre-build (its first hand-back message never arrived — the lane restated on request): `convert_to_pflow_params`
  reads only a literal `"type"`, so `$ref` (FastMCP model args) and every `Optional[X] = None` come out typed `str` (EXECUTED) —
  that type drives validation + runtime handling. Options A1 (one recursive walk → real types + `structure`; validation follows the
  corrected type) / A2 (structure only); P1 (snippet = required params only, placeholders kept) / P2 (#804 table — its `'[...]'`
  entries read as a string in a `.pflow.md` line, EXECUTED); new `src/pflow/mcp/schema.py` sharing the walk with describe's output
  paths. RULED here (settled by "close bug classes"; A2 leaves a contradiction, P2 ships a validating-then-failing placeholder):
  **A1 + P1 + module**; fail-closed: only previously-wrong types change verdicts (before/after table from a real server), no common
  pydantic shape becomes a union, no trace/baseline/examples drift. Lane RESUMED.
- **MERGED #813** — PR #820 → `92dddfc4` (closes [813] only — verified via `gh`; #821 still open; 16/16 incl. both Windows shards +
  MCP smoke + `baseline-oracle`; 6 codex lenses + falsifier). Option A as narrowed: resolver records `_resolved_files` (optional IR
  key, stripped from both hashes — 190 workflows byte-identical); compiler sets a `source_file` ATTRIBUTE on the code node (no
  param, no engine edit); `__file__` for file-loaded bodies only; `__name__` unchanged ("Refs #821 — not a closing PR"); one
  `_load_file` helper replaced three bookkeeping copies; 1 baseline case re-recorded (guide line). Worktree torn down; main ff'd;
  delta to 184. Residual: `graph/build.py:841-848` recalculates the path (comment on #813).
- Provisioned `fix/issue-822-caption-placement` @ `92dddfc4`; evidence (shots, DOM JSON, probe) copied; LAUNCHED lane **#822** (Opus
  per the owner's routing ruling; hand back on any new visual). Live: 184 · lanes #812 (PR #819) #811 #822. #823 after #822
  (shares `GraphView.tsx`, one live `pflow ui`).
- **MERGED #812** — PR #819 → `923725b8` (closes [812] only — verified via `gh`; CI green incl. both Windows shards; 6 codex lenses +
  falsifier ×2). One `get_version()` (registry reads it, never suffixed); `get_display_version()` adds `+g<sha>[.dirty]` on editable
  installs via ONE `git describe`, only on `--version` (eager callback — no git on every command), pinned to the checkout (GIT_* env
  dropped, ceiling set — falsifier caught a hook's GIT_DIR naming another repo); release skill's fallback step removed (+ `.agents/`
  twin). REAL SURFACE checked by me: `uv run pflow --version` → `pflow version 0.16.0+g923725b8`. Cost 50–76 ms under load ~160
  (git startup). Worktree torn down; main ff'd. SHARED TOOLING (release skill) changed — no live producer reads it. Residuals:
  `pflow wf.pflow.md --version` "Unknown option" (pre-existing); git+https installs show the plain version; MCP serverInfo → 178.
- Provisioned `fix/issue-821-code-step-systemexit` @ `923725b8`; LAUNCHED lane **#821 member 1** (Opus, high; python_code.py only; PR must not close #821 — member 2 after 184). Live: 184 · lanes #811 #822 #821m1. Load 25.
- **MERGED #811** — PR #825 → `f2da18e2` (closes [811] only — verified via `gh`; 16/16 incl. `baseline-oracle` + 3 Windows jobs; 7 codex
  lenses + re-review + falsifier). Worse than filed: every FastMCP `$ref` and `Optional[X]` param was registered `str` → object params
  arrived as JSON text and non-parsing servers rejected them (EXECUTED on main). New `mcp/schema.py` = the one reader of MCP schemas
  (input params + describe's output walker; `convert_to_pflow_params` gone); types `dict` / `X` / `list[...]`, fields in `structure`
  (depth 3); unions only without a text member (both Criticals were union regressions, fixed); describe prints fields + defaults +
  enums; one snippet function, required params only. Fail-closed held (before/after table in the PR). Evidence copied to
  `scratchpads/session-15/lane-811-evidence/`; worktree torn down; main ff'd. **USER ACTION**: the user's registry picks up corrected
  MCP types only on `pflow mcp sync` (their HOME — not mine; note in CURRENT-STATE). Residuals (lane-reported, NOT re-run):
  `registry/metadata_extractor.py` splits `(optional, default: utf-8)` at the comma → a fake `default` param in read/copy/move-file
  snippets (no issue); validation accepts text into a dict/list-containing union the runtime never parses (engine); a tool's own
  `timeout`/`type` param collides with built-ins; `mcp add` re-sync hint wrong on a schema error; component context lacks `(one of …)`.
  → batch these into the end-of-night verification sweep before filing.
- Provisioned `fix/issue-824-stale-viewer-bundle` @ `f2da18e2`; LAUNCHED lane **#824** (Opus, high; Makefile edit = hand-back).
  Live: 184 · lanes #822 #821m1 #824. #823 after #822.
- **MERGED #822** — PR #826 → `0ca6201d` (closes [822] only — verified via `gh`; CI green incl. Windows; 5 codex lenses + falsifier
  driving the real UI). One `calloutPlacement.ts`: first side with room in the visible canvas (TD left→right→above; LR above→below→
  left), slide while overlapping the node, last-resort push-in; `NodeCallout` re-places on pan/resize/panel/caption change; same card,
  same CSS; LR also clipped before (1200×560). I VIEWED the after shot (TD, docked, 1200): caption fully readable, placed above the
  focused step, ✕ reachable — it overlays the lower half of the preceding step (trade-off, reported to the user). Shots copied to
  `scratchpads/session-15/shots-822/`. Worktree torn down; main ff'd. Residuals: overlays (left rail, zoom controls, run banners) are
  not obstacles → a card can still land under the rail after a pan/fallback → follow-up issue AFTER #823 (shares GraphView.tsx);
  gate deep-link run callout off-screen (pre-existing); jsdom gotcha (`.react-flow__renderer` measures the canvas).
- Provisioned `fix/issue-823-frame-highlight` @ `0ca6201d`; LAUNCHED lane **#823** (Opus; reuse `hover-mark`, hand back on any new
  visual; + clear-focus guide line). Live: 184 · lanes #821m1 #824 #823.
- **MERGED Task 184** — PR #829 → `c1249b61` (closes [695, 699, 737] — verified via `gh`, all three CLOSED; task-review present (173
  lines); spec done + Completed 2026-10-12; 16/16 checks incl. `baseline-oracle` (oracle + examples capture) + both Windows + MCP
  smoke; head contained main `0ca6201d`). One `build_run_outcome` + per-channel renderers; JSON contract change (top-level
  `nodes_executed`, `checkpoint`, `paused_node_id`, `gate_request` dropped; identity on success; errors always a list); MCP text
  identity block; warnings before the error block (3 baseline cases); 28 example captures re-recorded; `capture.py` masks
  `trace_path` (shared tooling, disclosed). Orchestrator's rulings (2/5 each): `success` derived from status (= F20 A). Filed by
  the producer: **#828** (a gate inside a sub-workflow leaves its host step `completed` — executor/engine → task-shaped, the user's).
  Task-review copied to `scratchpads/session-15/task-184-review-copy.md`. Worktree torn down; main ff'd; text deltas to #821m1
  (document shape for its tests), #824, #823. Integration Points carry #801's attachment sites (all channels at `build_run_outcome`'s
  return incl. the 3 Diagnostic lists; CLI JSON + trailer; stderr loop; MCP text; NOT the text-mode stdout value / `-o` — #799
  residual 1). Candidates (producer-reported, not re-run): (a) trace-write-fault gate fallback names inapplicable causes; (b) a resumed
  saved workflow reports `workflow.action: "unsaved"` (`resume.py:161,180`) → end-of-night sweep.
- run.py serial queue now OPEN: #801 → #815 → #814 → #806 → #807 → #817 → #821 member 2. Lane slots full (#821m1 #824 #823); the build
  slot is free but the queue is lanes (cap 3) — #801 launches when the next lane merges.
- **MERGED #821 member 1** — PR #827 → `61625533` (closingIssuesReferences EMPTY — verified via `gh`; #821 OPEN with the lane's
  "member 1 shipped, member 2 remains" comment; CI green incl. Windows + `baseline-oracle`; 6 codex lenses + 2 re-reviews + falsifier ×2).
  Wider than filed: the class is any non-`Exception` BaseException except KeyboardInterrupt (`asyncio.CancelledError`, `GeneratorExit`
  crashed with a raw traceback) — caught around the worker's `exec()`, raised as `NodeError` (so `retry:` applies — falsifier pass 1
  caught the error-dict version skipping retry); `sys.exit(0)` also fails the step (ruled by the lane 2/5 — code after the exit never
  ran); registered user nodes deliberately out (engine thread). Worktree torn down; main ff'd. Residuals (lane-reported, NOT re-run):
  stale docstring `test_code_file_provenance.py:6`; an ordinary code-step failure hides captured stderr (diagnostic pipeline); Ctrl-C
  during a long body exits only after the thread finishes (~24 s); `batch.max_retries` without node `retry:` re-ran a failing item 0×
  → end-of-night sweep.
- Provisioned `fix/issue-801-value-scrub` @ `61625533`; packet (pre-written + provisioning line) verified; LAUNCHED lane **#801** (Opus,
  high; hand back before building on the secret-set home + min length). Live: lanes #824 #823 #801.
- Lane #801 HANDED BACK pre-build (124k): leak re-executed on post-184 main across all channels + a new `-v` member; Task 184's attach
  claim holds but covers 4 channels of ~30 exits; #183 prior art (rejected a taint set for `secret: true` + seams + provenance).
  Decisions 1–4 (set source A/B/C, min length 8/6, scope whole-document vs diagnostics, lane file scope) → **PARKED for the user**
  (3+/5, security design with a prior user-guided rejection in the same space; Decision 3 changes printed results). Park comment on
  #801 holds the options + state (read back). Worktree kept clean. Not counted against the cap; the run.py queue moves to #815.
- Provisioned `fix/issue-815-exit-code-table` @ `61625533`; codex evidence copied; LAUNCHED lane **#815** (Opus, high; hand back on (a) validate-only/dry-run 1→2, (b) unknown-flag 1→2, (c) table home, if not obvious). Live: lanes #824 #823 #815 · #801 PARKED on the user.
- Lane #815 HANDED BACK pre-build: EXECUTED nine exit-1 cases on main; **my issue's mechanism claim was WRONG** — Task 184's document
  does NOT know the phase (`ExecutionResult` has no phase field; `_exception_to_result` maps every phase to FAILED; the identity rule
  only orders trace settling). RULED here (2/5 each, realising the owner's phase rule): D1 A (`engine_started: bool = True`, set False
  before `engine.run`); D2 `validate_only_target` moved before the engine (`--only <unknown>` → 2), missing snapshot stays 1;
  (a) validate-only/dry-run → 2, (b) unknown-flag → 2, (c) one table in `run_outcome.py` + `EXIT_REJECTED`; resume refusals → 2,
  declined confirm → 1. Ownership + `runner.py`, `result.py`, `tests/test_execution/`. Fail-closed: no exit change for an engine-
  started run except `--only <unknown>`; every `ExecutionResult(` site classified. Lane RESUMED.
  RECURRENCE: a pre-execution mechanism in an issue body I wrote was refuted by the lane's reading (#815) — the promoted filing-bar
  rule held (marked HYPOTHESIS in the issue); the error was the confidence of the "184 already distinguishes" sentence.
- **MERGED #824** — PR #830 → `44709095` (closes [824] only — verified via `gh`; 15/15 incl. both Windows; 5 codex lenses + falsifier, 7/7
  promises held). Option (a): `bundle_warning()` warns once on a NEW `pflow ui` start in a source checkout (package at
  `<repo>/src/pflow/ui`) when the bundle is missing or older than any BUILD input under `web/` (tests/`*.md`/node_modules excluded — the
  issue's "newest file in web/src" rule would have fired on a test edit); prints the newest file + `make -C <repo> ui-build`; silent on
  a reused server; <1 ms. Worktree torn down; main ff'd. Residuals: a reused server may run pre-pull Python (needs `/api/health` code
  version); cmd.exe quoting untested.
- run.py + runner.py held by #815 → no queue item can start. LAUNCHED the residual verification sweep (Opus agent: R1–R10 from lanes #811 #804 #821 #755 #812 + Task 184's (a)(b); execute, dedup, class-group, draft) → `scratchpads/session-15/residuals/summary.md`. Live: lanes #823 #815 · #801 PARKED · sweep agent.
- **MERGED #823** — PR #831 → `2fb391d9` (closes [823] only — verified via `gh`; 16/16; 4 codex lenses + falsifier + 2-lens re-review;
  one CI flake "chip-click camera follow" green on re-run). The latest `frame` target is kept by workflow ref and ringed through the
  existing hover-mark channel (falsifier: `box-shadow` identical to the focus ring); cleared by the next agent focus / clear-focus /
  a deliberate user point (`reportUserPoint`), KEPT across live-reload and panel close (falsifier caught both). No new visual / message /
  CSS. The issue's guide line (a) was WRONG — `clear-focus` between chained `--say` lines would cut each clip (clear stops audio +
  resets pacing; read, audio not executed) → guide says "at a break"; (b) not built. I VIEWED a shot (ring on the framed step + card).
  Shots copied to `scratchpads/session-15/shots-823/`. Worktree torn down; main ff'd. Residuals: beautiful-density connection frame
  hides its line; overlapping cards at small viewports (#822 placement); "one card at a time" = a `say` persistence design question;
  the #822 rail-as-obstacle follow-up is now unblocked (verify before filing).
- 13 merges tonight → LAUNCHED the standing dogfood pass (Opus, fresh eyes, isolated HOME, `dogfood-s15-` prefix, ≤10 cheap LLM calls; report → `scratchpads/session-15/dogfood/report.md`). Then a verification agent re-executes + dedups before serial filing. Live: lane #815 · sweep agent · dogfood agent · #801 PARKED.
- Residual sweep DONE (`scratchpads/session-15/residuals/summary.md`): R1–R10 re-executed — 9 reproduce (R8b documented behaviour,
  only the silent validation is the gap), R9 REFUTED (the exit-0 stderr warning keeps head+tail since #808/184). Drafts read in full by
  me; one astra pass over the eight mechanisms (`verify/out-residuals.md`) corrected cites in 7 of 8 (biggest: settings-env inheritance
  is SHELL-wide, MCP gets an allowlist, agents filter their keys; the code-step formatter ignores stderr for ordinary exceptions; MCP
  derives `workflow.action` separately; explicit `mcp sync` never prints the hint) — folded before filing. FILED serially (read back):
  **#832** MCP union params validate then reach the server as text · **#833** settings env exported to every shell step vs the help's
  "not injected implicitly" (OWNER DECISION A stop exporting / B fix the doc — premise for A not established) · **#834** a code step's
  ordinary exception drops its stdout/stderr everywhere · **#835** MCP tool params named like step keys are unreachable · **#836** gate
  remedy after a trace write fault lists four inapplicable causes · **#837** resuming a saved workflow by token reports `unsaved` ·
  **#838** `mcp add` re-sync hint after a schema failure · **#839** `batch.max_retries` inert on handled-failure nodes, no advisory (low).
  Comments: #277 (wider: validation affected; `(required)` on every platform param; paren-aware splitter exists), #76 (MCP required now
  known, validation missing; after #835), #821 (Ctrl-C waits for the body's thread — RULED: folded into member 2), #192 (core ask
  shipped; `--version` after the workflow is the remaining member — left open).
- Dogfood DONE (agent's report file write was blocked by the harness → saved verbatim by me to `scratchpads/session-15/dogfood/report.md`):
  0 BLOCKER, 9 MISLEAD, 8 GAP, 17 PAPERCUT; this week's changes HELD (run outcome, input usage, head+tail, sys.exit, `__file__`, MCP types,
  `--version`, stale-bundle warning); caption placement/frame not tested. Top: `--validate-only` passes required/type/enum errors (M1);
  a run flag before a subcommand makes it a workflow name (M2); save doesn't bundle a code file's siblings read via `__file__` (M3);
  template error names the producer step (M4); `probe` exits 0 on failure (M5); HTTP error bodies dropped (G1); JSON embeds full stderr
  twice — 2.6 MB (G3). INCIDENT: one accidental paid LLM call — the calling shell exports GEMINI/OPENAI keys and an isolated HOME does
  not isolate env (`pflow find` used one) → RECURRENCE candidate: dogfood/verification briefs must `env -u` provider keys.
  Verification agent LAUNCHED (re-execute, dedup, class drafts, zero LLM calls) → `dogfood/verified.md`.
- **MERGED #815** — PR #840 → `52e91f6c` (closes [815] only — verified via `gh`; 16/16; codex fan-out + falsifier). `ExecutionResult.engine_started`
  (set on the one line between `_compile_for_run` — which now ends with the moved `--only` target check — and `_execute`); `EXIT_REJECTED = 2`
  beside `EXIT_CODES` in `run_outcome.py`; outer handlers of run + resume, validate-only, dry-run, removed commands use it. Fail-closed held
  (a temporary probe over the full suite recorded 0 post-engine exit-2s; positive control fired). 14 baseline + 2 example cases re-recorded
  (exit code only). Fixed in review: `--only` refused pre-engine left an unmarked trace (UI/analyze-cache autoload) — runner records the
  target at trace creation; Ctrl-D at the resume prompt back to 1. REAL SURFACE checked by me: a missing workflow file → exit 2.
  Teardown REFUSED by 4 PIDs (91026/91042 zsh probe shells whose argv names the #815 worktree, 91043 `head`, 91044 `ugrep` hung 18 min on
  stdin — the falsifier's abandoned `ls -t | grep` probe) → killed exactly those (argv carries the worktree path), then `rm` OK.
  Residuals: stale "exit 1" comments `plan.py:2282`, `exceptions.py:1587`; `workflow_executor.py:155` comment; validate-only passes a
  sub-workflow cycle; pre-engine refusals still save an empty failed trace; flags after the workflow accepted (`… key=v --print`).
- Dogfood verification DONE (`dogfood/verified.md`): 24 verified (7 partly in open issues), 5 duplicates (#807 #734 Task 117 #806 #689),
  2 declined by ruling (M9 Task 184's count rule; G7 `-p` one output), 2 partial, 1 refuted (P12 shipped by #818 on purpose). Drafts read
  in full by me; one astra pass (`verify/out-dogfood.md`) corrected all 12 (binding: the HTTP-body excerpt must be redacted before it is
  made a string — `core/CLAUDE.md:232-237`; the resume-child closing options conflict with `execution/CLAUDE.md:68-78` /
  `runtime/CLAUDE.md:76-84` or fail for batch children → hand-back at pick-up; find's empty library already skips the LLM; the gate
  header's node type is the class name) — appended to each body as "Cross-model check". FILED serially (read back): **#841** HTTP error
  body dropped · **#842** template error names the producer · **#843** JSON failure doc unbounded (2.6 MB) · **#844** resume confirms a
  never-started sub-workflow step · **#845** save doesn't bundle a code file's siblings · **#846** probe exits 0 on failure · **#847**
  `--help` "No description" + untyped outputs · **#848** enum fields reject templates with a bare error · **#849** pause preview unlabelled
  · **#850** run header before validation · **#851** find formatter text · **#852** help docstring formatting. Comments (count read back):
  #76 #689 #693 #702 #738 #740 #803 #805 #806 #807.
- Provisioned + LAUNCHED lanes **#814** (stdin rule; run.py stdin block + shell_integration; subsumes #666) and **#817** (reserved-name rule; validation_utils + runner setdefault) @ `52e91f6c` (Opus, high; files disjoint; both exit 2 on rejection per #815). Live: #814 #817 · #801 PARKED. After these two land: close the session (context is long; the remaining run.py queue — #806, #807, #821 member 2 — goes to the next session's CURRENT-STATE).
- Lane #817 HANDED BACK pre-build: three boundaries never run the name rule (resume overrides, UI preflight, analyze-cache — EXECUTED);
  the issue's one-rule fix would make UI `POST /api/run` fail SILENTLY (spawned run rejects pre-trace, streams to DEVNULL); author-side
  members (batch alias `as: _pflow_workflow_file` → `from-b` EXECUTED; dict-IR node id crash; run-only declared check). RULED here
  (class-closing, settled by the standing instruction): **B** — check once at `WorkflowRunner._prepare_workflow` + `check_supplied_inputs`,
  ownership + runner.py; `run.py` untouched (#814 live) — its redundant check is a queued follow-up; fail-closed: internal injections still
  run (nested, batch, resume, --only), the UI path rejects visibly (executed); exit 2. Lane files the author-side members as one new issue.
- Lane #817 STOPPED on the fail-closed tripwire (the `check_supplied_inputs` check rejected the runner's own `_pflow_workflow_file` on the dry-run nudge path — the nudge silently vanished; 2 tests caught it). EXECUTED so far: CLI run/validate-only → 2, resume → 2, real UI POST /api/run → HTTP 400 with the shared message (item 2 removed). RULED option 1: the one check stays in `_prepare_workflow`; analyze-cache + `runner.validate` (non-executing) join the author-side issue. Lane RESUMED.
- Lane #814: PR #853 opened green (both Windows shards); stopped pre-merge for two out-of-ownership doc edits (`core/CLAUDE.md:187` pipe-only claim; `architecture/features/shell-pipes.md` promising the deleted refusal) in a separate commit. RULED A (living-docs rule; no live lane on those files); closing #666 kept only if the Windows file-redirect test verifiably ran, else 'Refs #666'. EXECUTED by the lane: open/empty/data/file stdin into a no-input workflow ~0.2 s (was 4 s wait + refusal); `< file` fills a declared input; 6/7 new real-descriptor tests fail with the fix reverted (5 hang). Lane RESUMED to merge.
- **MERGED #814 (+#666)** — PR #853 → `f7a69d04` (closes [666, 814] — verified via `gh`, both CLOSED; 16 pass + Mintlify skip; 5 codex lenses +
  falsifier 7/7). stdin read only after resolution, only for a declared `stdin: true` input not supplied on the CLI; the refusal deleted;
  regular-file redirects read on Unix + Windows (the lane PROVED the Windows file-redirect test ran by shard test-count arithmetic: +6
  passed, skips unchanged). Docs commit kept (ruled A). Worktree torn down; main ff'd. Residuals: Unix binary stdin passed as mangled text
  (#589); dead `stdin_data` param in `execute_json_workflow` (resume.py); unused `detect_stdin()`.
- **MERGED #817** — PR #854 → `a7ba08de` (closes [817] only — verified via `gh`; main push CI green on `a7ba08de`; 7 codex lenses + falsifier).
  One `_parameter_name_problem` (reserves `_pflow_`); one `check_parameter_names` in `WorkflowRunner._prepare_workflow` before the runner's
  own key (covers CLI run, resume, MCP, UI preflight); `setdefault` → assignment. EXECUTED: CLI run + resume → 2; real `pflow ui` POST → HTTP 400,
  nothing spawned. The merge RACED #814 (main moved between the lane's fetch and its click) → merged-result gate ran AFTER the merge: green
  (make test 11794, main CI success) — RECURRENCE s08 entry hits n=2. Filed by the lane: **#855** (batch `as: _pflow_…`, dict-IR node ids,
  run-only declared check, analyze-cache, `runner.validate`). Worktree torn down; main ff'd. Residuals: `run.py:816-830` redundant check +
  misleading hint (queued — #814 has merged); probe exits 1 for every wrong call; stale "via setdefault" comments `execution_service.py:138,245`;
  `compile_validation.py:206` output-name hint.
- DRAINED: no live agents, 0 open PRs; only `fix/issue-801-value-scrub` (parked on the user, clean, nothing built). → close ritual.

## Braindump

_Tacit residue only — ships, rulings and parked work live above, in CURRENT-STATE, the PR bodies and the issues._

**The user this session — their words, and what they did with them**

- They raised the MCP question unprompted, while declining a planner I proposed: *"right now using the cli works good and we've seen
  no indication users would prefer an mcp"*. The CLI is the product's centre of gravity in their head; MCP-server work is held, not
  scheduled. Do not re-propose Task 152 without new evidence (a user asking for MCP, or MCP usage appearing in a consumer report).
- They brought two external reports from projects that dogfood pflow and want them evaluated, never adopted wholesale. Their
  instruction for both: *"never mention any specifics like loukult from the projekt"*. Write "a consumer project" / "a
  demo-production studio" everywhere durable. The second report lives at `~/projects/video-generation/projects/pflow-teaser/
  pflow-findings.md` (append-only); they want the NEXT orchestrator to read both reports itself, not inherit my triage.
- *"make sure there are no assumptions and amibiguity before we file, prefer using pflow astra searchers to verify"*. The loop that
  satisfied it: execute (an Opus agent with an isolated HOME), then one astra pass over the drafts' MECHANISM sections, then fold the
  corrections in, then file serially with read-back. The astra pass corrected something in nearly every batch (7 of 8, then 12 of 12),
  so skipping it is not a cost saving.
- A routing correction arrived as a one-liner: *"falbe is not needed when its just fixes"*. I had asked whether F1 needed Fable; they
  read "UI" as "taste" only when something is being designed. Now on DECISIONS #24.
- *"yes I think so"* to building F2 + F6 rested on F6's premise ("no scripted dismiss"), which the mechanism pass refuted
  (`clear-focus` exists). I reported it back and did not build. An approval resting on a false premise is not an approval of the
  refuted part.
- *"we are utilizing pflow astra for reviews etc right?"*: they audit the dispatch channel. I answered from PR bodies, not handbacks:
  every lane's reading lenses ran on codex by the workflow default, and the falsifier ran natively.

**Overturned or corrected, owned**

- #815's issue said Task 184's document "already distinguishes a pre-engine failure". It does not; I wrote that from 184's spec
  sentence about identity, not from the result type. The lane caught it by reading `ExecutionResult`. Third time this session a lane
  refuted my issue text (#811: render vs sync; #823: the guide line I proposed would cut audio). The promoted "a pre-execution
  mechanism is a HYPOTHESIS" rule held: every one was caught before code.
- I accepted #813's `__name__ = "__main__"` call (2/5) without asking what a main block DOES. The falsifier showed it would silently end
  runs. When accepting a producer's small call, ask "what existing code takes a different path because of this?"
- I told the user the slow deny was real in the first-pass triage. The trace said 1.8 s, and an execution said 0.9–1.4 s. Read the
  cited artifact before relaying a report's number.

**Mechanisms that worked — reuse them**

- **Residual sweep:** one Opus agent re-executes every lane-reported residual (R1–R10), dedups, groups by class and drafts. Then astra
  over the drafts, then file. 10 residuals became 8 issues + 4 comments + 1 refuted, in about an hour.
- **Pre-writing the next lane's packet while slots are full** (`scratchpads/session-15/packets/`). Launch became one command when #821
  merged.
- **Partial lanes with an explicit "must not close" rule** (#821 member 1): check `closingIssuesReferences` is empty before merging,
  then post a "member 1 shipped" comment. Worked cleanly.
- **Fail-closed predicates in rulings** stopped #817 twice at real seams (the dry-run nudge silently vanishing; the UI silent failure).

**Dead ends — don't repeat**

- A subagent's report-file write can be blocked by the harness ("Subagents should return findings as text"). The dogfood agent returned
  its report inline and I saved it. Briefs should say "write the file; if blocked, return it inline".
- `( sleep N ) | pflow …` timed with `date` measures the whole pipeline. Time the right-hand side only (`… | ( S=…; pflow …; echo … )`).
- Background `uv run pflow …run-searcher… &` inside a `run_in_background` Bash returns immediately. Wait on a `done.txt` marker with an
  until-loop, not on the Bash notification.

**Seams noticed, not yet forced**

- `cli/commands/run.py` is the bottleneck file. #801, #806, #807, #821 member 2, #847, #850 and the redundant name check all touch it.
  A run.py-touching lane is effectively serial. Consider one "run.py presentation" lane bundling #806 + #850 + the redundant check.
- #801 (value scrub), #841 (HTTP body excerpt must be redacted first) and #843 (JSON cap) all decide what raw data a printed failure
  carries. Rule #801 first; the other two then follow its carrier.
- #833 (settings env exported to shell steps) is a credential-exposure question, not a doc bug. If the user picks A, #801's
  settings-env members simplify.
- The examples capture + Task-159 oracle (both required) now re-record on almost every user-visible lane (59 cases in #804, 14 in #815).
  Fine while they catch drift, but watch whether re-records become reflexive.

**Local-only artifacts**

- `scratchpads/session-15/` (main checkout, gitignored): `consumer-report-disposition.md` (both reports' maps); `verify/` (astra prompts +
  outputs for every filing); `residuals/` and `dogfood/` (drafts + bodies as filed); `issues/` (bodies as filed); `*-verify.md` (execution
  evidence); `shots-822/`, `shots-823/` (UI before/after); `task-184-review-copy.md`; `stray-root-probes/` (15 probe files an agent left
  at the repo root — disposable); `packets/packet-801.md`.
- Worktree `../pflow-worktrees/fix-issue-801-value-scrub` (local branch, clean, nothing built). Its gitignored `scratchpads/801/` holds
  the lane's probe fixtures.

**Markers**

- ASKED-NOT-ANSWERED: #801 Decisions 1–4; F4 file-or-not; the uncommitted deep-review skill sentence (needs the word); the RECURRENCE
  PROPOSED entries (listed in the closing message).
- UNCLEAR: whether the user re-synced MCP servers after #811 (their registry still has `str` for model/optional params until they do).
- NEEDS VERIFICATION: #811's lane says "no capture includes MCP param lists". True tonight (CI green), but a future MCP example would make
  the examples capture sensitive to the type change.
