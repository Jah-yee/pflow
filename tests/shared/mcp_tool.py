"""A virtual MCP tool for tests: registered like ``pflow mcp sync`` registers one, called
through a stub at the MCP boundary (the connection pool, and the no-pool fallback).

Everything between the workflow and the boundary — validation, compilation, template
resolution, ``MCPNode.prep`` — is the real code, so a test reads exactly the arguments
the tool would have been sent.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from mcp.types import CallToolResult, TextContent

from pflow.mcp.manager import MCPServerManager
from pflow.mcp.pool import MCPConnectionPool
from pflow.nodes.mcp.node import MCPNode
from pflow.registry import Registry


def register_mcp_tool(server: str, tool: str, params: dict[str, str]) -> str:
    """Register ``mcp-<server>-<tool>`` with ``params`` (name → type) in the isolated test
    registry and add ``server`` to the isolated MCP config; returns the node type."""
    node_type = f"mcp-{server}-{tool}"
    entry = {
        "class_name": "MCPNode",
        "module": "pflow.nodes.mcp.node",
        "file_path": "virtual://mcp",
        "type": "mcp",
        "interface": {
            "description": f"Test tool {tool}",
            "inputs": [],
            "params": [{"key": key, "type": type_, "description": key} for key, type_ in params.items()],
            "outputs": [{"key": "result", "type": "any", "description": "The tool's result"}],
            "actions": ["default"],
            "mcp_metadata": {"server": server, "tool": tool, "original_schema": {}, "output_schema": {}},
        },
    }
    registry = Registry()
    registry.save(registry.load(include_filtered=True) | {node_type: entry})
    MCPServerManager().add_server(server, command="true")
    return node_type


@contextmanager
def stub_mcp_calls(result: str = "ok") -> Iterator[list[dict[str, Any]]]:
    """Record the arguments of every MCP tool call; each call returns ``result`` as text."""
    calls: list[dict[str, Any]] = []

    def call_tool(self: Any, server_name: str, tool: str, arguments: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        calls.append(dict(arguments))
        return CallToolResult(content=[TextContent(type="text", text=result)], isError=False)

    async def exec_async(self: Any, prep_res: dict[str, Any]) -> dict[str, Any]:
        calls.append(dict(prep_res["arguments"]))
        return {"result": result}

    with (
        patch.object(MCPConnectionPool, "call_tool", call_tool),
        patch.object(MCPNode, "_exec_async", exec_async),
        patch.object(MCPNode, "_load_server_config", return_value={"command": "true"}),
    ):
        yield calls
