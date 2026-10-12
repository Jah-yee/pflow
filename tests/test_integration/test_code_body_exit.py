"""A code body that calls ``sys.exit`` fails its step; it never ends the pflow run (issue #821).

Before the fix the body's ``SystemExit`` became pflow's own process exit — ``sys.exit(3)`` exited 3 (the
denied-gate code) with no JSON document on stdout. Driven through the real CLI entry point: a plain step,
an item of a parallel batch, and a step inside a child workflow each yield the JSON failure document
naming the exit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pflow.cli.main import main

PLAIN = """# Plain

## Steps

### quit

Exit mid-body.

- type: code

```python code
import sys
result: int = 1
print("no input file", file=sys.stderr)
sys.exit(3)
```

### downstream

Must not run.

- type: shell

```shell command
echo downstream
```
"""

BATCH = """# Batch

## Steps

### fan

Exit on the second item.

- type: code
- inputs: {n: "${item}"}
- batch:
    items: [1, 2]
    parallel: true

```python code
import sys
n: int
if n == 2:
    sys.exit(4)
result: int = n
```
"""

CHILD = """# Child

## Steps

### quit

Exit mid-body.

- type: code

```python code
import sys
sys.exit(5)
result: int = 1
```

## Outputs

### value

The child's value.

- source: ${quit.result}
"""

PARENT = """# Parent

## Steps

### nested

Run the child.

- type: workflow
- workflow: ./child.pflow.md
"""


RETRIED = """# Retried

## Steps

### quit

Count attempts, then exit or raise.

- type: code
- inputs: {log: "LOG", how: "HOW"}
- retry: { max: 3 }

```python code
import sys
log: str
how: str
with open(log, "a", encoding="utf-8") as fh:
    fh.write("x")
if how == "exit":
    sys.exit(1)
raise RuntimeError("flaky")
result: int = 1
```
"""


def _run(path: Path) -> dict:
    run = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", str(path)])
    assert run.exit_code == 1, f"exit {run.exit_code}\n{run.stdout}{run.stderr}"
    document: dict = json.loads(run.stdout)
    assert document["success"] is False
    return document


def test_sys_exit_fails_the_step_and_downstream_never_runs(tmp_path: Path) -> None:
    (tmp_path / "plain.pflow.md").write_text(PLAIN, encoding="utf-8")

    document = _run(tmp_path / "plain.pflow.md")

    assert document["error"].startswith("Code called sys.exit(3)")
    assert "Stderr: no input file" in document["error"]
    assert [e["node_id"] for e in document["errors"]] == ["quit"]
    assert document["execution"]["nodes_executed"] == 0


@pytest.mark.parametrize(
    ("files", "shown"),
    [({"batch.pflow.md": BATCH}, "sys.exit(4)"), ({"child.pflow.md": CHILD, "parent.pflow.md": PARENT}, "sys.exit(5)")],
    ids=["parallel-batch-item", "child-workflow"],
)
def test_sys_exit_inside_batch_item_or_child_fails_the_run(tmp_path: Path, files: dict[str, str], shown: str) -> None:
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")

    document = _run(tmp_path / list(files)[-1])

    assert f"Code called {shown}" in document["error"]


@pytest.mark.parametrize(("how", "error"), [("exit", "Code called sys.exit(1)"), ("raise", "RuntimeError: flaky")])
def test_step_retry_reruns_a_sys_exit_like_a_raised_exception(tmp_path: Path, how: str, error: str) -> None:
    log = tmp_path / "attempts.txt"
    workflow = tmp_path / "retried.pflow.md"
    workflow.write_text(RETRIED.replace("LOG", log.as_posix()).replace("HOW", how), encoding="utf-8")

    document = _run(workflow)

    assert document["error"].startswith(error)
    assert log.read_text(encoding="utf-8") == "xxx"
