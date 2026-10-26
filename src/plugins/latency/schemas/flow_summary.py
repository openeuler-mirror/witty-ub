# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Flow summary schemas: role-interaction flow graphs (read/write) for traces.

Data model mirrors the flow_stages structure used by the offline
``ds_trace_triage.py`` report (nodes + read/write edges with latency rollups),
so the frontend can render the same read-flow / write-flow diagram for both
connectivity (通断) and latency (时延) fault traces.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from latency.schemas.parse_config import StrictRequestModel
from latency.schemas.response import ResponseBase


class FlowEdgeTraceItemModel(BaseModel):
    """单条命中该交互段的 trace 明细（按耗时降序）。"""

    trace_id: str = Field(..., description="Trace ID")
    value_ms: float = Field(..., description="该段时延(ms)")
    roles: dict[str, str] = Field(default_factory=dict, description="{role: 容器}，供定界故障容器")


class FlowEdgeRollupModel(BaseModel):
    """Per-edge latency statistics across the selected traces."""

    trace_count: int = Field(default=0, description="该 flow 参与统计的全量 Trace 数（avg 为该口径，可与总时延对账）")
    observed: int = Field(default=0, description="观测到正值的 Trace 数（< trace_count 表示部分 Trace 无该段数据）")
    avg_ms: Optional[float] = Field(default=None, description="平均时延(ms)，全量 Trace 口径（含 0）")
    p50_ms: Optional[float] = Field(default=None, description="p50 时延(ms)")
    p99_ms: Optional[float] = Field(default=None, description="p99 时延(ms)")
    max_ms: Optional[float] = Field(default=None, description="最大时延(ms)")
    top_trace: Optional[str] = Field(default=None, description="该段最大时延的 Trace")
    top_workers: list[str] = Field(default_factory=list, description="Top 容器")
    top_ips: list[str] = Field(default_factory=list, description="Top IP")
    trace_items: list[FlowEdgeTraceItemModel] = Field(default_factory=list, description="命中 trace 明细（按耗时降序）")


class FlowEdgeModel(BaseModel):
    """Directed role-interaction edge with evidence and latency rollup."""

    name: str = Field(..., description="边名（含 read/write 前缀）")
    source: str = Field(..., description="源角色节点 id：client/entry/meta/data")
    target: str = Field(..., description="目标角色节点 id")
    operation: str = Field(default="", description="交互段操作描述，如 Client→Entry RPC/UB")
    status: str = Field(default="present", description="present|warn|critical|missing")
    summary: str = Field(default="", description="avg/p99/max/worker/IP 摘要文本")
    rollup: FlowEdgeRollupModel = Field(default_factory=FlowEdgeRollupModel)
    reason: str = Field(default="", description="该段的判读说明")
    report_reading: str = Field(default="", description="报告阅读指引")
    source_pods: list[str] = Field(default_factory=list, description="该段命中 Trace 中源角色的 Top 容器")
    target_pods: list[str] = Field(default_factory=list, description="该段命中 Trace 中目标角色的 Top 容器")


class FlowNodeModel(BaseModel):
    """Fixed role node (client / entry / meta / data)."""

    id: str = Field(..., description="节点 id：client/entry/meta/data")
    label: str = Field(default="", description="显示名")
    role: str = Field(default="", description="client|entry_worker|meta_worker|data_worker")
    top_ips: list[str] = Field(default_factory=list)
    top_workers: list[str] = Field(default_factory=list)
    own_rollup: Optional[FlowEdgeRollupModel] = Field(
        default=None,
        description="节点自身处理统计（点归点：不含跨角色交互边、不含残差），avg 为全量 Trace 口径（含 0），可与总时延 avg 对账",
    )
    own_observed: Optional[int] = Field(
        default=None,
        description="观测到自身处理正值的 Trace 数（< trace_count 表示部分 Trace 无该节点处理段，实际处理水平 avg = 全量avg × trace_count / own_observed）",
    )


class FlowGraphModel(BaseModel):
    """One flow (read or write): role nodes + interaction edges."""

    nodes: list[FlowNodeModel] = Field(default_factory=list)
    edges: list[FlowEdgeModel] = Field(default_factory=list)
    warn_ms: Optional[float] = Field(default=None, description="自适应 warn 阈值(ms)，按该 flow 全部交互段时延的 p50 计算")
    critical_ms: Optional[float] = Field(default=None, description="自适应 critical 阈值(ms)，按该 flow 全部交互段时延的 p99 计算")


class TraceFlowStageModel(BaseModel):
    """Per-trace stage latencies, used by the single-trace flow diagram."""

    trace_id: str = Field(..., description="Trace ID")
    operation: str = Field(default="", description="GET/SET")
    total_ms: Optional[float] = Field(default=None, description="端到端时延(ms)")
    stages: dict[str, float] = Field(default_factory=dict, description="{stage_key: ms}，含正交分解各段互斥分配值")
    roles: dict[str, str] = Field(default_factory=dict, description="{role: 容器}，节点级容器信息")
    raw: dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="32 项 YUANRONG 关键时延原始微秒值，供前端单 trace 时延明细表透传对齐",
    )


class FlowDecompositionSegmentModel(BaseModel):
    """正交分解段：总时延按因果顺序互斥分配，Σ(段) + 残差 = 总时延。

    段值均为"分配值"（min(remaining, observed) 瀑布扣除），非原始观测窗口，
    保证任意两段不重叠、逐 trace 可加总。
    """

    key: str = Field(..., description="段 key：GET=sdk_processing_us/query_get_network_us/query_get_framework_us/query_get_worker_internal_us/urma_processing_us/client_urma_processing_us/worker_residual_us；SET=client_process/client_net_resid/entry_to_meta_publish/worker_local；residual 为残差")
    name: str = Field(..., description="展示名")
    node: str = Field(default="", description="归属节点：client/entry/meta/data（残差为空）")
    rollup: FlowEdgeRollupModel = Field(default_factory=FlowEdgeRollupModel, description="该段统计（分配值）")


class FlowDecompositionModel(BaseModel):
    """总时延的正交分解视图（点归点/线归线）：角色自身处理标注在节点，交互 RPC 是边。"""

    operation: str = Field(..., description="GET/SET")
    total: FlowEdgeRollupModel = Field(default_factory=FlowEdgeRollupModel, description="总时延统计")
    segments: list[FlowDecompositionSegmentModel] = Field(default_factory=list, description="正交分解段（按瀑布扣除顺序）")


class FlowSummaryModel(BaseModel):
    """Read/write flow summary for a set of traces."""

    nodes: list[FlowNodeModel] = Field(default_factory=list)
    read: FlowGraphModel = Field(default_factory=FlowGraphModel)
    write: FlowGraphModel = Field(default_factory=FlowGraphModel)
    per_trace: list[TraceFlowStageModel] = Field(default_factory=list)
    decomposition: list[FlowDecompositionModel] = Field(default_factory=list, description="GET/SET 各一份正交分解（总时延/残差标注用）")


class ListFlowSummaryRequest(StrictRequestModel):
    """Request for the read/write flow summary aggregation."""

    model_config = ConfigDict(extra="allow")

    kb_id: str = Field(..., description="日志知识库 ID")
    source: str = Field(default="latency", description="latency（时延故障）| fault（通断故障）")
    trace_ids: Optional[list[str]] = Field(default=None, description="Trace ID 列表（缺省按 source 全量聚合）")
    operation: Optional[str] = Field(default=None, description="GET/SET，缺省按 trace 实际操作分组")
    start_time: Optional[str] = Field(default=None, description="起始时间 YYYY-MM-DD HH:MM:SS")
    end_time: Optional[str] = Field(default=None, description="结束时间 YYYY-MM-DD HH:MM:SS")


class ListFlowSummaryMsg(BaseModel):
    result: FlowSummaryModel = Field(..., description="读写 Flow 汇总")


class ListFlowSummaryResponse(ResponseBase):
    result: ListFlowSummaryMsg = Field(..., description="读写 Flow 汇总响应")
