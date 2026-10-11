"""Behavioral tests for the generate-changelog workflow's PR linking and release summary.

``gather-commit-data`` runs through the real code node against a throwaway git repository;
only ``gh`` (the network boundary) is answered from fixtures. The LLM steps are not run here.
GH #741: the first ``(#N)`` of a squash subject — the issue — used to become the PR link.
"""

from __future__ import annotations

import json
import re
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
        "body": "## Summary\nOutputs need a source.\n\n## Tests\nOne.",
    },
    {"number": 12, "title": "Add retries", "body": "Implements Task 57."},
    {"number": 559, "title": "Task 164 decisions", "body": ""},
]
# `gh api repos/{repo}/issues/N` answers (exit code, stdout, stderr) — the endpoint serves issues and PRs alike.
OLDER_ITEMS = {
    30: {"number": 30, "title": "Old feature", "body": "", "pull_request": {"merged_at": "2026-01-02T00:00:00Z"}},
    31: {"number": 31, "title": "Closed without merging", "body": "", "pull_request": {"merged_at": None}},
    656: {"number": 656, "title": "Web UI: approve all remaining", "body": "An issue."},
}
API_ANSWERS = {n: (0, json.dumps(item), "") for n, item in OLDER_ITEMS.items()} | {
    9998: (1, "", "gh: This issue was deleted (HTTP 410)")
}
NOT_FOUND = (1, '{"message":"Not Found"}', "gh: Not Found (HTTP 404)")
FIXTURE_MESSAGES = [
    "fix(validation): require a source on every declared output (#628) (#649)",
    "docs(task-183): approval gates in loops (#656); spec refreshed by an architecture-fit read",
    "docs: spec for approve-all (#656)",
    "docs: spec for a typo'd reference (#9999)",
    "docs: note on a since-deleted issue (#9998)",
    "Merge pull request #12 from someone/retries\n\nAdd retries",
    "feat: old feature (#30)",
    "chore: closed attempt (#31)",
    "docs: post-merge reconcile for Task 164\n\nDecisions locked in (#559)",
]


def run_step(step_id: str, inputs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    ir = parse_markdown(CHANGELOG_WORKFLOW.read_text(encoding="utf-8")).ir
    step = next(n for n in ir["nodes"] if n["id"] == step_id)
    assert set(step["params"]["inputs"]) == set(inputs)
    node = PythonCodeNode()
    node.set_params({"code": step["params"]["code"], "inputs": inputs})
    shared: dict[str, Any] = {}
    return node.run(shared), shared


def gather(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, api_error: str = "") -> tuple[str, dict[str, Any]]:
    """Commit FIXTURE_MESSAGES after tag v0.1.0 and run gather-commit-data on them.

    ``api_error`` makes every ``gh api`` lookup fail with that stderr (an outage, not a 404).
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run([*GIT, *args], cwd=repo, capture_output=True, check=True)  # noqa: S603

    git("init", "-q", "-b", "main")
    git("commit", "-q", "--allow-empty", "-m", "init")
    git("tag", "v0.1.0")
    for message in FIXTURE_MESSAGES:
        git("commit", "-q", "--allow-empty", "-m", message)

    real_run = subprocess.run

    def fake_gh(argv: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[0] != "gh":
            return real_run(argv, *args, **kwargs)
        if argv[1:3] == ["repo", "view"]:
            return subprocess.CompletedProcess(argv, 0, "owner/repo\n", "")
        if argv[1:3] == ["pr", "list"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(RECENT_PRS), "")
        if argv[1] == "api" and argv[2].startswith("repos/owner/repo/issues/"):
            code, out, err = (
                (1, "", api_error) if api_error else API_ANSWERS.get(int(argv[2].rsplit("/", 1)[1]), NOT_FOUND)
            )
            return subprocess.CompletedProcess(argv, code, out, err)
        raise AssertionError(f"unexpected gh call: {argv}")

    monkeypatch.setattr(subprocess, "run", fake_gh)
    monkeypatch.chdir(repo)
    return run_step("gather-commit-data", {"tag": "v0.1.0", "to_ref": "HEAD"})


@pytest.fixture
def commits_by_subject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    action, shared = gather(tmp_path, monkeypatch)
    assert action == "default", shared.get("error")
    return {c["commit_message"].split("\n")[0]: c for c in shared["result"]}


def test_squash_commit_links_its_pr_not_the_issue_it_names(commits_by_subject: dict[str, dict[str, Any]]) -> None:
    commit = commits_by_subject["fix(validation): require a source on every declared output (#628) (#649)"]

    assert commit["pr_number"] == 649
    assert commit["pr_link"] == "https://github.com/owner/repo/pull/649"
    assert commit["pr_title"] == "fix(validation): require a source on every declared output (#628)"
    assert commit["pr_body"] == RECENT_PRS[0]["body"]
    assert commit["pr_summary"] == "Summary\nOutputs need a source.\n"
    assert commit["is_merge"] is False


@pytest.mark.parametrize(
    "subject",
    [
        "docs(task-183): approval gates in loops (#656); spec refreshed by an architecture-fit read",
        "docs: spec for approve-all (#656)",
        "docs: spec for a typo'd reference (#9999)",
        "docs: note on a since-deleted issue (#9998)",
        "chore: closed attempt (#31)",
        "docs: post-merge reconcile for Task 164",
    ],
    ids=["issue-mid-subject", "issue-trailing", "no-such-number", "deleted-issue", "unmerged-pr", "pr-in-body-only"],
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


def test_failed_pr_lookup_fails_the_step_instead_of_dropping_the_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    action, shared = gather(tmp_path, monkeypatch, api_error="gh: API rate limit exceeded (HTTP 403)")

    assert action == "error"
    assert re.search(
        r"Cannot check whether #\d+ is a merged PR: gh: API rate limit exceeded \(HTTP 403\) — re-run once gh can reach GitHub",
        shared["error"],
    )


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
            "entries": [{"context": {"pr_link": "https://github.com/o/r/pull/1"}}] * 16
            + [{"context": {"pr_link": ""}}] * 9,
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
    assert "25 entries, 16 with PR links" in shared["result"]
    assert "31 skipped changes, 3 task reviews included — review before committing" in shared["result"]
