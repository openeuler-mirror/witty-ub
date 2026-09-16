# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Trace 轻量取数层 schema（/trace/list + /trace/{trace_id} + /stats/stages）。

独立新增文件（设计文档 docs/design/trace-light-api.md）：全部为轻量取数
API 专用的请求/响应模型，不复用、不修改既有 schemas 文件中的旧类。
清单条目命名 TraceListItem，避免与 response.py 既有 TraceItem
（/log_parse_result/traces/host/list 按主机条目）冲突。
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from latency.schemas.parse_config import StrictRequestModel, TimeStr
from latency.schemas.response import ResponseBase


# ============================================================
# 请求模型
# ============================================================
class ListTracesRequest(StrictRequestModel):
    """trace 清单（粗筛主接口）请求：时延/故障双源合并。

    设计文档 docs/design/trace-light-api.md §4.1。
    """
    kb_id: str = Field(..., description="知识库ID，用于过滤")
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志文件的解析结果")
    trace_ids: Optional[list[str]] = Field(default=None, description="Trace ID列表，用于批量查询多个链路")
    operation: Optional[str] = Field(default=None, description="操作类型过滤：GET / SET")
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="时延侧异常标记过滤：True仅异常，False仅正常，None不区分",
    )
    pod_ip: Optional[str] = Field(default=None, description="Pod IP 或 Pod 名称，用于精确过滤（时延侧）")
    host: Optional[str] = Field(default=None, description="主机名称，用于模糊过滤（时延侧）")
    cluster_name: Optional[str] = Field(default=None, description="集群名称，用于精确过滤（时延侧）")
    src_ip: Optional[str] = Field(default=None, description="源IP地址过滤")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址过滤")
    start_time: Optional[TimeStr] = Field(
        default=None,
        description="开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[TimeStr] = Field(
        default=None,
        description="结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    status_codes: Optional[list[str]] = Field(
        default=None,
        description="故障码过滤（故障侧语义：返回挂有任一指定故障码的 trace）",
    )
    sort_by: Literal["total_latency", "failure_cnt", "timestamp"] = Field(
        default="total_latency",
        description="排序键：total_latency/timestamp 走时延侧原生排序，failure_cnt 为故障码计数总和（服务内聚合排序）",
    )
    sort_order: Literal["desc", "asc"] = Field(default="desc", description="排序方向，默认降序")
    page_cnt: int = Field(default=20, ge=1, le=500, description="每页条数（≤500），默认20")
    page_num: int = Field(default=1, ge=1, description="页码，默认1")
    include: list[Literal["failure_codes", "topology"]] = Field(
        default_factory=list,
        description="附加块：failure_codes=故障码聚合；topology=Pod/主机/IP拓扑；未指定的块不出现在响应里（非 null 占位）",
    )


class GetStageStatsRequest(StrictRequestModel):
    """主导问题分类（组件定位入口）请求。

    设计文档 docs/design/trace-light-api.md §4.3。
    """
    kb_id: str = Field(..., description="知识库ID，用于过滤")
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志文件")
    operation: Optional[str] = Field(
        default="GET",
        description="操作类型过滤：GET / SET（仅 GET 支持主导问题分类，SET 返回空 items + note）",
    )
    start_time: Optional[TimeStr] = Field(
        default=None,
        description="开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[TimeStr] = Field(
        default=None,
        description="结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    sample_cap: int = Field(
        default=1000,
        ge=50,
        le=5000,
        description="采样上限：异常 trace 全量 + top 慢正常合并去重后的最大条数",
    )


class ListFailureCodeStatsRequest(StrictRequestModel):
    """trace 故障码聚合统计查询（/trace/list 故障主源路径的 manager 入参）。

    设计文档 docs/design/trace-light-api.md §5：聚合/排序/分页全部下推 DB
    （unnest → GROUP BY → ORDER/LIMIT/OFFSET），服务层不做全量拉取。
    过滤字段与 ListTraceFailureEventResultRequest 对齐（故障侧原生语义），
    但 is_anomalous 例外：此处为时延侧口径（log_parse_result.is_anomalous），
    由 SQL 侧 join log_parse_result 过滤，非故障侧 failure_mode 口径。
    """

    kb_id: str = Field(..., description="知识库ID，用于过滤")
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志文件")
    trace_ids: Optional[list[str]] = Field(default=None, description="Trace ID列表，用于批量查询")
    pod_names: Optional[list[str]] = Field(default=None, description="容器名列表，用于过滤")
    host_names: Optional[list[str]] = Field(default=None, description="主机名列表，用于过滤")
    cluster_names: Optional[list[str]] = Field(default=None, description="集群名列表，用于过滤")
    src_ip: Optional[str] = Field(default=None, description="源IP地址，用于过滤")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，用于过滤")
    status_codes: Optional[list[str]] = Field(
        default=None, description="故障码过滤（数组重叠，返回挂有任一指定故障码的 trace）"
    )
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="时延侧异常标记（SQL join log_parse_result 过滤；纯故障 trace 无时延行会被剔除）",
    )
    start_time: Optional[TimeStr] = Field(
        default=None,
        description="开始时间（基于故障侧 timestamp 字段），格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[TimeStr] = Field(
        default=None,
        description="结束时间（基于故障侧 timestamp 字段），格式为YYYY-MM-DD HH:MM:SS",
    )
    operation: Optional[str] = Field(default=None, description="操作类型过滤：GET / SET")
    sort_by: Literal["failure_cnt", "total_latency", "timestamp"] = Field(
        default="failure_cnt",
        description="排序键：failure_cnt=故障码计数总和；total_latency/timestamp=join 时延侧排序键（纯故障 trace 排末尾）",
    )
    sort_order: Literal["desc", "asc"] = Field(default="desc", description="排序方向，默认降序")
    page_cnt: int = Field(default=20, ge=1, le=500, description="每页条数（≤500），默认20")
    page_num: int = Field(default=1, ge=1, description="页码，默认1")


# ============================================================
# manager 返回模型（DB 侧聚合行）
# ============================================================
class FailureCodeCntItem(BaseModel):
    """单故障码计数（trace 级聚合行）"""
    code: str = Field(..., description="故障码")
    cnt: int = Field(..., description="出现次数")


class TraceFailureCodeStatModel(BaseModel):
    """trace 故障码聚合统计行。

    TraceLightPGManager.list_failure_code_stats /
    list_failure_codes_by_trace_ids 的返回模型（SQL 侧
    unnest(status_code) → GROUP BY 聚合，支撑 10W~50W 行规模）。
    """
    trace_id: str = Field(..., description="Trace ID")
    failure_cnt: int = Field(default=0, description="故障码计数总和")
    codes: list[FailureCodeCntItem] = Field(
        default_factory=list, description="故障码计数明细（cnt 降序、code 升序）"
    )
    operation: Optional[str] = Field(
        default=None, description="操作类型（故障侧聚合，纯故障 trace 回退用）"
    )


# ============================================================
# 响应模型：/trace/list + /trace/{trace_id}
# ============================================================
class TraceFailureCodeItem(BaseModel):
    """trace 故障码聚合条目（status_code 列表 Counter 聚合）。"""
    code: str = Field(..., description="故障码")
    cnt: int = Field(..., description="该 trace 命中该故障码的次数")


class TraceListItem(BaseModel):
    """trace 清单条目。

    默认最小形态仅含基础四字段（trace_id/total_latency_ms/is_anomalous/operation），
    include 指定的附加块才会被服务层显式赋值并出现在响应里（非 null 占位）。
    """
    trace_id: str = Field(..., description="Trace ID")
    total_latency_ms: Optional[float] = Field(
        default=None, description="总时延（毫秒）；纯故障 trace 无时延行时为 null"
    )
    is_anomalous: Optional[bool] = Field(
        default=None, description="时延侧异常标记；纯故障 trace 为 null"
    )
    operation: Optional[str] = Field(default=None, description="操作类型 GET / SET")
    failure_codes: Optional[list[TraceFailureCodeItem]] = Field(
        default=None,
        description="故障码聚合（include=failure_codes / status_codes 过滤 / failure_cnt 排序时）",
    )
    failure_cnt: Optional[int] = Field(
        default=None,
        description="故障码计数总和（故障主源路径：status_codes 过滤 / failure_cnt 排序时）",
    )
    pod_ips: Optional[list[str]] = Field(
        default=None, description="涉及 Pod IP 列表（include=topology）"
    )
    host: Optional[str] = Field(default=None, description="主机名（include=topology）")
    src_ip: Optional[str] = Field(default=None, description="源 IP（include=topology）")
    dst_ip: Optional[str] = Field(default=None, description="目的 IP（include=topology）")


class ListTracesMsg(BaseModel):
    total: int = Field(..., description="命中 trace 总数（主源 total）")
    items: list[TraceListItem] = Field(default_factory=list, description="trace 清单")


class ListTracesResponse(ResponseBase):
    result: ListTracesMsg = Field(..., description="trace 清单响应结果")


class GetTraceMsg(BaseModel):
    """单 trace 轻量画像：一次拿全时延 + 故障码 + 拓扑。"""
    trace_id: str = Field(..., description="Trace ID")
    total_latency_ms: Optional[float] = Field(
        default=None, description="总时延（毫秒）；纯故障 trace 无时延行时为 null"
    )
    is_anomalous: Optional[bool] = Field(
        default=None, description="时延侧异常标记；纯故障 trace 为 null"
    )
    operation: Optional[str] = Field(default=None, description="操作类型 GET / SET")
    failure_codes: list[TraceFailureCodeItem] = Field(
        default_factory=list, description="故障码聚合（无故障记录为 []）"
    )
    pod_ips: Optional[list[str]] = Field(default=None, description="涉及 Pod IP 列表")
    host: Optional[str] = Field(default=None, description="主机名")
    src_ip: Optional[str] = Field(default=None, description="源 IP")
    dst_ip: Optional[str] = Field(default=None, description="目的 IP")
    timestamp: Optional[str] = Field(
        default=None,
        description="时间戳：故障侧最早日志时间优先，无故障记录时取解析侧时间",
    )


class GetTraceResponse(ResponseBase):
    result: GetTraceMsg = Field(..., description="单 trace 轻量画像响应结果")


# ============================================================
# 响应模型：/stats/stages（主导问题分类，组件定位入口）
# ============================================================
class StageStatsTopTrace(BaseModel):
    """桶内 top trace 下钻种子：trace_id 直接用于 /trace/list 批查。"""
    trace_id: str = Field(..., description="Trace ID")
    evidence_ms: float = Field(..., description="该桶主阶段证据耗时（毫秒）")
    client_ms: Optional[float] = Field(
        default=None, description="该 trace 的 Client 总时延对照（毫秒）"
    )


class StageStatsItem(BaseModel):
    """主导问题分类桶。

    每条 trace 按“最大互斥阶段”归入唯一一个桶（winner-take-all），
    URMA 超时 / 交叉窗口未细分走规则特判；桶间互斥、合计 = 采样 trace 数。
    """
    key: str = Field(
        ...,
        description=(
            "桶标识：rpc_network/rpc_queue/query_meta/urma/data_worker/"
            "cross_window/residual/urma_timeout"
        ),
    )
    name: str = Field(
        ...,
        description=(
            "桶显示名：RPC网络/RPC排队/QueryMeta/URMA/Data Worker服务端处理/"
            "Client/Worker交叉窗口未细分/未解释残差/URMA超时"
        ),
    )
    trace_cnt: int = Field(default=0, description="归入该桶的 trace 总数（成功+失败）")
    success_cnt: int = Field(default=0, description="其中成功 trace 数（is_anomalous=False）")
    fail_cnt: int = Field(default=0, description="其中失败 trace 数（is_anomalous=True）")
    p50_ms: Optional[float] = Field(
        default=None, description="该桶主阶段证据耗时 P50(ms)；普通瓶颈取 winner 维度耗时"
    )
    p90_ms: Optional[float] = Field(default=None, description="该桶主阶段证据耗时 P90(ms)")
    max_ms: Optional[float] = Field(default=None, description="该桶主阶段证据耗时 max(ms)")
    client_p50_ms: Optional[float] = Field(
        default=None, description="桶内 trace Client 总时延 P50(ms) 对照"
    )
    client_p90_ms: Optional[float] = Field(
        default=None, description="桶内 trace Client 总时延 P90(ms) 对照"
    )
    metric_name: str = Field(
        default="主阶段耗时",
        description="证据口径：主阶段耗时 / URMA timeout elapsedMs",
    )
    action: str = Field(default="", description="该类问题的治理指引（静态文案）")
    note: Optional[str] = Field(default=None, description="桶口径/构成字段说明")
    top_traces: list[StageStatsTopTrace] = Field(
        default_factory=list,
        description="桶内证据耗时 Top trace（下钻种子，按 evidence_ms 降序）",
    )


class GetStageStatsMsg(BaseModel):
    operation: str = Field(..., description="操作类型（仅 GET 支持主导问题分类）")
    sample_cnt: int = Field(..., description="实际参与分类的采样 trace 数（= Σ各桶 trace_cnt）")
    truncated: bool = Field(default=False, description="是否因采样上限截断")
    items: list[StageStatsItem] = Field(
        default_factory=list, description="8 互斥桶（固定顺序，含零计数桶）"
    )
    note: Optional[str] = Field(default=None, description="样本集/口径说明")


class GetStageStatsResponse(ResponseBase):
    result: GetStageStatsMsg = Field(..., description="主导问题分类响应结果")
