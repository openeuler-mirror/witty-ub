from enum import StrEnum


class SourceType(StrEnum):
    """数据来源类型"""

    LOCAL = "local"
    REMOTE = "remote"
    UPLOAD = "upload"


class DiagnosisConfigLogType(StrEnum):
    """日志类型，上传、解析和诊断配置共用。

    对外规范取值是 ``KVCache`` / ``UBSocket``；历史上前端/脚本还发过 ``kv-cache``、
    ``kvcache``、``ubsocket`` 这类写法，用 ``_missing_`` 统一归一化，避免为一个取值大小写
    把整条登记打成 422。
    """

    KVCACHE = "KVCache"
    UBSOCKET = "UBSocket"

    @classmethod
    def _missing_(cls, value):
        key = str(value).strip().lower().replace("-", "").replace("_", "")
        for member in cls:
            if member.value.lower() == key:
                return member
        return None


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


class InitStatus(StrEnum):
    """数据库初始化状态"""

    UNINITIALIZED = "uninitialized"
    SUCCESS = "success"
    FAILED = "failed"
