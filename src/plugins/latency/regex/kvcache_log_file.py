SDK_ACCESS_LOG_PATTERNS = [
    "SDK_*/ds_client_access_*.log",
    "SDK_*/ds_client_access_*.log.gz",
    "SDK_*/ds_client.log",
    "SDK_*/ds_client.log.gz",
    "SDK_*/ds_client_access.log",
    "SDK_*/ds_client_access.*.log.gz",
]

WORKER_ACCESS_LOG_PATTERNS = [
    "*worker_*/access.log",
    "*worker_*/access.log.gz",
]

URMA_LOG_PATTERNS = [
    "*worker_*/datasystem_worker.INFO.*",
    "*worker_*/datasystem_worker.INFO.*.gz",
    "*worker_*/kvcache.INFO.*",
    "*worker_*/kvcache.INFO.*.gz",
]

REMOTE_PULL_LOG_PATTERNS = [
    "*worker_*/datasystem_worker.INFO.*",
    "*worker_*/datasystem_worker.INFO.*.gz",
    "*worker_*/kvcache.INFO.*",
    "*worker_*/kvcache.INFO.*.gz",
]

LINK_LOG_PATTERNS = [
    "*worker_*/datasystem_worker.INFO.*",
    "*worker_*/datasystem_worker.INFO.*.gz",
    "*worker_*/kvcache.INFO.*",
    "*worker_*/kvcache.INFO.*.gz",
]

QUERY_META_LOG_PATTERNS = [
    "*worker_*/datasystem_worker.INFO.*",
    "*worker_*/datasystem_worker.INFO.*.gz",
    "*worker_*/kvcache.INFO.*",
    "*worker_*/kvcache.INFO.*.gz",
]
