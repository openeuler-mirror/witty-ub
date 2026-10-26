"""Ops snapshot thresholds and the rolling retrieval window."""
import pytest

from latency.config import phenomenon as settings
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager as Mgr
from latency.services import phenomenon_search
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.phenomenon_status import PhenomenonStatusService


def _reset_retrieval() -> None:
    phenomenon_search._RETRIEVAL_EVENTS.clear()


def test_retrieval_snapshot_prunes_old_events_and_reports_p95():
    _reset_retrieval()
    phenomenon_search.record_retrieval(0.1, True, at=400.0)
    phenomenon_search.record_retrieval(0.2, True, at=401.0)
    phenomenon_search.record_retrieval(4.0, False, at=402.0)
    phenomenon_search.record_retrieval(0.3, True, at=100.0)

    snapshot = phenomenon_search.retrieval_snapshot(now=402.0)

    assert snapshot["requests"] == 3
    assert snapshot["errors"] == 1
    assert snapshot["error_rate"] == pytest.approx(1 / 3, abs=0.0001)
    assert snapshot["p95_ms"] == 4000.0
    _reset_retrieval()


def _patch_snapshot(monkeypatch, *, cards, searchable, cleanup=(0, None), events=(0, None), stuck=0):
    async def report_counts():
        return {"indexed": 2}

    async def card_counts():
        return cards

    async def searchable_count():
        return searchable

    async def cleanup_backlog():
        return cleanup

    async def event_backlog():
        return events

    async def stuck_count():
        return stuck

    monkeypatch.setattr(Mgr, "report_status_counts", staticmethod(report_counts))
    monkeypatch.setattr(Mgr, "card_status_counts_all", staticmethod(card_counts))
    monkeypatch.setattr(Mgr, "searchable_card_count", staticmethod(searchable_count))
    monkeypatch.setattr(Mgr, "cleanup_backlog", staticmethod(cleanup_backlog))
    monkeypatch.setattr(Mgr, "event_backlog", staticmethod(event_backlog))
    monkeypatch.setattr(Mgr, "stuck_parsing_count", staticmethod(stuck_count))


@pytest.mark.asyncio
async def test_status_snapshot_is_clean_when_index_is_healthy(monkeypatch):
    _reset_retrieval()
    monkeypatch.setattr(settings, "index_enabled", lambda: True)
    monkeypatch.setattr(settings, "search_enabled", lambda: True)
    monkeypatch.setattr(settings, "self_check_enabled", lambda: True)
    monkeypatch.setattr(settings, "rag_core_url", lambda: "http://rag")
    monkeypatch.setattr(settings, "rag_kb_id", lambda: "kb")
    monkeypatch.setattr(
        PhenomenonIndexService, "self_check_done", staticmethod(lambda: True)
    )
    _patch_snapshot(monkeypatch, cards={"indexed": 10}, searchable=8)

    msg = await PhenomenonStatusService.snapshot()

    assert msg.index_enabled and msg.search_enabled
    assert msg.rag_configured and msg.self_check_done
    assert msg.reports.total == 2
    assert msg.cards.enabled == 10
    assert msg.cards.searchable == 8
    assert msg.alerts == []


@pytest.mark.asyncio
async def test_status_snapshot_flags_failure_backlog_and_retrieval(monkeypatch):
    _reset_retrieval()
    monkeypatch.setattr(settings, "index_enabled", lambda: True)
    monkeypatch.setattr(settings, "search_enabled", lambda: True)
    monkeypatch.setattr(settings, "self_check_enabled", lambda: True)
    monkeypatch.setattr(settings, "rag_core_url", lambda: None)
    monkeypatch.setattr(settings, "rag_kb_id", lambda: None)
    monkeypatch.setattr(
        PhenomenonIndexService, "self_check_done", staticmethod(lambda: False)
    )
    _patch_snapshot(
        monkeypatch,
        cards={"failed": 6, "indexed": 94},
        searchable=80,
        cleanup=(10001, None),
        events=(1200, None),
        stuck=10,
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_status.retrieval_snapshot",
        lambda: {
            "window_seconds": 300,
            "requests": 20,
            "errors": 6,
            "error_rate": 0.3,
            "p95_ms": 2500.0,
        },
    )

    msg = await PhenomenonStatusService.snapshot()

    codes = {alert.code for alert in msg.alerts}
    assert {
        "rag_not_configured",
        "self_check_not_passed",
        "card_failure_rate_high",
        "cleanup_backlog_high",
        "event_backlog_high",
        "parsing_stuck",
        "retrieval_error_rate_high",
        "retrieval_p95_high",
    } <= codes
    critical = {alert.code for alert in msg.alerts if alert.severity == "critical"}
    assert {"rag_not_configured", "cleanup_backlog_high", "retrieval_p95_high"} <= critical
