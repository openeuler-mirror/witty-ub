from enum import StrEnum


class SourceType(StrEnum):
    """数据来源类型"""

    LOCAL = "local"
    REMOTE = "remote"
    UPLOAD = "upload"


class LogLevel(StrEnum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OnlineStatus(StrEnum):
    """在线状态"""

    ONLINE = "online"
    OFFLINE = "offline"


class FilePath(StrEnum):
    """文件路径"""

    FILE_UPLOAD_PATH = "latency/file/file_upload/"
    FILE_PARSE_RESULT_PATH = "latency/file/file_parse_result/"
