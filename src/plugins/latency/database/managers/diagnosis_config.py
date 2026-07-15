import json
from datetime import datetime

from latency.config.config import Config
from latency.database.engine import AsyncSQLiteSingleton
from latency.schemas.config import DiagnosisRuntimeConfig


class DiagnosisConfigManager:
    """按资产库持久化诊断配置。"""

    @staticmethod
    def get_default_config() -> DiagnosisRuntimeConfig:
        return Config().get_default_diagnosis_config()

    @staticmethod
    async def get_or_create(kb_id: str) -> DiagnosisRuntimeConfig:
        rows = await AsyncSQLiteSingleton().execute_query(
            "SELECT config_json FROM diagnosis_config_table WHERE kb_id = :kb_id",
            {"kb_id": kb_id},
        )
        if rows:
            return DiagnosisRuntimeConfig.model_validate_json(rows[0]["config_json"])

        config = DiagnosisConfigManager.get_default_config()
        await DiagnosisConfigManager.upsert(kb_id, config)
        return config

    @staticmethod
    async def upsert(
        kb_id: str, config: DiagnosisRuntimeConfig
    ) -> DiagnosisRuntimeConfig:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            """
            INSERT INTO diagnosis_config_table (kb_id, config_json, created_at, updated_at)
            VALUES (:kb_id, :config_json, :created_at, :updated_at)
            ON CONFLICT(kb_id) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = excluded.updated_at
            """,
            {
                "kb_id": kb_id,
                "config_json": json.dumps(
                    config.model_dump(mode="json"), ensure_ascii=False
                ),
                "created_at": now,
                "updated_at": now,
            },
        )
        return config.model_copy(deep=True)

    @staticmethod
    async def reset(kb_id: str) -> DiagnosisRuntimeConfig:
        return await DiagnosisConfigManager.upsert(
            kb_id, DiagnosisConfigManager.get_default_config()
        )

    @staticmethod
    async def delete(kb_id: str) -> bool:
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            "DELETE FROM diagnosis_config_table WHERE kb_id = :kb_id",
            {"kb_id": kb_id},
        )
        return success
