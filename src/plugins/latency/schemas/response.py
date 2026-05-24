from pydantic import BaseModel, Field
from typing import Optional, Any
from latency.schemas.log import (
    LogKnowledgeModel,
    LogFileModel,
    src_dst_aggregated_eventModel,
)


class ResponseBase(BaseModel):
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    result: Any = Field(..., description="响应结果")


class CreateLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="创建的知识ID")


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


class CreateLogKnowledgeResponse(ResponseBase):
    result: CreateLogKnowledgeMsg = Field(..., description="创建日志知识响应结果")


class UploadLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="上传日志文件的ID列表"
    )


class UploadLogFilesResponse(ResponseBase):
    result: UploadLogFilesMsg = Field(..., description="上传日志文件响应结果")
