# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""HTTP client used by the MCP tools to query the latency service."""

from __future__ import annotations

import os
from typing import Any

import httpx


class LatencyApiError(RuntimeError):
    """Raised when the latency API cannot provide a usable response."""


class LatencyApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("LATENCY_API_BASE_URL", "http://127.0.0.1:9772")
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("LATENCY_API_TIMEOUT_SECONDS", "30")
        )
        self.transport = transport

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LatencyApiError(
                f"Latency API request timed out after {self.timeout_seconds:g}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LatencyApiError(
                f"Latency API returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise LatencyApiError(f"Latency API is unavailable: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise LatencyApiError("Latency API returned a non-JSON response") from exc

        if not isinstance(payload, dict):
            raise LatencyApiError("Latency API returned an invalid JSON object")

        code = payload.get("code", 200)
        if code != 200:
            message = str(payload.get("message", "unknown business error"))[:500]
            raise LatencyApiError(f"Latency API returned business code {code}: {message}")

        return payload
