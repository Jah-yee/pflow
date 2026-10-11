"""Discovery records each tool's schemas exactly as the server sent them (#756).

The tests run discovery against a real stdio MCP server. A tool definition whose schema
cannot be read (the SDK 2.x shape spells it ``input_schema``) must fail discovery, so
``pflow mcp sync`` reports the error and the server keeps its prior tools, rather than
registering every tool without parameters.
"""

import json
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click.testing
import pytest
from mcp import ClientSession

from pflow.cli.commands.mcp import mcp
from pflow.mcp import MCPDiscovery, MCPRegistrar, MCPServerManager
from pflow.registry import Registry

CLICK_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {"ref": {"type": "string", "description": "Element reference"}},
    "required": ["ref"],
    "additionalProperties": False,
}
ZERO_ARG_SCHEMA = {"type": "object", "properties": {}}
RESULT_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}

SERVER_SOURCE = f"""
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

server = Server("schema-fixture")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="click", description="Click", inputSchema={CLICK_SCHEMA!r}, outputSchema={RESULT_SCHEMA!r}),
        types.Tool(name="close", description="Close", inputSchema={ZERO_ARG_SCHEMA!r}, outputSchema={{}}),
        types.Tool(name="anything", inputSchema={{}}),
    ]


async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


anyio.run(main)
"""


@pytest.fixture
def server_config(tmp_path: Path) -> dict[str, Any]:
    script = tmp_path / "schema_server.py"
    script.write_text(textwrap.dedent(SERVER_SOURCE), encoding="utf-8")
    return {"command": sys.executable, "args": [str(script)]}


@pytest.fixture
def sdk2_shaped_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve tool definitions the way SDK 2.x exposes them: snake_case schema attributes."""

    async def list_tools(self: ClientSession, *args: Any, **kwargs: Any) -> SimpleNamespace:
        tool = SimpleNamespace(name="click", description="Click", input_schema=CLICK_SCHEMA, output_schema=None)
        return SimpleNamespace(tools=[tool])

    monkeypatch.setattr(ClientSession, "list_tools", list_tools)


def test_discovery_records_schemas_exactly_as_the_server_sent_them(server_config: dict[str, Any]) -> None:
    tools = {tool["name"]: tool for tool in MCPDiscovery().discover_tools("fixture", server_config=server_config)}

    assert tools["click"]["inputSchema"] == CLICK_SCHEMA
    assert tools["click"]["outputSchema"] == RESULT_SCHEMA
    assert tools["close"]["inputSchema"] == ZERO_ARG_SCHEMA
    # Empty schemas are stored as sent: not replaced by a substitute, not dropped.
    assert tools["close"]["outputSchema"] == {}
    assert tools["anything"]["inputSchema"] == {}
    assert "outputSchema" not in tools["anything"]
    assert tools["anything"]["description"] == "MCP tool from fixture"


def test_unreadable_output_schema_fails_discovery(
    server_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A readable input schema does not excuse an output schema the SDK spells differently."""

    async def list_tools(self: ClientSession, *args: Any, **kwargs: Any) -> SimpleNamespace:
        tool = SimpleNamespace(name="click", description="Click", inputSchema=CLICK_SCHEMA, output_schema=RESULT_SCHEMA)
        return SimpleNamespace(tools=[tool])

    monkeypatch.setattr(ClientSession, "list_tools", list_tools)

    with pytest.raises(RuntimeError, match="has no attribute 'outputSchema'"):
        MCPDiscovery().discover_tools("fixture", server_config=server_config)


@pytest.mark.usefixtures("sdk2_shaped_tools")
def test_sync_reports_unreadable_schema_and_keeps_prior_tools(server_config: dict[str, Any]) -> None:
    MCPServerManager().save({"mcpServers": {"fixture": server_config}})
    registry = Registry()
    prior = MCPRegistrar()._create_registry_entry("fixture", {"name": "click", "inputSchema": CLICK_SCHEMA})
    registry.save({"mcp-fixture-click": prior})

    result = click.testing.CliRunner().invoke(mcp, ["sync", "fixture"])

    assert result.exit_code != 0
    assert "has no attribute 'inputSchema'" in result.output
    persisted = registry.load(include_filtered=True)["mcp-fixture-click"]
    assert persisted == json.loads(json.dumps(prior))
    assert persisted["interface"]["params"][0]["key"] == "ref"
