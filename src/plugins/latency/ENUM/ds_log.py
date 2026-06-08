from enum import StrEnum, IntEnum


class OpType(StrEnum):
    """DS日志操作类型"""

    DS_KV_CLIENT_GET = "DS_KV_CLIENT_GET"
    DS_OBJECT_CLIENT_GET = "DS_OBJECT_CLIENT_GET"
    DS_POSIX_GET = "DS_POSIX_GET"


class StatusCode(IntEnum):
    """请求状态码"""

    OK = 0
