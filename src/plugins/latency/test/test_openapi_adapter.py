import asyncio

import httpx
import pytest

from latency.access.openapi_adapter import (
    OpenApiAdapter,
    OpenApiInvocationError,
    OpenApiLoadError,
)


def _schema(*, operations):
    return {
        "openapi": "3.1.0",
        "info": {"title": "test", "version": "1"},
        "paths": operations,
        "components": {
            "schemas": {
                "ListRequest": {
                    "type": "object",
                    "properties": {
                        "page_num": {"type": "integer"},
                    },
                }
            }
        },
    }


def _adapter(schema):
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/openapi.json"
        return httpx.Response(200, json=schema)

    return OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )


def test_load_indexes_only_enabled_read_only_operations():
    schema = _schema(
        operations={
            "/log_file/{log_file_id}": {
                "parameters": [
                    {
                        "name": "log_file_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_log_file",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "parameters": [
                        {
                            "name": "verbose",
                            "in": "query",
                            "schema": {"type": "boolean"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                },
            },
            "/internal": {
                "get": {
                    "operationId": "internal_operation",
                    "responses": {"200": {"description": "ok"}},
                }
            },
        }
    )

    adapter = asyncio.run(_adapter(schema).load())
    operation = adapter.get_operation("get_log_file")

    assert set(adapter.operations) == {"get_log_file"}
    assert operation.method == "GET"
    assert operation.path == "/log_file/{log_file_id}"
    assert [item.name for item in operation.path_parameters] == ["log_file_id"]
    assert [item.name for item in operation.query_parameters] == ["verbose"]
    adapter.verify_required_operations({"get_log_file"})


def test_load_keeps_json_request_schema_reference():
    schema = _schema(
        operations={
            "/log_file/list": {
                "post": {
                    "operationId": "list_log_files",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ListRequest"
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    adapter = asyncio.run(_adapter(schema).load())
    operation = adapter.get_operation("list_log_files")

    assert operation.request_body_required is True
    assert operation.request_schema == {
        "$ref": "#/components/schemas/ListRequest"
    }
    assert adapter.resolve_ref(operation.request_schema["$ref"])["type"] == "object"


def test_build_input_schema_merges_path_query_and_body():
    schema = _schema(
        operations={
            "/log_file/list/{kb_id}": {
                "post": {
                    "operationId": "list_log_files",
                    "description": "List log files.",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "parameters": [
                        {
                            "name": "kb_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "verbose",
                            "in": "query",
                            "schema": {"type": "boolean"},
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ListRequest"
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    schema["components"]["schemas"]["ListRequest"]["required"] = ["page_num"]

    adapter = asyncio.run(_adapter(schema).load())
    input_schema = adapter.build_input_schema("list_log_files")

    assert input_schema == {
        "type": "object",
        "properties": {
            "page_num": {"type": "integer", "minimum": 1},
            "kb_id": {"type": "string"},
            "verbose": {"type": "boolean"},
        },
        "additionalProperties": False,
        "required": ["page_num", "kb_id"],
    }
    assert adapter.get_operation("list_log_files").description == "List log files."


def test_build_input_schema_rewrites_nested_component_references():
    schema = _schema(
        operations={
            "/search": {
                "post": {
                    "operationId": "search",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "sort": {
                                            "$ref": "#/components/schemas/SortField"
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    schema["components"]["schemas"]["SortField"] = {
        "type": "object",
        "properties": {"field": {"type": "string"}},
    }

    adapter = asyncio.run(_adapter(schema).load())
    input_schema = adapter.build_input_schema("search")

    assert input_schema["properties"]["sort"] == {
        "$ref": "#/$defs/SortField"
    }
    assert input_schema["$defs"]["SortField"]["type"] == "object"


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (
            {
                "operationId": "unsafe",
                "x-mcp-enabled": True,
                "responses": {"200": {"description": "ok"}},
            },
            "not marked read-only",
        ),
        (
            {
                "operationId": "unsafe",
                "x-mcp-enabled": True,
                "x-mcp-read-only": True,
                "responses": {"200": {"description": "ok"}},
            },
            "disallowed HTTP method",
        ),
    ],
)
def test_load_rejects_unsafe_operations(operation, message):
    schema = _schema(operations={"/unsafe": {"delete": operation}})

    with pytest.raises(OpenApiLoadError, match=message):
        asyncio.run(_adapter(schema).load())


def test_load_rejects_duplicate_operation_ids():
    enabled = {
        "operationId": "duplicate",
        "x-mcp-enabled": True,
        "x-mcp-read-only": True,
        "responses": {"200": {"description": "ok"}},
    }
    schema = _schema(
        operations={
            "/first": {"get": enabled},
            "/second": {"post": enabled},
        }
    )

    with pytest.raises(OpenApiLoadError, match="Duplicate MCP operationId"):
        asyncio.run(_adapter(schema).load())


def test_verify_required_operations_reports_all_missing_ids():
    adapter = asyncio.run(_adapter(_schema(operations={})).load())

    with pytest.raises(
        OpenApiLoadError,
        match="first_missing, second_missing",
    ):
        adapter.verify_required_operations({"second_missing", "first_missing"})


def test_load_converts_openapi_http_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="not ready")

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenApiLoadError, match="HTTP 503"):
        asyncio.run(adapter.load())


def test_invoke_renders_path_and_query_parameters():
    requests = []
    schema = _schema(
        operations={
            "/log_file/{log_file_id}": {
                "get": {
                    "operationId": "get_log_file",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "parameters": [
                        {
                            "name": "log_file_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "verbose",
                            "in": "query",
                            "schema": {"type": "boolean"},
                        },
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=schema)
        return httpx.Response(
            200,
            json={"code": 200, "result": {"id": "log/1"}},
        )

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.load())
    payload = asyncio.run(
        adapter.invoke(
            "get_log_file",
            {"log_file_id": "log/1", "verbose": True, "ignored_none": None},
        )
    )

    assert payload["result"]["id"] == "log/1"
    assert requests[-1].method == "GET"
    assert requests[-1].url.path == "/log_file/log/1"
    assert requests[-1].url.raw_path == b"/log_file/log%2F1?verbose=true"
    assert requests[-1].url.params["verbose"] == "true"


def test_invoke_sends_and_validates_json_body():
    request_bodies = []
    schema = _schema(
        operations={
            "/log_file/list": {
                "post": {
                    "operationId": "list_log_files",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ListRequest"
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=schema)
        request_bodies.append(request.content)
        return httpx.Response(200, json={"code": 200, "result": {"total": 0}})

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.load())
    asyncio.run(adapter.invoke("list_log_files", {"page_num": 2}))

    assert request_bodies == [b'{"page_num":2}']

    with pytest.raises(OpenApiInvocationError, match="Invalid arguments"):
        asyncio.run(adapter.invoke("list_log_files", {"page_num": "invalid"}))


def test_invoke_rejects_missing_and_unexpected_arguments():
    schema = _schema(
        operations={
            "/log_file/{log_file_id}": {
                "get": {
                    "operationId": "get_log_file",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "parameters": [
                        {
                            "name": "log_file_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    adapter = asyncio.run(_adapter(schema).load())

    with pytest.raises(OpenApiInvocationError, match="required property"):
        asyncio.run(adapter.invoke("get_log_file", {}))
    with pytest.raises(OpenApiInvocationError, match="Additional properties"):
        asyncio.run(
            adapter.invoke(
                "get_log_file",
                {"log_file_id": "log-1", "not_supported": True},
            )
        )


def test_invoke_converts_business_errors():
    schema = _schema(
        operations={
            "/log_file/list": {
                "post": {
                    "operationId": "list_log_files",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=schema)
        return httpx.Response(
            200,
            json={"code": 409, "message": "contract changed"},
        )

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.load())

    with pytest.raises(OpenApiInvocationError, match="business code 409"):
        asyncio.run(adapter.invoke("list_log_files", {}))


def test_invoke_applies_agent_defaults_without_changing_backend_schema():
    requests = []
    schema = _schema(
        operations={
            "/aggregated_event/list": {
                "post": {
                    "operationId": "list_latency_events",
                    "x-mcp-enabled": True,
                    "x-mcp-read-only": True,
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "kb_id": {
                                            "anyOf": [
                                                {"type": "string"},
                                                {"type": "null"},
                                            ],
                                            "default": None,
                                        },
                                        "stat_type": {
                                            "anyOf": [
                                                {"type": "string"},
                                                {"type": "null"},
                                            ],
                                            "default": "ave",
                                        },
                                        "sort_fields": {
                                            "anyOf": [
                                                {"type": "array"},
                                                {"type": "null"},
                                            ],
                                            "default": None,
                                        },
                                        "operation": {
                                            "anyOf": [
                                                {"type": "string"},
                                                {"type": "null"},
                                            ],
                                            "default": None,
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=schema)
        requests.append(request)
        return httpx.Response(200, json={"code": 200, "result": {}})

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.load())

    input_schema = adapter.build_input_schema("list_latency_events")
    assert input_schema["properties"]["stat_type"]["default"] == "p99"
    backend_properties = schema["paths"]["/aggregated_event/list"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]["properties"]
    assert backend_properties["stat_type"]["default"] == "ave"

    asyncio.run(adapter.invoke("list_latency_events", {"kb_id": "kb-1"}))
    assert requests[-1].content == (
        b'{"kb_id":"kb-1","stat_type":"p99","sort_fields":'
        b'[{"field":"total_latency","order":"desc"}]}'
    )

    with pytest.raises(OpenApiInvocationError, match="Invalid arguments"):
        asyncio.run(adapter.invoke("list_latency_events", {}))
