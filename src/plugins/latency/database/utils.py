# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL data conversion helpers."""
from __future__ import annotations

import ipaddress
import uuid
from datetime import datetime
from typing import Any


def set_db_timezone(tz) -> None:
    """No-op kept for backward compatibility.

    All timestamps are now stored as naive TIMESTAMP (no timezone),
    so no timezone configuration is needed.
    """
    pass


def get_db_timezone() -> None:
    """No-op kept for backward compatibility.

    Returns None since naive timestamps do not use a timezone.
    """
    return None


def parse_timestamp(value: str | datetime | None) -> datetime | None:
    """Convert timestamp string or datetime to a naive datetime (no timezone).

    All timestamps are stored as PostgreSQL TIMESTAMP (without timezone),
    preserving the original values exactly as they appear in logs and queries.
    No timezone conversion is performed.

    Timezone-aware datetimes are stripped to naive (tzinfo is discarded).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Convert IP string to Python ipaddress object for PostgreSQL INET."""
    if not value:
        return None
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        pass
    # Handle IPv4:port format (single colon, e.g. "192.168.1.1:8080")
    if value.count(":") == 1:
        try:
            return ipaddress.ip_address(value.rsplit(":", 1)[0])
        except ValueError:
            pass
    # Handle [IPv6]:port format
    if value.startswith("[") and "]" in value:
        try:
            return ipaddress.ip_address(value[1 : value.index("]")])
        except ValueError:
            pass
    return None


def parse_pod_ips(value: str | list[str] | None) -> list[str] | None:
    """Convert pod_ips JSON string or list to PostgreSQL TEXT[]."""
    if value is None:
        return None
    if isinstance(value, list):
        return value if value else None
    import json

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list) and parsed:
            return [str(v) for v in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def format_timestamp(value: datetime | None) -> str | None:
    """Format datetime back to SQLite-style string."""
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def format_ip(value: Any) -> str | None:
    """Format PostgreSQL INET / ipaddress object back to a plain IP string."""
    if value is None:
        return None
    if isinstance(value, (ipaddress.IPv4Interface, ipaddress.IPv4Network,
                          ipaddress.IPv6Interface, ipaddress.IPv6Network)):
        return str(value.ip)
    return str(value)


def result_to_pg_tuple(result: Any) -> tuple[Any, ...]:
    """Convert a LogParseResult dataclass/model to PostgreSQL COPY tuple."""
    result_id = result.id if getattr(result, "id", None) else str(uuid.uuid4())
    return (
        result_id,
        result.log_id,
        result.aggregated_event_id or "",
        result.anomalous_event_id or "",
        result.trace_id,
        parse_timestamp(result.timestamp),
        parse_ip(result.src_ip),
        parse_ip(result.dst_ip),
        parse_pod_ips(result.pod_ips),
        result.cluster_name,
        result.host,
        result.total_latency,
        result.c2w_latency,
        result.worker_query_meta_latency,
        result.urma_total_latency,
        result.urma_link_latency,
        result.urma_inflight_count,
        result.c2w_urma_latency,
        result.w2w_urma_latency,
        result.operation,
        result.data_size,
        result.offset,
        result.is_anomalous,
        result.content,
        result.anomaly_reason,
        result.anomaly_score,
        result.remark,
        result.existed_status,
        parse_timestamp(result.created_at),
        result.sdk_process,
        result.sdk_rpc,
        result.local_worker_cost,
        result.local_worker_lock,
        result.remote_worker_cost,
        result.remote_worker_rpc,
        result.master_process,
        result.master_rpc_total,
        result.create_latency,
        result.publish_latency,
        result.worker_total_latency,
    )


COPY_COLUMNS = [
    "id",
    "log_id",
    "aggregated_event_id",
    "anomalous_event_id",
    "trace_id",
    "timestamp",
    "src_ip",
    "dst_ip",
    "pod_ips",
    "cluster_name",
    "host",
    "total_latency",
    "c2w_latency",
    "worker_query_meta_latency",
    "urma_total_latency",
    "urma_link_latency",
    "urma_inflight_count",
    "c2w_urma_latency",
    "w2w_urma_latency",
    "operation",
    "data_size",
    "offset",
    "is_anomalous",
    "content",
    "anomaly_reason",
    "anomaly_score",
    "remark",
    "existed_status",
    "created_at",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    "create_latency",
    "publish_latency",
    "worker_total_latency",
]
