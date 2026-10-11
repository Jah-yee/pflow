"""External file reference resolution for workflow IR.

Detects file path references in node parameters, reads the files,
and substitutes their content into the IR before compilation.
This enables prompts, code, batch configs, etc. to live in
external files while being validated identically to inline content.
"""

import logging
from pathlib import Path
from typing import Any

from pflow.core.workflow.template_surfaces import param_mode
from pflow.core.yaml_utils import safe_load_preserving_templates

logger = logging.getLogger(__name__)

# Extensions that trigger file reference detection
FILE_REFERENCE_EXTENSIONS = frozenset({
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
})

# Params where file content is YAML-parsed, not raw text.
# Matches the is_yaml_config distinction in markdown_parser.py:489-501
YAML_PARSED_PARAMS = frozenset({"batch", "output_schema", "headers"})

# Only these params can be resolved as file references.
# A subset of code block tags from markdown_parser.py _CODE_BLOCK_TAG_TO_PARAM.
# Other params like 'file_path', 'workflow', 'url', etc. contain path/URL VALUES,
# not content to inline. Content params like 'system', 'content', 'body' could be
# added here in the future but are not yet file-resolvable.
# Note: "batch" is handled separately in _resolve_batch_file_references(), not here.
FILE_RESOLVABLE_PARAMS = frozenset({
    "command",
    "code",
    "prompt",
    "source",
    "stdin",
    "headers",
    "output_schema",
})


def is_file_reference(value: Any) -> bool:
    """Detect whether a parameter value is a file path reference.

    A value is treated as a file reference if it:
    - Is a non-empty string without newlines, spaces, or template variables
    - Starts with './' or '../' (always matches regardless of extension), OR
    - Contains '/' and ends with a recognized file extension

    Args:
        value: The parameter value to check

    Returns:
        True if the value looks like a file path reference
    """
    if not isinstance(value, str) or not value:
        return False

    # Template variables are never file references
    if "${" in value:
        return False

    # Multi-line strings are never file paths
    if "\n" in value:
        return False

    # Strings with spaces are commands or prose, not file paths
    if " " in value:
        return False

    # URLs are never file references
    if "://" in value:
        return False

    # Explicit relative paths
    if value.startswith("./") or value.startswith("../"):
        return True

    # Path with recognized extension
    if "/" in value:
        suffix = Path(value).suffix.lower()
        if suffix in FILE_REFERENCE_EXTENSIONS:
            return True

    return False


def is_param_file_reference(node_type: str | None, key: str, value: Any) -> bool:
    """``is_file_reference`` for one param (or batch-item key) of a node of ``node_type``.

    A body (``param_mode`` → ``"body"``) holding a ``$`` is a command, never a path:
    ``./scripts/$NAME.sh`` reads a shell variable. Every param walk that detects file
    references asks this, never ``is_file_reference`` directly.
    """
    if param_mode(node_type, key) == "body" and isinstance(value, str) and "$" in value:
        return False
    return is_file_reference(value)


def is_workflow_file_reference(value: str) -> bool:
    """Detect if a workflow param value is a file path (vs. a saved workflow name).

    Used by WorkflowExecutor and dependency discovery to distinguish
    `- workflow: ./sub.pflow.md` (file reference) from
    `- workflow: my-helper` (saved workflow name).

    Args:
        value: The workflow parameter value to check

    Returns:
        True if the value looks like a file path
    """
    return "/" in value or "\\" in value or value.endswith(".pflow.md") or value.startswith(".")


def resolve_file_references(ir_dict: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Resolve file references in workflow IR, modifying it in place.

    Walks all node params and batch items. When a value matches the
    file reference heuristic and the file exists, reads the file and
    substitutes its content. For YAML params (batch, output_schema,
    headers), the file content is parsed with
    ``yaml_utils.safe_load_preserving_templates`` so unquoted ``${...}``
    templates in flow style parse like block form (issue #482).

    Args:
        ir_dict: The workflow IR dict (modified in place)
        base_dir: Directory to resolve relative paths from
                  (typically the workflow file's parent directory)

    Returns:
        The same ir_dict (for chaining convenience)

    Raises:
        FileNotFoundError: If a detected file reference doesn't exist
        yaml.YAMLError: If a YAML file fails to parse
    """
    for node in ir_dict.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id", "unknown")

        # A. Resolve file references in node params
        params = node.get("params", {})
        if not isinstance(params, dict):
            continue
        node_type = node.get("type")
        for key, value in list(params.items()):
            if key not in FILE_RESOLVABLE_PARAMS:
                continue
            if is_param_file_reference(node_type, key, value):
                content = _load_file(node, key, value, base_dir)
                if key in YAML_PARSED_PARAMS:
                    params[key] = safe_load_preserving_templates(content)
                else:
                    params[key] = content
                logger.debug(f"Resolved file reference: node '{node_id}', param '{key}' <- {value}")

        # B. Resolve file references in batch config
        batch = node.get("batch")
        if batch is not None:
            _resolve_batch_file_references(node, batch, base_dir)

    return ir_dict


def _resolve_batch_file_references(
    node: dict[str, Any],
    batch: Any,
    base_dir: Path,
) -> None:
    """Resolve file references in batch config.

    Handles two cases:
    - Batch is a string file reference (entire config in external file)
    - Batch is a dict with inline items containing file references
    """
    # B1. Batch is a string — entire config in external file
    if isinstance(batch, str) and is_file_reference(batch):
        original_value = batch
        content = _load_file(node, "batch", batch, base_dir)
        node["batch"] = safe_load_preserving_templates(content)
        logger.debug(f"Resolved file reference: node '{node.get('id')}', batch <- {original_value}")
        batch = node["batch"]  # Update local var for B2 fall-through

    # B2. Batch is a dict with inline items — check for file refs in items
    if isinstance(batch, dict):
        items = batch.get("items")
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    for key, value in list(item.items()):
                        if key not in FILE_RESOLVABLE_PARAMS:
                            continue
                        if is_param_file_reference(node.get("type"), key, value):
                            location = f"batch.items[{i}].{key}"
                            content = _load_file(node, location, value, base_dir)
                            if key in YAML_PARSED_PARAMS:
                                item[key] = safe_load_preserving_templates(content)
                            else:
                                item[key] = content
                            logger.debug(f"Resolved file reference: node '{node.get('id')}', {location} <- {value}")


def _load_file(node: dict[str, Any], location: str, file_ref: str, base_dir: Path) -> str:
    """Read ``file_ref`` (relative to ``base_dir``) and record its provenance on ``node``.

    ``location`` is a param name or ``batch`` / ``batch.items[i].<key>``. The node records the
    authored reference under ``_source_files[location]`` (what diagnostics show) and the resolved
    absolute path under ``_resolved_files[location]`` (what a code step sees as ``__file__``).

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    resolved_path = (base_dir / file_ref).resolve()

    if not resolved_path.is_file():
        raise FileNotFoundError(
            f"File reference in node '{node.get('id', 'unknown')}', param '{location}' not found: {file_ref}\n"
            f"  Resolved to: {resolved_path}\n"
            f"  Relative to: {base_dir}"
        )

    content = resolved_path.read_text(encoding="utf-8")
    node.setdefault("_source_files", {})[location] = file_ref
    node.setdefault("_resolved_files", {})[location] = str(resolved_path)
    return content


def has_file_references(ir_dict: dict[str, Any]) -> list[str]:
    """Scan IR for file references without resolving them.

    Returns a list of file reference strings found (empty if none).
    Useful for detecting file references in inline workflows where
    there's no file path context for resolution.
    """
    found: list[str] = []
    for node in ir_dict.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        _collect_param_file_refs(node_type, node.get("params", {}), found)
        _collect_batch_file_refs(node_type, node.get("batch"), found)
    return found


def _collect_param_file_refs(node_type: str | None, params: Any, found: list[str]) -> None:
    """Collect file references from node params."""
    if not isinstance(params, dict):
        return
    for key, value in params.items():
        if key in FILE_RESOLVABLE_PARAMS and is_param_file_reference(node_type, key, value):
            found.append(value)


def _collect_batch_file_refs(node_type: str | None, batch: Any, found: list[str]) -> None:
    """Collect file references from batch config."""
    if isinstance(batch, str) and is_file_reference(batch):
        found.append(batch)
    if isinstance(batch, dict):
        items = batch.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    _collect_param_file_refs(node_type, item, found)


def get_base_dir(initial_params: dict[str, Any]) -> Path:
    """Derive base directory for file resolution from initial params.

    Uses _pflow_workflow_file if available, otherwise falls back to CWD.

    Args:
        initial_params: The initial params dict (may contain _pflow_workflow_file)

    Returns:
        Path to use as base directory for resolving relative file references
    """
    workflow_file = initial_params.get("_pflow_workflow_file")
    if workflow_file:
        return Path(workflow_file).parent
    return Path.cwd()
