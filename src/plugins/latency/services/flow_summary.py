# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Read/write flow summary aggregation service.

Aggregates per-trace latency stages (role-interaction segments) into the
read-flow / write-flow graph used by the frontend:

- GET (read flow):  client→entry, entry→meta, entry→data, data→entry(URMA write)
- SET (write flow): client→entry(createbuffer), client→entry(publish), entry→meta(publish)

Every edge carries a latency rollup (trace_count/p50/p99/max + top pods) plus a
status derived from fixed thresholds (10ms warn / 50ms critical), independent of
the diagnosis-config threshold.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Optional

from sqlalchemy import func, select

from latency.database.engine import PGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.pod_role import PodRolePGManager
from latency.database.models import LogParseResult, TraceFailureEvent
from latency.database.utils import format_ip
from latency.schemas.flow_summary import (
    FlowEdgeModel,
    FlowEdgeRollupModel,
    FlowEdgeTraceItemModel,
    FlowGraphModel,
    FlowNodeModel,
    FlowSummaryModel,
    ListFlowSummaryRequest,
    TraceFlowStageModel,
)
from latency.schemas.log import YUANRONG_METRIC_FIELDS


logger = logging.getLogger(__name__)

# 固定阈值（ms）：max>=CRITICAL 红粗、>=WARN 橙、有数据蓝、无数据灰虚线
WARN_MS = 10.0
CRITICAL_MS = 50.0

# 时延分解对齐字段：32 项 YUANRONG 指标（request_mode 为字符串不做聚合）。
# _load_trace_rows 按此清单读取，_decompose_trace 从中取互斥分解的原始观测值。
_YUANRONG_SELECT_FIELDS: tuple[str, ...] = tuple(
    name for name in YUANRONG_METRIC_FIELDS if name != "request_mode"
)
# 旧口径补充字段（仅操作类型推断兜底仍需）。
_LEGACY_SELECT_FIELDS: tuple[str, ...] = (
    "create_latency",
    "publish_latency",
)
_ALL_SELECT_FIELDS: tuple[str, ...] = (*_YUANRONG_SELECT_FIELDS, *_LEGACY_SELECT_FIELDS)

# stage_key -> (source, target, operation, decomp_keys, reason, report_reading)
# "点归点线归线"：边只保留真正的跨角色交互窗口（RPC/传输）；
# client/worker 自身处理不再作为边，改由正交分解标注在对应节点上。
# 边值取自 9 段互斥分解的对应段（decomp_keys 多字段求和），与瀑布图口径完全一致。
READ_STAGES: list[dict[str, Any]] = [
    {
        "stage": "client_to_entry",
        "source": "client",
        "target": "entry",
        "operation": "Client UB 通信",
        "decomp_keys": ["client_urma_processing_us"],
        "reason": "Client 侧 UB 通信窗口（与 9 段分解的 Client UB 通信段一致）。",
        "report_reading": "客户端侧 UB 传输/接收窗口；QueryGet 分支下是 client→meta 的 UB 交互。",
    },
    {
        "stage": "entry_to_meta",
        "source": "entry",
        "target": "meta",
        "operation": "QueryGet RPC 网络/框架",
        "decomp_keys": ["query_get_network_us", "query_get_framework_us"],
        "reason": "元数据 RPC 交互段：QueryGet 分支的 client→meta 网络+框架时延（与 9 段分解一致）。",
        "report_reading": "只有 QueryGet RPC 网络/框架有值时才归因到元数据路径。",
    },
    {
        "stage": "entry_to_data",
        "source": "entry",
        "target": "data",
        "operation": "Entry→Data 远端供数",
        "decomp_keys": ["entry_to_data_remote_us"],
        "reason": "从 9 段分解的 Worker/Meta 内部(扣除UB)中切出远端供数段（entry_to_data_remote_us = min(remote_worker_internal_us, worker_residual)），仅远端供数窗口可观测时点亮。",
        "report_reading": "远端 Data Worker 供数处理窗口；与 9 段分解的 Entry→Data 远端供数段一致，恒从 Worker/Meta 内部预算中扣除，保证闭合。",
    },
    {
        "stage": "data_to_entry_ub",
        "source": "data",
        "target": "entry",
        "operation": "Worker UB 通信(URMA 回传)",
        "decomp_keys": ["urma_processing_us"],
        "reason": "DataWorker 通过 URMA Write 反向写回 EntryWorker（与 9 段分解的 Worker UB 通信段一致）。",
        "report_reading": "读取路径的数据回传阶段，方向是 DataWorker -> EntryWorker。",
    },
]

WRITE_STAGES: list[dict[str, Any]] = [
    {
        "stage": "client_to_entry",
        "source": "client",
        "target": "entry",
        "operation": "Client UB 通信",
        "decomp_keys": ["client_urma_processing_us"],
        "reason": "Client 侧 UB 通信窗口（与 9 段分解的 Client UB 通信段一致）。",
        "report_reading": "SET 写入主路径的客户端侧 UB 传输/接收窗口。",
    },
    {
        "stage": "entry_to_meta_publish",
        "source": "entry",
        "target": "meta",
        "operation": "Entry→Meta Publish",
        "decomp_keys": [],
        "reason": "9 段互斥分解无独立 Entry→Meta Publish 段（写入时延已并入 Worker/Meta 内部处理与 SDK 处理），该边恒无数据。",
        "report_reading": "SET 写入的 meta 侧发布处理已并入 9 段分解的 Worker/Meta 内部，无独立交互窗口。",
    },
]

_STAGE_BY_OPERATION: dict[str, list[dict[str, Any]]] = {
    "GET": READ_STAGES,
    "SET": WRITE_STAGES,
}

# ── 正交分解段定义 ─────────────────────────────────────────────────────
# 原则：以 total_latency_us 为预算池，按因果顺序逐段扣除 min(remaining, observed)，
# 保证任意两段互斥（每 1ms 只归入一段），Σ(段) + 残差 = 总时延。
# GET 与 kvcache 基准 _build_exclusive_segments / 前端 buildExclusiveSegments 完全一致：
# QueryGet 分支 = SDK处理(剩余残差) + QueryGet网络/框架 + Worker内部(server_exec−UB)
#   + Worker UB + Client UB（仅分配剩余预算），无独立"其他"段；
# 普通分支 = SDK处理 + Worker/Meta内部(outer−UB) + Worker UB + Client UB + "其他"残差；
#   Worker/Meta 内部中再切出远端供数段（remote_worker_internal = remote_worker_processing−UB），
#   作为 Entry→Data 远端供数交互段；sdk/worker 内部/远端供数均按剩余预算 min 扣除，
#   保证 Σ(段) ≤ total（修复 sdk 与 worker 窗口重叠导致 Σ段 > 总时延的问题）。
# 每段: key -> (展示名, 归属节点, 原始观测提取字段)
_GET_DECOMP_SEGMENTS: list[tuple[str, str, str, str]] = [
    ("sdk_processing_us", "SDK 处理", "client", "sdk_processing_us"),
    ("query_get_network_us", "QueryGet 网络", "", "query_get_network"),
    ("query_get_framework_us", "QueryGet 框架", "", "query_get_framework"),
    ("query_get_worker_internal_us", "QueryGet Worker 内部", "meta", "query_get_worker_internal"),
    ("urma_processing_us", "Worker UB 通信", "", "urma_processing_us"),
    ("client_urma_processing_us", "Client UB 通信", "", "client_urma_processing_us"),
    ("entry_to_data_remote_us", "Entry→Data 远端供数", "", "remote_worker_internal"),
    ("worker_residual_us", "Worker/Meta 内部(扣除UB)", "entry", "worker_residual"),
]
# SET 与 GET 普通分支完全一致：SDK 处理 + Worker/Meta 内部(outer−UB) + Worker UB + Client UB + 残差。
# 实际 SET 数据中 query_get_*/urma/client_urma 通常为空，分解退化为 sdk + worker_residual + 残差。
_SET_DECOMP_SEGMENTS: list[tuple[str, str, str, str]] = [
    ("sdk_processing_us", "SDK 处理", "client", "sdk_processing_us"),
    ("worker_residual_us", "Worker/Meta 内部(扣除UB)", "entry", "worker_residual"),
    ("urma_processing_us", "Worker UB 通信", "", "urma_processing_us"),
    ("client_urma_processing_us", "Client UB 通信", "", "client_urma_processing_us"),
]
_DECOMP_OPERATION: dict[str, list[tuple[str, str, str, str]]] = {
    "GET": _GET_DECOMP_SEGMENTS,
    "SET": _SET_DECOMP_SEGMENTS,
}
# 残差段的 key 与展示名（对齐瀑布图的"其他"残差）
RESIDUAL_KEY = "residual"
RESIDUAL_NAME = "其他"

# 作为"边"的正交分解段 key（跨角色交互）：节点自身处理统计必须排除它们
_EDGE_DECOMP_KEYS: frozenset[str] = frozenset(
    key for stage in (*READ_STAGES, *WRITE_STAGES) for key in stage.get("decomp_keys") or ()
)


def _decompose_trace(info: dict[str, Any], operation: str) -> dict[str, float]:
    """逐 trace 正交分解：以 total_latency_us 为预算池瀑布扣除，返回互斥段分配值。

    段值 = min(remaining, observed)（残差 = max(0, remaining)），恒有
    Σ(段) + 残差 = total_latency。GET/SET 与 9 段互斥分解口径完全一致：
    - QueryGet 分支：SDK处理 = 剩余残差（闭合）、QueryGet网络/框架、Worker内部
      = server_exec−UB、Worker UB、Client UB（仅分配剩余预算），无独立"其他"段；
    - 普通分支（含 SET）：SDK处理、Worker/Meta内部 = outer−UB（outer 优先
      worker_access，否则 remote_worker_processing）、Worker UB、Client UB、
      Entry→Data远端供数 = min(remote_worker_internal, Worker/Meta内部) 切出，
      "其他" = 剩余残差。sdk/worker 内部/远端供数按剩余预算 min 扣除，Σ(段) ≤ total。
    """
    total = info.get("total_ms")
    if not isinstance(total, (int, float)) or not (total > 0):
        return {}

    fields = info["fields"]

    def ms(name: str) -> float:
        value = fields.get(name)
        return float(value) if isinstance(value, (int, float)) and value > 0 else 0.0

    query_net = ms("query_get_local_rpc_network_us") + ms("query_get_remote_rpc_network_us")
    query_fw = ms("query_get_local_rpc_framework_us") + ms("query_get_remote_rpc_framework_us")
    server_exec = ms("query_get_server_exec_us")
    urma = ms("urma_processing_us")
    raw_client_urma = ms("client_urma_processing_us")
    out: dict[str, float] = {}
    if query_net > 0 or query_fw > 0:
        # QueryGet 分支（对齐基准 _build_exclusive_segments）：client_urma 已含在
        # worker 等待窗口内，只分配剩余预算，避免 Σ段 超过总时延；SDK 处理吸收
        # 剩余残差，恒有 Σ段 = 总时延，无独立"其他"段。
        worker_internal = max(server_exec - urma, 0.0)
        core_used = query_net + query_fw + worker_internal + urma
        remaining = max(total - core_used, 0.0)
        client_urma = min(raw_client_urma, remaining)
        sdk = max(remaining - client_urma, 0.0)
        if sdk > 0:
            out["sdk_processing_us"] = sdk
        if query_net > 0:
            out["query_get_network_us"] = query_net
        if query_fw > 0:
            out["query_get_framework_us"] = query_fw
        if worker_internal > 0:
            out["query_get_worker_internal_us"] = worker_internal
        if urma > 0:
            out["urma_processing_us"] = urma
        if client_urma > 0:
            out["client_urma_processing_us"] = client_urma
        out[RESIDUAL_KEY] = 0.0
        return out

    # 普通分支（对齐基准，SET 与此完全一致）：outer = worker_access 优先，
    # 否则 remote_worker_processing；worker/meta 内部 = outer − UB；
    # 从 worker 内部切出远端供数段（remote_worker_internal = remote_worker_processing − UB），
    # 作为 Entry→Data 远端供数；sdk / worker 内部 / 远端供数均按 min(remaining, observed)
    # 扣预算，保证 Σ(段) ≤ total（修复 sdk 与 worker 窗口重叠导致 Σ段 > 总时延的问题）；
    # client_urma 仅分配剩余预算；"其他"闭合总时延。
    sdk_obs = ms("sdk_processing_us")
    outer = ms("worker_access_latency_us") or ms("remote_worker_processing_us")
    urma = ms("urma_processing_us")
    raw_remote = ms("remote_worker_internal_us")
    sdk = min(sdk_obs, total)
    urma = min(urma, max(total - sdk, 0.0))
    worker_residual = min(max(outer - urma, 0.0), max(total - sdk - urma, 0.0))
    remote_data = min(raw_remote, worker_residual)
    worker_residual -= remote_data
    core_used = sdk + urma + worker_residual + remote_data
    remaining = max(total - core_used, 0.0)
    client_urma = min(raw_client_urma, remaining)
    if sdk > 0:
        out["sdk_processing_us"] = sdk
    if worker_residual > 0:
        out["worker_residual_us"] = worker_residual
    if remote_data > 0:
        out["entry_to_data_remote_us"] = remote_data
    if urma > 0:
        out["urma_processing_us"] = urma
    if client_urma > 0:
        out["client_urma_processing_us"] = client_urma
    out[RESIDUAL_KEY] = max(remaining - client_urma, 0.0)
    return out


# 各角色在 pod_role 表中的取值
_ROLE_POD_FIELDS: dict[str, str] = {
    "client": "client_pod",
    "entry": "entry_worker_pods",
    "meta": "meta_worker_pods",
    "data": "data_worker_pods",
}


def _percentiles(values: list[float]) -> dict[str, Optional[float]]:
    if not values:
        return {"avg": None, "p50": None, "p99": None, "max": None}
    ordered = sorted(values)
    n = len(ordered)

    def pct(p: float) -> float:
        idx = min(int(p / 100.0 * n), n - 1)
        return ordered[idx]

    return {
        "avg": sum(values) / n,
        "p50": pct(50),
        "p99": pct(99),
        "max": ordered[-1],
    }


# 各角色在 pod_role 表中每角色只取一个代表容器（列表取首个），用于 trace 明细与节点标注
def _roles_of(role: Any) -> dict[str, str]:
    """从 pod_role 记录提取 {role: 容器}；无记录返回空字典。"""
    if role is None:
        return {}
    result: dict[str, str] = {}
    for role_name, field_name in _ROLE_POD_FIELDS.items():
        value = getattr(role, field_name)
        if isinstance(value, list):
            value = next((pod for pod in value if pod), None)
        if value:
            result[role_name] = str(value)
    return result


class FlowSummaryService:
    """Aggregates read/write flow graphs for latency or connectivity traces."""

    @staticmethod
    async def summarize(req: ListFlowSummaryRequest) -> FlowSummaryModel:
        log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)

        trace_rows = await FlowSummaryService._load_trace_rows(req, log_ids)
        if not trace_rows:
            # 该批次 Trace 均无解析行（通断故障常见）：仍下发默认节点布局，
            # 并按请求 trace_ids 补充 pod_role 容器角色，保证单 Trace 图有角色可渲染。
            return await FlowSummaryService._empty_model_with_roles(req, log_ids)

        trace_ids = sorted(trace_rows.keys())
        roles = await PodRolePGManager.list_pod_roles_by_trace_ids(trace_ids)

        role_by_trace: dict[str, Any] = {}
        for role in roles:
            if role.trace_id:
                role_by_trace[role.trace_id] = role

        # 统一推断每个 trace 的操作类型（GET/SET），供各 flow 过滤与单 trace 展示使用。
        for info in trace_rows.values():
            info["resolved_operation"] = FlowSummaryService._operation_of(req, info)
            # 正交分解（互斥分配值）：边/节点/残差统一从这里取值，保证可加总
            info["decomp"] = _decompose_trace(info, info["resolved_operation"])

        per_trace = FlowSummaryService._build_per_trace(trace_rows, role_by_trace)
        nodes = FlowSummaryService._build_nodes(trace_rows, role_by_trace)
        read = FlowSummaryService._build_flow(READ_STAGES, trace_rows, role_by_trace, "GET")
        write = FlowSummaryService._build_flow(WRITE_STAGES, trace_rows, role_by_trace, "SET")
        decomposition = FlowSummaryService._build_decomposition(trace_rows, role_by_trace)

        return FlowSummaryModel(
            nodes=nodes,
            read=read,
            write=write,
            per_trace=per_trace,
            decomposition=decomposition,
        )

    @staticmethod
    def _empty_model() -> FlowSummaryModel:
        default_nodes = [
            FlowNodeModel(id="client", label="Client", role="client"),
            FlowNodeModel(id="entry", label="Entry Worker", role="entry_worker"),
            FlowNodeModel(id="meta", label="Meta Worker", role="meta_worker"),
            FlowNodeModel(id="data", label="Data Worker", role="data_worker"),
        ]
        return FlowSummaryModel(
            nodes=default_nodes,
            read=FlowGraphModel(nodes=default_nodes, warn_ms=WARN_MS, critical_ms=CRITICAL_MS),
            write=FlowGraphModel(nodes=default_nodes, warn_ms=WARN_MS, critical_ms=CRITICAL_MS),
        )

    @staticmethod
    async def _empty_model_with_roles(
        req: ListFlowSummaryRequest, log_ids: list[str]
    ) -> FlowSummaryModel:
        """无解析行 Trace 的空汇总：保留默认节点布局，并按请求 trace_ids 补充角色信息。

        通断故障多数 Trace 在 log_parse_result 无对应行，仅存在 trace_failure_event /
        pod_role 记录。此方法保证单 Trace 角色交互时延流仍能渲染出完整角色布局，
        Client/Worker 容器名从 pod_role 聚合表中取；时延段信息（stages/total_ms）
        留空，由前端显示"无数据"。
        """
        model = FlowSummaryService._empty_model()
        if not req.trace_ids:
            return model

        roles = await PodRolePGManager.list_pod_roles_by_trace_ids(req.trace_ids, log_ids)
        role_by_trace: dict[str, Any] = {}
        for role in roles:
            if role.trace_id:
                role_by_trace[role.trace_id] = role

        per_trace: list[TraceFlowStageModel] = []
        for trace_id in req.trace_ids:
            role = role_by_trace.get(trace_id)
            operation = (role.operation or "").upper()
            # 兜底：pod_role 无记录时按请求 operation 推断，仍缺省 GET
            if not operation and req.operation:
                operation = req.operation.upper()
            if not operation:
                operation = "GET"
            per_trace.append(
                TraceFlowStageModel(
                    trace_id=trace_id,
                    operation=operation,
                    total_ms=None,
                    stages={},
                    roles=_roles_of(role),
                )
            )

        return FlowSummaryModel(
            nodes=model.nodes,
            read=model.read,
            write=model.write,
            per_trace=per_trace,
        )

    @staticmethod
    async def _load_trace_rows(
        req: ListFlowSummaryRequest, log_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """One row per trace: operation + latency fields + ips.

        Returns {trace_id: {"operation": str, "total_ms": float|None, "fields": {...},
                            "raw": {...}}}.
        fields 为毫秒口径（*_us 列 ÷1000），供正交分解/边聚合使用；raw 保留 YUANRONG
        原始微秒值，供前端单 trace 时延明细表（32 项关键时延指标）直接透传对齐。
        """
        if not log_ids:
            return {}

        select_cols: list[Any] = [
            LogParseResult.trace_id,
            LogParseResult.operation,
            func.max(LogParseResult.total_latency).label("total_latency_ms"),
            func.max(LogParseResult.src_ip).label("src_ip"),
            func.max(LogParseResult.dst_ip).label("dst_ip"),
        ]
        for name in _ALL_SELECT_FIELDS:
            select_cols.append(func.max(getattr(LogParseResult, name)).label(name))
        stmt = select(*select_cols)
        stmt = stmt.where(LogParseResult.log_id.in_(log_ids))
        stmt = stmt.where(LogParseResult.trace_id.is_not(None))
        stmt = stmt.group_by(LogParseResult.trace_id, LogParseResult.operation)

        if req.trace_ids:
            stmt = stmt.where(LogParseResult.trace_id.in_(req.trace_ids))
        elif req.source == "latency":
            # 时延页汇总图只统计时延故障 trace（is_anomalous=true）；单 trace 请求不强制过滤
            stmt = stmt.where(LogParseResult.is_anomalous.is_(True))
        if req.start_time:
            from latency.database.utils import parse_timestamp

            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            from latency.database.utils import parse_timestamp

            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(req.end_time))

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            trace_id = row.trace_id
            if not trace_id:
                continue
            fields: dict[str, Optional[float]] = {}
            raw: dict[str, Optional[float]] = {}
            for name in _ALL_SELECT_FIELDS:
                value = getattr(row, name)
                if isinstance(value, (int, float)):
                    fvalue = float(value)
                    # *_us 列为微秒，统一转毫秒后再参与分解；urma_inflight_max 为 count 保留原值
                    fields[name] = fvalue / 1000.0 if name.endswith("_us") else fvalue
                    if name in _YUANRONG_SELECT_FIELDS:
                        # 透传原始微秒值（对齐 32 项 YUANRONG 指标落库契约）
                        raw[name] = fvalue
                else:
                    fields[name] = None
                    if name in _YUANRONG_SELECT_FIELDS:
                        raw[name] = None
            total_us = fields.get("total_latency_us")
            total_ms = (
                total_us
                if isinstance(total_us, (int, float)) and total_us > 0
                else row.total_latency_ms
            )
            result[trace_id] = {
                "operation": (row.operation or "").upper(),
                "total_ms": float(total_ms) if isinstance(total_ms, (int, float)) else None,
                "fields": fields,
                "raw": raw,
                "ips": FlowSummaryService._collect_ips(row),
            }

        # source=fault 时只保留通断故障 trace（trace_failure_event 中存在）。
        if req.source == "fault":
            fault_trace_ids = await FlowSummaryService._fault_trace_ids(req, log_ids)
            if req.trace_ids:
                fault_trace_ids = set(req.trace_ids) & fault_trace_ids
            result = {tid: info for tid, info in result.items() if tid in fault_trace_ids}

        return result

    @staticmethod
    def _collect_ips(row: Any) -> list[str]:
        ips: list[str] = []
        for col in ("src_ip", "dst_ip"):
            value = getattr(row, col, None)
            text = format_ip(value) if value is not None else ""
            if text:
                ips.append(text)
        return ips

    @staticmethod
    async def _fault_trace_ids(
        req: ListFlowSummaryRequest, log_ids: list[str]
    ) -> set[str]:
        stmt = (
            select(TraceFailureEvent.trace_id)
            .where(TraceFailureEvent.log_id.in_(log_ids))
            .where(
                TraceFailureEvent.failure_mode.is_not(None),
                TraceFailureEvent.failure_mode != "",
            )
        )
        if req.trace_ids:
            stmt = stmt.where(TraceFailureEvent.trace_id.in_(req.trace_ids))
        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return {tid for tid in rows if tid}

    @staticmethod
    def _resolve_stage_value(info: dict[str, Any], stage: dict[str, Any]) -> Optional[float]:
        """从正交分解取该边的互斥分配值（decomp_keys 多段求和），保证 Σ(边)+Σ(点处理)+残差=总时延。

        include_zero 的边保留 0.0 计入统计（全部 key 均观测到 0.0 时）；
        其余边仅计入正值（字段缺失/不可观测 → 不命中）。
        """
        decomp = info.get("decomp") or {}
        keys = stage.get("decomp_keys") or ()
        if not keys:
            return None
        total = 0.0
        hit = False
        for key in keys:
            value = decomp.get(key)
            if isinstance(value, (int, float)) and value > 0:
                total += float(value)
                hit = True
        if not hit:
            if stage.get("include_zero") and all(
                isinstance(decomp.get(key), (int, float)) for key in keys
            ):
                return 0.0
            return None
        return total

    @staticmethod
    def _operation_of(req: ListFlowSummaryRequest, info: dict[str, Any]) -> str:
        if req.operation:
            return req.operation.upper()
        op = (info.get("operation") or "").upper()
        # 写入类操作（SET/CREATE/PUBLISH）优先，避免误判为 GET
        if "SET" in op or "CREATE" in op or "PUBLISH" in op:
            return "SET"
        if "GET" in op:
            return "GET"
        # 兜底：依据字段推断（写入段有值 -> SET，否则 GET）
        if info["fields"].get("create_latency") or info["fields"].get("publish_latency"):
            return "SET"
        return "GET"

    @staticmethod
    def _build_per_trace(
        trace_rows: dict[str, dict[str, Any]],
        role_by_trace: dict[str, Any],
    ) -> list[TraceFlowStageModel]:
        per_trace: list[TraceFlowStageModel] = []
        for trace_id, info in trace_rows.items():
            stages: dict[str, float] = {}
            operation = info.get("resolved_operation") or ""
            stage_defs = _STAGE_BY_OPERATION.get(operation, READ_STAGES)
            for stage in stage_defs:
                value = FlowSummaryService._resolve_stage_value(info, stage)
                if value is not None:
                    stages[stage["stage"]] = value
            # 正交分解全量段（互斥分配值）一并下发，供单 trace 图标注节点自身处理与残差
            decomp = info.get("decomp") or {}
            for key, value in decomp.items():
                stages[key] = value
            per_trace.append(
                TraceFlowStageModel(
                    trace_id=trace_id,
                    operation=operation,
                    total_ms=info.get("total_ms"),
                    stages=stages,
                    roles=_roles_of(role_by_trace.get(trace_id)),
                    raw=info.get("raw") or {},
                )
            )
        return per_trace

    @staticmethod
    def _node_own_rollup(
        operation: str, trace_rows: dict[str, dict[str, Any]]
    ) -> tuple[dict[str, FlowEdgeRollupModel], dict[str, int]]:
        """节点自身处理统计：逐 trace 累加该节点"点归点"段（排除交互边/残差）。

        avg 为**全量 Trace 口径**（含 0，Σ节点avg + Σ边avg + 残差avg = 总时延avg，可对账）；
        无任何正值观测的节点 avg 置 None（前端回退仅显示节点名），避免"自身处理=0"误导。
        返回 (rollups, observed)：observed[node] = 观测到正值的 trace 数，供 tooltip 说明实际处理水平。
        """
        decomp_defs = _DECOMP_OPERATION.get(operation, _GET_DECOMP_SEGMENTS)
        per_node: dict[str, list[float]] = {node: [] for _k, _n, node, _o in decomp_defs}
        observed: dict[str, int] = {node: 0 for node in per_node}
        for info in trace_rows.values():
            if info.get("resolved_operation") != operation:
                continue
            decomp = info.get("decomp") or {}
            sums: dict[str, float] = {}
            for key, _name, node, _obs in decomp_defs:
                if key in _EDGE_DECOMP_KEYS:
                    continue
                sums[node] = sums.get(node, 0.0) + decomp.get(key, 0.0)
            for node, value in sums.items():
                per_node[node].append(value)
                if value > 0:
                    observed[node] += 1

        def rollup(values: list[float], has_observed: bool) -> FlowEdgeRollupModel:
            pct = _percentiles(values)
            return FlowEdgeRollupModel(
                trace_count=len(values),
                avg_ms=pct["avg"] if has_observed else None,
                p50_ms=pct["p50"],
                p99_ms=pct["p99"],
                max_ms=pct["max"],
            )

        rollups = {
            node: rollup(values, observed.get(node, 0) > 0)
            for node, values in per_node.items()
        }
        return rollups, observed

    @staticmethod
    def _build_nodes(
        trace_rows: dict[str, dict[str, Any]],
        role_by_trace: dict[str, Any],
        own_rollups: Optional[dict[str, FlowEdgeRollupModel]] = None,
        own_observed: Optional[dict[str, int]] = None,
    ) -> list[FlowNodeModel]:
        pod_counter: dict[str, Counter] = {key: Counter() for key in _ROLE_POD_FIELDS}
        for trace_id in trace_rows:
            role = role_by_trace.get(trace_id)
            if role is None:
                continue
            for node_id, field_name in _ROLE_POD_FIELDS.items():
                value = getattr(role, field_name)
                if isinstance(value, list):
                    for pod in value:
                        if pod:
                            pod_counter[node_id][pod] += 1
                elif value:
                    pod_counter[node_id][str(value)] += 1

        def node(node_id: str, label: str, role: str) -> FlowNodeModel:
            return FlowNodeModel(
                id=node_id,
                label=label,
                role=role,
                top_workers=[pod for pod, _ in pod_counter[node_id].most_common(3)],
                own_rollup=(own_rollups or {}).get(node_id),
                own_observed=(own_observed or {}).get(node_id),
            )

        return [
            node("client", "Client", "client"),
            node("entry", "Entry Worker", "entry_worker"),
            node("meta", "Meta Worker", "meta_worker"),
            node("data", "Data Worker", "data_worker"),
        ]

    @staticmethod
    def _build_flow(
        stage_defs: list[dict[str, Any]],
        trace_rows: dict[str, dict[str, Any]],
        role_by_trace: dict[str, Any],
        operation_filter: str,
    ) -> FlowGraphModel:
        edges: list[FlowEdgeModel] = []
        # 收集该 flow 全部交互段的时延值，按全局分位自适应 warn/critical 阈值
        all_values: list[float] = []
        for trace_id, info in trace_rows.items():
            if info.get("resolved_operation") != operation_filter:
                continue
            for stage in stage_defs:
                value = FlowSummaryService._resolve_stage_value(info, stage)
                if value is not None:
                    all_values.append(value)
        pct = _percentiles(all_values)
        warn_ms = pct["p50"]
        critical_ms = pct["p99"]
        if warn_ms is None or critical_ms is None or critical_ms <= warn_ms:
            # 数据不足或分位退化时回退固定阈值
            warn_ms, critical_ms = WARN_MS, CRITICAL_MS

        for stage in stage_defs:
            values: list[float] = []
            hit_traces: list[tuple[str, float]] = []
            for trace_id, info in trace_rows.items():
                if info.get("resolved_operation") != operation_filter:
                    continue
                value = FlowSummaryService._resolve_stage_value(info, stage)
                # 全量 Trace 口径：该 trace 无该段数据 → 贡献 0，
                # 保证 Σ边avg + Σ节点avg + 残差avg = 总时延 avg 可对账
                values.append(value if value is not None else 0.0)
                if value is not None:
                    hit_traces.append((trace_id, value))
            edges.append(
                FlowSummaryService._build_edge(
                    stage, values, hit_traces, role_by_trace, warn_ms, critical_ms
                )
            )
        own_rollups, own_observed = FlowSummaryService._node_own_rollup(
            operation_filter, trace_rows
        )
        nodes = FlowSummaryService._build_nodes(
            trace_rows,
            role_by_trace,
            own_rollups,
            own_observed,
        )
        return FlowGraphModel(nodes=nodes, edges=edges, warn_ms=warn_ms, critical_ms=critical_ms)

    @staticmethod
    def _build_decomposition(
        trace_rows: dict[str, dict[str, Any]],
        role_by_trace: dict[str, Any],
    ) -> list[FlowDecompositionModel]:
        """总时延正交分解：GET/SET 各一份，段 = 互斥分配值，total/残差 一并标注。

        输出 order 与瀑布扣除顺序一致；残差恒为最后一段，满足
        Σ(段) + 残差 = total（前端图旁标注用）。
        """
        from latency.schemas.flow_summary import FlowDecompositionModel, FlowDecompositionSegmentModel

        result: list[FlowDecompositionModel] = []
        for operation in ("GET", "SET"):
            decomp_defs = _DECOMP_OPERATION.get(operation, _GET_DECOMP_SEGMENTS)
            totals: list[float] = []
            per_seg: dict[str, list[float]] = {}
            for info in trace_rows.values():
                if info.get("resolved_operation") != operation:
                    continue
                total = info.get("total_ms")
                if isinstance(total, (int, float)) and total > 0:
                    totals.append(float(total))
                decomp = info.get("decomp") or {}
                for key, _name, _node, _obs in decomp_defs:
                    per_seg.setdefault(key, []).append(decomp.get(key, 0.0))
                per_seg.setdefault(RESIDUAL_KEY, []).append(decomp.get(RESIDUAL_KEY, 0.0))

            def rollup(values: list[float]) -> FlowEdgeRollupModel:
                pct = _percentiles(values)
                return FlowEdgeRollupModel(
                    trace_count=len(values),
                    avg_ms=pct["avg"],
                    p50_ms=pct["p50"],
                    p99_ms=pct["p99"],
                    max_ms=pct["max"],
                )

            segments = []
            for key, name, node, _obs in decomp_defs:
                values = per_seg.get(key, [])
                segments.append(
                    FlowDecompositionSegmentModel(
                        key=key,
                        name=name,
                        node=node,
                        rollup=rollup(values),
                    )
                )
            residual_values = per_seg.get(RESIDUAL_KEY, [])
            segments.append(
                FlowDecompositionSegmentModel(
                    key=RESIDUAL_KEY,
                    name=RESIDUAL_NAME,
                    node="",
                    rollup=rollup(residual_values),
                )
            )
            result.append(
                FlowDecompositionModel(
                    operation=operation,
                    total=rollup(totals),
                    segments=segments,
                )
            )
        return result

    @staticmethod
    def _build_edge(
        stage: dict[str, Any],
        values: list[float],
        hit_traces: list[tuple[str, float]],
        role_by_trace: dict[str, Any],
        warn_ms: float,
        critical_ms: float,
    ) -> FlowEdgeModel:
        pct = _percentiles(values)
        max_ms = pct["max"]
        hit_trace_ids = {tid for tid, _ in hit_traces}
        # 无任何正值观测（全 0）→ 视为无数据（missing），avg 置 None 避免展示 0
        has_observed = len(hit_trace_ids) > 0
        if not has_observed:
            status = "missing"
        elif max_ms >= critical_ms:
            status = "critical"
        elif max_ms >= warn_ms:
            status = "warn"
        else:
            status = "present"

        top_trace = None
        if hit_traces:
            top_trace = max(hit_traces, key=lambda item: item[1])[0]

        def top_pods(role_name: str) -> list[str]:
            """统计命中 trace 中某角色出现次数最多的容器（Top 3）。"""
            field_name = _ROLE_POD_FIELDS.get(role_name)
            if not field_name:
                return []
            counter: Counter[str] = Counter()
            for trace_id in hit_trace_ids:
                role = role_by_trace.get(trace_id)
                if role is None:
                    continue
                value = getattr(role, field_name)
                if isinstance(value, list):
                    for pod in value:
                        if pod:
                            counter[pod] += 1
                elif value:
                    counter[str(value)] += 1
            return [pod for pod, _ in counter.most_common(3)]

        source_pods = top_pods(stage["source"])
        target_pods = top_pods(stage["target"])

        # 命中该段的 trace 明细，按耗时降序（前端点击边后展示列表并可下钻详情）
        trace_items = [
            FlowEdgeTraceItemModel(
                trace_id=tid,
                value_ms=value,
                roles=_roles_of(role_by_trace.get(tid)),
            )
            for tid, value in sorted(hit_traces, key=lambda item: item[1], reverse=True)[:50]
        ]

        rollup = FlowEdgeRollupModel(
            trace_count=len(values),
            observed=len(hit_trace_ids),
            avg_ms=pct["avg"] if has_observed else None,
            p50_ms=pct["p50"] if has_observed else None,
            p99_ms=pct["p99"] if has_observed else None,
            max_ms=max_ms if has_observed else None,
            top_trace=top_trace,
            top_workers=target_pods,
            trace_items=trace_items,
        )

        summary_parts = []
        if has_observed and pct["avg"] is not None:
            summary_parts.append(f"avg={pct['avg']:.1f}ms")
        if has_observed and pct["p99"] is not None:
            summary_parts.append(f"p99={pct['p99']:.1f}ms")
        if has_observed and (source_pods or target_pods):
            summary_parts.append(
                "容器 " + ", ".join((source_pods + target_pods)[:3])
            )
        if not summary_parts:
            summary_parts.append("无该段时延数据")

        return FlowEdgeModel(
            name=stage["stage"],
            source=stage["source"],
            target=stage["target"],
            operation=stage["operation"],
            status=status,
            summary=" / ".join(summary_parts),
            rollup=rollup,
            reason=stage["reason"],
            report_reading=stage["report_reading"],
            source_pods=source_pods,
            target_pods=target_pods,
        )
