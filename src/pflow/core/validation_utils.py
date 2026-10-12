"""Shared validation utilities for pflow."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from pflow.core.diagnostic import Diagnostic

VALIDATION_PLACEHOLDER: Final[str] = "__validation_placeholder__"
"""Sentinel value substituted for unresolved declared inputs during
structural validation, cache-key prediction, and cross-workflow walker
compile passes. Consumers that handle real workflow values must short-
circuit when they see this string — it is never a meaningful payload."""


def generate_dummy_parameters(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate dummy parameters for workflow validation.

    Creates placeholder values for all declared inputs to enable
    structural validation without real values.

    Args:
        inputs: Declared workflow inputs

    Returns:
        Dictionary of dummy parameter values

    Example:
        >>> inputs = {"api_key": {"type": "string"}, "repo": {"type": "string"}}
        >>> generate_dummy_parameters(inputs)
        {'api_key': '__validation_placeholder__', 'repo': '__validation_placeholder__'}
    """
    return dict.fromkeys(inputs, VALIDATION_PLACEHOLDER)


def validate_with_placeholder_inputs(workflow_ir: dict[str, Any], *, workflow_file: Path | None) -> list["Diagnostic"]:
    """Validate a workflow without real input values -- the shared call behind
    ``--validate-only``, ``pflow save``, and ``analyze-cache``.

    Declared inputs get placeholder values. ``workflow_file`` reaches the
    validator on both channels it reads -- the ``workflow_file`` argument and
    ``_pflow_workflow_file`` in the params -- so relative sub-workflow paths
    resolve against the workflow's directory, never the current directory.
    Callers pass the path once here instead of assembling those params by hand.
    """
    from pflow.core.workflow.validator import WorkflowValidator
    from pflow.registry import Registry

    params = generate_dummy_parameters(workflow_ir.get("inputs") or {})
    if workflow_file is not None:
        params["_pflow_workflow_file"] = str(workflow_file)
    return WorkflowValidator.validate(
        workflow_ir=workflow_ir,
        extracted_params=params,
        registry=Registry(),
        skip_node_types=False,
        workflow_file=workflow_file,
    )


RESERVED_NAME_PREFIX: Final[str] = "_pflow_"
"""Prefix of pflow's own root shared-store keys (``_pflow_workflow_file``, ``_pflow_depth``,
``_pflow_stack``, ...). A parameter or declared name using it would seed the state those keys
carry — child-workflow resolution and the nesting guards — so the name rule reserves it."""


# Shell special characters are dangerous in commands and template expansion; whitespace breaks
# CLI parsing and the template regex. First match names the problem.
_NAME_CHARACTER_RULES: Final[tuple[tuple[str, str], ...]] = (
    (" ", "cannot contain spaces (use hyphens or underscores instead)"),
    ("\t", "cannot contain tabs"),
    ("$", "cannot contain '$' (conflicts with template syntax)"),
    ("|><&;`", "cannot contain shell special characters"),
    ("\n\r\0", "cannot contain control characters"),
    ("\"'", "cannot contain quotes"),
    ("\\", "cannot contain backslashes"),
)


def _parameter_name_problem(name: str) -> str | None:
    """Why ``name`` cannot be a parameter name, or ``None`` when it can — the one rule behind
    :func:`is_valid_parameter_name` and :func:`get_parameter_validation_error`."""
    if not name or not name.strip():
        return "cannot be empty"
    # `__*__` keys bypass NamespacedSharedStore and write to the root store, as `_pflow_*` keys do.
    if name.startswith("__") and name.endswith("__"):
        return "names wrapped in double underscores are reserved for internal use"
    if name.startswith(RESERVED_NAME_PREFIX):
        return f"names starting with '{RESERVED_NAME_PREFIX}' are reserved for pflow"
    return next((reason for chars, reason in _NAME_CHARACTER_RULES if any(char in name for char in chars)), None)


def is_valid_parameter_name(name: str) -> bool:
    """Whether ``name`` may name a workflow parameter, input or output.

    Permissive by design — hyphens (``api-key``), dots (``file.path``) and a leading digit
    (``2fa-token``) are fine. Rejected: blank names, the reserved ``__*__`` and
    ``_pflow_*`` (:data:`RESERVED_NAME_PREFIX`) forms, whitespace, and shell special characters.
    """
    return _parameter_name_problem(name) is None


def get_parameter_validation_error(name: str, param_type: str = "parameter") -> str:
    """The error naming why ``name`` is invalid; ``param_type`` is the noun (``input``, ``output``, ``parameter``)."""
    problem = _parameter_name_problem(name) or "contains invalid characters"
    quoted = f" '{name}'" if name.strip() else ""
    return f"Invalid {param_type} name{quoted} - {problem}"
