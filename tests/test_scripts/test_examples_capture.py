"""Behavioural tests for the examples capture harness (Task 170's examples-baseline/capture.py).

The real script runs against a throwaway repo — its own examples and manifest, the pflow beside
this interpreter. Every run gets a non-empty piped stdin, as a CI step or an agent's shell may
give the harness: pflow reads a piped stdin, so an example that inherited it would fail.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CAPTURE = (
    Path(__file__).resolve().parents[2]
    / ".taskmaster"
    / "tasks"
    / "task_170"
    / "implementation"
    / "examples-baseline"
    / "capture.py"
)

WORKFLOW = """# Writer

Writes one file.

## Steps

### hello

Write a greeting.

- type: write-file
- content: Hello
- file_path: {file_path}
"""


PLATFORM_WORKFLOW = """# Platform

Reports where it runs.

## Steps

### where

Name the OS and machine.

- type: code

```python code
import platform

result: str = f"on {platform.system()} {platform.machine()}"
```
"""


def write_manifest(here: Path, examples: list[str]) -> None:
    entries = [{"example": example, "params": {}} for example in examples]
    (here / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")


@pytest.fixture
def harness(tmp_path: Path) -> Path:
    # capture.py resolves the repo root four levels up, so keep the real depth.
    here = tmp_path / "repo" / ".taskmaster" / "tasks" / "task_170" / "implementation" / "examples-baseline"
    here.mkdir(parents=True)
    shutil.copy2(CAPTURE, here / "capture.py")
    examples = tmp_path / "repo" / "examples"
    examples.mkdir()
    for name in ("one", "two"):
        (examples / f"{name}.pflow.md").write_text(WORKFLOW.format(file_path="hello.txt"), encoding="utf-8")
    write_manifest(here, ["examples/one.pflow.md", "examples/two.pflow.md"])
    return here


def run(here: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(here / "capture.py"), *args]
    return subprocess.run(command, input="caller stdin\n", capture_output=True, encoding="utf-8")  # noqa: S603


def test_capture_runs_every_example_on_an_empty_stdin_and_check_matches(harness: Path) -> None:
    captured = run(harness)
    assert captured.returncode == 0, captured.stdout + captured.stderr
    manifest = json.loads((harness / "manifest.json").read_text(encoding="utf-8"))
    assert [(entry["exit_code"], entry["output"]) for entry in manifest] == [(0, "one.json"), (0, "two.json")]
    stored = json.loads((harness / "one.json").read_text(encoding="utf-8"))
    assert stored["status"] == "success"
    assert "<CWD>" in stored["result"]["hello"]["written"]
    # The run's identity is stored masked: the id by its UUID shape, the trace file (whose name
    # carries a timestamp) by its key — otherwise every re-capture would differ.
    assert stored["execution_id"] == "<UUID>"
    assert stored["trace_path"] == "<TRACE_PATH>"

    checked = run(harness, "--check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "2 examples, 0 differing" in checked.stdout


def test_check_fails_and_names_the_example_whose_output_drifted(harness: Path) -> None:
    assert run(harness).returncode == 0
    example = harness.parents[4] / "examples" / "two.pflow.md"
    example.write_text(WORKFLOW.format(file_path="bye.txt"), encoding="utf-8")

    checked = run(harness, "--check")
    assert checked.returncode == 1, checked.stdout + checked.stderr
    assert "same examples/one.pflow.md" in checked.stdout
    assert "DIFF examples/two.pflow.md (exit 0 -> 0)" in checked.stdout
    assert "bye.txt" in checked.stdout
    assert "2 examples, 1 differing" in checked.stdout


def test_the_os_name_and_machine_are_normalized(harness: Path) -> None:
    # CI checks on Linux what a developer records on macOS; an example printing `uname` must match on both.
    example = harness.parents[4] / "examples" / "one.pflow.md"
    example.write_text(PLATFORM_WORKFLOW, encoding="utf-8")

    assert run(harness).returncode == 0
    assert '"on <OS> <ARCH>"' in (harness / "one.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("args", [(), ("--check",)])
def test_a_listed_example_that_no_longer_exists_is_a_harness_error(harness: Path, args: tuple[str, ...]) -> None:
    # Re-recording would otherwise store pflow's file-not-found document as the expected output.
    write_manifest(harness, ["examples/one.pflow.md", "examples/gone.pflow.md"])

    result = run(harness, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "harness error: listed example does not exist: examples/gone.pflow.md" in result.stderr
    assert not (harness / "one.json").exists()


@pytest.mark.parametrize("args", [(), ("--check",)])
def test_an_empty_manifest_is_a_harness_error(harness: Path, args: tuple[str, ...]) -> None:
    # Otherwise capture deletes every stored capture and check passes having compared nothing.
    stored = harness / "one.json"
    stored.write_text("{}\n", encoding="utf-8")
    write_manifest(harness, [])

    result = run(harness, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "harness error: manifest.json lists no examples" in result.stderr
    assert stored.exists()


def test_a_stored_capture_without_a_manifest_entry_fails_check_and_capture_removes_it(harness: Path) -> None:
    stale = harness / "gone.json"
    stale.write_text("{}\n", encoding="utf-8")

    checked = run(harness, "--check")
    assert checked.returncode == 2, checked.stdout + checked.stderr
    assert "harness error: stored capture has no manifest entry: gone.json" in checked.stderr

    captured = run(harness)
    assert captured.returncode == 0, captured.stdout + captured.stderr
    assert not stale.exists()
    assert run(harness, "--check").returncode == 0
