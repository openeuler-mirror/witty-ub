import asyncio
from types import SimpleNamespace

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from latency.access import mcp_server
from latency.access.mcp_contract import McpContractError


class FakeAdapter:
    def __init__(self) -> None:
        self.operations = {
            "get_log_file": SimpleNamespace(
                operation_id="get_log_file",
                description="Get one log file.",
            ),
            "list_log_files": SimpleNamespace(
                operation_id="list_log_files",
                description="List log files.",
            ),
        }
        self.calls = []

    def build_input_schema(self, operation_id):
        if operation_id == "get_log_file":
            return {
                "type": "object",
                "properties": {"log_file_id": {"type": "string"}},
                "required": ["log_file_id"],
                "additionalProperties": False,
            }
        return {
            "type": "object",
            "properties": {"page_num": {"type": "integer", "default": 1}},
            "additionalProperties": False,
        }

    async def invoke(self, operation_id, arguments):
        self.calls.append((operation_id, arguments))
        return {
            "code": 200,
            "result": {"operation_id": operation_id, "arguments": arguments},
        }


def test_mcp_lists_openapi_derived_and_local_tools(monkeypatch):
    fake = FakeAdapter()
    monkeypatch.setattr(mcp_server, "_adapter", fake)

    async def inspect_tools():
        async with create_connected_server_and_client_session(
            mcp_server.mcp
        ) as session:
            result = await session.list_tools()
            return {tool.name: tool for tool in result.tools}

    tools = asyncio.run(inspect_tools())

    assert set(tools) == {"get_log_file", "list_log_files", "read_file"}
    assert "parse status" in tools["get_log_file"].description
    assert tools["get_log_file"].inputSchema["required"] == ["log_file_id"]
    assert tools["get_log_file"].annotations.readOnlyHint is True
    assert tools["read_file"].inputSchema["additionalProperties"] is False


def test_mcp_dispatches_dynamic_tool_to_adapter(monkeypatch):
    fake = FakeAdapter()
    monkeypatch.setattr(mcp_server, "_adapter", fake)

    async def invoke_tool():
        async with create_connected_server_and_client_session(
            mcp_server.mcp
        ) as session:
            return await session.call_tool(
                "get_log_file",
                {"log_file_id": "log-1"},
            )

    result = asyncio.run(invoke_tool())

    assert result.isError is False
    assert result.structuredContent == {
        "code": 200,
        "result": {
            "operation_id": "get_log_file",
            "arguments": {"log_file_id": "log-1"},
        },
    }
    assert fake.calls == [
        ("get_log_file", {"log_file_id": "log-1"}),
    ]


def test_mcp_validates_dynamic_tool_input(monkeypatch):
    fake = FakeAdapter()
    monkeypatch.setattr(mcp_server, "_adapter", fake)

    async def invoke_tool():
        async with create_connected_server_and_client_session(
            mcp_server.mcp
        ) as session:
            return await session.call_tool(
                "get_log_file",
                {"log_file_id": 123},
            )

    result = asyncio.run(invoke_tool())

    assert result.isError is True
    assert "Input validation error" in result.content[0].text
    assert fake.calls == []


def test_read_file_returns_bounded_text_file(tmp_path):
    target = tmp_path / "sample.log"
    target.write_text("diagnostic evidence", encoding="utf-8")

    result = asyncio.run(mcp_server.read_file(str(target)))

    assert result == {
        "file_path": str(target),
        "size_bytes": len("diagnostic evidence"),
        "content": "diagnostic evidence",
    }


def test_read_file_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        asyncio.run(mcp_server.read_file(str(tmp_path / "missing.log")))


def test_mcp_rejects_agent_policy_for_missing_operation(monkeypatch):
    fake = FakeAdapter()
    fake.operations = {}

    async def fake_load():
        return fake

    monkeypatch.setattr(mcp_server, "_adapter", None)
    monkeypatch.setattr(mcp_server, "OpenApiAdapter", lambda: fake)
    monkeypatch.setattr(fake, "load", fake_load, raising=False)

    with pytest.raises(McpContractError, match="unavailable operations"):
        asyncio.run(mcp_server._get_adapter())
