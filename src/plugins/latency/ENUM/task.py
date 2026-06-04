from enum import Enum, StrEnum


class TaskTypeEnum(StrEnum):
    KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"
    KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER = "kv_cache_log_event_diagnosis_worker"


class TaskStatusEnum(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESSFUL_PENDING_REMOVE = "successful_pending_remove"
    FAILED_PENDING_REMOVE = "failed_pending_remove"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class TaskSplitStrategy(Enum):
    """任务分组策略"""
    BY_FILE_SIZE = "file_size"      # 按文件大小加权（推荐）
    BY_FILE_COUNT = "file_count"    # 按文件数量平均
    BY_PARSER_COUNT = "parser_count" # 按解析器数量加权
