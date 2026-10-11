"""Parameter parsing utilities for CLI commands."""

from __future__ import annotations

import json
from typing import Any


def infer_type(value: str) -> Any:
    """Guess a type for a node parameter typed on ``pflow probe``'s command line.

    Never used for workflow inputs: their declared type decides (``coerce_declared_input``).

    Supports:
    - Booleans: 'true', 'false' (case-insensitive)
    - Numbers: integers and floats
    - JSON: arrays and objects starting with '[' or '{'
    - Strings: everything else (default)

    Args:
        value: String value to infer type from

    Returns:
        Inferred Python value with appropriate type
    """
    # Boolean detection
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    # Number detection
    try:
        # Try integer first (more restrictive)
        if "." not in value and "e" not in value.lower():
            return int(value)
        # Then try float
        return float(value)
    except ValueError:
        pass

    # JSON detection for arrays and objects
    if value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # Default to string
    return value


def parse_workflow_params(args: tuple[str, ...]) -> dict[str, str]:
    """Split ``name=value`` arguments on the first ``=``; arguments without one are skipped.

    Values stay text: a workflow input is typed by its declaration at the input boundary
    (``prepare_inputs``), never guessed here.
    """
    return {key: value for key, _, value in (arg.partition("=") for arg in args if "=" in arg)}


def format_param_value(value: Any) -> str:
    """Convert a Python value to its CLI string representation.

    The inverse of the declared-type coercer for every type but ``any``: compact JSON
    for a container, ``true``/``false`` for a boolean, text as is — so the token reads
    back as the same value through ``coerce_declared_input``.

    Args:
        value: The Python value to convert

    Returns:
        The string representation for CLI usage (WITHOUT shell escaping)
    """
    if isinstance(value, bool):
        # Booleans become lowercase strings
        return str(value).lower()

    elif isinstance(value, (int, float)):
        # Numbers convert directly
        return str(value)

    elif isinstance(value, (list, dict)):
        # JSON types need compact serialization
        return json.dumps(value, separators=(",", ":"))

    elif isinstance(value, str):
        # Strings pass through as-is
        return value

    else:
        # Fallback for other types
        return str(value)
