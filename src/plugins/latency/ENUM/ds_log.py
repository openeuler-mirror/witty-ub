from enum import StrEnum, IntEnum


class OpType(StrEnum):
    """DS日志操作类型"""

    DS_KV_CLIENT_GET = "DS_KV_CLIENT_GET"
    DS_OBJECT_CLIENT_GET = "DS_OBJECT_CLIENT_GET"
    DS_POSIX_GET = "DS_POSIX_GET"


class AccessLogCol(IntEnum):
    """Access log按空格split后的列索引"""

    TIMESTAMP = 0
    TRACE_ID = 5
    STATUS_CODE = 7
    HANDLE = 8
    ELAPSED = 9
    SIZE = 10
    REQ_MSG = 11
    RESP_MSG = 12


class StatusCode(IntEnum):
    """请求状态码"""

    OK = 0
