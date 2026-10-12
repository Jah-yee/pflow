# Examples capture

The run-JSON regression net for the workflows under `examples/` — the files agents copy from.
Each example listed in `manifest.json` runs as `pflow --output-format json <file> [k=v ...]`
in a fresh HOME, a fresh cwd and an empty stdin; its output is normalized (durations, trace paths, UUIDs,
OS/arch, repo/cwd/HOME paths) and stored as `<dir>__<name>.json`. Built for Task 170; the Task-159
oracle (`.taskmaster/tasks/task_159/baseline/`) is its sibling for analyze-cache, warnings,
validation and run-flag text.

```bash
uv run python .taskmaster/tasks/task_170/implementation/examples-baseline/capture.py --check  # diff
uv run python .taskmaster/tasks/task_170/implementation/examples-baseline/capture.py          # re-record
```

`--check` exit codes: 0 = clean, 1 = drift (unified diff per example), 2 = harness error
(the manifest is empty, a listed example no longer exists, or a stored capture has no
manifest entry).

CI runs `--check` on every PR and on `main`, in the `baseline-oracle` job of
`.github/workflows/main.yml` (ubuntu, after the Task-159 oracle). **A PR that intentionally
changes an example's output re-records in the same PR (`capture.py`) and names the
re-recorded examples in its body; any other drift is a regression.**

## The case list

`manifest.json` is the list: add `{"example": "examples/…/x.pflow.md", "params": {}}` and run
`capture.py`, which fills in `exit_code` and `output`. Delete an entry with its example;
re-capturing removes the stale `.json`. Not every example is listed: `llm`/`agent`/`http`/MCP
examples cannot run offline, and a few offline ones (fixture-file inputs, the parse-error
fixtures in `examples/invalid/`) were never added — adding one is the step above.
