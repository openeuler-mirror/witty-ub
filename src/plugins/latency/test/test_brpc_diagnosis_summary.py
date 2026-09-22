"""BRPC summary 一页纸单元测试（/brpc-diagnosis/{knowledge,batch}/summary）。

对应设计文档 docs/design/trace-light-api.md §11.2（批次 2 后半段）：
- 响应形状固定六块：hit_count / time_range / components / top_pods /
  top_failure_modes / peak_window（单窗，非时间序列）
- 响应规模只与 top_n 绑定：components ≤ 组件枚举、top_* ≤ top_n、peak 单对象
- 时间缺省回填数据侧范围（batch 元数据 / kb 批次 min-max）
- 峰值窗口自动选窗：跨度 ≤10min→10s、≤2h→1m、否则 1h

manager 与 PGManager.session 层打桩，不依赖真实数据库；
router 层用 httpx ASGITransport 驱动请求-响应校验。
"""

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.routers.brpc_diagnosis import router
from latency.schemas.brpc_diagnosis import (
    BrpcSummaryComponentItem,
    BrpcSummaryFailureModeItem,
    BrpcSummaryMsg,
    BrpcSummaryPeakWindow,
    BrpcSummaryPodItem,
    BrpcSummaryTimeRange,
    format_brpc_api_time,
    parse_brpc_query_timestamp,
)
from latency.services.brpc_diagnosis import BrpcDiagnosisService

KB_ID = "kb-0001"
BATCH_ID = "0198aaaa-1111-7111-8111-111111111111"
BATCH_ID_2 = "0198aaaa-2222-7222-8222-222222222222"

# epoch 微秒基准
T0 = 1_786_000_000_000_000
US_S = 1_000_000
US_M = 60 * US_S
US_H = 3_600 * US_S

# service 命名空间 patch 边界（manager 打桩，不触 DB）
SESSION = "latency.services.brpc_diagnosis.PGManager.session"
GET_BATCH = "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager.get_batch"
LIST_KB_BATCHES = (
    "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager."
    "list_batches_by_kb_id"
)
COMPONENT_COUNTS = (
    "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager."
    "get_summary_component_counts"
)
POD_TOP = (
    "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager."
    "get_summary_pod_top"
)
FAILURE_MODE_COUNTS = (
    "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager."
    "get_failure_mode_hit_counts"
)
PEAK_WINDOW = (
    "latency.services.brpc_diagnosis.BrpcDiagnosisPGManager."
    "get_summary_peak_window"
)

# router 命名空间 patch 边界
REQUIRE_RESOURCE = "latency.routers.brpc_diagnosis.ResourceIdService.require"
KNOWLEDGE_SUMMARY = (
    "latency.routers.brpc_diagnosis.BrpcDiagnosisService."
    "get_knowledge_summary"
)
BATCH_SUMMARY = (
    "latency.routers.brpc_diagnosis.BrpcDiagnosisService.get_summary"
)


def make_batch_row(
    batch_id: str = BATCH_ID,
    *,
    start_timestamp: int = T0,
    end_timestamp: int = T0 + 21 * US_S,
) -> SimpleNamespace:
    return SimpleNamespace(
        batch_id=batch_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        hit_count=2,
    )


def make_component_rows() -> list[dict]:
    return [
        {"component": "ubsocket", "hit_count": 900},
        {"component": "urma", "hit_count": 100},
    ]


def make_failure_mode_rows() -> list[dict]:
    return [
        {
            "failure_mode_id": "umq.failure.a",
            "component": "umq",
            "failure_mode_name": "A",
            "hit_count": 5,
        },
        {
            "failure_mode_id": "umq.failure.b",
            "component": "umq",
            "failure_mode_name": "B",
            "hit_count": 9,
        },
        {
            "failure_mode_id": "urma.failure.c",
            "component": "urma",
            "failure_mode_name": "C",
            "hit_count": 100,
        },
    ]


@asynccontextmanager
async def _fake_session():
    yield SimpleNamespace()


def _summary_mocks(**overrides):
    """构造一组默认成功的 manager 打桩；overrides 可替换任意返回值。"""
    return {
        "get_batch": AsyncMock(return_value=make_batch_row()),
        "list_batches_by_kb_id": AsyncMock(return_value=[make_batch_row()]),
        "get_summary_component_counts": AsyncMock(
            return_value=make_component_rows()
        ),
        "get_summary_pod_top": AsyncMock(
            return_value=[{"pod_ip": "10.0.0.1", "pod_name": "pod-a", "hit_count": 420}]
        ),
        "get_failure_mode_hit_counts": AsyncMock(
            return_value=make_failure_mode_rows()
        ),
        "get_summary_peak_window": AsyncMock(
            return_value={
                "window_start_timestamp": Decimal(T0),
                "hit_count": 7,
            }
        ),
        **overrides,
    }


def make_summary_msg(**overrides) -> BrpcSummaryMsg:
    fields = dict(
        hit_count=1000,
        time_range=BrpcSummaryTimeRange(
            start_time=T0, end_time=T0 + 21 * US_S
        ),
        components=[
            BrpcSummaryComponentItem(
                component="ubsocket", hit_count=900, pct=90.0
            )
        ],
        top_pods=[
            BrpcSummaryPodItem(pod_ip="10.0.0.1", pod_name="pod-a", hit_count=420)
        ],
        top_failure_modes=[
            BrpcSummaryFailureModeItem(
                failure_mode_id="ubsocket.failure.1", name="发送超时", hit_count=380
            )
        ],
        peak_window=BrpcSummaryPeakWindow(
            start_time=T0,
            end_time=T0 + 10 * US_S,
            hit_count=900,
            window_size="10s",
        ),
    )
    fields.update(overrides)
    return BrpcSummaryMsg(**fields)


class TestSummaryService:
    async def test_batch_default_time_range_from_batch_metadata(self):
        mocks = _summary_mocks()
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, mocks["get_batch"]):
                with patch(COMPONENT_COUNTS, mocks["get_summary_component_counts"]):
                    with patch(POD_TOP, mocks["get_summary_pod_top"]):
                        with patch(
                            FAILURE_MODE_COUNTS,
                            mocks["get_failure_mode_hit_counts"],
                        ):
                            with patch(
                                PEAK_WINDOW, mocks["get_summary_peak_window"]
                            ):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID
                                )
        counts_kwargs = mocks["get_summary_component_counts"].call_args.kwargs
        assert counts_kwargs["batch_id"] == [BATCH_ID]
        assert counts_kwargs["start_timestamp"] == T0
        assert counts_kwargs["end_timestamp"] == T0 + 21 * US_S
        assert result.hit_count == 1000
        assert result.time_range.start_time == T0

    async def test_knowledge_default_range_min_max_across_batches(self):
        rows = [
            make_batch_row(BATCH_ID, start_timestamp=T0, end_timestamp=T0 + US_M),
            make_batch_row(
                BATCH_ID_2,
                start_timestamp=T0 + 10 * US_M,
                end_timestamp=T0 + 3 * US_H,
            ),
        ]
        mocks = _summary_mocks(
            list_batches_by_kb_id=AsyncMock(return_value=rows)
        )
        with patch(SESSION, _fake_session):
            with patch(LIST_KB_BATCHES, mocks["list_batches_by_kb_id"]):
                with patch(COMPONENT_COUNTS, mocks["get_summary_component_counts"]):
                    with patch(POD_TOP, mocks["get_summary_pod_top"]):
                        with patch(
                            FAILURE_MODE_COUNTS,
                            mocks["get_failure_mode_hit_counts"],
                        ):
                            with patch(
                                PEAK_WINDOW, mocks["get_summary_peak_window"]
                            ):
                                result = (
                                    await BrpcDiagnosisService.get_knowledge_summary(
                                        kb_id=KB_ID
                                    )
                                )
        counts_kwargs = mocks["get_summary_component_counts"].call_args.kwargs
        assert counts_kwargs["batch_id"] == [BATCH_ID, BATCH_ID_2]
        assert counts_kwargs["start_timestamp"] == T0
        assert counts_kwargs["end_timestamp"] == T0 + 3 * US_H
        assert result.hit_count == 1000

    @pytest.mark.parametrize(
        ("explicit", "expected"),
        [
            (
                {"start_timestamp": T0 + 60 * US_S},
                {"start_timestamp": T0 + 60 * US_S, "end_timestamp": T0 + 3 * US_H},
            ),
            (
                {"end_timestamp": T0 + 60 * US_S},
                {"start_timestamp": T0, "end_timestamp": T0 + 60 * US_S},
            ),
            (
                {
                    "start_timestamp": T0 + 60 * US_S,
                    "end_timestamp": T0 + 120 * US_S,
                },
                {"start_timestamp": T0 + 60 * US_S, "end_timestamp": T0 + 120 * US_S},
            ),
        ],
    )
    async def test_time_defaults_fill_from_data_side(self, explicit, expected):
        # 长批次窗（3h），保证单侧缺省回填后区间仍有效
        batch = make_batch_row(
            start_timestamp=T0, end_timestamp=T0 + 3 * US_H
        )
        counts = AsyncMock(return_value=make_component_rows())
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=batch)):
                with patch(COMPONENT_COUNTS, counts):
                    with patch(POD_TOP, AsyncMock(return_value=[])):
                        with patch(
                            FAILURE_MODE_COUNTS, AsyncMock(return_value=[])
                        ):
                            with patch(PEAK_WINDOW, AsyncMock(return_value=None)):
                                await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID, **explicit
                                )
        kwargs = counts.call_args.kwargs
        assert kwargs["start_timestamp"] == expected["start_timestamp"]
        assert kwargs["end_timestamp"] == expected["end_timestamp"]

    @pytest.mark.parametrize(
        ("span_us", "expected_window_us"),
        [
            (21 * US_S, 10 * US_S),          # ≤10min → 10s
            (60 * US_M, US_M),               # ≤2h → 1m
            (3 * US_H, US_H),                # >2h → 1h
        ],
    )
    async def test_peak_window_auto_size(self, span_us, expected_window_us):
        batch = make_batch_row(
            start_timestamp=T0, end_timestamp=T0 + span_us
        )
        peak = AsyncMock(
            return_value={"window_start_timestamp": Decimal(T0), "hit_count": 7}
        )
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=batch)):
                with patch(
                    COMPONENT_COUNTS, AsyncMock(return_value=make_component_rows())
                ):
                    with patch(POD_TOP, AsyncMock(return_value=[])):
                        with patch(
                            FAILURE_MODE_COUNTS, AsyncMock(return_value=[])
                        ):
                            with patch(PEAK_WINDOW, peak):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID
                                )
        assert peak.call_args.kwargs["window_us"] == expected_window_us
        assert result.peak_window.end_time == T0 + expected_window_us
        assert result.peak_window.hit_count == 7

    async def test_empty_hits_short_circuit(self):
        counts = AsyncMock(return_value=[])
        pod_top = AsyncMock(return_value=[])
        fm_counts = AsyncMock(return_value=[])
        peak = AsyncMock(return_value=None)
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with patch(COMPONENT_COUNTS, counts):
                    with patch(POD_TOP, pod_top):
                        with patch(FAILURE_MODE_COUNTS, fm_counts):
                            with patch(PEAK_WINDOW, peak):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID
                                )
        assert result.hit_count == 0
        assert result.components == []
        assert result.top_pods == []
        assert result.top_failure_modes == []
        assert result.peak_window is None
        assert result.time_range.start_time == T0
        pod_top.assert_not_awaited()
        fm_counts.assert_not_awaited()
        peak.assert_not_awaited()

    async def test_pct_components_and_top_pods_built_from_rows(self):
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with patch(
                    COMPONENT_COUNTS, AsyncMock(return_value=make_component_rows())
                ):
                    with patch(
                        POD_TOP,
                        AsyncMock(
                            return_value=[
                                {"pod_ip": "10.0.0.1", "pod_name": "pod-a", "hit_count": 420},
                                {"pod_ip": "10.0.0.2", "pod_name": None, "hit_count": 80},
                            ]
                        ),
                    ):
                        with patch(
                            FAILURE_MODE_COUNTS, AsyncMock(return_value=[])
                        ):
                            with patch(PEAK_WINDOW, AsyncMock(return_value=None)):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID
                                )
        assert result.hit_count == 1000
        assert [
            (item.component, item.hit_count, item.pct)
            for item in result.components
        ] == [("ubsocket", 900, 90.0), ("urma", 100, 10.0)]
        assert result.top_pods[1].pod_name is None
        assert result.top_pods[1].hit_count == 80

    async def test_failure_modes_component_filter_sort_and_topn(self):
        fm_counts = AsyncMock(return_value=make_failure_mode_rows())
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with patch(
                    COMPONENT_COUNTS, AsyncMock(return_value=make_component_rows())
                ):
                    with patch(POD_TOP, AsyncMock(return_value=[])):
                        with patch(FAILURE_MODE_COUNTS, fm_counts):
                            with patch(PEAK_WINDOW, AsyncMock(return_value=None)):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID,
                                    component="umq",
                                    top_n=1,
                                )
        # 复用的 failure_mode 聚合不带 component 参数（Python 侧过滤）
        assert "component" not in fm_counts.call_args.kwargs
        assert [
            (item.failure_mode_id, item.hit_count)
            for item in result.top_failure_modes
        ] == [("umq.failure.b", 9)]

    async def test_failure_modes_no_component_keeps_all_sorted(self):
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with patch(
                    COMPONENT_COUNTS, AsyncMock(return_value=make_component_rows())
                ):
                    with patch(POD_TOP, AsyncMock(return_value=[])):
                        with patch(
                            FAILURE_MODE_COUNTS,
                            AsyncMock(return_value=make_failure_mode_rows()),
                        ):
                            with patch(PEAK_WINDOW, AsyncMock(return_value=None)):
                                result = await BrpcDiagnosisService.get_summary(
                                    batch_id=BATCH_ID
                                )
        assert [
            item.failure_mode_id for item in result.top_failure_modes
        ] == ["urma.failure.c", "umq.failure.b", "umq.failure.a"]

    async def test_explicit_end_before_start_rejected(self):
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with pytest.raises(BadRequestBizException):
                    await BrpcDiagnosisService.get_summary(
                        batch_id=BATCH_ID,
                        start_timestamp=T0 + 10 * US_S,
                        end_timestamp=T0,
                    )

    async def test_defaulted_range_degenerate_rejected(self):
        # 显式 start 晚于数据侧 end 且未给 end → 回填后 end<=start
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=make_batch_row())):
                with pytest.raises(BadRequestBizException):
                    await BrpcDiagnosisService.get_summary(
                        batch_id=BATCH_ID,
                        start_timestamp=T0 + 60 * US_S,
                    )

    async def test_batch_not_found(self):
        with patch(SESSION, _fake_session):
            with patch(GET_BATCH, AsyncMock(return_value=None)):
                with pytest.raises(NotFoundBizException):
                    await BrpcDiagnosisService.get_summary(batch_id=BATCH_ID)

    async def test_knowledge_no_batches(self):
        with patch(SESSION, _fake_session):
            with patch(LIST_KB_BATCHES, AsyncMock(return_value=[])):
                with pytest.raises(NotFoundBizException):
                    await BrpcDiagnosisService.get_knowledge_summary(kb_id=KB_ID)


class TestSummarySchema:
    def test_summary_msg_strict_and_serializes_times_as_utc8(self):
        msg = make_summary_msg()
        payload = msg.model_dump(mode="json")
        assert payload["time_range"]["start_time"] == format_brpc_api_time(T0)
        assert payload["peak_window"]["window_size"] == "10s"
        assert payload["components"][0]["pct"] == 90.0

        with pytest.raises(ValueError):
            BrpcSummaryMsg(
                **{**msg.model_dump(), "unexpected": 1}
            )

    def test_pct_bounds_validated(self):
        assert (
            BrpcSummaryComponentItem(
                component="ubsocket", hit_count=1, pct=100.0
            ).pct
            == 100.0
        )
        with pytest.raises(ValueError):
            BrpcSummaryComponentItem(
                component="ubsocket", hit_count=1, pct=100.1
            )


class TestSummaryRouter:
    async def test_knowledge_summary_passthrough(self):
        msg = make_summary_msg()
        service = AsyncMock(return_value=msg)
        require = AsyncMock()
        app = FastAPI()
        app.include_router(router)
        start_ts = parse_brpc_query_timestamp("2026-08-06 15:00:00")
        end_ts = parse_brpc_query_timestamp("2026-08-06 15:01:00")

        with patch(REQUIRE_RESOURCE, new=require):
            with patch(KNOWLEDGE_SUMMARY, new=service):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        f"/brpc-diagnosis/knowledge/{KB_ID}/summary",
                        params={
                            "start_time": "2026-08-06 15:00:00",
                            "end_time": "2026-08-06 15:01:00",
                            "component": "ubsocket",
                            "top_n": 20,
                        },
                    )

        assert response.status_code == 200
        require.assert_awaited_once_with("kb", KB_ID)
        kwargs = service.call_args.kwargs
        assert kwargs["kb_id"] == KB_ID
        assert kwargs["start_timestamp"] == start_ts
        assert kwargs["end_timestamp"] == end_ts
        assert kwargs["component"] == "ubsocket"
        assert kwargs["top_n"] == 20
        body = response.json()
        assert body["code"] == 200
        assert body["result"]["hit_count"] == 1000
        assert body["result"]["time_range"]["start_time"] == format_brpc_api_time(T0)
        assert body["result"]["peak_window"]["hit_count"] == 900
        assert body["result"]["top_failure_modes"][0]["name"] == "发送超时"

    async def test_batch_summary_passthrough_and_null_peak(self):
        msg = make_summary_msg(peak_window=None)
        service = AsyncMock(return_value=msg)
        app = FastAPI()
        app.include_router(router)

        with patch(BATCH_SUMMARY, new=service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"/brpc-diagnosis/batch/{BATCH_ID}/summary"
                )

        assert response.status_code == 200
        kwargs = service.call_args.kwargs
        assert kwargs["batch_id"] == BATCH_ID
        assert kwargs["start_timestamp"] is None
        assert kwargs["top_n"] == 10
        body = response.json()
        assert body["result"]["peak_window"] is None
        assert body["result"]["top_pods"][0]["pod_ip"] == "10.0.0.1"

    @pytest.mark.parametrize(
        "params",
        [
            {"top_n": 51},
            {"top_n": 0},
            {"component": "foo"},
            {"start_time": "2026-08-06T15:00:00"},
        ],
    )
    async def test_validation_errors(self, params):
        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/brpc-diagnosis/knowledge/{KB_ID}/summary",
                params=params,
            )
        assert response.status_code == 422
