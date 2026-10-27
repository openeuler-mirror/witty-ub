import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from latency.access.fastapi_server import bad_request_exception_handler
from latency.exceptions import BadRequestBizException
from latency.routers.diagnostic_report import router
from latency.services import report_import
from latency.services.report_import import ImportBatchResult


@pytest.fixture
def application():
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(BadRequestBizException, bad_request_exception_handler)
    return app


async def test_path_import_options_and_identity_gate(application, tmp_path, monkeypatch):
    root = tmp_path / "permitted"
    root.mkdir()
    monkeypatch.setenv("WITTY_REPORT_IMPORT_ROOTS", str(root))
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")
    importer = AsyncMock()
    monkeypatch.setattr(report_import, "import_reports", importer)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
        options = await client.get("/diagnostic_report/import/options")
        assert options.status_code == 200
        assert options.json()["result"] == {"path_import_enabled": True, "allowed_roots": [str(root)]}
        denied = await client.post("/diagnostic_report/import/path", json={
            "path": str(root / "one.json"), "operator": "body-only",
            "source_name": "合作伙伴", "declared_verified": True,
        })
        assert denied.status_code == 400
    importer.assert_not_awaited()


async def test_path_endpoint_uses_shared_import_and_private_snapshot(application, tmp_path, monkeypatch):
    root = tmp_path / "permitted"
    root.mkdir()
    source = root / "one.json"
    content = json.dumps({"report": {"title": "外部报告"}, "conclusion": {"one_line_conclusion": "故障结论"}}).encode()
    source.write_bytes(content)
    monkeypatch.setenv("WITTY_REPORT_IMPORT_ROOTS", str(root))
    monkeypatch.delenv("WITTY_REQUIRE_TRUSTED_OPERATOR", raising=False)
    seen = []

    async def imported(path, options):
        assert path != source and path.read_bytes() == content
        assert options.operator == "importer" and options.source_name == "合作伙伴"
        assert options.declared_verified is False and options.build_cases is False
        seen.append(path)
        return ImportBatchResult(
            batch_id="batch-1", status="completed", imported_by=options.operator,
            declared_verified=False, file_count=1, summary={"imported": 1}, items=[],
        )

    monkeypatch.setattr(report_import, "import_reports", imported)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
        response = await client.post("/diagnostic_report/import/path", json={
            "path": str(source), "operator": "importer", "source_name": "合作伙伴",
            "declared_verified": False,
        })
    assert response.status_code == 200
    assert response.json()["result"]["file_count"] == 1
    assert len(seen) == 1 and not seen[0].exists()
    assert source.read_bytes() == content


async def test_content_failure_never_reaches_import_persistence(application, tmp_path, monkeypatch):
    monkeypatch.setenv("WITTY_REPORT_IMPORT_ROOTS", str(tmp_path))
    monkeypatch.delenv("WITTY_REQUIRE_TRUSTED_OPERATOR", raising=False)
    path = tmp_path / "not-report.json"
    path.write_text('{"message":"not a report"}')
    importer = AsyncMock()
    monkeypatch.setattr(report_import, "import_reports", importer)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
        response = await client.post("/diagnostic_report/import/path", json={
            "path": str(path), "operator": "importer", "source_name": "合作伙伴",
            "declared_verified": True,
        })
    assert response.status_code == 400
    assert "invalid_report" in response.json()["detail"]
    importer.assert_not_awaited()
