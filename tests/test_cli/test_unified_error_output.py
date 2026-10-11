"""Tests for unified CLI error output pipeline (Task 137).

Validates that error_output.py produces a consistent JSON shape for ALL error
categories, that structured exception fields survive into the unified JSON,
and that core regressions (plain text leaking into JSON mode, error field as
dict instead of string) are covered.

Focus: shape correctness and field preservation, not exact error messages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from pflow.cli.error_output import format_error_json
from pflow.cli.main import main
from tests.shared.markdown_utils import write_workflow_file


def _exception_to_errors(exception: Exception) -> tuple[str, list[dict[str, Any]]]:
    """Test helper: the (summary, errors) pair the JSON failure document carries for an exception."""
    document = format_error_json(exception=exception)
    return document["error"], document["errors"]


# ---------------------------------------------------------------------------
# Valid error categories
# ---------------------------------------------------------------------------
# Categories from exception_to_diagnostics (pre-execution exceptions)
_PRE_EXECUTION_CATEGORIES = {
    "validation",
    "compilation",
    "runtime",
    "parse_error",
    "not_found",
    "cli",
    "mcp",
    "max_visits",
    "file_not_found",
    "permission_denied",
    "unknown",
}
# Categories from executor_service._determine_error_category (post-execution errors)
_POST_EXECUTION_CATEGORIES = {
    "execution_failure",
    "api_validation",
    "template_error",
}
VALID_CATEGORIES = frozenset(_PRE_EXECUTION_CATEGORIES | _POST_EXECUTION_CATEGORIES)

# Old fields that must NOT appear in unified output
FORBIDDEN_FIELDS = frozenset({
    "is_error",
    "validation_errors",
    "metadata",
    "failed_node",
    "checkpoint",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json_output(result: Any) -> dict[str, Any]:
    """Parse JSON from CLI runner output, raising a clear error on failure."""
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Expected valid JSON output but got:\n{result.stdout[:500]}") from exc


def _assert_unified_shape(output: dict[str, Any]) -> None:
    """Assert the unified error JSON shape is correct."""
    # Top-level required fields
    assert output["success"] is False, "success must be False for errors"
    assert output["status"] == "failed", f"status must be 'failed', got {output['status']!r}"
    assert isinstance(output["error"], str), (
        f"error must be a string, got {type(output['error']).__name__}: {output['error']!r}"
    )
    assert isinstance(output["errors"], list), "errors must be a list"
    assert len(output["errors"]) > 0, "errors list must not be empty"

    # Each error entry must have message and category, in the same form diagnostics[] carries it
    for i, err in enumerate(output["errors"]):
        assert isinstance(err, dict), f"errors[{i}] must be a dict"
        assert "message" in err, f"errors[{i}] missing 'message'"
        category = err["context"]["category"]
        assert category in VALID_CATEGORIES, f"errors[{i}] category = {category!r} not in valid categories"
        assert err in output["diagnostics"], f"errors[{i}] differs from its diagnostics[] entry"

    # Workflow metadata
    assert isinstance(output["workflow"], dict), "workflow must be a dict"
    assert "action" in output["workflow"], "workflow must have 'action' key"

    # Old fields must NOT appear
    for field in FORBIDDEN_FIELDS:
        assert field not in output, f"Old field '{field}' must not appear in unified output"


# ---------------------------------------------------------------------------
# TestUnifiedErrorJsonShape
# ---------------------------------------------------------------------------


class TestUnifiedErrorJsonShape:
    """Each test triggers a specific error via the CLI with --output-format json
    and validates the unified JSON shape."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Passing a nonexistent .pflow.md path produces not_found category."""
        runner = CliRunner(mix_stderr=False)
        nonexistent = str(tmp_path / "does-not-exist.pflow.md")

        result = runner.invoke(main, ["--output-format", "json", nonexistent])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        _assert_unified_shape(output)

        assert output["errors"][0]["context"]["category"] == "not_found"

    def test_parse_error(self, tmp_path: Path) -> None:
        """A malformed .pflow.md file (no ## Steps) produces parse_error category."""
        bad_file = tmp_path / "bad.pflow.md"
        bad_file.write_text("# My Workflow\n\nSome description but no steps section.\n", encoding="utf-8")

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--output-format", "json", str(bad_file)])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        _assert_unified_shape(output)

        assert output["errors"][0]["context"]["category"] == "parse_error"

    def test_validation_error(self, tmp_path: Path) -> None:
        """A workflow with an unknown node type produces a validation error."""
        workflow = {
            "nodes": [
                {
                    "id": "bad-node",
                    "type": "completely-nonexistent-node-type-xyz",
                    "params": {},
                },
            ],
            "edges": [],
        }
        workflow_path = tmp_path / "validation-error.pflow.md"
        write_workflow_file(workflow, workflow_path)

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        _assert_unified_shape(output)

        # Should be a validation or compilation error about unknown node type
        categories = {err["context"]["category"] for err in output["errors"]}
        assert categories & {"validation", "compilation"}, (
            f"Expected validation or compilation error, got categories: {categories}"
        )

    def test_execution_error(self, tmp_path: Path) -> None:
        """A workflow with 'exit 1' shell command produces unified error with execution key."""
        workflow = {
            "nodes": [
                {"id": "fail-step", "type": "shell", "params": {"command": "exit 1"}},
            ],
            "edges": [],
        }
        workflow_path = tmp_path / "exec-error.pflow.md"
        write_workflow_file(workflow, workflow_path)

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        _assert_unified_shape(output)

        # Execution errors should include the execution key with step info
        assert "execution" in output, "execution key should be present for runtime errors"

    def test_json_extension_error(self, tmp_path: Path) -> None:
        """Passing a .json file path produces not_found category (migration message)."""
        runner = CliRunner(mix_stderr=False)
        json_path = str(tmp_path / "old-format.json")

        result = runner.invoke(main, ["--output-format", "json", json_path])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        _assert_unified_shape(output)

        assert output["errors"][0]["context"]["category"] == "not_found"


# ---------------------------------------------------------------------------
# TestStructuredFieldPreservation
# ---------------------------------------------------------------------------


class TestStructuredFieldPreservation:
    """Tests that structured exception fields survive into the unified JSON errors list."""

    def test_exception_to_errors_max_node_visits(self) -> None:
        """MaxNodeVisitsError fields (node_id, visit_count, max_visits) survive."""
        from pflow.core.exceptions import MaxNodeVisitsError

        exc = MaxNodeVisitsError(node_id="loop-node", visit_count=100, max_visits=50)
        summary, errors = _exception_to_errors(exc)

        assert len(errors) == 1
        err = errors[0]
        assert err["node_id"] == "loop-node"
        assert err["context"] == {"category": "max_visits", "visit_count": 100, "max_visits": 50}
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_exception_to_errors_validation_error(self) -> None:
        """IR schema ValidationError fields (path, suggestions) survive."""
        from pflow.core.exceptions import SchemaValidationError

        exc = SchemaValidationError(
            message="Node type 'foo' is not registered",
            path="nodes[0].type",
            suggestion="Did you mean 'file'?",
        )
        _summary, errors = _exception_to_errors(exc)

        assert len(errors) == 1
        err = errors[0]
        assert err["context"]["category"] == "validation"
        assert err["context"]["path"] == "nodes[0].type"
        # suggestion is now a list: suggestions=["Did you mean 'file'?"]
        assert "suggestions" in err, f"Expected 'suggestions' field, got keys: {list(err.keys())}"
        assert "Did you mean 'file'?" in err["suggestions"]
        assert "title" in err
        assert "foo" in err["message"]

    def test_exception_to_errors_workflow_not_found(self) -> None:
        """WorkflowNotFoundError with similar names produces suggestions field."""
        from pflow.core.exceptions import WorkflowNotFoundError

        exc = WorkflowNotFoundError(
            workflow_name="my-workflo",
            similar_names=["my-workflow", "my-workflow-v2"],
        )
        _summary, errors = _exception_to_errors(exc)

        assert len(errors) == 1
        err = errors[0]
        assert err["context"]["category"] == "not_found"
        assert "title" in err
        # suggestions is now a list; similar_names are in context, not suggestions
        assert "suggestions" in err, f"Expected 'suggestions' field, got keys: {list(err.keys())}"
        # The similar_names are available in context for rendering
        assert err["context"]["similar_names"] == ["my-workflow", "my-workflow-v2"]

    def test_missing_required_input_preserves_path_and_suggestion(self, tmp_path: Path) -> None:
        """Missing required input produces JSON with path and suggestion fields.

        This is the end-to-end test for THE core bug this task prevents:
        prepare_inputs() returns (msg, path, suggestion) tuples that must survive
        through WorkflowValidationError → _exception_to_errors → JSON output.
        If anyone breaks the tuple unpacking, these fields silently vanish.
        """
        write_workflow_file(
            {
                "inputs": {"data": {"type": "string", "required": True}},
                "nodes": [
                    {"id": "n1", "type": "shell", "params": {"command": 'echo "$DATA"', "env": {"DATA": "${data}"}}}
                ],
                "edges": [],
            },
            tmp_path / "test.pflow.md",
        )

        runner = CliRunner(mix_stderr=False)
        # Invoke WITHOUT providing the required "data" parameter
        result = runner.invoke(main, ["--output-format", "json", str(tmp_path / "test.pflow.md")])

        assert result.exit_code == 1
        output = _parse_json_output(result)
        assert output["success"] is False
        assert len(output["errors"]) > 0

        # THE critical assertion: path survives from prepare_inputs() tuples
        err = output["errors"][0]
        assert err["context"]["category"] == "validation"
        assert "data" in err["message"].lower(), f"Error should mention the missing input 'data': {err['message']}"
        assert "path" in err["context"], f"Missing 'path' field — tuple unpacking broke: {err}"
        assert "inputs" in err["context"]["path"], f"Path should reference the input: {err['context']['path']}"


# ---------------------------------------------------------------------------
# TestCoreRegression
# ---------------------------------------------------------------------------


class TestCoreRegression:
    """Regression tests for the core bugs this task fixes."""

    def test_workflow_not_found_produces_json(self, tmp_path: Path) -> None:
        """Passing a nonexistent workflow with --output-format json must produce valid JSON.

        Regression: before the unified pipeline, WorkflowNotFoundError was caught
        and displayed as plain text even in JSON mode.
        """
        runner = CliRunner(mix_stderr=False)
        nonexistent = str(tmp_path / "nonexistent-workflow.pflow.md")

        result = runner.invoke(main, ["--output-format", "json", nonexistent])

        assert result.exit_code != 0
        # This is the critical assertion: output must be valid JSON, not plain text
        output = _parse_json_output(result)
        assert output["success"] is False

    def test_error_field_is_string_not_dict(self, tmp_path: Path) -> None:
        """The top-level 'error' field must be a string, not a dict.

        Regression: before unification, the error field was sometimes a dict
        with 'type' and 'message' keys instead of a flat string.
        """
        runner = CliRunner(mix_stderr=False)
        nonexistent = str(tmp_path / "nonexistent.pflow.md")

        result = runner.invoke(main, ["--output-format", "json", nonexistent])

        assert result.exit_code != 0
        output = _parse_json_output(result)
        assert isinstance(output["error"], str), (
            f"error field must be a string, got {type(output['error']).__name__}: {output['error']!r}"
        )
        # Must not be a dict (the old shape)
        assert not isinstance(output["error"], dict)


# ---------------------------------------------------------------------------
# TestOutputResolutionFailure (#754)
# ---------------------------------------------------------------------------

# `facts` resolves; `video` reads a field the node's result does not have.
_PARTIAL_OUTPUTS_IR: dict[str, Any] = {
    "nodes": [{"id": "run", "type": "code", "params": {"code": 'result: dict = {"verdict": "hang"}'}}],
    "edges": [],
    "outputs": {
        "facts": {"source": "${run.result}"},
        "video": {"source": "${run.result.video_path}"},
    },
}

_OPTIONAL_HINT = "${run.result.video_path ?? null}"


class TestOutputResolutionFailure:
    """One unresolvable declared output still fails the run (strict contract), but the
    outputs that resolved survive in the failure document and the error names `?? null`."""

    def test_json_failure_keeps_resolved_outputs_and_names_null_fallback(self, tmp_path: Path) -> None:
        workflow_path = tmp_path / "partial.pflow.md"
        write_workflow_file(_PARTIAL_OUTPUTS_IR, workflow_path)

        result = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code == 1
        output = _parse_json_output(result)
        _assert_unified_shape(output)
        assert output["result"] == {"facts": {"verdict": "hang"}}
        assert output["errors"][0]["context"]["output_failures"][0]["output_name"] == "video"
        assert any(_OPTIONAL_HINT in s for s in output["errors"][0]["suggestions"])

    def test_text_failure_prints_nothing_on_stdout_and_names_null_fallback(self, tmp_path: Path) -> None:
        workflow_path = tmp_path / "partial.pflow.md"
        write_workflow_file(_PARTIAL_OUTPUTS_IR, workflow_path)

        result = CliRunner(mix_stderr=False).invoke(main, ["-p", "-o", "facts", str(workflow_path)])

        assert result.exit_code == 1
        assert result.stdout == ""
        assert _OPTIONAL_HINT in result.stderr

    def test_failed_output_sharing_a_node_name_is_not_reported_as_resolved(self, tmp_path: Path) -> None:
        """The node namespace `run` sits in the shared store under the failed output's name."""
        workflow = {
            **_PARTIAL_OUTPUTS_IR,
            "outputs": {"facts": {"source": "${run.result}"}, "run": {"source": "${run.result.video_path}"}},
        }
        workflow_path = tmp_path / "partial.pflow.md"
        write_workflow_file(workflow, workflow_path)

        result = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code == 1
        assert _parse_json_output(result)["result"] == {"facts": {"verdict": "hang"}}

    def test_node_failure_has_no_result_even_when_a_node_shares_an_output_name(self, tmp_path: Path) -> None:
        """Outputs are only populated once every step ran; before that a declared name in the
        shared store is a node namespace, not an output — it must not surface as `result`."""
        workflow = {
            "nodes": [
                {"id": "summary", "type": "code", "params": {"code": 'result: str = "hi"'}},
                {"id": "boom", "type": "code", "params": {"code": 'raise RuntimeError("boom")\nresult: str = ""'}},
            ],
            "edges": [{"from": "summary", "to": "boom"}],
            "outputs": {"summary": {"source": "${summary.result}"}},
        }
        workflow_path = tmp_path / "node-fails.pflow.md"
        write_workflow_file(workflow, workflow_path)

        result = CliRunner(mix_stderr=False).invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code == 1
        output = _parse_json_output(result)
        assert output["errors"][0]["node_id"] == "boom"
        assert "result" not in output
