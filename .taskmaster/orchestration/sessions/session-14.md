# session-14 — 2026-10-11

## [2026-10-11 10:45] main orchestrator — boot + reality diff

- Booted per the role prompt (Fable, user `/model` saved default). Predecessor `pflow-main-orch-session-13` live → ONE
  bounded question; ANSWERED: nothing beyond its session file — no post-close ruling (#769, #767, 181 §4d, chrome-devtools,
  #692, RECURRENCE promotions all still open), main clean at `752b7ebc`, no live agents or processes, only the parked 120
  worktree. Boot fork launched → `scratchpads/session-14/boot-fork-report.md` (s08/s09 braindumps, 120 spec, 181 review,
  issues #769 #768 #767 #742 #743).
- Reality vs CURRENT-STATE: NO drift — main == origin/main == `752b7ebc`; push CI green on `f68680ba` and `752b7ebc`
  (run 38102864555) → folded (the one "verify at boot" line). No open PRs; 165 open issues, newest #769; worktree
  `feat-task-120-declared-input-types` @ `c2036d23` clean, 12 commits behind main; `./scripts/tasks --check` clean; load ~5.
- User focus: *"lets continue where the last session left of, carefully deciding what is the most high value/leverage thing
  to work on. the last session is available through sendmessage if you have any critical questions not answered by docs"*
- MEASURED for the 120 packet: `git diff --name-only 285e7b3f..origin/main` (merge-base) = see count in (saved to
  `scratchpads/session-14/main-delta-since-120-base.txt`); a searcher is extracting the 120 plan's per-phase file list
  (mechanical, for collision analysis against lane fills — I do not read the plan).

## [2026-10-11 10:55] [RULING] the user approved the launch set — Task 120 build + lanes #680 #756 #741 LAUNCHED

- Read as: launch the recommended set. The six "decisions only you can make" (#769, #767, 181 §4d, chrome-devtools, #692,
  RECURRENCE promotions) are NOT ruled by this word — still pending.
- Boot fork DONE (`scratchpads/session-14/boot-fork-report.md`, 196k): spec on MAIN is behind the BRANCH copy (expected — branch
  owns it); #769 not a 120 blocker (byte rule in the binding code, a small lane after); CLAIM for 120's packet: the spec assumes
  a sub-workflow host's prep error routes to `on-error` while #768 shows shell/code prep errors do not; #680 drift count 12
  (issue) vs 13 (CURRENT-STATE) — the lane measures.
- Commit gate (DECISIONS #5): nothing producer-facing uncommitted on main → lanes branch from verified `origin/main` `752b7ebc`.
  Provisioned sequentially: `fix/issue-680-baseline-rerecord`, `fix/issue-756-mcp-sync-empty-schema`,
  `fix/issue-741-changelog-pr-links` (all @ `752b7ebc`). Collision analysis: 120's plan file list (searcher-extracted,
  mechanical) ∩ lane ownership = ∅; held for after 120: #755 #722 #748 #749 (shared files); #716 queued (tiny, disjoint).
- Packets written into each worktree's `scratchpads/session-14/` (verified by `/bin/ls`). 120's packet carries the MEASURED
  main-only delta (`git diff --name-only 285e7b3f..origin/main`, 165 paths) and the 29 of them the plan also names.
- LAUNCHED (Claude, all `model: opus`, `effort: high`): Task 120 task-orchestrator (implement-from-plan; first act merges
  origin/main; P0 re-verifies 181's seven shapes; PF screenshot checkpoint → user) · lane #680 (fail-closed: every re-record
  traces to a merged PR, else file + hand back) · lane #756 (hand-back BEFORE building: shapes (a)/(b)/(c)) · lane #741.
  Load: 1 build + 3 lanes = the cap.
- Lane #756 HANDED BACK pre-build (90k, 5 min): issue PREMISE REFUTED — servers send schemas; the Oct-7 incident was PyPI
  pflow 0.15.1 (no `mcp<2` cap) + mcp 2.3.0 (`input_schema`), so `hasattr(tool,"inputSchema")` failed and discovery saved
  the empty fallback for every tool. RE-MEASURED by me read-only: heptabase 20/20, notebooklm 53/53, resend 106/106, hokuz 2/2,
  playwright 31/62 still carry the fallback schema; uv cache env `PvOsolhyyZoCYhgNOlEhH` holds `pflow_cli-0.15.1` + `mcp-2.3.0`.
  ESCALATED (3/5, overlaps Task 178): (d) delete the silent fallback, read the fields directly, fail loud [rec] vs (e) close as
  superseded by 178. User actions: re-sync the five servers (their HOME); yank ≤0.15.1 on PyPI (public). Lane stopped, clean.
- **MERGED #680** — PR #773 → `5a93929d` (closes [680] only — verified via `gh`; 14/14 checks; push CI in progress). Oracle
  87/87 (was 73 pass / 14 drift on `752b7ebc` — MEASURED by the lane, not 12 or 13). 10 of 14 drifts were the FIXTURES going
  invalid (#649 `source`, #704 output-source checks) → fixtures fixed, recordings kept; 3 re-recorded (#759/#765/#772 guide
  text, #771 message, 02/05 extra log line); the #767 `SyntaxWarning` left alone (fresh-env only). No regressions filed.
  Worktree torn down; main ff'd. 120 build notified (merge main at its next phase boundary). Lane's decision for the user:
  nothing runs `verify.sh` automatically (not in `.github/` or the Makefile) → a CI gate? Residuals: baseline README says 79
  cases (87 now); denied cleanup `scratchpad/bisect680` (session scratch) — disposable.
- LAUNCHED lane **#716** `fix/issue-716-cookie-header-masking` @ `5a93929d` (Opus, high; the approved set's queued fill — ownership
  `core/security_utils.py` + tests; hand back if the fix wants a mechanism beyond the word list). Live: 120 build · lanes #741
  #716 · #756 stopped on the user's ruling.
- **MERGED #741** — PR #774 → `90dc9b01` (closes [741] only — verified via `gh`; 14/14 incl. both Windows jobs; push CI on
  `5a93929d` green, on `90dc9b01` in progress). Rule tightened beyond the issue: the PR is the `Merge pull request #N` number or
  the squash subject's TRAILING `(#N)`, kept only if N is a merged PR (`gh api repos/{repo}/issues/N` for numbers outside the
  200 window; any other lookup failure STOPS the step). Squash commits now carry PR title/body/summary; summary line fixed; UTF-8
  decoding. Tests `tests/test_runtime/test_changelog_workflow.py` (real step code, throwaway git repo, faked `gh`, no LLM).
  Release-skill interface unchanged. Worktree torn down; main ff'd. Residuals (lane-reported, NOT re-run): full PR bodies now
  flow into the render step (~336K chars for v0.16.0 — watch release cost; one-line follow-up = send the summary); `generate-
  changelog-simple` takes the first `#N` (loses the PR link, never wrong); `gh repo view` failures show only an exit code.
  Live: 120 build · lane #716 · #756 stopped on the user's ruling.
- **MERGED #716** — PR #775 → `3a7643c8` (closes [716] only — verified via `gh`; 15 pass + Mintlify skip, both Windows jobs).
  `cookie`/`cookies` join the sensitive-name list (one rule, every reader); docs word lists refreshed (settings list also gained
  `credential(s)`/`authorization`/`auth`); real-surface verified by the lane (report + web run panel show `<REDACTED>`, trace keeps
  raw). Worktree torn down; main ff'd. Residual 1 (3/5, lane-reported, pre-existing on main): `--output-format json` http error
  carries unmasked copies of `raw_response`/`response_headers` under `errors[].context` + `diagnostics[].context`
  (`error_formatter.py:60-68` masks top-level keys only — I READ the lines; re-execution delegated before filing). Residuals 2–3:
  hand-listed "19 sensitive names" in `test_executor_service.py:167` and `review-agent-ux.md:37` (now 21). Live: 120 build
  (`39cb8f96`) · #756 stopped.
- FILED **#776** (`--output-format json` failure document prints raw HTTP body/headers under `errors[].context` +
  `diagnostics[].context`; top-level copies masked) — RE-EXECUTED on `3a7643c8` by an Opus agent (isolated HOME; 2+2 raw hits in
  the JSON, 0 in text / report; evidence + mechanism by function in `scratchpads/session-14/leak-json-error-context.md`), draft
  read in full by me, filed with `--body-file`, read back. Closing mechanism: one sanitizing pass over the whole failure
  document. Sibling hygiene in the body: hand-listed "19 sensitive names" in `test_executor_service.py:167` + `review-agent-ux.md:37`.
  Lane candidate — DISJOINT from 120? `error_formatter.py` and `cli/error_output.py` are NOT in 120's plan list; `core/diagnostic.py`
  neither → parallel-safe, but security-sensitive ⇒ full lens floor. Not launched yet (user's call on the fill order).
- Task 120 build HANDED BACK at the PF user checkpoint (243k, 3.5 h; head `7f174555`, not pushed): all phases built; two mid-task
  reviews ran; `make check` green, 11439 tests; baseline 86/87 — the 1 drift is MAIN's (#716 added `COOKIE` to the guide masking
  list; `04-guide-auto-detect` not re-recorded — 120's PF edits the guide so its own re-record of that case covers it; told
  the orchestrator). Checkpoint page `scratchpads/task-120/checkpoint-pf.md` + `pf/evidence.md` + 5 shots (worktree); I VIEWED
  all 5 shots myself and copied the set to the session scratchpad `cp120/` for the Artifact page. Decisions D1–D5 → user.
  Closing keywords: my packet said "exactly #686 #687" — WRONG, the branch spec line 314 says "#188 (closed by the per-item
  child boundary)"; RULED here (2/5, spec-settled): #188 closes too. Proposed CONTEXT.md term "Declared type" → mine at merge.
  Proposed screenshot-skill issue (form fill/submit workflow, `scroll_to`, locale `3,0`) → fold into #762 at merge.

## [2026-10-11 14:35] [RULING] *"this all looks good, go ahead with recommendations, but note that we should always strive to close bug classes rather than bugs if that makes sense. And if anything is unclear we should resolve that ambiguity first before comitting, and we should resolve all assumptions."* + the run-form checkbox sits centred under its label (user screenshot)

- Read as: Task 120 D1 B · D2 accept · D3 accept · D4 (a) + follow-up issue · D5 accepted; #756 → (d); #767 → fix at the source if a
  fixed anyio exists, else a narrow filter; the lens-message proposals (#776 reshaped lane, two searchers on the #695/#699/#737
  builders and the #700/#739 remedy sites) treated as covered by "recommendations" — stated to the user so they can stop it.
  Two standing instructions, quoted verbatim into every packet from here: close the CLASS; resolve ambiguity + assumptions
  before committing.
- Checkbox: the boolean control in the run form renders centred in its row (user's screenshot, shot 01/03 confirm). Handed to
  the 120 orchestrator: if the control lives in the files PF already touches (`web/src/utils/controlForType.ts`, `RunForm.tsx`),
  fix it in PF (left-align with the label row, screenshot-verified); if it is outside its files, hand back with `git blame`.
- Lane #756 RESUMED with (d) + the two user instructions verbatim. Task 120 orchestrator RESUMED with D1–D5 rulings, #188 closes,
  the checkbox job, the instructions verbatim. Provisioned + LAUNCHED lanes **#767** (`fix/issue-767-third-party-syntaxwarning`,
  hand-back before building: source-first vs filter + the class rule) and **#776** (`fix/issue-776-json-error-context-leak`,
  hand-back before building: the proposed JSON document shape — one representation, sanitized once) @ `3a7643c8`. Load: 1 build +
  3 lanes = cap. Two native searchers launched (run-outcome document builders behind #695/#699/#737/#748; hand-authored remedy
  syntax sites behind #700/#739) — user mid-turn: *"prefer using pflow astra searchers when relevant"* → the searcher OFFLOAD
  is the default from here; both briefs ALSO sent through `workflows/search/run-searcher.pflow.md` (backgrounded, outputs
  `scratchpads/session-14/verify/{builders,remedies}.out`) as the cross-model pair.
- Native searcher (builders) DONE (183k): CLAIM — 13 builders (+2 exception fallbacks) across 30 live outcome×channel cells; only
  success has a shared builder (`success_formatter.format_execution_success`) and callers bolt identity on per side
  (`workflow_output.py:908` passes `trace_path=None`; MCP patches `execution_id` at `execution_service.py:88-89`); lineage lives
  only inside the success builder; `nodes_executed` has FOUR meanings. #695 + #737 + half of #699 = one missing presentation
  seam (ExecutionResult → document for every status); the other half of #699 = `runner.py:907-913` never attaches metrics on
  the exception path; #748 = probe surface, not a run document. Awaiting the astra pair (`verify/builders.out`) before ruling
  lane vs task.
- Native searcher (remedies) DONE (105k): CLAIM — 8 WRONG sites / 11 literals (`python_code.py:446,851-854,974,996`,
  `save_service.py:458`, `copy_file.py:94`, `move_file.py:128`, `cli/commands/run.py:981-990`) + 3 MCP spellings + ~15
  near-misses (no `- ` marker / IR wording); NO shared renderer for "set param X" (only `written_reference()` for `${…}` and
  `cache_ttl_syntax_hint()` for one param); #700's HTTP half already fixed by #707; the save collision's two remedies come from
  `save_service.py:458` (service) + `cli/commands/save.py:56` (CLI) each adding its own; MCP rewrites at
  `execution_service.py:615-618`; no test pins any wrong literal verbatim; guide `code.md:85,89` repeats the inputs-dict wording.
  COLLIDES with Task 120 (`run.py`, `execution_service.py`, `guide/nodes/code.md`) → after 120. Awaiting the astra pair.
- [STANDING] User: *"keep a lookout for obvious refactors that needs to be made in regards to consolidating seams if that makes
  sense"* — read as: name consolidation candidates (deletion test as the bar) instead of filing instance fixes. Candidates open:
  (1) one run-outcome document builder (#695/#737/½#699); (2) remedies never hand-author syntax (#700/#739); (3) 120 must leave
  ONE leaf-policy carrier, not `embedded` + a second (check at its task-review); (4) #756's helper as the shape Task 178's other
  seven `hasattr` sites consolidate onto. Offered a scoped `improve-codebase-architecture` pass after 120 merges.
- Astra pairs DONE (`verify/builders.out` 28 KB, `verify/remedies.out` 34 KB; read in full by me) — CONVERGE with the native
  pass, zero contradictions. Builders: 13 builder functions / 15 format-specific paths across 25 live cells; only success shares
  a builder (`format_execution_success`, takes loose args not an `ExecutionResult`); CLI passes `trace_path=None` while MCP
  enriches `execution_id`; lineage copied only in the success builder; `nodes_executed` = metrics count vs completed-steps
  count in BOTH formatters; #699's metrics loss is in `runner.py:907` (`_exception_to_result` omits `metrics=`) BEFORE any
  formatter; #748 is the `registry_run` probe adapter (`execution_service.py:754`), not a run document; MCP pause drops
  diagnostics the CLI pause keeps. Remedies: 9 wrong-dialect sites (astra) vs 8 (native; astra counts `run.py:982` and `:990`
  separately) + 23 fragment/malformed standalone examples; `binding_phrase()` (`data_flow.py:1196-1210`) ALREADY renders
  `- param:` bullets for env/inputs — the precedent helper; `validator.py:1888` emits a literal `\n`; `markdown_parser.py:192`
  TTL hint includes a comment the parser rejects. Both astra runs: `gh` cannot reach api.github.com from the codex sandbox
  (n=2 with s10's "comments empty" — offload briefs must paste issue bodies inline).
- Lane #767 HANDED BACK pre-build (79k, 12 min): anyio FIXED it in 4.10.0 (2025-08-04; latest 4.15.1); only `uv.lock` (4.9.0) still
  shows it — fresh user installs get 4.15.1 and print nothing; trigger is the first registry scan (`claude_agent_sdk → mcp →
  anyio`), NOT `import pflow.cli` (my packet's probe was wrong — #752 made the import lazy); a site-packages-scoped filter does
  not work on 3.14.0 (warning attributed to `importlib._bootstrap`); pip has one module-scoped filter, poetry none. Only ONE
  third-party compile warning exists across 5,482 files. RULED here (settled by the user's source-first ruling + "close classes"):
  (a+) lock bump + a root test compiling every runtime dependency and failing on any compile-time warning + the CLAUDE.md rule
  line; test at `tests/test_third_party_compile_warnings.py` (ownership widened); `anyio>=4.5` pin untouched (178). Lane RESUMED.
  Host load average 86 during its run (1 build + 3 lanes + 2 offloads) → RECURRENCE host-load entry n=3 at close.

## [2026-10-11 15:00] [GRANT] the user approved the seven-step plan

- Read as: the ordered plan of my previous message — after 120 merges: (1) remedy-text lane #700+#739 · (2) baseline CI-gate
  issue once #767 confirms a clean fresh runner · (3) run-outcome document TASK (spec mine, user rules, planner) · (4) held fills
  #755 #722 #749 · then (5) dogfood pass · (6) release · (7) Task 178 planner (client-era Q1 is the user's); the scoped
  architecture pass between 5 and 7. Standing boundaries hold (release = user's word at the time; 3+/5 forks park).
- Now: drafting the run-outcome document spec (no slot needed; collides with nothing) from the two converged searcher reports.
- **MERGED #756** — PR #779 → `2a548519` (closes [756] only — verified via `gh`; 14/14 incl. Windows; 6 codex lenses + falsifier).
  One `_tool_definition` helper replaces both transports' fallback; schemas stored as sent (`{}` included); an SDK-shape
  mismatch fails discovery and keeps prior tools; mypy on SDK 2.3.0 now flags the site; real-stdio-server tests
  (`tests/test_mcp/test_discovery_schemas.py`); Task 178 spec amended (discovery no longer silent; SDK 2.3.0 rejects a whole
  tool list if one schema lacks `type`); incident evidence commented on #756. Worktree torn down; main ff'd. Residuals (PR
  body, NOT re-run): discovery reads only the first tool page (no `nextCursor`); `sync --all` partial failure exits 0 (pinned,
  pre-existing); #685 bare `Error: Error` header. User-side: re-sync the five servers; PyPI yank (≤0.15.1) still open.
- Task 184 spec DRAFTED on main (`.taskmaster/tasks/task_184/task-184.md`, uncommitted, producer-facing): "One Run Outcome" —
  D1–D4 PROPOSED for the user; proposed CONTEXT.md noun "Run outcome"; coordinate-with Task 120; #748 out. `--check` next.
- Lane #776 HANDED BACK pre-build (145k, 17 min): the named-key sanitizer CRASHES on a text 401 body (AttributeError misreported
  as the failure, identity dropped); secrets also reach `context.unresolved_references[].failure.*` via on-error template
  diagnostics (24 raw paths) and the SUCCESS/degraded document's `warnings[]` under permissive mode; `to_display_dict` makes
  up to 3 copies. Options: shape S1 (nested `errors[]` like `diagnostics[]`, flattened copies gone) / S0; masking M2 (one
  redacting serializer on `Diagnostic`, success formatter added to ownership) / M1. ESCALATED (3/5) → user; rec S1+M2 (the
  Task 184 direction). Decision-independent hygiene already done (SENSITIVE_KEYS iteration; review-agent-ux count dropped).
- [RULING] *"you can resync the mcp servers"* → registry backed up to the session scratchpad (`registry.before-resync.json`),
  then `pflow mcp sync <name>` ×5 from main `2a548519` (one name per call — `sync` takes a single NAME); all five re-registered.

## [2026-10-11 15:40] [RULING] the user accepted the standing recommendations

- Applied: #776 → S1 + M2, ownership + `success_formatter.py` (lane RESUMED; follow-ups: run.py documents after 120, trace
  `to_display_dict` retirement = task). Task 184 D1–D4 → DECIDED in the spec. CONTEXT.md gains **Run outcome** (before
  Snapshot). #769 → strict UTF-8 on every binding channel — ruling posted on the issue (read back). Ratified for close:
  181 §4d wording; #692 stays open, low, lane at pick-up (same trigger as #665); RECURRENCE promotions s10–s13 (five) →
  applied at close. #767 (a+) and #680's CI gate already ruled. Uncommitted producer-facing on main: `task_184/`,
  `context/CONTEXT.md` — wait for the user's word or the next prep commit (DECISIONS #5).
- [STANDING] User rule: do not quote them unless the wording carries specific meaning and weight; a bare approval is
  written as "the user accepted …". Applied at its homes: ORCHESTRATION log vocabulary, role prompt "Working with the
  user" (uncommitted, producer-facing); today's three approval-only headings in this file rewritten.
- **MERGED #767** — PR #780 → `5e316c67` (closes [767] — `gh` also lists a phantom [816]: the PR body cites anyio's upstream
  "fixes #816" and GitHub parsed it as a closing reference to THIS repo's #816, which does not exist; no effect, but an
  upstream issue number next to a closing keyword is the "does not close #N" trap in a new form — RECURRENCE n=1). 14/14
  incl. Windows + 3.14. Lock: anyio 4.15.1 (+ typing-extensions 4.16.0), pyproject untouched; `tests/test_third_party_compile_
  warnings.py` compiles every runtime dependency (5,488 files, 0 warnings on the locked 3.14 env — MEASURED by the lane) and
  fails on any; `cli/CLAUDE.md` rule line; the dry-run subprocess test's warning suppression removed. Fresh CI runner now
  clean → #680's baseline CI gate is filable. Worktree torn down; main ff'd. Residuals (PR body, NOT re-run): starlette 0.47.3
  test-client `DeprecationWarning` under anyio 4.15 (test-only; upgrade starlette); `MCPConnectionPool._evict_session` logs a
  cancel-scope `RuntimeError` on a dead session (same on 4.9.0; reconnect works); `test_dry_run_subprocess.py` can pick a
  global `pflow` without `VIRTUAL_ENV`; one uncaptured 648-byte cold-cache stderr (not reproduced in 24+ runs).
- FILED **#783** (baseline oracle never runs in CI; a job runs `verify.sh` on every PR — class: an unenforced regression net
  decays into noise; precondition #767 verified by its lane). Provisioned `chore/issue-783-baseline-ci-gate` @ `5e316c67`;
  LAUNCHED (Opus, high; additive job only; NOT required until 120 merges — my flip). Live: 120 build · lanes #776 #783.
- Lane #783 HANDED BACK (89k, 12 min; draft PR #784 @ `85e97401`): **`verify.sh` false-green on bash 5** — the loop pipes the
  case list on stdin and pflow reads a piped stdin (`core/shell_integration.py:161`), so case 1 swallows the other 86 and
  CI reported "1 passed" exit 0; macOS bash 3.2 uses a temp file, so every local 87/87 (incl. #680's) was real only by
  accident of shell version. Fix: empty stdin per case + a ran-fewer-than-found harness error. Main is red by one case
  (#775's guide `COOKIE` line, merged after #773). CI wall-clock 4m24s (3.13) / 5m16s (3.14), ~1 min added to PR wall-clock;
  no local-state deps; Windows not needed. RULED here (2/5 each): re-record the one case in this PR; ownership + `run-case.sh`
  + `regenerate.sh` (same bug — fix at the shared script); matrix → 3.13; not required until 120 merges. Lane RESUMED.
- **MERGED #776** — PR #787 → `714df226` (closes [776] only — verified via `gh`; CI green incl. Windows; 6 codex lenses, 0
  findings; falsifier 5/5 promises held). `Diagnostic.to_output_dict()` (= `to_dict()` through `redact_sensitive`) is the one
  printed form for both documents; `errors[]`/`warnings[]`/`advisories[]` lose the flattened copies (JSON-shape change, stated);
  the crash on a text 4xx body gone; `sanitize=` + the two-key block deleted; docs fixed (phantom `fixable` dropped); new
  `tests/test_cli/test_json_diagnostic_redaction.py` (real server, 4 cases, presence+absence). Follow-ups #781 #782 filed by
  the lane. Worktree torn down (falsifier stderr copied to `scratchpads/session-14/776-evidence/` first); main ff'd.
  Residual NOT filed by the lane: TEXT mode + MCP text print a failed reference's node data raw (`Response: {'access_token':
  'SECRET-…'}`, `core/diagnostic_render.py`, Task 120's file) — re-execution delegated before filing.
- FILED **#788** (text renderer prints a failed reference's node data unmasked — CLI text, permissive warnings, MCP text, and the
  trace `error` string `pflow report` prints verbatim; RE-EXECUTED on `714df226` incl. MCP over stdio; headers do NOT leak —
  the block renders body only; closing mechanism: render from `redact_sensitive(diagnostic.context)` at `format_diagnostic`'s
  one entry, drop the per-block calls; after Task 120 — `diagnostic_render.py` is its file). Evidence:
  `scratchpads/session-14/leak-text-mode-reference.md`. Queue: after 120, beside #781.
- Task 120 HANDED BACK post-gate (308k, 1.7 h; head `52ceb51e`, not pushed): gate + falsifier done (15 + 5 fixes, 0 Critical);
  `make check` green, 11469 tests, baseline 87/87; follow-ups filed by the orchestrator: #785 #786 #789 #790 #791 #792 + a
  comment on #743. Checkbox fixed (I4, `align-self: flex-start`, before/after shots 05/06; pre-existing `686b27f6c`) — I viewed
  shot 06. ESCALATED (3/5 ×2) → user: **H1** a required child input supplied only by env/settings — file-fixed child refused,
  runtime-picked child accepts (main refused both) → rec B (must come from the parent); **W1** a declared input bound to another
  name (`inputs: {doc: ${v}}`, batch alias) loses the never-re-parsed protection → rec A (inherit through whole-reference
  bindings; 168 in-tree bindings, zero behaviour change). Optional: fold #790 (shared container default; one deepcopy in a
  function the task rewrote) → RULED here (2/5): include, stated in the PR body as pre-existing.
- [RULING] the user accepted the recommendations: Task 120 H1 → B, W1 → A (in-task, plan addendum + targeted re-review;
  ADR-0017 one-liner mine at merge), #790 folded (closes). Task orchestrator RESUMED with the main deltas (#787 #780 #779) and
  the #783 baseline re-record ordering.
- **MERGED #783** — PR #784 → `e0f3af7d` (closes [783] only — verified via `gh`; CI green; the new `baseline-oracle` job 87/87 on
  the merged head, 4m05s; push CI on `e0f3af7d` in progress). `run-case.sh` gives every case `/dev/null` stdin (the one fix both
  scripts pass through); `verify.sh`/`regenerate.sh` fail when fewer cases ran than were found; `12/04-guide-auto-detect`
  re-recorded for #775; README counts fixed; `tests/test_scripts/test_baseline_harness.py` (5 tests, each mutation-checked);
  job NOT required yet — MINE after 120 merges: add `baseline-oracle` to `needs:` of `tests-and-type-check-done` + its result
  check. Worktree torn down; main ff'd. 120 merged main AFTER this landed? — its branch is at `151d703a`; verify at its
  hand-back that `04-guide-auto-detect` was regenerated on top of #784's recording.

## [2026-10-11 17:10] [GRANT] steps 1–5 of the plan this session, then close

- User: *"you are only at 446k so do 1-5 in this session then close"* — the wording sets the scope, so quoted. Read as: (1) merge
  120 + ADR-0017 W1 amendment; (2) flip `baseline-oracle` to required (its workflow commit on main is covered); (3) post-120
  lanes — #700+#739 class lane, #788, #781, then #755 #722 #749; (4) Task 184 planner (the spec/glossary/process prep commit is
  covered); (5) the standing dogfood pass; then the close ritual (state commit per DECISIONS #5 exception 2). OUT: the release
  (step 6), Task 178 (step 7), anything destructive beyond `./scripts/worktree rm`, any 3+/5 fork (parks), the user's HOME
  beyond the already-ruled re-sync.
- Task 120 PARKED on the HOME stop condition (337k; head `fc7da16e`, PG built: W1 A, H1 B, #790 folded; targeted re-review 2
  lenses, 2 fixes; `make test` 11528 before test-reflect): `~/.pflow/registry.json` rewritten 17:14:53 with the worktree's paths
  during I5's `make test`. RE-MEASURED by me: all MCP tool sets intact (post-repair counts), only the 11 built-in node paths
  re-pointed (now main's, mtime 17:19) — a registry RE-SCAN, not the s13 stub-overwrite class; the 15:11 MAIN-path rewrite
  was my ruled `mcp sync`. RULED: resume tests (benign class only; an MCP entry changing stays a hard stop); the test writer
  ROUTED to its own issue (probe agent launched: suspect `test_ui.py:1203-1207`, subprocess with inherited env); smaller
  decisions 1–3 accepted; ADR-0017 W1 line received (mine at merge). RECURRENCE "tests wrote the real HOME" → n=2 (different
  channel: subprocess env vs fixture order) — promote at close. Orchestrator RESUMED to merge main → gates → review → PR.
- Probe DONE (81k): suspect `test_ui.py` REFUTED; proven writers = three module-scoped `registry()` fixtures (`test_loop_
  validation.py:19`, `test_code_body_consumers.py:34`, `test_code_body_leftovers.py:35`) set up BEFORE the function-scoped
  isolation fixture — the Task 181 class again; entries preserved across 5 snapshots. My "mtime guard" closing mechanism
  REFUTED by evidence (concurrent real-HOME writers on this machine: a global `~/.local/bin/pflow` uv tool at **0.15.0**, two
  `pflow mcp serve`, worktree runs — version ping-pong rewrites on every load). FILED **#793** with (A): session-level HOME
  redirect + in-process tripwire naming the test + a spawn-env ratchet. User-side: the stale global uv tool install (0.15.0).
- LAUNCHED lane **#793** `fix/issue-793-tests-real-home` @ `e0f3af7d` (Opus, high; shape (A) ruled from the probe's evidence;
  fail-closed: zero real-HOME writes measured on the full suite before the PR; disjoint from 120 — 120 merges first if both
  are ready). Live: 120 (merging main → gates → PR) · lane #793.
- **MERGED Task 120** — PR #794 → `b95df8c5` (closes [188, 686, 687, 790] — verified via `gh`, all four CLOSED; task-review
  present; spec done + Completed 2026-10-11; CI green on the head incl. both Windows jobs, 3.10–3.14 and `baseline-oracle`;
  `make test-all-local` 11588; baseline 87/87 on the fixed harness). Carrier seam CHECKED: declared types ride the store
  (`__pflow_input_types__`), `embedded`/`auto_parse` stay consumer-side call args — one carrier, no second flag. Worktree torn
  down; main ff'd. Follow-ups (producer-filed): #777 #778 #785 #786 #789 #791 #792; comments on #675 #743. Producer residual to
  route: the Task-170 examples capture baseline is stale since #787 (12 diffs, 0 from 120) — same class as #680/#783.
- COMMITTED + PUSHED main `0b8ba587` (grant): ADR-0017 W1 amendment; CONTEXT.md **Declared type** (+ Run outcome from earlier);
  `.github/workflows/main.yml` — `baseline-oracle` in `needs:` + result check of `tests-and-type-check-done` (step 2 DONE).
- Provisioned post-120 lanes @ `0b8ba587`: `fix/issue-700-remedy-syntax-class` (closes #700 + #739), `fix/issue-788-text-
  diagnostic-redaction`, `fix/issue-781-run-documents-redacted`; packets copied with the base filled. Launching.
- LAUNCHED lanes (Opus, high, @ `0b8ba587`): **#700** (+#739, class lane) · **#788** (full floor + falsifier) · **#781** (full floor
  + falsifier; sibling: #700's two `run.py` literals). Live: lanes #793 #700 #788 #781 (4 lanes, 0 builds — at the cap).
  Next: Task 184 planner after #788 + #781 merge; dogfood pass after the lanes quiet; close.
- Lane #781 HANDED BACK mid-build (ownership): the class has one more member — the `--dry-run` JSON document
  (`plan_formatter.py:30,453`, raw `to_dict()`; EXECUTED: `api_key=SECRET…` printed at 4 `index_values` paths, masked without
  `--dry-run`); paused + denied leaks EXECUTED on post-120 main (denied via a real pty deny); `ui/server.py`'s six raw calls
  reported-not-fixed (authored data only). RULED here (2/5 ×2): plan_formatter swap + dry-run test (ownership widened);
  `to_display_dict` docstring corrected. Lane RESUMED. (Its ratchet covers `cli/`, `execution/formatters/`, `mcp_server/`.)
- FILED **#795** (Task-170 examples capture baseline unenforced; 12/29 drift = #787's S1 shape — RE-EXECUTED by me on `0b8ba587`
  under an isolated HOME; fold the check into the `baseline-oracle` job or delete the net on evidence). Queue: after #781 + #788.
- Lane #700 HANDED BACK pre-build (evaluation): both issues still real (executed); ~55 correct `- param:` literals already follow
  one house style → a nine-site renderer would be a SECOND convention; `template_errors.py` branch NOT dead (a set in a value
  reaches it; its "quote it" fix is a no-op). RULED here: R1 = (A) `binding_phrase()` for every bind-a-name remedy (three
  hand-written copies), house-style literals for scalars; ratchet = kwarg + JSON-key rules only (flag rule measured
  ineffective: 18/18 false positives, would not have caught `--timeout=60`); ownership + `type_validation.py`, `test_types.py`,
  `ir_preparation.py:285`, `guide/nodes/code.md:85,89`; `template_errors.py` message text only (engine logic untouched, stated
  in the PR) — the lane-B engine exclusion guards logic, not strings; `run.py` literals → #781's unless it merges first.
  Lane RESUMED. (R1 was rated 3/5 by the lane; settled by the lens — surfaced to the user.)

## [2026-10-11 ~18:10] Pre-swap handoff (Fable → Opus) — written, then EXECUTED by the Opus half (settled handling per lane,
steps 3–5, authority lines); cut at close as spent — every item landed or is parked in CURRENT-STATE.

- (Opus, after the user's `/model` swap) **MERGED #781** — PR #796 → `929d7729` (closes [781] only — verified via `gh`; CI green
  incl. Windows + `baseline-oracle`; 6 codex lenses + falsifier). Paused, denied, validate-only AND dry-run JSON documents use
  `to_output_dict()`; AST ratchet over `cli/`, `execution/formatters/`, `mcp_server/` with no allowlist; `- stdin: true` remedy
  literals fixed. Worktree torn down; main ff'd. Residuals: dry-run TEXT leak via `format_diagnostic` → relayed to lane #788;
  `analyze-cache --format=json` raw `to_dict()` (`prompt_cache_analysis/rendering/json.py:374`, no secret path found —
  ratchet-widening candidate); `ui/server.py` raw bodies (authored data only) → Task 184 planner; `validator.py:469,504` +
  `ir_preparation.py:285` JSON-key stdin text → already in lane #700's widened ownership.
- Provisioned `fix/issue-749-mcp-instructions-from-guide` @ `929d7729` (held fill; disjoint: #755 waits on #788's file, #722 shares
  `execution_service.py` with #700). Hand-back before building on any agent-facing contract change. Launching.
- Lane #749 HANDED BACK pre-build: the MCP instruction resources are a separate frozen 72 KB guide (~2,170 lines each), not
  drifted copies — ~30 shared sections mostly drifted, ~55 resource-only; whole features absent (approval, prompt caching,
  resume, `carry:`/`loop:`), some text now wrong (backward-edge loops; `pflow guide <topic>` for sandbox agents). Both packet
  mechanisms change what MCP agents receive. **Task 152** (pending, "then") already owns the surface: Phase 2 deletes the
  instruction resources for a `guide()` MCP tool, Phase 3 is the single-source decision; its spec is stale (file sizes, guide
  path, topic list, missing `plan_workflow`/`analyze_cache`, the `server.py:275-295` pointer, the pinning test).
  ESCALATED (4/5) → user: A fold #749 into 152 + refresh 152's spec + consider promoting it to "next" [rec] · B interim
  preface + full guide now · C paste the missing sections. Lane PARKED, worktree kept clean.
- **MERGED #788** — PR #797 → `9ef1be24` (closes [788] only — verified; 15/15 checks incl. Windows + `baseline-oracle`; 6 lenses +
  falsifier + delta re-review). `format_diagnostic` renders from `redact_sensitive(context)` once; all four per-block
  `sanitize_parameters` calls deleted (their 20-char truncation hid API errors); one `_capped(value, 300)` for every data line;
  ratchet: only the entry reads `diagnostic.context`; dry-run text covered. Worktree torn down; main ff'd. Residuals: batch
  `child_failure` raw copy into JSON (EXECUTED by its falsifier, 30 hits — re-execution delegated before filing);
  `template_errors.py:87-95` Value preview unredacted → relayed to lane #700 (its file); `mcp_server/utils/CLAUDE.md:12` stale
  "sanitize_parameters owns redaction"; permissive trace stores `warnings[].context` raw (#782 territory).
- Step 4: prep commit `05884642` (Task 184 spec + quote-rule process edits, by pathspec; pushed). Provisioned
  `feat/task-184-run-outcome` @ `05884642`; packet + evidence copied, base filled. LAUNCHED the **Fable task-planner** (plan-only,
  high). Live: planner 184 · lanes #793 #700 · #749 PARKED on the user.
- FILED **#799** (batched sub-workflow `child_failure` copied raw into CLI JSON + MCP success results — RE-EXECUTED on
  `05884642`: 4/20/4 hits across 3 variants, not "30"; text + report clean; ratchet misses it because the formatter copies a
  dict; closing at `compact_batch_error_detail` + guard; Task 184 coordination line added by me). Provisioned
  `fix/issue-799-batch-child-failure-redaction` @ `05884642` and LAUNCHING (security, same class as #776/#781/#788; free slot;
  not `runtime/`). (#798 appeared between filings — see next line.)
- #798 is lane #793's PR (session HOME redirect + audit-hook tripwire), not an issue. LAUNCHED lane **#799** (Opus, high).
  Live: planner 184 · lanes #793 (PR #798 open) #700 #799 · #749 parked on the user.
- **MERGED #793** — PR #798 → `b0ebe0a2` (closes [793] only — verified; 15/15 incl. Windows + 3.10–3.14). New plugin
  `tests/shared/real_home_guard.py` (armed at import, before any conftest): session HOME/USERPROFILE redirect + an audit hook
  that REFUSES file ops under the real `~/.pflow` + personal skill dirs (both `$HOME` and the `pwd` home) and any spawn whose env
  lacks/points at the real home; refusals fail the offending test by id. Measured: `make test` 11553 + e2e 56 with 0 refusals; the
  stand-in home got no `.pflow`. Hook ~1% CPU. Worktree torn down; main ff'd. SHARED TOOLING CHANGED → text delta sent to the
  live lanes (#700, #799). Residual: `git push`/`gh` with a redirected HOME fails the credential helper (agents: push with the
  normal HOME).
- Lane #799 HANDED BACK (STOP): the print funnel `compact_batch_output_value` is ALSO the runtime's archival compactor
  (`workflow_executor.py:689-693`) — redacting it redacts nested (depth ≥2) child-failure bundles in the trace + shared store
  (MEASURED: 8 raw → `<REDACTED>`). Options A (funnel only; trace redacted at depth ≥2) / B split raw-archive vs printing
  compactor, one-line runtime call-site (needs the lane-B exclusion waived) [rec] / C per-printer. ESCALATED (3/5) → user.
  Siblings for the next dogfood: `prompt_cache_analysis/rendering/json.py:373` raw `to_dict()` (analyze-cache JSON + MCP);
  `ui/server.py` raw bodies echoed by `cli/commands/ui.py:239-241` in JSON mode; `_probe_impl.py:258-272` prints a failed
  node's raw outputs (by design?). Not executed with a secret. Lane PARKED, edits uncommitted in its worktree.
- **MERGED #700 + #739** — PR #800 → `cf8b7fcb` (closes [700, 739] — verified; all checks pass incl. Windows + `baseline-oracle`;
  7 codex lenses + falsifier + delta re-review). Remedies name the `.pflow.md` line; bind-a-name remedies via `binding_phrase()`;
  `WorkflowExistsError` with each surface rendering its own fix; `template_errors.py` message text only (non-JSON value cause;
  Value preview redacted); ratchet `tests/test_remedy_syntax_hygiene.py` (JSON-key + kwarg rules, expiring allow-list);
  3 baseline cases re-recorded, named. Worktree torn down; main ff'd. Residuals: `delete_file.py:183` `confirm_delete=true`
  allow-listed with a reword reason (next session); MCP `workflow_save` docstring `force=true`; `settings.py` `pflow ui --say`;
  case-sensitive "str"; JSON-parse error Value preview unredacted; step with no code block passes validate-only; bare
  `RecursionError`; batch per-item errors show first line only; node remedies seen by `registry_run` users.
- Step 5: LAUNCHED the standing dogfood pass (Opus fresh-eyes, isolated HOME, `dogfood-s14-` prefix, ≤10 cheap LLM calls; report
  → `scratchpads/session-14/dogfood/report.md`). Then a verification agent re-executes + dedups + drafts; I file serially.
  Live: dogfood · planner 184 · parked on the user: #799 (A/B/C), #749 (Task 152 fold).
- Dogfood DONE: 28 findings (0 BLOCKER, 9 MISLEAD, 4 GAP, 15 PAPERCUT); 6 billed LLM calls ~$0.00004; isolated HOME; cleanup
  done (no delete command → removed by hand, #692 evidence). This week's changes: strict input types, "of up to M", redacted
  gate preview HELD; remedies-name-the-line holds only partly (unknown params/types, template typos, runtime param errors
  don't). Verification agent LAUNCHED (re-execute all 28, dedup, group into classes, draft) → `dogfood/verified.md`.
- Task 184 PLANNER HANDED BACK (~400k incl. 4 native searchers; plan `aa96b450` on the branch, not pushed): phases P0–P4 all Opus,
  one deep module `execution/formatters/run_outcome.py` (`build_run_outcome` + `render_cli_stderr` + `render_mcp_text`), ~30
  test files, no engine/trace/web contact; 6-lens codex plan review folded. Spec corrections (8, each cited) committed on the
  branch — incl. `errors` always a list, identity iff the trace streamed, field-specific "absent never null", pre-engine
  failures carry identity, top-level `nodes_executed` dropped. CP-1 (show-before-code, 4 questions, each ~2–3/5) → user:
  `implementation/show-before-code.md`. Not small → Opus task-orchestrator NEXT SESSION after CP-1 (grant excludes a build now).
- Dogfood verification DONE (203k): 27 reproduced, 1 partial (F14), 0 not. Read in full by me. FILED serially (each read back):
  **#801** (A, SECURITY: name-only masking prints the value in message/stderr/JSON; `set-env` echoes 3 chars) · **#802** (B:
  `--only` ignores the snapshot's recorded inputs; resume parity; #458 linked) · **#803** (C: remedies without a line / no-op fix /
  flag without command; one source-line enrichment seam + ratchet) · **#804** (D: input type + sources not surfaced; one helper;
  carries an OPEN decision — exact-case env matching, rec (a)) · **#805** (E: internal vocabulary on agent surfaces; `NodeConfig`
  IR type; trace-format note) · **#806** (F: plurals/articles/multi-line formatting; two helpers) · **#807** (G: resume messages
  ignore the attempt chain). Evidence comments: #675 (raise to medium — batch memo key omits every resolved non-item param),
  #735 (widen to every node's literal params; #76 a member), #245, #689, #740, #694, #350. Duplicates linked only: #458 #697
  #277 #428 #692 #701 #742 #712. Task 184 spec note (F20: what `success` means for paused/denied) → its next-session packet.
- STEPS 1–5 DONE. Parked on the user at close: #799 (A/B/C, rec B), #749 (rec A: fold into Task 152 + promote 152), Task 184
  CP-1 (Q1–Q4, rec yes ×4). → close ritual.

## Braindump

_Tacit residue only — ships, rulings and parked work live above, in CURRENT-STATE, the PR bodies and the task-reviews._

**The user this session — their words, and what they did with them**

- They restated the governing lens verbatim and asked *"does this change anything about how you see about any of this?"* —
  the fifth session running it arrives as an audit. Re-running the queue through it flipped three of five open items
  (#776's mechanism, #695 lane→task, #700 strings→class) and withdrew one (Task 121 freshening, recommended by analogy, not by
  an observed hit). Read a restated lens as "re-run everything on the table now", and label the re-derived shapes HYPOTHESIS.
- Their fix-standard arrived as two sentences that now ride every packet (role prompt): close the class, resolve ambiguity
  and assumptions before committing; and "keep a lookout for … consolidating seams". They accepted every class-shaped
  ruling I made on lanes (R1 = `binding_phrase` over a new renderer; drop the ineffective ratchet rule) without comment —
  the deletion-test reasoning stated in the ruling is what made that safe.
- *"i dont want myself quoted unless it has specific meaning and carries weight"* — they read the session file. A bare
  approval quoted in a heading irritated them; the quote rule is now at its homes. Corollary: they DO want operative wording
  verbatim (the lens, the class rule) — the distinction is weight, not quoting per se.
- *"prefer using pflow astra searchers when relevant"* — the codex offload is their default for searches now; the native
  searcher is the pair. Both astra runs this session could not reach GitHub — paste issue text inline (now in the workflow).
- They asked *"what does it mean in practice"* about the PyPI yank and implicitly tested whether I would overstate a public
  action. Answering the mechanism (yank ≠ delete; changes nothing for unpinned installs) flipped my own recommendation to NO.
  When a public action is on the table, explain the mechanism before recommending it.
- *"you can resync the mcp servers"* — they grant HOME writes per action, narrowly. I backed up the registry first; keep that.
- They noticed a UI defect (the run-form checkbox) from a checkpoint screenshot I had approved. Second session in a row the
  user caught a visual issue in a page I published as fine (s10: buttons below the fold). When publishing UI shots, look at
  every control's alignment, not just the feature under test.

**Overturned or corrected, owned**

- My closing mechanisms were refuted by the lanes' execution four times (#776 named-key sanitize crashes on a text body;
  #793 mtime guard flakes on concurrent writers; #767 `import pflow.cli` probe — the import is lazy since #752; #749 both
  mechanisms collide with Task 152). Each was written before anything ran. RECURRENCE n=2 → PROPOSED. The lanes' "hand back
  before building" condition is what caught every one — keep putting it in packets for anything with ≥2 shapes.
- My packet said Task 120 closes "exactly #686 #687"; the branch spec named #188. Read the BRANCH copy of a spec once a
  worktree owns it — main's copy is older by design.
- I filed #776's closing mechanism as "one sanitize pass" and only the lens re-run showed the duplication itself was the
  defect. Wrote the class from the evidence, the mechanism from habit.

**Mechanisms that worked — reuse them**

- **Producer residual → my re-execution agent → read draft → file.** Six security/process issues this session (#776 #783
  #788 #793 #795 #799) went through it; three were wider than the producer reported, one narrower (#799 "30 hits" → 20).
  The pattern: delegate the re-run to an Opus general-purpose agent with an isolated HOME and a section-structured draft;
  read the whole draft; file with `--body-file`; read back.
- **Text deltas to live lanes when main moves** (#781 → #788's dry-run text case; #793's guard → #700/#799) — one message,
  measured paths, "no reply needed". No lane tripped on a merge.
- **Splitting a verified file into issue bodies with a script**, then filing serially with a read-back per issue and a
  comment-count delta per comment — 7 issues + 8 comments in two calls, zero silent failures.
- **Pre-swap handoff with authority lines** (may rule / must escalate / never) — the Opus half ran 6 merges, a planner, the
  dogfood pass and its filing without re-deriving anything. Third session this held (s11, s12, s14).

**Dead ends — don't repeat**

- `pflow mcp sync a b c` — `sync` takes ONE name; loop it.
- `sed` substitution of a packet placeholder that wraps across lines silently matched 1 of 3 packets — prepend the filled
  line instead, and `grep -c` the result.
- `gh pr checks <N>` reported "no checks" after CI finished (API lag, seen by two lanes) — use `gh run view <id> --json jobs`.
- `python3 -c "import yaml"` — system python lacks it; `uv run python`.

**Seams noticed, not yet forced**

- The redaction class keeps finding new members because every fix closed a SURFACE (JSON docs, text render, run.py docs,
  batch funnel), not the property. #801 (value-based scrub at the render seam) is the first fix aimed at the property; if it
  lands before #799, #799 may shrink to the trace question. Task 184's single document builder is where a whole-document
  guard finally has one home — tell its orchestrator.
- Task 152 (MCP parity) and Task 178 (MCP SDK 2.x) both reshape `mcp_server/` and neither is planned; #749's finding (MCP
  agents read a frozen 72 KB guide missing approval/caching/resume) makes 152 more urgent than its "then" slot says.
- The examples capture net (#795) and the Task-159 oracle are two outer nets for overlapping surfaces; the #795 lane may
  find one redundant — the deletion test applies to test infrastructure too.
- The CLI's `--only` and `resume` assemble inputs differently (#802); Task 184 unifies outcome documents but not input
  assembly — a future "one run-input assembly" seam is visible in #802 + #804.

**Local-only artifacts**

- `scratchpads/session-14/` (main checkout, gitignored): `boot-fork-report.md`, `verify/{builders,remedies}.out` (the two
  astra reports Task 184 rests on — also copied into the 184 worktree), `leak-*.md` (re-execution write-ups behind #776,
  #788, #799), `test-real-home-writer.md` (#793's probe), `dogfood/{report,verified}.md` + `file/` (bodies as filed),
  `post120/` packets, `lane-799-parked.patch`, `776-evidence/`.
- Session scratchpad (`/private/tmp/claude-501/…/scratchpad/`): `registry.before-resync.json` (the user's pre-resync
  registry), `cp120/` (the published 120 checkpoint page source), isolated HOMEs and probe workflows. Disposable except the
  registry backup until the user confirms the re-sync is fine.
- Artifact page https://claude.ai/artifact/CLLwKWWRp6Dx5czbnmrzGd (private, Task 120 PF checkpoint).
- Branches `feat/task-184-run-outcome`, `fix/issue-799-…`, `fix/issue-749-…` exist ONLY locally with their worktrees.
  If lost: 184's plan is gone (spec on main survives); #799's patch is in the scratchpad; #749 had nothing built.

**Markers**

- ASKED-NOT-ANSWERED: Task 184 CP-1; #799 A/B/C; #749 / Task 152; the RECURRENCE "mechanism is a hypothesis" promotion.
- ASSUMPTION: the user's "go ahead with your recommendations for standing decisions" ratified the five s10–s13 RECURRENCE
  promotions AND the already-applied "ratify or revert" ones — all applied/deleted at this close on that reading.
- UNCLEAR: whether the user refreshed the stale global `pflow` 0.15.0 uv tool or cleaned the uvx cache — both told, neither
  confirmed.
- NEEDS VERIFICATION: the 184 plan's "P1 leaves the tree import-red by design" — the task orchestrator should confirm the
  phase-gate command the planner named actually runs green at P1's end before accepting that.
