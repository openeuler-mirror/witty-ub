# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Historical report import: source safety, idempotency, confirmation and cases."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from latency.database.managers import report_import as import_manager_module
from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.schemas.diag_case_library import CreateDiagCaseDraftMsg
from latency.services import report_import as import_module
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.report_import import (
    CASE_CONFIRMED,
    CASE_DRAFT,
    CASE_SKIPPED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_IMPORTED,
    ImportOptions,
    ImportRenderError,
    ImportSourceError,
    collect_json_entries,
    derive_report_id,
    import_reports,
)
from latency.services.report_review import ReportReviewService


async def _none(*_args, **_kwargs):
    return None


def _fault(fault_id: str = "F01", **overrides):
    fault = {
        "id": fault_id,
        "title": "远端 Worker 处理超时",
        "status": "confirmed",
        "severity": "P1",
        "role": "primary",
        "category": "latency",
        "conclusion": {
            "one_line_conclusion": "远端 Worker 排队导致请求超时",
            "key_findings": ["P99 高于基线"],
            "first_level_label": None,
            "second_level_label": None,
        },
        "root_cause": {"confirmed_root_cause": "远端 Worker 队列积压"},
        "evidence_traces": [
            {
                "trace_id": "trace-1",
                "kind": "latency",
                "why": "P99 超基线",
                "status_code": "K_TIMEOUT",
            }
        ],
        "solution": {"short_term": ["扩容远端 Worker"]},
    }
    fault.update(overrides)
    return fault


def _payload(faults=None):
    return {
        "report": {
            "title": "历史诊断报告",
            "report_id": "OLD-REPORT-1",
            "generated_at": "2025-01-02 03:04:05",
        },
        "basic_info": {
            "kb_id": "old-kb",
            "kb_name": "旧知识库",
            "operation": "GET",
            "total_trace_cnt": 100,
        },
        "statistics": {},
        "workflow": {"steps": []},
        "faults": faults if faults is not None else [_fault()],
    }


def _write_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


@pytest.fixture
def fake_batch(monkeypatch):
    batches: dict[str, dict] = {}
    items: list[dict] = []

    async def create_batch(**kwargs):
        batches[kwargs["batch_id"]] = kwargs

    async def finish_batch(batch_id, status, summary):
        batches[batch_id]["status"] = status
        batches[batch_id]["summary"] = summary

    async def add_item(values):
        items.append(values)

    monkeypatch.setattr(
        import_manager_module.ReportImportPGManager, "create_batch", create_batch
    )
    monkeypatch.setattr(
        import_manager_module.ReportImportPGManager, "finish_batch", finish_batch
    )
    monkeypatch.setattr(
        import_manager_module.ReportImportPGManager, "add_item", add_item
    )
    async def reports_for_content(content_hash):
        return []
    monkeypatch.setattr(
        import_manager_module.ReportImportPGManager, "reports_for_content", reports_for_content
    )
    async def detach_historical_assets(report_id):
        return None
    monkeypatch.setattr(
        import_manager_module.ReportImportPGManager, "detach_historical_assets", detach_historical_assets
    )
    return batches, items


@pytest.fixture
def report_env(tmp_path, monkeypatch, fake_batch):
    root = tmp_path / "reports"
    root.mkdir()
    monkeypatch.setattr(import_module, "report_root", lambda: root)

    def render(payload, out_html, **_kwargs):
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text("<html>rendered</html>", encoding="utf-8")

    monkeypatch.setattr(import_module, "_render_report_html", render)
    upserts: list[dict] = []
    confirms: list[tuple] = []
    rows: dict[str, object] = {}

    async def get_report_index(report_id):
        return rows.get(report_id)

    async def upsert_report_index(values):
        upserts.append(values)
        rows[values["report_id"]] = SimpleNamespace(**values)

    async def confirm(report_id, expected_hash, operator, confirmation_source="review"):
        confirms.append((report_id, expected_hash, operator, confirmation_source))
        return {}

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_report_index", get_report_index
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_report_index", upsert_report_index
    )
    monkeypatch.setattr(ReportReviewService, "confirm", confirm)
    return root, upserts, confirms, fake_batch


def test_derive_report_id_is_content_addressed_and_path_safe():
    first = derive_report_id("worker-process-exit 01.json", _payload())
    second = derive_report_id("renamed-by-partner.json", _payload())
    changed = _payload()
    changed["report"]["title"] = "另一个标题"
    third = derive_report_id("worker-process-exit 01.json", changed)

    assert first == second
    assert first[0].startswith("report_hist_")
    assert first[0] == first[0].replace(" ", "")
    assert len(first[0]) <= 200
    assert third[0] != first[0]


def test_collect_json_entries_rejects_zip_traversal(tmp_path):
    archive = _write_zip(
        tmp_path / "reports.zip", {"../evil.json": b"{}"}
    )
    with pytest.raises(ImportSourceError) as excinfo:
        collect_json_entries(archive)
    assert excinfo.value.code == "zip_entry_traversal"


def test_collect_json_entries_skips_non_json_and_junk(tmp_path):
    archive = _write_zip(
        tmp_path / "reports.zip",
        {
            "reports/a.json": b"{}",
            "__MACOSX/._a.json": b"junk",
            "reports/readme.txt": b"ignored",
        },
    )
    entries = collect_json_entries(archive)
    assert [entry.name for entry in entries] == ["reports/a.json"]


async def test_import_writes_report_and_is_idempotent(report_env):
    root, upserts, confirms, (batches, items) = report_env
    source = root.parent / "one.json"
    payload = _payload()
    source.write_text(json.dumps(payload), encoding="utf-8")

    options = ImportOptions(operator="importer", index=False)
    first = await import_reports(source, options)
    report_id = first.items[0].report_id
    assert first.items[0].status == STATUS_IMPORTED
    assert first.status == "completed"
    assert (root / f"{report_id}.html").is_file()
    assert (root / f"{report_id}.source.json").read_bytes() == source.read_bytes()
    assert json.loads((root / f"{report_id}.json").read_text()) == payload
    assert upserts[0]["report_meta_id"] == "OLD-REPORT-1"
    assert upserts[0]["kb_id"] is None
    assert confirms == []

    second = await import_reports(source, options)
    assert second.items[0].status == STATUS_DUPLICATE
    assert len(upserts) == 1
    assert len(items) == 2
    assert batches[first.batch_id]["status"] == "completed"
    assert batches[second.batch_id]["summary"]["duplicate"] == 1


async def test_declared_verified_confirms_report_with_import_source(report_env):
    root, _upserts, confirms, _batch = report_env
    source = root.parent / "one.json"
    source.write_text(json.dumps(_payload()), encoding="utf-8")

    result = await import_reports(
        source,
        ImportOptions(
            operator="importer",
            declared_verified=True,
            build_cases=False,
            index=False,
        ),
    )
    item = result.items[0]
    assert item.report_confirmed is True
    assert confirms == [
        (item.report_id, item.content_hash, "importer", "import")
    ]
    assert result.summary["reports_confirmed"] == 1


async def test_build_cases_requires_declared_verified(report_env):
    root, _upserts, _confirms, _batch = report_env
    source = root.parent / "one.json"
    source.write_text(json.dumps(_payload()), encoding="utf-8")
    with pytest.raises(ValueError):
        await import_reports(
            source, ImportOptions(operator="importer", build_cases=True, index=False)
        )


async def test_external_validation_publishes_cases_without_match_signals(
    report_env, monkeypatch
):
    root, _upserts, _confirms, _batch = report_env
    created: list[tuple] = []
    confirmed: list[tuple] = []

    async def find_active_bound_case(*args, **kwargs):
        return None

    async def create_report_case(preview, operator):
        created.append((preview.source_fault_id, preview.missing_fields))
        return CreateDiagCaseDraftMsg(
            case_id=f"case-{preview.source_fault_id}", case_no="UB-CASE-000001"
        )

    async def confirm_case(case_id, req, operator_header=None, *, confirmation_source="review"):
        confirmed.append((case_id, confirmation_source))
        return None

    monkeypatch.setattr(
        DiagCaseLibraryPGManager, "find_active_bound_case", find_active_bound_case
    )
    monkeypatch.setattr(
        DiagCaseLibraryService, "create_report_case", create_report_case
    )
    monkeypatch.setattr(DiagCaseLibraryService, "confirm_case", confirm_case)
    async def verify_report_fault(report_id, fault_id, digest, operator, observed, method, **kwargs):
        confirmed.append((f"case-{fault_id}", kwargs["confirmation_source"]))
        return SimpleNamespace(case=SimpleNamespace(id=f"case-{fault_id}", case_no="UB-CASE-000001"))
    monkeypatch.setattr(DiagCaseLibraryService, "verify_report_fault", verify_report_fault)

    incomplete = _fault("F02", evidence_traces=[])
    payload = _payload([_fault("F01"), incomplete])
    source = root.parent / "two.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    result = await import_reports(
        source,
        ImportOptions(
            operator="importer",
            declared_verified=True,
            build_cases=True,
            index=False,
        ),
    )
    outcomes = {outcome.fault_id: outcome for outcome in result.items[0].cases}
    assert outcomes["F01"].status == "confirmed"
    assert outcomes["F02"].status == "confirmed"
    assert confirmed == [("case-F01", "import"), ("case-F02", "import")]
    assert result.summary["cases"]["confirmed"] == 2
    assert result.summary["cases"]["draft"] == 0


async def test_flat_report_has_stable_import_fault_and_original_preserved(report_env, monkeypatch):
    root, _upserts, _confirms, _batch = report_env
    called: list[str] = []

    async def create_report_case(preview, operator):
        called.append(preview.source_fault_id)
        return CreateDiagCaseDraftMsg()

    monkeypatch.setattr(
        DiagCaseLibraryService, "create_report_case", create_report_case
    )
    async def find_active_bound_case(*args, **kwargs):
        return None
    async def verify_report_fault(report_id, fault_id, *args, **kwargs):
        called.append(fault_id)
        return SimpleNamespace(case=SimpleNamespace(id="case-flat", case_no="UB-CASE-000001"))
    monkeypatch.setattr(DiagCaseLibraryPGManager, "find_active_bound_case", find_active_bound_case)
    monkeypatch.setattr(DiagCaseLibraryService, "verify_report_fault", verify_report_fault)
    payload = {
        "report": {"title": "扁平报告", "report_id": "OLD-2"},
        "basic_info": {"kb_id": "old-kb", "kb_name": "旧库"},
        "statistics": {},
        "workflow": {"steps": []},
        "conclusion": {
            "one_line_conclusion": "请求失败",
            "key_findings": ["错误率上升"],
            "first_level_label": None,
            "second_level_label": None,
        },
        "root_cause": {"confirmed_root_cause": "网络抖动"},
        "evidence_traces": [
            {"trace_id": "trace-9", "kind": "error", "why": "错误率", "status_code": "K_ERR"}
        ],
        "solution": {"short_term": ["检查网络"]},
    }
    source = root.parent / "flat.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    result = await import_reports(
        source,
        ImportOptions(
            operator="importer",
            declared_verified=True,
            build_cases=True,
            index=False,
        ),
    )
    outcomes = result.items[0].cases
    assert len(outcomes) == 1
    assert outcomes[0].status == "confirmed"
    assert called == ["F01"]
    report_id = result.items[0].report_id
    assert json.loads((root / f"{report_id}.source.json").read_text()) == payload
    normalized = json.loads((root / f"{report_id}.json").read_text())
    assert normalized["faults"][0]["id"] == "F01"


async def test_render_failure_leaves_no_report_files(report_env, monkeypatch):
    root, _upserts, _confirms, _batch = report_env
    source = root.parent / "one.json"
    source.write_text(json.dumps(_payload()), encoding="utf-8")

    def fail_render(payload, out_html, **_kwargs):
        raise ImportRenderError("renderer_rejected", "missing statistics")

    monkeypatch.setattr(import_module, "_render_report_html", fail_render)
    result = await import_reports(
        source, ImportOptions(operator="importer", index=False)
    )
    item = result.items[0]
    assert item.status == STATUS_FAILED
    assert item.error.startswith("renderer_rejected")
    assert list(root.iterdir()) == []


def test_collect_json_entries_reads_single_json(tmp_path):
    source = tmp_path / "one.json"
    source.write_bytes(b'{"report": {}}')
    entries = collect_json_entries(source)
    assert entries[0].name == "one.json"
    assert entries[0].data == b'{"report": {}}'




async def test_render_rejection_still_fails_by_default(report_env, monkeypatch):
    """默认严格：渲染校验不通过就不落盘。"""
    root, _upserts, _confirms, _batch = report_env
    source = root.parent / "one.json"
    source.write_text(json.dumps(_payload()), encoding="utf-8")

    def reject(payload, out_html, *, allow_incomplete=False):
        assert allow_incomplete is False
        raise ImportRenderError(
            "renderer_rejected", "faults[0].error: breakdowns 须为非空数组"
        )

    monkeypatch.setattr(import_module, "_render_report_html", reject)

    result = await import_reports(
        source, ImportOptions(operator="importer", index=False)
    )
    item = result.items[0]
    assert item.status == STATUS_FAILED
    assert item.error.startswith("renderer_rejected")


async def test_allow_incomplete_renders_rejected_report_and_builds_case(
    report_env, monkeypatch
):
    """放行后：校验失败的报告照样落盘，并建出案例；缺的字段要能被看到。"""
    root, _upserts, _confirms, _batch = report_env
    seen: list[bool] = []

    def render(payload, out_html, *, allow_incomplete=False):
        seen.append(allow_incomplete)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text("<html>rendered</html>", encoding="utf-8")

    monkeypatch.setattr(import_module, "_render_report_html", render)
    calls: list[tuple] = []

    async def verify(report_id, fault_id, content_hash, operator, *args, **kwargs):
        calls.append((report_id, fault_id))
        return SimpleNamespace(case=SimpleNamespace(id="case-1", case_no="UB-CASE-000001"))

    monkeypatch.setattr(
        import_module.DiagCaseLibraryService, "verify_report_fault", verify
    )
    monkeypatch.setattr(
        import_module.DiagCaseLibraryPGManager,"find_active_bound_case", _none
    )

    # 缺 evidence / remediation：这两项才是真正会进 missing_fields 的，
    # 摘要字段有标题兜底不会缺。
    fault = _fault()
    fault.pop("evidence_traces", None)
    fault.pop("solution", None)
    source = root.parent / "one.json"
    source.write_text(json.dumps(_payload([fault])), encoding="utf-8")

    result = await import_reports(
        source,
        ImportOptions(
            operator="importer",
            declared_verified=True,
            build_cases=True,
            index=False,
            allow_incomplete=True,
        ),
    )

    item = result.items[0]
    assert item.status == STATUS_IMPORTED
    assert seen == [True], "放行时必须把开关传给渲染器"
    assert len(calls) == 1
    assert item.cases[0].status == CASE_CONFIRMED
    degraded = result.degraded_summary()
    assert degraded["case_count"] == 1
    assert set(degraded["cases"][0]["missing_fields"]) >= {"evidence_json"}
