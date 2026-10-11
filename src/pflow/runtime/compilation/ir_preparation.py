"""IR structure validation and input preparation for the compilation pipeline.

- validate_ir_structure: the basic shape of workflow IR (nodes, edges arrays)
- prepare_inputs: the workflow input boundary — resolve, type, report
"""

import logging
import os
from collections.abc import Mapping
from typing import Any

from pflow.core.diagnostic import Diagnostic, Severity
from pflow.core.exceptions import CompilationError, InputTypeError
from pflow.core.param_coercion import InputSource, coerce_declared_input
from pflow.core.validation_utils import get_parameter_validation_error, is_valid_parameter_name

logger = logging.getLogger(__name__)


def _input_error(message: str, path: str, suggestion: str = "") -> Diagnostic:
    """An input-boundary error that is not a type mismatch (missing, empty, undeclared, misnamed)."""
    return Diagnostic(
        severity=Severity.ERROR,
        message=message,
        title="Validation Error",
        suggestions=[suggestion] if suggestion else None,
        source="validation",
        context={"category": "validation", "path": path},
    )


def _fallback_value(
    input_name: str, input_spec: dict[str, Any], settings_env: Mapping[str, str]
) -> tuple[Any, InputSource | None]:
    """A value for an input nobody supplied: shell environment → settings.env → declared default.

    ``(None, None)`` when none has one (a ``default: null`` is no value).
    """
    if input_name in os.environ:
        return os.environ[input_name], "env"
    if input_name in settings_env:
        return settings_env[input_name], "settings"
    if input_spec.get("default") is not None:
        return input_spec["default"], "default"
    return None, None


def _resolve_input(
    input_name: str,
    input_spec: dict[str, Any],
    supplied: Any,
    supplied_source: InputSource,
    settings_env: Mapping[str, str],
) -> tuple[Diagnostic | None, Any, InputSource | None]:
    """One declared input: ``(problem, typed value, source)``; ``source`` is ``None`` when no value exists."""
    value, source = (
        (supplied, supplied_source) if supplied is not None else _fallback_value(input_name, input_spec, settings_env)
    )
    description = input_spec.get("description", "No description provided")
    is_required = input_spec.get("required", True)
    if source is None:
        if is_required:
            return (
                _input_error(f"Workflow requires input '{input_name}': {description}", f"inputs.{input_name}"),
                None,
                None,
            )
        return None, None, None
    if is_required and value == "":
        origin = "" if supplied is not None else f" (resolved from {source})"
        message = f"Required input '{input_name}' is empty{origin}: {description}"
        return _input_error(message, f"inputs.{input_name}", "Provide a non-empty value"), None, source
    try:
        return None, coerce_declared_input(input_name, input_spec.get("type"), value, source=source), source
    except InputTypeError as e:
        return e.to_diagnostics()[0], None, source


def _is_framework_param_key(key: str) -> bool:
    """Whether ``key`` matches the documented framework-key conventions.

    Two patterns are recognized, matching what the Runner / compiler actually
    inject into ``initial_params`` before ``prepare_inputs`` runs:

    - ``_pflow_*`` — single-underscore framework namespace
      (e.g. ``_pflow_workflow_file``, ``_pflow_depth``, ``_pflow_stack``).
    - ``__*__`` — dunder-wrapped metadata keys
      (e.g. ``__template_resolution_mode__``, ``__registry__``).

    Any other underscore-prefixed name (e.g. ``_foo``) is treated as
    user-authored. Keeps user typos like ``_foo`` for declared ``foo``
    visible as extras errors, and catches framework-key typos like
    ``_pflow_workflo_file`` as unknown inputs instead of silently dropping
    them. ``is_valid_parameter_name`` already rejects ``__*__`` user names
    at schema validation, so a user cannot collide with the dunder form.
    """
    return key.startswith("_pflow_") or (key.startswith("__") and key.endswith("__"))


def _check_undeclared_extras(declared_names: set[str], provided_params: Mapping[str, Any]) -> list[Diagnostic]:
    """Detect keys in ``provided_params`` that are not declared as workflow inputs.

    Framework-internal keys are filtered via :func:`_is_framework_param_key`.
    Symmetric with the sub-workflow check in
    ``WorkflowValidator._check_required_inputs`` (GH #288 / task 153).

    Returns one Diagnostic per undeclared key.
    """
    user_provided = [k for k in provided_params if not _is_framework_param_key(k)]
    extras = sorted(set(user_provided) - declared_names)
    if not extras:
        return []

    from pflow.core.suggestion_utils import find_similar_items

    errors: list[Diagnostic] = []
    sorted_declared = sorted(declared_names)
    for extra in extras:
        if sorted_declared:
            similar = find_similar_items(extra, sorted_declared, max_results=2, method="fuzzy")
            message = f"Unknown input '{extra}' — not declared by this workflow."
            suggestion = (
                f"Did you mean '{similar[0]}'?" if similar else f"Available inputs: {', '.join(sorted_declared)}"
            )
        else:
            message = f"Unknown input '{extra}' — this workflow declares no inputs."
            suggestion = "Remove the parameter, or declare it in ## Inputs."
        errors.append(_input_error(message, f"inputs.{extra}", suggestion))
    return errors


def validate_ir_structure(ir_dict: dict[str, Any]) -> None:
    """Validate basic IR structure (nodes, edges arrays).

    This performs minimal structural validation to ensure the IR has
    the required top-level keys. Full validation should be done by
    the IR schema validator before compilation.

    Args:
        ir_dict: The IR dictionary to validate

    Raises:
        CompilationError: If required keys are missing or have wrong types
    """
    logger.debug("Validating IR structure", extra={"phase": "validation"})

    # Check for required 'nodes' key
    if "nodes" not in ir_dict:
        raise CompilationError(
            "Missing 'nodes' key in IR", phase="validation", suggestion="IR must contain 'nodes' array"
        )

    # Check nodes is a list
    if not isinstance(ir_dict["nodes"], list):
        raise CompilationError(
            f"'nodes' must be an array, got {type(ir_dict['nodes']).__name__}",
            phase="validation",
            suggestion="Ensure 'nodes' is an array of node objects",
        )

    # Check for required 'edges' key
    if "edges" not in ir_dict:
        raise CompilationError(
            "Missing 'edges' key in IR", phase="validation", suggestion="IR must contain 'edges' array (can be empty)"
        )

    # Check edges is a list
    if not isinstance(ir_dict["edges"], list):
        raise CompilationError(
            f"'edges' must be an array, got {type(ir_dict['edges']).__name__}",
            phase="validation",
            suggestion="Ensure 'edges' is an array of edge objects",
        )

    logger.debug(
        "IR structure validated",
        extra={"phase": "validation", "node_count": len(ir_dict["nodes"]), "edge_count": len(ir_dict["edges"])},
    )


def prepare_inputs(
    workflow_ir: dict[str, Any],
    provided_params: Mapping[str, Any],
    settings_env: Mapping[str, str] | None = None,
    *,
    input_sources: Mapping[str, InputSource] | None = None,
) -> tuple[list[Diagnostic], dict[str, Any], set[str]]:
    """The workflow input boundary: resolve each declared input, type it, report what is wrong.

    Per declared input, the first value found wins: supplied (a supplied ``None`` is no
    value) → shell environment → settings.env → declared default; with none, a required
    input (``required`` defaults to true) is an error and an optional one is ``None``.
    Every value found is typed by ``coerce_declared_input`` with its source — supplied
    values take theirs from ``input_sources`` (absent key: ``"argument"``). Does not mutate
    ``provided_params``.

    Returns:
        ``(errors, updates, settings_names)``: one Diagnostic per problem (type mismatch,
        missing or empty required input, undeclared key, invalid name, several ``stdin: true``
        inputs); the values to apply over ``provided_params`` — every input resolved by a
        fallback and every supplied value the coercer changed; the names whose value came
        from settings.env.
    """
    errors: list[Diagnostic] = []
    updates: dict[str, Any] = {}
    settings_names: set[str] = set()
    settings_env = settings_env or {}
    input_sources = input_sources or {}
    inputs: dict[str, Any] = workflow_ir.get("inputs") or {}

    # Reject undeclared extras (GH #288, symmetric with the sub-workflow check in
    # WorkflowValidator._check_required_inputs).
    errors.extend(_check_undeclared_extras(set(inputs), provided_params))

    stdin_inputs = [name for name, spec in inputs.items() if spec.get("stdin") is True]
    if len(stdin_inputs) > 1:
        errors.append(
            _input_error(
                f'Multiple inputs marked with "stdin": true: {", ".join(stdin_inputs)}',
                "inputs",
                "Only one input can receive piped stdin",
            )
        )

    for input_name, input_spec in inputs.items():
        if not is_valid_parameter_name(input_name):
            errors.append(
                _input_error(
                    get_parameter_validation_error(input_name, "input"),
                    f"inputs.{input_name}",
                    "Avoid shell special characters like $, |, >, <, &, ;",
                )
            )
            continue
        supplied = provided_params.get(input_name)
        problem, value, source = _resolve_input(
            input_name, input_spec, supplied, input_sources.get(input_name, "argument"), settings_env
        )
        if problem is not None:
            errors.append(problem)
            continue
        if input_name not in provided_params or value is not supplied:
            updates[input_name] = value
        if source == "settings":
            settings_names.add(input_name)

    return errors, updates, settings_names
