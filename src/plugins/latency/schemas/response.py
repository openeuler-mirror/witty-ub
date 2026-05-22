from pydantic import BaseModel, Field
from typing import Optional, Any


class ResponseBase(BaseModel):
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    result: Any = Field(..., description="响应结果")


class UploadLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="上传日志文件的ID列表"
    )


class UploadLogFilesResponse(ResponseBase):
    result: UploadLogFilesMsg = Field(..., description="上传日志文件响应结果")
