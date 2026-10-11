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
CHILD_HOME_VAR = "USERPROFILE" if sys.platform == "win32" else "HOME"

INNER_TESTS = """
import os
import subprocess
import sys
from pathlib import Path

import pytest

REAL_HOME = Path(os.environ["PFLOW_TEST_REAL_HOME"])
MARKERS = Path(os.environ["GUARD_TEST_MARKERS"])
CHILD_HOME_VAR = "USERPROFILE" if sys.platform == "win32" else "HOME"
WRITE_HOME_TO_MARKER = "import sys; from pathlib import Path; Path(sys.argv[1]).write_text(str(Path.home()), encoding='utf-8')"


@pytest.fixture(scope="module")
def module_scoped_home():
    # Set up before any function-scoped fixture could redirect the home (#793).
    state = Path.home() / ".pflow" / "registry.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("written by a module-scoped fixture", encoding="utf-8")
    return Path.home()


def test_wider_scoped_fixture_gets_the_session_home(module_scoped_home):
    assert module_scoped_home != REAL_HOME


def test_swallowed_write_under_real_pflow():
    try:
        (REAL_HOME / ".pflow" / "registry.json").write_text("overwritten", encoding="utf-8")
    except Exception:
        pass  # code under test that swallows the refusal must not hide it


def test_swallowed_spawn_without_child_home_var():
    # Only the variable this platform's children read is missing; the other stays set.
    env = {k: v for k, v in os.environ.items() if k.upper() != CHILD_HOME_VAR}
    try:
        subprocess.run([sys.executable, "-c", WRITE_HOME_TO_MARKER, str(MARKERS / "refused")], env=env)
    except Exception:
        pass


def test_swallowed_inherited_spawn_without_child_home_var(monkeypatch):
    monkeypatch.delenv(CHILD_HOME_VAR)
    try:
        subprocess.run([sys.executable, "-c", WRITE_HOME_TO_MARKER, str(MARKERS / "refused-inherited")])
    except Exception:
        pass


def test_spawn_with_isolated_home(tmp_path):
    env = dict(os.environ, **{CHILD_HOME_VAR: str(tmp_path)})
    marker = MARKERS / "allowed"
    subprocess.run([sys.executable, "-c", WRITE_HOME_TO_MARKER, str(marker)], env=env, check=True)
    assert marker.read_text(encoding="utf-8") == str(tmp_path)
"""

INNER_COLLECTION_TIME_WRITE = """
import os
from pathlib import Path

try:
    (Path(os.environ["PFLOW_TEST_REAL_HOME"]) / ".pflow" / "registry.json").write_text("x", encoding="utf-8")
except Exception:
    pass


def test_never_reached():
    pass
"""


# pytest imports ``test*/conftest.py`` before configuring the session; the guard must already be armed.
INNER_EARLY_CONFTEST = """
from pathlib import Path

state = Path.home() / ".pflow" / "registry.json"
state.parent.mkdir(parents=True, exist_ok=True)
state.write_text("written while pytest imported its first conftests", encoding="utf-8")
"""


def test_guard_redirects_wider_scopes_and_refuses_the_real_home(tmp_path: Path) -> None:
    real_home = tmp_path / "real_home"
    real_registry = real_home / ".pflow" / "registry.json"
    real_registry.parent.mkdir(parents=True)
    real_registry.write_text("the user's registry", encoding="utf-8")
    markers = tmp_path / "markers"
    markers.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (project / "conftest.py").write_text('pytest_plugins = ("tests.shared.real_home_guard",)\n', encoding="utf-8")
    (project / "test_early").mkdir()
    (project / "test_early" / "conftest.py").write_text(INNER_EARLY_CONFTEST, encoding="utf-8")
    (project / "test_inner.py").write_text(INNER_TESTS, encoding="utf-8")
    (project / "test_collection_time.py").write_text(INNER_COLLECTION_TIME_WRITE, encoding="utf-8")

    env = {k: v for k, v in os.environ.items() if k not in ("PFLOW_TEST_REAL_HOME", "PYTEST_CURRENT_TEST")}
    set_isolated_home(env, real_home)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["GUARD_TEST_MARKERS"] = str(markers)
    flags = ["-p", "no:xdist", "-p", "no:cacheprovider", "-rA", "--continue-on-collection-errors"]
    result = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, "-m", "pytest", *flags, "."],
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
        "test_swallowed_spawn_without_child_home_var": "FAILED",
        "test_swallowed_inherited_spawn_without_child_home_var": "FAILED",
        "test_spawn_with_isolated_home": "PASSED",
        "test_collection_time.py": "ERROR",
    }, output
    assert "test_swallowed_write_under_real_pflow touched the developer's real home" in output
    assert f"its env has no {CHILD_HOME_VAR}" in output
    # Refused means prevented, not just reported: the write and the spawn never happened.
    assert real_registry.read_text(encoding="utf-8") == "the user's registry"
    assert not (markers / "refused").exists()
    assert not (markers / "refused-inherited").exists()
    assert (markers / "allowed").exists()
