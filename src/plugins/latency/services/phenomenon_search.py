# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Phenomenon search: RAG recall, local mapping and detail pointers."""
from __future__ import annotations

import asyncio
import math
import time
from collections import deque

from latency.config import phenomenon as settings
from latency.database.engine import PGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager as Mgr
from latency.database.models import DiagCaseLibrary, PhenomenonIndex
from latency.database.utils import format_timestamp
from latency.ENUM.phenomenon import (
    BindingStatus,
    PhenomenonKind,
    VerificationLevel,
)
from latency.exceptions import (
    DependencyUnavailableBizException,
    FeatureDisabledBizException,
    NotFoundBizException,
    UpstreamContractBizException,
)
from latency.schemas.phenomenon import (
    GetPhenomenonMsg,
    PhenomenonMatchModel,
    SearchPhenomenaMsg,
    SearchPhenomenonRequest,
)
from latency.services.rag_client import (
    RAGClient,
    RAGContractError,
    RAGUnavailableError,
)
from sqlalchemy import select

SYMPTOM_MAX = 600
MAX_CANDIDATE_LIMIT = 200
# Absolute budget for one search, including every widening round and local
# mapping.  Read-interval timeouts cannot bound a slow-drip upstream, and the
# caller must get an explicit error before the 5-second deadline.
SEARCH_BUDGET_SECONDS = 4.5

# 运维快照只看最近 5 分钟；进程重启后自动清零。
RETRIEVAL_WINDOW_SECONDS = 300
_RETRIEVAL_EVENTS: deque[tuple[float, float, bool]] = deque(maxlen=5000)


def record_retrieval(
    duration_seconds: float, ok: bool, at: float | None = None
) -> None:
    """Record one completed search attempt for the ops snapshot."""
    _RETRIEVAL_EVENTS.append(
        (time.monotonic() if at is None else at, max(0.0, duration_seconds), ok)
    )


def retrieval_snapshot(now: float | None = None) -> dict[str, float | int | None]:
    """Return request count, error rate and p95 over the rolling window."""
    global _RETRIEVAL_EVENTS
    current = time.monotonic() if now is None else now
    cutoff = current - RETRIEVAL_WINDOW_SECONDS
    _RETRIEVAL_EVENTS = deque(
        (event for event in _RETRIEVAL_EVENTS if event[0] >= cutoff),
        maxlen=_RETRIEVAL_EVENTS.maxlen,
    )
    durations = [duration for _, duration, _ in _RETRIEVAL_EVENTS]
    requests = len(durations)
    errors = sum(1 for _, _, ok in _RETRIEVAL_EVENTS if not ok)
    p95_ms: float | None = None
    if durations:
        ordered = sorted(durations)
        index = max(0, math.ceil(len(ordered) * 0.95) - 1)
        p95_ms = round(ordered[index] * 1000, 1)
    return {
        "window_seconds": RETRIEVAL_WINDOW_SECONDS,
        "requests": requests,
        "errors": errors,
        "error_rate": round(errors / requests, 4) if requests else 0.0,
        "p95_ms": p95_ms,
    }


def _fingerprints_equal(left: str | None, right: str | None) -> bool:
    return left == right


def _case_closed_loop(case: DiagCaseLibrary) -> bool:
    verification = case.verification_json or {}
    if isinstance(verification, dict):
        return bool(verification.get("closed_loop"))
    return bool(getattr(verification, "closed_loop", False))


class _CardState:
    """Resolved pointers / trust label for one card at query time."""

    def __init__(
        self,
        card: PhenomenonIndex,
        *,
        case: DiagCaseLibrary | None,
        report_available: bool,
    ):
        self.card = card
        self.case = case
        self.report_available = report_available
        self.case_active = bool(case and case.status == "confirmed" and _case_closed_loop(case))
        self.report_pointer = bool(
            card.report_id
            and card.binding_status != BindingStatus.STALE.value
            and report_available
        )
        if self.case_active:
            self.verification = (
                VerificationLevel.VERIFIED.value
                if _case_closed_loop(case)
                else VerificationLevel.CONFIRMED_UNVERIFIED.value
            )
        elif card.kind == PhenomenonKind.LEGACY_CASE.value:
            self.verification = (
                VerificationLevel.TASK_OBSERVED.value
                if card.verification == VerificationLevel.TASK_OBSERVED.value
                else VerificationLevel.LEGACY_UNVERIFIED.value
            )
        elif card.kind == PhenomenonKind.CASE.value:
            self.verification = card.verification
        else:
            self.verification = (
                VerificationLevel.SUSPECTED.value
                if card.verification == VerificationLevel.SUSPECTED.value
                else VerificationLevel.REPORT_ONLY.value
            )

    @property
    def usable(self) -> bool:
        if not self.card.enabled or not self.card.searchable:
            return False
        if self.card.published_text is None:
            return False
        if self.card.kind == PhenomenonKind.CASE.value and not self.case_active:
            return False
        return True

    @property
    def get_case(self) -> str | None:
        if self.case_active and self.case is not None:
            return f"/diag_case_library/{self.case.id}"
        return None

    @property
    def get_fault(self) -> str | None:
        if (
            self.report_pointer
            and self.card.source_fault_id
            and not self.card.source_fault_id.startswith("auto:")
        ):
            return (
                f"/diagnostic_report/{self.card.report_id}/faults/"
                f"{self.card.source_fault_id}"
            )
        return None

    def match(
        self, score: float, score_raw: float, operation_scope: str | None
    ) -> PhenomenonMatchModel:
        card = self.card
        return PhenomenonMatchModel(
            doc_id=card.doc_id,
            score=score,
            score_raw=score_raw,
            kind=card.kind,
            title=card.published_title or card.title,
            symptom=(card.published_symptom or card.symptom or "")[:SYMPTOM_MAX],
            report_id=card.report_id if self.report_pointer else None,
            source_fault_id=card.source_fault_id if self.report_pointer else None,
            case_id=self.case.id if self.case_active and self.case else None,
            case_no=self.case.case_no if self.case_active and self.case else None,
            legacy_case_id=card.legacy_case_id,
            verification=self.verification,
            binding_status=card.binding_status,
            operation_scope=operation_scope,
            report_available=self.report_available,
            get_report=(
                f"/diagnostic_report/{card.report_id}" if self.report_pointer else None
            ),
            get_report_html=(
                f"/diagnostic_report/{card.report_id}/html"
                if self.report_pointer
                else None
            ),
            get_fault=self.get_fault,
            get_case=self.get_case,
            get_legacy_case=(
                f"/case_library/{card.legacy_case_id}"
                if card.legacy_case_id
                else None
            ),
        )


class PhenomenonSearchService:
    """Read-only search over published cards."""

    @staticmethod
    async def search(req: SearchPhenomenonRequest) -> SearchPhenomenaMsg:
        if not settings.search_enabled():
            raise FeatureDisabledBizException(
                message="现象检索未启用",
                detail="PHENOMENON_SEARCH_ENABLED=false",
            )
        try:
            client, kb_id = _rag_targets()
        except RAGUnavailableError as exc:
            raise DependencyUnavailableBizException(
                message="现象检索依赖不可用", detail=str(exc)
            ) from exc

        started = time.monotonic()
        ok = False
        try:
            result = await asyncio.wait_for(
                PhenomenonSearchService._search(req, client, kb_id),
                SEARCH_BUDGET_SECONDS,
            )
            ok = True
            return result
        except asyncio.TimeoutError as exc:  # noqa: UP041 - a separate class on Python 3.10
            raise DependencyUnavailableBizException(
                message="现象检索超时",
                detail=f"search budget {SEARCH_BUDGET_SECONDS}s exceeded",
            ) from exc
        finally:
            record_retrieval(time.monotonic() - started, ok)

    @staticmethod
    async def _search(
        req: SearchPhenomenonRequest, client: RAGClient, kb_id: str
    ) -> SearchPhenomenaMsg:
        top_k = int(req.top_k)
        first_window = min(MAX_CANDIDATE_LIMIT, max(top_k * 5, top_k))
        matches, truncated = await PhenomenonSearchService._collect(
            req, client, kb_id, first_window
        )
        if len(matches) < top_k and first_window < MAX_CANDIDATE_LIMIT:
            matches, truncated = await PhenomenonSearchService._collect(
                req, client, kb_id, MAX_CANDIDATE_LIMIT
            )
        matches.sort(key=lambda item: item.score, reverse=True)
        final = matches[:top_k]
        return SearchPhenomenaMsg(
            matches=final,
            returned_count=len(final),
            truncated=truncated,
        )

    @staticmethod
    async def _collect(
        req: SearchPhenomenonRequest,
        client: RAGClient,
        kb_id: str,
        window: int,
    ) -> tuple[list[PhenomenonMatchModel], bool]:
        try:
            chunks = await client.search_chunks(
                kb_id,
                req.query,
                window,
                is_rerank=settings.rag_is_rerank(),
                ratio=settings.rag_ratio(),
            )
        except RAGUnavailableError as exc:
            raise DependencyUnavailableBizException(
                message="现象检索依赖不可用", detail=str(exc)
            ) from exc
        except RAGContractError as exc:
            raise UpstreamContractBizException(
                message="现象检索上游契约错误", detail=str(exc)
            ) from exc

        truncated = len(chunks) >= MAX_CANDIDATE_LIMIT
        scale = settings.rag_score_scale()
        if scale <= 0:
            raise UpstreamContractBizException(
                message="现象检索分数配置非法", detail="RAG_SCORE_SCALE<=0"
            )
        min_score = (
            settings.rag_min_score()
            if req.min_score is None
            else float(req.min_score)
        )

        scored: dict[str, tuple[float, float]] = {}
        for chunk in chunks:
            raw = chunk.get("score")
            rag_doc_id = chunk.get("doc_id")
            if (
                isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(float(raw))
                or float(raw) < 0
                or float(raw) > scale
            ):
                raise UpstreamContractBizException(
                    message="现象检索分数越界",
                    detail=f"score={raw!r}, scale={scale}",
                )
            if not rag_doc_id:
                raise UpstreamContractBizException(
                    message="现象检索响应缺少 doc_id"
                )
            normalized = float(raw) / scale
            if normalized < min_score:
                continue
            doc_key = str(rag_doc_id)
            previous = scored.get(doc_key)
            if previous is None or normalized > previous[0]:
                scored[doc_key] = (normalized, float(raw))

        cards = await Mgr.get_cards_by_rag_docs(
            (kb_id, doc_id) for doc_id in scored
        )
        if not cards:
            return [], truncated
        states = await PhenomenonSearchService._resolve_states(cards)

        results: dict[str, PhenomenonMatchModel] = {}
        for card in cards:
            state = states.get(card.doc_id)
            if state is None or not state.usable:
                continue
            if not _fingerprints_equal(
                card.published_source_fault_hash, card.source_fault_hash
            ):
                continue
            if card.rag_doc_id not in scored:
                continue
            score, score_raw = scored[card.rag_doc_id]
            operation_scope = None
            if req.log_type and card.log_type != req.log_type:
                continue
            if req.fault_type and card.fault_type != req.fault_type:
                continue
            if req.operation:
                if card.operation == req.operation:
                    pass
                elif card.operation == "MIXED":
                    operation_scope = "report"
                else:
                    continue
            if (
                not req.include_unverified
                and state.verification not in {
                    VerificationLevel.VERIFIED.value, VerificationLevel.TASK_OBSERVED.value,
                }
            ):
                continue
            match = state.match(score, score_raw, operation_scope)
            existing = results.get(card.doc_id)
            if existing is None or match.score > existing.score:
                results[card.doc_id] = match
        return list(results.values()), truncated

    @staticmethod
    async def _resolve_states(
        cards: list[PhenomenonIndex],
    ) -> dict[str, _CardState]:
        case_ids = {card.case_id for card in cards if card.case_id}
        report_ids = {card.report_id for card in cards if card.report_id}
        cases: dict[str, DiagCaseLibrary] = {}
        if case_ids:
            async with PGManager.session() as session:
                rows = await session.execute(
                    select(DiagCaseLibrary).where(DiagCaseLibrary.id.in_(case_ids))
                )
                cases = {row.id: row for row in rows.scalars().all()}
        reports = await Mgr.get_report_indexes(report_ids)
        states: dict[str, _CardState] = {}
        for card in cards:
            report = reports.get(card.report_id) if card.report_id else None
            available = bool(report and report.report_available)
            states[card.doc_id] = _CardState(
                card,
                case=cases.get(card.case_id) if card.case_id else None,
                report_available=available,
            )
        return states

    @staticmethod
    async def get_card(doc_id: str) -> GetPhenomenonMsg:
        card = await Mgr.get_card(doc_id)
        if card is None:
            raise NotFoundBizException(resource=f"现象卡片 {doc_id}")
        states = await PhenomenonSearchService._resolve_states([card])
        state = states[card.doc_id]
        return GetPhenomenonMsg(
            doc_id=card.doc_id,
            kind=card.kind,
            content_source=card.content_source,
            report_id=card.report_id if state.report_pointer else None,
            source_fault_id=card.source_fault_id if state.report_pointer else None,
            case_id=state.case.id if state.case_active and state.case else None,
            case_no=state.case.case_no if state.case_active and state.case else None,
            legacy_case_id=card.legacy_case_id,
            title=card.published_title or card.title,
            symptom=(card.published_symptom or card.symptom or "")[:SYMPTOM_MAX],
            verification=state.verification,
            binding_status=card.binding_status,
            operation_scope=None,
            report_available=state.report_available,
            get_report=(
                f"/diagnostic_report/{card.report_id}" if state.report_pointer else None
            ),
            get_report_html=(
                f"/diagnostic_report/{card.report_id}/html"
                if state.report_pointer
                else None
            ),
            get_fault=state.get_fault,
            get_case=state.get_case,
            get_legacy_case=(
                f"/case_library/{card.legacy_case_id}"
                if card.legacy_case_id
                else None
            ),
            index_status=card.index_status,
            index_error=card.index_error,
            retry_count=int(card.retry_count or 0),
            indexed_at=format_timestamp(card.indexed_at),
            content_hash=card.content_hash or "",
            indexed_content_hash=card.indexed_content_hash,
        )


def _rag_targets() -> tuple[RAGClient, str]:
    client = RAGClient.from_env()
    kb_id = settings.rag_kb_id()
    if not kb_id:
        raise RAGUnavailableError("RAG_PHENOMENON_KB_ID is not configured")
    return client, kb_id
