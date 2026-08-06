from enum import StrEnum, IntEnum


class OpType(StrEnum):
    """DS日志操作类型"""

    DS_KV_CLIENT_GET = "DS_KV_CLIENT_GET"
    DS_OBJECT_CLIENT_GET = "DS_OBJECT_CLIENT_GET"
    DS_POSIX_GET = "DS_POSIX_GET"
    DS_KV_CLIENT_SET = "DS_KV_CLIENT_SET"
    DS_POSIX_CREATE = "DS_POSIX_CREATE"
    DS_POSIX_PUBLISH = "DS_POSIX_PUBLISH"


class StatusCode(IntEnum):
    """请求状态码"""

    OK = 0


class EntryType(StrEnum):
    """日志条目类型"""

    SDK_GET = "SDK_GET"
    WORKER_GET = "WORKER_GET"
    SDK_SET = "SDK_SET"
    WORKER_CREATE = "WORKER_CREATE"
    WORKER_PUBLISH = "WORKER_PUBLISH"
    URMA = "URMA"
    REMOTE_PULL = "REMOTE_PULL"
    LINK = "LINK"
    QUERY_META = "QUERY_META"
    # 新增时延指标类型
    SDK_PROCESS = "SDK_PROCESS"
    SDK_RPC = "SDK_RPC"
    LOCAL_WORKER_COST = "LOCAL_WORKER_COST"
    LOCAL_WORKER_LOCK = "LOCAL_WORKER_LOCK"
    REMOTE_WORKER_COST = "REMOTE_WORKER_COST"
    REMOTE_WORKER_RPC = "REMOTE_WORKER_RPC"
    MASTER_PROCESS = "MASTER_PROCESS"
    MASTER_RPC = "MASTER_RPC"
    CLIENT_RPC = "CLIENT_RPC"


class TupleField(IntEnum):
    """序列化 tuple 的字段索引（与 _serialize_entry 定义的顺序一致）"""

    TIMESTAMP = 0       # 时间戳
    OPERATION = 1       # 操作类型
    ELAPSED_US = 2      # 耗时（微秒）
    DATA_SIZE = 3       # 数据大小
    OBJECT_KEY = 4      # 对象键
    TRACE_ID = 5        # 追踪ID
    POD_IP = 6          # Pod IP
    STATUS_CODE = 7     # 状态码
    RESP_MSG = 8        # 响应消息
    ENTRY_TYPE = 9      # 条目类型
    CLUSTER_NAME = 10   # 集群名称
    SRC_ADDR = 11       # 源地址
    DST_ADDR = 12       # 目标地址
    INFLIGHT_COUNT = 13 # 在飞请求数
    REQUEST_SIZE = 14   # 请求大小
    LOG_ID = 15         # 日志ID
