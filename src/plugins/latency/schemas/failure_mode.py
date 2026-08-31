from typing import Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator


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
    error_code: Optional[str] = Field(None, description="错误码")

    @field_validator("error_code", mode="before")
    @classmethod
    def _coerce_error_code(cls, value: object) -> Optional[str]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    @field_serializer("error_code")
    def _serialize_error_code(self, value: Optional[str]) -> Optional[str]:
        return value if value else None
