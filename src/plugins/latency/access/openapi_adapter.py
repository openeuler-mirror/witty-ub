# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Load and index the read-only FastAPI operations exposed to the MCP server."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Literal, Mapping
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

ParameterLocation = Literal["path", "query"]
_HTTP_METHODS = ("get", "post", "put", "patch", "delete")
_READ_ONLY_HTTP_METHODS = frozenset({"GET", "POST"})


class OpenApiLoadError(RuntimeError):
    """Raised when the backend OpenAPI contract cannot be loaded or indexed."""


class OpenApiInvocationError(RuntimeError):
    """Raised when an indexed backend operation cannot be invoked safely."""


@dataclass(frozen=True)
class OpenApiParameter:
    """One path or query parameter accepted by an exposed operation."""

    name: str
    location: ParameterLocation
    required: bool
    schema: Mapping[str, Any]


@dataclass(frozen=True)
class OpenApiOperation:
    """An MCP-enabled backend operation discovered from OpenAPI."""

    operation_id: str
    description: str
    method: str
    path: str
    path_parameters: tuple[OpenApiParameter, ...]
    query_parameters: tuple[OpenApiParameter, ...]
    request_schema: Mapping[str, Any] | None
    request_body_required: bool


class OpenApiAdapter:
    """Load OpenAPI, build MCP schemas and invoke enabled read-only operations."""

    def __init__(
        self,
        *,
        openapi_url: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved_base_url = (
            base_url
            or os.getenv("LATENCY_API_BASE_URL")
            or "http://127.0.0.1:9772"
        ).rstrip("/")
        self.base_url = resolved_base_url
        self.openapi_url = (
            openapi_url
            or f"{resolved_base_url}/openapi.json"
        )
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("LATENCY_API_TIMEOUT_SECONDS", "30")
        )
        self.transport = transport
        self._schema: dict[str, Any] | None = None
        self._operations: dict[str, OpenApiOperation] = {}

    @property
    def schema(self) -> Mapping[str, Any]:
        """Return the loaded OpenAPI document."""
        if self._schema is None:
            raise OpenApiLoadError("OpenAPI schema has not been loaded")
        return self._schema

    @property
    def operations(self) -> Mapping[str, OpenApiOperation]:
        """Return MCP-enabled operations indexed by stable operation ID."""
        return self._operations

    async def load(self) -> "OpenApiAdapter":
        """Fetch, validate and index the backend OpenAPI document."""
        schema = await self._fetch_schema()
        operations = self._index_operations(schema)
        self._schema = schema
        self._operations = operations
        return self

    def get_operation(self, operation_id: str) -> OpenApiOperation:
        """Return one exposed operation or raise a contract error."""
        try:
            return self._operations[operation_id]
        except KeyError as exc:
            raise OpenApiLoadError(
                f"Required backend operation is unavailable: {operation_id}"
            ) from exc

    def verify_required_operations(self, operation_ids: set[str]) -> None:
        """Fail if the loaded contract does not provide every required operation."""
        missing = sorted(operation_ids - self._operations.keys())
        if missing:
            raise OpenApiLoadError(
                "Required backend operations are unavailable: " + ", ".join(missing)
            )

    def resolve_ref(self, reference: str) -> Mapping[str, Any]:
        """Resolve a local JSON reference against the loaded OpenAPI document."""
        return self._resolve_local_ref(self.schema, reference)

    def build_input_schema(self, operation_id: str) -> dict[str, Any]:
        """Build a self-contained MCP input schema for one OpenAPI operation."""
        operation = self.get_operation(operation_id)
        properties: dict[str, Any] = {}
        required: list[str] = []
        definitions: dict[str, Any] = {}

        if operation.request_schema is not None:
            body_schema = self._dereference_top_level(operation.request_schema)
            if body_schema.get("type") != "object":
                raise OpenApiLoadError(
                    f"MCP operation request body must be an object: {operation_id}"
                )
            body_properties = body_schema.get("properties", {})
            body_required = body_schema.get("required", [])
            if not isinstance(body_properties, Mapping) or not isinstance(
                body_required,
                list,
            ):
                raise OpenApiLoadError(
                    f"MCP operation request schema is invalid: {operation_id}"
                )
            for name, value_schema in body_properties.items():
                if not isinstance(name, str) or not isinstance(value_schema, Mapping):
                    raise OpenApiLoadError(
                        f"MCP operation request property is invalid: {operation_id}"
                    )
                properties[name] = self._rewrite_schema_refs(
                    value_schema,
                    definitions,
                )
            required.extend(
                name for name in body_required if isinstance(name, str)
            )

        for parameter in (
            *operation.path_parameters,
            *operation.query_parameters,
        ):
            if parameter.name in properties:
                raise OpenApiLoadError(
                    f"MCP operation has an ambiguous argument "
                    f"{parameter.name}: {operation_id}"
                )
            properties[parameter.name] = self._rewrite_schema_refs(
                parameter.schema,
                definitions,
            )
            if parameter.required:
                required.append(parameter.name)

        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            input_schema["required"] = list(dict.fromkeys(required))
        if definitions:
            input_schema["$defs"] = definitions
        return input_schema

    async def invoke(
        self,
        operation_id: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Invoke one indexed operation using its current OpenAPI definition."""
        operation = self.get_operation(operation_id)
        remaining = {
            name: value
            for name, value in arguments.items()
            if value is not None
        }
        self._validate_value(
            remaining,
            self.build_input_schema(operation_id),
            operation_id,
            "arguments",
            standalone=True,
        )

        path = operation.path
        for parameter in operation.path_parameters:
            value = self._pop_required_parameter(
                remaining,
                parameter,
                operation_id,
            )
            self._validate_value(value, parameter.schema, operation_id, parameter.name)
            path = path.replace(
                "{" + parameter.name + "}",
                quote(str(value), safe=""),
            )

        query: dict[str, Any] = {}
        for parameter in operation.query_parameters:
            if parameter.name not in remaining:
                if parameter.required:
                    raise OpenApiInvocationError(
                        f"Missing required argument for {operation_id}: "
                        f"{parameter.name}"
                    )
                continue
            value = remaining.pop(parameter.name)
            self._validate_value(value, parameter.schema, operation_id, parameter.name)
            query[parameter.name] = value

        body: dict[str, Any] | None
        if operation.request_schema is not None:
            body = remaining
            if not body and not operation.request_body_required:
                body = None
            if body is not None:
                self._validate_value(
                    body,
                    operation.request_schema,
                    operation_id,
                    "request body",
                )
        else:
            body = None
            if remaining:
                unexpected = ", ".join(sorted(remaining))
                raise OpenApiInvocationError(
                    f"Unexpected arguments for {operation_id}: {unexpected}"
                )

        return await self._invoke_http(
            operation=operation,
            path=path,
            query=query,
            body=body,
        )

    async def _fetch_schema(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(self.openapi_url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenApiLoadError(
                f"OpenAPI request timed out after {self.timeout_seconds:g}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise OpenApiLoadError(
                f"OpenAPI endpoint returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OpenApiLoadError(f"OpenAPI endpoint is unavailable: {exc}") from exc

        try:
            schema = response.json()
        except ValueError as exc:
            raise OpenApiLoadError(
                "OpenAPI endpoint returned a non-JSON response"
            ) from exc

        if not isinstance(schema, dict):
            raise OpenApiLoadError("OpenAPI endpoint returned an invalid JSON object")
        if not isinstance(schema.get("openapi"), str):
            raise OpenApiLoadError("OpenAPI document is missing the openapi version")
        if not isinstance(schema.get("paths"), dict):
            raise OpenApiLoadError("OpenAPI document is missing the paths object")
        return schema

    @staticmethod
    def _pop_required_parameter(
        arguments: dict[str, Any],
        parameter: OpenApiParameter,
        operation_id: str,
    ) -> Any:
        try:
            return arguments.pop(parameter.name)
        except KeyError as exc:
            raise OpenApiInvocationError(
                f"Missing required argument for {operation_id}: {parameter.name}"
            ) from exc

    def _validate_value(
        self,
        value: Any,
        value_schema: Mapping[str, Any],
        operation_id: str,
        argument_name: str,
        *,
        standalone: bool = False,
    ) -> None:
        try:
            if standalone:
                validator = Draft202012Validator(value_schema)
            else:
                validator = Draft202012Validator(self.schema).evolve(
                    schema=value_schema
                )
            validator.validate(value)
        except ValidationError as exc:
            location = ".".join(str(item) for item in exc.absolute_path)
            suffix = f" at {location}" if location else ""
            raise OpenApiInvocationError(
                f"Invalid {argument_name} for {operation_id}{suffix}: {exc.message}"
            ) from exc
        except SchemaError as exc:
            raise OpenApiLoadError(
                f"Invalid OpenAPI schema for {operation_id}: {exc.message}"
            ) from exc

    async def _invoke_http(
        self,
        *,
        operation: OpenApiOperation,
        path: str,
        query: Mapping[str, Any],
        body: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.request(
                    operation.method,
                    path,
                    params=query,
                    json=body,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} timed out after "
                f"{self.timeout_seconds:g}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} returned HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} is unavailable: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} returned non-JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} returned "
                "an invalid JSON object"
            )

        code = payload.get("code", 200)
        if code != 200:
            message = str(payload.get("message", "unknown business error"))[:500]
            raise OpenApiInvocationError(
                f"Backend operation {operation.operation_id} returned "
                f"business code {code}: {message}"
            )
        return payload

    def _index_operations(
        self,
        schema: dict[str, Any],
    ) -> dict[str, OpenApiOperation]:
        operations: dict[str, OpenApiOperation] = {}

        for path, path_item_value in schema["paths"].items():
            if not isinstance(path, str) or not isinstance(path_item_value, dict):
                raise OpenApiLoadError("OpenAPI paths contains an invalid path item")
            path_item = self._resolve_object(schema, path_item_value)

            for method_name in _HTTP_METHODS:
                operation_value = path_item.get(method_name)
                if operation_value is None:
                    continue
                if not isinstance(operation_value, dict):
                    raise OpenApiLoadError(
                        f"OpenAPI operation is invalid: {method_name.upper()} {path}"
                    )
                operation_document = self._resolve_object(schema, operation_value)
                if not operation_document.get("x-mcp-enabled", False):
                    continue

                method = method_name.upper()
                if operation_document.get("x-mcp-read-only") is not True:
                    raise OpenApiLoadError(
                        f"MCP operation is not marked read-only: {method} {path}"
                    )
                if method not in _READ_ONLY_HTTP_METHODS:
                    raise OpenApiLoadError(
                        f"MCP operation uses a disallowed HTTP method: {method} {path}"
                    )

                operation_id = operation_document.get("operationId")
                if not isinstance(operation_id, str) or not operation_id.strip():
                    raise OpenApiLoadError(
                        f"MCP operation has no stable operationId: {method} {path}"
                    )
                if operation_id in operations:
                    raise OpenApiLoadError(
                        f"Duplicate MCP operationId: {operation_id}"
                    )

                operations[operation_id] = self._build_operation(
                    schema=schema,
                    method=method,
                    path=path,
                    path_item=path_item,
                    operation_id=operation_id,
                    operation_document=operation_document,
                )

        return operations

    def _dereference_top_level(
        self,
        value_schema: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        reference = value_schema.get("$ref")
        if reference is None:
            return value_schema
        if not isinstance(reference, str):
            raise OpenApiLoadError("OpenAPI schema $ref must be a string")
        return self.resolve_ref(reference)

    def _rewrite_schema_refs(
        self,
        value: Any,
        definitions: dict[str, Any],
    ) -> Any:
        if isinstance(value, list):
            return [
                self._rewrite_schema_refs(item, definitions)
                for item in value
            ]
        if not isinstance(value, Mapping):
            return value

        reference = value.get("$ref")
        if isinstance(reference, str):
            prefix = "#/components/schemas/"
            if reference.startswith(prefix):
                name = reference.removeprefix(prefix)
                if not name:
                    raise OpenApiLoadError(
                        f"OpenAPI schema reference is invalid: {reference}"
                    )
                if name not in definitions:
                    definitions[name] = {}
                    definitions[name] = self._rewrite_schema_refs(
                        self.resolve_ref(reference),
                        definitions,
                    )
                rewritten = {"$ref": f"#/$defs/{name}"}
                rewritten.update(
                    {
                        key: self._rewrite_schema_refs(item, definitions)
                        for key, item in value.items()
                        if key != "$ref"
                    }
                )
                return rewritten

            return self._rewrite_schema_refs(
                self.resolve_ref(reference),
                definitions,
            )

        return {
            key: self._rewrite_schema_refs(item, definitions)
            for key, item in value.items()
        }

    def _build_operation(
        self,
        *,
        schema: Mapping[str, Any],
        method: str,
        path: str,
        path_item: Mapping[str, Any],
        operation_id: str,
        operation_document: Mapping[str, Any],
    ) -> OpenApiOperation:
        parameters: dict[tuple[str, str], OpenApiParameter] = {}
        combined_parameters = [
            *self._parameter_list(path_item, method, path),
            *self._parameter_list(operation_document, method, path),
        ]

        for parameter_value in combined_parameters:
            parameter = self._resolve_object(schema, parameter_value)
            location = parameter.get("in")
            if location not in {"path", "query"}:
                continue

            name = parameter.get("name")
            parameter_schema = parameter.get("schema", {})
            if not isinstance(name, str) or not name:
                raise OpenApiLoadError(
                    f"OpenAPI parameter has no name: {method} {path}"
                )
            if not isinstance(parameter_schema, dict):
                raise OpenApiLoadError(
                    f"OpenAPI parameter schema is invalid: {method} {path} {name}"
                )

            parsed = OpenApiParameter(
                name=name,
                location=location,
                required=bool(parameter.get("required", False)),
                schema=parameter_schema,
            )
            parameters[(location, name)] = parsed

        request_schema, request_body_required = self._request_body(
            schema,
            operation_document,
            method,
            path,
        )
        return OpenApiOperation(
            operation_id=operation_id,
            description=str(
                operation_document.get("description")
                or operation_document.get("summary")
                or operation_id.replace("_", " ")
            ),
            method=method,
            path=path,
            path_parameters=tuple(
                parameter
                for (location, _), parameter in parameters.items()
                if location == "path"
            ),
            query_parameters=tuple(
                parameter
                for (location, _), parameter in parameters.items()
                if location == "query"
            ),
            request_schema=request_schema,
            request_body_required=request_body_required,
        )

    @staticmethod
    def _parameter_list(
        document: Mapping[str, Any],
        method: str,
        path: str,
    ) -> list[dict[str, Any]]:
        values = document.get("parameters", [])
        if not isinstance(values, list) or not all(
            isinstance(value, dict) for value in values
        ):
            raise OpenApiLoadError(
                f"OpenAPI parameters are invalid: {method} {path}"
            )
        return values

    def _request_body(
        self,
        schema: Mapping[str, Any],
        operation_document: Mapping[str, Any],
        method: str,
        path: str,
    ) -> tuple[Mapping[str, Any] | None, bool]:
        request_body_value = operation_document.get("requestBody")
        if request_body_value is None:
            return None, False
        if not isinstance(request_body_value, dict):
            raise OpenApiLoadError(
                f"OpenAPI request body is invalid: {method} {path}"
            )

        request_body = self._resolve_object(schema, request_body_value)
        content = request_body.get("content", {})
        if not isinstance(content, dict):
            raise OpenApiLoadError(
                f"OpenAPI request body content is invalid: {method} {path}"
            )
        json_content = content.get("application/json")
        if not isinstance(json_content, dict):
            raise OpenApiLoadError(
                f"MCP operation has no application/json request body: {method} {path}"
            )
        request_schema = json_content.get("schema")
        if not isinstance(request_schema, dict):
            raise OpenApiLoadError(
                f"MCP operation has no valid request schema: {method} {path}"
            )
        return request_schema, bool(request_body.get("required", False))

    def _resolve_object(
        self,
        schema: Mapping[str, Any],
        value: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        reference = value.get("$ref")
        if reference is None:
            return value
        if not isinstance(reference, str):
            raise OpenApiLoadError("OpenAPI $ref must be a string")
        return self._resolve_local_ref(schema, reference)

    @staticmethod
    def _resolve_local_ref(
        schema: Mapping[str, Any],
        reference: str,
    ) -> Mapping[str, Any]:
        if not reference.startswith("#/"):
            raise OpenApiLoadError(
                f"External OpenAPI references are not supported: {reference}"
            )

        current: Any = schema
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, Mapping) or part not in current:
                raise OpenApiLoadError(
                    f"OpenAPI reference cannot be resolved: {reference}"
                )
            current = current[part]

        if not isinstance(current, Mapping):
            raise OpenApiLoadError(
                f"OpenAPI reference does not point to an object: {reference}"
            )
        return current
