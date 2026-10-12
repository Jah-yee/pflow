"""A file-loaded code step can locate itself (issue #813).

``- code: ./x.py`` gives the body ``__file__`` = that file's absolute path, from any working
directory, including inside a nested child (resolved against the CHILD file) and per item of a
parallel batch; an inline body has no ``__file__``. A reused script's ``if __name__ == "__main__":``
block does not run (its ``sys.exit`` would end the whole run). Driven through the real CLI entry
point from a third directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pflow.cli.main import main

LOCATE = """import sys

result: dict = {"file": globals().get("__file__")}

if __name__ == "__main__":
    sys.exit(3)
"""

CHILD = """# Child

## Steps

### where

Report location.

- type: code
- code: ./lib/where.py

## Outputs

### located

Where the child's code file is.

- source: ${where.result}
"""

PARENT = """# Parent

## Steps

### top

Report location.

- type: code
- code: ./top.py

### fan

Report location per item.

- type: code
- code: ./top.py
- batch:
    items: [1, 2]
    parallel: true

### nested

Run the child.

- type: workflow
- workflow: ../kids/child.pflow.md

### inline

Inline body.

- type: code

```python code
result: dict = {"file": globals().get("__file__")}
```

## Outputs

### top

Top step.

- source: ${top.result}

### fan

Batch step.

- source: ${fan.results}

### child

Child step.

- source: ${nested.located}

### inline

Inline step.

- source: ${inline.result}
"""


def test_code_file_sees_its_own_path_from_any_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent, kids, elsewhere = tmp_path / "parent", tmp_path / "kids", tmp_path / "elsewhere"
    (kids / "lib").mkdir(parents=True)
    parent.mkdir()
    elsewhere.mkdir()
    (parent / "top.py").write_text(LOCATE, encoding="utf-8")
    (kids / "lib" / "where.py").write_text(LOCATE, encoding="utf-8")
    (kids / "child.pflow.md").write_text(CHILD, encoding="utf-8")
    (parent / "wf.pflow.md").write_text(PARENT, encoding="utf-8")
    monkeypatch.chdir(elsewhere)

    run = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", "../parent/wf.pflow.md"])

    assert run.exit_code == 0, run.stdout + run.stderr
    result = json.loads(run.stdout)["result"]
    top_file = str((parent / "top.py").resolve())
    assert result["top"] == {"file": top_file}
    assert [item["result"] for item in result["fan"]] == [{"file": top_file}] * 2
    assert result["child"] == {"file": str((kids / "lib" / "where.py").resolve())}
    assert result["inline"] == {"file": None}
