from pydantic import BaseModel, Field, field_serializer


class StatusCodeKnowledgeModel(BaseModel):
    status_code: str = Field(..., description="故障码")
    symptom: str = Field(..., description="故障现象")
    root_cause: str = Field(..., description="故障原因")


class FailureModeModel(BaseModel):
    id: str = Field(..., description="故障模式id")
    name: str = Field(..., description="故障模式名称")
    symptom: str = Field(..., description="故障表现")
    root_cause: str = Field(..., description="故障根因")
    solution: str = Field(..., description="解决方法")
    failure_domain: str = Field(..., description="故障域")
    children_failure_mode_ids: str = Field(..., description="子故障")
