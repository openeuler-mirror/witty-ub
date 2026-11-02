# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Ops snapshot and threshold alerts for phenomenon indexing and retrieval."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from latency.common.local_time import local_now
from latency.config import phenomenon as settings
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager as Mgr
from latency.schemas.phenomenon import (
    CardCountsModel,
    PhenomenonAlertModel,
    PhenomenonStatusMsg,
    QueueCountsModel,
    ReportIndexCountsModel,
    RetrievalStatsModel,
)
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.phenomenon_search import retrieval_snapshot

CARD_FAILURE_RATE_WARNING = 0.01
CARD_FAILURE_RATE_CRITICAL = 0.05
CLEANUP_BACKLOG_WARNING = 5000
CLEANUP_BACKLOG_CRITICAL = 10000
CLEANUP_OLDEST_WARNING_SECONDS = 3600
EVENT_BACKLOG_WARNING = 1000
EVENT_OLDEST_WARNING_SECONDS = 600
STUCK_PARSING_WARNING = 1
STUCK_PARSING_CRITICAL = 10
RETRIEVAL_MIN_REQUESTS = 20
RETRIEVAL_ERROR_RATE_CRITICAL = 0.05
RETRIEVAL_P95_CRITICAL_MS = 2000.0


def _age_seconds(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    return max(0, int((now - value).total_seconds()))


class PhenomenonStatusService:
    """Read-only snapshot; never mutates cards, queues or RAG state."""

    @staticmethod
    async def snapshot() -> PhenomenonStatusMsg:
        report_counts = await Mgr.report_status_counts()
        card_counts = await Mgr.card_status_counts_all()
        searchable = await Mgr.searchable_card_count()
        cleanup_count, cleanup_oldest = await Mgr.cleanup_backlog()
        event_count, event_oldest = await Mgr.event_backlog()
        stuck = await Mgr.stuck_parsing_count()
        retrieval = RetrievalStatsModel(**retrieval_snapshot())

        index_enabled = settings.index_enabled()
        search_enabled = settings.search_enabled()
        self_check_enabled = settings.self_check_enabled()
        self_check_done = PhenomenonIndexService.self_check_done()
        rag_configured = bool(settings.rag_core_url() and settings.rag_kb_id())

        now = local_now()
        cleanup_age = _age_seconds(cleanup_oldest, now)
        event_age = _age_seconds(event_oldest, now)
        enabled_cards = sum(card_counts.values())
        failed_cards = int(card_counts.get("failed", 0))
        alerts = PhenomenonStatusService._alerts(
            index_enabled=index_enabled,
            search_enabled=search_enabled,
            self_check_enabled=self_check_enabled,
            self_check_done=self_check_done,
            rag_configured=rag_configured,
            enabled_cards=enabled_cards,
            failed_cards=failed_cards,
            cleanup_count=cleanup_count,
            cleanup_age=cleanup_age,
            event_count=event_count,
            event_age=event_age,
            stuck=stuck,
            retrieval=retrieval,
        )
        return PhenomenonStatusMsg(
            index_enabled=index_enabled,
            search_enabled=search_enabled,
            self_check_enabled=self_check_enabled,
            self_check_done=self_check_done,
            rag_configured=rag_configured,
            reports=ReportIndexCountsModel(
                total=sum(report_counts.values()), by_status=report_counts
            ),
            cards=CardCountsModel(
                enabled=enabled_cards, searchable=searchable, by_status=card_counts
            ),
            queues=QueueCountsModel(
                cleanup_active=cleanup_count,
                cleanup_oldest_age_seconds=cleanup_age,
                events_active=event_count,
                events_oldest_age_seconds=event_age,
                stuck_parsing=stuck,
            ),
            retrieval=retrieval,
            alerts=alerts,
        )

    @staticmethod
    def _alerts(
        *,
        index_enabled: bool,
        search_enabled: bool,
        self_check_enabled: bool,
        self_check_done: bool,
        rag_configured: bool,
        enabled_cards: int,
        failed_cards: int,
        cleanup_count: int,
        cleanup_age: int | None,
        event_count: int,
        event_age: int | None,
        stuck: int,
        retrieval: RetrievalStatsModel,
    ) -> list[PhenomenonAlertModel]:
        alerts: list[PhenomenonAlertModel] = []

        def add(
            code: str,
            severity: Literal["warning", "critical"],
            message: str,
            value: float | int | str | None,
            threshold: float | int | str | None,
        ) -> None:
            alerts.append(
                PhenomenonAlertModel(
                    code=code,
                    severity=severity,
                    message=message,
                    value=value,
                    threshold=threshold,
                )
            )

        if (index_enabled or search_enabled) and not rag_configured:
            add(
                "rag_not_configured",
                "critical",
                "索引或检索已启用，但 RAG 地址或现象专用知识库未配置",
                None,
                "RAG_CORE_URL + RAG_PHENOMENON_KB_ID",
            )
        if index_enabled and self_check_enabled and not self_check_done:
            add(
                "self_check_not_passed",
                "warning",
                "启动自检尚未通过，上传→解析→检索链路可能不可用",
                None,
                "upload→parse→search",
            )

        if enabled_cards:
            failure_rate = failed_cards / enabled_cards
            if failure_rate > CARD_FAILURE_RATE_CRITICAL:
                add(
                    "card_failure_rate_high",
                    "critical",
                    "现象卡片失败率超过 5%",
                    round(failure_rate, 4),
                    CARD_FAILURE_RATE_CRITICAL,
                )
            elif failure_rate > CARD_FAILURE_RATE_WARNING:
                add(
                    "card_failure_rate_high",
                    "warning",
                    "现象卡片失败率超过 1%",
                    round(failure_rate, 4),
                    CARD_FAILURE_RATE_WARNING,
                )

        if cleanup_count > CLEANUP_BACKLOG_CRITICAL:
            add(
                "cleanup_backlog_high",
                "critical",
                "RAG 清理任务积压超过 10,000",
                cleanup_count,
                CLEANUP_BACKLOG_CRITICAL,
            )
        elif cleanup_count > CLEANUP_BACKLOG_WARNING:
            add(
                "cleanup_backlog_high",
                "warning",
                "RAG 清理任务积压超过 5,000",
                cleanup_count,
                CLEANUP_BACKLOG_WARNING,
            )
        if cleanup_age is not None and cleanup_age > CLEANUP_OLDEST_WARNING_SECONDS:
            add(
                "cleanup_oldest_stale",
                "warning",
                "最老 RAG 清理任务等待超过 1 小时",
                cleanup_age,
                CLEANUP_OLDEST_WARNING_SECONDS,
            )

        if event_count > EVENT_BACKLOG_WARNING:
            add(
                "event_backlog_high",
                "warning",
                "索引事件积压超过 1,000",
                event_count,
                EVENT_BACKLOG_WARNING,
            )
        if event_age is not None and event_age > EVENT_OLDEST_WARNING_SECONDS:
            add(
                "event_oldest_stale",
                "warning",
                "最老索引事件等待超过 10 分钟",
                event_age,
                EVENT_OLDEST_WARNING_SECONDS,
            )

        if stuck >= STUCK_PARSING_CRITICAL:
            add(
                "parsing_stuck",
                "critical",
                "超过 30 分钟仍处于 parsing 的卡片过多",
                stuck,
                STUCK_PARSING_CRITICAL,
            )
        elif stuck >= STUCK_PARSING_WARNING:
            add(
                "parsing_stuck",
                "warning",
                "存在超过 30 分钟仍处于 parsing 的卡片",
                stuck,
                STUCK_PARSING_WARNING,
            )

        if retrieval.requests >= RETRIEVAL_MIN_REQUESTS:
            if retrieval.error_rate > RETRIEVAL_ERROR_RATE_CRITICAL:
                add(
                    "retrieval_error_rate_high",
                    "critical",
                    "近 5 分钟现象检索失败率超过 5%",
                    retrieval.error_rate,
                    RETRIEVAL_ERROR_RATE_CRITICAL,
                )
            if (
                retrieval.p95_ms is not None
                and retrieval.p95_ms > RETRIEVAL_P95_CRITICAL_MS
            ):
                add(
                    "retrieval_p95_high",
                    "critical",
                    "近 5 分钟现象检索 p95 超过 2 秒",
                    retrieval.p95_ms,
                    RETRIEVAL_P95_CRITICAL_MS,
                )
        return alerts
