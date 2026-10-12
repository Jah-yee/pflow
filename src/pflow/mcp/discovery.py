"""MCP tool discovery for pflow."""

import asyncio
import contextlib
import logging
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, TextIO

from pflow.mcp.auth_utils import build_auth_headers, expand_env_vars_nested

from .manager import MCPServerManager

if TYPE_CHECKING:
    from mcp.types import Tool

logger = logging.getLogger(__name__)

DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 60


def _tool_definition(tool: "Tool", server_name: str) -> dict[str, Any]:
    """Return one discovered tool as pflow's tool definition, schemas exactly as the server sent them.

    Schemas are read as attributes, never probed with ``hasattr``: an SDK that renames
    them (2.x spells ``input_schema``) must fail discovery, which keeps the server's
    prior tools, rather than register every tool without parameters (#756).
    """
    tool_def: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description or f"MCP tool from {server_name}",
        "server": server_name,
        "inputSchema": tool.inputSchema,
    }
    if tool.outputSchema is not None:
        tool_def["outputSchema"] = tool.outputSchema
    return tool_def


class MCPDiscovery:
    """Discovers tools from MCP servers.

    This class connects to MCP servers and discovers their available tools,
    converting them to a format suitable for the pflow registry.
    """

    def __init__(self, manager: MCPServerManager | None = None):
        """Initialize MCPDiscovery.

        Args:
            manager: MCP server manager instance. Creates default if not provided.
        """
        self.manager = manager or MCPServerManager()

    @contextlib.contextmanager
    def _get_stderr_handler(self, verbose: bool) -> Iterator[TextIO]:
        """Get stderr handler for MCP server output.

        Args:
            verbose: Whether to show server stderr

        Yields:
            File-like object for stderr output
        """
        import os

        if verbose:
            yield sys.stderr
        else:
            # Properly manage devnull file handle
            with open(os.devnull, "w", encoding="utf-8") as devnull:
                yield devnull

    def discover_tools(
        self,
        server_name: str,
        verbose: bool = False,
        *,
        server_config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Discover tools from an MCP server (synchronous wrapper).

        Args:
            server_name: Name of the configured MCP server
            verbose: Whether to show server output to stderr
            server_config: Optional raw configuration snapshot. When supplied,
                discovery uses it instead of re-reading the manager.

        Returns:
            List of tool definitions with metadata

        Raises:
            ValueError: If server not found in configuration
            RuntimeError: If discovery fails
        """
        if server_config is None:
            server_config = self.manager.get_server(server_name)

        if not server_config:
            available = ", ".join(self.manager.list_servers()) or "none"
            raise ValueError(f"MCP server '{server_name}' not found. Available servers: {available}")

        timeout = server_config.get("timeout", DEFAULT_DISCOVERY_TIMEOUT_SECONDS)
        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._discover_async(server_name, server_config, verbose),
                    timeout=timeout,
                )
            )
        except Exception as e:
            from pflow.mcp.errors import describe_mcp_error

            diagnostic = describe_mcp_error(e, timeout=timeout)
            logger.debug("Discovery failed for %s: %s", server_name, diagnostic.message, exc_info=True)
            raise RuntimeError(f"Tool discovery failed for {server_name}: {diagnostic.message}") from e

    async def _discover_async(
        self, server_name: str, server_config: dict[str, Any], verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Async implementation of tool discovery with transport routing.

        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary
            verbose: Whether to show server output to stderr

        Returns:
            List of tool definitions
        """
        # Expand env vars in entire config (checks os.environ and settings.json)
        server_config = expand_env_vars_nested(
            server_config,
            include_settings=True,
            raise_on_missing=True,
        )

        # Standard format: use "type" field, default to stdio if not present
        transport_type = server_config.get("type", "stdio")

        if transport_type == "http":
            return await self._discover_async_http(server_name, server_config)
        elif transport_type == "stdio" or transport_type is None:
            return await self._discover_async_stdio(server_name, server_config, verbose)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    async def _discover_async_stdio(
        self, server_name: str, server_config: dict[str, Any], verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Stdio transport discovery implementation.

        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary
            verbose: Whether to show server output to stderr

        Returns:
            List of tool definitions
        """
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        # Get env vars (already expanded by _discover_async)
        env = server_config.get("env", {})
        if not isinstance(env, dict):
            env = {}

        # Prepare server parameters
        params = StdioServerParameters(
            command=server_config["command"], args=server_config.get("args", []), env=env if env else None
        )

        logger.info(f"Connecting to MCP server '{server_name}'...")

        # Use the stderr handler context manager for proper file management
        with self._get_stderr_handler(verbose) as errlog:
            # Now use the configured errlog with stdio_client
            async with stdio_client(params, errlog=errlog) as (read, write), ClientSession(read, write) as session:
                # Initialize handshake
                await session.initialize()
                logger.debug(f"Initialized connection to {server_name}")

                # List available tools
                tools_response = await session.list_tools()

                tools_list = [_tool_definition(tool, server_name) for tool in tools_response.tools]

                logger.info(f"Discovered {len(tools_list)} tools from {server_name}")

        return tools_list

    async def _discover_async_http(self, server_name: str, server_config: dict[str, Any]) -> list[dict[str, Any]]:
        """HTTP transport discovery implementation.

        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary

        Returns:
            List of tool definitions
        """
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        url = server_config.get("url")
        if not url:
            raise ValueError(f"HTTP transport requires 'url' in config for server {server_name}")

        # Build authentication headers
        headers = self._build_auth_headers(server_config)

        # Get timeout settings
        timeout = server_config.get("timeout", 30)
        sse_timeout = server_config.get("sse_timeout", 300)

        logger.info(f"Connecting to HTTP MCP server '{server_name}' at {url}...")

        async with (
            streamablehttp_client(url=url, headers=headers, timeout=timeout, sse_read_timeout=sse_timeout) as (
                read,
                write,
                get_session_id,
            ),
            ClientSession(read, write) as session,
        ):
            # Initialize handshake
            await session.initialize()

            session_id = get_session_id()
            logger.debug(f"Initialized HTTP connection to {server_name}, session: {session_id}")

            # List available tools (same as stdio)
            tools_response = await session.list_tools()

            tools_list = [_tool_definition(tool, server_name) for tool in tools_response.tools]

            logger.info(f"Discovered {len(tools_list)} tools from HTTP server {server_name}")

        return tools_list

    def _build_auth_headers(self, config: dict[str, Any]) -> dict[str, str]:
        """Build authentication headers from configuration.

        Args:
            config: Server configuration dictionary

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return build_auth_headers(config)

    def discover_all_servers(self) -> dict[str, list[dict[str, Any]]]:
        """Discover tools from all configured MCP servers.

        Returns:
            Dictionary mapping server names to their tool lists
        """
        all_tools = {}
        servers = self.manager.list_servers()

        for server_name in servers:
            try:
                tools = self.discover_tools(server_name)
                all_tools[server_name] = tools
                logger.info(f"Discovered {len(tools)} tools from {server_name}")
            except Exception:
                logger.debug("Failed to discover tools from %s", server_name, exc_info=True)
                all_tools[server_name] = []  # Empty list for failed servers

        return all_tools
