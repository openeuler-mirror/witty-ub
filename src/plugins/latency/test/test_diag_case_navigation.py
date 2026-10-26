# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case detail → source report navigation through the case library service."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from latency.database.managers.diag_case_library import (
    DiagCaseLibraryPGManager as Manager,
)
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.exceptions import NotFoundBizException
from latency.schemas.diag_case_library import DiagCaseLibraryModel
from latency.services import label_taxonomy
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.report_phenomenon import (
    compute_sidecar_hash,
    compute_source_fault_hash,
)

REPORT_ID = "report_kb_20261021_101500"
KB_DIR = "kb-1"
HTML_BODY = "<html><body>report</body></html>"


def _labels() -> tuple[str, str]:
    options = label_taxonomy.label_options()
    first = options["first_level_labels"][0]
    pair = next(
        item for item in options["pairs"] if item["first_level_label"] == first
    )
    return first, pair["second_level_labels"][0]


def _payload() -> dict:
    first, second = _labels()
    return {
        "report": {"title": "KVCache 时延诊断报告"},
        "basic_info": {"kb_id": KB_DIR, "operation": "GET"},
        "faults": [
            {
                "id": "F01",
                "title": "GET 阻塞",
                "status": "confirmed",
                "category": "latency",
                "conclusion": {
                    "first_level_label": first,
                    "second_level_label": second,
                    "one_line_conclusion": "GET 等待约 1.8 秒",
                },
                "root_cause": {"confirmed_root_cause": "订阅等待"},
                "evidence_traces": [{"trace_id": "t-1", "status_code": "3"}],
                "solution": {"short_term": ["重启 Worker"]},
            }
        ],
    }


@pytest.fixture(autouse=True)
def report_dir(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "reports"
    root.mkdir()
    monkeypatch.setenv("WITTY_REPORT_DIR", str(root))
    return root


def _write_report(root: Path, sidecar: dict | None) -> None:
    directory = root / KB_DIR
    directory.mkdir(parents=True, exist_ok=True)
    html = directory / f"{REPORT_ID}.html"
    html.write_text(HTML_BODY, encoding="utf-8")
    if sidecar is not None:
        html.with_suffix(".json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )


def _install_case(monkeypatch, case) -> None:
    async def get_case(case_id):
        return case

    monkeypatch.setattr(Manager, "get_case", staticmethod(get_case))


def _install_report_index(monkeypatch, row) -> None:
    async def get_report_index(report_id):
        return row

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_report_index", staticmethod(get_report_index)
    )


def _bound_case(payload: dict) -> DiagCaseLibraryModel:
    fault = payload["faults"][0]
    first = fault["conclusion"]["first_level_label"]
    second = fault["conclusion"]["second_level_label"]
    version = label_taxonomy.label_options()["version"]
    return DiagCaseLibraryModel(
        id="case-1",
        status="confirmed",
        report_id=REPORT_ID,
        source_fault_id="F01",
        source_fault_hash=compute_source_fault_hash(fault, "F01", "GET"),
        first_level_label=first,
        second_level_label=second,
        source_label_hash=label_taxonomy.label_snapshot_hash(first, second, version),
    )


async def test_case_detail_of_an_independent_case_has_no_source_link(monkeypatch):
    case = DiagCaseLibraryModel(id="case-1", status="confirmed")
    _install_case(monkeypatch, case)

    msg = await DiagCaseLibraryService.get_case("case-1")

    assert msg.case.id == "case-1"
    assert msg.source_report.status == "independent"
    assert msg.source_report.get_report is None
    assert msg.source_report.get_fault is None


async def test_case_detail_links_a_current_report_fault(report_dir, monkeypatch):
    payload = _payload()
    _write_report(report_dir, payload)
    case = _bound_case(payload)
    _install_case(monkeypatch, case)
    _install_report_index(
        monkeypatch,
        SimpleNamespace(
            confirmed_by="alice",
            confirmed_at=datetime(2026, 10, 21, 11, 0, 0),
            confirmed_sidecar_hash=compute_sidecar_hash(payload),
        ),
    )

    msg = await DiagCaseLibraryService.get_case("case-1")

    assert msg.source_report.status == "valid"
    assert msg.source_report.review_status == "confirmed"
    assert msg.source_report.classification_status == "valid"
    assert msg.source_report.get_report == f"/diagnostic_report/{REPORT_ID}"
    assert msg.source_report.get_fault == (
        f"/diagnostic_report/{REPORT_ID}/faults/F01"
    )


async def test_case_detail_marks_a_deleted_report(report_dir, monkeypatch):
    case = _bound_case(_payload())
    _install_case(monkeypatch, case)

    msg = await DiagCaseLibraryService.get_case("case-1")

    assert msg.source_report.status == "deleted"
    assert msg.source_report.report_id == REPORT_ID
    assert msg.source_report.get_report is None


async def test_case_detail_degrades_when_navigation_fails(monkeypatch):
    case = _bound_case(_payload())
    _install_case(monkeypatch, case)

    async def explode(case_arg):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "latency.services.diag_case_library.ReportReviewService.describe_case_source",
        staticmethod(explode),
    )

    msg = await DiagCaseLibraryService.get_case("case-1")

    assert msg.case.id == "case-1"
    assert msg.source_report.status == "unavailable"
    assert msg.source_report.classification_status == "unavailable"


async def test_case_detail_missing_case_is_not_found(monkeypatch):
    async def get_case(case_id):
        return None

    monkeypatch.setattr(Manager, "get_case", staticmethod(get_case))

    with pytest.raises(NotFoundBizException):
        await DiagCaseLibraryService.get_case("case-absent")
