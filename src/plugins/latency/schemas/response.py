from pydantic import BaseModel, Field
from typing import Optional, Any
from latency.schemas.log import (
    LogKnowledgeModel,
    LogFileModel,
    SrcDstAggregatedEventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
)


class ResponseBase(BaseModel):
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    result: Any = Field(..., description="响应结果")


class CreateLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="创建的知识ID")


class CreateLogKnowledgeResponse(ResponseBase):
    result: CreateLogKnowledgeMsg = Field(..., description="创建日志知识响应结果")


class DeleteLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="删除的知识ID")


class DeleteLogKnowledgeResponse(ResponseBase):
    result: DeleteLogKnowledgeMsg = Field(..., description="删除日志知识响应结果")


class UpdateLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="更新的知识ID")


class UpdateLogKnowledgeResponse(ResponseBase):
    result: UpdateLogKnowledgeMsg = Field(..., description="更新日志知识响应结果")


class ListLogKnowledgeMsg(BaseModel):
    total: int = Field(..., description="符合条件的知识总数")
    kbs: list[LogKnowledgeModel] = Field(default_factory=list, description="知识列表")


class ListLogKnowledgeResponse(ResponseBase):
    result: ListLogKnowledgeMsg = Field(..., description="查询日志知识列表响应结果")


class GetLogKnowledgeMsg(BaseModel):
    kb: Optional[LogKnowledgeModel] = Field(default=None, description="知识详情")


class GetLogKnowledgeResponse(ResponseBase):
    result: GetLogKnowledgeMsg = Field(..., description="查询日志知识详情响应结果")


class UploadLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="上传日志文件的ID列表"
    )


class UploadLogFilesResponse(ResponseBase):
    result: UploadLogFilesMsg = Field(..., description="上传日志文件响应结果")


class DeleteLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="删除日志文件的ID列表"
    )


class DeleteLogFilesResponse(ResponseBase):
    result: DeleteLogFilesMsg = Field(..., description="删除日志文件响应结果")


class UpdateLogFileMsg(BaseModel):
    log_file_id: Optional[str] = Field(default=None, description="更新的日志文件ID")


class UpdateLogFileResponse(ResponseBase):
    result: UpdateLogFileMsg = Field(..., description="更新日志文件响应结果")


class ListLogFilesMsg(BaseModel):
    total: int = Field(..., description="符合条件的日志文件总数")
    log_files: list[LogFileModel] = Field(
        default_factory=list, description="日志文件列表"
    )


class ListLogFilesResponse(ResponseBase):
    result: ListLogFilesMsg = Field(..., description="查询日志文件列表响应结果")


class GetLogFileMsg(BaseModel):
    log_file: Optional[LogFileModel] = Field(default=None, description="日志文件详情")


class GetLogFileResponse(ResponseBase):
    result: GetLogFileMsg = Field(..., description="查询日志文件详情响应结果")


class ListSrcDstAggregatedEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的聚合事件总数")
    events: list[SrcDstAggregatedEventModel] = Field(
        default_factory=list, description="聚合事件列表"
    )


class ListSrcDstAggregatedEventResponse(ResponseBase):
    result: ListSrcDstAggregatedEventMsg = Field(
        ..., description="查询聚合事件列表响应结果"
    )


class GetSrcDstAggregatedEventMsg(BaseModel):
    event: Optional[SrcDstAggregatedEventModel] = Field(
        default=None, description="聚合事件详情"
    )


class GetSrcDstAggregatedEventResponse(ResponseBase):
    result: GetSrcDstAggregatedEventMsg = Field(
        ..., description="查询聚合事件详情响应结果"
    )


class GetAnomalousEventMsg(BaseModel):
    event: Optional[AnomalousEventModel] = Field(
        default=None, description="异常事件详情"
    )


class GetAnomalousEventResponse(ResponseBase):
    result: GetAnomalousEventMsg = Field(..., description="查询异常事件详情响应结果")


class ListAnomalousEventChainsMsg(BaseModel):
    total: int = Field(..., description="符合条件的异常事件链总数")
    event_chains: list[AnomalousEventChainModel] = Field(
        default_factory=list, description="异常事件链列表"
    )


class ListAnomalousEventChainsResponse(ResponseBase):
    result: ListAnomalousEventChainsMsg = Field(
        ..., description="查询异常事件链列表响应结果"
    )


class ListLogParseResultsMsg(BaseModel):
    total: int = Field(..., description="符合条件的日志解析结果总数")
    log_parse_results: list[LogParseResultModel] = Field(
        default_factory=list, description="日志解析结果列表"
    )


class ListLogParseResultsResponse(ResponseBase):
    result: ListLogParseResultsMsg = Field(
        ..., description="查询日志解析结果列表响应结果"
    )


class StopOrRunLogParseMsg(BaseModel):
    success: bool = Field(..., description="操作是否成功")


class StopOrRunLogParseResponse(ResponseBase):
    result: StopOrRunLogParseMsg = Field(..., description="停止或运行日志解析响应结果")
