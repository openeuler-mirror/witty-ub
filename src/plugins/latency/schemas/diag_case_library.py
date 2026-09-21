# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Schemas for the supernode diagnosis case library (``/diag_case_library``).

Structured JSON contracts follow
``docs/design/supernode-case-library.md`` §3.4 and are validated by pydantic
models rather than free-form dicts, so a malformed evidence / remediation /
verification payload is rejected at the API boundary.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from latency.ENUM.case_library import (
    DiagCaseOperation,
    DiagCaseSource,
    DiagCaseStatus,
)
from latency.ENUM.general import DiagnosisConfigLogType
from latency.common.local_time import local_now
from latency.schemas.parse_config import StrictRequestModel
from latency.schemas.response import ResponseBase

FaultType = Literal["latency", "connectivity", "mixed", "unknown"]

# Enums inside ``StrictRequestModel`` need an explicit lax marker; otherwise the
# strict config rejects the plain string values the API actually receives.
_LaxStatus = Annotated[DiagCaseStatus, Field(strict=False)]
_LaxOperation = Annotated[DiagCaseOperation, Field(strict=False)]
_LaxLogType = Annotated[DiagnosisConfigLogType, Field(strict=False)]


def _now() -> str:
    return local_now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ============================================================
# §3.4 结构化 JSON 契约
# ============================================================
class StageBucketModel(BaseModel):
    """L2 阶段桶分布中的单个桶（取值与 /stats/stages 的桶 key 一致）。"""

    key: str = Field(..., min_length=1, description="桶 key，如 set_client / set_worker")
    trace_cnt: int = Field(default=0, ge=0, description="样本 trace 数")
    success_cnt: int = Field(default=0, ge=0, description="成功数")
    fail_cnt: int = Field(default=0, ge=0, description="失败数")
    p50_ms: Optional[float] = Field(default=None, description="P50 耗时（毫秒）")
    p90_ms: Optional[float] = Field(default=None, description="P90 耗时（毫秒）")
    max_ms: Optional[float] = Field(default=None, description="最大耗时（毫秒）")
    metric_name: Optional[str] = Field(default=None, description="指标名")
    note: Optional[str] = Field(default=None, description="备注")


class StageFeaturesModel(BaseModel):
    """stage_features_json 契约。"""

    operation: Optional[str] = Field(default=None, description="该快照对应的操作类型")
    buckets: list[StageBucketModel] = Field(default_factory=list, description="桶分布")
    sample_cnt: int = Field(default=0, ge=0, description="样本总数")
    truncated: bool = Field(default=False, description="样本是否被截断")


class EvidenceModel(BaseModel):
    """evidence_json 单项证据锚点。"""

    kind: Literal["api", "trace", "log", "sql"] = Field(..., description="证据类型")
    ref: str = Field(..., min_length=1, description="可复现引用，如 trace_id / 文件:行号")
    params: dict[str, Any] = Field(default_factory=dict, description="kind=api 时的请求参数")
    excerpt: Optional[str] = Field(default=None, description="原文片段")
    note: Optional[str] = Field(default=None, description="该证据说明什么")


class RemediationStepModel(BaseModel):
    """remediation_json 单个处置步骤。"""

    step: int = Field(..., ge=1, description="步骤序号，从 1 开始")
    action: str = Field(..., min_length=1, description="处置动作")
    expected: Optional[str] = Field(default=None, description="执行后应观察到的现象")
    risk: Optional[str] = Field(default=None, description="该步骤的风险")


class VerificationModel(BaseModel):
    """verification_json 验证闭环。"""

    method: Optional[str] = Field(default=None, description="验证方法")
    observed_result: Optional[str] = Field(default=None, description="实测观察到的结果")
    closed_loop: bool = Field(default=False, description="是否已闭环")
    verified_at: Optional[str] = Field(default=None, description="验证时间")
    notes: Optional[str] = Field(default=None, description="补充说明")


class RelationModel(BaseModel):
    """relations_json 单条案例关系。"""

    case_no: str = Field(..., min_length=1, description="关联案例编号，如 UB-CASE-000012")
    relation: Literal["same_fault", "upstream", "downstream", "false_positive"] = Field(
        ..., description="关系类型"
    )
    note: Optional[str] = Field(default=None, description="关系说明")


class VersionModel(BaseModel):
    """version_json 版本快照（补 L4 版本缺口）。"""

    kernel: Optional[str] = Field(default=None, description="内核版本")
    os: Optional[str] = Field(default=None, description="操作系统版本")
    urma: Optional[str] = Field(default=None, description="URMA 版本")
    umq: Optional[str] = Field(default=None, description="UMQ 版本")
    ubsocket: Optional[str] = Field(default=None, description="UBSocket 版本")


class TimeWindowModel(BaseModel):
    """time_window_json 故障时间窗口。"""

    start: Optional[str] = Field(default=None, description="开始时间")
    end: Optional[str] = Field(default=None, description="结束时间")


# ============================================================
# 领域模型
# ============================================================
class DiagCaseLibrarySignalModel(BaseModel):
    case_id: str = Field(..., description="超节点诊断案例ID")
    signal_type: str = Field(..., description="信号类型")
    signal_value: str = Field(..., description="信号值")
    weight: float = Field(default=1.0, description="匹配权重")


class DiagCaseLibraryModel(BaseModel):
    """diag_case_library 一行."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="案例ID")
    case_no: Optional[str] = Field(default=None, description="可读编号，如 UB-CASE-000123")
    status: DiagCaseStatus = Field(default=DiagCaseStatus.DRAFT, description="审核状态")
    revision: int = Field(default=0, description="案例修订号")
    created_by: Optional[str] = Field(default=None, description="创建人标识")
    confirmed_by: Optional[str] = Field(default=None, description="确认人标识")
    archived_by: Optional[str] = Field(default=None, description="归档人标识")
    confirmed_at: Optional[str] = Field(default=None, description="确认时间")
    archived_at: Optional[str] = Field(default=None, description="归档时间")
    archive_reason: Optional[str] = Field(default=None, description="归档原因")
    source: DiagCaseSource = Field(default=DiagCaseSource.INTERNAL, description="案例来源")
    source_url: Optional[str] = Field(default=None, description="community / online 来源链接")
    title: Optional[str] = Field(default=None, description="案例标题")
    log_type: Optional[str] = Field(default=None, description="日志类型 KVCache / UBSocket")
    kb_id: Optional[str] = Field(default=None, description="来源知识库ID，可空表示全局案例")
    kb_name: Optional[str] = Field(default=None, description="来源知识库名称")
    cluster_name: Optional[str] = Field(default=None, description="集群名称")
    hosts: list[str] = Field(default_factory=list, description="主机名")
    pods: list[str] = Field(default_factory=list, description="Pod 名")
    src_ips: list[str] = Field(default_factory=list, description="源 IP")
    dst_ips: list[str] = Field(default_factory=list, description="目的 IP")
    node_type: Optional[str] = Field(default=None, description="超节点形态")
    version_json: Optional[VersionModel] = Field(default=None, description="版本快照")
    scope_limits: Optional[str] = Field(default=None, description="不适用场景")
    operation: Optional[DiagCaseOperation] = Field(default=None, description="操作类型")
    fault_type: FaultType = Field(default="unknown", description="故障类型")
    status_codes: list[str] = Field(default_factory=list, description="关联状态码")
    failure_mode_ids: list[str] = Field(default_factory=list, description="关联故障模式ID")
    latency_components: list[str] = Field(default_factory=list, description="异常时延组件桶 key")
    log_keywords: list[str] = Field(default_factory=list, description="关键日志原文短语")
    stage_features_json: Optional[StageFeaturesModel] = Field(
        default=None, description="L2 阶段桶分布快照"
    )
    fault_shape: Optional[str] = Field(default=None, description="故障时间形状")
    time_window_json: Optional[TimeWindowModel] = Field(default=None, description="故障时间窗口")
    confidence: float = Field(default=0.0, description="结论验证强度，0~1")
    symptom_summary: str = Field(default="", description="现象摘要")
    evidence_json: list[EvidenceModel] = Field(default_factory=list, description="证据锚点")
    root_cause_summary: str = Field(default="", description="一句话根因")
    root_cause_detail: Optional[str] = Field(default=None, description="机理长文")
    counter_evidence_json: list[dict[str, Any]] = Field(
        default_factory=list, description="已排除项"
    )
    remediation_json: list[RemediationStepModel] = Field(
        default_factory=list, description="分步处置"
    )
    verification_json: Optional[VerificationModel] = Field(
        default=None, description="验证闭环"
    )
    relations_json: list[RelationModel] = Field(default_factory=list, description="关联案例")
    search_text: Optional[str] = Field(default=None, description="embedding 正文，写入时生成")
    embedding_model: Optional[str] = Field(default=None, description="向量模型，本轮留空")
    embedded_at: Optional[str] = Field(default=None, description="向量化时间，本轮留空")
    source_log_ids: list[str] = Field(default_factory=list, description="来源日志ID")
    hit_count: int = Field(default=0, description="采纳次数")
    existed_status: bool = Field(default=True, description="是否有效")
    created_at: str = Field(default_factory=_now, description="创建时间")
    updated_at: str = Field(default_factory=_now, description="更新时间")


class DiagCaseLibraryMatchModel(BaseModel):
    case: DiagCaseLibraryModel = Field(..., description="命中的超节点诊断案例")
    match_score: float = Field(..., description="未归一化匹配分")
    score_norm: float = Field(..., description="按查询侧权重和归一化后的分数，0~1")
    matched_signals: list[DiagCaseLibrarySignalModel] = Field(
        default_factory=list, description="命中的结构化信号"
    )


# ============================================================
# 请求模型
# ============================================================
class CreateDiagCaseDraftRequest(StrictRequestModel):
    """建草稿请求；``case_no`` / ``search_text`` 由服务端生成，不接受外部传入。"""

    log_type: _LaxLogType = Field(..., description="日志类型：KVCache 或 UBSocket")
    source: DiagCaseSource = Field(
        ..., strict=False, description="案例来源：internal / community / online"
    )
    source_url: Optional[str] = Field(
        default=None, description="来源链接，source 为 community / online 时必填"
    )
    title: str = Field(..., min_length=1, description="案例标题")
    symptom_summary: str = Field(..., min_length=1, description="故障现象摘要，需可独立阅读")
    root_cause_summary: str = Field(..., min_length=1, description="一句话根因")
    root_cause_detail: Optional[str] = Field(default=None, description="根因机理长文")
    created_by: Optional[str] = Field(default=None, description="创建人（或 agent）标识")
    kb_id: Optional[str] = Field(
        default=None, description="来源知识库ID，可空表示全局案例（跨库可召回）"
    )
    kb_name: Optional[str] = Field(default=None, description="来源知识库名称")
    cluster_name: Optional[str] = Field(default=None, description="集群名称")
    hosts: list[str] = Field(default_factory=list, description="主机名")
    pods: list[str] = Field(default_factory=list, description="Pod 名")
    src_ips: list[str] = Field(default_factory=list, description="源 IP")
    dst_ips: list[str] = Field(default_factory=list, description="目的 IP")
    node_type: Optional[str] = Field(default=None, description="超节点形态")
    version_json: Optional[VersionModel] = Field(default=None, description="版本快照")
    scope_limits: Optional[str] = Field(default=None, description="不适用场景，防误套用")
    operation: Optional[_LaxOperation] = Field(
        default=None, description="操作类型：GET / SET / N/A"
    )
    fault_type: FaultType = Field(
        default="unknown", description="故障类型：latency / connectivity / mixed / unknown"
    )
    status_codes: list[str] = Field(default_factory=list, description="关联状态码")
    failure_mode_ids: list[str] = Field(default_factory=list, description="关联故障模式ID")
    latency_components: list[str] = Field(
        default_factory=list, description="异常时延组件桶 key"
    )
    log_keywords: list[str] = Field(
        default_factory=list, description="现场关键日志原文短语"
    )
    stage_features_json: Optional[StageFeaturesModel] = Field(
        default=None, description="L2 阶段桶分布快照"
    )
    fault_shape: Optional[str] = Field(default=None, description="故障时间形状")
    time_window_json: Optional[TimeWindowModel] = Field(
        default=None, description="故障时间窗口"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="结论验证强度，0~1")
    evidence_json: list[EvidenceModel] = Field(default_factory=list, description="证据锚点")
    counter_evidence_json: list[dict[str, Any]] = Field(
        default_factory=list, description="已排除项"
    )
    remediation_json: list[RemediationStepModel] = Field(
        default_factory=list, description="分步处置"
    )
    verification_json: Optional[VerificationModel] = Field(
        default=None, description="验证闭环"
    )
    relations_json: list[RelationModel] = Field(default_factory=list, description="关联案例")
    source_log_ids: list[str] = Field(default_factory=list, description="来源日志ID")

    @model_validator(mode="after")
    def _require_source_url(self) -> "CreateDiagCaseDraftRequest":
        if self.source in (DiagCaseSource.COMMUNITY, DiagCaseSource.ONLINE) and not (
            self.source_url or ""
        ).strip():
            raise ValueError("source 为 community / online 时 source_url 必填")
        return self


class UpdateDiagCaseRequest(StrictRequestModel):
    """局部更新案例请求（§4.4）；字段集与建草稿一致，**全部可选**。

    接受的字段按当前状态分档：``draft`` 可改全部内容物；``confirmed`` 只放行
    ``verification_json``（处置闭环的事后证据）；``archived`` 全拒。
    未传字段保持不变（`exclude_unset` 语义），因此显式传空数组/空值才算清空。
    ``case_no`` / ``status`` / ``revision`` / ``created_by`` / ``confirmed_*`` /
    ``archived_*`` 等元信息不在本模型内，服务端不接受修改。
    ``source`` 为 community / online 时 `source_url` 的必填校验放在服务层，
    按「案例合并后的结果」判定，避免只改 `source` 时误伤已存在的 `source_url`。
    """

    log_type: Optional[_LaxLogType] = Field(
        default=None, description="日志类型：KVCache 或 UBSocket"
    )
    source: Optional[DiagCaseSource] = Field(
        default=None, strict=False, description="案例来源：internal / community / online"
    )
    source_url: Optional[str] = Field(default=None, description="来源链接")
    title: Optional[str] = Field(default=None, min_length=1, description="案例标题")
    symptom_summary: Optional[str] = Field(
        default=None, min_length=1, description="故障现象摘要，需可独立阅读"
    )
    root_cause_summary: Optional[str] = Field(
        default=None, min_length=1, description="一句话根因"
    )
    root_cause_detail: Optional[str] = Field(default=None, description="根因机理长文")
    kb_id: Optional[str] = Field(
        default=None, description="来源知识库ID，可空表示全局案例（跨库可召回）"
    )
    kb_name: Optional[str] = Field(default=None, description="来源知识库名称")
    cluster_name: Optional[str] = Field(default=None, description="集群名称")
    hosts: Optional[list[str]] = Field(default=None, description="主机名")
    pods: Optional[list[str]] = Field(default=None, description="Pod 名")
    src_ips: Optional[list[str]] = Field(default=None, description="源 IP")
    dst_ips: Optional[list[str]] = Field(default=None, description="目的 IP")
    node_type: Optional[str] = Field(default=None, description="超节点形态")
    version_json: Optional[VersionModel] = Field(default=None, description="版本快照")
    scope_limits: Optional[str] = Field(default=None, description="不适用场景，防误套用")
    operation: Optional[_LaxOperation] = Field(
        default=None, description="操作类型：GET / SET / N/A"
    )
    fault_type: Optional[FaultType] = Field(
        default=None, description="故障类型：latency / connectivity / mixed / unknown"
    )
    status_codes: Optional[list[str]] = Field(default=None, description="关联状态码")
    failure_mode_ids: Optional[list[str]] = Field(
        default=None, description="关联故障模式ID"
    )
    latency_components: Optional[list[str]] = Field(
        default=None, description="异常时延组件桶 key"
    )
    log_keywords: Optional[list[str]] = Field(
        default=None, description="现场关键日志原文短语"
    )
    stage_features_json: Optional[StageFeaturesModel] = Field(
        default=None, description="L2 阶段桶分布快照"
    )
    fault_shape: Optional[str] = Field(default=None, description="故障时间形状")
    time_window_json: Optional[TimeWindowModel] = Field(
        default=None, description="故障时间窗口"
    )
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="结论验证强度，0~1"
    )
    evidence_json: Optional[list[EvidenceModel]] = Field(
        default=None, description="证据锚点"
    )
    counter_evidence_json: Optional[list[dict[str, Any]]] = Field(
        default=None, description="已排除项"
    )
    remediation_json: Optional[list[RemediationStepModel]] = Field(
        default=None, description="分步处置"
    )
    verification_json: Optional[VerificationModel] = Field(
        default=None,
        description=(
            "验证闭环；报告阶段留空，处置执行 + 复测后才可回填 "
            "observed_result / closed_loop / verified_at，严禁臆造"
        ),
    )
    relations_json: Optional[list[RelationModel]] = Field(
        default=None, description="关联案例"
    )
    source_log_ids: Optional[list[str]] = Field(default=None, description="来源日志ID")


class ConfirmDiagCaseRequest(StrictRequestModel):
    """确认请求；``draft → confirmed`` 需通过 §4.2 确认闸门。"""

    confirmed_by: str = Field(..., min_length=1, description="确认人（或 agent）标识")
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="确认后的结论验证强度，缺省沿用草稿值"
    )


class ArchiveDiagCaseRequest(StrictRequestModel):
    """归档请求；``draft | confirmed → archived``，已归档案例幂等返回。"""

    archived_by: Optional[str] = Field(default=None, description="归档人标识")
    archive_reason: Optional[str] = Field(default=None, description="归档原因")


class SearchDiagCaseLibraryRequest(StrictRequestModel):
    """跨库检索请求；``kb_id`` 可空表示不过滤来源。"""

    operation: Optional[_LaxOperation] = Field(
        default=None, description="操作类型过滤：GET / SET / N/A"
    )
    log_type: Optional[_LaxLogType] = Field(
        default=None, description="日志类型过滤：KVCache / UBSocket"
    )
    fault_type: Optional[FaultType] = Field(default=None, description="故障类型过滤")
    kb_id: Optional[str] = Field(
        default=None, description="知识库ID，为空表示跨库召回（仍附带全局案例）"
    )
    status_codes: list[str] = Field(default_factory=list, description="待匹配状态码")
    failure_mode_ids: list[str] = Field(
        default_factory=list, description="待匹配故障模式ID"
    )
    src_ips: list[str] = Field(default_factory=list, description="待匹配源IP")
    dst_ips: list[str] = Field(default_factory=list, description="待匹配目的IP")
    hosts: list[str] = Field(default_factory=list, description="待匹配主机")
    pods: list[str] = Field(default_factory=list, description="待匹配Pod")
    clusters: list[str] = Field(default_factory=list, description="待匹配集群")
    latency_components: list[str] = Field(
        default_factory=list, description="待匹配异常时延组件"
    )
    log_keywords: list[str] = Field(default_factory=list, description="待匹配关键日志短语")
    min_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="最低案例置信度"
    )
    include_status: list[_LaxStatus] = Field(
        default_factory=lambda: [DiagCaseStatus.CONFIRMED],
        description="纳入检索的状态集合，默认只返回已确认案例",
    )
    page_cnt: int = Field(default=10, ge=1, description="每页数量")
    page_num: int = Field(default=1, ge=1, description="页码")


# ============================================================
# 响应模型
# ============================================================
class CreateDiagCaseDraftMsg(BaseModel):
    case_id: Optional[str] = Field(default=None, description="创建的超节点诊断案例ID")
    case_no: Optional[str] = Field(default=None, description="服务端生成的可读编号")


class CreateDiagCaseDraftResponse(ResponseBase):
    result: CreateDiagCaseDraftMsg = Field(..., description="创建超节点诊断案例草稿响应结果")


class GetDiagCaseMsg(BaseModel):
    case: Optional[DiagCaseLibraryModel] = Field(default=None, description="超节点诊断案例")


class GetDiagCaseResponse(ResponseBase):
    result: GetDiagCaseMsg = Field(..., description="获取超节点诊断案例详情响应结果")


class ConfirmDiagCaseResponse(ResponseBase):
    result: GetDiagCaseMsg = Field(..., description="确认超节点诊断案例响应结果")


class UpdateDiagCaseResponse(ResponseBase):
    result: GetDiagCaseMsg = Field(..., description="更新超节点诊断案例响应结果")


class ArchiveDiagCaseResponse(ResponseBase):
    result: GetDiagCaseMsg = Field(..., description="归档超节点诊断案例响应结果")


class HitDiagCaseResponse(ResponseBase):
    result: GetDiagCaseMsg = Field(..., description="命中超节点诊断案例响应结果")


class SearchDiagCasesMsg(BaseModel):
    total: int = Field(..., description="符合条件的超节点诊断案例总数")
    matches: list[DiagCaseLibraryMatchModel] = Field(
        default_factory=list, description="超节点诊断案例匹配列表"
    )


class SearchDiagCasesResponse(ResponseBase):
    result: SearchDiagCasesMsg = Field(..., description="检索超节点诊断案例响应结果")