import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum


class TaskReportModel(BaseModel):
    task_id: str = Field(..., description="任务ID")
    progress: float = Field(..., description="任务进度百分比")
    message: str | None = Field(default=None, description="任务状态消息")
    existed_status: bool = Field(
        True, description="任务报告是否存在的状态，默认为True表示存在"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="任务报告创建时间",
    )


class TaskModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务ID")
    kb_id: str = Field(default="", description="所属知识库ID")
    op_id: str = Field(default="", description="任务相关的操作ID")
    retry_times: int = Field(default=0, description="任务重试次数")
    task_name: str = Field(..., description="任务名称")
    task_type: TaskTypeEnum = Field(..., description="任务类型")
    task_reports: list[TaskReportModel] = Field(
        default_factory=list, description="任务进度报告列表"
    )
    status: TaskStatusEnum = Field(..., description="任务状态")
    existed_status: bool = Field(
        True, description="任务是否存在的状态，默认为True表示存在"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="任务创建时间"
    )
