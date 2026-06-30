import json
from datetime import datetime
from typing import Any

from latency.database.engine import AsyncSQLiteSingleton
from latency.schemas.diagnosis_case import (
    DiagnosisCaseMatchModel,
    DiagnosisCaseModel,
    DiagnosisCaseSignalModel,
)
from latency.schemas.request import SearchDiagnosisCasesRequest


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


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


class DiagnosisCaseManager:
    """历史诊断案例管理器。"""

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
    def _case_to_row(case: DiagnosisCaseModel) -> dict[str, Any]:
        row = case.model_dump()
        for key in (
            "failure_mode_ids",
            "status_codes",
            "fingerprint_json",
            "evidence_refs_json",
            "counter_evidence_json",
            "source_log_ids",
        ):
            row[key] = _json_dumps(row[key])
        return row

    @staticmethod
    def _row_to_case(row: dict[str, Any]) -> DiagnosisCaseModel:
        payload = dict(row)
        payload["failure_mode_ids"] = _json_loads(row.get("failure_mode_ids"), [])
        payload["status_codes"] = _json_loads(row.get("status_codes"), [])
        payload["fingerprint_json"] = _json_loads(row.get("fingerprint_json"), {})
        payload["evidence_refs_json"] = _json_loads(row.get("evidence_refs_json"), [])
        payload["counter_evidence_json"] = _json_loads(row.get("counter_evidence_json"), [])
        payload["source_log_ids"] = _json_loads(row.get("source_log_ids"), [])
        return DiagnosisCaseModel.model_validate(payload)

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
        for field, signal_type in DiagnosisCaseManager.SIGNAL_FIELD_MAP.items():
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
        sql_str = """
            INSERT OR REPLACE INTO diagnosis_case_table (
                id, kb_id, fault_type, title, symptom_summary, root_cause,
                recommendation, confidence, failure_mode_ids, status_codes,
                fingerprint_json, evidence_refs_json, counter_evidence_json,
                source_log_ids, hit_count, existed_status, first_seen_at,
                last_seen_at, created_at, updated_at
            ) VALUES (
                :id, :kb_id, :fault_type, :title, :symptom_summary, :root_cause,
                :recommendation, :confidence, :failure_mode_ids, :status_codes,
                :fingerprint_json, :evidence_refs_json, :counter_evidence_json,
                :source_log_ids, :hit_count, :existed_status, :first_seen_at,
                :last_seen_at, :created_at, :updated_at
            )
        """
        saved = await AsyncSQLiteSingleton().execute_modify(
            sql_str, DiagnosisCaseManager._case_to_row(case)
        )
        if not saved:
            return ""

        await AsyncSQLiteSingleton().execute_modify(
            "DELETE FROM diagnosis_case_signal_table WHERE case_id = :case_id",
            {"case_id": case.id},
        )
        signals = DiagnosisCaseManager._signals_for_case(case)
        if signals:
            await AsyncSQLiteSingleton().execute_modify(
                """
                INSERT OR REPLACE INTO diagnosis_case_signal_table
                (case_id, signal_type, signal_value, weight)
                VALUES (:case_id, :signal_type, :signal_value, :weight)
                """,
                [signal.model_dump() for signal in signals],
            )
        return case.id

    @staticmethod
    async def get_case(case_id: str) -> DiagnosisCaseModel | None:
        rows = await AsyncSQLiteSingleton().execute_query(
            """
            SELECT *
            FROM diagnosis_case_table
            WHERE id = :case_id AND existed_status = 1
            """,
            {"case_id": case_id},
        )
        if not rows:
            return None
        return DiagnosisCaseManager._row_to_case(rows[0])

    @staticmethod
    async def mark_case_hit(case_id: str) -> bool:
        now = _now()
        return await AsyncSQLiteSingleton().execute_modify(
            """
            UPDATE diagnosis_case_table
            SET hit_count = hit_count + 1, last_seen_at = :now, updated_at = :now
            WHERE id = :case_id AND existed_status = 1
            """,
            {"case_id": case_id, "now": now},
        )

    @staticmethod
    async def search_cases(req: SearchDiagnosisCasesRequest) -> tuple[int, list[DiagnosisCaseMatchModel]]:
        sql_str = """
            SELECT *
            FROM diagnosis_case_table
            WHERE existed_status = 1
        """
        params: dict[str, Any] = {}
        if req.kb_id:
            sql_str += " AND (kb_id = :kb_id OR kb_id IS NULL OR kb_id = '')"
            params["kb_id"] = req.kb_id
        if req.fault_type:
            sql_str += " AND fault_type IN (:fault_type, 'mixed', 'unknown')"
            params["fault_type"] = req.fault_type
        if req.min_confidence is not None:
            sql_str += " AND confidence >= :min_confidence"
            params["min_confidence"] = req.min_confidence
        sql_str += " ORDER BY updated_at DESC"

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        cases = [DiagnosisCaseManager._row_to_case(row) for row in rows]
        case_by_id = {case.id: case for case in cases}
        if not case_by_id:
            return 0, []

        query_signals = DiagnosisCaseManager._signals_for_search(req)
        if not query_signals:
            total = len(cases)
            offset = (req.page_num - 1) * req.page_cnt
            page = cases[offset : offset + req.page_cnt]
            return total, [
                DiagnosisCaseMatchModel(case=case, match_score=0.0, matched_signals=[])
                for case in page
            ]

        placeholders = ",".join(f":case_id_{idx}" for idx in range(len(case_by_id)))
        signal_rows = await AsyncSQLiteSingleton().execute_query(
            f"""
            SELECT case_id, signal_type, signal_value, weight
            FROM diagnosis_case_signal_table
            WHERE case_id IN ({placeholders})
            """,
            {f"case_id_{idx}": case_id for idx, case_id in enumerate(case_by_id)},
        )

        scores: dict[str, float] = {}
        matched: dict[str, list[DiagnosisCaseSignalModel]] = {}
        for row in signal_rows:
            key = (row["signal_type"], row["signal_value"])
            query_weight = query_signals.get(key)
            if query_weight is None:
                continue
            signal = DiagnosisCaseSignalModel.model_validate(row)
            scores[row["case_id"]] = scores.get(row["case_id"], 0.0) + min(
                float(row["weight"]), query_weight
            )
            matched.setdefault(row["case_id"], []).append(signal)

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
