"""Structural checks on MCP execution parameters.

Values are not inspected, so MCP accepts the values the CLI accepts (#722): pflow never
evaluates an input value (code bodies are never template-resolved, ADR-0016), and a
single-node run's code params are code its caller may run anyway, as with `pflow probe`.
"""

import json
from typing import Any

from pflow.core.validation_utils import get_parameter_validation_error, is_valid_parameter_name

_MAX_PARAMS_BYTES = 1024 * 1024


def validate_execution_parameters(params: dict[str, Any]) -> tuple[bool, str | None]:
    """Check parameter names, JSON-serialisability, and the 1MB serialized size.

    Returns:
        Tuple of (is_valid, error_message)
    """
    for key in params:
        if not is_valid_parameter_name(key):
            return False, get_parameter_validation_error(key, "parameter")

    try:
        serialized = json.dumps(params)
    except Exception as e:
        return False, f"Parameters not JSON serializable: {e}"
    if len(serialized) > _MAX_PARAMS_BYTES:
        return False, "Parameters too large (max 1MB)"
    return True, None
