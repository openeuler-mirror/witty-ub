from typing import Annotated

from fastapi import APIRouter, Body

from latency.schemas.config import DiagnosisRuntimeConfig
from latency.schemas.response import ResponseBase
from latency.services.diagnosis_config import DiagnosisConfigService


router = APIRouter(prefix="/diagnosis_config", tags=["Diagnosis Config"])


@router.get("/{kb_id}", response_model=ResponseBase)
async def get_diagnosis_config(kb_id: str) -> ResponseBase:
    """获取指定资产库的诊断配置；旧资产库会自动初始化默认配置。"""
    return ResponseBase(result=await DiagnosisConfigService.get(kb_id))


@router.put("/{kb_id}", response_model=ResponseBase)
async def update_diagnosis_config(
    kb_id: str,
    req: Annotated[DiagnosisRuntimeConfig, Body()],
) -> ResponseBase:
    """更新指定资产库的配置，不写回原始 diagnosis_config.toml。"""
    return ResponseBase(result=await DiagnosisConfigService.update(kb_id, req))


@router.post("/{kb_id}/reset", response_model=ResponseBase)
async def reset_diagnosis_config(kb_id: str) -> ResponseBase:
    """使用服务启动时读取的可信原始配置快照恢复诊断配置。"""
    return ResponseBase(result=await DiagnosisConfigService.reset(kb_id))
