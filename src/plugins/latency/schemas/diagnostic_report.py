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
class DiagnosticReportItem(BaseModel):
    """报告条目：目录元信息 + 侧车 JSON 摘要。

    侧车缺失（``has_sidecar=false``）时仅目录元信息可用，其余字段为 null。
    """
    report_id: str = Field(..., description="报告唯一标识（HTML 文件名去扩展名），用于详情与下发")
    kb_id: Optional[str] = Field(default=None, description="知识库ID（报告目录名；无侧车时为目录名兜底）")
    kb_name: Optional[str] = Field(default=None, description="知识库名称（侧车 basic_info）")
    title: Optional[str] = Field(default=None, description="报告标题（侧车 report.title）")
    generated_at: Optional[str] = Field(
        default=None, description="报告生成时间 YYYY-MM-DD HH:MM:SS（侧车 report.generated_at）"
    )
    operation: Optional[str] = Field(default=None, description="操作类型 GET / SET")
    time_range_start: Optional[str] = Field(default=None, description="分析时间范围起点")
    time_range_end: Optional[str] = Field(default=None, description="分析时间范围终点")
    fault_count: Optional[int] = Field(
        default=None, description="故障数（faults 数组长度；扁平单故障取 conclusion.fault_count）"
    )
    file_name: str = Field(..., description="报告 HTML 文件名")
    file_size: int = Field(default=0, description="报告 HTML 字节数")
    has_sidecar: bool = Field(default=False, description="是否存在侧车 JSON（列表标题/故障数依赖它）")


class ListDiagnosticReportsMsg(BaseModel):
    total: int = Field(..., description="符合条件的报告总数")
    items: list[DiagnosticReportItem] = Field(default_factory=list, description="报告清单（生成时间倒序）")


class ListDiagnosticReportsResponse(ResponseBase):
    result: ListDiagnosticReportsMsg = Field(..., description="查询诊断报告列表响应结果")


class GetDiagnosticReportMsg(BaseModel):
    report: DiagnosticReportItem = Field(..., description="报告元信息")
    data: Optional[dict[str, Any]] = Field(
        default=None, description="侧车 JSON 原文（渲染入参，可用于复现渲染）；缺侧车时为 null"
    )


class GetDiagnosticReportResponse(ResponseBase):
    result: GetDiagnosticReportMsg = Field(..., description="查询诊断报告详情响应结果")