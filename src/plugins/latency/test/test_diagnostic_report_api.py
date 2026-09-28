"""诊断报告库（/diagnostic_report）单元测试。

对应设计文档 docs/design/diagnostic-report-library.md §11.1：
- POST /diagnostic_report/list         报告列表（目录扫描 + 侧车 JSON 摘要）
- GET  /diagnostic_report/{report_id}  详情（含侧车原文，供复现渲染）
- GET  /diagnostic_report/{report_id}/html  下发自包含 HTML（inline + nosniff）

数据全部在 pytest tmp_path 里构造，经 WITTY_REPORT_DIR 注入报告根目录，
不依赖真实容器目录、不依赖数据库。

被测模块：
- latency.schemas.diagnostic_report
- latency.services.diagnostic_report.DiagnosticReportService / report_root / kb_slug
- latency.routers.diagnostic_report
"""

import json
import os
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from latency.access.fastapi_server import (
    bad_request_exception_handler,
    not_found_exception_handler,
    request_validation_exception_handler,
)
from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.routers import diagnostic_report as diagnostic_report_router
from latency.schemas.diagnostic_report import (
    PAGE_CNT_MAX,
    ListDiagnosticReportsRequest,
)
from latency.services.diagnostic_report import (
    DiagnosticReportService,
    _fault_count,
    kb_slug,
    report_root,
)

KB_ALPHA = "3533f5b6-1111-2222-3333-444455556666"
KB_BETA = "alpha_beta-9"
HTML_BODY = "<html><body><h1>诊断报告</h1></body></html>"


# ---------------------------------------------------------------------------
# 造数helper
# ---------------------------------------------------------------------------
def _sidecar(report_id: str, kb_id: str, **overrides) -> dict:
    """侧车 JSON：渲染入参原样落盘 + report.report_id / generated_at 补齐。"""
    payload = {
        "report": {
            "report_id": report_id,
            "title": "KVCache 时延故障诊断报告",
            "generated_at": "2026-09-22 14:41:00",
        },
        "basic_info": {
            "kb_id": kb_id,
            "kb_name": "kvcache-测试库",
            "operation": "GET",
            "time_range_start": "2026-09-22 13:00:00",
            "time_range_end": "2026-09-22 14:00:00",
        },
        "faults": [{"id": "F01", "title": "URMA 超时"}, {"id": "F02", "title": "残差偏高"}],
    }
    payload.update(overrides)
    return payload


def _write_report(
    root: Path,
    kb_dir: str,
    name: str,
    *,
    sidecar: dict | None = None,
    mtime: float | None = None,
) -> Path:
    """落一份报告（可选侧车），返回 HTML 路径。"""
    target = root / kb_dir
    target.mkdir(parents=True, exist_ok=True)
    html = target / f"{name}.html"
    html.write_text(HTML_BODY, encoding="utf-8")
    if sidecar is not None:
        (target / f"{name}.json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )
    if mtime is not None:
        os.utime(html, (mtime, mtime))
        if sidecar is not None:
            os.utime(target / f"{name}.json", (mtime, mtime))
    return html


@pytest.fixture(autouse=True)
def report_dir(tmp_path, monkeypatch) -> Path:
    """每个用例都把报告根目录指向独立的 tmp_path（避免读到真实报告目录）。"""
    root = tmp_path / "reports"
    root.mkdir()
    monkeypatch.setenv("WITTY_REPORT_DIR", str(root))
    return root


# ---------------------------------------------------------------------------
# 根目录与命名清洗（与 render_report.py 必须同规则）
# ---------------------------------------------------------------------------
class TestReportRootAndSlug:
    def test_report_root_follows_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WITTY_REPORT_DIR", str(tmp_path))
        assert report_root() == tmp_path

    def test_report_root_falls_back_without_env(self, monkeypatch):
        monkeypatch.delenv("WITTY_REPORT_DIR", raising=False)
        assert report_root() == Path("/tmp/reports")

    def test_report_root_falls_back_on_empty_env(self, monkeypatch):
        monkeypatch.setenv("WITTY_REPORT_DIR", "")
        assert report_root() == Path("/tmp/reports")

    def test_kb_slug_keeps_safe_chars(self):
        assert kb_slug(KB_ALPHA) == KB_ALPHA

    def test_kb_slug_replaces_path_separators(self):
        # 清洗后不能残留 / 或 .，否则目录名可被用于路径穿越
        assert kb_slug("../../etc/passwd") == "______etc_passwd"
        assert "/" not in kb_slug("a/b/c")
        assert kb_slug("a b\tc") == "a_b_c"

    def test_kb_slug_falls_back_on_blank(self):
        assert kb_slug(None) == "unknown"
        assert kb_slug("") == "unknown"
        assert kb_slug("   ") == "unknown"
        assert kb_slug("../..") == "_____"


# ---------------------------------------------------------------------------
# 服务层：列表
# ---------------------------------------------------------------------------
class TestListReportsService:
    async def test_missing_root_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WITTY_REPORT_DIR", str(tmp_path / "not-created"))
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 0
        assert msg.items == []

    async def test_empty_root_returns_empty(self):
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 0
        assert msg.items == []

    async def test_sidecar_summary_mapping(self, report_dir):
        _write_report(
            report_dir,
            KB_ALPHA,
            "report_3533f5b6_20260922_144100",
            sidecar=_sidecar("report_3533f5b6_20260922_144100", KB_ALPHA),
        )
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 1
        item = msg.items[0]
        assert item.report_id == "report_3533f5b6_20260922_144100"
        assert item.kb_id == KB_ALPHA
        assert item.kb_name == "kvcache-测试库"
        assert item.title == "KVCache 时延故障诊断报告"
        assert item.generated_at == "2026-09-22 14:41:00"
        assert item.operation == "GET"
        assert item.time_range_start == "2026-09-22 13:00:00"
        assert item.time_range_end == "2026-09-22 14:00:00"
        assert item.fault_count == 2
        assert item.file_name == "report_3533f5b6_20260922_144100.html"
        assert item.file_size == len(HTML_BODY.encode("utf-8"))
        assert item.has_sidecar is True

    async def test_sidecar_missing_degrades_to_directory_metadata(self, report_dir):
        """侧车缺失：列表项仍出现，摘要字段留空，不报错。"""
        _write_report(report_dir, KB_ALPHA, "report_3533f5b6_20260922_150000")
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 1
        item = msg.items[0]
        assert item.has_sidecar is False
        assert item.kb_id == KB_ALPHA  # 侧车缺失时用目录名兜底
        assert (item.title, item.kb_name, item.generated_at, item.operation) == (
            None,
            None,
            None,
            None,
        )
        assert item.fault_count is None
        assert item.file_size > 0

    async def test_broken_sidecar_degrades_without_failing_list(self, report_dir):
        """侧车 JSON 损坏只降级单条，不影响其它报告。"""
        html = _write_report(report_dir, KB_ALPHA, "report_broken_20260922_150001")
        html.with_suffix(".json").write_text("{ not json", encoding="utf-8")
        _write_report(
            report_dir,
            KB_ALPHA,
            "report_ok_20260922_150002",
            sidecar=_sidecar("report_ok_20260922_150002", KB_ALPHA),
        )
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 2
        broken = next(i for i in msg.items if i.report_id == "report_broken_20260922_150001")
        assert broken.has_sidecar is False
        assert broken.title is None

    async def test_sorted_by_mtime_desc(self, report_dir):
        _write_report(report_dir, KB_ALPHA, "report_old_20260922_100000", mtime=1_700_000_000)
        _write_report(report_dir, KB_ALPHA, "report_new_20260922_120000", mtime=1_700_000_900)
        _write_report(report_dir, KB_ALPHA, "report_mid_20260922_110000", mtime=1_700_000_500)
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert [i.report_id for i in msg.items] == [
            "report_new_20260922_120000",
            "report_mid_20260922_110000",
            "report_old_20260922_100000",
        ]

    async def test_kb_id_filter(self, report_dir):
        _write_report(
            report_dir, KB_ALPHA, "report_a_20260922_100000",
            sidecar=_sidecar("report_a_20260922_100000", KB_ALPHA),
        )
        _write_report(
            report_dir, KB_BETA, "report_b_20260922_110000",
            sidecar=_sidecar("report_b_20260922_110000", KB_BETA),
        )
        msg = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(kb_id=KB_BETA)
        )
        assert msg.total == 1
        assert msg.items[0].report_id == "report_b_20260922_110000"

    async def test_unknown_kb_filter_returns_empty_not_error(self, report_dir):
        _write_report(report_dir, KB_ALPHA, "report_a_20260922_100000")
        msg = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(kb_id="kb-does-not-exist")
        )
        assert msg.total == 0
        assert msg.items == []

    async def test_pagination_total_is_full_count(self, report_dir):
        for index in range(5):
            _write_report(
                report_dir, KB_ALPHA, f"report_p{index}_20260922_10000{index}",
                mtime=1_700_000_000 + index,
            )
        first = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(page_num=1, page_cnt=2)
        )
        second = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(page_num=2, page_cnt=2)
        )
        last = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(page_num=3, page_cnt=2)
        )
        assert first.total == second.total == last.total == 5
        assert len(first.items) == len(second.items) == 2
        assert len(last.items) == 1
        # 分页不重叠且保持倒序
        seen = [i.report_id for i in first.items + second.items + last.items]
        assert len(set(seen)) == 5
        assert seen[0] == "report_p4_20260922_100004"

    async def test_page_beyond_range_returns_empty_items(self, report_dir):
        _write_report(report_dir, KB_ALPHA, "report_only_20260922_100000")
        msg = await DiagnosticReportService.list_reports(
            ListDiagnosticReportsRequest(page_num=9, page_cnt=10)
        )
        assert msg.total == 1
        assert msg.items == []

    async def test_root_level_report_is_listed(self, report_dir):
        """手工搬运到根目录的历史报告也要能列出（kb 归属未知）。"""
        html = report_dir / "report_kvcache_3533f5b6.html"
        html.write_text(HTML_BODY, encoding="utf-8")
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 1
        assert msg.items[0].report_id == "report_kvcache_3533f5b6"
        assert msg.items[0].kb_id is None

    async def test_non_report_files_are_ignored(self, report_dir):
        (report_dir / "README.md").write_text("x", encoding="utf-8")
        _write_report(report_dir, KB_ALPHA, "other_20260922_100000")
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.total == 0

    async def test_flat_single_fault_conclusion_count(self, report_dir):
        """扁平单故障报告：无 faults 数组时取 conclusion.fault_count。"""
        _write_report(
            report_dir,
            KB_ALPHA,
            "report_flat_20260922_100000",
            sidecar={
                "report": {"generated_at": "2026-09-22 10:00:00"},
                "basic_info": {"kb_id": KB_ALPHA},
                "conclusion": {"fault_count": 1},
            },
        )
        msg = await DiagnosticReportService.list_reports(ListDiagnosticReportsRequest())
        assert msg.items[0].fault_count == 1


class TestFaultCount:
    """``_fault_count`` 的边界：有 faults 用长度，无则看 conclusion。"""

    def test_faults_list_length_wins(self):
        assert _fault_count({"faults": [{"id": "a"}]}) == 1

    def test_empty_faults_falls_back_to_conclusion(self):
        data = {"faults": [], "conclusion": {"fault_count": 3}}
        assert _fault_count(data) == 3

    def test_no_hint_returns_none(self):
        assert _fault_count({}) is None
        assert _fault_count({"faults": []}) is None

    def test_non_positive_fault_count_becomes_single(self):
        assert _fault_count({"conclusion": {"fault_count": 0}}) == 1


# ---------------------------------------------------------------------------
# 服务层：定位与路径安全
# ---------------------------------------------------------------------------
class TestReportLocating:
    async def test_get_report_returns_sidecar_payload(self, report_dir):
        report_id = "report_3533f5b6_20260922_144100"
        payload = _sidecar(report_id, KB_ALPHA)
        _write_report(report_dir, KB_ALPHA, report_id, sidecar=payload)
        msg = await DiagnosticReportService.get_report(report_id)
        assert msg.report.report_id == report_id
        assert msg.report.fault_count == 2
        assert msg.data == payload

    async def test_get_report_without_sidecar_has_null_data(self, report_dir):
        report_id = "report_3533f5b6_20260922_150000"
        _write_report(report_dir, KB_ALPHA, report_id)
        msg = await DiagnosticReportService.get_report(report_id)
        assert msg.data is None
        assert msg.report.has_sidecar is False

    async def test_missing_report_raises_not_found(self):
        with pytest.raises(NotFoundBizException):
            await DiagnosticReportService.get_report("report_absent_20260922_100000")

    async def test_sidecar_only_file_is_not_a_report(self, report_dir):
        """只有 .json 没有 .html 时不应被当报告（避免误报可用）。"""
        target = report_dir / KB_ALPHA
        target.mkdir(parents=True)
        (target / "report_3533f5b6_20260922_144100.json").write_text("{}", encoding="utf-8")
        with pytest.raises(NotFoundBizException):
            await DiagnosticReportService.get_report("report_3533f5b6_20260922_144100")

    async def test_symlink_escape_is_rejected(self, report_dir, tmp_path):
        """符号链接指向根目录之外时，resolve 兜底必须拦成 400。"""
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "report_escape_20260922_100000.html").write_text(
            HTML_BODY, encoding="utf-8"
        )
        link = report_dir / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("当前环境不支持创建目录符号链接")
        with pytest.raises(BadRequestBizException):
            await DiagnosticReportService.resolve_html("report_escape_20260922_100000")


# ---------------------------------------------------------------------------
# 路由层（httpx ASGI：响应形状 / 参数校验 / 404）
# ---------------------------------------------------------------------------
@pytest.fixture
def report_api_app():
    app = FastAPI()
    app.include_router(diagnostic_report_router.router)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(NotFoundBizException, not_found_exception_handler)
    app.add_exception_handler(BadRequestBizException, bad_request_exception_handler)
    return app


@pytest.fixture
async def client(report_api_app):
    transport = httpx.ASGITransport(app=report_api_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDiagnosticReportRouters:
    async def test_list_envelope_and_total_items_shape(self, client, report_dir):
        report_id = "report_3533f5b6_20260922_144100"
        _write_report(report_dir, KB_ALPHA, report_id, sidecar=_sidecar(report_id, KB_ALPHA))
        response = await client.post("/diagnostic_report/list", json={"page_num": 1, "page_cnt": 20})
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert set(body) >= {"code", "message", "result"}
        assert body["result"]["total"] == 1
        assert body["result"]["items"][0]["report_id"] == report_id

    async def test_list_defaults_when_body_empty(self, client, report_dir):
        _write_report(report_dir, KB_ALPHA, "report_a_20260922_100000")
        response = await client.post("/diagnostic_report/list", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["total"] == 1
        assert body["result"]["items"][0]["has_sidecar"] is False

    async def test_list_unknown_field_is_tolerated(self, client):
        """StrictRequestModel 不做 forbid extra，前端多传字段不应 422。"""
        response = await client.post(
            "/diagnostic_report/list", json={"page_num": 1, "page_cnt": 10, "unexpected": 1}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "payload",
        [
            {"page_num": 0},
            {"page_cnt": 0},
            {"page_cnt": PAGE_CNT_MAX + 1},
            {"page_num": -1},
            {"page_cnt": "10"},  # strict 模式不接受字符串数字
        ],
    )
    async def test_list_invalid_pagination_is_422(self, client, payload):
        response = await client.post("/diagnostic_report/list", json=payload)
        assert response.status_code == 422

    async def test_list_missing_body_is_422(self, client):
        response = await client.post("/diagnostic_report/list")
        assert response.status_code == 422

    async def test_list_kb_filter_via_api(self, client, report_dir):
        _write_report(
            report_dir, KB_ALPHA, "report_a_20260922_100000",
            sidecar=_sidecar("report_a_20260922_100000", KB_ALPHA),
        )
        _write_report(
            report_dir, KB_BETA, "report_b_20260922_110000",
            sidecar=_sidecar("report_b_20260922_110000", KB_BETA),
        )
        response = await client.post("/diagnostic_report/list", json={"kb_id": KB_BETA})
        assert response.status_code == 200
        body = response.json()["result"]
        assert body["total"] == 1
        assert body["items"][0]["kb_id"] == KB_BETA

    async def test_detail_returns_sidecar_data(self, client, report_dir):
        report_id = "report_3533f5b6_20260922_144100"
        _write_report(report_dir, KB_ALPHA, report_id, sidecar=_sidecar(report_id, KB_ALPHA))
        response = await client.get(f"/diagnostic_report/{report_id}")
        assert response.status_code == 200
        body = response.json()["result"]
        assert body["report"]["report_id"] == report_id
        assert body["data"]["basic_info"]["kb_id"] == KB_ALPHA

    async def test_detail_missing_report_is_404(self, client):
        response = await client.get("/diagnostic_report/report_absent_20260922_100000")
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "report_id",
        [
            "%2E%2E",  # 编码后的 ..
            "report_3533f5b6.20260922",  # 含点（可能被当成扩展名绕过）
            "-leading-dash",  # 非法首字符
            "with space",  # 空格
            "a" * 201,  # 超长
        ],
    )
    async def test_invalid_report_id_is_422(self, client, report_id):
        response = await client.get(f"/diagnostic_report/{report_id}")
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "raw_path",
        [
            "..",  # 未编码会被 URL 归一化，落到 404 也不能下发文件
            "%2E%2E%2F%2E%2E%2Fetc%2Fpasswd",
            "%2Fetc%2Fpasswd",
        ],
    )
    async def test_path_traversal_is_never_served(self, client, raw_path):
        """编码后的路径穿越必须被拒（422 或 404），绝不能下发文件。"""
        response = await client.get(f"/diagnostic_report/{raw_path}")
        assert response.status_code in (400, 404, 422)

    async def test_html_is_inline_with_nosniff(self, client, report_dir):
        report_id = "report_3533f5b6_20260922_144100"
        _write_report(report_dir, KB_ALPHA, report_id, sidecar=_sidecar(report_id, KB_ALPHA))
        response = await client.get(f"/diagnostic_report/{report_id}/html")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.headers["content-disposition"].startswith("inline")
        assert f'filename="{report_id}.html"' in response.headers["content-disposition"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "诊断报告" in response.text

    async def test_html_missing_report_is_404(self, client):
        response = await client.get("/diagnostic_report/report_absent_20260922_100000/html")
        assert response.status_code == 404

    async def test_html_invalid_report_id_is_422(self, client):
        response = await client.get("/diagnostic_report/..%2E/html")
        assert response.status_code == 422