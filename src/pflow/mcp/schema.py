"""Read an MCP tool's JSON Schemas: its input schema as registry params, its output schema as path hints.

Both walks resolve local ``$ref`` pointers the same way; neither contacts a server.
"""

from __future__ import annotations

from typing import Any

from pflow.core.exceptions import PflowError

# A param's nested ``structure`` stops after this many object/array levels, which also ends a
# self-referencing schema (a tree node whose children are tree nodes).
_MAX_PARAM_DEPTH = 3
_MAX_DECLARED_OUTPUT_DEPTH = 10
_MAX_DECLARED_OUTPUT_PATHS = 100

_PYTHON_TYPE_NAMES = {
    "string": "str",
    "number": "float",
    "integer": "int",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}


def _resolve_schema_pointer(root_schema: dict, ref: str) -> dict | None:
    """Resolve one local JSON Pointer target."""
    if ref == "#":
        return root_schema
    if not ref.startswith("#/"):
        return None
    target: object = root_schema
    for raw_segment in ref[2:].split("/"):
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or segment not in target:
            return None
        target = target[segment]
    return target if isinstance(target, dict) else None


def resolve_local_ref(root_schema: dict, field_schema: dict) -> dict:
    """Resolve chained local JSON Pointer references with a cycle guard."""
    current = field_schema
    visited: set[str] = set()
    while isinstance(ref := current.get("$ref"), str) and ref not in visited:
        visited.add(ref)
        target = _resolve_schema_pointer(root_schema, ref)
        if target is None:
            break
        current = target
    return current


def _array_items(schema: dict) -> dict | None:
    """Return an array's item schema when its type declaration includes array."""
    schema_type = schema.get("type")
    is_array = schema_type == "array" or (isinstance(schema_type, list) and "array" in schema_type)
    items = schema.get("items")
    return items if is_array and isinstance(items, dict) else None


def _combinator_branches(schema: dict) -> list[dict]:
    """Return the branches of a schema's ``anyOf`` / ``oneOf`` unions."""
    branches: list[dict] = []
    for keyword in ("anyOf", "oneOf"):
        alternatives = schema.get(keyword)
        if isinstance(alternatives, list):
            branches.extend(item for item in alternatives if isinstance(item, dict))
    return branches


# ── Input schema → registry params ─────────────────────────────────────────────


def pflow_params(input_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """The registry params of an MCP tool's input schema, one per top-level property.

    Each param carries ``key``, ``type`` and ``required``, plus ``description``, ``default`` and
    ``enum`` when the schema states them. An object, or an array of objects, also carries its
    fields as ``structure`` — the same shape a node docstring's indented fields produce.
    """
    if input_schema.get("type") != "object":
        return []
    required = input_schema.get("required", [])
    return [
        {"key": name, **_param_shape(input_schema, prop, required=name in required, depth=0)}
        for name, prop in _properties(input_schema).items()
    ]


def _properties(schema: dict) -> dict[str, dict]:
    """A schema's properties by name. A boolean schema reads as ``{}``; anything else that is not a
    schema fails, so sync reports the tool and keeps the server's prior entries rather than
    registering it without the param."""
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise PflowError(f"'properties' must be an object, got {properties!r}")
    malformed = {name: prop for name, prop in properties.items() if not isinstance(prop, (dict, bool))}
    if malformed:
        raise PflowError(f"property schemas must be objects or booleans, got {malformed!r}")
    return {name: prop if isinstance(prop, dict) else {} for name, prop in properties.items()}


def _param_shape(root: dict, schema: dict, *, required: bool, depth: int) -> dict[str, Any]:
    """One property's type, required flag, description, default, enum and (nested) structure."""
    resolved = _concrete_schema(root, schema)
    param: dict[str, Any] = {"type": _param_type(root, resolved, depth), "required": required}
    for keyword in ("description", "default", "enum"):
        # The property's own keyword wins over the target's: ``{"$ref": ..., "description": ...}``.
        if keyword in schema:
            param[keyword] = schema[keyword]
        elif keyword in resolved:
            param[keyword] = resolved[keyword]
    if depth < _MAX_PARAM_DEPTH and (structure := _structure(root, resolved, depth)):
        param["structure"] = structure
    return param


def _concrete_schema(root: dict, schema: dict) -> dict:
    """The schema a value must match: ``$ref`` followed, and an optional value's (or a lone
    ``allOf``'s) single non-null branch taken — ``Optional[X]`` reads as ``X``."""
    seen: set[int] = set()
    schema = resolve_local_ref(root, schema)
    while "type" not in schema and id(schema) not in seen and len(branches := _non_null_branches(root, schema)) == 1:
        seen.add(id(schema))
        schema = branches[0]
    return schema


def _non_null_branches(root: dict, schema: dict) -> list[dict]:
    alternatives = _combinator_branches(schema)
    all_of = schema.get("allOf")
    if not alternatives and isinstance(all_of, list) and len(all_of) == 1 and isinstance(all_of[0], dict):
        alternatives = all_of
    resolved = [resolve_local_ref(root, branch) for branch in alternatives]
    return [branch for branch in resolved if branch.get("type") != "null"]


def _param_type(root: dict, schema: dict, depth: int) -> str:
    """The registry type of a concrete schema: ``str``, ``dict``, ``list[str]``, ``list[dict]``, ``int|str``.

    An ``anyOf`` / ``oneOf`` union names each distinct non-null member; one with a single distinct
    member (two object branches) is that member. No declared shape at all (``{}``) accepts
    anything: ``any``; a type name outside JSON Schema keeps the text fallback ``str``.
    """
    declared = schema.get("type")
    if isinstance(declared, list):
        # Its first non-null member, never a union: the runtime cannot parse JSON text into a
        # union, so ``["object", "array"]`` as ``dict|list`` would stop parsing what ``dict`` parses.
        declared = next((t for t in declared if t != "null"), "null")
    if isinstance(declared, str):
        name = _PYTHON_TYPE_NAMES.get(declared, "str")
    elif depth < _MAX_PARAM_DEPTH and (branches := _non_null_branches(root, schema)):
        return _union([_param_type(root, _concrete_schema(root, branch), depth + 1) for branch in branches])
    elif "properties" in schema:
        name = "dict"
    elif "items" in schema:
        name = "list"
    else:
        return "any"
    if name == "list" and depth < _MAX_PARAM_DEPTH and isinstance(items := schema.get("items"), dict):
        item_type = _param_type(root, _concrete_schema(root, items), depth + 1)
        # ``list[int|str]`` would read as a union to the runtime's bare-name type checks.
        if item_type != "any" and "|" not in item_type:
            return f"list[{item_type}]"
    return name


def _union(names: list[str]) -> str:
    return "|".join(dict.fromkeys(names))


def _structure(root: dict, schema: dict, depth: int) -> dict[str, Any]:
    """An object's fields, or an array's item fields, keyed by name."""
    items = schema.get("items")
    if isinstance(items, dict) and "properties" not in schema:
        schema = _concrete_schema(root, items)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return {}
    required = schema.get("required", [])
    # Display only, unlike a top-level param: a field that is not a schema is left out, never fails sync.
    return {
        name: _param_shape(root, prop if isinstance(prop, dict) else {}, required=name in required, depth=depth + 1)
        for name, prop in properties.items()
        if isinstance(prop, (dict, bool))
    }


# ── Output schema → declared result paths ──────────────────────────────────────


def _schema_type_label(schema: dict) -> str:
    """Return a readable JSON Schema type label."""
    schema_type = schema.get("type")
    if schema_type is None:
        if "properties" in schema:
            schema_type = "object"
        elif "items" in schema:
            schema_type = "array"
        else:
            schema_type = "any"
    if isinstance(schema_type, list):
        return " | ".join(str(item) for item in schema_type)
    if schema_type == "any":
        for keyword in ("anyOf", "oneOf"):
            alternatives = schema.get(keyword)
            if isinstance(alternatives, list):
                labels = [_schema_type_label(item) for item in alternatives if isinstance(item, dict)]
                if labels:
                    return " | ".join(dict.fromkeys(labels))
    return str(schema_type)


def _schema_children(field_schema: dict, path: str) -> list[tuple[dict, str, bool]]:
    """Return nested schemas with their display paths and path-emission flag."""
    children: list[tuple[dict, str, bool]] = []
    properties = field_schema.get("properties")
    if isinstance(properties, dict):
        children.extend(
            (child_schema, f"{path}.{name}", True)
            for name, child_schema in properties.items()
            if isinstance(child_schema, dict)
        )

    items = _array_items(field_schema)
    if items is not None:
        children.append((items, f"{path}[0]", True))

    # Union branches describe the same parent path, so only emit their children.
    children.extend((branch, path, False) for branch in _combinator_branches(field_schema))
    return children


def declared_output_paths(schema: dict, prefix: str = "result") -> tuple[list[tuple[str, str]], bool]:
    """Flatten reliable JSON Schema properties into result-prefixed ``(path, type label)`` hints,
    and whether the walk was truncated."""
    paths: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    truncated = False

    def walk(field_schema: dict, path: str, *, include_path: bool = True, depth: int = 0) -> None:
        nonlocal truncated
        # Bound recursive/branching schemas while keeping ordinary nested tool
        # results useful and terminal output predictable.
        if depth > _MAX_DECLARED_OUTPUT_DEPTH:
            truncated = True
            return
        field_schema = resolve_local_ref(schema, field_schema)

        if include_path and path not in seen_paths:
            if len(paths) >= _MAX_DECLARED_OUTPUT_PATHS:
                truncated = True
                return
            paths.append((path, _schema_type_label(field_schema)))
            seen_paths.add(path)

        # Optional structured values are commonly represented as an object
        # branch plus a null branch. Traverse branches without repeating the
        # parent path so their nested properties remain statically discoverable.
        for child_schema, child_path, emit_path in _schema_children(field_schema, path):
            walk(child_schema, child_path, include_path=emit_path, depth=depth + 1)

    walk(schema, prefix, include_path=False)
    return paths, truncated
