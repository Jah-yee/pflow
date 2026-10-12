"""Error output for CLI failures that have no Run outcome.

A run that produced an ``ExecutionResult`` renders through ``execution/formatters/run_outcome.py``.
This module renders the rest: exceptions raised before a run exists (resolution, flags, a
subcommand's error) or escaping the runner — ``{success, status, error, errors, diagnostics,
workflow}`` in JSON, the diagnostic text otherwise.
"""

from __future__ import annotations

from typing import Any

import click

from pflow.core.diagnostic import exception_to_diagnostics
from pflow.core.diagnostic_render import format_diagnostic


def format_error_json(*, exception: Exception, workflow_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """The JSON error document for an exception."""
    diagnostics = exception_to_diagnostics(exception)
    errors = [d.to_output_dict() for d in diagnostics]
    if len(errors) == 1:
        summary = errors[0].get("title") or errors[0].get("message") or str(exception)
    else:
        summary = getattr(exception, "summary", None) or f"Workflow execution failed ({len(errors)} errors)"

    return {
        "success": False,
        "status": "failed",
        "error": summary,
        "errors": errors,
        "diagnostics": [d.to_output_dict() for d in diagnostics],
        "workflow": workflow_metadata or {"action": "unsaved"},
    }


def display_exception_text(exception: Exception, verbose: bool = False) -> None:
    """Display exception in text mode using the diagnostic pipeline."""
    for diagnostic in exception_to_diagnostics(exception):
        click.echo(format_diagnostic(diagnostic, verbose=verbose), err=True)


def output_error(
    ctx: click.Context | None,
    exception: Exception,
    output_format: str = "text",
    verbose: bool = False,
    workflow_metadata: dict[str, Any] | None = None,
) -> None:
    """Output an exception in the requested format (JSON document on stdout, or text on stderr)."""
    if output_format == "json":
        from pflow.cli.workflow_output import _serialize_json_result

        _serialize_json_result(format_error_json(exception=exception, workflow_metadata=workflow_metadata), verbose)
    else:
        display_exception_text(exception, verbose)
