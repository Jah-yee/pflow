from importlib.metadata import PackageNotFoundError, distribution, version

_DISTRIBUTION = "pflow-cli"


def get_version() -> str:
    """The installed package version — the one every version comparison uses.

    Never carries a commit suffix: the registry compares it to decide whether to
    rescan core nodes, and a per-commit value would rescan on every commit.
    """
    try:
        return version(_DISTRIBUTION)
    except PackageNotFoundError:
        return "0.0.0-dev"


def get_display_version() -> str:
    """The version ``pflow --version`` prints — display only, never compared.

    An editable install reports ``pyproject.toml``'s version however far the
    checkout is past that release, so the checkout's commit is appended as a
    PEP 440 local label: ``0.16.0+g93798a80``, or ``0.16.0+g93798a80.dirty``
    with uncommitted tracked changes. Any other install, or any git failure,
    prints the plain package version.
    """
    package_version = get_version()
    source_dir = _editable_source_dir()
    commit = _git_commit(source_dir) if source_dir else None
    return f"{package_version}+g{commit}" if commit else package_version


def _editable_source_dir() -> str | None:
    """The checkout an editable install points at (PEP 610 ``direct_url.json``), else None."""
    import json
    from urllib.parse import urlparse
    from urllib.request import url2pathname

    try:
        direct_url = json.loads(distribution(_DISTRIBUTION).read_text("direct_url.json") or "{}")
    except (PackageNotFoundError, ValueError):
        return None
    if not direct_url.get("dir_info", {}).get("editable"):
        return None
    url = urlparse(direct_url.get("url", ""))
    return url2pathname(url.path) if url.scheme == "file" else None


def _git_commit(source_dir: str) -> str | None:
    """Short HEAD commit of ``source_dir`` (``.dirty``-marked), or None when git can't say.

    ``describe --always`` with every tag excluded is ``rev-parse --short HEAD``
    plus the dirty check in one process; it resolves linked worktrees, detached
    HEAD and packed refs the way reading ``.git/HEAD`` by hand would not.

    The lookup is pinned to ``source_dir`` itself: inherited ``GIT_*`` variables
    are dropped (a git hook exports ``GIT_DIR``/``GIT_INDEX_FILE`` for ITS repo)
    and the parent is a ceiling, so a source that is not its own repo never
    reports an enclosing repo's commit.
    """
    import os
    import subprocess

    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(os.path.realpath(source_dir))
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty=.dirty", "--exclude=*"],  # noqa: S607 - fixed executable resolved from PATH
            cwd=source_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
