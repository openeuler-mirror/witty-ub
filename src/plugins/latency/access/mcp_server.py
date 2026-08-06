# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Dynamic read-only MCP tools generated from the latency OpenAPI contract."""

from __future__ import annotations

import os
from typing import Any, Mapping

from mcp import types
from mcp.server.fastmcp import FastMCP

from latency.access.openapi_adapter import OpenApiAdapter


_INSTRUCTIONS = (
    "Use these read-only tools to investigate parsed latency and connectivity "
    "fault data. Confirm that parsing completed before concluding that no fault "
    "exists. Empty query results are not proof that the system is healthy."
)

mcp = FastMCP("witty-ub-latency", instructions=_INSTRUCTIONS)
_server = mcp._mcp_server

READ_ONLY_TOOL = types.ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_MAX_READ_BYTES = 5 * 1024 * 1024
_READ_FILE_TOOL = types.Tool(
    name="read_file",
    description=(
        "Read a local text file referenced during an investigation. "
        "Files larger than 5 MB are rejected."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the text file.",
            }
        },
        "required": ["file_path"],
        "additionalProperties": False,
    },
    annotations=READ_ONLY_TOOL,
)

_adapter: OpenApiAdapter | None = None


async def _get_adapter() -> OpenApiAdapter:
    global _adapter
    if _adapter is None:
        loaded = OpenApiAdapter()
        await loaded.load()
        if "read_file" in loaded.operations:
            raise RuntimeError(
                "Backend operationId conflicts with local MCP tool: read_file"
            )
        _adapter = loaded
    return _adapter


async def _list_dynamic_tools() -> list[types.Tool]:
    adapter = await _get_adapter()
    tools = [
        types.Tool(
            name=operation.operation_id,
            description=operation.description,
            inputSchema=adapter.build_input_schema(operation.operation_id),
            annotations=READ_ONLY_TOOL,
        )
        for operation in adapter.operations.values()
    ]
    tools.sort(key=lambda tool: tool.name)
    tools.append(_READ_FILE_TOOL)
    return tools


async def _call_dynamic_tool(
    name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    if name == "read_file":
        file_path = arguments.get("file_path")
        if not isinstance(file_path, str):
            raise ValueError("file_path must be a string")
        return await read_file(file_path)

    adapter = await _get_adapter()
    return await adapter.invoke(name, arguments)


@_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List OpenAPI-derived tools plus explicitly implemented local tools."""
    return await _list_dynamic_tools()


@_server.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch every OpenAPI-derived tool through the common adapter."""
    return await _call_dynamic_tool(name, arguments)


async def read_file(file_path: str) -> dict[str, Any]:
    """Read a bounded local text file used as diagnostic evidence."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    size = os.path.getsize(file_path)
    if size > _MAX_READ_BYTES:
        raise ValueError(
            f"File too large ({size} bytes): exceeds {_MAX_READ_BYTES} byte limit"
        )
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    return {"file_path": file_path, "size_bytes": size, "content": content}


class MCPServer:
    """MCP server entry point kept for compatibility with existing launchers."""

    @staticmethod
    def start() -> None:
        transport = os.getenv("LATENCY_MCP_TRANSPORT", "stdio")
        if transport not in {"stdio", "sse", "streamable-http"}:
            raise ValueError(
                "LATENCY_MCP_TRANSPORT must be stdio, sse or streamable-http"
            )
        mcp.run(transport=transport)


if __name__ == "__main__":
    MCPServer.start()
