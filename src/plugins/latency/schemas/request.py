from pydantic import BaseModel, Field
from typing import Optional, Any


class CreateLogKnowledgeRequest(BaseModel):
    image_bytes: bytes = Field(..., description="知识相关的图片数据")
    name: str = Field(..., description="知识名称")
    description: str = Field(..., description="知识描述")


class UpdateLogKnowledgeRequest(BaseModel):
    image_bytes: Optional[bytes] = Field(default=None, description="知识相关的图片数据")
    name: Optional[str] = Field(default=None, description="知识名称")
    description: Optional[str] = Field(default=None, description="知识描述")


class ListLogKnowledgeRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="知识名称，支持模糊查询")
    description: Optional[str] = Field(
        default=None, description="知识描述，支持模糊查询"
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="知识创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="知识创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_sort: Optional[str] = Field(
        default=None,
        description="知识创建时间排序方式，asc表示升序，desc表示降序，默认为None表示不排序",
    )
    page: int = Field(default=1, description="页码，从1开始")
    page_size: int = Field(default=10, description="每页记录数，默认10条")
