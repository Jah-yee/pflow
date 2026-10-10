"""POSIX shell timeout: SIGTERM to the process group, a fixed grace, then SIGKILL."""

import signal
import subprocess
import sys
import time

import pytest

import pflow.nodes.shell.shell as shell_module
from pflow.nodes.shell.shell import ShellNode, _run_posix_shell_command

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups are not available on Windows")

GRACE = shell_module.TIMEOUT_GRACE_SECONDS


def run_shell_node(shared, **params):
    node = ShellNode()
    node.set_params(params)
    return node.run(shared)


class FakeProc:
    """Popen stand-in: the first communicate() times out, later calls follow ``after_stop``."""

    pid = 4321

    def __init__(self, after_stop="exit"):
        self.after_stop = after_stop  # "exit" | "ignore_term" | "hang"
        self.communicate_timeouts = []

    def communicate(self, input=None, timeout=None, **kwargs):  # noqa: A002 - mirrors subprocess API.
        self.communicate_timeouts.append(timeout)
        call = len(self.communicate_timeouts)
        if call == 1 or self.after_stop == "hang" or (self.after_stop == "ignore_term" and call == 2):
            raise subprocess.TimeoutExpired("sleep 10", timeout or 0, output=b"partial", stderr=b"err")
        return b"captured", b"stderr"


@pytest.fixture
def killpg_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(shell_module.os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    return calls


def _run_fake(monkeypatch, fake_proc, popen_calls=None):
    def fake_popen(*args, **kwargs):
        if popen_calls is not None:
            popen_calls.append((args, kwargs))
        return fake_proc

    monkeypatch.setattr(shell_module.subprocess, "Popen", fake_popen)
    return _run_posix_shell_command("sleep 10", stdin_bytes=None, cwd=None, env={"PATH": "x"}, timeout=0.1)


def test_timeout_terms_the_group_then_kills_what_outlived_the_shell(monkeypatch, killpg_calls):
    """A step that exits on SIGTERM keeps the output it wrote while stopping."""
    fake_proc = FakeProc(after_stop="exit")
    popen_calls = []

    with pytest.raises(subprocess.TimeoutExpired) as exc_info:
        _run_fake(monkeypatch, fake_proc, popen_calls)

    assert popen_calls[0][0][0] == "sleep 10"
    assert popen_calls[0][1] == {
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "cwd": None,
        "env": {"PATH": "x"},
        "start_new_session": True,
    }
    # The group id is the shell's pid (start_new_session); SIGKILL sweeps stragglers.
    assert killpg_calls == [(4321, signal.SIGTERM), (4321, signal.SIGKILL)]
    assert fake_proc.communicate_timeouts == [0.1, GRACE]
    assert exc_info.value.output == b"captured"
    assert exc_info.value.stderr == b"stderr"


def test_timeout_kills_a_step_that_outlives_the_grace(monkeypatch, killpg_calls):
    fake_proc = FakeProc(after_stop="ignore_term")

    with pytest.raises(subprocess.TimeoutExpired) as exc_info:
        _run_fake(monkeypatch, fake_proc)

    assert killpg_calls == [(4321, signal.SIGTERM), (4321, signal.SIGKILL)]
    assert fake_proc.communicate_timeouts == [0.1, GRACE, 1]
    assert exc_info.value.output == b"captured"


def test_timeout_uses_partial_output_when_drain_still_times_out(monkeypatch, killpg_calls):
    """A missed pipe holder must not make timeout recovery block indefinitely."""
    with pytest.raises(subprocess.TimeoutExpired) as exc_info:
        _run_fake(monkeypatch, FakeProc(after_stop="hang"))

    assert exc_info.value.output == b"partial"
    assert exc_info.value.stderr == b"err"


@pytest.mark.parametrize("raised", [KeyboardInterrupt, SystemExit])
def test_interrupt_kills_the_group_without_a_grace(monkeypatch, killpg_calls, raised):
    """Ctrl-C/SystemExit: pflow is exiting, so the group is killed at once — no SIGTERM."""

    class InterruptedProc:
        pid = 4321

        def __init__(self):
            self.communicate_timeouts = []

        def communicate(self, input=None, timeout=None, **kwargs):  # noqa: A002 - mirrors subprocess API.
            self.communicate_timeouts.append(timeout)
            if len(self.communicate_timeouts) == 1:
                raise raised()
            return b"", b""

    fake_proc = InterruptedProc()
    with pytest.raises(raised):
        _run_fake(monkeypatch, fake_proc)

    assert killpg_calls == [(4321, signal.SIGKILL)]
    assert fake_proc.communicate_timeouts == [0.1, 1]


def test_shell_timeout_kills_grandchild_holding_stdout_pipe():
    """A real grandchild that inherits stdout must not keep communicate() blocked."""
    shared = {}
    start = time.monotonic()

    action = run_shell_node(shared, command="sleep 2 | cat", timeout=0.05)

    elapsed = time.monotonic() - start
    assert elapsed < 0.5
    assert action == "error"
    assert shared["exit_code"] == -1
    assert "timed out" in shared["error"]


def test_timed_out_step_runs_its_term_trap_and_keeps_what_it_printed():
    """The point of the grace: a cooperative step reports before it goes."""
    shared = {}

    action = run_shell_node(
        shared,
        command="trap 'echo verdict-on-term; exit 7' TERM; echo early; sleep 30",
        timeout=0.5,
    )

    assert action == "error"
    assert shared["stdout"] == "early\nverdict-on-term"
    assert shared["exit_code"] == -1
    assert shared["timeout"] is True
    assert shared["error"] == "Command timed out after 0.5 seconds"


def test_step_ignoring_sigterm_is_killed_after_the_grace(monkeypatch):
    monkeypatch.setattr(shell_module, "TIMEOUT_GRACE_SECONDS", 0.3)
    shared = {}
    start = time.monotonic()

    # An ignored signal stays ignored in children, so `sleep` ignores SIGTERM too.
    action = run_shell_node(shared, command="trap '' TERM; echo early; sleep 30", timeout=0.2)

    elapsed = time.monotonic() - start
    assert 0.5 <= elapsed < 3
    assert action == "error"
    assert shared["stdout"] == "early"
    assert shared["exit_code"] == -1
    assert shared["timeout"] is True
