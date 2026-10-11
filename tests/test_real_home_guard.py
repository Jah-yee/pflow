"""The real-home guard (``tests/shared/real_home_guard.py``) works end to end.

Runs a throwaway pytest session in a subprocess whose "real" home is a temp
directory, so the guard can be exercised without the developer's actual home
being at stake.
"""

import os
import subprocess
import sys
from pathlib import Path

from tests.conftest import set_isolated_home

REPO_ROOT = Path(__file__).resolve().parent.parent

INNER_TESTS = """
import os
import subprocess
import sys
from pathlib import Path

import pytest

REAL_HOME = Path(os.environ["PFLOW_TEST_REAL_HOME"])


@pytest.fixture(scope="module")
def module_scoped_home():
    # Set up before any function-scoped fixture could redirect the home (#793).
    state = Path.home() / ".pflow" / "registry.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("{}", encoding="utf-8")
    return Path.home()


def test_wider_scoped_fixture_gets_the_session_home(module_scoped_home):
    assert module_scoped_home != REAL_HOME


def test_swallowed_write_under_real_pflow(tmp_path):
    try:
        (REAL_HOME / ".pflow" / "registry.json").write_text("{}", encoding="utf-8")
    except Exception:
        pass  # code under test that swallows the refusal must not hide it


def test_swallowed_spawn_without_home():
    env = {k: v for k, v in os.environ.items() if k not in ("HOME", "USERPROFILE")}
    try:
        subprocess.run([sys.executable, "-c", "pass"], env=env, check=False)
    except Exception:
        pass


def test_spawn_with_isolated_home(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    subprocess.run([sys.executable, "-c", "pass"], env=env, check=True)
"""


def test_guard_redirects_wider_scopes_and_fails_tests_that_reach_the_real_home(tmp_path: Path) -> None:
    real_home = tmp_path / "real_home"
    real_home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (project / "test_inner.py").write_text(INNER_TESTS, encoding="utf-8")

    env = {k: v for k, v in os.environ.items() if k != "PFLOW_TEST_REAL_HOME"}
    set_isolated_home(env, real_home)
    env["PYTHONPATH"] = str(REPO_ROOT)
    inner_pytest = [sys.executable, "-m", "pytest", "-p", "tests.shared.real_home_guard", "-p", "no:xdist"]
    result = subprocess.run(  # noqa: S603 - fixed argv
        [*inner_pytest, "-p", "no:cacheprovider", "-rA", "test_inner.py"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    output = result.stdout + result.stderr

    outcomes = {
        line.split()[1].split("::")[-1]: line.split()[0]
        for line in result.stdout.splitlines()
        if line.startswith(("PASSED ", "FAILED ", "ERROR "))
    }
    assert outcomes == {
        "test_wider_scoped_fixture_gets_the_session_home": "PASSED",
        "test_swallowed_write_under_real_pflow": "FAILED",
        "test_swallowed_spawn_without_home": "FAILED",
        "test_spawn_with_isolated_home": "PASSED",
    }, output
    assert "test_swallowed_write_under_real_pflow touched the developer's real home" in output
    assert "has no HOME" in output or "has no USERPROFILE" in output
    assert not (real_home / ".pflow").exists(), "the refused write still landed in the real home"
