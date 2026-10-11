"""Behavioral tests for the generate-changelog workflow's PR linking and release summary.

``gather-commit-data`` runs through the real code node against a throwaway git repository;
only ``gh`` (the network boundary) is answered from fixtures. The LLM steps are not run here.
GH #741: the first ``(#N)`` of a squash subject — the issue — used to become the PR link.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from pflow.core.markdown_parser import parse_markdown
from pflow.nodes.python.python_code import PythonCodeNode

CHANGELOG_WORKFLOW = (
    Path(__file__).resolve().parents[2] / "examples/real-workflows/generate-changelog/workflow.pflow.md"
)
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]

# The 200 most recent merged PRs, as `gh pr list` returns them.
RECENT_PRS = [
    {
        "number": 649,
        "title": "fix(validation): require a source on every declared output (#628)",
        "body": "## Summary\nOutputs need a source.",
    },
    {"number": 12, "title": "Add retries", "body": "Implements Task 57."},
    {"number": 559, "title": "Task 164 decisions", "body": ""},
]
# Merged, but older than the `gh pr list` window — only `gh pr view` finds it.
OLD_PR = {"number": 30, "title": "Old feature", "body": "", "state": "MERGED"}
UNMERGED_PR = {"number": 31, "title": "Closed without merging", "body": "", "state": "CLOSED"}


def run_step(step_id: str, inputs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    ir = parse_markdown(CHANGELOG_WORKFLOW.read_text(encoding="utf-8")).ir
    step = next(n for n in ir["nodes"] if n["id"] == step_id)
    assert set(step["params"]["inputs"]) == set(inputs)
    node = PythonCodeNode()
    node.set_params({"code": step["params"]["code"], "inputs": inputs})
    shared: dict[str, Any] = {}
    return node.run(shared), shared


@pytest.fixture
def commits_by_subject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    """Commit a fixture history after tag v0.1.0, run gather-commit-data on it, key results by subject."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run([*GIT, *args], cwd=repo, capture_output=True, check=True)  # noqa: S603

    git("init", "-q", "-b", "main")
    git("commit", "-q", "--allow-empty", "-m", "init")
    git("tag", "v0.1.0")
    for message in [
        "fix(validation): require a source on every declared output (#628) (#649)",
        "docs(task-183): approval gates in loops (#656); spec refreshed by an architecture-fit read",
        "docs: spec for approve-all (#656)",
        "Merge pull request #12 from someone/retries\n\nAdd retries",
        "feat: old feature (#30)",
        "chore: closed attempt (#31)",
        "docs: post-merge reconcile for Task 164\n\nDecisions locked in (#559).",
    ]:
        git("commit", "-q", "--allow-empty", "-m", message)

    real_run = subprocess.run

    def fake_gh(argv: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[0] != "gh":
            return real_run(argv, *args, **kwargs)
        if argv[1:3] == ["repo", "view"]:
            return subprocess.CompletedProcess(argv, 0, "owner/repo\n", "")
        if argv[1:3] == ["pr", "list"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(RECENT_PRS), "")
        if argv[1:3] == ["pr", "view"]:
            pr = {p["number"]: p for p in (OLD_PR, UNMERGED_PR)}.get(int(argv[3]))
            if pr is None:
                return subprocess.CompletedProcess(
                    argv, 1, "", f"Could not resolve to a PullRequest with the number of {argv[3]}."
                )
            return subprocess.CompletedProcess(argv, 0, json.dumps(pr), "")
        raise AssertionError(f"unexpected gh call: {argv}")

    monkeypatch.setattr(subprocess, "run", fake_gh)
    monkeypatch.chdir(repo)
    action, shared = run_step("gather-commit-data", {"tag": "v0.1.0", "to_ref": "HEAD"})
    assert action == "default", shared.get("error")
    return {c["commit_message"].split("\n")[0]: c for c in shared["result"]}


def test_squash_commit_links_its_pr_not_the_issue_it_names(commits_by_subject: dict[str, dict[str, Any]]) -> None:
    commit = commits_by_subject["fix(validation): require a source on every declared output (#628) (#649)"]

    assert commit["pr_number"] == 649
    assert commit["pr_link"] == "https://github.com/owner/repo/pull/649"
    assert commit["pr_title"] == "fix(validation): require a source on every declared output (#628)"
    assert commit["pr_summary"].startswith("Summary")
    assert commit["is_merge"] is False


@pytest.mark.parametrize(
    "subject",
    [
        "docs(task-183): approval gates in loops (#656); spec refreshed by an architecture-fit read",
        "docs: spec for approve-all (#656)",
        "chore: closed attempt (#31)",
        "docs: post-merge reconcile for Task 164",
    ],
    ids=["issue-mid-subject", "issue-trailing", "unmerged-pr", "pr-in-body-only"],
)
def test_commit_without_a_merged_pr_gets_no_pr_link(
    commits_by_subject: dict[str, dict[str, Any]], subject: str
) -> None:
    commit = commits_by_subject[subject]

    assert (commit["pr_number"], commit["pr_link"], commit["pr_title"]) == (None, "", "")


def test_merged_pr_older_than_the_list_window_is_still_linked(commits_by_subject: dict[str, dict[str, Any]]) -> None:
    commit = commits_by_subject["feat: old feature (#30)"]

    assert commit["pr_link"] == "https://github.com/owner/repo/pull/30"
    assert commit["pr_title"] == "Old feature"


def test_merge_commit_links_its_pr_and_takes_the_task_from_the_pr_body(
    commits_by_subject: dict[str, dict[str, Any]],
) -> None:
    commit = commits_by_subject["Merge pull request #12 from someone/retries"]

    assert commit["pr_link"] == "https://github.com/owner/repo/pull/12"
    assert commit["pr_title"] == "Add retries"
    assert commit["is_merge"] is True
    assert commit["task_number"] == 57


def test_release_summary_names_what_the_task_review_count_counts() -> None:
    action, shared = run_step(
        "create-summary",
        {
            "entries": [{}] * 25,
            "skipped": [{}] * 31,
            "task_reviews": {"118": "review", "181": "review", "183": "review"},
            "next_version": "v0.16.0",
            "bump_type": "minor",
            "date_iso": "2026-10-11",
            "warnings": [],
            "changelog_path": "CHANGELOG.md",
            "mintlify_path": "docs/changelog.mdx",
            "context_path": "releases/v0.16.0-context.md",
        },
    )

    assert action == "default"
    assert "31 skipped changes, 3 task reviews included — review before committing" in shared["result"]
