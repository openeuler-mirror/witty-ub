# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""诊断报告库（/diagnostic_report）schema。

独立新增文件（设计文档 docs/design/diagnostic-report-library.md §6）：报告
清单一律来自报告目录（``$WITTY_REPORT_DIR``）下的侧车 JSON，不涉及数据库。
"""
from typing import Any, Optional

from pydantic import BaseModel, Field

from latency.schemas.parse_config import StrictRequestModel
from latency.schemas.response import ResponseBase

PAGE_CNT_MAX = 100


# ============================================================
# 请求模型
# ============================================================
class ListDiagnosticReportsRequest(StrictRequestModel):
    """报告列表请求（设计文档 §6.1）。"""
    kb_id: Optional[str] = Field(
        default=None, description="知识库ID过滤；为空表示跨库（返回全部知识库的报告）"
    )
    page_cnt: int = Field(
        default=20, ge=1, le=PAGE_CNT_MAX, description=f"每页条数（≤{PAGE_CNT_MAX}），默认20"
    )
    page_num: int = Field(default=1, ge=1, description="页码，默认1")


# ============================================================
# 响应模型
# ============================================================
class ClassificationModel(BaseModel):
    """Normalised two-level label result for one report fault."""

    first_level_label: Optional[str] = Field(default=None, description="一级分类")
    second_level_label: Optional[str] = Field(default=None, description="二级分类")
    status: str = Field(
        default="empty",
        description="empty / first_only / pair / invalid / unavailable",
    )
    error: Optional[str] = Field(default=None, description="非法原因")
    taxonomy_version: Optional[str] = Field(default=None, description="分类字典版本")
    snapshot_hash: Optional[str] = Field(default=None, description="分类快照哈希")


class FaultSummaryModel(BaseModel):
    """One fault in the report workbench; labels are never inferred client-side."""

    fault_id: Optional[str] = Field(default=None, description="稳定故障ID")
    title: Optional[str] = Field(default=None, description="故障标题")
    status: Optional[str] = Field(default=None, description="诊断状态")
    category: Optional[str] = Field(default=None, description="报告 category")
    confidence: Optional[float] = Field(default=None, description="置信度")
    classification: ClassificationModel = Field(
        default_factory=ClassificationModel, description="两级分类"
    )
    indexable: bool = Field(default=True, description="是否可作为案例来源")
    synthetic: bool = Field(default=False, description="是否为 auto: 合成键")
    excluded: bool = Field(default=False, description="是否被报告排除")


class DiagnosticCaseRefModel(BaseModel):
    """报告故障关联的案例引用。"""

    case_id: str = Field(..., description="案例ID")
    case_no: Optional[str] = Field(default=None, description="可读案例编号")
    source_fault_id: Optional[str] = Field(default=None, description="绑定故障ID")
    source_fault_hash: Optional[str] = Field(
        default=None, description="建案时的源故障版本哈希"
    )
    is_current_version: bool = Field(
        default=False, description="是否与当前报告故障指纹一致"
    )
    status: str = Field(..., description="draft / confirmed / archived")
    revision: int = Field(default=0, description="案例 revision，用于验证回填乐观锁")
    verification: str = Field(..., description="案例信任标签")
    binding_status: str = Field(..., description="valid / stale")
    first_level_label: Optional[str] = Field(default=None, description="案例一级分类快照")
    second_level_label: Optional[str] = Field(default=None, description="案例二级分类快照")
    verification_method: Optional[str] = Field(default=None, description="验证方法")
    observed_result: Optional[str] = Field(default=None, description="实测结果")
    closed_loop: bool = Field(default=False, description="是否已闭环")
    verified_by: Optional[str] = Field(default=None, description="验证人")
    verified_at: Optional[str] = Field(default=None, description="验证时间")


class DiagnosticReportItem(BaseModel):
    """报告条目：目录元信息 + 侧车 JSON 摘要 + 现象索引状态。

    侧车缺失（``has_sidecar=false``）时仅目录元信息可用，其余字段为 null。
    """
    source_name: Optional[str] = Field(default=None, description="历史资料来源")
    classifications: list[ClassificationModel] = Field(
        default_factory=list, description="所有非排除故障的分类；文档筛选按任一故障匹配、按文档去重"
    )
    validation_status: str = Field(
        default="unavailable", description="定界文档结论检验：pending / partial / validated / unavailable"
    )
    validated_fault_count: int = Field(default=0, description="当前文档已通过人工检验的唯一故障数")
    imported_by: Optional[str] = Field(default=None, description="导入经手人")
    report_id: str = Field(..., description="报告唯一标识（HTML 文件名去扩展名），用于详情与下发")
    kb_id: Optional[str] = Field(default=None, description="知识库ID（报告目录名；无侧车时为目录名兜底）")
    kb_name: Optional[str] = Field(default=None, description="知识库名称（侧车 basic_info）")
    title: Optional[str] = Field(default=None, description="报告标题（侧车 report.title）")
    generated_at: Optional[str] = Field(
        default=None, description="报告生成时间 YYYY-MM-DD HH:MM:SS（侧车 report.generated_at）"
    )
    operation: Optional[str] = Field(default=None, description="操作类型 GET / SET / MIXED / N/A")
    time_range_start: Optional[str] = Field(default=None, description="分析时间范围起点")
    time_range_end: Optional[str] = Field(default=None, description="分析时间范围终点")
    fault_count: Optional[int] = Field(
        default=None, description="故障数（faults 数组长度；扁平单故障取 conclusion.fault_count）"
    )
    file_name: str = Field(..., description="报告 HTML 文件名")
    file_size: int = Field(default=0, description="报告 HTML 字节数")
    has_sidecar: bool = Field(default=False, description="是否存在侧车 JSON（列表标题/故障数依赖它）")
    index_status: str = Field(
        default="unknown",
        description="indexed / partial / pending / failed / not_applicable / unknown",
    )
    index_error: Optional[str] = Field(default=None, description="聚合异常或侧车错误")
    status_counts: dict[str, int] = Field(
        default_factory=dict, description="有效卡片索引状态计数"
    )
    indexable_fault_count: Optional[int] = Field(
        default=None, description="非 excluded 故障数"
    )
    confirmed_fault_count: Optional[int] = Field(
        default=None, description="报告内 status=confirmed 故障数"
    )
    case_count: int = Field(default=0, description="当前版本有效绑定案例数")
    verified_case_count: int = Field(default=0, description="当前版本已闭环案例数")
    report_available: bool = Field(default=True, description="报告文件是否存在")
    review_status: str = Field(
        default="unconfirmed",
        description="unconfirmed / confirmed / stale / unavailable",
    )
    current_sidecar_hash: Optional[str] = Field(
        default=None, description="当前侧车规范化哈希"
    )
    review_confirmed_by: Optional[str] = Field(default=None, description="报告确认人")
    review_confirmed_at: Optional[str] = Field(default=None, description="报告确认时间")
    review_confirmation_source: Optional[str] = Field(
        default=None, description="确认来源：review（在线）/ import（历史导入）"
    )
    imported: bool = Field(
        default=False, description="是否为历史报告导入（文件名 report_hist_*）"
    )


class ListDiagnosticReportsMsg(BaseModel):
    total: int = Field(..., description="符合条件的报告总数")
    items: list[DiagnosticReportItem] = Field(default_factory=list, description="报告清单（生成时间倒序）")


class ListDiagnosticReportsResponse(ResponseBase):
    result: ListDiagnosticReportsMsg = Field(..., description="查询诊断报告列表响应结果")


class DiagnosticReportDetailItem(DiagnosticReportItem):
    """报告详情条目：在列表字段上增加关联案例引用与故障摘要。"""

    case_refs: list[DiagnosticCaseRefModel] = Field(
        default_factory=list, description="关联案例引用"
    )
    fault_summaries: list[FaultSummaryModel] = Field(
        default_factory=list, description="逐故障分类与可建案状态"
    )


class GetDiagnosticReportMsg(BaseModel):
    report: DiagnosticReportDetailItem = Field(..., description="报告元信息")
    data: Optional[dict[str, Any]] = Field(
        default=None, description="侧车 JSON 原文（渲染入参，可用于复现渲染）；缺侧车时为 null"
    )


class GetDiagnosticReportResponse(ResponseBase):
    result: GetDiagnosticReportMsg = Field(..., description="查询诊断报告详情响应结果")


class GetDiagnosticReportFaultMsg(BaseModel):
    report: DiagnosticReportDetailItem = Field(..., description="最小报告元信息")
    fault: dict[str, Any] = Field(..., description="目标故障原文")
    classification: ClassificationModel = Field(
        default_factory=ClassificationModel, description="规范化两级分类"
    )
    case_refs: list[DiagnosticCaseRefModel] = Field(
        default_factory=list, description="该故障的有效关联案例"
    )


class GetDiagnosticReportFaultResponse(ResponseBase):
    result: GetDiagnosticReportFaultMsg = Field(
        ..., description="查询单故障响应结果"
    )


class ReindexDiagnosticReportMsg(BaseModel):
    accepted: bool = Field(default=True, description="是否已受理")
    report_id: str = Field(..., description="报告ID")
    queued_count: int = Field(default=0, description="入队卡片数")
    index_status: Optional[str] = Field(default=None, description="报告聚合状态")


class ReindexDiagnosticReportResponse(ResponseBase):
    result: ReindexDiagnosticReportMsg = Field(..., description="报告重建受理结果")


class ConfirmDiagnosticReportRequest(StrictRequestModel):
    """整份报告人工确认；版本哈希必须与页面所见一致。"""

    expected_sidecar_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="页面所见的当前侧车规范化哈希",
    )
    reviewed_by: Optional[str] = Field(
        default=None, max_length=64, description="操作人；未填时读取 X-Witty-Operator"
    )


class ConfirmDiagnosticReportResponse(ResponseBase):
    result: DiagnosticReportDetailItem = Field(..., description="确认后的报告详情")


class LabelPairModel(BaseModel):
    first_level_label: str = Field(..., description="一级分类")
    second_level_labels: list[str] = Field(
        default_factory=list, description="该一级下的二级分类"
    )


class LabelTaxonomyMsg(BaseModel):
    version: str = Field(..., description="分类字典 sha256")
    first_level_labels: list[str] = Field(default_factory=list)
    pairs: list[LabelPairModel] = Field(default_factory=list)


class LabelTaxonomyResponse(ResponseBase):
    result: LabelTaxonomyMsg = Field(..., description="两级分类字典")


class ReportCasePreviewMsg(BaseModel):
    report_id: str = Field(..., description="报告ID")
    source_fault_id: str = Field(..., description="目标故障ID")
    expected_sidecar_hash: str = Field(..., description="建案所基于的侧车哈希")
    source_fault_hash: str = Field(..., description="目标故障指纹")
    classification: ClassificationModel = Field(
        default_factory=ClassificationModel, description="目标故障分类快照"
    )
    draft: dict[str, Any] = Field(default_factory=dict, description="预填案例草稿")
    missing_fields: list[str] = Field(
        default_factory=list, description="确认闸门尚缺字段"
    )
    ready: bool = Field(default=False, description="是否满足草稿创建条件")


class ReportCasePreviewResponse(ResponseBase):
    result: ReportCasePreviewMsg = Field(..., description="按故障建案预览")


class CreateCaseFromReportRequest(StrictRequestModel):
    """从已确认报告的指定故障生成案例草稿。"""

    expected_sidecar_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="页面所见的当前侧车规范化哈希",
    )
    reviewed_by: Optional[str] = Field(
        default=None, max_length=64, description="操作人；未填时读取 X-Witty-Operator"
    )


class CreateCaseFromReportMsg(BaseModel):
    case_id: Optional[str] = Field(default=None, description="生成的案例ID")
    case_no: Optional[str] = Field(default=None, description="可读案例编号")
    missing_fields: list[str] = Field(
        default_factory=list, description="草稿仍缺少的确认闸门字段"
    )


class CreateCaseFromReportResponse(ResponseBase):
    result: CreateCaseFromReportMsg = Field(..., description="报告派生案例草稿")