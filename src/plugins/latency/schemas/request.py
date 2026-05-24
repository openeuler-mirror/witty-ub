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
    created_at_sort: bool = Field(
        default=False,
        description="知识创建时间排序，True表示升序，False表示降序，默认为False",
    )
    page_cnt: int = Field(default=10, description="每页的知识数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class UpdateLogFileRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="日志文件名称")


class ListLogFileRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="日志文件名称，支持模糊查询")
    created_at_start: Optional[str] = Field(
        default=None,
        description="日志文件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="日志文件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_sort: bool = Field(
        default=False,
        description="日志文件创建时间排序，True表示升序，False表示降序，默认为False",
    )
    page_cnt: int = Field(default=10, description="每页的日志文件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListSrcDstAggregatedEventRequest(BaseModel):
    src_ip: Optional[str] = Field(default=None, description="源IP地址，支持模糊查询")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，支持模糊查询")
    created_at_start: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_sort: Optional[bool] = Field(
        default=None,
        description="聚合事件创建时间排序，True表示升序，False表示降序，None表示不排序",
    )
    page_cnt: int = Field(default=10, description="每页的聚合事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListAnomalousEventChainRequest(BaseModel):
    page_cnt: int = Field(default=10, description="每页的异常事件链数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListLogParseResultRequest(BaseModel):
    src_ip: Optional[str] = Field(default=None, description="源IP地址，支持模糊查询")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，支持模糊查询")
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="是否为异常解析结果，True表示异常，False表示正常，None表示不区分",
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_sort: Optional[bool] = Field(
        default=None,
        description="日志解析结果创建时间排序，True表示升序，False表示降序，None表示不排序",
    )
    page_cnt: int = Field(default=10, description="每页的日志解析结果数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")
