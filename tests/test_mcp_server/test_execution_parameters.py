"""MCP execution parameters: structural checks only — values are data (#722).

A value that reads like code (``eval(``, ``__import__``, …) is accepted exactly as the
CLI accepts it; only the parameter names, JSON-serialisability and size are checked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from pflow.cli.main import main
from pflow.mcp_server.services.execution_service import ExecutionService
from pflow.mcp_server.utils.validation import validate_execution_parameters

# Every substring the removed blocklist rejected, in source that a code step legitimately carries.
CODE_LIKE_VALUE = 'const f = eval("1+1"); exec(cmd); compile (it); globals(); locals(); __import__("os")'

ECHO_WORKFLOW = """\
# Echo Snippet

Carry a snippet through a code step.

## Inputs

### snippet

The source text to carry.

- type: string

## Steps

### carry

Return the snippet unchanged.

- type: code
- inputs: { snippet: "${snippet}" }

```python code
snippet: str
result: str = snippet
```

## Outputs

### text

The carried snippet.

- source: ${carry.result}
"""


@pytest.fixture
def echo_workflow(tmp_path: Path) -> Path:
    path = tmp_path / "echo-snippet.pflow.md"
    path.write_text(ECHO_WORKFLOW, encoding="utf-8")
    return path


def test_mcp_and_cli_run_a_code_like_input_value_identically(echo_workflow: Path) -> None:
    mcp_text = ExecutionService.execute_workflow(str(echo_workflow), parameters={"snippet": CODE_LIKE_VALUE})
    cli = CliRunner().invoke(main, [str(echo_workflow), f"snippet={CODE_LIKE_VALUE}"])

    assert cli.exit_code == 0, cli.output
    assert "Workflow completed" in mcp_text
    assert CODE_LIKE_VALUE in mcp_text
    assert CODE_LIKE_VALUE in cli.output


def test_nested_code_like_value_is_accepted() -> None:
    assert validate_execution_parameters({"payload": {"scripts": [CODE_LIKE_VALUE]}}) == (True, None)


@pytest.mark.parametrize(
    ("params", "expected_error"),
    [
        ({"bad name": "x"}, "Invalid parameter name"),
        (
            {"_pflow_workflow_file": "/elsewhere/x.pflow.md"},
            "Invalid parameter name '_pflow_workflow_file' - names starting with '_pflow_' are reserved for pflow",
        ),
        ({"blob": object()}, "Parameters not JSON serializable"),
        ({"blob": "x" * (1024 * 1024)}, "Parameters too large (max 1MB)"),
    ],
    ids=["invalid-name", "reserved-pflow-prefix", "not-serializable", "over-1mb"],
)
def test_structural_checks_still_reject(params: dict[str, object], expected_error: str) -> None:
    is_valid, error = validate_execution_parameters(params)

    assert is_valid is False
    assert error is not None
    assert expected_error in error


def test_mcp_execute_refuses_a_reserved_param_name(echo_workflow: Path) -> None:
    """The MCP tool cannot steer child resolution or the nesting guards with a `_pflow_*` key (#817)."""
    with pytest.raises(ValueError, match="names starting with '_pflow_' are reserved for pflow"):
        ExecutionService.execute_workflow(str(echo_workflow), parameters={"snippet": "x", "_pflow_depth": -1000})
