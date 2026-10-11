"""Parameter type coercion, one function per pipeline stage.

- ``coerce_declared_input``: a workflow input's value typed by its declared type, once,
  where it enters — or ``InputTypeError``.
- ``coerce_param_for_node``: a resolved dict/list serialized to JSON for a node param
  declared ``str``.
"""

import json
import logging
from typing import Any, Literal

from pflow.core.exceptions import InputTypeError
from pflow.core.json_utils import try_parse_json
from pflow.core.templates import to_string
from pflow.core.types import CANONICAL_TYPES, TypeSpec
from pflow.core.validation_utils import VALIDATION_PLACEHOLDER

logger = logging.getLogger(__name__)


def coerce_param_for_node(
    value: Any,
    expected_type: str | None,
) -> Any:
    """Coerce a resolved parameter value for node execution.

    Intentionally narrow: only serializes dict/list → JSON string when the
    node declares the parameter as type "str". All other values pass through
    unchanged. This handles the MCP tool case where a tool declares `param: str`
    but the upstream produced a dict/list.

    This function does NOT perform general type coercion (e.g., str→int).
    At this pipeline stage, values are already in their intended form from
    template resolution or the shared store.

    Note on vocabulary: ``expected_type`` here is the S3 node-Interface type
    (Python-aliased — ``"str"``, ``"dict"``), NOT the S1 workflow-IR vocabulary.
    This is why ``"str"``/``"string"`` are both accepted below, even though
    the S1 vocabulary (``## Inputs``) rejects Python aliases. See
    ``src/pflow/core/types.py`` module docstring for the surface split.

    Args:
        value: The resolved value to potentially coerce
        expected_type: Declared type from node interface ("str", "dict", etc.)

    Returns:
        Coerced value if conversion needed, otherwise original value

    Examples:
        >>> coerce_param_for_node({"key": "value"}, "str")
        '{"key": "value"}'
        >>> coerce_param_for_node([1, 2, 3], "str")
        '[1, 2, 3]'
        >>> coerce_param_for_node("hello", "str")
        'hello'
        >>> coerce_param_for_node({"key": "value"}, "dict")
        {'key': 'value'}
    """
    if expected_type is None:
        return value

    # Normalize type aliases
    normalized_type = expected_type.lower()

    # dict/list -> str: Serialize to JSON
    if normalized_type in ("str", "string") and isinstance(value, (dict, list)):
        try:
            serialized = json.dumps(value)
            logger.debug(
                f"Coerced {type(value).__name__} to JSON string for str-typed parameter",
                extra={"original_type": type(value).__name__},
            )
            return serialized
        except (TypeError, ValueError) as e:
            # Non-serializable objects (custom classes, file handles, etc.)
            # Fall back to original value - let downstream handle the type mismatch
            logger.warning(
                f"Cannot serialize {type(value).__name__} to JSON: {e}. Passing original value.",
                extra={"original_type": type(value).__name__, "error": str(e)},
            )
            return value

    return value


InputSource = Literal["argument", "stdin", "call", "recorded", "env", "settings", "default", "parent"]
"""Where a workflow input's value entered. Only a CLI ``argument`` (the web form spawns the CLI)
is inferred for an ``any`` input; every other source arrives as typed or as raw text."""

_ASCII_WHITESPACE = " \t\n\r\f\v"


def coerce_declared_input(name: str, declared_type: str | None, value: Any, *, source: InputSource) -> Any:
    """Type ``value`` by the input's declared type, once, where it enters — or raise ``InputTypeError``.

    Text reads through ``TypeSpec.parse_text`` (surrounding ASCII whitespace stripped for every
    type but ``string``, whose text is kept exactly). A non-text value must satisfy
    ``TypeSpec.accepts`` — except that a ``string`` takes any scalar as the text ``${x}`` would
    produce (``to_string``: ``True`` → ``"True"``); a container into a ``string`` is an error.
    ``any`` and an untyped input: text from a CLI ``argument`` is inferred losslessly
    (``_infer_lossless``), every other value is kept as given. ``None`` (no value) and
    ``VALIDATION_PLACEHOLDER`` pass through: presence is the caller's rule. A value that already
    fits is returned as the same object, so a second call changes nothing.
    """
    if value is None or value == VALIDATION_PLACEHOLDER:
        return value
    spec = TypeSpec(declared_type if declared_type in CANONICAL_TYPES else "any")
    if spec.name == "any":
        return _infer_lossless(value) if source == "argument" and isinstance(value, str) else value
    if isinstance(value, str):
        fits, typed = spec.parse_text(value if spec.name == "string" else value.strip(_ASCII_WHITESPACE))
    elif spec.name == "string":
        fits, typed = not isinstance(value, (dict, list)), to_string(value)
    else:
        fits, typed = spec.accepts(value), value
    if not fits:
        raise InputTypeError(name=name, declared_type=spec.name, received=value, source=source)
    return typed


def _infer_lossless(text: str) -> Any:
    """``text`` typed only when the value reads back as the same text (decision (d)).

    ``true``, ``42``, ``2.5``, ``[1]``, ``{"a":1}`` type; ``02134``, ``1.10``, ``1e3``, ``TRUE``,
    ``yes``, `` 42``, ``[1, 2]``, ``null`` and a quoted JSON string stay text — the
    comparison is against compact JSON, the canonical rendering.
    """
    ok, parsed = try_parse_json(text)
    if not ok or parsed is None or isinstance(parsed, str):
        return text
    try:
        canonical = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError:  # -Infinity
        return text
    return parsed if canonical == text else text
