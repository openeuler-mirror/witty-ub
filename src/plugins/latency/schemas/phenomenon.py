# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Schemas for the phenomenon search / index API."""
from __future__ import annotations

from typing import Literal

from latency.config import phenomenon as settings
from latency.schemas.parse_config import StrictRequestModel
from latency.schemas.response import ResponseBase
from pydantic import BaseModel, Field, model_validator

PhenomenonScope = Literal["report", "case", "all", "legacy_all"]
LogType = Literal["KVCache", "UBSocket"]
OperationType = Literal["GET", "SET"]
FaultType = Literal["latency", "connectivity", "mixed", "unknown"]


class SearchPhenomenonRequest(StrictRequestModel):
    """Agent-facing natural-language phenomenon query."""

    query: str = Field(..., min_length=1, max_length=2000, description="本次现场现象描述")
    top_k: int = Field(
        default_factory=settings.rag_default_top_k,
        validate_default=True,
        ge=1,
        le=20,
        description="返回卡片数上限",
    )
    min_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="归一化分数阈值"
    )
    log_type: LogType | None = Field(default=None, description="日志类型过滤")
    operation: OperationType | None = Field(default=None, description="操作类型过滤")
    fault_type: FaultType | None = Field(default=None, description="故障类型过滤")
    include_unverified: bool = Field(
        default=True, description="false 时仅返回 verified 卡片"
    )


class PhenomenonMatchModel(BaseModel):
    doc_id: str = Field(..., description="卡片逻辑主键")
    score: float = Field(..., description="归一化相似度 0~1")
    score_raw: float = Field(..., description="上游原始分数")
    kind: str = Field(..., description="report / case / legacy_case")
    title: str = Field(..., description="已发布版本的卡片标题")
    symptom: str = Field(..., description="已发布版本的现象摘要，≤400 字符")
    report_id: str | None = Field(default=None, description="报告指针")
    source_fault_id: str | None = Field(default=None, description="报告故障指针")
    case_id: str | None = Field(default=None, description="新案例指针")
    case_no: str | None = Field(default=None, description="新案例编号")
    legacy_case_id: str | None = Field(default=None, description="旧案例指针")
    verification: str = Field(..., description="信任标签，按当前业务状态实时派生")
    binding_status: str = Field(..., description="none / valid / stale")
    operation_scope: str | None = Field(
        default=None, description="report 表示操作归属来自整份报告"
    )
    report_available: bool = Field(..., description="报告文件是否仍存在")
    get_report: str | None = Field(default=None, description="报告详情相对路径")
    get_report_html: str | None = Field(default=None, description="报告 HTML 相对路径")
    get_fault: str | None = Field(default=None, description="单故障读取相对路径")
    get_case: str | None = Field(default=None, description="新案例详情相对路径")
    get_legacy_case: str | None = Field(default=None, description="旧案例详情相对路径")


class SearchPhenomenaMsg(BaseModel):
    matches: list[PhenomenonMatchModel] = Field(default_factory=list)
    returned_count: int = Field(default=0, description="本次实际返回卡片数")
    truncated: bool = Field(
        default=False, description="候选检查达到上限仍未穷尽时为 true"
    )


class SearchPhenomenaResponse(ResponseBase):
    result: SearchPhenomenaMsg = Field(..., description="现象检索响应结果")


class IndexPhenomenonRequest(StrictRequestModel):
    scope: PhenomenonScope = Field(..., description="report / case / all / legacy_all")
    report_id: str | None = Field(default=None, max_length=200)
    case_id: str | None = Field(default=None, max_length=64)
    force: bool = Field(default=False, description="忽略哈希强制重建")

    @model_validator(mode="after")
    def _require_target(self) -> IndexPhenomenonRequest:
        if self.scope == "report" and not self.report_id:
            raise ValueError("scope=report 时 report_id 必填")
        if self.scope == "case" and not self.case_id:
            raise ValueError("scope=case 时 case_id 必填")
        return self


class IndexPhenomenonMsg(BaseModel):
    accepted: bool = Field(default=True)
    scope: str = Field(..., description="本次重建范围")
    target_id: str | None = Field(default=None)
    queued_count: int = Field(default=0)
    skipped_count: int = Field(default=0)
    index_status: str | None = Field(default=None)


class IndexPhenomenonResponse(ResponseBase):
    result: IndexPhenomenonMsg = Field(..., description="现象重建受理结果")


class GetPhenomenonMsg(BaseModel):
    doc_id: str
    kind: str
    content_source: str
    report_id: str | None = None
    source_fault_id: str | None = None
    case_id: str | None = None
    case_no: str | None = None
    legacy_case_id: str | None = None
    title: str
    symptom: str
    verification: str
    binding_status: str
    operation_scope: str | None = None
    report_available: bool = False
    get_report: str | None = None
    get_report_html: str | None = None
    get_fault: str | None = None
    get_case: str | None = None
    get_legacy_case: str | None = None
    index_status: str
    index_error: str | None = None
    retry_count: int = 0
    indexed_at: str | None = None
    content_hash: str
    indexed_content_hash: str | None = None


class GetPhenomenonResponse(ResponseBase):
    result: GetPhenomenonMsg = Field(..., description="现象卡片详情响应结果")


class ReportIndexCountsModel(BaseModel):
    total: int = Field(default=0, description="报告索引行数")
    by_status: dict[str, int] = Field(default_factory=dict, description="按聚合索引状态计数")


class CardCountsModel(BaseModel):
    enabled: int = Field(default=0, description="启用中的卡片数")
    searchable: int = Field(default=0, description="当前可检索的卡片数")
    by_status: dict[str, int] = Field(default_factory=dict, description="按索引状态计数")


class QueueCountsModel(BaseModel):
    cleanup_active: int = Field(default=0, description="未完成的 RAG 清理任务数")
    cleanup_oldest_age_seconds: int | None = Field(default=None, description="最老清理任务等待秒数")
    events_active: int = Field(default=0, description="未完成的索引事件数")
    events_oldest_age_seconds: int | None = Field(default=None, description="最老索引事件等待秒数")
    stuck_parsing: int = Field(default=0, description="超过 30 分钟仍处于 parsing 的卡片数")


class RetrievalStatsModel(BaseModel):
    window_seconds: int = Field(default=300, description="滚动窗口秒数")
    requests: int = Field(default=0, description="窗口内检索次数")
    errors: int = Field(default=0, description="窗口内失败次数")
    error_rate: float = Field(default=0.0, description="窗口内失败率")
    p95_ms: float | None = Field(default=None, description="窗口内 p95 毫秒")


class PhenomenonAlertModel(BaseModel):
    code: str = Field(..., description="告警编码")
    severity: Literal["warning", "critical"] = Field(..., description="告警级别")
    message: str = Field(..., description="告警说明")
    value: float | int | str | None = Field(default=None, description="当前值")
    threshold: float | int | str | None = Field(default=None, description="触发阈值")


class PhenomenonStatusMsg(BaseModel):
    index_enabled: bool = Field(..., description="索引 worker 开关")
    search_enabled: bool = Field(..., description="检索开关")
    self_check_enabled: bool = Field(..., description="启动自检开关")
    self_check_done: bool = Field(..., description="启动自检是否通过")
    rag_configured: bool = Field(..., description="RAG 地址与专用知识库是否已配置")
    reports: ReportIndexCountsModel = Field(..., description="报告索引概况")
    cards: CardCountsModel = Field(..., description="现象卡片概况")
    queues: QueueCountsModel = Field(..., description="清理与事件积压")
    retrieval: RetrievalStatsModel = Field(..., description="近期检索指标")
    alerts: list[PhenomenonAlertModel] = Field(
        default_factory=list, description="按阈值派生的告警项"
    )


class GetPhenomenonStatusResponse(ResponseBase):
    result: PhenomenonStatusMsg = Field(..., description="现象索引与检索运维快照")
