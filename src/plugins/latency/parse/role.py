# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""容器角色识别：根据日志行特征推断该行所属容器的功能角色。

KVCache 集群中同一 Worker 会在不同请求路径扮演不同功能角色，因此角色
按"日志行"粒度识别：client / entry worker / meta worker / data worker。
判定基于日志行字段（pod_name / cluster_name / filename / message /
log_file），规则为按优先级命中（client > meta > data > entry）。

- ``identify_log_role``：Python 逐行实现（legacy 扫描 / 回填 / 单测）。
- ``role_expr``：Polars 向量化实现（生产主路径，原生且不物化逐行对象）。
"""
from __future__ import annotations

import polars as pl

from enum import Enum


class LogRole(str, Enum):
    """容器功能角色。"""

    CLIENT = "client"
    ENTRY_WORKER = "entry_worker"
    META_WORKER = "meta_worker"
    DATA_WORKER = "data_worker"
    UNKNOWN = "unknown"


# ------------------------------------------------------------------
# 判定信号（统一小写子串匹配）
# ------------------------------------------------------------------
# client：pod/cluster 命名含 client，或 client 侧访问操作 / RPC
_CLIENT_POD_HINTS = ("client",)
_CLIENT_MSG_HINTS = (
    "ds_kv_client", "ds_object_client", "client rpc", "client_worker_remote_api",
)
# meta worker：元数据查询 / 元数据管理请求 / master 节点操作
_META_MSG_HINTS = (
    "querymeta", "createmeta", "updatemeta", "deletemeta",
    "master rpc", "master query", "master done",
)
_META_FILE_HINTS = ("oc_metadata", "master_oc", "metastore")
# data worker：URMA 传输 / 远程拉取 / 数据面日志文件
_DATA_MSG_HINTS = (
    "urma", "remote get request", "processing pull object", "pull object",
    "target address", "src address",
)
_DATA_FILE_HINTS = ("urma", "remote_pull", "link")
# entry worker：worker 侧访问操作（DS_POSIX_*）
_ENTRY_MSG_HINTS = ("ds_posix",)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def identify_log_role(
    *,
    pod_name: str = "",
    cluster_name: str = "",
    filename: str = "",
    message: str = "",
    log_file: str = "",
) -> str:
    """逐行识别日志所属容器角色，返回 :class:`LogRole` 的值。

    优先级：client > meta worker > data worker > entry worker > unknown。
    """
    pod_cluster = f"{pod_name} {cluster_name}".lower()
    file_text = f"{log_file}".lower()
    msg = (message or "").lower()
    filename_lower = (filename or "").lower()
    content = f"{msg} {filename_lower} {file_text}"

    if _contains_any(pod_cluster, _CLIENT_POD_HINTS) or _contains_any(
        content, _CLIENT_MSG_HINTS
    ):
        return LogRole.CLIENT.value
    if _contains_any(content, _META_MSG_HINTS) or _contains_any(
        filename_lower, _META_FILE_HINTS
    ):
        return LogRole.META_WORKER.value
    if _contains_any(content, _DATA_MSG_HINTS) or _contains_any(
        file_text, _DATA_FILE_HINTS
    ):
        return LogRole.DATA_WORKER.value
    if _contains_any(msg, _ENTRY_MSG_HINTS):
        return LogRole.ENTRY_WORKER.value
    return LogRole.UNKNOWN.value


def role_expr(
    *,
    pod_name: pl.Expr | None = None,
    cluster_name: pl.Expr | None = None,
    filename: pl.Expr | None = None,
    message: pl.Expr | None = None,
    log_file: pl.Expr | None = None,
) -> pl.Expr:
    """Polars 向量化角色识别表达式（生产主路径）。

    默认引用同名输入列（log_file / pod_name / cluster_name / filename /
    message），也可显式传入列表达式（如投影中基于原始分隔字段的 strip）。
    """
    has = lambda column, hints: pl.any_horizontal(  # noqa: E731
        column.str.to_lowercase().str.contains(hint, literal=True) for hint in hints
    )
    pod_name = pod_name if pod_name is not None else pl.col("pod_name")
    cluster_name = cluster_name if cluster_name is not None else pl.col("cluster_name")
    filename = filename if filename is not None else pl.col("filename")
    message = message if message is not None else pl.col("message")
    log_file = log_file if log_file is not None else pl.col("log_file")

    pod_cluster = pl.concat_str([pod_name, cluster_name], separator=" ")
    content = pl.concat_str([message, filename, log_file], separator=" ")

    return (
        pl.when(has(pod_cluster, _CLIENT_POD_HINTS) | has(content, _CLIENT_MSG_HINTS))
        .then(pl.lit(LogRole.CLIENT.value))
        .when(has(content, _META_MSG_HINTS) | has(filename, _META_FILE_HINTS))
        .then(pl.lit(LogRole.META_WORKER.value))
        .when(has(content, _DATA_MSG_HINTS) | has(log_file, _DATA_FILE_HINTS))
        .then(pl.lit(LogRole.DATA_WORKER.value))
        .when(has(message, _ENTRY_MSG_HINTS))
        .then(pl.lit(LogRole.ENTRY_WORKER.value))
        .otherwise(pl.lit(LogRole.UNKNOWN.value))
    )
