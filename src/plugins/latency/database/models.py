# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL ORM models for latency plugin.

Design choices:
- SrcDstAggregatedEvent table keeps only dimensions and counts.  All
  percentile/min/max/ave values are computed on the fly from log_parse_result
  via PostgreSQL ordered-set aggregates / window functions.
- pod_ips is stored as TEXT[] with a GIN index; the legacy trigger-maintained
  junction table is removed.
- IP columns use PostgreSQL INET type.
- Timestamps use TIMESTAMP (naive, no timezone conversion).
- JSON columns use JSONB.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Identity,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ============================================================
# 1. 元数据表
# ============================================================
class LogKnowledge(Base):
    __tablename__ = "log_knowledge"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_bytes: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    anomalous_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    trace_failure_event_cnt: Mapped[int] = mapped_column(Integer, default=0)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(), onupdate=lambda: datetime.now()
    )


class DiagnosisConfig(Base):
    __tablename__ = "diagnosis_config"

    kb_id: Mapped[str] = mapped_column(String, primary_key=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(), onupdate=lambda: datetime.now()
    )


class LogFile(Base):
    __tablename__ = "log_file"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kb_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    parse_status: Mapped[Optional[str]] = mapped_column(String)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    size: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    anomalous_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(), onupdate=lambda: datetime.now()
    )


# ============================================================
# 2. 核心大表: log_parse_result
#    按 log_id HASH 分区
# ============================================================
class LogParseResult(Base):
    """日志解析结果表，按 log_id HASH 分区。"""

    __tablename__ = "log_parse_result"
    __table_args__ = (
        {"postgresql_partition_by": "HASH (log_id)"},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    log_id: Mapped[str] = mapped_column(String, primary_key=True)
    aggregated_event_id: Mapped[str] = mapped_column(String, default="")
    anomalous_event_id: Mapped[str] = mapped_column(String, default="")
    trace_id: Mapped[Optional[str]] = mapped_column(String)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    src_ip: Mapped[Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]] = mapped_column(INET)
    dst_ip: Mapped[Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]] = mapped_column(INET)
    pod_ips: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    cluster_name: Mapped[Optional[str]] = mapped_column(String)
    host: Mapped[Optional[str]] = mapped_column(String)
    total_latency: Mapped[Optional[float]] = mapped_column(Float)
    c2w_latency: Mapped[Optional[float]] = mapped_column(Float)
    worker_query_meta_latency: Mapped[Optional[float]] = mapped_column(Float)
    urma_total_latency: Mapped[Optional[float]] = mapped_column(Float)
    urma_link_latency: Mapped[Optional[float]] = mapped_column(Float)
    urma_inflight_count: Mapped[Optional[int]] = mapped_column(Integer)
    c2w_urma_latency: Mapped[Optional[float]] = mapped_column(Float)
    w2w_urma_latency: Mapped[Optional[float]] = mapped_column(Float)
    operation: Mapped[Optional[str]] = mapped_column(String)
    data_size: Mapped[Optional[str]] = mapped_column(String)
    offset: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_anomalous: Mapped[Optional[bool]] = mapped_column(Boolean)
    content: Mapped[Optional[str]] = mapped_column(Text)
    anomaly_reason: Mapped[Optional[str]] = mapped_column(Text)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    sdk_process: Mapped[Optional[float]] = mapped_column(Float)
    sdk_rpc: Mapped[Optional[float]] = mapped_column(Float)
    local_worker_cost: Mapped[Optional[float]] = mapped_column(Float)
    local_worker_lock: Mapped[Optional[float]] = mapped_column(Float)
    remote_worker_cost: Mapped[Optional[float]] = mapped_column(Float)
    remote_worker_rpc: Mapped[Optional[float]] = mapped_column(Float)
    master_process: Mapped[Optional[float]] = mapped_column(Float)
    master_rpc_total: Mapped[Optional[float]] = mapped_column(Float)
    create_latency: Mapped[Optional[float]] = mapped_column(Float)
    publish_latency: Mapped[Optional[float]] = mapped_column(Float)
    worker_total_latency: Mapped[Optional[float]] = mapped_column(Float)


# ============================================================
# 3. 聚合表（仅保留维度 + 计数）
# ============================================================
class SrcDstAggregatedEvent(Base):
    """源目的聚合表，仅保留维度 + 计数，统计量从 log_parse_result 实时计算。"""

    __tablename__ = "src_dst_aggregated_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    src_ip: Mapped[Optional[Any]] = mapped_column(INET)
    dst_ip: Mapped[Optional[Any]] = mapped_column(INET)
    log_id: Mapped[str] = mapped_column(String, index=True)
    log_parse_result_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    anomaly_log_parse_result_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    anomaly_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )


# ============================================================
# 4. 异常/诊断表
# ============================================================
class AnomalousEvent(Base):
    __tablename__ = "anomalous_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    log_id: Mapped[str] = mapped_column(String, index=True)
    aggregated_event_id: Mapped[Optional[str]] = mapped_column(String)
    start_log_parse_offset: Mapped[Optional[int]] = mapped_column(BigInteger)
    end_log_parse_offset: Mapped[Optional[int]] = mapped_column(BigInteger)
    anomaly_reason: Mapped[Optional[str]] = mapped_column(Text)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )


class AnomalousEventChain(Base):
    __tablename__ = "anomalous_event_chain"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    log_id: Mapped[str] = mapped_column(String, index=True)
    anomalous_event_id: Mapped[Optional[str]] = mapped_column(String)
    name: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    anomaly_code: Mapped[Optional[str]] = mapped_column(String)
    offset: Mapped[Optional[int]] = mapped_column(BigInteger)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )


class DiagnosisCase(Base):
    __tablename__ = "diagnosis_case"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kb_id: Mapped[str] = mapped_column(String, index=True)
    fault_type: Mapped[str] = mapped_column(String, default="unknown")
    title: Mapped[Optional[str]] = mapped_column(String)
    symptom_summary: Mapped[str] = mapped_column(Text, default="")
    root_cause: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    failure_mode_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, default=list)
    status_codes: Mapped[Optional[list[Any]]] = mapped_column(JSONB, default=list)
    fingerprint_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=dict)
    evidence_refs_json: Mapped[Optional[list[Any]]] = mapped_column(JSONB, default=list)
    counter_evidence_json: Mapped[Optional[list[Any]]] = mapped_column(JSONB, default=list)
    source_log_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, default=list)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(), onupdate=lambda: datetime.now()
    )


class DiagnosisCaseSignal(Base):
    __tablename__ = "diagnosis_case_signal"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    signal_type: Mapped[str] = mapped_column(String, primary_key=True)
    signal_value: Mapped[str] = mapped_column(String, primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


# ============================================================
# 5. 任务表
# ============================================================
class Task(Base):
    __tablename__ = "task"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kb_id: Mapped[str] = mapped_column(String)
    op_id: Mapped[str] = mapped_column(String, index=True)
    retry_times: Mapped[int] = mapped_column(Integer, default=0)
    task_name: Mapped[Optional[str]] = mapped_column(String)
    task_type: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)


class TaskReport(Base):
    __tablename__ = "task_report"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(start=1, increment=1), primary_key=True
    )
    task_id: Mapped[str] = mapped_column(String, index=True)
    progress: Mapped[Optional[float]] = mapped_column(Float)
    message: Mapped[Optional[str]] = mapped_column(Text)
    existed_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now()
    )


# ============================================================
# 6. 失败事件表
# ============================================================
class LogFailureEvent(Base):
    __tablename__ = "log_failure_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    log_id: Mapped[str] = mapped_column(String, index=True)
    log_file: Mapped[Optional[str]] = mapped_column(String)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    host_name: Mapped[str] = mapped_column(String, default="Unknown")
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    level: Mapped[Optional[str]] = mapped_column(String)
    filename: Mapped[Optional[str]] = mapped_column(String)
    pod_name: Mapped[Optional[str]] = mapped_column(String)
    pid: Mapped[Optional[str]] = mapped_column(String)
    tid: Mapped[Optional[str]] = mapped_column(String)
    trace_id: Mapped[Optional[str]] = mapped_column(String)
    cluster_name: Mapped[Optional[str]] = mapped_column(String)
    message: Mapped[Optional[str]] = mapped_column(Text)
    status_code: Mapped[Optional[str]] = mapped_column(String)
    failure_mode: Mapped[Optional[str]] = mapped_column(String)


class TraceFailureEvent(Base):
    __tablename__ = "trace_failure_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    log_id: Mapped[str] = mapped_column(String, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String)
    pod_names: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    src_ip: Mapped[Optional[Any]] = mapped_column(INET)
    dst_ip: Mapped[Optional[Any]] = mapped_column(INET)
    host_names: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    cluster_names: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    status_code: Mapped[Optional[str]] = mapped_column(String)
    failure_mode: Mapped[Optional[str]] = mapped_column(String)


class FailureModeKnowledge(Base):
    __tablename__ = "failure_mode_knowledge"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    symptom: Mapped[Optional[str]] = mapped_column(Text)
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    solution: Mapped[Optional[str]] = mapped_column(Text)
    failure_domain: Mapped[Optional[str]] = mapped_column(String)
    children_failure_mode_ids: Mapped[Optional[str]] = mapped_column(String)


class StatusCodeKnowledge(Base):
    __tablename__ = "status_code_knowledge"

    status_code: Mapped[str] = mapped_column(String, primary_key=True)
    symptom: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
