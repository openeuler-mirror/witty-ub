"""轻量取数层 API（/trace + /stats/*）单元测试。

对应设计文档 docs/design/trace-light-api.md 批次 1（TDD：测试先行）：
- POST /trace/list     trace 清单（粗筛主接口，时延/故障双源合并）
- GET  /trace/{id}     单 trace 下钻（轻量画像）
- POST /stats/stages   主导问题分类（组件定位入口，GET 8 桶 / SET 5 桶独立视角）

批次 2（§11.1 单维度统计）：
- POST /stats/error_codes  Top 故障码（trace 级 Counter + 日志级事件数）
- POST /stats/pods         Top Pod（时延侧聚合 + 故障侧 join）
- POST /stats/links        Top 源目对（时延侧聚合 + 故障侧 join）
- POST /stats/heatmap      时间热点（自动选窗 + slots 上限 240）

数据全部按当前表结构 mock（log_parse_result / trace_failure_event），
底层 manager 与 service 打桩，不依赖真实数据库。

被测新模块（实现前本文件 collection 失败属预期）：
- latency.schemas.trace_light.ListTracesRequest / GetStageStatsRequest /
  TraceListItem / TraceFailureCodeItem / ListTracesMsg /
  GetTraceMsg / StageStatsItem / StageStatsTopTrace / GetStageStatsMsg
- latency.schemas.trace_light（批次 2）StatsDimensionRequest /
  HeatmapStatsRequest / ErrorCodeStatItem / PodStatItem / LinkStatItem /
  HeatmapSlotItem 及各 Msg/Response
- latency.services.trace.TraceService
- latency.services.stats.StatsService
- latency.routers.trace / latency.routers.stats
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from latency.access.fastapi_server import (
    not_found_exception_handler,
    request_validation_exception_handler,
)
from latency.exceptions.biz_exceptions import NotFoundBizException
from latency.routers import stats as stats_router
from latency.routers import trace as trace_router
from latency.schemas.log import LogParseResultModel
from latency.schemas.log_failure_event import TraceFailureEventModel
from latency.schemas.trace_light import (
    ErrorCodeStatItem,
    ErrorCodeStatsMsg,
    FailureCodeCntItem,
    GetStageStatsMsg,
    GetStageStatsRequest,
    GetTraceMsg,
    HeatmapStatsMsg,
    HeatmapStatsRequest,
    HeatmapSlotItem,
    LinkStatItem,
    LinkStatsMsg,
    ListTracesMsg,
    ListTracesRequest,
    PodStatItem,
    PodStatsMsg,
    StageStatsItem,
    StageStatsTopTrace,
    StatsDimensionRequest,
    TraceFailureCodeItem,
    TraceFailureCodeStatModel,
    TraceListItem,
)
from latency.services.stats import StatsService
from latency.services.trace import TraceService

KB_ID = "kb-0001"
LOG_ID = "log-0001"

# 轻量读路径统一 patch 边界：独立 manager（trace_light.TraceLightPGManager）
TRACE_LATENCY_LIST = (
    "latency.services.trace.TraceLightPGManager.list_latency_projection"
)
TRACE_FAILURE_LIST = (
    "latency.services.trace.TraceLightPGManager."
    "list_failure_events_by_trace_ids"
)
# 故障主源路径：DB 侧聚合/排序/分页（10W~50W 行规模下推 DB）
FAILURE_CODE_STATS = (
    "latency.services.trace.TraceLightPGManager.list_failure_code_stats"
)
# 时延主源 include=failure_codes 的页内补源（trace_ids IN ≤ page_cnt，有界）
FAILURE_CODES_BY_IDS = (
    "latency.services.trace.TraceLightPGManager."
    "list_failure_codes_by_trace_ids"
)
STATS_LATENCY_LIST = (
    "latency.services.stats.LogParseResultPGManager.list_log_parse_results"
)
# 批次 2 单维度统计：SQL 聚合下推 DB（TraceLightPGManager 新增方法）
STATS_ERROR_CODES = (
    "latency.services.stats.TraceLightPGManager.list_error_code_stats"
)
STATS_PODS = "latency.services.stats.TraceLightPGManager.list_pod_stats"
STATS_LINKS = "latency.services.stats.TraceLightPGManager.list_link_stats"
STATS_FAULT_RANGE = (
    "latency.services.stats.TraceLightPGManager.list_fault_time_range"
)
STATS_HEATMAP_BUCKETS = (
    "latency.services.stats.TraceLightPGManager.list_heatmap_buckets"
)

# 8 互斥桶固定顺序（light_result._DOMINANT_BUCKET_SPEC / 设计文档 §4.3）
BUCKET_KEYS = [
    "rpc_network", "rpc_queue", "query_meta", "urma",
    "data_worker", "cross_window", "residual", "urma_timeout",
]

# SET 独立视角 5 桶固定顺序（stats._SET_BUCKET_SPEC，GET/SET key 不重叠）
SET_BUCKET_KEYS = [
    "set_urma_timeout", "set_no_evidence", "set_residual",
    "set_client", "set_worker",
]


# ---------------------------------------------------------------------------
# mock 数据工厂（按 log_parse_result / trace_failure_event 当前表结构）
# ---------------------------------------------------------------------------

def make_parse_result(
    trace_id: str,
    *,
    is_anomalous: bool = True,
    total_latency: float = 100.0,
    operation: str = "GET",
    request_mode: str = "get",
    total_latency_us: float | None = None,
    anomaly_reason: str | None = None,
    content: str | None = None,
    pod_ips: list[str] | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    host: str | None = None,
    cluster_name: str | None = None,
    timestamp: str | None = None,
    **us_fields: float,
) -> LogParseResultModel:
    """构造 log_parse_result 行；us_fields 直传 26 个 yuanrong us 字段。"""
    return LogParseResultModel(
        trace_id=trace_id,
        log_id=LOG_ID,
        is_anomalous=is_anomalous,
        total_latency=total_latency,
        operation=operation,
        request_mode=request_mode,
        total_latency_us=total_latency_us,
        anomaly_reason=anomaly_reason,
        content=content,
        pod_ips=pod_ips,
        src_ip=src_ip,
        dst_ip=dst_ip,
        host=host,
        cluster_name=cluster_name,
        timestamp=timestamp,
        **us_fields,
    )


def make_trace_failure_event(
    trace_id: str,
    *,
    status_code: list[str] | None = None,
    pod_names: list[str] | None = None,
    src_ip: str = "10.0.1.5",
    dst_ip: str = "10.0.2.8",
    host_names: list[str] | None = None,
    cluster_names: list[str] | None = None,
    timestamp: str = "2026-09-03 12:03:11",
    operation: str = "GET",
    failure_mode: list[str] | None = None,
) -> TraceFailureEventModel:
    """构造 trace_failure_event 行。"""
    return TraceFailureEventModel(
        trace_id=trace_id,
        log_id=LOG_ID,
        pod_names=pod_names if pod_names is not None else ["pod-a"],
        src_ip=src_ip,
        dst_ip=dst_ip,
        host_names=host_names if host_names is not None else ["host-101"],
        cluster_names=cluster_names if cluster_names is not None else ["cluster-1"],
        timestamp=timestamp,
        status_code=status_code or [],
        operation=operation,
        failure_mode=failure_mode or [],
    )


def patch_latency_side(total: int, rows: list[LogParseResultModel]):
    return patch(TRACE_LATENCY_LIST, new=AsyncMock(return_value=(total, rows)))


def make_failure_code_stat(
    trace_id: str,
    *,
    codes: dict[str, int] | None = None,
    operation: str = "GET",
) -> TraceFailureCodeStatModel:
    """构造 trace 故障码聚合行（manager 聚合查询的返回形态：
    codes 按 cnt 降序、code 升序，failure_cnt 为计数总和）。"""
    items = [
        FailureCodeCntItem(code=code, cnt=cnt)
        for code, cnt in sorted(
            (codes or {}).items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]
    return TraceFailureCodeStatModel(
        trace_id=trace_id,
        failure_cnt=sum(item.cnt for item in items),
        codes=items,
        operation=operation,
    )


def patch_failure_side(events: list):
    """get_trace 故障侧补源：直接返回事件投影行列表。"""
    return patch(TRACE_FAILURE_LIST, new=AsyncMock(return_value=events))


# ---------------------------------------------------------------------------
# 请求 schema 校验
# ---------------------------------------------------------------------------

class TestListTracesRequestSchema:
    def test_defaults(self):
        req = ListTracesRequest(kb_id=KB_ID)
        assert req.sort_by == "total_latency"
        assert req.sort_order == "desc"
        assert req.page_cnt == 20
        assert req.page_num == 1
        assert req.include == []

    def test_page_cnt_capped_at_500(self):
        assert ListTracesRequest(kb_id=KB_ID, page_cnt=500).page_cnt == 500
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, page_cnt=501)

    @pytest.mark.parametrize("page_cnt", [0, -1])
    def test_page_cnt_must_be_positive(self, page_cnt):
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, page_cnt=page_cnt)

    @pytest.mark.parametrize(
        "sort_by", ["total_latency", "failure_cnt", "timestamp"]
    )
    def test_sort_by_enum(self, sort_by):
        assert ListTracesRequest(kb_id=KB_ID, sort_by=sort_by).sort_by == sort_by

    @pytest.mark.parametrize("sort_by", ["bogus", "total_latency_us"])
    def test_sort_by_rejects_unknown(self, sort_by):
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, sort_by=sort_by)

    @pytest.mark.parametrize(
        "include",
        [["failure_codes"], ["topology"], ["failure_codes", "topology"]],
    )
    def test_include_enum(self, include):
        assert ListTracesRequest(kb_id=KB_ID, include=include).include == include

    def test_include_rejects_unknown(self):
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, include=["bogus"])

    def test_time_window_format(self):
        req = ListTracesRequest(
            kb_id=KB_ID,
            start_time="2026-09-03 00:00:00",
            end_time="2026-09-03 23:59:59",
        )
        assert req.start_time == "2026-09-03 00:00:00"
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, start_time="2026/09/03 00:00:00")

    def test_strict_type_no_coercion(self):
        with pytest.raises(ValueError):
            ListTracesRequest(kb_id=KB_ID, page_cnt="20")


class TestGetStageStatsRequestSchema:
    def test_defaults(self):
        req = GetStageStatsRequest(kb_id=KB_ID)
        assert req.operation == "GET"
        assert req.sample_cap == 1000

    @pytest.mark.parametrize("cap", [49, 5001, 0])
    def test_sample_cap_bounds(self, cap):
        with pytest.raises(ValueError):
            GetStageStatsRequest(kb_id=KB_ID, sample_cap=cap)

    @pytest.mark.parametrize("cap", [50, 1000, 5000])
    def test_sample_cap_valid(self, cap):
        assert GetStageStatsRequest(kb_id=KB_ID, sample_cap=cap).sample_cap == cap


# ---------------------------------------------------------------------------
# TraceService.list_traces（/trace/list）
# ---------------------------------------------------------------------------

class TestListTracesService:
    async def test_default_minimal_response_single_source(self):
        """默认最小形态 = traceid+总时延；未 include 的块不出现，不查故障侧。"""
        rows = [
            make_parse_result(
                "t-1", is_anomalous=True, total_latency=1180.5,
                timestamp="2026-09-03 12:03:11",
            ),
            make_parse_result("t-2", is_anomalous=False, total_latency=2.3),
        ]
        with (
            patch_latency_side(2, rows) as latency_mock,
            patch(TRACE_FAILURE_LIST, new=AsyncMock()) as failure_mock,
        ):
            msg = await TraceService.list_traces(ListTracesRequest(kb_id=KB_ID))

        assert msg.total == 2
        assert [i.trace_id for i in msg.items] == ["t-1", "t-2"]
        first = msg.items[0]
        assert first.total_latency_ms == 1180.5  # 原生 ms，无 us 换算
        assert first.is_anomalous is True
        assert first.operation == "GET"
        # 未 include 的块不占位
        assert first.failure_codes is None
        assert first.pod_ips is None
        # 最快路径：单查询，不触发故障侧
        latency_mock.assert_awaited_once()
        failure_mock.assert_not_awaited()

    @pytest.mark.parametrize(
        ("sort_by", "sort_order", "expected"),
        [
            ("total_latency", "desc", [("total_latency", "desc")]),
            ("total_latency", "asc", [("total_latency", "asc")]),
            ("timestamp", "desc", [("timestamp", "desc")]),
        ],
    )
    async def test_filters_and_latency_sort_forwarded_to_manager(
        self, sort_by, sort_order, expected
    ):
        """过滤参数与 total_latency/timestamp 排序透传主源原生排序。"""
        captured = []

        async def fake_list(req):
            captured.append(req)
            return (0, [])

        with patch(TRACE_LATENCY_LIST, new=fake_list):
            await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, log_id=LOG_ID, operation="GET", is_anomalous=True,
                pod_ip="10.0.1.5", host="host-101", cluster_name="cluster-1",
                src_ip="10.0.1.5", dst_ip="10.0.2.8",
                start_time="2026-09-03 00:00:00", end_time="2026-09-03 01:00:00",
                page_cnt=50, page_num=2,
                sort_by=sort_by, sort_order=sort_order,
            ))

        assert len(captured) == 1
        req = captured[0]
        assert req.kb_id == KB_ID
        assert req.log_id == LOG_ID
        assert req.operation == "GET"
        assert req.is_anomalous is True
        assert req.pod_ip == "10.0.1.5"
        assert req.host == "host-101"
        assert req.cluster_name == "cluster-1"
        assert req.src_ip == "10.0.1.5"
        assert req.dst_ip == "10.0.2.8"
        assert req.start_time == "2026-09-03 00:00:00"
        assert req.end_time == "2026-09-03 01:00:00"
        assert req.page_cnt == 50
        assert req.page_num == 2
        assert [(s.field, s.order) for s in req.sort_fields] == expected

    async def test_trace_ids_batch_forwarded(self):
        captured = []

        async def fake_list(req):
            captured.append(req)
            return (1, [make_parse_result("t-1", total_latency=1.0)])

        with patch(TRACE_LATENCY_LIST, new=fake_list):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, trace_ids=["t-1"]))

        assert captured[0].trace_ids == ["t-1"]
        assert [i.trace_id for i in msg.items] == ["t-1"]

    async def test_include_failure_codes_db_aggregation_bounded_by_page(self):
        """failure_codes 补源走 DB 聚合（list_failure_codes_by_trace_ids），
        仅按当前页 trace_ids 取数（≤ page_cnt，有界）。"""
        rows = [
            make_parse_result("t-1", total_latency=100.0),
            make_parse_result("t-2", total_latency=200.0),
        ]
        captured = {}

        async def fake_codes_by_ids(kb_id, log_id, trace_ids):
            captured["args"] = (kb_id, log_id, trace_ids)
            return [
                make_failure_code_stat("t-1", codes={"-1002": 2, "-1003": 1}),
            ]

        with (
            patch_latency_side(2, rows),
            patch(FAILURE_CODES_BY_IDS, new=fake_codes_by_ids),
        ):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, include=["failure_codes"]))

        # 补源仅按页内 trace_ids，kb/log 上下文透传
        assert captured["args"] == (KB_ID, None, ["t-1", "t-2"])
        codes = {i.trace_id: i.failure_codes for i in msg.items}
        assert codes["t-1"] == [
            TraceFailureCodeItem(code="-1002", cnt=2),
            TraceFailureCodeItem(code="-1003", cnt=1),
        ]
        # LEFT JOIN：故障侧无记录 → []，不丢条
        assert codes["t-2"] == []

    async def test_include_topology_from_latency_side(self):
        rows = [make_parse_result(
            "t-1", total_latency=100.0,
            pod_ips=["10.0.1.5", "10.0.1.6"], src_ip="10.0.1.5",
            dst_ip="10.0.2.8", host="host-101", cluster_name="cluster-1",
        )]
        with (
            patch_latency_side(1, rows),
            patch(TRACE_FAILURE_LIST, new=AsyncMock()) as failure_mock,
        ):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, include=["topology"]))

        item = msg.items[0]
        assert item.pod_ips == ["10.0.1.5", "10.0.1.6"]
        assert item.src_ip == "10.0.1.5"
        assert item.dst_ip == "10.0.2.8"
        assert item.host == "host-101"
        assert item.failure_codes is None  # topology 不触发故障侧
        failure_mock.assert_not_awaited()

    async def test_left_join_trace_without_failure_gets_empty_codes(self):
        """LEFT JOIN：整页均无故障记录 → 全页 failure_codes=[]，不丢条。"""
        rows = [make_parse_result("t-1", total_latency=100.0)]
        with (
            patch_latency_side(1, rows),
            patch(FAILURE_CODES_BY_IDS, new=AsyncMock(return_value=[])),
        ):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, include=["failure_codes"]))

        assert msg.items[0].trace_id == "t-1"
        assert msg.items[0].failure_codes == []

    async def test_sort_by_failure_cnt_uses_failure_side_as_primary(self):
        """故障主源路径：聚合/排序/分页下推 DB（list_failure_code_stats），
        纯故障 trace 不丢条。"""
        stats = [
            make_failure_code_stat("t-rich", codes={"-1002": 5}),
            make_failure_code_stat("t-poor", codes={"-1003": 1}),
            make_failure_code_stat("t-none"),
        ]
        rows = [make_parse_result("t-poor", total_latency=9.9)]
        with (
            patch(FAILURE_CODE_STATS,
                  new=AsyncMock(return_value=(3, stats))) as stats_mock,
            patch_latency_side(1, rows),
        ):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, sort_by="failure_cnt"))

        stats_mock.assert_awaited_once()
        assert msg.total == 3  # 主源 total 即响应 total（DB 侧计数）
        assert [i.trace_id for i in msg.items] == ["t-rich", "t-poor", "t-none"]
        assert [i.failure_cnt for i in msg.items] == [5, 1, 0]
        # 无时延行的故障 trace：total_latency_ms=None，不丢弃整条
        assert msg.items[0].total_latency_ms is None
        assert msg.items[1].total_latency_ms == 9.9

    async def test_status_codes_filter_uses_failure_side_semantics(self):
        """status_codes 过滤（"哪些 trace 挂了 -1002"）走故障侧语义，
        过滤参数映射并下推到 DB 聚合查询。"""
        captured = {}

        async def fake_stats(req):
            captured["req"] = req
            return 1, [make_failure_code_stat("t-hit", codes={"-1002": 2})]

        with (
            patch(FAILURE_CODE_STATS, new=fake_stats),
            patch_latency_side(
                1, [make_parse_result("t-hit", total_latency=100.0)]),
        ):
            msg = await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, status_codes=["-1002"]))

        assert captured["req"].status_codes == ["-1002"]
        assert [i.trace_id for i in msg.items] == ["t-hit"]
        assert msg.items[0].failure_codes == [
            TraceFailureCodeItem(code="-1002", cnt=2)
        ]

    async def test_failure_primary_filters_and_pagination_pushed_to_db(self):
        """故障主源：过滤字段映射（host→host_names、cluster→cluster_names）
        + 排序/分页参数下推 DB，应用侧不做全量拉取。"""
        captured = []

        async def fake_stats(req):
            captured.append(req)
            return 0, []

        with patch(FAILURE_CODE_STATS, new=fake_stats):
            await TraceService.list_traces(ListTracesRequest(
                kb_id=KB_ID, log_id=LOG_ID, operation="GET",
                host="host-101", cluster_name="cluster-1",
                src_ip="10.0.1.5", dst_ip="10.0.2.8",
                start_time="2026-09-03 00:00:00",
                end_time="2026-09-03 01:00:00",
                sort_by="failure_cnt", sort_order="asc",
                page_cnt=50, page_num=3,
                status_codes=["-1002"],
            ))

        req = captured[0]
        assert req.kb_id == KB_ID
        assert req.log_id == LOG_ID
        assert req.host_names == ["host-101"]
        assert req.cluster_names == ["cluster-1"]
        assert req.pod_names is None  # pod_ip 无故障侧等价字段，不做错误映射
        assert req.src_ip == "10.0.1.5"
        assert req.dst_ip == "10.0.2.8"
        assert req.start_time == "2026-09-03 00:00:00"
        assert req.end_time == "2026-09-03 01:00:00"
        assert req.operation == "GET"
        assert req.status_codes == ["-1002"]
        # 聚合/排序/分页下推：manager 收到原始分页参数
        assert req.sort_by == "failure_cnt"
        assert req.sort_order == "asc"
        assert req.page_cnt == 50
        assert req.page_num == 3

    async def test_empty_result_is_not_an_error(self):
        with patch_latency_side(0, []):
            msg = await TraceService.list_traces(ListTracesRequest(kb_id=KB_ID))
        assert msg.total == 0
        assert msg.items == []


# ---------------------------------------------------------------------------
# TraceService.get_trace（GET /trace/{trace_id}）
# ---------------------------------------------------------------------------

class TestGetTraceService:
    async def test_merges_both_sides_with_failure_timestamp_priority(self):
        row = make_parse_result(
            "t-abc", is_anomalous=True, total_latency=1180.5,
            pod_ips=["10.0.1.5"], src_ip="10.0.1.5", dst_ip="10.0.2.8",
            host="host-101", cluster_name="cluster-1",
            timestamp="2026-09-03 12:03:10",
        )
        failure_events = [
            make_trace_failure_event(
                "t-abc", status_code=["-1002", "-1002", "-1003"],
                timestamp="2026-09-03 12:03:11",
            ),
        ]
        with (
            patch_latency_side(1, [row]),
            patch_failure_side(failure_events),
        ):
            msg = await TraceService.get_trace("t-abc", kb_id=KB_ID)

        assert msg.trace_id == "t-abc"
        assert msg.total_latency_ms == 1180.5
        assert msg.is_anomalous is True
        assert msg.operation == "GET"
        assert msg.failure_codes == [
            TraceFailureCodeItem(code="-1002", cnt=2),
            TraceFailureCodeItem(code="-1003", cnt=1),
        ]
        assert msg.pod_ips == ["10.0.1.5"]
        assert msg.host == "host-101"
        assert msg.src_ip == "10.0.1.5"
        assert msg.dst_ip == "10.0.2.8"
        # timestamp 取故障侧最早日志时间
        assert msg.timestamp == "2026-09-03 12:03:11"

    async def test_timestamp_falls_back_to_parse_side(self):
        row = make_parse_result(
            "t-abc", total_latency=5.0, timestamp="2026-09-03 12:03:10"
        )
        with (
            patch_latency_side(1, [row]),
            patch_failure_side([]),
        ):
            msg = await TraceService.get_trace("t-abc", kb_id=KB_ID)

        assert msg.timestamp == "2026-09-03 12:03:10"
        assert msg.failure_codes == []

    async def test_pure_failure_trace_keeps_null_latency(self):
        """纯故障 trace（无时延行）：total_latency_ms=None，不丢整条。"""
        failure_events = [
            make_trace_failure_event("t-abc", status_code=["-1002"]),
        ]
        with (
            patch_latency_side(0, []),
            patch_failure_side(failure_events),
        ):
            msg = await TraceService.get_trace("t-abc", kb_id=KB_ID)

        assert msg.trace_id == "t-abc"
        assert msg.total_latency_ms is None
        assert msg.failure_codes == [TraceFailureCodeItem(code="-1002", cnt=1)]


# ---------------------------------------------------------------------------
# StatsService.get_stage_stats（POST /stats/stages）
# ---------------------------------------------------------------------------

class TestStageStatsService:
    @staticmethod
    def _patch_stats_manager(anomalous_rows, normal_rows,
                             anom_total=None, norm_total=None):
        anom_total = len(anomalous_rows) if anom_total is None else anom_total
        norm_total = len(normal_rows) if norm_total is None else norm_total

        async def fake_list(req):
            if req.is_anomalous:
                return anom_total, anomalous_rows
            return norm_total, normal_rows

        return patch(STATS_LATENCY_LIST, new=fake_list)

    async def test_dominant_classification_full_scenario(self):
        """互斥分桶 + 分位 + client 对照 + top_traces + 零计数桶全量场景。"""
        anomalous_rows = [
            # query_meta 主导（node48 风格：queryAndGet 窗口吃满总时延）
            make_parse_result(
                "t-qm-1", is_anomalous=True, total_latency=20.155,
                total_latency_us=20155.0,
                worker_access_latency_us=20150.0, urma_processing_us=5.0,
            ),
            make_parse_result(
                "t-qm-2", is_anomalous=True, total_latency=16.0,
                total_latency_us=16000.0,
                worker_access_latency_us=15100.0, urma_processing_us=100.0,
            ),
            # urma_timeout：文本匹配 + elapsedMs 证据口径
            make_parse_result(
                "t-ut-1", is_anomalous=True, total_latency=500.0,
                total_latency_us=500000.0, urma_processing_us=490000.0,
                anomaly_reason="urma wait timeout, elapsed_ms=500.0",
            ),
            # rpc_network 主导
            make_parse_result(
                "t-rn-1", is_anomalous=True, total_latency=12.0,
                total_latency_us=12000.0, sdk_rpc_network_us=10000.0,
            ),
            # 无 us 原材料 → 不进样本
            make_parse_result("t-nous-1", is_anomalous=True, total_latency=1.0),
        ]
        normal_rows = [
            # cross_window：request_mode=unknown，正常 trace
            make_parse_result(
                "t-cw-1", is_anomalous=False, total_latency=8.0,
                total_latency_us=8000.0, request_mode="unknown",
            ),
        ]
        with self._patch_stats_manager(anomalous_rows, normal_rows):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.operation == "GET"
        assert msg.sample_cnt == 5
        assert msg.truncated is False
        # 8 桶固定返回（含零计数桶），顺序固定
        assert [i.key for i in msg.items] == BUCKET_KEYS
        # 互斥：Σ trace_cnt == sample_cnt
        assert sum(i.trace_cnt for i in msg.items) == msg.sample_cnt

        by_key = {i.key: i for i in msg.items}

        qm = by_key["query_meta"]
        assert qm.trace_cnt == 2
        assert qm.fail_cnt == 2
        assert qm.success_cnt == 0
        assert qm.p50_ms == 15.0
        assert qm.p90_ms == 20.145
        assert qm.max_ms == 20.145
        assert qm.client_p50_ms == 16.0
        assert qm.client_p90_ms == 20.155
        assert qm.metric_name == "主阶段耗时"
        # top_traces 按证据耗时降序，可直接用于 /trace 批查
        assert [t.trace_id for t in qm.top_traces] == ["t-qm-1", "t-qm-2"]
        assert qm.top_traces[0].evidence_ms == 20.145
        assert qm.top_traces[0].client_ms == 20.155

        ut = by_key["urma_timeout"]
        assert ut.trace_cnt == 1
        assert ut.fail_cnt == 1
        assert ut.max_ms == 500.0  # elapsed_ms=500.0 → 500000us
        assert ut.client_p50_ms == 500.0
        assert ut.metric_name == "URMA timeout elapsedMs"
        assert ut.top_traces[0].trace_id == "t-ut-1"

        cw = by_key["cross_window"]
        assert cw.trace_cnt == 1
        assert cw.success_cnt == 1
        assert cw.fail_cnt == 0
        assert cw.max_ms == 8.0  # 交叉窗口证据取总时延

        rn = by_key["rpc_network"]
        assert rn.trace_cnt == 1
        assert rn.fail_cnt == 1

        # 零计数桶保留，分位为 None
        for key in ("urma", "residual", "data_worker", "rpc_queue"):
            assert by_key[key].trace_cnt == 0
            assert by_key[key].p50_ms is None

        # 治理指引与样本集说明
        assert all(i.action for i in msg.items)
        assert "样本集" in msg.note

    async def test_unknown_coarse_split_client_worker(self):
        """request_mode=unknown 粗分定界：worker 窗口≥50% 总时延→data_worker，
        否则 cross_window（客户端等待主导）；note 动态标注粗分口径与深挖指引。"""
        anomalous_rows = [
            # worker 窗口占 60% → data_worker（证据=worker 侧窗口）
            make_parse_result(
                "t-dw-1", is_anomalous=True, total_latency=10.0,
                total_latency_us=10000.0, request_mode="unknown",
                worker_access_latency_us=6000.0,
            ),
            # worker 窗口 30%（有窗口但干净）→ cross_window
            make_parse_result(
                "t-cw-r-1", is_anomalous=True, total_latency=10.0,
                total_latency_us=10000.0, request_mode="unknown",
                worker_access_latency_us=3000.0,
            ),
            # 无 worker 窗口（未触达数据面）→ cross_window
            make_parse_result(
                "t-cw-u-1", is_anomalous=True, total_latency=10.0,
                total_latency_us=10000.0, request_mode="unknown",
            ),
        ]
        with self._patch_stats_manager(anomalous_rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.sample_cnt == 3
        # 互斥：Σ trace_cnt == sample_cnt
        assert sum(i.trace_cnt for i in msg.items) == msg.sample_cnt
        by_key = {i.key: i for i in msg.items}

        dw = by_key["data_worker"]
        assert dw.trace_cnt == 1
        assert dw.fail_cnt == 1
        assert dw.max_ms == 6.0  # 证据=worker 侧窗口 6000us
        assert dw.top_traces[0].trace_id == "t-dw-1"
        assert "含粗分 1 条" in dw.note

        cw = by_key["cross_window"]
        assert cw.trace_cnt == 2
        assert cw.max_ms == 10.0  # 客户端等待主导，证据取总时延
        # note 动态覆盖：粗分口径 + worker 干净占比 + 未触达计数 + 深挖指引
        assert "粗分" in cw.note
        assert "客户端等待主导" in cw.note
        assert "1/2 条 worker 有窗口但干净" in cw.note
        assert "30.0%" in cw.note
        assert "1/2 条未触达数据面" in cw.note
        assert "brpc_stage_drill.py" in cw.note

        # 顶部 note 含粗分口径总说明
        assert "粗分定界" in msg.note

    async def test_unknown_coarse_split_boundary_exactly_half(self):
        """边界：worker 窗口恰=50% 总时延 → 判 data_worker（≥ 含等号）。"""
        anomalous_rows = [
            make_parse_result(
                "t-dw-edge", is_anomalous=True, total_latency=10.0,
                total_latency_us=10000.0, request_mode="unknown",
                local_worker_internal_us=5000.0,
            ),
        ]
        with self._patch_stats_manager(anomalous_rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        by_key = {i.key: i for i in msg.items}
        assert by_key["data_worker"].trace_cnt == 1
        assert by_key["cross_window"].trace_cnt == 0

    async def test_empty_attribution_subset_returns_zero_buckets_with_note(self):
        """归因子集为空（老格式缺 us 列）→ 8 桶全 0 + note，不是错误。"""
        anomalous_rows = [
            make_parse_result("t-old-1", is_anomalous=True, total_latency=3.0),
        ]
        with self._patch_stats_manager(anomalous_rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.sample_cnt == 0
        assert msg.truncated is False
        assert [i.key for i in msg.items] == BUCKET_KEYS
        assert all(i.trace_cnt == 0 for i in msg.items)
        assert msg.note  # 说明归因子集为空

    async def test_set_independent_buckets_full_scenario(self):
        """SET 独立视角：5 桶固定返回，逐桶口径与证据列实测可得。"""
        anomalous_rows = [
            # set_client：有 worker 列，SDK 段主导（node48 DS_KV_CLIENT_SET 主流）
            make_parse_result(
                "t-set-cli-1", is_anomalous=True, total_latency=21.565,
                operation="DS_KV_CLIENT_SET",
                total_latency_us=21565.0, sdk_processing_us=21511.0,
                worker_access_latency_us=35.0, local_worker_internal_us=54.0,
            ),
            # set_worker：Worker 写处理主导（node48 长尾：92.5ms 中 worker 89.6ms）
            make_parse_result(
                "t-set-wrk-1", is_anomalous=True, total_latency=92.503,
                operation="DS_POSIX_CREATE",
                total_latency_us=92503.0, sdk_processing_us=2945.0,
                worker_access_latency_us=89535.0,
                local_worker_internal_us=89558.0,
            ),
            # set_no_evidence：worker 侧列全空（数据面未观测）
            make_parse_result(
                "t-set-nev-1", is_anomalous=True, total_latency=20.3,
                operation="DS_POSIX_CREATE",
                total_latency_us=20300.0, sdk_processing_us=20300.0,
            ),
            # set_urma_timeout：文本匹配优先于 worker 分段
            make_parse_result(
                "t-set-to-1", is_anomalous=True, total_latency=100.0,
                operation="DS_POSIX_PUBLISH",
                total_latency_us=100000.0, sdk_processing_us=2000.0,
                local_worker_internal_us=1000.0,
                anomaly_reason="urma wait timeout, elapsed_ms=100.0",
            ),
            # set_residual：total − (sdk + worker) ≥ +0.5ms（残差 18ms 未被两段解释，
            # node48 侧对应唯一偏离行：total 11908 / sdk+locint 3755 → 残差 8153us）
            make_parse_result(
                "t-set-res-1", is_anomalous=True, total_latency=20.0,
                operation="DS_KV_CLIENT_SET",
                total_latency_us=20000.0, sdk_processing_us=1000.0,
                worker_access_latency_us=1000.0,
                local_worker_internal_us=1000.0,
            ),
        ]
        with self._patch_stats_manager(anomalous_rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SET"))

        assert msg.operation == "SET"
        assert msg.sample_cnt == 5
        assert msg.truncated is False
        assert [i.key for i in msg.items] == SET_BUCKET_KEYS
        # 互斥：Σ trace_cnt == sample_cnt
        assert sum(i.trace_cnt for i in msg.items) == msg.sample_cnt

        by_key = {i.key: i for i in msg.items}

        cli = by_key["set_client"]
        assert cli.trace_cnt == 1
        assert cli.fail_cnt == 1
        assert cli.max_ms == 21.511  # 证据 = sdk_processing_us
        assert cli.client_p50_ms == 21.565
        assert cli.metric_name == "主阶段耗时"
        assert cli.top_traces[0].trace_id == "t-set-cli-1"

        wrk = by_key["set_worker"]
        assert wrk.trace_cnt == 1
        assert wrk.max_ms == 89.558  # 证据 = local_worker_internal_us
        assert wrk.top_traces[0].trace_id == "t-set-wrk-1"

        nev = by_key["set_no_evidence"]
        assert nev.trace_cnt == 1
        assert nev.max_ms == 20.3  # 证据 = 总时延
        assert nev.metric_name == "Client 总时延（数据面未观测）"
        assert "DS_POSIX_CREATE" in nev.note  # 家族构成

        ut = by_key["set_urma_timeout"]
        assert ut.trace_cnt == 1
        assert ut.max_ms == 100.0  # elapsed_ms=100.0 → 100000us
        assert ut.metric_name == "URMA timeout elapsedMs"

        res = by_key["set_residual"]
        assert res.trace_cnt == 1
        assert res.max_ms == 18.0

        # 治理指引 + 样本集/剔除维度说明
        assert all(i.action for i in msg.items)
        assert "样本集" in msg.note
        for token in ("c2w", "create_latency", "publish_latency", "residual"):
            assert token in msg.note

    async def test_set_no_worker_columns_lands_in_no_evidence(self):
        """worker 侧列全空 → set_no_evidence，其余桶零计数仍返回。"""
        rows = [
            make_parse_result(
                "t-set-nev-1", is_anomalous=True, total_latency=20.22,
                operation="DS_KV_CLIENT_SET", total_latency_us=20220.0,
                sdk_processing_us=20220.0,
            ),
        ]
        with self._patch_stats_manager(rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SET"))

        by_key = {i.key: i for i in msg.items}
        assert by_key["set_no_evidence"].trace_cnt == 1
        assert by_key["set_no_evidence"].p50_ms == 20.22
        for key in ("set_client", "set_worker", "set_urma_timeout", "set_residual"):
            assert by_key[key].trace_cnt == 0
            assert by_key[key].p50_ms is None

    async def test_set_worker_dominant_long_tail(self):
        """worker 写处理 > SDK 段 → set_worker（证据取 worker 侧耗时）。"""
        rows = [
            make_parse_result(
                "t-set-wrk-1", is_anomalous=True, total_latency=92.503,
                operation="DS_POSIX_CREATE",
                total_latency_us=92503.0, sdk_processing_us=2945.0,
                worker_access_latency_us=89535.0,
                local_worker_internal_us=89558.0,
            ),
            make_parse_result(
                "t-set-wrk-2", is_anomalous=True, total_latency=80.0,
                operation="DS_POSIX_CREATE",
                total_latency_us=80000.0, sdk_processing_us=1000.0,
                local_worker_internal_us=79000.0,
            ),
        ]
        with self._patch_stats_manager(rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SET"))

        wrk = {i.key: i for i in msg.items}["set_worker"]
        assert wrk.trace_cnt == 2
        # top_traces 按证据耗时降序
        assert [t.trace_id for t in wrk.top_traces] == ["t-set-wrk-1", "t-set-wrk-2"]
        assert wrk.top_traces[0].evidence_ms == 89.558

    async def test_set_timeout_text_priority_over_worker_split(self):
        """SET 侧 URMA 超时文本匹配优先级最高（近似口径保留）。"""
        rows = [
            make_parse_result(
                "t-set-to-1", is_anomalous=True, total_latency=100.0,
                operation="DS_POSIX_PUBLISH", total_latency_us=100000.0,
                sdk_processing_us=2000.0, local_worker_internal_us=1000.0,
                content="URMA_WAIT_TIMEOUT",
            ),
        ]
        with self._patch_stats_manager(rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SET"))

        by_key = {i.key: i for i in msg.items}
        assert by_key["set_urma_timeout"].trace_cnt == 1
        assert by_key["set_worker"].trace_cnt == 0
        # 无 elapsedMs → 证据退回总时延
        assert by_key["set_urma_timeout"].max_ms == 100.0

    async def test_get_still_returns_eight_buckets_without_set_note(self):
        """GET 回归：仍为 8 桶、无 set_ 前缀、不含 SET 剔除维度说明。"""
        rows = [
            make_parse_result(
                "t-qm-1", is_anomalous=True, total_latency=20.155,
                total_latency_us=20155.0,
                worker_access_latency_us=20150.0, urma_processing_us=5.0,
            ),
        ]
        with self._patch_stats_manager(rows, []):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.operation == "GET"
        assert len(msg.items) == 8
        assert [i.key for i in msg.items] == BUCKET_KEYS
        assert not any(i.key.startswith("set_") for i in msg.items)
        assert "create_latency" not in msg.note
        assert msg.note

    async def test_unknown_operation_returns_empty_items_with_note(self):
        """未知 operation（如 SCAN）仍短路：空 items + note，不触发明细查询。"""
        with patch(STATS_LATENCY_LIST, new=AsyncMock()) as manager_mock:
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SCAN"))

        assert msg.items == []
        assert msg.operation == "SCAN"
        assert "GET" in msg.note and "SET" in msg.note
        manager_mock.assert_not_awaited()

    async def test_set_operation_forwarded_to_manager(self):
        """SET 采样下推：明细查询的 operation 必须是 "SET"。"""
        captured: list[str] = []

        async def fake_list(req):
            captured.append(req.operation)
            return 1, [
                make_parse_result(
                    "t-set-1", is_anomalous=True, total_latency=20.0,
                    operation="DS_POSIX_CREATE", total_latency_us=20000.0,
                    sdk_processing_us=20000.0,
                )
            ]

        with patch(STATS_LATENCY_LIST, new=fake_list):
            await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID, operation="SET"))

        assert captured == ["SET", "SET"]

    async def test_truncated_when_anomalous_total_exceeds_returned_rows(self):
        rows = [
            make_parse_result(
                "t-1", is_anomalous=True, total_latency=20.0,
                total_latency_us=20000.0, worker_access_latency_us=19000.0,
            ),
        ]
        with self._patch_stats_manager(rows, [], anom_total=374, norm_total=0):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.truncated is True

    async def test_anomalous_priority_dedup(self):
        """同一 trace 双侧出现 → 异常侧优先，仅计一次。"""
        dup_kwargs = dict(
            total_latency=20.0, total_latency_us=20000.0,
            worker_access_latency_us=19000.0,
        )
        anomalous_rows = [
            make_parse_result("t-dup", is_anomalous=True, **dup_kwargs),
        ]
        normal_rows = [
            make_parse_result("t-dup", is_anomalous=False, **dup_kwargs),
        ]
        with self._patch_stats_manager(anomalous_rows, normal_rows):
            msg = await StatsService.get_stage_stats(
                GetStageStatsRequest(kb_id=KB_ID))

        assert msg.sample_cnt == 1
        qm = {i.key: i for i in msg.items}["query_meta"]
        assert qm.trace_cnt == 1
        assert qm.fail_cnt == 1
        assert qm.success_cnt == 0

    async def test_request_filters_forwarded_to_manager(self):
        captured = []

        async def fake_list(req):
            captured.append(req)
            return (0, [])

        with patch(STATS_LATENCY_LIST, new=fake_list):
            await StatsService.get_stage_stats(GetStageStatsRequest(
                kb_id=KB_ID, log_id=LOG_ID, operation="GET",
                start_time="2026-09-03 00:00:00",
                end_time="2026-09-03 01:00:00",
                sample_cap=100,
            ))

        assert {r.is_anomalous for r in captured} == {True, False}
        for req in captured:
            assert req.kb_id == KB_ID
            assert req.log_id == LOG_ID
            assert req.operation == "GET"
            assert req.start_time == "2026-09-03 00:00:00"
            assert req.end_time == "2026-09-03 01:00:00"
            assert req.page_cnt == 100  # sample_cap → 取样上限
            assert [(s.field, s.order) for s in req.sort_fields] == [
                ("total_latency", "desc")
            ]


# ---------------------------------------------------------------------------
# 路由层（httpx ASGI：响应形状 / 校验 / 404）
# ---------------------------------------------------------------------------

@pytest.fixture
def light_api_app():
    app = FastAPI()
    app.include_router(trace_router.router)
    app.include_router(stats_router.router)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(NotFoundBizException, not_found_exception_handler)
    return app


@pytest.fixture
async def client(light_api_app):
    transport = httpx.ASGITransport(app=light_api_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac


class TestTraceLightRouters:
    async def test_trace_list_default_minimal_shape(self, client):
        """默认响应 items 仅含 4 个基础字段，未 include 的块不出现在 JSON。"""
        msg = ListTracesMsg(
            total=1,
            items=[TraceListItem(
                trace_id="t-abc", total_latency_ms=1180.5,
                is_anomalous=True, operation="GET",
            )],
        )
        with (
            patch("latency.routers.trace.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.trace.TraceService.list_traces",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/trace/list", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["result"]["total"] == 1
        assert set(data["result"]["items"][0]) == {
            "trace_id", "total_latency_ms", "is_anomalous", "operation",
        }
        assert data["result"]["items"][0]["trace_id"] == "t-abc"
        assert data["result"]["items"][0]["total_latency_ms"] == 1180.5

    async def test_trace_list_include_blocks_present(self, client):
        msg = ListTracesMsg(
            total=1,
            items=[TraceListItem(
                trace_id="t-abc", total_latency_ms=1180.5,
                is_anomalous=True, operation="GET",
                failure_codes=[TraceFailureCodeItem(code="-1002", cnt=3)],
                pod_ips=["10.0.1.5"], host="host-101",
                src_ip="10.0.1.5", dst_ip="10.0.2.8",
            )],
        )
        with (
            patch("latency.routers.trace.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.trace.TraceService.list_traces",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/trace/list", json={
                "kb_id": KB_ID,
                "include": ["failure_codes", "topology"],
            })

        assert resp.status_code == 200
        item = resp.json()["result"]["items"][0]
        assert set(item) == {
            "trace_id", "total_latency_ms", "is_anomalous", "operation",
            "failure_codes", "pod_ips", "host", "src_ip", "dst_ip",
        }
        assert item["failure_codes"] == [{"code": "-1002", "cnt": 3}]

    async def test_get_trace_returns_full_picture(self, client):
        msg = GetTraceMsg(
            trace_id="t-abc", total_latency_ms=1180.5, is_anomalous=True,
            operation="GET",
            failure_codes=[TraceFailureCodeItem(code="-1002", cnt=3)],
            pod_ips=["10.0.1.5"], host="host-101",
            src_ip="10.0.1.5", dst_ip="10.0.2.8",
            timestamp="2026-09-03 12:03:11",
        )
        with (
            patch("latency.routers.trace.ResourceIdService.require_trace_ids",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.trace.TraceService.get_trace",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.get("/trace/t-abc")

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["trace_id"] == "t-abc"
        assert result["total_latency_ms"] == 1180.5
        assert result["failure_codes"] == [{"code": "-1002", "cnt": 3}]
        assert result["pod_ips"] == ["10.0.1.5"]
        assert result["timestamp"] == "2026-09-03 12:03:11"

    async def test_get_trace_not_found_returns_404(self, client):
        def raise_not_found(*args, **kwargs):
            raise NotFoundBizException(
                resource="Trace", detail="不存在的 trace_id: missing"
            )

        with patch(
            "latency.routers.trace.ResourceIdService.require_trace_ids",
            new=AsyncMock(side_effect=raise_not_found),
        ):
            resp = await client.get("/trace/missing")

        assert resp.status_code == 404
        assert resp.json()["code"] == 404

    async def test_trace_list_rejects_unknown_include(self, client):
        resp = await client.post("/trace/list", json={
            "kb_id": KB_ID, "include": ["bogus"],
        })
        assert resp.status_code == 422
        assert resp.json()["code"] == 422

    async def test_trace_list_requires_kb_id(self, client):
        resp = await client.post("/trace/list", json={})
        assert resp.status_code == 422

    async def test_trace_list_rejects_page_cnt_over_500(self, client):
        resp = await client.post("/trace/list", json={
            "kb_id": KB_ID, "page_cnt": 501,
        })
        assert resp.status_code == 422

    async def test_stats_stages_passthrough(self, client):
        msg = GetStageStatsMsg(
            operation="GET", sample_cnt=1, truncated=False,
            items=[StageStatsItem(
                key="query_meta", name="QueryMeta",
                trace_cnt=1, success_cnt=0, fail_cnt=1,
                p50_ms=20.144, p90_ms=20.144, max_ms=20.183,
                client_p50_ms=20.155, client_p90_ms=20.166,
                metric_name="主阶段耗时",
                action="排查 Meta Worker 响应、元数据锁竞争。",
                note="worker_access_latency_us − urma_processing_us",
                top_traces=[StageStatsTopTrace(
                    trace_id="t-abc", evidence_ms=20.183, client_ms=20.201,
                )],
            )],
            note="样本集=异常 trace 全量+top慢正常",
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_stage_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/stages", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["operation"] == "GET"
        assert result["sample_cnt"] == 1
        assert result["truncated"] is False
        assert result["items"][0]["key"] == "query_meta"
        assert result["items"][0]["top_traces"][0]["trace_id"] == "t-abc"

    async def test_stats_stages_rejects_out_of_range_sample_cap(self, client):
        resp = await client.post("/stats/stages", json={
            "kb_id": KB_ID, "sample_cap": 10,
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 批次 2：/stats/* 单维度统计（§11.1）
# ---------------------------------------------------------------------------

class TestStatsDimensionRequestSchema:
    def test_defaults(self):
        req = StatsDimensionRequest(kb_id=KB_ID)
        assert req.log_id is None
        assert req.operation is None
        assert req.start_time is None
        assert req.end_time is None
        assert req.top_n == 20

    @pytest.mark.parametrize("top_n", [1, 20, 100])
    def test_top_n_valid(self, top_n):
        assert StatsDimensionRequest(kb_id=KB_ID, top_n=top_n).top_n == top_n

    @pytest.mark.parametrize("top_n", [0, 101, -1])
    def test_top_n_bounds(self, top_n):
        with pytest.raises(ValueError):
            StatsDimensionRequest(kb_id=KB_ID, top_n=top_n)

    def test_heatmap_defaults(self):
        req = HeatmapStatsRequest(kb_id=KB_ID)
        assert req.window_size is None
        assert req.top_n == 20  # 共用骨架字段（heatmap 不适用 top_n）

    @pytest.mark.parametrize("window_size", ["1m", "10m", "1h"])
    def test_heatmap_window_size_valid(self, window_size):
        assert (
            HeatmapStatsRequest(kb_id=KB_ID, window_size=window_size).window_size
            == window_size
        )

    def test_heatmap_window_size_rejects_unknown(self):
        with pytest.raises(ValueError):
            HeatmapStatsRequest(kb_id=KB_ID, window_size="5m")

    def test_strict_type_no_coercion(self):
        with pytest.raises(ValueError):
            StatsDimensionRequest(kb_id=KB_ID, top_n="20")


class TestDimensionStatsService:
    async def test_error_codes_passthrough_with_event_cnt(self):
        """trace_cnt 降序由 manager 保证，服务层透传 + 口径 note。"""
        items = [
            ErrorCodeStatItem(status_code="1008", trace_cnt=5093, event_cnt=12000),
            ErrorCodeStatItem(status_code="1001", trace_cnt=371, event_cnt=400),
        ]
        with patch(STATS_ERROR_CODES, new=AsyncMock(return_value=(2, items))):
            msg = await StatsService.get_error_code_stats(
                StatsDimensionRequest(kb_id=KB_ID))

        assert msg.total == 2
        assert msg.items == items
        assert "status_codes 过滤取值" in msg.note
        assert "event_cnt" in msg.note

    async def test_error_codes_event_side_unavailable_note(self):
        """log_failure_event 侧无数据 → event_cnt 全 null + note 说明。"""
        items = [
            ErrorCodeStatItem(status_code="1001", trace_cnt=371, event_cnt=None)
        ]
        with patch(STATS_ERROR_CODES, new=AsyncMock(return_value=(1, items))):
            msg = await StatsService.get_error_code_stats(
                StatsDimensionRequest(kb_id=KB_ID))

        assert msg.items[0].event_cnt is None
        assert "event_cnt 为 null" in msg.note

    async def test_error_codes_empty_items(self):
        with patch(STATS_ERROR_CODES, new=AsyncMock(return_value=(0, []))):
            msg = await StatsService.get_error_code_stats(
                StatsDimensionRequest(kb_id=KB_ID))

        assert msg.total == 0
        assert msg.items == []
        assert "status_codes" in msg.note

    async def test_error_codes_forwards_filters(self):
        captured = []

        async def fake(req):
            captured.append(req)
            return 0, []

        with patch(STATS_ERROR_CODES, new=fake):
            await StatsService.get_error_code_stats(StatsDimensionRequest(
                kb_id=KB_ID, log_id=LOG_ID, operation="GET", top_n=5,
                start_time="2026-09-03 00:00:00",
                end_time="2026-09-03 01:00:00",
            ))

        assert len(captured) == 1
        assert captured[0].kb_id == KB_ID
        assert captured[0].log_id == LOG_ID
        assert captured[0].operation == "GET"
        assert captured[0].top_n == 5

    async def test_pods_passthrough_with_note(self):
        items = [
            PodStatItem(
                pod_ip="10.0.1.5", host="host-101",
                trace_cnt=100, fault_trace_cnt=80,
            ),
            PodStatItem(
                pod_ip="10.0.1.6", host="host-102",
                trace_cnt=90, fault_trace_cnt=0,
            ),
        ]
        with patch(STATS_PODS, new=AsyncMock(return_value=(2, items))):
            msg = await StatsService.get_pod_stats(
                StatsDimensionRequest(kb_id=KB_ID))

        assert msg.total == 2
        assert msg.items == items
        assert "各 Pod 均计数一次" in msg.note
        assert "pod_ip 过滤取值" in msg.note

    async def test_links_passthrough_with_note(self):
        items = [
            LinkStatItem(
                src_ip="10.0.1.5", dst_ip="10.0.2.8",
                trace_cnt=100, fault_trace_cnt=80,
            ),
        ]
        with patch(STATS_LINKS, new=AsyncMock(return_value=(1, items))):
            msg = await StatsService.get_link_stats(
                StatsDimensionRequest(kb_id=KB_ID))

        assert msg.total == 1
        assert msg.items == items
        assert "src_ip/dst_ip" in msg.note
        assert "均非空" in msg.note


class TestHeatmapStatsService:
    @staticmethod
    def _range_mock(min_ts, max_ts):
        return patch(
            STATS_FAULT_RANGE, new=AsyncMock(return_value=(min_ts, max_ts))
        )

    @staticmethod
    def _buckets_mock(items):
        return patch(STATS_HEATMAP_BUCKETS, new=AsyncMock(return_value=items))

    async def test_auto_window_1m_for_short_span(self):
        """跨度 30min → 自动 1m，buckets 以 60s 分桶。"""
        with (
            self._range_mock(
                datetime(2026, 9, 3, 12, 0, 0),
                datetime(2026, 9, 3, 12, 30, 0),
            ),
            self._buckets_mock([
                HeatmapSlotItem(
                    window_start="2026-09-03 12:00:00", fault_trace_cnt=5
                ),
            ]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(
                HeatmapStatsRequest(kb_id=KB_ID))

        assert msg.window_size == "1m"
        assert msg.total == 1
        assert msg.items[0].window_start == "2026-09-03 12:00:00"
        buckets.assert_awaited_once()
        assert buckets.call_args[0][1] == 60
        assert "自动" in msg.note

    async def test_auto_window_10m_for_medium_span(self):
        """跨度 3h → 自动 10m（18 slots ≤ 240，不放大）。"""
        with (
            self._range_mock(
                datetime(2026, 9, 3, 9, 0, 0),
                datetime(2026, 9, 3, 12, 0, 0),
            ),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(
                HeatmapStatsRequest(kb_id=KB_ID))

        assert msg.window_size == "10m"
        assert buckets.call_args[0][1] == 600

    async def test_auto_window_enlarged_when_slots_exceed_240(self):
        """跨度 45h：自动 10m → 270 slots > 240 → 放大到 1h。"""
        with (
            self._range_mock(
                datetime(2026, 9, 1, 12, 0, 0),
                datetime(2026, 9, 3, 9, 0, 0),
            ),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(
                HeatmapStatsRequest(kb_id=KB_ID))

        assert msg.window_size == "1h"
        assert buckets.call_args[0][1] == 3600
        assert "45.0h" in msg.note

    async def test_explicit_window_not_enlarged(self):
        """指定 1m 跨度 10h（600 slots）：尊重显式选择，仅 note 提示超限。"""
        with (
            self._range_mock(
                datetime(2026, 9, 3, 2, 0, 0),
                datetime(2026, 9, 3, 12, 0, 0),
            ),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(
                HeatmapStatsRequest(kb_id=KB_ID, window_size="1m"))

        assert msg.window_size == "1m"
        assert buckets.call_args[0][1] == 60
        assert "超过 240 上限" in msg.note
        assert "指定" in msg.note

    async def test_no_data_returns_empty_with_note(self):
        with (
            self._range_mock(None, None),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(
                HeatmapStatsRequest(kb_id=KB_ID))

        assert msg.total == 0
        assert msg.window_size == "10m"
        assert msg.items == []
        assert "无故障 trace 数据" in msg.note
        buckets.assert_not_awaited()

    async def test_invalid_window_start_after_end(self):
        with (
            self._range_mock(None, None),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(HeatmapStatsRequest(
                kb_id=KB_ID,
                start_time="2026-09-03 12:30:00",
                end_time="2026-09-03 12:00:00",
            ))

        assert msg.total == 0
        assert "时间窗无效" in msg.note
        buckets.assert_not_awaited()

    async def test_request_bounds_extend_data_range(self):
        """请求时间窗宽于数据范围：跨度按请求窗计算（选窗依据请求窗）。"""
        with (
            self._range_mock(
                datetime(2026, 9, 3, 11, 50, 0),
                datetime(2026, 9, 3, 12, 0, 0),
            ),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(HeatmapStatsRequest(
                kb_id=KB_ID,
                start_time="2026-09-03 10:00:00",
                end_time="2026-09-03 12:00:00",
            ))

        # 有效跨度 2h（按请求窗）→ 1m，slots=120 ≤ 240
        assert msg.window_size == "1m"
        assert buckets.call_args[0][1] == 60

    async def test_one_sided_bound_uses_data_for_other_side(self):
        """仅给 start_time：end 取故障侧数据 max（缺省侧数据补齐）。"""
        with (
            self._range_mock(
                datetime(2026, 9, 3, 10, 0, 0),
                datetime(2026, 9, 3, 12, 0, 0),
            ),
            self._buckets_mock([]) as buckets,
        ):
            msg = await StatsService.get_heatmap_stats(HeatmapStatsRequest(
                kb_id=KB_ID, start_time="2026-09-03 09:00:00"))

        # 有效跨度 09:00→12:00 = 3h → 10m
        assert msg.window_size == "10m"
        assert buckets.call_args[0][1] == 600


class TestStatsDimensionRouters:
    async def test_error_codes_passthrough(self, client):
        msg = ErrorCodeStatsMsg(
            total=1,
            items=[ErrorCodeStatItem(
                status_code="1001", trace_cnt=371, event_cnt=400,
            )],
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_error_code_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/error_codes", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["total"] == 1
        assert result["items"][0] == {
            "status_code": "1001", "trace_cnt": 371, "event_cnt": 400,
        }

    async def test_error_codes_event_cnt_null_in_json(self, client):
        msg = ErrorCodeStatsMsg(
            total=1,
            items=[ErrorCodeStatItem(status_code="1001", trace_cnt=371)],
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_error_code_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/error_codes", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        assert resp.json()["result"]["items"][0]["event_cnt"] is None

    async def test_pods_passthrough(self, client):
        msg = PodStatsMsg(
            total=1,
            items=[PodStatItem(
                pod_ip="10.0.1.5", host="host-101",
                trace_cnt=100, fault_trace_cnt=80,
            )],
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_pod_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/pods", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["total"] == 1
        assert result["items"][0] == {
            "pod_ip": "10.0.1.5", "host": "host-101",
            "trace_cnt": 100, "fault_trace_cnt": 80,
        }

    async def test_links_passthrough(self, client):
        msg = LinkStatsMsg(
            total=1,
            items=[LinkStatItem(
                src_ip="10.0.1.5", dst_ip="10.0.2.8",
                trace_cnt=100, fault_trace_cnt=80,
            )],
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_link_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/links", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["total"] == 1
        assert result["items"][0] == {
            "src_ip": "10.0.1.5", "dst_ip": "10.0.2.8",
            "trace_cnt": 100, "fault_trace_cnt": 80,
        }

    async def test_heatmap_passthrough_with_window_size(self, client):
        msg = HeatmapStatsMsg(
            total=2, window_size="1m",
            items=[
                HeatmapSlotItem(
                    window_start="2026-09-03 12:00:00", fault_trace_cnt=5
                ),
                HeatmapSlotItem(
                    window_start="2026-09-03 12:01:00", fault_trace_cnt=8
                ),
            ],
            note="窗口 1m（自动）",
        )
        with (
            patch("latency.routers.stats.ResourceIdService.validate_request",
                  new=AsyncMock(return_value=None)),
            patch("latency.routers.stats.StatsService.get_heatmap_stats",
                  new=AsyncMock(return_value=msg)),
        ):
            resp = await client.post("/stats/heatmap", json={"kb_id": KB_ID})

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["total"] == 2
        assert result["window_size"] == "1m"
        assert result["items"][0] == {
            "window_start": "2026-09-03 12:00:00", "fault_trace_cnt": 5,
        }

    async def test_top_n_over_100_rejected(self, client):
        resp = await client.post("/stats/error_codes", json={
            "kb_id": KB_ID, "top_n": 101,
        })
        assert resp.status_code == 422
        assert resp.json()["code"] == 422

    async def test_heatmap_invalid_window_size_rejected(self, client):
        resp = await client.post("/stats/heatmap", json={
            "kb_id": KB_ID, "window_size": "5m",
        })
        assert resp.status_code == 422

    async def test_stats_dimension_requires_kb_id(self, client):
        for path in ("/stats/error_codes", "/stats/pods", "/stats/links",
                     "/stats/heatmap"):
            resp = await client.post(path, json={})
            assert resp.status_code == 422
