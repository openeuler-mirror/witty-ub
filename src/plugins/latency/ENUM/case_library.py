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
    """案例对应的请求操作类型

    ``MIXED`` 表示整份报告同时覆盖 GET 与 SET、无法归属到单一操作；
    检索时按「GET / SET 都能命中」处理，而不是当成第三种操作取值。
    """

    GET = "GET"
    SET = "SET"
    NA = "N/A"
    MIXED = "MIXED"
