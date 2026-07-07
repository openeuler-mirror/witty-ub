"""日志文件匹配模式 - 支持从配置文件读取"""

MIXED_ROTATED_GZ_PATTERN = "*.log_*.gz"


def include_gzip_patterns(patterns: list[str]) -> list[str]:
    """从文本日志规则派生 gzip 规则，并补充聚合轮转日志规则。"""
    result: list[str] = []
    for pattern in patterns:
        if pattern not in result:
            result.append(pattern)
        if pattern.lower().endswith(".log"):
            gzip_pattern = f"{pattern}.gz"
            if gzip_pattern not in result:
                result.append(gzip_pattern)
    if MIXED_ROTATED_GZ_PATTERN not in result:
        result.append(MIXED_ROTATED_GZ_PATTERN)
    return result


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
        filename_config = config.log_filename_pattern

        # Client access and info logs share the SDK parser set.
        # ds_client_access_log_file + ds_client_info_log_file -> SDK_ACCESS_LOG_PATTERNS
        sdk_access_patterns = filename_config.ds_client_access_log_file.copy()
        sdk_access_patterns.extend(filename_config.ds_client_info_log_file)

        # ds_worker_access_log_file -> WORKER_ACCESS_LOG_PATTERNS
        worker_access_patterns = filename_config.ds_worker_access_log_file.copy()

        # ds_worker_info_log_file -> URMA_LOG_PATTERNS, REMOTE_PULL_LOG_PATTERNS, LINK_LOG_PATTERNS, QUERY_META_LOG_PATTERNS
        worker_info_patterns = filename_config.ds_worker_info_log_file.copy()

        return (
            include_gzip_patterns(
                sdk_access_patterns or _DEFAULT_SDK_ACCESS_LOG_PATTERNS
            ),
            include_gzip_patterns(
                worker_access_patterns or _DEFAULT_WORKER_ACCESS_LOG_PATTERNS
            ),
            include_gzip_patterns(
                worker_info_patterns or _DEFAULT_WORKER_INFO_LOG_PATTERNS
            ),
        )
    except Exception:
        # 配置加载失败时使用默认值
        return (
            _DEFAULT_SDK_ACCESS_LOG_PATTERNS,
            _DEFAULT_WORKER_ACCESS_LOG_PATTERNS,
            _DEFAULT_WORKER_INFO_LOG_PATTERNS,
        )


def reload_patterns():
    """从当前运行时配置刷新所有向后兼容的 Pattern 列表。"""
    global SDK_ACCESS_LOG_PATTERNS
    global WORKER_ACCESS_LOG_PATTERNS
    global WORKER_INFO_LOG_PATTERNS
    global URMA_LOG_PATTERNS
    global REMOTE_PULL_LOG_PATTERNS
    global LINK_LOG_PATTERNS
    global QUERY_META_LOG_PATTERNS

    loaded = _load_patterns()
    # 原地更新，确保通过 from ... import 获取到列表的解析器也能看到新值。
    if "SDK_ACCESS_LOG_PATTERNS" in globals():
        SDK_ACCESS_LOG_PATTERNS[:] = loaded[0]
        WORKER_ACCESS_LOG_PATTERNS[:] = loaded[1]
        WORKER_INFO_LOG_PATTERNS[:] = loaded[2]
    else:
        SDK_ACCESS_LOG_PATTERNS = loaded[0]
        WORKER_ACCESS_LOG_PATTERNS = loaded[1]
        WORKER_INFO_LOG_PATTERNS = loaded[2]

    URMA_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
    REMOTE_PULL_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
    LINK_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS
    QUERY_META_LOG_PATTERNS = WORKER_INFO_LOG_PATTERNS


reload_patterns()
