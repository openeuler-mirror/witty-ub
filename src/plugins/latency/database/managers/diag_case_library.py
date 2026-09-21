# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for diag_case_library and diag_case_library_signal.

Signal normalization deliberately reuses the module-level helpers from
``latency.database.managers.diagnosis_case`` so the whole repository keeps one
matching vocabulary (``strip().lower()`` + the same signal types/weights).

Pure ``@staticmethod`` helpers (no DB) carry the matching semantics so they can
be unit tested without PostgreSQL: ``_signals_for_case`` / ``_signals_for_search``
/ ``_build_search_text`` / ``_score`` / ``_matches_search_filters`` /
``_rank_search``.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Iterable

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert

from latency.ENUM.case_library import DiagCaseStatus
from latency.common.local_time import local_now
from latency.database.engine import PGManager
from latency.database.managers.diagnosis_case import (
    _iter_values,
    _normalize_signal_value,
)
from latency.database.models import DiagCaseLibrary, DiagCaseLibrarySignal
from latency.database.utils import format_timestamp
from latency.schemas.diag_case_library import (
    DiagCaseLibraryMatchModel,
    DiagCaseLibraryModel,
    DiagCaseLibrarySignalModel,
    SearchDiagCaseLibraryRequest,
)

CASE_NO_SEQUENCE = "diag_case_library_case_no_seq"


def _now() -> datetime:
    return local_now()


def _plain(value: Any) -> Any:
    """Unwrap ``StrEnum`` members so asyncpg receives plain strings."""
    return value.value if isinstance(value, Enum) else value


class DiagCaseLibraryPGManager:
    """PostgreSQL-backed supernode diagnosis case library manager."""

    # signal_type -> weight, mirroring §3.3 of the design document.
    OPERATION_SIGNAL = "operation"

    # §4.4 草稿可局部更新的列；case_no / status / revision / 留痕与命中计数等
    # 元信息不在其中，PATCH 无法触达。
    UPDATABLE_COLUMNS: tuple[str, ...] = (
        "source",
        "source_url",
        "title",
        "log_type",
        "kb_id",
        "kb_name",
        "cluster_name",
        "hosts",
        "pods",
        "src_ips",
        "dst_ips",
        "node_type",
        "version_json",
        "scope_limits",
        "operation",
        "fault_type",
        "status_codes",
        "failure_mode_ids",
        "latency_components",
        "log_keywords",
        "stage_features_json",
        "fault_shape",
        "time_window_json",
        "confidence",
        "symptom_summary",
        "evidence_json",
        "root_cause_summary",
        "root_cause_detail",
        "counter_evidence_json",
        "remediation_json",
        "verification_json",
        "relations_json",
        "source_log_ids",
    )

    @staticmethod
    def _format_case_no(seq_value: int) -> str:
        """Render the human readable case number from the sequence value."""
        return f"UB-CASE-{int(seq_value):06d}"

    @staticmethod
    def _signals_for_case(
        case: DiagCaseLibraryModel,
    ) -> list[DiagCaseLibrarySignalModel]:
        signals: dict[tuple[str, str], DiagCaseLibrarySignalModel] = {}

        def add(signal_type: str, value: Any, weight: float = 1.0) -> None:
            if value is None:
                # ``_normalize_signal_value`` stringifies None to "none"; a
                # missing optional field must not become a matchable signal.
                return
            signal_value = _normalize_signal_value(value)
            if not signal_value:
                return
            key = (signal_type, signal_value)
            existing = signals.get(key)
            if existing is None or existing.weight < weight:
                signals[key] = DiagCaseLibrarySignalModel(
                    case_id=case.id,
                    signal_type=signal_type,
                    signal_value=signal_value,
                    weight=weight,
                )

        for status_code in case.status_codes:
            add("status_code", status_code, 3.0)
        for failure_mode_id in case.failure_mode_ids:
            add("failure_mode_id", failure_mode_id, 3.0)
        for value in case.src_ips:
            add("src_ip", value, 1.5)
        for value in case.dst_ips:
            add("dst_ip", value, 1.5)
        for value in case.hosts:
            add("host", value, 1.5)
        for value in case.pods:
            add("pod", value, 1.5)
        add("cluster", case.cluster_name, 1.5)
        for value in case.latency_components:
            add("latency_component", value, 1.5)
        for value in case.log_keywords:
            add("log_keyword", value, 1.0)
        add(DiagCaseLibraryPGManager.OPERATION_SIGNAL, case.operation, 1.5)
        return list(signals.values())

    @staticmethod
    def _signals_for_search(
        req: SearchDiagCaseLibraryRequest,
    ) -> dict[tuple[str, str], float]:
        query_signals: dict[tuple[str, str], float] = {}

        def add(signal_type: str, values: Iterable[Any], weight: float) -> None:
            for value in values:
                signal_value = _normalize_signal_value(value)
                if signal_value:
                    query_signals[(signal_type, signal_value)] = weight

        add("status_code", req.status_codes, 3.0)
        add("failure_mode_id", req.failure_mode_ids, 3.0)
        add("src_ip", req.src_ips, 1.5)
        add("dst_ip", req.dst_ips, 1.5)
        add("host", req.hosts, 1.5)
        add("pod", req.pods, 1.5)
        add("cluster", req.clusters, 1.5)
        add("latency_component", req.latency_components, 1.5)
        add("log_keyword", req.log_keywords, 1.0)
        add(
            DiagCaseLibraryPGManager.OPERATION_SIGNAL,
            [req.operation] if req.operation else [],
            1.5,
        )
        return query_signals

    @staticmethod
    def _build_search_text(case: DiagCaseLibraryModel) -> str:
        """Build the embedding body per CASE_FEATURE_CONTRACT.md §五.

        Only正文 is included; IPs / hosts / clusters are pure identity noise and
        stay out so cross-cluster recall is not polluted.
        """
        parts: list[str] = []
        for value in (
            case.title,
            case.symptom_summary,
            case.root_cause_summary,
            case.root_cause_detail,
        ):
            if value and str(value).strip():
                parts.append(str(value).strip())
        if case.operation:
            parts.append(str(_plain(case.operation)))
        if case.fault_shape and case.fault_shape.strip():
            parts.append(case.fault_shape.strip())
        for component in _iter_values(case.latency_components):
            if str(component).strip():
                parts.append(str(component).strip())
        version_json = case.version_json
        if version_json is not None:
            for value in version_json.model_dump().values():
                if value and str(value).strip():
                    parts.append(str(value).strip())
        for keyword in _iter_values(case.log_keywords):
            if str(keyword).strip():
                parts.append(str(keyword).strip())
        return "\n".join(parts)

    @staticmethod
    def _score(
        case_signals: Iterable[DiagCaseLibrarySignalModel],
        query_signals: dict[tuple[str, str], float],
    ) -> tuple[float, float, list[DiagCaseLibrarySignalModel]]:
        """Score one case against the query signals.

        ``match_score`` = Σ min(案例权重, 查询权重)（未归一化）；
        ``score_norm`` = match_score / Σ 查询侧权重（0~1，跨查询可比）。
        """
        match_score = 0.0
        matched: list[DiagCaseLibrarySignalModel] = []
        for signal in case_signals:
            query_weight = query_signals.get((signal.signal_type, signal.signal_value))
            if query_weight is None:
                continue
            match_score += min(float(signal.weight), query_weight)
            matched.append(signal)
        total_query_weight = sum(query_signals.values())
        score_norm = match_score / total_query_weight if total_query_weight > 0 else 0.0
        return match_score, score_norm, matched

    @staticmethod
    def _matches_search_filters(
        case: DiagCaseLibraryModel,
        req: SearchDiagCaseLibraryRequest,
    ) -> bool:
        """Structured header filters; ``kb_id`` empty means "no source filter"."""
        if case.status not in req.include_status:
            return False
        if req.kb_id and case.kb_id not in (None, "", req.kb_id):
            return False
        if req.log_type and case.log_type != req.log_type:
            return False
        if req.fault_type and case.fault_type not in (req.fault_type, "mixed", "unknown"):
            return False
        if req.operation and case.operation != req.operation:
            return False
        if req.min_confidence is not None and float(case.confidence or 0.0) < (
            req.min_confidence
        ):
            return False
        return True

    @staticmethod
    def _rank_search(
        cases: list[DiagCaseLibraryModel],
        signals_by_case: dict[str, list[DiagCaseLibrarySignalModel]],
        req: SearchDiagCaseLibraryRequest,
    ) -> tuple[int, list[DiagCaseLibraryMatchModel]]:
        """Filter, score, sort and paginate an in-memory candidate set."""
        query_signals = DiagCaseLibraryPGManager._signals_for_search(req)
        matches: list[DiagCaseLibraryMatchModel] = []
        for case in cases:
            if not DiagCaseLibraryPGManager._matches_search_filters(case, req):
                continue
            if not query_signals:
                # 零信号查询：返回该状态下的全部案例，分数为 0。
                matches.append(
                    DiagCaseLibraryMatchModel(
                        case=case, match_score=0.0, score_norm=0.0, matched_signals=[]
                    )
                )
                continue
            match_score, score_norm, matched = DiagCaseLibraryPGManager._score(
                signals_by_case.get(case.id, []), query_signals
            )
            if not matched:
                continue
            matches.append(
                DiagCaseLibraryMatchModel(
                    case=case,
                    match_score=match_score,
                    score_norm=score_norm,
                    matched_signals=matched,
                )
            )

        matches.sort(
            key=lambda item: (
                item.score_norm,
                item.case.confidence,
                item.case.hit_count,
                item.case.updated_at,
            ),
            reverse=True,
        )
        total = len(matches)
        offset = (req.page_num - 1) * req.page_cnt
        return total, matches[offset : offset + req.page_cnt]

    # --------------------------------------------------------
    # DB 方法
    # --------------------------------------------------------
    @staticmethod
    def _orm_to_case(row: DiagCaseLibrary) -> DiagCaseLibraryModel:
        return DiagCaseLibraryModel(
            id=row.id,
            case_no=row.case_no,
            status=row.status or DiagCaseStatus.DRAFT,
            revision=row.revision or 0,
            created_by=row.created_by,
            confirmed_by=row.confirmed_by,
            archived_by=row.archived_by,
            confirmed_at=format_timestamp(row.confirmed_at),
            archived_at=format_timestamp(row.archived_at),
            archive_reason=row.archive_reason,
            source=row.source or "internal",
            source_url=row.source_url,
            title=row.title,
            log_type=row.log_type,
            kb_id=row.kb_id or None,
            kb_name=row.kb_name,
            cluster_name=row.cluster_name,
            hosts=row.hosts or [],
            pods=row.pods or [],
            src_ips=row.src_ips or [],
            dst_ips=row.dst_ips or [],
            node_type=row.node_type,
            version_json=row.version_json or None,
            scope_limits=row.scope_limits,
            operation=row.operation or None,
            fault_type=row.fault_type or "unknown",
            status_codes=row.status_codes or [],
            failure_mode_ids=row.failure_mode_ids or [],
            latency_components=row.latency_components or [],
            log_keywords=row.log_keywords or [],
            stage_features_json=row.stage_features_json or None,
            fault_shape=row.fault_shape,
            time_window_json=row.time_window_json or None,
            confidence=row.confidence or 0.0,
            symptom_summary=row.symptom_summary or "",
            evidence_json=row.evidence_json or [],
            root_cause_summary=row.root_cause_summary or "",
            root_cause_detail=row.root_cause_detail,
            counter_evidence_json=row.counter_evidence_json or [],
            remediation_json=row.remediation_json or [],
            verification_json=row.verification_json or None,
            relations_json=row.relations_json or [],
            search_text=row.search_text,
            embedding_model=row.embedding_model,
            embedded_at=format_timestamp(row.embedded_at),
            source_log_ids=row.source_log_ids or [],
            hit_count=row.hit_count or 0,
            existed_status=row.existed_status,
            created_at=format_timestamp(row.created_at) or "",
            updated_at=format_timestamp(row.updated_at) or "",
        )

    @staticmethod
    async def add_draft(case: DiagCaseLibraryModel) -> str:
        """Persist a draft, generating ``case_no`` from the sequence."""
        now = _now()
        data = case.model_dump(mode="json")
        data["search_text"] = DiagCaseLibraryPGManager._build_search_text(case)
        data["status"] = DiagCaseStatus.DRAFT.value
        data["revision"] = 0
        data["hit_count"] = 0
        data["existed_status"] = True
        data["created_at"] = now
        data["updated_at"] = now
        data["embedding_model"] = None
        data["embedded_at"] = None

        async with PGManager.session() as session:
            seq_value = await session.scalar(
                text(f"SELECT nextval('{CASE_NO_SEQUENCE}')")
            )
            case_no = DiagCaseLibraryPGManager._format_case_no(seq_value)
            data["case_no"] = case_no
            await session.execute(insert(DiagCaseLibrary).values(data))
            await DiagCaseLibraryPGManager._replace_signals(session, case.id, case)
        case.case_no = case_no
        case.search_text = data["search_text"]
        return case.id

    @staticmethod
    async def get_case(case_id: str) -> DiagCaseLibraryModel | None:
        async with PGManager.session() as session:
            row = await session.get(DiagCaseLibrary, case_id)
        if row is None or not row.existed_status:
            return None
        return DiagCaseLibraryPGManager._orm_to_case(row)

    @staticmethod
    async def _replace_signals(
        session: Any, case_id: str, case: DiagCaseLibraryModel
    ) -> None:
        """Rebuild ``diag_case_library_signal`` rows for one case.

        信号列必须与主表特征同步，否则检索口径与内容物不一致。
        """
        await session.execute(
            delete(DiagCaseLibrarySignal).where(
                DiagCaseLibrarySignal.case_id == case_id
            )
        )
        signals = DiagCaseLibraryPGManager._signals_for_case(case)
        if not signals:
            return
        await session.execute(
            insert(DiagCaseLibrarySignal).values(
                [
                    {
                        "case_id": signal.case_id,
                        "signal_type": signal.signal_type,
                        "signal_value": signal.signal_value,
                        "weight": signal.weight,
                    }
                    for signal in signals
                ]
            )
        )

    @staticmethod
    async def update_draft(case_id: str, case: DiagCaseLibraryModel) -> bool:
        """§4.4 落库局部更新结果：重算 search_text 与信号行，``revision + 1``。

        只在 ``status = draft`` 时生效（并发下确认后的案例不会被改写）。
        """
        data = case.model_dump(mode="json")
        values = {
            column: data.get(column)
            for column in DiagCaseLibraryPGManager.UPDATABLE_COLUMNS
        }
        values["search_text"] = DiagCaseLibraryPGManager._build_search_text(case)
        values["updated_at"] = _now()

        async with PGManager.session() as session:
            result = await session.execute(
                update(DiagCaseLibrary)
                .where(
                    DiagCaseLibrary.id == case_id,
                    DiagCaseLibrary.existed_status.is_(True),
                    DiagCaseLibrary.status == DiagCaseStatus.DRAFT.value,
                )
                .values(revision=DiagCaseLibrary.revision + 1, **values)
            )
            if not (result.rowcount or 0):
                return False
            await DiagCaseLibraryPGManager._replace_signals(session, case_id, case)
        return True

    @staticmethod
    async def confirm_case(
        case_id: str,
        confirmed_by: str,
        confidence: float | None = None,
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                text(
                    "UPDATE diag_case_library SET status = :status, "
                    "confirmed_by = :confirmed_by, confirmed_at = :now, "
                    "revision = revision + 1, updated_at = :now, "
                    "confidence = COALESCE(:confidence, confidence) "
                    "WHERE id = :case_id AND existed_status = TRUE"
                ),
                {
                    "status": DiagCaseStatus.CONFIRMED.value,
                    "confirmed_by": confirmed_by,
                    "confidence": confidence,
                    "now": now,
                    "case_id": case_id,
                },
            )
        return (result.rowcount or 0) > 0

    @staticmethod
    async def archive_case(
        case_id: str,
        archived_by: str | None = None,
        archive_reason: str | None = None,
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                text(
                    "UPDATE diag_case_library SET status = :status, "
                    "archived_by = :archived_by, archived_at = :now, "
                    "archive_reason = :archive_reason, updated_at = :now "
                    "WHERE id = :case_id AND existed_status = TRUE"
                ),
                {
                    "status": DiagCaseStatus.ARCHIVED.value,
                    "archived_by": archived_by,
                    "archive_reason": archive_reason,
                    "now": now,
                    "case_id": case_id,
                },
            )
        return (result.rowcount or 0) > 0

    @staticmethod
    async def mark_hit(case_id: str) -> bool:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                text(
                    "UPDATE diag_case_library SET hit_count = hit_count + 1, "
                    "updated_at = :now WHERE id = :case_id AND existed_status = TRUE"
                ),
                {"case_id": case_id, "now": now},
            )
        return (result.rowcount or 0) > 0

    @staticmethod
    async def search_cases(
        req: SearchDiagCaseLibraryRequest,
    ) -> tuple[int, list[DiagCaseLibraryMatchModel]]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(DiagCaseLibrary).where(DiagCaseLibrary.existed_status.is_(True))
            )
            rows = result.scalars().all()

        cases = [DiagCaseLibraryPGManager._orm_to_case(row) for row in rows]
        if not cases:
            return 0, []

        signals_by_case: dict[str, list[DiagCaseLibrarySignalModel]] = {}
        async with PGManager.session() as session:
            signal_result = await session.execute(
                select(DiagCaseLibrarySignal).where(
                    DiagCaseLibrarySignal.case_id.in_([case.id for case in cases])
                )
            )
            for row in signal_result.scalars().all():
                signals_by_case.setdefault(row.case_id, []).append(
                    DiagCaseLibrarySignalModel(
                        case_id=row.case_id,
                        signal_type=row.signal_type,
                        signal_value=row.signal_value,
                        weight=row.weight,
                    )
                )

        return DiagCaseLibraryPGManager._rank_search(cases, signals_by_case, req)