"""Standalone template resolution functions for the execution engine.

Extracted from template_wrapper.py. These functions handle template variable
resolution, type validation, and parameter splitting — all without instance
state. The engine calls these directly instead of delegating to a wrapper.

Key difference from the old wrapper: _build_resolution_context is eliminated.
context = dict(shared) — NO initial_params override. The shared store is the
single source of runtime data.
"""

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from pflow.core.param_coercion import coerce_param_for_node
from pflow.core.templates import (
    CONTAINER_TYPES,
    DECLARED_INPUT_TYPES_KEY,
    LIST_TYPES,
    Reference,
    Resolution,
    TemplateResolver,
    lookup,
    parse,
    resolve,
)
from pflow.core.types import outer_base_type
from pflow.core.workflow.template_surfaces import param_mode

from .template_errors import (
    build_declared_text_error_message,
    build_json_parse_error_message,
    build_shape_error_message,
    build_template_error_diagnostic,
    build_type_error_message,
)
from .types import TemplateConfig

logger = logging.getLogger(__name__)


def _runtime_base_type(type_str: str) -> str:
    """Normalize a declared type for runtime comparison against bare type names.

    The runtime type machinery (the JSON auto-parse gate in ``resolve_templates``
    and ``validate_resolved_type``) compares against bare names — ``dict``/``list``/
    ``object``/``array``/``str``. Strip a parameterized generic to its outer base so
    ``list[str]`` is recognized as ``list``. Without this, a code/shell value wired
    into a ``list[str]`` param would pass validation (the validator already strips
    generics — see ``core.templates.is_type_compatible``) but silently fail to
    JSON-auto-parse at runtime (issue #460 / PR #461).

    Unions are left intact — they are never auto-parsed, and collapsing
    ``list[str]|str`` to ``list`` would wrongly start parsing them.
    """
    return type_str if "|" in type_str else outer_base_type(type_str)


def build_type_cache(interface_metadata: dict[str, Any] | None) -> dict[str, str]:
    """Extract param_key -> expected_type from registry interface metadata.

    Declared types are normalized to their outer base via ``_runtime_base_type``
    (``list[str]`` -> ``list``) so the runtime type machinery, which only speaks
    bare type names, stays in sync with the generic-aware validation layer.

    Args:
        interface_metadata: Node interface metadata from registry

    Returns:
        Dictionary mapping parameter keys to their expected types.
        Empty dict if no interface metadata available.
    """
    if not interface_metadata:
        return {}

    types: dict[str, str] = {}

    # Extract types from inputs
    inputs = interface_metadata.get("inputs", [])
    if isinstance(inputs, list):
        for input_spec in inputs:
            if isinstance(input_spec, dict):
                key = input_spec.get("key")
                type_str = input_spec.get("type")
                if key and type_str:
                    types[key] = _runtime_base_type(type_str)

    # Extract types from params
    params = interface_metadata.get("params", [])
    if isinstance(params, list):
        for param_spec in params:
            if isinstance(param_spec, dict):
                key = param_spec.get("key")
                type_str = param_spec.get("type")
                if key and type_str:
                    types[key] = _runtime_base_type(type_str)

    return types


# (node type, param) whose leaves the resolver hands on as text — the consumer types them:
# shell.env binds environment text (ADR-0016); an HTTP header value is text by protocol; a
# workflow step's inputs: are typed by the child's own ## Inputs (ADR-0017).
_CONSUMER_TYPES_LEAVES: frozenset[tuple[str, str]] = frozenset({
    ("shell", "env"),
    ("http", "headers"),
    ("workflow", "inputs"),
})


def parses_leaves(template_config: TemplateConfig, key: str, subkey: str | None = None) -> bool:
    """Whether a structured param's string leaves are JSON-parsed on resolution.

    The consumer-side half of the parse decision (the source-side half — a declared input
    is never re-parsed — rides the store, ``core/templates.DECLARED_INPUT_TYPES_KEY``): no
    for a ``_CONSUMER_TYPES_LEAVES`` param, and for a code step's ``inputs:`` key annotated
    text (``subkey`` in ``text_input_keys``); yes otherwise. Keyed on ``(node type, param)``,
    never on the param name alone.
    """
    if (template_config.node_type, key) in _CONSUMER_TYPES_LEAVES:
        return False
    return subkey is None or subkey not in template_config.text_input_keys


def _bind_locally(context: dict[str, Any], names: Iterable[str]) -> None:
    """A step's own ``inputs:`` keys enter ``context`` as local bindings: a same-named
    declared input no longer owns those roots, so they leave the declared-type map."""
    declared: Mapping[str, str] = context.get(DECLARED_INPUT_TYPES_KEY) or {}
    shadowed = declared.keys() & set(names)
    if shadowed:
        context[DECLARED_INPUT_TYPES_KEY] = {k: v for k, v in declared.items() if k not in shadowed}


def split_params(
    params: dict[str, Any],
    expected_types: dict[str, str],
    node_type: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate params into template_params and static_params.

    A body (``param_mode`` → ``"body"``) is static whatever it contains — decided
    before ``has_templates``, so a ``$${`` in a shell command reaches sh unchanged.
    Embedded code (``"embedded"``) is a template param only when it holds a JSON insert,
    so JavaScript's own ``${…}`` and ``$${`` reach the tool unchanged.
    Otherwise only params TemplateResolver.has_templates detects are ever resolved; an
    undetected template stays a literal in static_params.
    Static params get type coercion via coerce_param_for_node.
    _source_line keys are kept in static_params (nodes read them for error
    reporting, e.g. python_code.py uses _code_source_line for line numbers).
    They are filtered out later by compute_node_config() for cache hashing.

    Args:
        params: Node parameters to classify
        expected_types: param_key -> expected type mapping
        node_type: the node's type, for ``param_mode`` (``None`` — no param is a body)

    Returns:
        (template_params, static_params)
    """
    template_params: dict[str, Any] = {}
    static_params: dict[str, Any] = {}

    for key, value in params.items():
        mode = param_mode(node_type, key)
        if mode != "body" and TemplateResolver.has_templates(value, embedded=mode == "embedded"):
            template_params[key] = value
        else:
            expected_type = expected_types.get(key)
            coerced_value = coerce_param_for_node(value, expected_type)
            static_params[key] = coerced_value

    return template_params, static_params


def validate_resolved_type(
    param_key: str,
    resolved_value: Any,
    template_str: str,
    expected_types: dict[str, str],
    resolution_mode: str,
    *,
    declared_input: tuple[str, str] | None = None,
) -> str | None:
    """Validate that resolved value type matches expected parameter type.

    Returns error message string on type mismatch, None on success.
    In strict mode, the caller should raise ValueError with the returned message.
    In permissive mode, the caller should store the error and continue.

    The __PERMISSIVE_TYPE_ERROR__ prefix protocol is eliminated.

    Args:
        param_key: Parameter name being validated
        resolved_value: Value after template resolution
        template_str: Original template string (for error message)
        expected_types: param_key -> expected type mapping
        resolution_mode: "strict" or "permissive"
        declared_input: ``(name, declared type)`` when the template reads a declared input —
            its text was never parsed, and the message says so

    Returns:
        Error message string if type mismatch detected, None otherwise
    """
    expected_type = expected_types.get(param_key)
    if not expected_type or expected_type == "any":
        return None

    # String parameters receiving dicts/lists
    if expected_type == "str" and isinstance(resolved_value, (dict, list)):
        actual_type = type(resolved_value).__name__
        return build_type_error_message(param_key, resolved_value, template_str, expected_type, actual_type)

    if expected_type not in CONTAINER_TYPES:
        return None
    # Correct type matches
    if isinstance(resolved_value, list if expected_type in LIST_TYPES else dict):
        return None

    # The other container shape — well-formed JSON of the wrong kind
    if isinstance(resolved_value, (dict, list)):
        return build_shape_error_message(param_key, resolved_value, template_str, expected_type)

    # dict/list parameters receiving strings — a declared input's text, or a failed JSON parse
    if isinstance(resolved_value, str):
        if declared_input is not None:
            return build_declared_text_error_message(param_key, template_str, expected_type, *declared_input)
        trimmed = resolved_value.strip()
        if trimmed and trimmed[0] in ("{", "["):
            return build_json_parse_error_message(param_key, resolved_value, template_str, expected_type, trimmed)

    return None


def _declared_input_read(template: Any, context: dict[str, Any]) -> tuple[str, str] | None:
    """``(name, declared type)`` when a simple template's value came from a declared non-``any``
    input — judged by the operand that supplied it, as resolution judges it."""
    declared: Mapping[str, str] = context.get(DECLARED_INPUT_TYPES_KEY) or {}
    if not isinstance(template, str) or not declared or not (expressions := parse(template).expressions):
        return None
    for operand in expressions[0].operands:
        if not isinstance(operand, Reference):
            return None  # a literal won
        if lookup(operand, context)[0]:
            kind = declared.get(operand.root, "any")
            return (operand.root, kind) if kind != "any" else None
    return None


def _left_to_absent_nodes(template: Any, resolution: Resolution, context: dict[str, Any]) -> bool:
    """True if ``template`` stayed wholly literal because every node it reads is absent.

    Every operand must be a reference whose root is absent from context (absent
    covers "did not execute" and "executed and failed" — failed nodes leave the
    main namespace), so no expression could have resolved; and nothing may be an
    Issue. Only OUTER roots count: a present ``${__index__}`` inside ``[…]`` does
    not make ``${a[${__index__}].x}`` from an absent ``a`` resolvable.
    """
    if not isinstance(template, str) or not resolution.unresolved or resolution.issues:
        return False
    operands = [op for expr in parse(template).expressions for op in expr.operands]
    return all(isinstance(op, Reference) and op.root not in context for op in operands)


def inject_none_for_optional_inputs(
    resolved_inputs: dict[str, Any],
    template_inputs: dict[str, Any],
    context: dict[str, Any],
    optional_input_keys: set[str],
    resolutions_by_key: dict[str, Resolution],
) -> tuple[dict[str, Any], frozenset[str]]:
    """Replace optional inputs left unresolved by a non-executed branch with None.

    For code nodes with optional input annotations, when the source node
    didn't execute, inject None instead of leaving unresolved ${...}.

    Returns the inputs and the keys that received None — their resolutions no
    longer count as unresolved. Every other key keeps its own channel, even one
    sharing the injected key's expression text.
    """
    injected = frozenset(
        key
        for key in optional_input_keys
        if key in resolved_inputs
        and key in resolutions_by_key
        and _left_to_absent_nodes(template_inputs.get(key), resolutions_by_key[key], context)
    )
    if not injected:
        return resolved_inputs, injected
    return {**resolved_inputs, **dict.fromkeys(injected)}, injected


def resolve_templates(  # noqa: C901
    template_config: TemplateConfig,
    shared: dict[str, Any],
    node_id: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Resolve all template params against shared store.

    Returns (merged_params, last_resolutions, template_errors).
    - merged_params: static + resolved template params (ready to set on node)
    - last_resolutions: {key: {template, resolved}} for trace capture
    - template_errors: list of error dicts for permissive mode (empty in strict — raises instead)

    ORDERING CONTRACT: The 'inputs' key is ALWAYS processed first.

    CONTEXT BUILDING: context = dict(shared) — NO initial_params override.

    Raises ValueError in strict mode on unresolved templates or type mismatches.

    ON ERROR IN STRICT MODE: last_resolutions contains all params resolved so far.
    """
    if not template_config.template_params:
        return dict(template_config.static_params), {}, []

    # Build resolution context: shared store only — no initial_params override
    context = dict(shared)

    # Enrich context with static inputs so other params can reference them
    static_inputs = template_config.static_params.get("inputs")
    if isinstance(static_inputs, dict):
        _bind_locally(context, static_inputs)
        context.update(static_inputs)

    # Process 'inputs' before other params
    param_keys = list(template_config.template_params.keys())
    if "inputs" in param_keys:
        param_keys.remove("inputs")
        param_keys.insert(0, "inputs")

    resolved_params: dict[str, Any] = {}
    last_resolutions: dict[str, Any] = {}
    template_errors: list[dict[str, Any]] = []

    for key in param_keys:
        template = template_config.template_params[key]
        # `inputs` resolves per key, so an optional key injected with None below
        # drops its own channel without hiding a sibling that shares its text.
        inputs_by_key: dict[str, Resolution] | None = None
        if key == "inputs" and isinstance(template, dict):
            inputs_by_key = {
                k: resolve(v, context, auto_parse=parses_leaves(template_config, key, k)) for k, v in template.items()
            }
            resolved_value: Any = {k: r.value for k, r in inputs_by_key.items()}
            is_simple_template = False
        elif param_mode(template_config.node_type, key) == "embedded":
            # Embedded code: only JSON inserts are filled in; the result is always text.
            resolution = resolve(template, context, embedded=True)
            resolved_value = resolution.value
            is_simple_template = False
        else:
            # A nested dict/list parses JSON-text leaves, and a simple template's JSON text is parsed
            # for a structured param; a simple string otherwise keeps its value's type. Text from a
            # declared input is never parsed (the resolver's own rule).
            is_simple_template = isinstance(template, str) and parse(template).is_simple
            resolution = resolve(
                template,
                context,
                auto_parse=(isinstance(template, (dict, list)) and parses_leaves(template_config, key))
                or (is_simple_template and template_config.expected_types.get(key) in CONTAINER_TYPES),
            )
            resolved_value = resolution.value

        # Reverse: serialize dict/list -> str when expected type is str
        if isinstance(resolved_value, (dict, list)):
            expected_type = template_config.expected_types.get(key)
            resolved_value = coerce_param_for_node(resolved_value, expected_type)

        # Type validation for simple templates
        if is_simple_template:
            type_error = validate_resolved_type(
                key,
                resolved_value,
                str(template),
                template_config.expected_types,
                template_config.resolution_mode,
                declared_input=_declared_input_read(template, context),
            )
            if type_error:
                if template_config.resolution_mode == "strict":
                    # Store partial resolutions on exception for trace capture
                    partial = {
                        k: {"template": template_config.template_params[k], "resolved": resolved_params[k]}
                        for k in resolved_params
                    }
                    # Enrich with upstream stderr context
                    from .error_context import get_upstream_stderr

                    upstream_context = get_upstream_stderr(str(template), context)
                    if upstream_context:
                        type_error += upstream_context
                    exc = ValueError(type_error)
                    exc._pflow_partial_resolutions = partial  # type: ignore[attr-defined]
                    raise exc
                else:
                    # Build a structured Diagnostic at the source so
                    # _extract_runtime_warnings in the runner doesn't need a
                    # legacy canned-hint fallback. Type errors don't have the
                    # unresolved_references structure of full template errors,
                    # so the rendering still falls through to the one-liner
                    # warning path — but we keep the CLAUDE.md invariant that
                    # every __template_errors__ entry carries a Diagnostic.
                    from pflow.core.diagnostic import Diagnostic, Severity

                    type_diagnostic = Diagnostic(
                        severity=Severity.ERROR,  # runner downgrades to WARNING
                        message=type_error,
                        node_id=node_id,
                        source="runtime",
                        context={
                            "category": "template_error",
                            "type": "type_validation",
                            "param": key,
                        },
                    )
                    template_errors.append({
                        "message": type_error,
                        "type": "type_validation",
                        "param": key,
                        "diagnostic": type_diagnostic,
                    })

        if inputs_by_key is not None:
            # Inject None for optional inputs from non-executed branches
            injected: frozenset[str] = frozenset()
            if template_config.optional_input_keys and isinstance(resolved_value, dict):
                resolved_value, injected = inject_none_for_optional_inputs(
                    resolved_value, template, context, template_config.optional_input_keys, inputs_by_key
                )
            kept = (r for k, r in inputs_by_key.items() if k not in injected)
            resolution = Resolution.combine(resolved_value, kept)

        resolved_params[key] = resolved_value

        if not resolution.ok:
            diagnostic = build_template_error_diagnostic(
                key,
                template,
                context,
                resolution,
                node_id=node_id,
                source_file=_extract_source_file(shared),
                source_line=_extract_source_line(template_config, key),
            )

            if template_config.resolution_mode == "strict":
                from pflow.core.diagnostic_render import format_diagnostic

                # Store partial resolutions on exception for trace capture
                partial = {
                    k: {"template": template_config.template_params[k], "resolved": resolved_params[k]}
                    for k in resolved_params
                }
                exc = ValueError(format_diagnostic(diagnostic))
                exc._pflow_partial_resolutions = partial  # type: ignore[attr-defined]
                exc._pflow_template_diagnostic = diagnostic  # type: ignore[attr-defined]
                raise exc
            else:
                template_errors.append({
                    "message": diagnostic.message,
                    "unresolved": [key],
                    "unresolved_expressions": tuple(sorted(resolution.unresolved)),
                    "issues": tuple(sorted(resolution.issues)),
                    "template": template,
                    "diagnostic": diagnostic,
                })

        # After resolving 'inputs', enrich context for subsequent params
        if key == "inputs" and isinstance(resolved_value, dict):
            _bind_locally(context, resolved_value)
            context.update(resolved_value)

    # Build final resolutions for trace capture
    last_resolutions = {
        key: {"template": template_config.template_params[key], "resolved": resolved_params[key]}
        for key in resolved_params
    }

    merged_params = {**template_config.static_params, **resolved_params}
    return merged_params, last_resolutions, template_errors


def _extract_source_file(shared: dict[str, Any]) -> str | None:
    """Extract the workflow source file path for error messages."""
    return shared.get("_pflow_workflow_file")


def _extract_source_line(template_config: TemplateConfig, key: str) -> int | None:
    """Extract the source line for a template parameter, if tracked.

    The compiler stores _<key>_source_line in static_params for parameters
    written via code blocks. For inline params, this is None.
    """
    line_key = f"_{key}_source_line"
    line = template_config.static_params.get(line_key)
    return int(line) if isinstance(line, int) else None
