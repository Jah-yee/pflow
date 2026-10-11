"""Examples capture: run every example listed in manifest.json, normalize its JSON output, store or diff.

    uv run python .taskmaster/tasks/task_170/implementation/examples-baseline/capture.py          # capture
    uv run python .taskmaster/tasks/task_170/implementation/examples-baseline/capture.py --check  # diff vs stored

`manifest.json` is the case list: each entry names an example and its CLI params; capture
fills in `exit_code` and `output`. Each example runs as
`pflow --output-format json <file> [k=v ...]` (the pflow installed beside this interpreter)
in a fresh HOME (no memo cache, no settings, no traces leaking between runs), a fresh cwd
(file-writing examples write there) and an empty stdin (pflow reads a piped stdin, so an
inherited one would change every result). Normalized fields: every `duration_ms` and
`node_timings` value → 0; every UUID (execution ids) → `<UUID>`; the repo root → `<REPO>`;
the run's cwd → `<CWD>`; the run's HOME → `<HOME>`; the OS name and machine (`uname -s`/`-m`) →
`<OS>`/`<ARCH>`, so a capture recorded on macOS matches on CI's Linux runner.

Exit codes: 0 = every example matches, 1 = drift (a unified diff per differing example),
2 = harness error (the list is empty, a listed example is missing, or a stored capture has no
manifest entry).
"""

from __future__ import annotations

import difflib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
MANIFEST = HERE / "manifest.json"

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_PLATFORM = ((re.compile(rf"\b{re.escape(platform.system())}\b"), "<OS>"),
             (re.compile(rf"\b{re.escape(platform.machine())}\b"), "<ARCH>"))


def _normalize(value: Any, key: str | None, subs: tuple[tuple[str, str], ...]) -> Any:
    if isinstance(value, dict):
        if key == "node_timings":
            return {k: 0 for k in value}
        return {k: _normalize(v, k, subs) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v, key, subs) for v in value]
    if key is not None and key.endswith("duration_ms") and isinstance(value, (int, float)):
        return 0
    if isinstance(value, str):
        for old, new in subs:
            value = value.replace(old, new)
        value = _UUID.sub("<UUID>", value)
        for pattern, placeholder in _PLATFORM:
            value = pattern.sub(placeholder, value)
    return value


def run_one(pflow: str, example: str, params: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="t170-home-") as home, tempfile.TemporaryDirectory(
        prefix="t170-cwd-"
    ) as cwd:
        # Drop inherited PFLOW_* behavior switches (e.g. PFLOW_TEMPLATE_RESOLUTION_MODE,
        # PFLOW_MAX_NODE_VISITS) so a caller's shell cannot change the outputs; keep
        # PFLOW_BASH, which only locates bash on Windows.
        env = {k: v for k, v in os.environ.items() if not k.startswith("PFLOW_") or k == "PFLOW_BASH"}
        env.update({"HOME": home, "USERPROFILE": home})
        env.pop("PYTEST_CURRENT_TEST", None)
        args = [pflow, "--output-format", "json", str(REPO / example)]
        args += [f"{k}={v}" for k, v in params.items()]
        proc = subprocess.run(  # noqa: S603
            args,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        subs = ((str(Path(cwd).resolve()), "<CWD>"), (cwd, "<CWD>"), (str(Path(home).resolve()), "<HOME>"),
                (home, "<HOME>"), (str(REPO), "<REPO>"))
        try:
            payload: Any = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"__unparsed_stdout__": proc.stdout}
        text = json.dumps(_normalize(payload, None, subs), indent=2, sort_keys=True) + "\n"
        return proc.returncode, text


def _slug(example: str) -> str:
    return example.removeprefix("examples/").removesuffix(".pflow.md").replace("/", "__") + ".json"


def _harness_errors(entries: list[dict[str, Any]], check: bool) -> list[str]:
    """What would make the run meaningless: an empty list checks nothing, a missing example would be
    captured as pflow's file-not-found document, a stale capture would never be compared."""
    errors = [] if entries else ["manifest.json lists no examples"]
    errors += [f"listed example does not exist: {e['example']}" for e in entries if not (REPO / e["example"]).is_file()]
    if check:
        listed = {_slug(e["example"]) for e in entries}
        errors += [
            f"stored capture has no manifest entry: {path.name}"
            for path in sorted(HERE.glob("*.json"))
            if path != MANIFEST and path.name not in listed
        ]
    return errors


def main() -> int:
    check = "--check" in sys.argv
    entries: list[dict[str, Any]] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = _harness_errors(entries, check)
    pflow = shutil.which("pflow", path=str(Path(sys.executable).parent))
    if pflow is None:
        errors.append(f"no pflow executable beside {sys.executable}")
    if errors or pflow is None:
        for error in errors:
            print(f"harness error: {error}", file=sys.stderr)
        return 2
    failures = 0
    for entry in entries:
        example = entry["example"]
        code, text = run_one(pflow, example, entry.get("params", {}))
        out = HERE / _slug(example)
        if check:
            old = out.read_text(encoding="utf-8") if out.is_file() else ""
            if old != text or entry.get("exit_code") != code:
                failures += 1
                print(f"DIFF {example} (exit {entry.get('exit_code')} -> {code})")
                sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), text.splitlines(True), "before", "after"))
            else:
                print(f"same {example}")
        else:
            out.write_text(text, encoding="utf-8")
            entry.update(exit_code=code, output=out.name)
            print(f"captured {example} (exit {code})")
    if not check:
        MANIFEST.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
        listed = {entry["output"] for entry in entries}
        for path in HERE.glob("*.json"):
            if path != MANIFEST and path.name not in listed:
                path.unlink()
                print(f"removed stale capture {path.name}")
    print(f"{len(entries)} examples, {failures} differing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
