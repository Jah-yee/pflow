"""Text rendering masks sensitive-named node data the way the JSON document does (#788).

``format_diagnostic`` is the one text renderer for diagnostics: CLI text, MCP text, and the
strict-mode exception message the trace stores as a node's ``error``. Every block it draws
reads the redacted context, so a secret under a sensitive-named key never reaches the text.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest

from pflow.core import diagnostic_render
from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.diagnostic_render import format_diagnostic
from pflow.core.templates import resolve
from pflow.runtime.engine.template_errors import build_template_error_diagnostic
from pflow.runtime.node_state import (
    FAILURE_CATEGORY_EXCEPTION,
    FAILURE_CATEGORY_HTTP,
    FAILURE_CATEGORY_MCP,
    mark_node_failed,
)

SECRET = "SECRET-TOKEN-456"  # noqa: S105 — test fixture value


def _failed_reference_diagnostic(category: str, output: dict[str, Any]) -> Diagnostic:
    """The real template-error diagnostic for ``${api.nope}`` after node ``api`` failed with ``output``."""
    shared: dict[str, Any] = {
        "api": output,
        "__execution__": {
            "completed_nodes": [],
            "node_actions": {},
            "node_hashes": {},
            "failed_node": None,
            "node_visit_counts": {},
        },
    }
    mark_node_failed(shared, "api", category=category, error="request failed")
    template = "${api.nope}"
    return build_template_error_diagnostic("X", template, shared, resolve(template, shared), node_id="rescue")


_FAILED_REFERENCE_CASES = {
    "http_failure": (
        FAILURE_CATEGORY_HTTP,
        {"status_code": 401, "response": {"access_token": SECRET, "error": "nope"}},
        "Response: {'access_token': '<REDACTED>', 'error': 'nope'}",
    ),
    "mcp_failure": (
        FAILURE_CATEGORY_MCP,
        {"server": "srv", "tool": "t", "error_details": {"auth_token": SECRET, "hint": "nope"}},
        "Details: {'auth_token': '<REDACTED>', 'hint': 'nope'}",
    ),
    "generic": (
        FAILURE_CATEGORY_EXCEPTION,
        {"api_key": SECRET, "detail": "nope"},
        "api_key: <REDACTED>",
    ),
}


@pytest.mark.parametrize("severity", [Severity.ERROR, Severity.WARNING], ids=["strict-error", "permissive-warning"])
@pytest.mark.parametrize(
    ("category", "output", "masked_line"), _FAILED_REFERENCE_CASES.values(), ids=_FAILED_REFERENCE_CASES.keys()
)
def test_failed_reference_block_masks_sensitive_named_values(
    category: str, output: dict[str, Any], masked_line: str, severity: Severity
) -> None:
    diagnostic = _failed_reference_diagnostic(category, output)
    diagnostic.severity = severity

    rendered = format_diagnostic(diagnostic)

    assert SECRET not in rendered
    assert masked_line in rendered
    assert "nope" in rendered  # the non-secret neighbour still shows
    assert SECRET in str(diagnostic.context)  # rendering reads a redacted copy; the diagnostic stays raw


@pytest.mark.parametrize(
    ("context", "masked_line"),
    [
        (
            {"raw_response": {"message": {"detail": "bad", "access_token": SECRET}}},
            "    {'detail': 'bad', 'access_token': '<REDACTED>'}",
        ),
        ({"mcp_error_details": {"server": "srv", "api_key": SECRET}}, "Details: {'api_key': '<REDACTED>'}"),
    ],
    ids=["api-response", "mcp-error-details"],
)
def test_top_level_data_blocks_mask_sensitive_named_values(context: dict[str, Any], masked_line: str) -> None:
    rendered = format_diagnostic(Diagnostic(severity=Severity.ERROR, message="failed", context=context))

    assert SECRET not in rendered
    assert masked_line in rendered


def _api_message_lines(message: str) -> list[str]:
    rendered = format_diagnostic(
        Diagnostic(severity=Severity.ERROR, message="HTTP 403", context={"raw_response": {"message": message}})
    )
    return rendered.splitlines()


def test_api_message_shows_whole_up_to_the_display_cap() -> None:
    # The per-block ``sanitize_parameters`` this replaced cut every string over 100 chars to 20
    # (the #746 blinding the gate preview already dropped); an API's own message is the diagnosis.
    message = "The requested resource requires the 'repo' scope, which the token you supplied lacks."
    message += " Re-issue it with that scope."
    assert f"    {message}" in _api_message_lines(message)

    # Past 300 characters it is capped like every other data line, so a verbose upstream
    # message cannot flood stderr or an agent's MCP context.
    assert f"    {'m' * 300}..." in _api_message_lines("m" * 10_000)


def test_only_the_entry_reads_the_raw_diagnostic_context() -> None:
    """Ratchet: a renderer that reads ``diagnostic.context`` itself would bypass the redaction."""
    tree = ast.parse(inspect.getsource(diagnostic_render))
    readers = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute) and node.attr == "context"
    }

    assert readers == {"format_diagnostic"}
