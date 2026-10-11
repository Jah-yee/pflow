"""Shared compact formatting for batch item failures."""

from __future__ import annotations

import textwrap
from collections.abc import Callable, Mapping
from typing import Any

from pflow.core.security_utils import is_sensitive_parameter

MAX_BATCH_ERRORS_SHOWN = 5
MAX_ERROR_MESSAGE_CHARS = 200
MAX_ITEM_SUMMARY_CHARS = 240


def format_batch_errors_section(steps: list[dict[str, Any]]) -> list[str]:
    """Format compact batch error sections for execution step rows."""
    lines: list[str] = []

    for step in steps:
        if not step.get("is_batch") or step.get("batch_errors", 0) == 0:
            continue

        node_id = step.get("node_id", "unknown")
        error_details = step.get("batch_error_details", [])
        truncated = step.get("batch_errors_truncated", 0)

        lines.append(f"\nBatch '{node_id}' errors:")
        for err in error_details[:MAX_BATCH_ERRORS_SHOWN]:
            if not isinstance(err, Mapping):
                continue
            idx = err.get("index", "?")
            msg = _truncate_error_message(str(err.get("error", "Unknown error")))
            lines.append(f"  [{idx}] {msg}")
            provider_message = format_batch_provider_message(err)
            if provider_message:
                lines.append(f"      provider: {provider_message}")
            item_summary = format_batch_item_summary(err)
            if item_summary:
                lines.append(f"      item: {item_summary}")
            child_failure = err.get("child_failure")
            if isinstance(child_failure, Mapping):
                headline = _error_headline(str(err.get("error", "")))
                lines.extend(_format_child_failure_lines(dict(child_failure), node_id, headline))

        if truncated > 0:
            lines.append(f"  ...and {truncated} more errors")

    return lines


def format_batch_item_summary(error_detail: Mapping[str, Any]) -> str | None:
    """Return the display-safe item summary for one batch error, if present."""
    summary = error_detail.get("item_summary")
    if not isinstance(summary, Mapping):
        return None
    text = summary.get("summary")
    if not isinstance(text, str) or not text:
        return None
    return _truncate_text(text, MAX_ITEM_SUMMARY_CHARS)


def format_batch_provider_message(error_detail: Mapping[str, Any]) -> str | None:
    """Return the upstream provider diagnosis for one batch error, if present.

    ``provider_message`` is the raw provider text captured by the LLM adapter
    (masked for key material at capture). For a batched LLM failure it is often
    the only text naming the real cause — the item's ``error`` string carries
    pflow's wrapped framing. Rendered as the headline only, capped like every
    other batch error line.
    """
    provider_message = error_detail.get("provider_message")
    if not isinstance(provider_message, str) or not provider_message.strip():
        return None
    return _truncate_error_message(provider_message)


def compact_batch_error_detail(error_detail: Mapping[str, Any]) -> dict[str, Any]:
    """Return a printable batch error detail: the archival record, its ``child_failure`` redacted.

    The runtime builds that bundle raw (child failure data, ``Diagnostic.to_dict()``
    payloads) and archives it raw (#799); every surface that prints a batch error takes
    this form.
    """
    compact = _archive_batch_error_detail(error_detail)
    if "child_failure" in compact:
        compact["child_failure"] = _redact_child_failure(compact["child_failure"])
    return compact


def _redact_child_failure(value: Any) -> Any:
    """``redact_sensitive``, except the keys of a child bundle's ``failures`` map stay.

    Those keys are child node IDs — names the author chose, not parameter names: a step
    called ``auth`` keeps its failure record (the reconstructor reads it), and redaction
    applies inside the record. A bundle is any mapping carrying ``failed_node`` and
    ``failures`` (``WorkflowExecutor._extract_child_failure``), however deep it nests —
    under a child batch's ``errors[].child_failure`` or a child workflow's own bundle.
    """
    if isinstance(value, list):
        return [_redact_child_failure(item) for item in value]
    if not isinstance(value, Mapping):
        return value
    is_bundle = "failed_node" in value and isinstance(value.get("failures"), Mapping)
    redacted: dict[Any, Any] = {}
    for key, item in value.items():
        if is_bundle and key == "failures":
            redacted[key] = {node_id: _redact_child_failure(record) for node_id, record in item.items()}
        elif isinstance(key, str) and is_sensitive_parameter(key):
            redacted[key] = "<REDACTED>"
        else:
            redacted[key] = _redact_child_failure(item)
    return redacted


def _archive_batch_error_detail(error_detail: Mapping[str, Any]) -> dict[str, Any]:
    """Return a batch error detail without the raw item, values otherwise kept raw."""
    compact: dict[str, Any] = {
        "index": error_detail.get("index", "?"),
        "error": _truncate_error_message(str(error_detail.get("error", "Unknown error"))),
    }

    # Keep the provider diagnosis on the JSON/API surface too — it is plain,
    # masked text (never raw item data), and it is the field an agent needs to
    # tell "model retired" from "quota exceeded" inside one error class.
    provider_message = format_batch_provider_message(error_detail)
    if provider_message:
        compact["provider_message"] = provider_message

    summary = error_detail.get("item_summary")
    if isinstance(summary, Mapping):
        compact_summary = dict(summary)
        compact["item_summary"] = compact_summary
        item_ref = compact_summary.get("sha256")
        if isinstance(item_ref, str) and item_ref:
            compact["item_ref"] = item_ref

    if "item" in error_detail:
        compact["has_full_item"] = True

    # Keep the structured child-failure bundle (#252) so JSON/MCP consumers get the
    # child's per-node category + data, not a flattened string.
    child_failure = error_detail.get("child_failure")
    if isinstance(child_failure, Mapping):
        compact["child_failure"] = dict(child_failure)

    return compact


def _format_child_failure_lines(child_failure: dict[str, Any], node_id: str, headline: str) -> list[str]:
    """Render a failed batch sub-workflow item's reconstructed child diagnostics (indented).

    Reuses the same reconstruction primitive (``build_subworkflow_diagnostics``) and
    renderer (``format_diagnostic``) the non-batch path uses, so a batched
    sub-workflow failure shows the same rich, provenance-wrapped block. A diagnostic
    whose message IS the item's ``[idx]`` headline (a child input the step passes,
    placed at the step) shows only its detail lines, so the sentence reads once.
    """
    from pflow.core.diagnostic_render import format_diagnostic
    from pflow.execution.executor_service import build_subworkflow_diagnostics

    lines: list[str] = []
    for diagnostic in build_subworkflow_diagnostics(child_failure, node_id):
        rendered = format_diagnostic(diagnostic).splitlines()
        # Drop the top-level title frame ("Error: <title>" + its trailing blank line).
        # The "[idx] ..." line above is already the item's headline, so the title
        # would read as a second, separate error. format_diagnostic always emits the
        # severity-prefixed title first (diagnostic_render._format_error_diagnostic).
        if rendered and rendered[0].startswith(("Error:", "Warning:", "Info:")):
            rendered = rendered[1:]
            while rendered and not rendered[0].strip():
                rendered.pop(0)
        if rendered and rendered[0].strip() == headline:
            rendered = textwrap.dedent("\n".join(rendered[1:])).splitlines()
        lines.extend(f"      {line}" if line.strip() else "" for line in rendered)
    return lines


def compact_batch_output_value(value: Any) -> Any:
    """Return a printable copy of a batch aggregate output value.

    Successful ``results[].item`` values remain full-fidelity. Only failed
    ``errors[]`` records are compacted (``compact_batch_error_detail``) because they
    are the unbounded failure surface that renderers may otherwise dump as workflow output.
    """
    return _compact_batch_errors(value, compact_batch_error_detail)


def archive_batch_output_value(value: Any) -> Any:
    """Return the archival copy of a batch aggregate output value — the runtime's form.

    Drops each failed record's raw item like ``compact_batch_output_value`` but keeps
    every other value raw for the trace; a printer takes ``compact_batch_output_value``.
    """
    return _compact_batch_errors(value, _archive_batch_error_detail)


def _compact_batch_errors(value: Any, compact_error: Callable[[Mapping[str, Any]], dict[str, Any]]) -> Any:
    if not isinstance(value, Mapping):
        return value
    errors = value.get("errors")
    if not isinstance(errors, list) or not errors:
        return value
    if not value.get("batch_metadata") and not all(
        isinstance(error, Mapping) and "index" in error and "error" in error for error in errors
    ):
        return value

    compact = dict(value)
    compact["errors"] = [compact_error(error) if isinstance(error, Mapping) else error for error in errors]
    return compact


def _truncate_error_message(message: str, max_length: int = MAX_ERROR_MESSAGE_CHARS) -> str:
    headline = _error_headline(message)
    if len(headline) <= max_length:
        return headline
    return headline[: max_length - 3] + "..."


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _error_headline(message: str) -> str:
    for line in message.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "Unknown error"
