# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for diagnosis_config."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from latency.config.config import Config
from latency.database.engine import PGManager
from latency.database.models import DiagnosisConfig
from latency.schemas.config import DiagnosisRuntimeConfig


class DiagnosisConfigPGManager:
    @staticmethod
    def get_default_config() -> DiagnosisRuntimeConfig:
        return Config().get_default_diagnosis_config()

    @staticmethod
    async def get_or_create(kb_id: str) -> DiagnosisRuntimeConfig:
        async with PGManager.session() as session:
            result = await session.execute(
                select(DiagnosisConfig.config_json).where(DiagnosisConfig.kb_id == kb_id)
            )
            row = result.scalar_one_or_none()
        if row:
            return DiagnosisRuntimeConfig.model_validate(row)

        config = DiagnosisConfigPGManager.get_default_config()
        await DiagnosisConfigPGManager.upsert(kb_id, config)
        return config

    @staticmethod
    async def upsert(
        kb_id: str, config: DiagnosisRuntimeConfig
    ) -> DiagnosisRuntimeConfig:
        now = datetime.now()
        mapping = {
            "kb_id": kb_id,
            "config_json": config.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }
        async with PGManager.session() as session:
            await session.execute(
                insert(DiagnosisConfig)
                .values(mapping)
                .on_conflict_do_update(
                    index_elements=[DiagnosisConfig.kb_id],
                    set_={
                        "config_json": mapping["config_json"],
                        "updated_at": mapping["updated_at"],
                    },
                )
            )
        return config.model_copy(deep=True)

    @staticmethod
    async def reset(kb_id: str) -> DiagnosisRuntimeConfig:
        return await DiagnosisConfigPGManager.upsert(
            kb_id, DiagnosisConfigPGManager.get_default_config()
        )

    @staticmethod
    async def delete(kb_id: str) -> bool:
        async with PGManager.session() as session:
            result = await session.execute(
                DiagnosisConfig.__table__.delete().where(DiagnosisConfig.kb_id == kb_id)
            )
        return (result.rowcount or 0) > 0
