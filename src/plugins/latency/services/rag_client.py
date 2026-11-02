# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""REST adapter for Witty RAG Core ``release-0.10.2``.

Only protocol details live here: paths, auth header, multipart field names and
response shapes.  Business state stays in ``phenomenon_index``.
"""
from __future__ import annotations

from typing import Any

import httpx
from latency.config import phenomenon as settings

SEARCH_TIMEOUT_SECONDS = 4.5
CONNECT_TIMEOUT_SECONDS = 1.0
READ_TIMEOUT_SECONDS = 3.0


class RAGError(RuntimeError):
    """Base class for adapter failures."""

    kind = "rag_error"


class RAGUnavailableError(RAGError):
    """RAG is unreachable, timed out, or rejected authentication."""

    kind = "unavailable"


class RAGContractError(RAGError):
    """RAG answered but the response violates the frozen contract."""

    kind = "contract"

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(
        SEARCH_TIMEOUT_SECONDS,
        connect=CONNECT_TIMEOUT_SECONDS,
        read=READ_TIMEOUT_SECONDS,
    )


class RAGClient:
    """Async client for the RAG Core REST API."""

    def __init__(self, base_url: str, access_key: str | None = None):
        self._base_url = base_url.rstrip("/")
        self._access_key = access_key

    @classmethod
    def from_env(cls) -> RAGClient:
        base_url = settings.rag_core_url()
        if not base_url:
            raise RAGUnavailableError("RAG_CORE_URL is not configured")
        return cls(base_url, settings.rag_access_key())

    def _headers(self) -> dict[str, str]:
        if not self._access_key:
            return {}
        return {"Authorization": f"Bearer {self._access_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=_timeout(),
                headers=self._headers(),
            ) as client:
                response = await client.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise RAGUnavailableError("RAG request timed out") from exc
        except httpx.HTTPError as exc:
            raise RAGUnavailableError(f"RAG request failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise RAGUnavailableError("RAG rejected the access key")
        if response.status_code >= 500:
            raise RAGUnavailableError(
                f"RAG upstream error {response.status_code}"
            )
        if response.status_code >= 400:
            raise RAGContractError(
                f"RAG contract error {response.status_code}: {response.text[:256]}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RAGContractError("RAG response is not JSON") from exc
        return self._unwrap(payload)

    @staticmethod
    def _unwrap(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RAGContractError("RAG response is not an object")
        code = payload.get("code")
        if code is not None and int(code) != 200:
            if int(code) >= 500:
                raise RAGUnavailableError(f"RAG returned code {code}")
            raise RAGContractError(
                f"RAG returned code {code}", status_code=int(code)
            )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RAGContractError("RAG response has no result object")
        return result

    # ---------------------------------------------------------------- health
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=_timeout()
            ) as client:
                response = await client.get("/health_check")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    # ---------------------------------------------------------------- KB
    async def create_document_kb(self, name: str) -> str:
        result = await self._request(
            "POST",
            "/kb",
            json_body={
                "name": name,
                "owner_id": "witty-ub",
                "owner_name": "witty-ub",
                "meta_data_type": "document",
            },
        )
        kb_id = result.get("kb_id")
        if not kb_id:
            raise RAGContractError("create kb response missing kb_id")
        return str(kb_id)

    async def get_kb(self, kb_id: str) -> dict[str, Any]:
        result = await self._request("GET", f"/kb/{kb_id}")
        kb = result.get("knowledge_base")
        if not isinstance(kb, dict):
            raise RAGContractError("get kb response missing knowledge_base")
        return kb

    async def delete_kb(self, kb_id: str) -> bool:
        try:
            result = await self._request("DELETE", f"/kb/{kb_id}")
        except RAGContractError as exc:
            if exc.status_code == 404:
                return True
            raise
        if result.get("success") is None:
            raise RAGContractError("delete kb response missing success")
        return True

    # ---------------------------------------------------------------- docs
    async def upload_text(self, kb_id: str, filename: str, text: str) -> str:
        result = await self._request(
            "POST",
            f"/doc/{kb_id}",
            files={
                "doc_files": (
                    filename,
                    text.encode("utf-8"),
                    "text/plain",
                )
            },
        )
        doc_ids = result.get("doc_ids")
        if not isinstance(doc_ids, list) or not doc_ids:
            raise RAGContractError("upload response missing doc_ids")
        return str(doc_ids[0])

    async def get_document(self, doc_id: str) -> dict[str, Any]:
        result = await self._request("GET", f"/doc/{doc_id}")
        document = result.get("document")
        if not isinstance(document, dict):
            raise RAGContractError("get document response missing document")
        return document

    async def parse_status(self, doc_id: str) -> str:
        document = await self.get_document(doc_id)
        status = document.get("parse_status")
        if not status:
            raise RAGContractError("document response missing parse_status")
        return str(status)

    async def delete_document(self, doc_id: str) -> bool:
        try:
            result = await self._request("DELETE", f"/doc/{doc_id}")
        except RAGContractError as exc:
            if exc.status_code == 404:
                return True
            # Every other contract error must be retried by the caller.
            raise
        success = result.get("success")
        if success is None:
            raise RAGContractError("delete response missing success")
        if success:
            return True
        # A false result is only a final answer when the document is really gone.
        try:
            document = await self.get_document(doc_id)
        except RAGContractError as exc:
            if exc.status_code == 404:
                return True
            raise
        status = str(document.get("status") or document.get("parse_status") or "")
        if status == "deleted":
            return True
        raise RAGContractError(
            f"delete reported success=false but document {doc_id} remains"
        )

    async def list_documents(
        self,
        kb_id: str,
        *,
        page_size: int = 100,
        page_num: int = 1,
        parse_status: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        body: dict[str, Any] = {"page_size": page_size, "page_num": page_num}
        if parse_status:
            body["parse_status"] = parse_status
        result = await self._request("POST", f"/doc/list/{kb_id}", json_body=body)
        documents = result.get("documents")
        if not isinstance(documents, list):
            raise RAGContractError("list documents response missing documents")
        return int(result.get("total") or len(documents)), documents

    # ---------------------------------------------------------------- search
    async def search_chunks(
        self,
        kb_id: str,
        query: str,
        top_k: int,
        *,
        is_rerank: bool = False,
        ratio: float = 0.5,
        is_related_surrounding: bool = False,
    ) -> list[dict[str, Any]]:
        result = await self._request(
            "POST",
            "/chunk/search",
            json_body={
                "need_trace": False,
                "search_chunk_configs": [
                    {
                        "kb_id": kb_id,
                        "query": query,
                        "top_k": top_k,
                        "is_rerank": is_rerank,
                        "ratio": ratio,
                        "is_related_surrounding": is_related_surrounding,
                        "is_classify_by_doc": False,
                        "is_compress": False,
                        "need_raw_data": False,
                    }
                ],
            },
        )
        chunks = result.get("chunks")
        if not isinstance(chunks, list):
            raise RAGContractError("search response missing chunks")
        return [chunk for chunk in chunks if isinstance(chunk, dict)]
