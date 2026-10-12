"""`pflow <workflow>` reads stdin only for an input declared `stdin: true` (#814, #666).

Real processes, real descriptors: CliRunner's stdin is a StringIO with no file
descriptor, so it can neither block on an open pipe nor present a regular file —
the two shapes these tests pin. An agent harness that spawns pflow with a stdin
pipe it never closes must not hang a workflow that takes no stdin, and
`pflow wf < file` must route like `cat file | pflow wf`, on every platform.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import IO

import pytest

pytestmark = pytest.mark.e2e

# Generous for a cold Windows interpreter; a run that reads an open pipe never ends at all.
_TIMEOUT = 60

_NO_INPUT_WF = """# Say Hi

Takes no input.

## Steps

### hi

Print a fixed line.

- type: shell

```shell command
echo hi
```
"""

_STDIN_WF = """# Capture

Writes its stdin input to a file.

## Inputs

### data

The piped data.

- type: string
- required: true
- stdin: true

## Steps

### capture

Write the input.

- type: write-file
- file_path: {out}
- content: ${{data}}
"""


def _stdin_workflow(tmp_path: Path) -> tuple[Path, Path]:
    out = tmp_path / "captured.txt"
    wf = tmp_path / "capture.pflow.md"
    wf.write_text(_STDIN_WF.format(out=out.as_posix()), encoding="utf-8")
    return wf, out


@contextlib.contextmanager
def _stdin(shape: str, tmp_path: Path) -> Iterator[int | IO[bytes]]:
    """Yield a child stdin of the given shape; an "open-pipe" writer stays open throughout."""
    if shape == "file":
        path = tmp_path / "stdin.txt"
        path.write_bytes(b"from a file\n")
        with path.open("rb") as f:
            yield f
        return
    read_fd, write_fd = os.pipe()
    try:
        if shape == "data-pipe":
            os.write(write_fd, b"piped data\n")
        if shape != "open-pipe":
            os.close(write_fd)
            write_fd = -1
        yield read_fd
    finally:
        os.close(read_fd)
        if write_fd != -1:
            os.close(write_fd)


def _run_pflow(args: list[str], stdin: int | IO[bytes], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pflow.cli", *args],
            stdin=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"pflow {' '.join(args)} hung reading a stdin it never asked for")


@pytest.mark.parametrize("shape", ["open-pipe", "empty-pipe", "data-pipe", "file"])
def test_stdin_is_never_read_without_a_stdin_input(shape, tmp_path, prepared_subprocess_env):
    wf = tmp_path / "hi.pflow.md"
    wf.write_text(_NO_INPUT_WF, encoding="utf-8")

    with _stdin(shape, tmp_path) as stdin:
        result = _run_pflow(["-p", str(wf)], stdin, prepared_subprocess_env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "hi"


def test_file_redirect_routes_to_the_stdin_input(tmp_path, prepared_subprocess_env):
    wf, out = _stdin_workflow(tmp_path)

    with _stdin("file", tmp_path) as stdin:
        result = _run_pflow([str(wf)], stdin, prepared_subprocess_env)

    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == "from a file"


def test_an_argument_for_the_stdin_input_leaves_an_open_pipe_unread(tmp_path, prepared_subprocess_env):
    wf, out = _stdin_workflow(tmp_path)

    with _stdin("open-pipe", tmp_path) as stdin:
        result = _run_pflow([str(wf), "data=from-argument"], stdin, prepared_subprocess_env)

    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == "from-argument"


def test_an_unresolvable_workflow_exits_2_without_reading_an_open_pipe(tmp_path, prepared_subprocess_env):
    with _stdin("open-pipe", tmp_path) as stdin:
        result = _run_pflow([str(tmp_path / "missing.pflow.md")], stdin, prepared_subprocess_env)

    assert result.returncode == 2, result.stderr
    assert "not found" in result.stderr.lower()
