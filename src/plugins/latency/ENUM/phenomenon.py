# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Enums for the phenomenon index."""
from enum import StrEnum


class PhenomenonKind(StrEnum):
    """卡片初始来源。"""

    REPORT = "report"
    CASE = "case"
    LEGACY_CASE = "legacy_case"


class PhenomenonContentSource(StrEnum):
    """当前检索文本的数据来源；报告删除后可由 report 切为 case。"""

    REPORT = "report"
    CASE = "case"
    LEGACY_CASE = "legacy_case"


class PhenomenonIndexStatus(StrEnum):
    """单张卡片的索引同步进度。"""

    PENDING = "pending"
    PARSING = "parsing"
    INDEXED = "indexed"
    FAILED = "failed"
    STALE = "stale"
    DELETED = "deleted"


class ReportIndexStatus(StrEnum):
    """报告级聚合索引状态。"""

    PENDING = "pending"
    PARTIAL = "partial"
    INDEXED = "indexed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class VerificationLevel(StrEnum):
    """卡片信任标签，按查询时业务状态实时派生。"""

    VERIFIED = "verified"
    CONFIRMED_UNVERIFIED = "confirmed_unverified"
    REPORT_ONLY = "report_only"
    LEGACY_UNVERIFIED = "legacy_unverified"
    TASK_OBSERVED = "task_observed"
    SUSPECTED = "suspected"


class BindingStatus(StrEnum):
    """案例与报告故障当前版本的绑定状态。"""

    NONE = "none"
    VALID = "valid"
    STALE = "stale"


class IndexEventType(StrEnum):
    """业务状态变更事件。"""

    CASE_CONFIRMED = "case_confirmed"
    CASE_ARCHIVED = "case_archived"
    CASE_VERIFICATION = "case_verification"
    REPORT_DELETED = "report_deleted"
    LEGACY_CHANGED = "legacy_changed"


class IndexEventStatus(StrEnum):
    """outbox 事件消费状态。"""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class RagCleanupStatus(StrEnum):
    """RAG 文档清理任务状态。"""

    OBSERVING = "observing"
    PENDING = "pending"
    DELETING = "deleting"
    DONE = "done"
