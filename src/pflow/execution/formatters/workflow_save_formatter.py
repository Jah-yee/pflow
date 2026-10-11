"""Shared formatters for workflow save operations.

This module provides formatting functions for displaying workflow save success
messages across CLI and MCP interfaces. All formatters return strings that can
be displayed directly or incorporated into structured responses.

Usage:
    >>> from pflow.execution.formatters.workflow_save_formatter import format_save_success
    >>> message = format_save_success(
    ...     name="my-workflow",
    ...     saved_path="/path/to/workflow.pflow.md",
    ...     workflow_ir={"inputs": {"param": {"required": True, "type": "string"}}},
    ... )
    >>> print(message)
    ✓ Saved workflow 'my-workflow' to library
    ...
"""

from typing import Any

from pflow.core.types import input_usage, usage_arguments


def format_save_success(
    name: str,
    saved_path: str,
    workflow_ir: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    bundled_files: list[str] | None = None,
) -> str:
    """Format workflow save success message.

    Creates a comprehensive success message showing:
    - Save confirmation with location
    - Bundled dependency files (if any)
    - Execution hint with parameter placeholders
    - Optional parameters list
    - Discovery keywords (if metadata provided)
    - Tip for complex types (array/object/untyped)

    Args:
        name: Workflow name
        saved_path: Path where workflow was saved
        workflow_ir: Workflow IR dict with inputs/outputs
        metadata: Optional metadata dict with keywords
        bundled_files: Optional list of relative paths of bundled dependency files

    Returns:
        Formatted success message string

    Example:
        >>> result = format_save_success(
        ...     name="test-workflow",
        ...     saved_path="/path/to/workflow.pflow.md",
        ...     workflow_ir={
        ...         "inputs": {
        ...             "msg": {"required": True, "type": "string"},
        ...             "count": {"required": False, "type": "number"}
        ...         }
        ...     },
        ...     metadata={"keywords": ["test", "example"]}
        ... )
        >>> "Execute with: pflow test-workflow msg=<string>" in result
        True
        >>> "Optional params: count" in result
        True
    """
    lines = [
        f"✓ Saved workflow '{name}' to library",
        f"  Location: {saved_path}",
    ]

    # Show bundled dependency files
    if bundled_files:
        count = len(bundled_files)
        lines.append(f"  Bundled {count} {'file' if count == 1 else 'files'}:")
        for f in bundled_files:
            lines.append(f"    {f}")

    # Add execution hint with parameter information
    execution_hint = format_execution_hint(name, workflow_ir)
    lines.append(f"  ✨ Execute with: {execution_hint}")

    # Add note about optional parameters if there are any
    inputs = workflow_ir.get("inputs", {})
    optional_params = [param_name for param_name, spec in inputs.items() if not input_usage(spec).required]
    if optional_params:
        lines.append(f"  Optional params: {', '.join(optional_params)}")

    # Add tip if workflow has complex parameter types
    if _has_complex_types(workflow_ir):
        lines.append(f"  💡 For parameter details: pflow describe {name}")

    # Add keywords if metadata provided
    if metadata:
        keywords = metadata.get("keywords", [])
        if keywords:
            # Show first 3 keywords with ellipsis
            keywords_str = ", ".join(keywords[:3])
            if len(keywords) > 3:
                keywords_str += "..."
            lines.append(f"  Discoverable by: {keywords_str}")

    return "\n".join(lines)


def format_execution_hint(name: str, workflow_ir: dict[str, Any]) -> str:
    """The command that runs a saved workflow: every input as ``name=<placeholder>``, required first.

    Examples:
        >>> format_execution_hint("my-workflow", {"inputs": {}})
        'pflow my-workflow'

        >>> format_execution_hint("analyzer", {
        ...     "inputs": {
        ...         "count": {"required": True, "type": "integer"},
        ...         "data": {"required": False, "type": "array"},
        ...     }
        ... })
        "pflow analyzer count=<integer> data='[...]'"
    """
    return " ".join([f"pflow {name}", *usage_arguments(workflow_ir.get("inputs") or {}, include_optional=True)])


def _has_complex_types(workflow_ir: dict[str, Any]) -> bool:
    """Whether an input's placeholder says too little on its own: an array, object or untyped input."""
    return any(
        input_usage(spec).type.name in ("array", "object", "any") for spec in (workflow_ir.get("inputs") or {}).values()
    )
