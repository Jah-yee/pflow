"""An MCP tool's input schema becomes registry params with the type the server declared (#811).

The type is read through ``$ref``, ``Optional[X]`` (an ``anyOf`` with null) and array items, and an
object's fields travel with the param as ``structure``. The type is not only displayed: validation
and template resolution read it, so a wrong one changed what reached the server. Schemas below are
the ones FastMCP (pydantic) generates, copied verbatim, plus hand-written shapes other servers send.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import click.testing
import pytest

from pflow.cli.commands.mcp import mcp
from pflow.cli.main import cli
from pflow.core.exceptions import PflowError
from pflow.mcp import MCPRegistrar, MCPServerManager
from pflow.mcp.schema import pflow_params
from pflow.registry import Registry
from pflow.registry.context_builder import build_component_context

FIELD = {
    "properties": {"name": {"title": "Name", "type": "string"}, "value": {"title": "Value", "type": "string"}},
    "required": ["name", "value"],
    "title": "Field",
    "type": "object",
}
DEFS = {"Field": FIELD, "Color": {"enum": ["red", "blue"], "title": "Color", "type": "string"}}


def _tool_schema(prop: dict[str, Any], *, required: bool = True) -> dict[str, Any]:
    schema: dict[str, Any] = {"$defs": DEFS, "type": "object", "properties": {"p": prop}}
    if required:
        schema["required"] = ["p"]
    return schema


# Four required params with optional ones between them: the snippet sets all four and no other.
FILL_SCHEMA = {
    "$defs": DEFS
    | {
        "Opts": {
            "properties": {"mode": {"enum": ["draft", "submit"], "type": "string", "default": "draft"}},
            "type": "object",
        }
    },
    "type": "object",
    "properties": {
        "fields": {"items": {"$ref": "#/$defs/Field"}, "type": "array"},
        "color": {"$ref": "#/$defs/Color", "default": "red"},
        "title": {"type": "string"},
        "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None},
        "count": {"type": "integer"},
        "opts": {"$ref": "#/$defs/Opts"},
        "tags": {"items": {"type": "string"}, "type": "array"},
    },
    "required": ["fields", "title", "count", "tags"],
}
REQUIRED_SNIPPET = [
    "- type: mcp-fixture-fill",
    "- fields: value",
    "- title: ${previous-step.response}",
    "- count: 0",
    "- tags: ${previous-step.response}",
]

# (row id, property schema, required, type on main before #811, type now, whether shell text validates)
ROWS: list[tuple[str, dict[str, Any], bool, str, str, bool]] = [
    # Types that were wrong: ``str`` for a value the server reads as an object or number.
    ("model", {"$ref": "#/$defs/Field"}, True, "str", "dict", True),
    (
        "optional_model",
        {"anyOf": [{"$ref": "#/$defs/Field"}, {"type": "null"}], "default": None},
        False,
        "str",
        "dict",
        True,
    ),
    ("optional_int", {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None}, False, "str", "int", False),
    ("allof_model", {"allOf": [{"$ref": "#/$defs/Field"}], "description": "wrapped"}, True, "str", "dict", True),
    ("int_or_str", {"anyOf": [{"type": "integer"}, {"type": "string"}]}, True, "str", "int|str", True),
    ("any", {"title": "P"}, True, "str", "any", True),
    # Arrays gain their item type; the runtime compares the outer type only, so no verdict moves.
    ("list_of_models", {"items": {"$ref": "#/$defs/Field"}, "type": "array"}, True, "list", "list[dict]", True),
    ("list_of_str", {"items": {"type": "string"}, "type": "array"}, True, "list", "list[str]", True),
    ("nullable_list", {"type": ["array", "null"], "items": {"type": "string"}}, False, "list", "list[str]", True),
    # Already right: unchanged.
    ("int", {"type": "integer"}, True, "int", "int", False),
    ("str", {"type": "string"}, True, "str", "str", True),
    ("bare_list", {"items": {}, "type": "array"}, True, "list", "list", True),
    ("literal", {"enum": ["a", "b"], "type": "string"}, True, "str", "str", True),
    ("enum_ref", {"$ref": "#/$defs/Color"}, True, "str", "str", True),
    ("dict", {"additionalProperties": {"type": "integer"}, "type": "object"}, True, "dict", "dict", True),
    # A ``type`` list keeps its first non-null member: the runtime cannot parse JSON text into a union.
    ("type_list", {"type": ["string", "integer"]}, True, "str", "str", True),
    ("object_or_array", {"type": ["object", "array"]}, True, "dict", "dict", True),
]

PROBE_WORKFLOW = """# Probe

Feed shell text into one MCP param.

## Steps

### src

Produce text.

- type: shell

```shell command
printf '%s' 5
```

### call

Call the tool.

- type: {node_type}
- p: ${{src.stdout}}
"""


@pytest.mark.parametrize(
    ("prop", "required", "now", "text_validates"),
    [pytest.param(prop, required, now, ok, id=row) for row, prop, required, _, now, ok in ROWS],
)
def test_each_schema_shape_gets_the_declared_type_and_its_validation_verdict(
    tmp_path: Path, prop: dict[str, Any], required: bool, now: str, text_validates: bool
) -> None:
    entry = MCPRegistrar()._create_registry_entry(
        "fixture", {"name": "probe", "inputSchema": _tool_schema(prop, required=required)}
    )
    registry = Registry()
    registry.save(registry.load(include_filtered=True) | {"mcp-fixture-probe": entry})
    MCPServerManager().add_server("fixture", command="true")

    assert entry["interface"]["params"][0]["type"] == now
    workflow = tmp_path / "probe.pflow.md"
    workflow.write_text(PROBE_WORKFLOW.format(node_type="mcp-fixture-probe"), encoding="utf-8")
    result = click.testing.CliRunner().invoke(cli, ["--validate-only", str(workflow)])
    # Shell text fails only a param the server declares numeric — as it always has for a plain int.
    assert (result.exit_code == 0) is text_validates, result.output
    if not text_validates:
        assert f"has type 'str' but parameter expects '{now}'" in result.output


def test_object_and_list_params_carry_their_fields_as_structure() -> None:
    params = {
        p["key"]: p
        for p in pflow_params({
            "$defs": DEFS,
            "type": "object",
            "properties": {
                "fields": {"items": {"$ref": "#/$defs/Field"}, "type": "array"},
                "color": {"$ref": "#/$defs/Color", "description": "Pen colour", "default": "red"},
            },
            "required": ["fields"],
        })
    }

    assert params["fields"] == {
        "key": "fields",
        "type": "list[dict]",
        "required": True,
        "structure": {
            "name": {"type": "str", "required": True},
            "value": {"type": "str", "required": True},
        },
    }
    # The property's own description and default win; the enum lives on the referenced definition.
    assert params["color"] == {
        "key": "color",
        "type": "str",
        "required": False,
        "description": "Pen colour",
        "default": "red",
        "enum": ["red", "blue"],
    }


def test_an_optional_list_of_objects_keeps_its_item_fields() -> None:
    (param,) = pflow_params({
        "$defs": DEFS,
        "type": "object",
        "properties": {"p": {"anyOf": [{"items": {"$ref": "#/$defs/Field"}, "type": "array"}, {"type": "null"}]}},
    })

    assert param["type"] == "list[dict]"
    assert list(param["structure"]) == ["name", "value"]


def test_a_property_that_is_not_a_schema_fails_conversion() -> None:
    """Sync then reports the tool and keeps the server's prior entries (``registrar.sync_servers``),
    rather than registering the tool without a required param."""
    with pytest.raises(PflowError, match="property schemas must be objects or booleans"):
        pflow_params({"type": "object", "properties": {"query": None}, "required": ["query"]})
    # ``true`` is a schema: any value.
    assert pflow_params({"type": "object", "properties": {"x": True}}) == [
        {"key": "x", "type": "any", "required": False}
    ]


def test_self_referencing_schema_stops_at_the_depth_cap() -> None:
    tree = {
        "properties": {"label": {"type": "string"}, "children": {"items": {"$ref": "#/$defs/Tree"}, "type": "array"}},
        "type": "object",
    }
    (param,) = pflow_params({
        "$defs": {"Tree": tree},
        "type": "object",
        "properties": {"tree": {"$ref": "#/$defs/Tree"}},
    })

    level1 = param["structure"]["children"]
    level2 = level1["structure"]["children"]
    level3 = level2["structure"]["children"]
    assert (param["type"], level1["type"], level2["type"]) == ("dict", "list[dict]", "list[dict]")
    assert level3 == {"type": "list", "required": False}


@pytest.mark.parametrize(
    ("prop", "expected"),
    [
        # Two object shapes are still an object: no union, so Pass 6's container check still applies.
        pytest.param({"anyOf": [{"$ref": "#/$defs/Field"}, {"type": "object"}]}, "dict", id="two-objects"),
        # ``list[int|str]`` would read as a union to the runtime's bare-name checks.
        pytest.param(
            {"type": "array", "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]}}, "list", id="list-of-union"
        ),
        # Not a JSON Schema type: the long-standing text fallback.
        pytest.param({"type": "quantum"}, "str", id="unknown-type"),
        # A reference cycle through a combinator terminates.
        pytest.param({"$ref": "#/$defs/Loop"}, "any", id="ref-cycle"),
    ],
)
def test_edge_shapes(prop: dict[str, Any], expected: str) -> None:
    defs = DEFS | {"Loop": {"anyOf": [{"$ref": "#/$defs/Loop"}]}}
    (param,) = pflow_params({"$defs": defs, "type": "object", "properties": {"p": prop}})

    assert param["type"] == expected


def test_component_context_shows_fields_and_a_snippet_of_every_required_param() -> None:
    entry = MCPRegistrar()._create_registry_entry("fixture", {"name": "fill", "inputSchema": FILL_SCHEMA})
    registry = Registry()
    registry.save(registry.load(include_filtered=True) | {"mcp-fixture-fill": entry})

    context = build_component_context(["mcp-fixture-fill"], [], registry.load())
    assert isinstance(context, str)

    assert '"fields": [\n    {\n      "name": "str",' in context
    assert "- fields[].name (str) (required)" in context
    assert "- opts.mode (str) (default: draft) (one of: draft, submit)" in context
    # Every required param, in schema order, and nothing that has a default or is optional.
    snippet = context.split("**Usage in .pflow.md:**", 1)[1].strip().splitlines()
    assert [line.strip() for line in snippet[-5:]] == REQUIRED_SNIPPET


# ── Real stdio server ──────────────────────────────────────────────────────────

SERVER_SOURCE = """
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

SCHEMAS = {schemas!r}
server = Server("param-fixture")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name=name, description=name, inputSchema=schema) for name, schema in SCHEMAS.items()]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # No JSON pre-parsing (FastMCP has some): report exactly what arrived.
    return [types.TextContent(type="text", text=type(arguments.get("p")).__name__)]


async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


anyio.run(main)
"""


@pytest.fixture
def synced_server(tmp_path: Path) -> None:
    schemas = {
        "fill": FILL_SCHEMA,
        "model": _tool_schema({"$ref": "#/$defs/Field"}),
        "optional_model": _tool_schema({"anyOf": [{"$ref": "#/$defs/Field"}, {"type": "null"}]}, required=False),
    }
    script = tmp_path / "param_server.py"
    script.write_text(textwrap.dedent(SERVER_SOURCE.format(schemas=schemas)), encoding="utf-8")
    MCPServerManager().save({"mcpServers": {"fixture": {"command": sys.executable, "args": [str(script)]}}})
    result = click.testing.CliRunner().invoke(mcp, ["sync", "fixture"])
    assert result.exit_code == 0, result.output


@pytest.mark.usefixtures("synced_server")
def test_describe_shows_fields_defaults_and_a_snippet_of_required_params() -> None:
    result = click.testing.CliRunner().invoke(mcp, ["describe", "mcp-fixture-fill"])

    assert result.exit_code == 0, result.output
    parameters = result.output.split("Parameters:\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert parameters[:9] == [
        "  - fields: list[dict] (required)",
        "      - name: str (required)",
        "      - value: str (required)",
        "  - color: str (default: red) (one of: red, blue)",
        "  - title: str (required)",
        "  - limit: int (default: null)",
        "  - count: int (required)",
        "  - opts: dict",
        "      - mode: str (default: draft) (one of: draft, submit)",
    ]
    snippet = [line.strip() for line in result.output.split("Usage in .pflow.md:\n", 1)[1].strip().splitlines()]
    assert snippet[-5:] == REQUIRED_SNIPPET


OBJECT_WORKFLOW = """# Pass

Pass an object into an object param.

## Steps

### src

Produce the object.

{source}

### call

Call the tool.

- type: mcp-fixture-{tool}
- p: ${{src.{field}}}
"""
CODE_SOURCE = '- type: code\n\n```python code\nresult: dict = {"name": "a", "value": "b"}\n```'
SHELL_SOURCE = """- type: shell\n\n```shell command\nprintf '%s' '{"name": "a", "value": "b"}'\n```"""


@pytest.mark.usefixtures("synced_server")
@pytest.mark.parametrize("tool", ["model", "optional_model"])
@pytest.mark.parametrize(
    ("source", "field"), [(CODE_SOURCE, "result"), (SHELL_SOURCE, "stdout")], ids=["code", "shell"]
)
def test_an_object_reaches_the_server_as_an_object(tmp_path: Path, tool: str, source: str, field: str) -> None:
    """Typed ``str``, the param sent a code step's dict — and shell JSON — to the server as text."""
    workflow = tmp_path / "pass.pflow.md"
    workflow.write_text(OBJECT_WORKFLOW.format(source=source, tool=tool, field=field), encoding="utf-8")

    result = click.testing.CliRunner(mix_stderr=False).invoke(cli, ["--output-format", "json", str(workflow)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["result"] == {"result": "dict"}
