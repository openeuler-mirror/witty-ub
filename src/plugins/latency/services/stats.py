# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""统计服务（/stats/*）。

主导问题分类（/stats/stages，组件定位入口）：
血缘：yuanrong-scripts/ds_trace_bottleneck.py 的 problem_summary
（图 1-1 主问题 Trace 数 / 图 1-2 关键证据耗时）。
四件套（桶定义 / 26 us 字段 8 维归因 / 互斥分类 / 采样）自 light_result.py
平移（设计文档 docs/design/trace-light-api.md §4.3），增量三处：
- 聚合时同步收集 Client 总时延分位（client_p50_ms / client_p90_ms）；
- 桶定义表挂 action 治理指引文案（脚本 guidance_actions 8 句）；
- 每桶维护证据耗时 top-N 下钻种子（top_traces，直接用于 /trace 批查）。

批次 2（设计文档 §11.1）：/stats/error_codes | /stats/pods | /stats/links |
/stats/heatmap 四个单维度统计——SQL 聚合下推 DB（TraceLightPGManager），
服务层负责响应拼装、heatmap 自动选窗（跨度≤2h→1m、≤48h→10m、否则 1h，
slots 上限 240 超限自动放大）与联动口径 note。
"""

import asyncio
import heapq
import logging
import math
import re
from typing import Any, Optional

from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.trace_light import TraceLightPGManager
from latency.database.utils import parse_timestamp
from latency.schemas.request import (
    ListLogParseResultRequest,
    SortField,
)
from latency.schemas.trace_light import (
    ErrorCodeStatsMsg,
    GetStageStatsMsg,
    GetStageStatsRequest,
    HeatmapStatsMsg,
    HeatmapStatsRequest,
    LinkStatsMsg,
    PodStatsMsg,
    StageStatsItem,
    StageStatsTopTrace,
    StatsDimensionRequest,
)

logger = logging.getLogger(__name__)

# 主导阶段互斥分类桶：(key, 显示名, 口径 note, 治理指引 action)。
# 每条 trace 按最大互斥阶段归入唯一桶；action 文案来自
# yuanrong-scripts/ds_trace_bottleneck.py 的 guidance_actions。
_DOMINANT_BUCKET_SPEC: list[tuple[str, str, str, str]] = [
    ("rpc_network", "RPC网络",
     "Σ 各段 rpc network（sdk/master/remote/client 的 network_residual_us）",
     "Worker 处理相对较快时，优先排查 bRPC 网络、调度、响应通知和 framework residual。"),
    ("rpc_queue", "RPC排队",
     "rpc framework = total − network 残差，含框架排队/调度开销",
     "排查服务端请求队列、执行线程池饱和与 handler 调度；该阶段不等同于网络传输或业务执行。"),
    ("query_meta", "QueryMeta",
     "worker_access_latency_us − urma_processing_us（queryAndGet 查元数据/业务）",
     "排查 Meta Worker 响应、元数据锁竞争、路由刷新与 metadata RPC。"),
    ("urma", "URMA",
     "urma_processing_us（C2W/W2W urma 通信段）",
     "排查 URMA completion、poll/notify 唤醒、线程调度、inflight 和大对象分块写。"),
    ("data_worker", "Data Worker服务端处理",
     "worker 内部活跃 local_worker_internal_active_us + sdk/master processing",
     "远端 server 父窗口较高；结合 URMA 观测边界，排查对象查找、buffer 准备、重试与远端 Worker 调度。"),
    ("cross_window", "Client/Worker交叉窗口未细分",
     "request_mode=unknown，yuanrong 无法定位 client/worker，证据取总时延",
     "数据访问父窗口扣除已知子阶段后仍较高；仅有明确 Local processing / remoteObjects=0 证据时才判为本地处理，否则保留未细分。"),
    ("residual", "未解释残差",
     "total_latency_us − Σ 已解释维度（含 urma 调度/线程等未捕获开销）",
     "Client 总时延未被现有阶段覆盖，优先补齐 direct query/data、框架排队与 deadline 前后的观测。"),
    ("urma_timeout", "URMA超时",
     "anomaly_reason/content 文本匹配 timeout/超时；证据取日志 timeout elapsedMs",
     "已观测到 URMA_WAIT_TIMEOUT；优先检查 completion、send lane、pending WR 和错误上浮链。没有完成态时不把缺失的 URMA_ELAPSED_TOTAL 当作 0。"),
]

# URMA 超时文本识别（明细表无独立 timeout 标记，走 anomaly_reason/content 文本近似）
_TIMEOUT_TEXT_RE = re.compile(r"time?\s*out|timed?\s*out|超时", re.IGNORECASE)
_TIMEOUT_ELAPSED_RE = re.compile(
    r"elapsed[_ ]?ms[\"']?\s*[:=]\s*(\d+(?:\.\d+)?)", re.IGNORECASE
)

# SET（写操作）独立视角互斥分类桶：(key, 显示名, 口径 note, 治理指引 action)。
#
# SET 流程与 GET 不同（写路径走 CREATE/PUBLISH），可用列也不同。node48 实测
# （3638 条 SET 行）：
# - urma_processing_us / create_latency / publish_latency / w2w_urma_latency
#   在当前解析路径恒为 NULL（trace_frame 显式置 None）；
# - c2w_urma_latency = total_ms − worker_total_latency，而 SET 的
#   worker_total_latency 实测近 0 → c2w 恒 ≈ 总时延，无额外信息量；
# - sdk_processing_us + local_worker_internal_us ≡ total_latency_us
#   （3638 行仅 1 行偏离），故残差基本恒 0；
# - master/remote/sdk RPC 细分列在 SET 侧非空 ≈ 0。
# 据此只保留实测可得的归因维度，其余维度在响应 note 中显式列明原因。
_SET_BUCKET_SPEC: list[tuple[str, str, str, str]] = [
    ("set_urma_timeout", "SET·URMA超时",
     "anomaly_reason/content 文本匹配 timeout/超时（近似口径；node48 SET 侧暂 0 命中）",
     "已观测到 URMA_WAIT_TIMEOUT；先查 completion、send lane、pending WR，再核对写路径错误上浮链是否阻塞。"),
    ("set_no_evidence", "SET·数据面未观测",
     "local_worker_internal_us 与 worker_access_latency_us 均空（该 trace 无 Worker 侧行），证据取总时延",
     "客户端段独占且缺数据面证据：按 trace_id 复核 Worker 侧是否真的未打印，区分本地命中与观测缺口，勿直接判为 Worker 端慢。"),
    ("set_residual", "SET·未解释残差",
     "total_latency_us − (sdk_processing_us + local_worker_internal_us) ≥ +0.5ms，证据取残差",
     "写路径未被 SDK 段与 Worker 段覆盖：优先补齐 CREATE/PUBLISH 分段观测（create_latency/publish_latency 当前解析路径不产出）。"),
    ("set_client", "SET·客户端SDK段",
     "有 Worker 侧行且 sdk_processing_us ≥ local_worker_internal_us，证据取 SDK 段耗时",
     "写请求耗时集中在客户端 SDK 段（含等待数据面返回）：先查 SDK 侧排队/重试与端到端 deadline，再看 Worker 侧是否已返回。"),
    ("set_worker", "SET·Worker写处理",
     "有 Worker 侧行且 local_worker_internal_us > sdk_processing_us，证据取 Worker 端写处理耗时",
     "Worker 端 CREATE/PUBLISH 处理主导：排查元数据落盘、buffer 准备、锁竞争与远端 Worker 调度。"),
]

# SET 残差判定阈值（us）：实测唯一偏离为 8153us，0.5ms 可捕获离群而不计入舍入误差
_SET_RESIDUAL_THRESHOLD_US = 500.0

# 每桶下钻种子条数（全量约 8 桶 × 5 条 × ~60B ≈ 2.4KB，体积可控）
_TOP_TRACES_PER_BUCKET = 5


def _component_dim_us(row: Any) -> dict[str, float]:
    """把一条 trace 明细拆成 8 维 us（内部统一 us 累加，最后 clip）。

    单位口径：
    - ``*_us`` 字段（RPC/urma_processing/worker_access/sdk/master 等）原生 us
      （yuanrong 相减推导，仅解析归因子集非空）；
    - urma_link_latency / local_worker_lock 是 ms → *1000。
    """
    def _g(name: str) -> float:
        value = getattr(row, name, None)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    # dim1 RPC 网络（SDK→Master + Master→Worker + RemoteWorker + client 侧, 存在才加）
    d1 = (
        _g("sdk_rpc_network_us")
        + _g("master_rpc_network_us")
        + _g("remote_worker_rpc_network_us")
        + _g("client_master_rpc_network_us")
        + _g("client_remote_rpc_network_us")
    )
    # dim2 RPC 框架（framework = total - network 残差式，互斥）
    d2 = (
        _g("sdk_rpc_framework_us")
        + _g("master_rpc_framework_us")
        + _g("remote_worker_rpc_framework_us")
        + _g("client_master_rpc_framework_us")
        + _g("client_remote_rpc_framework_us")
    )
    # dim3 urma 通信（GET 有效；SET/空为 0）
    d3 = _g("urma_processing_us")
    # dim4 urma 建链（外部因子, ms→us）
    d4 = _g("urma_link_latency") * 1000.0 if row.urma_link_latency is not None else 0.0
    # dim5 queryAndGet 业务 = worker 处理扣 urma（可能负, clip≥0）
    d5 = max(0.0, _g("worker_access_latency_us") - d3)
    # dim6 其他调度/线程：优先 us，空则取 ms 的 lock → us
    active = _g("local_worker_internal_active_us")
    d6 = active if active else _g("local_worker_lock") * 1000.0
    d6 = max(0.0, d6)
    # dim7 其他 SDK+Master 处理
    d7 = _g("sdk_processing_us") + _g("master_processing_us")
    # dim8 未解释残差（含 urma 调度/线程、未捕获开销）
    explained = d1 + d2 + d3 + d4 + d5 + d6 + d7
    d8 = max(0.0, _g("total_latency_us") - explained)
    return {
        "d1_network": d1,
        "d2_framework": d2,
        "d3_urma_comm": d3,
        "d4_urma_link": d4,
        "d5_query_biz": d5,
        "d6_schedule": d6,
        "d7_sdk_master": d7,
        "d8_residual": d8,
    }


def _num(value: Any) -> float:
    """行字段安全转 float（None/文本 → 0.0）。"""
    return float(value) if isinstance(value, (int, float)) else 0.0


def _classify_dominant(row: Any, dims: dict[str, float]) -> tuple[str, float]:
    """把一条 trace 归入唯一互斥桶，返回 (bucket_key, evidence_us)。

    优先级：URMA 超时（文本） > request_mode=unknown 粗分定界 >
    普通瓶颈 winner-take-all。evidence_us 为该桶主阶段耗时：
    普通瓶颈取 winner 维度耗时，超时取日志 timeout elapsedMs，
    粗分 data_worker 取 worker 侧窗口，粗分 cross_window 取总时延。
    """
    total_us = float(getattr(row, "total_latency_us", None) or 0.0)

    # 1. URMA 超时：anomaly_reason/content 文本匹配（明细表无独立 timeout 标记）
    text = " ".join(
        str(x)
        for x in (getattr(row, "anomaly_reason", None), getattr(row, "content", None))
        if x
    )
    if text and _TIMEOUT_TEXT_RE.search(text):
        m = _TIMEOUT_ELAPSED_RE.search(text)
        ev = float(m.group(1)) * 1000.0 if m else total_us
        return "urma_timeout", max(ev, 0.0)

    # 2. request_mode=unknown：RPC 字段无映射原材料（bRPC perf 行未入库时
    #    d1/d2 恒 0），按现有列粗分定界——worker 侧窗口（访问窗口或内部
    #    处理）占 total ≥50% 判 data_worker（数据面慢），否则客户端等待
    #    主导（worker 干净或未触达数据面）落 cross_window，证据取总时延。
    #    RPC 细分归因（QueryMeta/RPC网络/RPC排队）用 skill 脚本
    #    brpc_stage_drill.py 深挖（latency-analysis SKILL 阶段 4.5）。
    if getattr(row, "request_mode", None) == "unknown":
        worker_side_us = max(
            _num(getattr(row, "worker_access_latency_us", None)),
            _num(getattr(row, "local_worker_internal_us", None)),
        )
        if total_us > 0 and worker_side_us >= 0.5 * total_us:
            return "data_worker", worker_side_us
        return "cross_window", total_us

    # 3. 普通瓶颈 winner-take-all（d4 urma_link 为外部因子，不参与投票）
    candidates = {
        "rpc_network": dims["d1_network"],
        "rpc_queue": dims["d2_framework"],
        "urma": dims["d3_urma_comm"],
        "query_meta": dims["d5_query_biz"],
        "data_worker": dims["d6_schedule"] + dims["d7_sdk_master"],
        "residual": dims["d8_residual"],
    }
    key = max(candidates, key=lambda k: candidates[k])
    return key, max(candidates[key], 0.0)


def _set_family_handle(row: Any) -> str:
    """SET 行的原始 handle（DS_KV_CLIENT_SET / DS_POSIX_CREATE / DS_POSIX_PUBLISH）。

    ``log_parse_result.operation`` 存的是原始 handle（非归一 "SET"），故可直接
    用作家族构成统计；缺失时回落 "unknown"。
    """
    return str(getattr(row, "operation", None) or "unknown")


def _classify_dominant_set(row: Any) -> tuple[str, float]:
    """把一条 SET trace 归入唯一互斥桶，返回 (bucket_key, evidence_us)。

    优先级：URMA 超时（文本）> 数据面未观测（Worker 侧列全空）>
    未解释残差（total − 两段之和 ≥ 阈值）> 客户端 SDK 段 / Worker 写处理（比大小）。

    与 GET 的 8 维公式不通用的原因见 ``_SET_BUCKET_SPEC`` 上方注释：
    SET 侧 urma_processing/c2w/RPC 细分列不可用，仅 sdk 段与 Worker 端两段
    可实测（且二者之和 ≡ 总时延）。
    """
    total_us = _num(getattr(row, "total_latency_us", None))

    # 1. URMA 超时：文本匹配优先（近似口径，与 GET 侧同一识别式）
    text = " ".join(
        str(x)
        for x in (getattr(row, "anomaly_reason", None), getattr(row, "content", None))
        if x
    )
    if text and _TIMEOUT_TEXT_RE.search(text):
        m = _TIMEOUT_ELAPSED_RE.search(text)
        ev = float(m.group(1)) * 1000.0 if m else total_us
        return "set_urma_timeout", max(ev, 0.0)

    sdk_us = _num(getattr(row, "sdk_processing_us", None))
    worker_us = _num(getattr(row, "local_worker_internal_us", None))
    has_worker_side = (
        getattr(row, "local_worker_internal_us", None) is not None
        or getattr(row, "worker_access_latency_us", None) is not None
    )

    # 2. Worker 侧无行 → 数据面未观测（证据取总时延）
    if not has_worker_side:
        return "set_no_evidence", max(total_us, 0.0)

    # 3. 未解释残差：总时延显著大于两段之和（证据取残差本身）
    residual_us = total_us - (sdk_us + worker_us)
    if residual_us >= _SET_RESIDUAL_THRESHOLD_US:
        return "set_residual", residual_us

    # 4/5. SDK 段 vs Worker 写处理
    if sdk_us >= worker_us:
        return "set_client", max(sdk_us, 0.0)
    return "set_worker", max(worker_us, 0.0)


def _percentile_ms(sorted_ms: list[float], q: float) -> Optional[float]:
    """nearest-rank 分位（输入需升序），单位 ms。"""
    if not sorted_ms:
        return None
    idx = min(len(sorted_ms) - 1, max(0, math.ceil(q * len(sorted_ms)) - 1))
    return round(sorted_ms[idx], 3)


def _zero_bucket_items(spec: list[tuple[str, str, str, str]] = _DOMINANT_BUCKET_SPEC) -> list[StageStatsItem]:
    return [
        StageStatsItem(key=key, name=name, note=note, action=action)
        for key, name, note, action in spec
    ]


# /stats/heatmap 自动选窗（设计文档 §11.1）：跨度≤2h→1m、≤48h→10m、
# 否则 1h；自动模式下 slots 上限 240，超限逐级放大窗口（指定窗口不放大）。
_WINDOW_SECONDS = {"1m": 60, "10m": 600, "1h": 3600}
_WINDOW_ORDER = ["1m", "10m", "1h"]
_HEATMAP_MAX_SLOTS = 240


def _auto_window(span_seconds: float) -> str:
    """按时间跨度自动选窗：≤2h→1m、≤48h→10m、否则 1h。"""
    if span_seconds <= 2 * 3600:
        return "1m"
    if span_seconds <= 48 * 3600:
        return "10m"
    return "1h"


def _format_span(seconds: float) -> str:
    """跨度秒数的人类可读格式（note 用）。"""
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    if seconds >= 60:
        return f"{seconds / 60:.1f}m"
    return f"{seconds:.0f}s"


class StatsService:
    """主导问题分类 + 单维度统计服务"""

    @staticmethod
    async def get_stage_stats(req: GetStageStatsRequest) -> GetStageStatsMsg:
        """主导问题分类入口：按 operation 分派到 GET / SET 两套独立视角。

        GET（读）与 SET（写）的请求流程与可观测字段不同，两套桶口径完全独立
        （见 ``_DOMINANT_BUCKET_SPEC`` / ``_SET_BUCKET_SPEC``），不做跨
        operation 混合归桶；其他 operation 仍短路返回空 items + note。
        """
        operation = (req.operation or "GET").upper()
        if operation == "GET":
            return await StatsService._get_stage_stats_get(req)
        if operation == "SET":
            return await StatsService._get_stage_stats_set(req)
        return GetStageStatsMsg(
            operation=operation,
            sample_cnt=0,
            truncated=False,
            items=[],
            note="仅支持 GET / SET 主导问题分类（其他操作无归因子集），请将 operation 切换为 GET 或 SET。",
        )

    @staticmethod
    async def _sample_traces(
        req: GetStageStatsRequest,
    ) -> tuple[int, int, list, list, list]:
        """GET/SET 共用采样管道：异常 trace 全量 + top 慢正常，合并去重。

        返回 ``(anom_total, norm_total, anomalous_rows, normal_rows, sampled)``；
        仅保留 ``total_latency_us`` 有值的代表 trace，异常侧优先。
        """
        cap = req.sample_cap
        base = dict(
            kb_id=req.kb_id,
            log_id=req.log_id,
            operation=(req.operation or "GET").upper(),
            start_time=req.start_time,
            end_time=req.end_time,
            sort_fields=[SortField(field="total_latency", order="desc")],
            page_cnt=cap,
            page_num=1,
        )

        async def _fetch(is_anomalous: bool) -> tuple[int, list]:
            sub_req = ListLogParseResultRequest(**base, is_anomalous=is_anomalous)
            return await LogParseResultPGManager.list_log_parse_results(sub_req)

        (anom_total, anomalous_rows), (norm_total, normal_rows) = await asyncio.gather(
            _fetch(True), _fetch(False)
        )

        # 异常优先（主问题 trace），再补 top 慢正常；仅保留有归因 us 的代表 trace
        seen: set[str] = set()
        sampled: list = []
        for row in list(anomalous_rows) + list(normal_rows):
            tid = row.trace_id
            if tid in seen:
                continue
            if row.total_latency_us is None or row.total_latency_us <= 0:
                continue
            seen.add(tid)
            sampled.append(row)
            if len(sampled) >= cap:
                break
        return (
            anom_total, norm_total,
            list(anomalous_rows), list(normal_rows), sampled,
        )

    @staticmethod
    def _is_truncated(
        anom_total: int,
        norm_total: int,
        anomalous_rows: list,
        normal_rows: list,
        sample_cnt: int,
        cap: int,
    ) -> bool:
        """采样截断判定（GET/SET 共用）：上游总数超出返回行数或触达采样上限。"""
        return (
            anom_total > len(anomalous_rows)
            or norm_total > len(normal_rows)
            or sample_cnt >= cap
        )

    @staticmethod
    async def _get_stage_stats_get(req: GetStageStatsRequest) -> GetStageStatsMsg:
        """GET 读路径主导问题分类（8 互斥桶，设计文档 §4.3）。"""
        cap = req.sample_cap
        (anom_total, norm_total, anomalous_rows, normal_rows, sampled) = (
            await StatsService._sample_traces(req)
        )

        if not sampled:
            return GetStageStatsMsg(
                operation="GET",
                sample_cnt=0,
                truncated=False,
                items=_zero_bucket_items(),
                note="明细中无 GET 归因子集（异常+top慢，缺 yuanrong us 字段），主导问题分类无样本",
            )

        buckets: dict[str, dict[str, Any]] = {
            key: {"success": 0, "fail": 0, "ev": [], "client": [], "top": []}
            for key, _, _, _ in _DOMINANT_BUCKET_SPEC
        }
        # 粗分来源统计（request_mode=unknown）：data_worker=worker 窗口
        # ≥50% 总时延；cross_window=客户端等待主导（worker 干净/未触达）
        cw_reached = 0
        cw_unreached = 0
        cw_shares: list[float] = []
        dw_coarse_cnt = 0
        for row in sampled:
            dims = _component_dim_us(row)
            key, ev_us = _classify_dominant(row, dims)
            b = buckets.get(key)
            if b is None:
                continue
            if getattr(row, "is_anomalous", False):
                b["fail"] += 1
            else:
                b["success"] += 1
            client_us = float(getattr(row, "total_latency_us", None) or 0.0)
            client_ms = client_us / 1000.0
            if client_ms > 0:
                b["client"].append(client_ms)
            if ev_us and ev_us > 0:
                ev_ms = ev_us / 1000.0
                b["ev"].append(ev_ms)
                b["top"].append((row.trace_id, ev_ms, client_ms))
            if getattr(row, "request_mode", None) == "unknown":
                if key == "data_worker":
                    dw_coarse_cnt += 1
                elif key == "cross_window":
                    worker_side_us = max(
                        _num(getattr(row, "worker_access_latency_us", None)),
                        _num(getattr(row, "local_worker_internal_us", None)),
                    )
                    if worker_side_us > 0:
                        cw_reached += 1
                        if client_us > 0:
                            cw_shares.append(worker_side_us / client_us)
                    else:
                        cw_unreached += 1

        items: list[StageStatsItem] = []
        for key, name, note, action in _DOMINANT_BUCKET_SPEC:
            b = buckets[key]
            ev = sorted(b["ev"])
            client = sorted(b["client"])
            top = heapq.nlargest(
                _TOP_TRACES_PER_BUCKET, b["top"], key=lambda t: t[1]
            )
            metric_name = (
                "URMA timeout elapsedMs" if key == "urma_timeout" else "主阶段耗时"
            )
            if key == "cross_window":
                cnt = b["success"] + b["fail"]
                if cnt > 0:
                    share_med = None
                    if cw_shares:
                        s = sorted(cw_shares)
                        mid = len(s) // 2
                        share_med = round(
                            (s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2)
                            * 100.0,
                            1,
                        )
                    seg = [
                        "粗分：request_mode=unknown，客户端等待主导"
                        "（worker 侧窗口<50% 总时延）"
                    ]
                    if cw_reached:
                        seg.append(
                            f"{cw_reached}/{cnt} 条 worker 有窗口但干净"
                            + (
                                f"，worker 窗口占比中位数 {share_med}%"
                                if share_med is not None
                                else ""
                            )
                        )
                    if cw_unreached:
                        seg.append(
                            f"{cw_unreached}/{cnt} 条未触达数据面（worker 窗口列空）"
                        )
                    seg.append(
                        "RPC 细分归因（QueryMeta/RPC网络/RPC排队）用 skill 脚本"
                        " brpc_stage_drill.py（latency-analysis 阶段 4.5）"
                    )
                    note = "；".join(seg)
            elif key == "data_worker" and dw_coarse_cnt > 0:
                note = note + (
                    f"；含粗分 {dw_coarse_cnt} 条（request_mode=unknown，"
                    "worker 侧窗口≥50% 总时延，RPC 字段无映射原材料）"
                )
            items.append(
                StageStatsItem(
                    key=key,
                    name=name,
                    trace_cnt=b["success"] + b["fail"],
                    success_cnt=b["success"],
                    fail_cnt=b["fail"],
                    p50_ms=_percentile_ms(ev, 0.5),
                    p90_ms=_percentile_ms(ev, 0.9),
                    max_ms=round(ev[-1], 3) if ev else None,
                    client_p50_ms=_percentile_ms(client, 0.5),
                    client_p90_ms=_percentile_ms(client, 0.9),
                    metric_name=metric_name,
                    action=action,
                    note=note,
                    top_traces=[
                        StageStatsTopTrace(
                            trace_id=tid,
                            evidence_ms=round(ev_ms, 3),
                            client_ms=round(c_ms, 3) if c_ms > 0 else None,
                        )
                        for tid, ev_ms, c_ms in top
                    ],
                )
            )

        truncated = StatsService._is_truncated(
            anom_total, norm_total, anomalous_rows, normal_rows, len(sampled), cap
        )
        notes = [
            "样本集=异常 trace 全量+top慢正常（yuanrong us 覆盖子集），每条 trace 按最大互斥阶段归入唯一桶",
            "URMA 超时为 anomaly_reason/content 文本匹配的近似口径",
            "request_mode=unknown 的 trace 按现有列粗分定界（worker 窗口≥50% 总时延→data_worker，否则 cross_window），RPC 细分归因用 skill 脚本 brpc_stage_drill.py",
        ]
        if truncated:
            notes.insert(0, f"达到采样上限 {cap}，异常/top慢合并去重已截断")
        return GetStageStatsMsg(
            operation="GET",
            sample_cnt=len(sampled),
            truncated=truncated,
            items=items,
            note="；".join(notes),
        )

    @staticmethod
    async def _get_stage_stats_set(req: GetStageStatsRequest) -> GetStageStatsMsg:
        """SET 写路径主导问题分类（5 互斥桶，口径见 ``_SET_BUCKET_SPEC``）。

        与 GET 不共用 8 维公式：SET 侧 urma_processing_us / create_latency /
        publish_latency / w2w_urma_latency 在当前解析路径恒空，c2w_urma_latency
        恒≈总时延，故只保留 sdk 段与 Worker 端两段实测维度（+ 超时文本、
        数据面未观测、未解释残差三个边界桶），其余维度在响应 note 中列明原因。
        """
        cap = req.sample_cap
        (anom_total, norm_total, anomalous_rows, normal_rows, sampled) = (
            await StatsService._sample_traces(req)
        )

        if not sampled:
            return GetStageStatsMsg(
                operation="SET",
                sample_cnt=0,
                truncated=False,
                items=_zero_bucket_items(_SET_BUCKET_SPEC),
                note="明细中无 SET 归因子集（异常+top慢，缺 total_latency_us 字段），主导问题分类无样本",
            )

        buckets: dict[str, dict[str, Any]] = {
            key: {"success": 0, "fail": 0, "ev": [], "client": [], "top": [], "fam": {}}
            for key, _, _, _ in _SET_BUCKET_SPEC
        }
        for row in sampled:
            key, ev_us = _classify_dominant_set(row)
            b = buckets.get(key)
            if b is None:
                continue
            if getattr(row, "is_anomalous", False):
                b["fail"] += 1
            else:
                b["success"] += 1
            client_ms = _num(getattr(row, "total_latency_us", None)) / 1000.0
            if client_ms > 0:
                b["client"].append(client_ms)
            if ev_us and ev_us > 0:
                ev_ms = ev_us / 1000.0
                b["ev"].append(ev_ms)
                b["top"].append((row.trace_id, ev_ms, client_ms))
            handle = _set_family_handle(row)
            b["fam"][handle] = b["fam"].get(handle, 0) + 1

        metric_names = {
            "set_urma_timeout": "URMA timeout elapsedMs",
            "set_no_evidence": "Client 总时延（数据面未观测）",
        }
        items: list[StageStatsItem] = []
        for key, name, note, action in _SET_BUCKET_SPEC:
            b = buckets[key]
            ev = sorted(b["ev"])
            client = sorted(b["client"])
            top = heapq.nlargest(
                _TOP_TRACES_PER_BUCKET, b["top"], key=lambda t: t[1]
            )
            if b["fam"]:
                fam = "、".join(
                    f"{h} {c}"
                    for h, c in sorted(b["fam"].items(), key=lambda kv: (-kv[1], kv[0]))
                )
                note = note + f"；家族构成：{fam}"
            items.append(
                StageStatsItem(
                    key=key,
                    name=name,
                    trace_cnt=b["success"] + b["fail"],
                    success_cnt=b["success"],
                    fail_cnt=b["fail"],
                    p50_ms=_percentile_ms(ev, 0.5),
                    p90_ms=_percentile_ms(ev, 0.9),
                    max_ms=round(ev[-1], 3) if ev else None,
                    client_p50_ms=_percentile_ms(client, 0.5),
                    client_p90_ms=_percentile_ms(client, 0.9),
                    metric_name=metric_names.get(key, "主阶段耗时"),
                    action=action,
                    note=note,
                    top_traces=[
                        StageStatsTopTrace(
                            trace_id=tid,
                            evidence_ms=round(ev_ms, 3),
                            client_ms=round(c_ms, 3) if c_ms > 0 else None,
                        )
                        for tid, ev_ms, c_ms in top
                    ],
                )
            )

        truncated = StatsService._is_truncated(
            anom_total, norm_total, anomalous_rows, normal_rows, len(sampled), cap
        )
        notes = [
            "样本集=异常 trace 全量+top慢正常（含 total_latency_us 的代表 trace），每条 trace 按写路径实测列归入唯一桶",
            "SET 流程与 GET 不同（写路径走 CREATE/PUBLISH），两套桶口径独立、不混合归桶；本视角仅用 SDK 段与 Worker 端两段实测列",
            "SET 侧剔除维度（node48 实测）：urma_processing_us / create_latency / publish_latency / w2w_urma_latency 恒 NULL；c2w_urma_latency = 总时延 − worker_total_latency 恒 ≈ 总时延，无额外信息量；sdk_processing_us + local_worker_internal_us ≡ total_latency_us，故 set_residual 桶实测恒 0（仅防御性保留）",
            "URMA 超时为 anomaly_reason/content 文本匹配的近似口径",
        ]
        if truncated:
            notes.insert(0, f"达到采样上限 {cap}，异常/top慢合并去重已截断")
        return GetStageStatsMsg(
            operation="SET",
            sample_cnt=len(sampled),
            truncated=truncated,
            items=items,
            note="；".join(notes),
        )

    # ------------------------------------------------------------------
    # /stats/* 单维度统计（批次 2，设计文档 §11.1）
    # ------------------------------------------------------------------

    @staticmethod
    async def get_error_code_stats(
        req: StatsDimensionRequest,
    ) -> ErrorCodeStatsMsg:
        """Top 故障码：trace 级 Counter（trace_cnt 降序）+ 日志级事件数。"""
        total, items = await TraceLightPGManager.list_error_code_stats(req)
        notes = ["Top 故障码可直接作为 /trace/list 的 status_codes 过滤取值"]
        if items and all(i.event_cnt is None for i in items):
            notes.append("log_failure_event 侧无日志级事件数据，event_cnt 为 null")
        elif any(i.event_cnt is not None for i in items):
            notes.append("event_cnt 为 log_failure_event 侧日志级事件数")
        return ErrorCodeStatsMsg(total=total, items=items, note="；".join(notes))

    @staticmethod
    async def get_pod_stats(req: StatsDimensionRequest) -> PodStatsMsg:
        """Top Pod：时延侧 pod 聚合 + 故障侧 join（fault_trace_cnt 降序）。"""
        total, items = await TraceLightPGManager.list_pod_stats(req)
        note = (
            "多 Pod trace 在各 Pod 均计数一次；fault_trace_cnt 为该 Pod 的 trace "
            "在故障侧（trace_failure_event，kb/log 范围）有记录的数量；"
            "Top Pod 可直接作为 /trace/list 的 pod_ip 过滤取值"
        )
        return PodStatsMsg(total=total, items=items, note=note)

    @staticmethod
    async def get_link_stats(req: StatsDimensionRequest) -> LinkStatsMsg:
        """Top 源目对：时延侧 src/dst 聚合 + 故障侧 join。"""
        total, items = await TraceLightPGManager.list_link_stats(req)
        note = (
            "仅统计 src_ip 与 dst_ip 均非空的链路；fault_trace_cnt 口径同 "
            "/stats/pods；Top 源目对可直接作为 /trace/list 的 src_ip/dst_ip "
            "过滤取值"
        )
        return LinkStatsMsg(total=total, items=items, note=note)

    @staticmethod
    async def get_heatmap_stats(req: HeatmapStatsRequest) -> HeatmapStatsMsg:
        """时间热点：自动选窗 + slots 上限 240（超限自动放大窗口）。

        跨度 = 请求时间窗（缺省侧用故障侧数据 min/max 补齐）；
        指定 window_size 时不放大（尊重显式选择），超限仅 note 提示。
        """
        data_min, data_max = await TraceLightPGManager.list_fault_time_range(req)
        start = parse_timestamp(req.start_time) or data_min
        end = parse_timestamp(req.end_time) or data_max

        if start is None or end is None:
            return HeatmapStatsMsg(
                total=0,
                window_size=req.window_size or "10m",
                items=[],
                note="时间窗内无故障 trace 数据（trace_failure_event 侧无记录）",
            )
        if end < start:
            return HeatmapStatsMsg(
                total=0,
                window_size=req.window_size or "10m",
                items=[],
                note="时间窗无效：start_time 晚于 end_time",
            )

        span = (end - start).total_seconds()
        auto = req.window_size is None
        window = req.window_size or _auto_window(span)
        if auto:
            while (
                window != "1h"
                and math.ceil(span / _WINDOW_SECONDS[window]) > _HEATMAP_MAX_SLOTS
            ):
                window = _WINDOW_ORDER[_WINDOW_ORDER.index(window) + 1]

        items = await TraceLightPGManager.list_heatmap_buckets(
            req, _WINDOW_SECONDS[window]
        )

        notes = []
        if auto:
            notes.append(
                f"窗口 {window}（自动：跨度≤2h→1m、≤48h→10m、否则 1h；"
                f"实际跨度 {_format_span(span)}）"
            )
        else:
            notes.append(f"窗口 {window}（指定）")
        slots_est = max(1, math.ceil(span / _WINDOW_SECONDS[window]))
        if slots_est > _HEATMAP_MAX_SLOTS:
            notes.append(
                f"估算 slots {slots_est} 超过 {_HEATMAP_MAX_SLOTS} 上限"
                "（窗口已到最大 1h）"
            )
        notes.append("仅返回有数据的时间槽；跨槽 trace 在每个有事件的槽各计一次")
        return HeatmapStatsMsg(
            total=len(items),
            window_size=window,
            items=items,
            note="；".join(notes),
        )
