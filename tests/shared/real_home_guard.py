"""Pytest plugin: the test session never touches the developer's real home.

``isolate_pflow_config`` (``tests/conftest.py``) redirects the home per test, but
it cannot reach two channels: fixtures with a wider scope are set up before it
runs, and a subprocess spawned with a hand-built env falls back to the
password-database home when ``HOME`` is absent. This plugin closes both for the
whole session:

1. Importing this module (``tests/conftest.py`` registers it, so pytest imports it
   right after the root conftest, before any other conftest, fixture or test)
   points ``HOME`` and ``USERPROFILE`` at a throwaway session home. xdist workers
   inherit the redirect, and the real home travels to them in ``PFLOW_TEST_REAL_HOME``.
2. An audit hook refuses any in-process file operation under a directory pflow
   owns in the real home (``$HOME`` as found, and the account's password-database
   home), and any spawn whose env lacks an isolated home. The
   refusal is recorded and fails the test (or collected module) whose phase
   triggered it, even if the code under test swallows the exception.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REAL_HOME_ENV = "PFLOW_TEST_REAL_HOME"
# ``--doctest-modules`` imports this file a second time under another module name; arm once per process.
_ARMED_PID_ENV = "PFLOW_TEST_HOME_GUARD_PID"
_HOME_VARS = ("HOME", "USERPROFILE")
# The variable a child's ``Path.home()`` reads; without it the child falls back to the account's real home.
_CHILD_HOME_VAR = "USERPROFILE" if sys.platform == "win32" else "HOME"

# Audit event -> positions of its path arguments (``os.rename`` is also raised by ``os.replace``).
_PATH_EVENTS: dict[str, tuple[int, ...]] = {
    "open": (0,),
    "os.listdir": (0,),
    "os.scandir": (0,),
    "os.mkdir": (0,),
    "os.rename": (0, 1),
    "os.remove": (0,),
    "os.rmdir": (0,),
    "os.chmod": (0,),
    "os.utime": (0,),
    "os.truncate": (0,),
    "os.link": (0, 1),
    "os.symlink": (0, 1),
    "shutil.copyfile": (0, 1),
    "shutil.copytree": (0, 1),
    "shutil.move": (0, 1),
    "shutil.rmtree": (0,),
    "sqlite3.connect": (0,),
}


class RealHomeAccessError(RuntimeError):
    """A test reached the developer's real home. Not an ``OSError``, so ``except OSError`` cannot hide it."""


@dataclass
class _State:
    real_homes: tuple[str, ...] = ()
    session_home: str = ""
    protected_roots: tuple[str, ...] = ()
    violations: list[str] = field(default_factory=list)


_state = _State()  # one per process: what the audit hook guards and what it has refused so far


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _real_homes(captured: str) -> tuple[str, ...]:
    """The home found in the environment, plus the one a child without ``HOME`` falls back to (POSIX)."""
    homes = {_norm(captured)}
    try:
        import pwd

        homes.add(_norm(pwd.getpwuid(os.getuid()).pw_dir))
    except (ImportError, KeyError):  # Windows has no pwd; a uid without an entry has no fallback home
        pass
    return tuple(sorted(homes))


def _protected_roots(real_homes: tuple[str, ...]) -> tuple[str, ...]:
    """Every directory pflow itself writes under a user's home: its state dir and the personal skill dirs."""
    from pflow.core.workflow.skill_service import SKILL_TARGETS

    subdirs = {".pflow", *(personal for _project, personal in SKILL_TARGETS.values())}
    roots = {_norm(os.path.join(home, subdir)) for home in real_homes for subdir in subdirs}
    roots |= {_norm(os.path.realpath(root)) for root in roots}
    return tuple(sorted(roots))


def _is_protected(path: object) -> bool:
    if not isinstance(path, (str, bytes, os.PathLike)):
        return False  # file descriptors, None
    normalized = _norm(os.fsdecode(path))
    return any(normalized == root or normalized.startswith(root + os.sep) for root in _state.protected_roots)


def _spawn_env_problem(env: Mapping[Any, Any]) -> str | None:
    """Why a subprocess env would let the child resolve the real home, or None if it cannot."""
    values = {os.fsdecode(key): os.fsdecode(value) for key, value in env.items()}
    if sys.platform == "win32":  # Windows env names are case-insensitive
        values = {key.upper(): value for key, value in values.items()}
    if _CHILD_HOME_VAR not in values:
        return f"its env has no {_CHILD_HOME_VAR}, so the child falls back to the real home"
    for var in _HOME_VARS:
        if var in values and _norm(values[var]) in _state.real_homes:
            return f"its env sets {var} to the real home"
    return None


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if event == "subprocess.Popen":
        _executable, argv, _cwd, env = args
        problem = _spawn_env_problem(os.environ if env is None else env)
        if problem:
            _refuse(f"spawned {argv!r}, but {problem}. Build the env with tests.conftest.set_isolated_home")
        return
    positions = _PATH_EVENTS.get(event)
    if positions is None:
        return
    for position in positions:
        if position < len(args) and _is_protected(args[position]):
            _refuse(f"{event} {os.fsdecode(args[position])!r}")


def _refuse(what: str) -> None:
    current = os.environ.get("PYTEST_CURRENT_TEST", "outside any test")
    message = f"{what} (during {current})"
    _state.violations.append(message)
    raise RealHomeAccessError(f"test touched the developer's real home: {message}")


def _drain_violations(nodeid: str, when: str) -> str | None:
    pending, _state.violations = _state.violations, []  # appends racing this swap land in ``pending``
    if not pending:
        return None
    return "\n".join([
        f"{nodeid} touched the developer's real home ({', '.join(_state.real_homes)}) during {when}:",
        *(f"  - {violation}" for violation in pending),
        "Resolve paths through Path.home()/$HOME at use time; give a wider-scoped fixture an explicit tmp path.",
    ])


def _fail_report(report: pytest.TestReport | pytest.CollectReport, text: str) -> None:
    if report.failed and report.longrepr is not None:
        report.sections.append(("real home guard", text))
    else:
        report.outcome = "failed"
        report.longrepr = text


def _arm() -> None:
    """Redirect the home and install the audit hook — at import, so even conftest module code is covered."""
    real_home = os.environ.get(REAL_HOME_ENV) or str(Path.home())
    _state.session_home = tempfile.mkdtemp(prefix="pflow-test-home-")
    os.environ[REAL_HOME_ENV] = real_home
    os.environ[_ARMED_PID_ENV] = str(os.getpid())
    for var in _HOME_VARS:
        os.environ[var] = _state.session_home
    _state.real_homes = _real_homes(real_home)
    _state.protected_roots = _protected_roots(_state.real_homes)
    # Never removed or disabled: a thread a test leaves running (a timed-out code node's worker)
    # can still touch the home after the session ends, and the refusal must still hold then.
    sys.addaudithook(_audit)


def pytest_unconfigure(config: pytest.Config) -> None:
    shutil.rmtree(_state.session_home, ignore_errors=True)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Generator[None, Any, None]:
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    text = _drain_violations(item.nodeid, report.when)
    if text:
        _fail_report(report, text)


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> Generator[None, Any, None]:
    outcome = yield
    text = _drain_violations(collector.nodeid, "collection")
    if text:
        _fail_report(outcome.get_result(), text)


if os.environ.get(_ARMED_PID_ENV) != str(os.getpid()):
    _arm()
