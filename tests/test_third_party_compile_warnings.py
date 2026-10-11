"""No installed runtime dependency emits a compile-time warning under this Python.

Python emits compile-time warnings (e.g. `SyntaxWarning`) only when it compiles a
module with no cached bytecode. Installers like uv skip install-time compilation by
default, so a fresh environment compiles third-party code on first import, and any
such warning prints on pflow's stderr once, where an agent reads it as pflow output.
The registry's first core-node scan imports most of the dependency tree (the agent
node pulls in claude-agent-sdk, mcp and anyio), so a first run or dry-run is enough.

This test compiles every `.py` file of every distribution in pflow's runtime
dependency closure, without writing bytecode, and fails on any warning. It runs on
every CI Python, so a lock that pins a dependency with a warning goes red on the
version that introduces it. The rule for a red run lives in `src/pflow/cli/CLAUDE.md`.
"""

import warnings
from importlib.metadata import Distribution, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT_DISTRIBUTION = "pflow-cli"
_TEST_DIRS = {"test", "tests"}


def _requirements(dist: Distribution, extras: set[str]) -> list[Requirement]:
    """`dist`'s requirements that apply to this interpreter with `extras` requested."""
    applicable = []
    for spec in dist.requires or []:
        req = Requirement(spec)
        if req.marker is None or any(req.marker.evaluate({"extra": extra}) for extra in extras | {""}):
            applicable.append(req)
    return applicable


def _runtime_closure() -> dict[str, Distribution]:
    """Every distribution pflow's base install pulls in, keyed by canonical name, pflow excluded.

    Walks (distribution, extra) pairs so a dependency reached first without an extra and later
    with one (`mcp` vs `mcp[cli]`) still contributes the extra's requirements. A requirement whose
    marker holds here but is not installed raises: the environment is broken, not exempt.
    """
    pending = _requirements(distribution(ROOT_DISTRIBUTION), set())
    closure: dict[str, Distribution] = {}
    walked: set[tuple[str, str]] = set()
    while pending:
        req = pending.pop()
        name = canonicalize_name(req.name)
        new_extras = {extra for extra in req.extras | {""} if (name, extra) not in walked}
        if not new_extras:
            continue
        walked.update((name, extra) for extra in new_extras)
        dist = closure.get(name) or distribution(req.name)
        closure[name] = dist
        pending.extend(_requirements(dist, new_extras - {""}))
    return closure


def _compile_warnings(dist: Distribution) -> list[str]:
    """`path:line Category: message` for each warning compiling `dist`'s Python files emits."""
    # No RECORD means nothing to scan; failing beats passing a dependency nobody checked.
    assert dist.files is not None, f"{dist.name} has no file inventory (RECORD); cannot scan it"
    found: list[str] = []
    for file in dist.files:
        # A dependency's own test suite is never imported by pflow, so it cannot reach stderr
        # (pywin32 ships one with a 3.14 SyntaxWarning).
        if file.suffix != ".py" or _TEST_DIRS & set(file.parts[:-1]):
            continue
        path = Path(str(dist.locate_file(file)))
        source = path.read_bytes()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                compile(source, str(path), "exec", dont_inherit=True)
            except SyntaxError:
                continue  # A file this Python cannot compile is never imported, so it cannot warn either.
        found.extend(f"{path}:{w.lineno} {w.category.__name__}: {w.message}" for w in caught)
    return found


def test_runtime_closure_covers_the_dependency_tree() -> None:
    """Guard the walk itself: an empty or truncated closure would pass the real test vacuously."""
    closure = _runtime_closure()
    # Direct deps, a transitive-only dep (httpcore via httpx), and an extra-gated one (typer via mcp[cli]).
    assert {"click", "mcp", "claude-agent-sdk", "anyio", "httpcore", "typer"} <= closure.keys()


def test_no_runtime_dependency_emits_a_compile_time_warning() -> None:
    found = [line for dist in _runtime_closure().values() for line in _compile_warnings(dist)]
    assert not found, (
        "These third-party compile-time warnings would print on pflow's stderr the first time a "
        "fresh environment imports them. Upgrade the dependency in the lock to a fixed release "
        "(`uv lock --upgrade-package <name>`); see src/pflow/cli/CLAUDE.md for the rule.\n" + "\n".join(found)
    )
