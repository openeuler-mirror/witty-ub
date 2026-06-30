import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class DiagnosisCaseSignalModel(BaseModel):
    case_id: str = Field(..., description="历史诊断案例ID")
    signal_type: str = Field(..., description="信号类型")
    signal_value: str = Field(..., description="信号值")
    weight: float = Field(default=1.0, description="匹配权重")


class DiagnosisCaseModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="历史诊断案例ID")
    kb_id: str | None = Field(default=None, description="来源日志知识库ID")
    fault_type: Literal["latency", "connectivity", "mixed", "unknown"] = Field(
        default="unknown", description="故障类型"
    )
    title: str | None = Field(default=None, description="案例标题")
    symptom_summary: str = Field(..., description="故障现象摘要")
    root_cause: str = Field(..., description="诊断出的故障原因")
    recommendation: str = Field(..., description="建议处理方案")
    confidence: float = Field(default=0.0, description="结论置信度，0到1")
    failure_mode_ids: list[str] = Field(default_factory=list, description="关联故障模式ID")
    status_codes: list[str] = Field(default_factory=list, description="关联状态码")
    fingerprint_json: dict[str, Any] = Field(
        default_factory=dict,
        description="可泛化的故障指纹，如IP对、主机、Pod、时延组件、关键日志短语",
    )
    evidence_refs_json: list[dict[str, Any]] = Field(
        default_factory=list, description="支持结论的证据引用"
    )
    counter_evidence_json: list[dict[str, Any]] = Field(
        default_factory=list, description="已检查的反证或排除项"
    )
    source_log_ids: list[str] = Field(default_factory=list, description="来源日志ID")
    hit_count: int = Field(default=0, description="被历史匹配命中的次数")
    existed_status: bool = Field(default=True, description="是否有效")
    first_seen_at: str = Field(default_factory=_now, description="首次发现时间")
    last_seen_at: str = Field(default_factory=_now, description="最近发现时间")
    created_at: str = Field(default_factory=_now, description="创建时间")
    updated_at: str = Field(default_factory=_now, description="更新时间")


class DiagnosisCaseMatchModel(BaseModel):
    case: DiagnosisCaseModel = Field(..., description="历史诊断案例")
    match_score: float = Field(..., description="匹配分数")
    matched_signals: list[DiagnosisCaseSignalModel] = Field(
        default_factory=list, description="命中的结构化信号"
    )
