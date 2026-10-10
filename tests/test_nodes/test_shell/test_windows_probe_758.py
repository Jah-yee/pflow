"""TEMPORARY measurement probe for #758 (Windows graceful-stop options). Never merged."""

import ctypes
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

import pflow.nodes.shell.shell as shell_module

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="windows-only probe")

STEP = (
    ": PROBE_MARKER; trap 'echo GOT_TERM; exit 7' TERM; trap 'echo GOT_INT; exit 8' INT; "
    "trap 'echo GOT_HUP; exit 9' HUP; echo early; sleep 20; echo late"
)

GROUP_TERM = (
    'for d in /proc/[0-9]*; do p="${d#/proc/}"; '
    'if tr "\\0" " " < "$d/cmdline" 2>/dev/null | grep -q "PROBE_""MARKER" '
    '&& [ "$(cat "$d/pgid" 2>/dev/null)" = "$p" ]; then echo "kill -TERM -$p"; kill -TERM -- "-$p"; fi; done'
)

TABLE = (
    'for d in /proc/[0-9]*; do printf "%s winpid=%s pgid=%s ppid=%s ctty=%s cmd=%s\\n" "${d#/proc/}" '
    '"$(cat $d/winpid 2>/dev/null)" "$(cat $d/pgid 2>/dev/null)" "$(cat $d/ppid 2>/dev/null)" '
    '"$(cat $d/ctty 2>/dev/null)" "$(tr "\\0" " " < $d/cmdline 2>/dev/null | cut -c1-80)"; done'
)


def _bash() -> str:
    bash = shell_module._resolve_windows_bash()
    assert bash
    return bash


def _env(bash: str) -> dict[str, str]:
    return shell_module._prepare_windows_shell_env(None, bash)


def _run(argv: list[str], bash: str) -> str:
    r = subprocess.run(argv, capture_output=True, env=_env(bash), check=False, timeout=30)  # noqa: S603
    return f"rc={r.returncode} out={r.stdout.decode(errors='replace')!r} err={r.stderr.decode(errors='replace')!r}"


def _measure(name: str, bash: str, stop) -> str:
    proc = subprocess.Popen(  # noqa: S603
        [bash, "-c", STEP],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        env=_env(bash),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    time.sleep(2)
    table = _run([bash, "-c", TABLE], bash)
    t0 = time.monotonic()
    try:
        stop_note = stop(proc, bash)
    except Exception as exc:
        stop_note = f"raised {exc!r}"
    try:
        out, err = proc.communicate(timeout=6)
        how = "EXITED"
    except subprocess.TimeoutExpired:
        shell_module._terminate_windows_process_tree(proc.pid)
        proc.kill()
        out, err = proc.communicate(timeout=10)
        how = "NEEDED-FORCE"
    return (
        f"\n=== [{name}] {how} after {time.monotonic() - t0:.2f}s rc={proc.returncode} popen_pid={proc.pid}\n"
        f"stop: {stop_note}\nstdout={out!r}\nstderr={err[-300:]!r}\nproc table before stop: {table}\n"
    )


def _ctrl_break(proc, bash):
    proc.send_signal(signal.CTRL_BREAK_EVENT)
    return "sent CTRL_BREAK_EVENT"


def _taskkill_no_f(proc, bash):
    return _run(["taskkill", "/PID", str(proc.pid), "/T"], bash)


def _msys_group_term(proc, bash):
    return _run([bash, "-c", GROUP_TERM], bash)


def _msys_kill_w(proc, bash):
    kill_exe = Path(bash).parent.parent / "usr" / "bin" / "kill.exe"
    return f"exists={kill_exe.is_file()} " + _run([str(kill_exe), "-TERM", "-W", str(proc.pid)], bash)


def test_probe_758_windows_graceful_stop_options():
    bash = _bash()
    console = ctypes.windll.kernel32.GetConsoleWindow()  # type: ignore[attr-defined]
    report = f"bash={bash} console_window={console}\n"
    for name, stop in [
        ("ctrl_break", _ctrl_break),
        ("taskkill_no_F", _taskkill_no_f),
        ("msys_group_term_via_proc", _msys_group_term),
        ("msys_kill_exe_W", _msys_kill_w),
    ]:
        report += _measure(name, bash, stop)
    pytest.fail("MEASUREMENT (deliberate failure to surface data):\n" + report)
