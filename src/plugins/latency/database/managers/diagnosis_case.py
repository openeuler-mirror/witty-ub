# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for diagnosis_case and diagnosis_case_signal."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from latency.database.engine import PGManager
from latency.database.models import DiagnosisCase, DiagnosisCaseSignal
from latency.database.utils import format_timestamp, parse_timestamp
from latency.schemas.diagnosis_case import (
    DiagnosisCaseMatchModel,
    DiagnosisCaseModel,
    DiagnosisCaseSignalModel,
)
from latency.schemas.request import SearchDiagnosisCasesRequest


def _now() -> datetime:
    return datetime.now()


def _normalize_signal_value(value: Any) -> str:
    return str(value).strip().lower()


def _iter_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


class DiagnosisCasePGManager:
    """PostgreSQL-backed diagnosis case manager."""

    SIGNAL_FIELD_MAP = {
        "src_ips": "src_ip",
        "dst_ips": "dst_ip",
        "hosts": "host",
        "pods": "pod",
        "pod_names": "pod",
        "clusters": "cluster",
        "cluster_names": "cluster",
        "latency_components": "latency_component",
        "log_keywords": "log_keyword",
    }

    @staticmethod
    def _case_to_orm(case: DiagnosisCaseModel) -> DiagnosisCase:
        data = case.model_dump()
        now = _now()
        first_seen = parse_timestamp(data.get("first_seen_at")) or now
        last_seen = parse_timestamp(data.get("last_seen_at")) or now
        created = parse_timestamp(data.get("created_at")) or now
        updated = parse_timestamp(data.get("updated_at")) or now
        return DiagnosisCase(
            id=data["id"],
            kb_id=data.get("kb_id") or "",
            fault_type=data.get("fault_type") or "unknown",
            title=data.get("title"),
            symptom_summary=data.get("symptom_summary") or "",
            root_cause=data.get("root_cause") or "",
            recommendation=data.get("recommendation") or "",
            confidence=float(data.get("confidence") or 0.0),
            failure_mode_ids=data.get("failure_mode_ids") or [],
            status_codes=data.get("status_codes") or [],
            fingerprint_json=data.get("fingerprint_json") or {},
            evidence_refs_json=data.get("evidence_refs_json") or [],
            counter_evidence_json=data.get("counter_evidence_json") or [],
            source_log_ids=data.get("source_log_ids") or [],
            hit_count=int(data.get("hit_count") or 0),
            existed_status=bool(data.get("existed_status", True)),
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            created_at=created,
            updated_at=updated,
        )

    @staticmethod
    def _orm_to_case(row: DiagnosisCase) -> DiagnosisCaseModel:
        return DiagnosisCaseModel(
            id=row.id,
            kb_id=row.kb_id or None,
            fault_type=row.fault_type or "unknown",
            title=row.title,
            symptom_summary=row.symptom_summary or "",
            root_cause=row.root_cause or "",
            recommendation=row.recommendation or "",
            confidence=row.confidence or 0.0,
            failure_mode_ids=row.failure_mode_ids or [],
            status_codes=row.status_codes or [],
            fingerprint_json=row.fingerprint_json or {},
            evidence_refs_json=row.evidence_refs_json or [],
            counter_evidence_json=row.counter_evidence_json or [],
            source_log_ids=row.source_log_ids or [],
            hit_count=row.hit_count or 0,
            existed_status=row.existed_status,
            first_seen_at=format_timestamp(row.first_seen_at) or "",
            last_seen_at=format_timestamp(row.last_seen_at) or "",
            created_at=format_timestamp(row.created_at) or "",
            updated_at=format_timestamp(row.updated_at) or "",
        )

    @staticmethod
    def _signals_for_case(case: DiagnosisCaseModel) -> list[DiagnosisCaseSignalModel]:
        signals: dict[tuple[str, str], DiagnosisCaseSignalModel] = {}

        def add(signal_type: str, value: Any, weight: float = 1.0) -> None:
            signal_value = _normalize_signal_value(value)
            if not signal_value:
                return
            key = (signal_type, signal_value)
            existing = signals.get(key)
            if existing is None or existing.weight < weight:
                signals[key] = DiagnosisCaseSignalModel(
                    case_id=case.id,
                    signal_type=signal_type,
                    signal_value=signal_value,
                    weight=weight,
                )

        for status_code in case.status_codes:
            add("status_code", status_code, 3.0)
        for failure_mode_id in case.failure_mode_ids:
            add("failure_mode_id", failure_mode_id, 3.0)
        for log_id in case.source_log_ids:
            add("source_log_id", log_id, 0.5)

        fingerprint = case.fingerprint_json or {}
        for field, signal_type in DiagnosisCasePGManager.SIGNAL_FIELD_MAP.items():
            for value in _iter_values(fingerprint.get(field)):
                add(signal_type, value, 1.5 if signal_type != "log_keyword" else 1.0)

        for signal in _iter_values(fingerprint.get("signals")):
            if not isinstance(signal, dict):
                continue
            signal_type = signal.get("type")
            signal_value = signal.get("value")
            weight = float(signal.get("weight", 1.0))
            if signal_type:
                add(str(signal_type), signal_value, weight)

        return list(signals.values())

    @staticmethod
    def _signals_for_search(req: SearchDiagnosisCasesRequest) -> dict[tuple[str, str], float]:
        query_signals: dict[tuple[str, str], float] = {}

        def add(signal_type: str, values: list[str], weight: float) -> None:
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
        return query_signals

    @staticmethod
    async def add_case(case: DiagnosisCaseModel) -> str:
        orm = DiagnosisCasePGManager._case_to_orm(case)
        values = {
            "id": orm.id,
            "kb_id": orm.kb_id,
            "fault_type": orm.fault_type,
            "title": orm.title,
            "symptom_summary": orm.symptom_summary,
            "root_cause": orm.root_cause,
            "recommendation": orm.recommendation,
            "confidence": orm.confidence,
            "failure_mode_ids": orm.failure_mode_ids,
            "status_codes": orm.status_codes,
            "fingerprint_json": orm.fingerprint_json,
            "evidence_refs_json": orm.evidence_refs_json,
            "counter_evidence_json": orm.counter_evidence_json,
            "source_log_ids": orm.source_log_ids,
            "hit_count": orm.hit_count,
            "existed_status": orm.existed_status,
            "first_seen_at": orm.first_seen_at,
            "last_seen_at": orm.last_seen_at,
            "created_at": orm.created_at,
            "updated_at": orm.updated_at,
        }
        async with PGManager.session() as session:
            stmt = (
                insert(DiagnosisCase)
                .values(values)
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "kb_id": values["kb_id"],
                        "fault_type": values["fault_type"],
                        "title": values["title"],
                        "symptom_summary": values["symptom_summary"],
                        "root_cause": values["root_cause"],
                        "recommendation": values["recommendation"],
                        "confidence": values["confidence"],
                        "failure_mode_ids": values["failure_mode_ids"],
                        "status_codes": values["status_codes"],
                        "fingerprint_json": values["fingerprint_json"],
                        "evidence_refs_json": values["evidence_refs_json"],
                        "counter_evidence_json": values["counter_evidence_json"],
                        "source_log_ids": values["source_log_ids"],
                        "hit_count": values["hit_count"],
                        "existed_status": values["existed_status"],
                        "first_seen_at": values["first_seen_at"],
                        "last_seen_at": values["last_seen_at"],
                        "updated_at": values["updated_at"],
                    },
                )
            )
            await session.execute(stmt)

            await session.execute(
                text(
                    "DELETE FROM diagnosis_case_signal WHERE case_id = :case_id"
                ),
                {"case_id": case.id},
            )
            signals = DiagnosisCasePGManager._signals_for_case(case)
            if signals:
                signal_values = [
                    {
                        "case_id": s.case_id,
                        "signal_type": s.signal_type,
                        "signal_value": s.signal_value,
                        "weight": s.weight,
                    }
                    for s in signals
                ]
                await session.execute(
                    insert(DiagnosisCaseSignal).values(signal_values)
                )
        return case.id

    @staticmethod
    async def get_case(case_id: str) -> DiagnosisCaseModel | None:
        async with PGManager.session() as session:
            row = await session.get(DiagnosisCase, case_id)
        if row is None or not row.existed_status:
            return None
        return DiagnosisCasePGManager._orm_to_case(row)

    @staticmethod
    async def mark_case_hit(case_id: str) -> bool:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                text(
                    "UPDATE diagnosis_case SET hit_count = hit_count + 1, "
                    "last_seen_at = :now, updated_at = :now "
                    "WHERE id = :case_id AND existed_status = TRUE"
                ),
                {"case_id": case_id, "now": now},
            )
        return (result.rowcount or 0) > 0

    @staticmethod
    async def search_cases(
        req: SearchDiagnosisCasesRequest,
    ) -> tuple[int, list[DiagnosisCaseMatchModel]]:
        stmt = select(DiagnosisCase).where(DiagnosisCase.existed_status.is_(True))
        if req.kb_id:
            stmt = stmt.where(
                (DiagnosisCase.kb_id == req.kb_id)
                | (DiagnosisCase.kb_id.is_(None))
                | (DiagnosisCase.kb_id == "")
            )
        if req.fault_type:
            stmt = stmt.where(
                DiagnosisCase.fault_type.in_([req.fault_type, "mixed", "unknown"])
            )
        if req.min_confidence is not None:
            stmt = stmt.where(DiagnosisCase.confidence >= req.min_confidence)
        stmt = stmt.order_by(DiagnosisCase.updated_at.desc())

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        cases = [DiagnosisCasePGManager._orm_to_case(row) for row in rows]
        case_by_id = {case.id: case for case in cases}
        if not case_by_id:
            return 0, []

        query_signals = DiagnosisCasePGManager._signals_for_search(req)
        if not query_signals:
            total = len(cases)
            offset = (req.page_num - 1) * req.page_cnt
            page = cases[offset : offset + req.page_cnt]
            return total, [
                DiagnosisCaseMatchModel(case=case, match_score=0.0, matched_signals=[])
                for case in page
            ]

        async with PGManager.session() as session:
            signal_stmt = select(DiagnosisCaseSignal).where(
                DiagnosisCaseSignal.case_id.in_(list(case_by_id.keys()))
            )
            signal_result = await session.execute(signal_stmt)
            signal_rows = signal_result.scalars().all()

        scores: dict[str, float] = {}
        matched: dict[str, list[DiagnosisCaseSignalModel]] = {}
        for row in signal_rows:
            key = (row.signal_type, row.signal_value)
            query_weight = query_signals.get(key)
            if query_weight is None:
                continue
            signal = DiagnosisCaseSignalModel(
                case_id=row.case_id,
                signal_type=row.signal_type,
                signal_value=row.signal_value,
                weight=row.weight,
            )
            scores[row.case_id] = scores.get(row.case_id, 0.0) + min(
                float(row.weight), query_weight
            )
            matched.setdefault(row.case_id, []).append(signal)

        matches = [
            DiagnosisCaseMatchModel(
                case=case_by_id[case_id],
                match_score=score,
                matched_signals=matched.get(case_id, []),
            )
            for case_id, score in scores.items()
        ]
        matches.sort(
            key=lambda item: (
                item.match_score,
                item.case.confidence,
                item.case.hit_count,
                item.case.updated_at,
            ),
            reverse=True,
        )

        total = len(matches)
        offset = (req.page_num - 1) * req.page_cnt
        return total, matches[offset : offset + req.page_cnt]
