# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Unit tests for phenomenon search post-processing."""
from __future__ import annotations

import pytest

from latency.database.models import PhenomenonIndex
from latency.ENUM.phenomenon import BindingStatus, VerificationLevel
from latency.exceptions import (
    DependencyUnavailableBizException,
    FeatureDisabledBizException,
    UpstreamContractBizException,
)
from latency.schemas.phenomenon import SearchPhenomenonRequest
from latency.services.phenomenon_search import (
    PhenomenonSearchService,
    _CardState,
)
from latency.services.rag_client import RAGUnavailableError


def test_top_k_default_follows_configuration(monkeypatch):
    monkeypatch.delenv("RAG_TOP_K", raising=False)
    assert SearchPhenomenonRequest(query="现象").top_k == 5
    monkeypatch.setenv("RAG_TOP_K", "7")
    assert SearchPhenomenonRequest(query="现象").top_k == 7


def _card(doc_id: str, rag_doc_id: str, **overrides) -> PhenomenonIndex:
    values = {
        "doc_id": doc_id,
        "kind": "report",
        "content_source": "report",
        "report_id": "report_r",
        "source_fault_id": "F01",
        "source_fault_hash": "hash-a",
        "published_source_fault_hash": "hash-a",
        "case_id": None,
        "case_no": None,
        "legacy_case_id": None,
        "title": "GET 阻塞",
        "symptom": "GET 对象不存在时阻塞",
        "published_title": "GET 阻塞",
        "published_symptom": "GET 对象不存在时阻塞",
        "published_text": "GET 阻塞",
        "text": "GET 阻塞",
        "content_hash": "hash-a",
        "indexed_content_hash": "hash-a",
        "rag_kb_id": "kb",
        "rag_doc_id": rag_doc_id,
        "verification": VerificationLevel.REPORT_ONLY.value,
        "binding_status": BindingStatus.VALID.value,
        "operation": "GET",
        "fault_type": "latency",
        "enabled": True,
        "searchable": True,
        "index_status": "indexed",
        "retry_count": 0,
    }
    values.update(overrides)
    return PhenomenonIndex(**values)


class _FakeClient:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.calls: list[dict] = []

    async def search_chunks(self, kb_id, query, top_k, **kwargs):
        self.calls.append(
            {"kb_id": kb_id, "query": query, "top_k": top_k, **kwargs}
        )
        return self.chunks


def _patch_search_env(monkeypatch, chunks, cards):
    client = _FakeClient(chunks)
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.search_enabled", lambda: True
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.rag_kb_id", lambda: "kb"
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.rag_min_score", lambda: 0.1
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.rag_score_scale", lambda: 100.0
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.rag_is_rerank", lambda: False
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.rag_ratio", lambda: 0.5
    )
    monkeypatch.setattr(
        "latency.services.phenomenon_search.RAGClient.from_env",
        classmethod(lambda cls: client),
    )
    by_rag = {card.rag_doc_id: card for card in cards}

    async def fake_cards(pairs):
        return [by_rag[doc_id] for kb_id, doc_id in pairs if doc_id in by_rag]

    async def fake_states(cards_):
        return {
            card.doc_id: _CardState(card, case=None, report_available=True)
            for card in cards_
        }

    monkeypatch.setattr(
        "latency.database.managers.phenomenon_index.PhenomenonIndexPGManager.get_cards_by_rag_docs",
        fake_cards,
    )
    monkeypatch.setattr(
        PhenomenonSearchService, "_resolve_states", staticmethod(fake_states)
    )
    return client


async def test_score_normalized_and_duplicate_chunks_deduplicated(monkeypatch):
    cards = [_card("report:r:F01", "d1"), _card("report:r:F02", "d2", title="SET 慢")]
    _patch_search_env(
        monkeypatch,
        [
            {"doc_id": "d1", "score": 19.23},
            {"doc_id": "d1", "score": 14.0},
            {"doc_id": "d2", "score": 14.0},
        ],
        cards,
    )
    result = await PhenomenonSearchService.search(
        SearchPhenomenonRequest(query="GET 阻塞", top_k=5)
    )

    assert result.returned_count == 2
    assert result.matches[0].doc_id == "report:r:F01"
    assert result.matches[0].score == pytest.approx(0.1923)
    assert result.matches[0].score_raw == pytest.approx(19.23)
    assert result.matches[0].get_fault == "/diagnostic_report/report_r/faults/F01"
    assert result.truncated is False
    # min_score 0.1 filters out the 0.03 raw score card.
    assert all(item.score >= 0.1 for item in result.matches)


async def test_score_out_of_range_is_a_contract_error(monkeypatch):
    _patch_search_env(
        monkeypatch,
        [{"doc_id": "d1", "score": 150.0}],
        [_card("report:r:F01", "d1")],
    )
    with pytest.raises(UpstreamContractBizException):
        await PhenomenonSearchService.search(
            SearchPhenomenonRequest(query="GET 阻塞", top_k=5)
        )


async def test_search_switch_off_returns_feature_disabled(monkeypatch):
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.search_enabled", lambda: False
    )
    with pytest.raises(FeatureDisabledBizException):
        await PhenomenonSearchService.search(
            SearchPhenomenonRequest(query="GET 阻塞", top_k=5)
        )


async def test_rag_unavailable_returns_dependency_error(monkeypatch):
    monkeypatch.setattr(
        "latency.services.phenomenon_search.settings.search_enabled", lambda: True
    )

    def raise_unavailable(cls):
        raise RAGUnavailableError("down")

    monkeypatch.setattr(
        "latency.services.phenomenon_search.RAGClient.from_env",
        classmethod(raise_unavailable),
    )
    with pytest.raises(DependencyUnavailableBizException):
        await PhenomenonSearchService.search(
            SearchPhenomenonRequest(query="GET 阻塞", top_k=5)
        )


async def test_operation_mixed_reports_scope(monkeypatch):
    cards = [_card("report:r:F01", "d1", operation="MIXED")]
    _patch_search_env(monkeypatch, [{"doc_id": "d1", "score": 90.0}], cards)

    result = await PhenomenonSearchService.search(
        SearchPhenomenonRequest(query="GET 阻塞", top_k=5, operation="GET")
    )
    assert result.matches[0].operation_scope == "report"


async def test_include_unverified_filters_report_only(monkeypatch):
    cards = [_card("report:r:F01", "d1")]
    _patch_search_env(monkeypatch, [{"doc_id": "d1", "score": 90.0}], cards)

    result = await PhenomenonSearchService.search(
        SearchPhenomenonRequest(
            query="GET 阻塞", top_k=5, include_unverified=False
        )
    )
    assert result.matches == []


def test_stale_binding_hides_report_pointers():
    card = _card(
        "case:abc",
        "d1",
        kind="case",
        content_source="case",
        report_id=None,
        source_fault_id=None,
        case_id="abc",
        binding_status=BindingStatus.STALE.value,
        verification=VerificationLevel.VERIFIED.value,
    )
    state = _CardState(card, case=None, report_available=False)
    match = state.match(0.2, 20.0, None)

    assert match.report_id is None
    assert match.get_report is None
    assert match.get_fault is None
    assert match.get_case is None
