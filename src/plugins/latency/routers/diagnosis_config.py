from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from latency.ENUM.general import DiagnosisConfigLogType
from latency.schemas.config import DiagnosisConfigUpdate
from latency.schemas.response import DiagnosisConfigResponse
from latency.services.diagnosis_config import DiagnosisConfigService


router = APIRouter(prefix="/diagnosis_config", tags=["Diagnosis Config"])


async def require_configurable_log_type(
    log_type: Annotated[DiagnosisConfigLogType, Query(description="日志类型")],
) -> DiagnosisConfigLogType:
    """在解析 PUT 请求体前拒绝不支持配置的日志类型。"""
    DiagnosisConfigService.ensure_configurable(log_type)
    return log_type


@router.get("/{kb_id}", response_model=DiagnosisConfigResponse)
async def get_diagnosis_config(
    kb_id: str,
    log_type: Annotated[DiagnosisConfigLogType, Query(description="日志类型")],
) -> DiagnosisConfigResponse:
    """获取指定资产库的诊断配置；旧资产库会自动初始化默认配置。"""
    return DiagnosisConfigResponse(
        result=await DiagnosisConfigService.get(kb_id, log_type)
    )


@router.put("/{kb_id}", response_model=DiagnosisConfigResponse)
async def update_diagnosis_config(
    kb_id: str,
    log_type: Annotated[DiagnosisConfigLogType, Depends(require_configurable_log_type)],
    req: Annotated[DiagnosisConfigUpdate, Body()],
) -> DiagnosisConfigResponse:
    """更新指定资产库的配置，不写回原始 diagnosis_config.toml。"""
    return DiagnosisConfigResponse(
        result=await DiagnosisConfigService.update(kb_id, log_type, req)
    )


@router.post("/{kb_id}/reset", response_model=DiagnosisConfigResponse)
async def reset_diagnosis_config(
    kb_id: str,
    log_type: Annotated[DiagnosisConfigLogType, Depends(require_configurable_log_type)],
) -> DiagnosisConfigResponse:
    """使用服务启动时读取的可信原始配置快照恢复诊断配置。"""
    return DiagnosisConfigResponse(
        result=await DiagnosisConfigService.reset(kb_id, log_type)
    )
