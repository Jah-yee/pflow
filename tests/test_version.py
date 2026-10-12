"""The version helpers in ``pflow/__init__.py`` (issue #812).

``get_version()`` is the package version every comparison uses;
``get_display_version()`` is what ``pflow --version`` prints, with the
checkout's commit appended on an editable install. Each test installs a real
fake ``pflow-cli`` dist-info (version 9.9.9) at the front of ``sys.path`` and
points its ``direct_url.json`` at a real throwaway git repo — no metadata or
git mocking.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import click.testing
import pytest

import pflow
from pflow.cli.main import main
from pflow.registry.registry import Registry


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - argv list, never a shell
        ["git", *args],  # noqa: S607 - fixed executable resolved from PATH
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with two commits."""
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(var, "t")
    for var in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(var, "t@example.com")
    path = tmp_path / "checkout"
    path.mkdir()
    _git(path, "init", "-q")
    (path / "f.txt").write_text("one\n", encoding="utf-8")
    _git(path, "add", "f.txt")
    _git(path, "commit", "-qm", "one")
    _git(path, "tag", "-a", "v9.9.9", "-m", "release")  # a tag at HEAD~1 must not leak into the suffix
    (path / "f.txt").write_text("two\n", encoding="utf-8")
    _git(path, "commit", "-qam", "two")
    return path


@pytest.fixture
def install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, object] | None], None]:
    """Shadow the real pflow-cli with a 9.9.9 dist-info carrying ``direct_url`` (None = no file)."""

    def _install(direct_url: dict[str, object] | None) -> None:
        dist_info = tmp_path / "site" / "pflow_cli-9.9.9.dist-info"
        dist_info.mkdir(parents=True)
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: pflow-cli\nVersion: 9.9.9\n", encoding="utf-8"
        )
        if direct_url is not None:
            (dist_info / "direct_url.json").write_text(json.dumps(direct_url), encoding="utf-8")
        monkeypatch.syspath_prepend(str(dist_info.parent))

    return _install


@pytest.fixture
def git_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Spy (records, then delegates to the real ``subprocess.run``): argv of every git spawn from here on."""
    calls: list[list[str]] = []
    real_run = subprocess.run

    def _spy(args, *rest, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and args[:1] == ["git"]:
            calls.append(args)
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    return calls


def _editable(source: Path) -> dict[str, object]:
    return {"url": source.as_uri(), "dir_info": {"editable": True}}


def test_editable_install_appends_short_commit_and_comparisons_stay_plain(repo: Path, install) -> None:
    install(_editable(repo))

    assert pflow.get_display_version() == f"9.9.9+g{_git(repo, 'rev-parse', '--short', 'HEAD')}"
    # The registry's staleness check compares this: a suffix there would rescan core nodes every commit.
    assert Registry._get_version() == "9.9.9"


def test_uncommitted_tracked_change_is_marked_dirty(repo: Path, install) -> None:
    install(_editable(repo))
    (repo / "untracked.txt").write_text("x", encoding="utf-8")
    assert not pflow.get_display_version().endswith(".dirty")  # untracked files don't count

    (repo / "f.txt").write_text("edited\n", encoding="utf-8")

    assert pflow.get_display_version() == f"9.9.9+g{_git(repo, 'rev-parse', '--short', 'HEAD')}.dirty"


def test_linked_worktree_on_detached_head_with_packed_refs(repo: Path, tmp_path: Path, install) -> None:
    """The shapes hand-reading ``.git/HEAD`` gets wrong: ``.git`` is a file, HEAD is a bare sha, refs are packed."""
    _git(repo, "pack-refs", "--all")
    worktree = tmp_path / "linked"
    _git(repo, "worktree", "add", "-q", "--detach", str(worktree), "HEAD~1")
    assert (worktree / ".git").is_file()
    install(_editable(worktree))

    assert pflow.get_display_version() == f"9.9.9+g{_git(worktree, 'rev-parse', '--short', 'HEAD')}"


@pytest.mark.parametrize(
    "direct_url",
    [
        pytest.param(lambda repo: None, id="index-install-no-direct-url"),
        pytest.param(lambda repo: {"url": repo.as_uri(), "dir_info": {}}, id="local-dir-not-editable"),
        pytest.param(
            lambda repo: {"url": repo.as_uri(), "archive_info": {"hashes": {}}},
            id="wheel-from-path",
        ),
    ],
)
def test_non_editable_install_prints_plain_version_without_running_git(
    repo: Path, install, git_calls: list[list[str]], direct_url
) -> None:
    install(direct_url(repo))  # the url names a real repo, so only the install kind stops git

    assert pflow.get_display_version() == "9.9.9"
    assert git_calls == []


@pytest.mark.parametrize("failure", ["git-not-on-path", "not-a-repo-but-inside-one", "checkout-moved"])
def test_git_that_cannot_answer_prints_plain_version(
    repo: Path, tmp_path: Path, install, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    source = repo
    if failure == "git-not-on-path":
        empty_bin = tmp_path / "empty-bin"
        empty_bin.mkdir()
        monkeypatch.setenv("PATH", str(empty_bin))
    elif failure == "not-a-repo-but-inside-one":
        source = repo / "vendored-copy"  # git must not walk up and report the enclosing repo's commit
        source.mkdir()
    else:
        source = tmp_path / "gone"
    install(_editable(source))

    assert pflow.get_display_version() == "9.9.9"


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_symlinked_source_that_is_not_a_repo_prints_plain_version(repo: Path, tmp_path: Path, install) -> None:
    """The ceiling is taken from the resolved path: git resolves its cwd, so a symlink's own parent sits too high."""
    vendored = repo / "vendored-copy"
    vendored.mkdir()
    link = tmp_path / "link-to-vendored"
    link.symlink_to(vendored, target_is_directory=True)
    install(_editable(link))

    assert pflow.get_display_version() == "9.9.9"


def test_inherited_git_dir_does_not_redirect_the_lookup(
    repo: Path, tmp_path: Path, install, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git hook exports GIT_DIR for its own repo; ``pflow --version`` run there still names pflow's checkout."""
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q")
    _git(other, "commit", "-q", "--allow-empty", "-m", "other")
    install(_editable(repo))
    expected = f"9.9.9+g{_git(repo, 'rev-parse', '--short', 'HEAD')}"
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))

    assert pflow.get_display_version() == expected


def test_version_flag_prints_the_display_version_at_invocation(repo: Path, install, git_calls: list[list[str]]) -> None:
    """The CLI module was imported long before this install: the version is read when the flag runs."""
    install(_editable(repo))
    expected = f"pflow version 9.9.9+g{_git(repo, 'rev-parse', '--short', 'HEAD')}\n"
    git_calls.clear()  # forget the test's own rev-parse

    result = click.testing.CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert result.output == expected
    assert len(git_calls) == 1


def test_importing_the_cli_and_running_a_command_never_runs_git(repo: Path, tmp_path: Path, install) -> None:
    """A fresh interpreter, because import-time work is invisible once this process has imported the CLI.

    ``click.version_option(version=...)`` computes its value at import — that shape
    would run git on every command of an editable install.
    """
    install(_editable(repo))
    probe = (
        "import subprocess, sys\n"
        f"sys.path.insert(0, {str(tmp_path / 'site')!r})\n"
        "calls, real_run = [], subprocess.run\n"
        "def spy(args, *rest, **kwargs):\n"
        "    if isinstance(args, list) and args[:1] == ['git']:\n"
        "        calls.append(args)\n"
        "    return real_run(args, *rest, **kwargs)\n"
        "subprocess.run = spy\n"
        "from pflow.cli.main import main\n"
        "main(['guide'], standalone_mode=False)\n"
        "assert calls == [], calls\n"
    )

    result = subprocess.run(  # noqa: S603 - argv list, never a shell
        [sys.executable, "-c", probe], stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", check=False
    )

    assert result.returncode == 0, result.stderr
