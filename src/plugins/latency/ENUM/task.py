from enum import StrEnum


class TaskTypeEnum(StrEnum):
    KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"


class TaskStatusEnum(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESSFUL_PENDING_REMOVE = "successful_pending_remove"
    FAILED_PENDING_REMOVE = "failed_pending_remove"
    SUCCESSFUL = "successful"
    FAILED = "failed"
