"""Behavioural tests for the Task-159 baseline harness (verify.sh / regenerate.sh / run-case.sh).

The real scripts run against a throwaway baseline whose cases read stdin (`cat`), the way pflow
reads a piped stdin. The harness feeds its case list to its loop on stdin, so a case that can
reach that stream ends the run after one case; these tests pin that every case still runs, and
that a run which covers fewer cases than it found is a harness error, never green.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the baseline harness is bash")

BASELINE = Path(__file__).resolve().parents[2] / ".taskmaster" / "tasks" / "task_159" / "baseline"
HARNESS = ("verify.sh", "regenerate.sh", "run-case.sh", "normalize.py")
CASES = ("c1", "c2", "c3")


@pytest.fixture
def baseline(tmp_path: Path) -> Path:
    # run-case.sh resolves the repo root four levels up, so keep the real depth.
    root = tmp_path / "repo" / ".taskmaster" / "tasks" / "task_159" / "baseline"
    root.mkdir(parents=True)
    for name in HARNESS:
        shutil.copy2(BASELINE / name, root / name)
    for case in CASES:
        case_dir = root / case
        case_dir.mkdir()
        (case_dir / "command.sh").write_text(f"cat > /dev/null\necho {case}\n", encoding="utf-8")
    return root


def run(baseline: Path, script: str) -> subprocess.CompletedProcess[str]:
    # A non-empty piped stdin, as an agent's shell or CI step may give the harness.
    command = ["bash", str(baseline / script)]
    return subprocess.run(command, input="caller stdin\n", capture_output=True, encoding="utf-8")  # noqa: S603


def record(baseline: Path) -> None:
    for case in CASES:
        (baseline / case / "expected-stdout.txt").write_text(f"{case}\n", encoding="utf-8")
        (baseline / case / "expected-stderr.txt").write_text("", encoding="utf-8")
        (baseline / case / "expected-exit-code.txt").write_text("0\n", encoding="utf-8")


def test_verify_runs_every_case_when_cases_read_stdin(baseline: Path) -> None:
    record(baseline)
    result = run(baseline, "verify.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "summary: 3 passed, 0 drifted, 0 harness errors" in result.stdout


def test_regenerate_records_every_case_when_cases_read_stdin(baseline: Path) -> None:
    result = run(baseline, "regenerate.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    for case in CASES:
        assert (baseline / case / "expected-stdout.txt").read_text(encoding="utf-8") == f"{case}\n"
        assert (baseline / case / "expected-exit-code.txt").read_text(encoding="utf-8") == "0\n"


@pytest.mark.parametrize(("script", "exit_code"), [("verify.sh", 2), ("regenerate.sh", 1)])
def test_a_run_that_ends_early_is_a_harness_error(baseline: Path, script: str, exit_code: int) -> None:
    # Any future path by which a case reaches the loop's stdin: a run-case.sh that reads it.
    (baseline / "run-case.sh").write_text("#!/usr/bin/env bash\ncat > /dev/null\n", encoding="utf-8")
    record(baseline)
    result = run(baseline, script)
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert "harness error: ran 1 of 3 cases" in result.stderr
