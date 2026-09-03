"""Business logic for per-knowledge-base diagnosis configuration."""

from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import NotFoundBizException
from latency.schemas.config import DiagnosisRuntimeConfig


class DiagnosisConfigService:
    @staticmethod
    async def _ensure_kb_exists(kb_id: str) -> None:
        if not await LogKnowledgePGManager.exists(kb_id):
            raise NotFoundBizException(resource="知识库")

    @staticmethod
    async def get(kb_id: str) -> DiagnosisRuntimeConfig:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        return await DiagnosisConfigPGManager.get_or_create(kb_id)

    @staticmethod
    async def update(
        kb_id: str, config: DiagnosisRuntimeConfig
    ) -> DiagnosisRuntimeConfig:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        return await DiagnosisConfigPGManager.upsert(kb_id, config)

    @staticmethod
    async def reset(kb_id: str) -> DiagnosisRuntimeConfig:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        return await DiagnosisConfigPGManager.reset(kb_id)
