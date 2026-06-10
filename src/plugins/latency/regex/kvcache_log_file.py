"""日志文件匹配模式 - 支持从配置文件读取"""

# 默认模式（当配置文件未设置时使用）
_DEFAULT_SDK_ACCESS_LOG_PATTERNS = [
    "SDK_*/ds_client_access_*.log",
    "SDK_*/ds_client_access_*.log.gz",
    "SDK_*/ds_client.log",
    "SDK_*/ds_client.log.gz",
    "SDK_*/ds_client_access.log",
    "SDK_*/ds_client_access.*.log.gz",
]

_DEFAULT_WORKER_ACCESS_LOG_PATTERNS = [
    "*worker_*/access.log",
    "*worker_*/access.log.gz",
]

_DEFAULT_WORKER_INFO_LOG_PATTERNS = [
    "*worker_*/datasystem_worker.INFO.*",
    "*worker_*/datasystem_worker.INFO.*.gz",
    "*worker_*/kvcache.INFO.*",
    "*worker_*/kvcache.INFO.*.gz",
]


def _load_patterns():
    """从配置文件加载日志文件匹配模式"""
    try:
        from latency.config.config import Config

        config = Config().get_config()
        ds_log_config = config.ds_log_analyzer

        # ds-client-access-log-file + ds-client-info-log-file -> SDK_ACCESS_LOG_PATTERNS
        sdk_access_patterns = ds_log_config.ds_client_access_log_file.copy()
        if ds_log_config.ds_client_info_log_file:
            sdk_access_patterns.extend(ds_log_config.ds_client_info_log_file)

        # ds-worker-access-log-file -> WORKER_ACCESS_LOG_PATTERNS
        worker_access_patterns = ds_log_config.ds_worker_access_log_file.copy()

        # ds-worker-info-log-file -> URMA_LOG_PATTERNS, REMOTE_PULL_LOG_PATTERNS, LINK_LOG_PATTERNS, QUERY_META_LOG_PATTERNS
        worker_info_patterns = ds_log_config.ds_worker_info_log_file.copy()

        return (
            sdk_access_patterns if sdk_access_patterns else _DEFAULT_SDK_ACCESS_LOG_PATTERNS,
            worker_access_patterns if worker_access_patterns else _DEFAULT_WORKER_ACCESS_LOG_PATTERNS,
            worker_info_patterns if worker_info_patterns else _DEFAULT_WORKER_INFO_LOG_PATTERNS,
        )
    except Exception:
        # 配置加载失败时使用默认值
        return (
            _DEFAULT_SDK_ACCESS_LOG_PATTERNS,
            _DEFAULT_WORKER_ACCESS_LOG_PATTERNS,
            _DEFAULT_WORKER_INFO_LOG_PATTERNS,
        )


SDK_ACCESS_LOG_PATTERNS, WORKER_ACCESS_LOG_PATTERNS, WORKER_INFO_LOG_PATTERNS = _load_patterns()

# 以下变量保持向后兼容，均使用Worker信息日志模式
URMA_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
REMOTE_PULL_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
LINK_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
QUERY_META_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS