"""Business logic for per-knowledge-base diagnosis configuration."""

from latency.ENUM.general import DiagnosisConfigLogType
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.schemas.config import (
    DiagnosisConfigResult,
    DiagnosisConfigUpdate,
    DiagnosisRuntimeConfig,
    KVCacheDiagnosisConfig,
    KVCacheLogFilenamePatternConfig,
    UBSocketDiagnosisConfig,
    UBSocketLogFilenamePatternConfig,
)


class DiagnosisConfigService:
    UBSOCKET_CONFIG_UNSUPPORTED = "UBSocket日志解析暂不支持配置"

    @staticmethod
    async def _ensure_kb_exists(kb_id: str) -> None:
        if not await LogKnowledgePGManager.exists(kb_id):
            raise NotFoundBizException(resource="知识库")

    @staticmethod
    def ensure_configurable(log_type: DiagnosisConfigLogType) -> None:
        if log_type == DiagnosisConfigLogType.UBSOCKET:
            raise BadRequestBizException(
                message=DiagnosisConfigService.UBSOCKET_CONFIG_UNSUPPORTED
            )

    @staticmethod
    def _select_config(
        config: DiagnosisRuntimeConfig, log_type: DiagnosisConfigLogType
    ) -> KVCacheDiagnosisConfig | UBSocketDiagnosisConfig:
        patterns = config.log_filename_pattern
        if log_type == DiagnosisConfigLogType.KVCACHE:
            return KVCacheDiagnosisConfig(
                log_filename_pattern=KVCacheLogFilenamePatternConfig(
                    ds_client_access_log_file=patterns.ds_client_access_log_file,
                    ds_client_info_log_file=patterns.ds_client_info_log_file,
                    ds_worker_access_log_file=patterns.ds_worker_access_log_file,
                    ds_worker_info_log_file=patterns.ds_worker_info_log_file,
                    resource_log_file=patterns.resource_log_file,
                ),
                log_analyzer_params=config.log_analyzer_params,
            )
        return UBSocketDiagnosisConfig(
            log_filename_pattern=UBSocketLogFilenamePatternConfig(
                brpc_log_file_patterns=patterns.brpc_log_file_patterns
            )
        )

    @staticmethod
    def _merge_config(
        current: DiagnosisRuntimeConfig,
        update: DiagnosisConfigUpdate,
    ) -> DiagnosisRuntimeConfig:
        if not isinstance(update, KVCacheDiagnosisConfig):
            raise BadRequestBizException(message="log_type 与配置项不匹配")
        merged = current.model_dump(mode="python")
        merged["log_filename_pattern"].update(
            update.log_filename_pattern.model_dump(mode="python")
        )
        merged["log_analyzer_params"] = update.log_analyzer_params.model_dump(
            mode="python"
        )
        return DiagnosisRuntimeConfig.model_validate(merged)

    @staticmethod
    def _result(
        config: DiagnosisRuntimeConfig, log_type: DiagnosisConfigLogType
    ) -> DiagnosisConfigResult:
        return DiagnosisConfigResult(
            log_type=log_type,
            config=DiagnosisConfigService._select_config(config, log_type),
        )

    @staticmethod
    async def get(
        kb_id: str, log_type: DiagnosisConfigLogType
    ) -> DiagnosisConfigResult:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        config = await DiagnosisConfigPGManager.get_or_create(kb_id)
        return DiagnosisConfigService._result(config, log_type)

    @staticmethod
    async def update(
        kb_id: str,
        log_type: DiagnosisConfigLogType,
        update: DiagnosisConfigUpdate,
    ) -> DiagnosisConfigResult:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        DiagnosisConfigService.ensure_configurable(log_type)
        current = await DiagnosisConfigPGManager.get_or_create(kb_id)
        config = DiagnosisConfigService._merge_config(current, update)
        saved = await DiagnosisConfigPGManager.upsert(kb_id, config)
        return DiagnosisConfigService._result(saved, log_type)

    @staticmethod
    async def reset(
        kb_id: str, log_type: DiagnosisConfigLogType
    ) -> DiagnosisConfigResult:
        await DiagnosisConfigService._ensure_kb_exists(kb_id)
        DiagnosisConfigService.ensure_configurable(log_type)
        current = await DiagnosisConfigPGManager.get_or_create(kb_id)
        default = DiagnosisConfigPGManager.get_default_config()
        default_group = DiagnosisConfigService._select_config(default, log_type)
        config = DiagnosisConfigService._merge_config(current, default_group)
        saved = await DiagnosisConfigPGManager.upsert(kb_id, config)
        return DiagnosisConfigService._result(saved, log_type)
