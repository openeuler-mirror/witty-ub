from enum import StrEnum


class DiagCaseStatus(StrEnum):
    """超节点诊断案例库的审核状态机"""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    ARCHIVED = "archived"


class DiagCaseSource(StrEnum):
    """案例来源渠道"""

    INTERNAL = "internal"
    COMMUNITY = "community"
    ONLINE = "online"


class DiagCaseOperation(StrEnum):
    """案例对应的请求操作类型"""

    GET = "GET"
    SET = "SET"
    NA = "N/A"