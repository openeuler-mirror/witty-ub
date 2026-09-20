"""列式 worker 输出 — per-line 投影（33 个 TRACE_COLUMNS + 内部列）。

T1 (polars-pipeline-rewrite): 扫描 worker 直产列式结果。每条日志 entry 被
投影成一行"稀疏 + None 对齐"的 TRACE_COLUMNS 列（带 ``_label`` / ``_src_rank``
内部列），替代 ``{label: [tuple]}`` 的按 label 分桶输出。T2 用
``pl.concat + group_by("tid")`` 从这些列重建每 trace 一行（df_trace）。

TRACE_COLUMNS 是冻结契约：必须等于 ``KVCacheLogParseWorker._build_flat_trace_index``
产出的平铺 dict 全部键（聚合标量 + 全部时延 + 明细字段），逐列对齐才能保证
T2/T3/T4/T5 与 golden fixture 的字段级 parity。实测平铺 dict 为 33 键
（计划里的 29 是估算偏差；总时延/op 有派生副本列，去重后仍全部需要）。

内部列：
- ``_label``: 该行的源 label（"Worker info parse" 桶按 entry_type 路由为子 label）
- ``_src_rank``: src/dst 取源优先级（URMA=2 > RemotePull=1 > 其他 0），
  T2 按 max-rank 挑该 trace 的 src/dst，复现 ``_extract_trace_metrics`` 的
  URMA→RemotePull→"" 链
"""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, Any

from latency.ENUM.ds_log import EntryType, TupleField
from latency.database.utils import parse_timestamp
from latency.parse.columns import ALL_COLUMNS, INTERNAL_COLUMNS, TRACE_COLUMNS
from latency.parse.labels import (
    BUCKET_LABELS,
    CLIENT_INFO_BUCKET_LABEL,
    CLIENT_RPC_LABEL,
    INFO_BUCKET_LABEL,
    LABEL_TO_COLUMNS,
    LINK_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
    QUERY_META_LABEL,
    REMOTE_PULL_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    SDK_LABEL,
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    URMA_LABEL,
    WORKER_ACCESS_LABEL,
)

if TYPE_CHECKING:  # 仅注解使用，运行时不导入
    from latency.schemas.ds_log import LogEntry

# P1 契约层（2026-09-16）：label 常量与 label→列集搬到 ``parse/labels.py``、
# 列契约搬到 ``parse/columns.py``（唯一来源）。本文件 import 回来继续导出，
# 兄弟模块（scan_vector* / trace_frame / scanner）的既有 import 路径一字不改。

logger = logging.getLogger(__name__)

# 需要按 entry_type 再路由到子 label 的 bucket 标签（值在 labels.py）
_BUCKET_LABELS = BUCKET_LABELS


COLUMNS_KEY = "columns"

# ── 冻结契约：平铺 dict 的全部 33 键（与 _build_flat_trace_index 逐键对齐）──
# P1 契约层：TRACE_COLUMNS / INTERNAL_COLUMNS / ALL_COLUMNS 的定义已搬到
# ``parse/columns.py``（唯一来源），本文件由顶部 import 再导出。


# 每个 label 的日志行填哪些列（P1：定义已搬到 ``parse/labels.py``）


# entry_type(字符串) → 子 label（镜像
# kv_cache_log_parse_worker.WORKER_INFO_LABEL_BY_ENTRY_TYPE）
_ENTRY_TYPE_TO_LABEL: dict[str, str] = {
    EntryType.URMA.value: URMA_LABEL,
    EntryType.REMOTE_PULL.value: REMOTE_PULL_LABEL,
    EntryType.LINK.value: LINK_LABEL,
    EntryType.QUERY_META.value: QUERY_META_LABEL,
    EntryType.SDK_PROCESS.value: SDK_PROCESS_LABEL,
    EntryType.SDK_RPC.value: SDK_RPC_LABEL,
    EntryType.LOCAL_WORKER_COST.value: LOCAL_WORKER_COST_LABEL,
    EntryType.LOCAL_WORKER_LOCK.value: LOCAL_WORKER_LOCK_LABEL,
    EntryType.REMOTE_WORKER_COST.value: REMOTE_WORKER_COST_LABEL,
    EntryType.REMOTE_WORKER_RPC.value: REMOTE_WORKER_RPC_LABEL,
    EntryType.MASTER_PROCESS.value: MASTER_PROCESS_LABEL,
    EntryType.MASTER_RPC.value: MASTER_RPC_LABEL,
    EntryType.CLIENT_RPC.value: CLIENT_RPC_LABEL,
}

# src/dst 取源优先级：URMA=2 > RemotePull/RemoteWorkerCost/RemoteWorkerRpc=1 > 其他 0
_SRC_RANK: dict[str, int] = {
    URMA_LABEL: 2,
    REMOTE_PULL_LABEL: 1,
    REMOTE_WORKER_COST_LABEL: 1,
    REMOTE_WORKER_RPC_LABEL: 1,
}


def _float(value: int | float | str | None) -> float | None:
    """统一数值列类型，避免 polars 从混合 int/float list 推断错误。"""
    if value is None:
        return None
    return float(value)


def _parse_rpc_resp(resp_msg: str | None) -> tuple[float | None, float | None, float | None]:
    """解析 RPC 响应消息，提取 e2e_us / server_exec_us / network_residual_us。

    输入形如 "e2e_us=123,server_exec_us=100,network_residual_us=23"。
    返回 (e2e_us, server_exec_us, network_us)，不存在时对应值为 None。
    """
    if not resp_msg:
        return (None, None, None)
    d: dict[str, int | None] = {}
    for part in resp_msg.split(","):
        k, sep, v = part.strip().partition("=")
        if sep and v.strip().lstrip("-").isdigit():
            d[k.strip()] = int(v.strip())
    return (_float(d.get("e2e_us")), _float(d.get("server_exec_us")),
            _float(d.get("network_residual_us")))


def _get(entry: "tuple | LogEntry", field: TupleField) -> Any:
    """从 tuple（_serialize_entry 产物）或 dataclass（LogEntry）读取字段值。

    TupleField 名的大写下划线形式 == LogEntry 属性名（TIMESTAMP→timestamp、
    SRC_ADDR→src_addr …），因此用 ``field.name.lower()`` 做 dataclass 属性索引。
    """
    if isinstance(entry, tuple):
        return entry[field]
    return getattr(entry, field.name.lower())


def _entry_type_value(entry: "tuple | LogEntry") -> str | None:
    value = _get(entry, TupleField.ENTRY_TYPE)
    if isinstance(value, EntryType):
        return value.value
    return value


def _latency_ms(entry: "tuple | LogEntry") -> float | None:
    """ELAPSED_US → ms（与 _resolve_snapshot 的 ``/ 1000.0`` 一致）。"""
    elapsed_us = _get(entry, TupleField.ELAPSED_US)
    if elapsed_us is None:
        return None
    return elapsed_us / 1000.0


def _clean_addr(value: str | None) -> str:
    """src/dst 归一化：strip 后空串兜底（与 _extract_trace_metrics 一致）。"""
    return str(value or "").strip() or ""


def _bucket_epoch_10s(ts_raw: str | None) -> int | None:
    """Wall-clock 10s-aligned bucket epoch（复刻 worker 的 _bucket_epoch_10s）。"""
    ts = parse_timestamp(ts_raw)
    if ts is not None:
        epoch_sec = int(ts.replace(tzinfo=timezone.utc).timestamp())
        return (epoch_sec // 10) * 10
    return None


def _effective_label(label: str, entry: "tuple | LogEntry") -> str:
    """bucket（"Worker info parse"）按 entry_type 路由到子 label。

    未知 entry_type 保持 bucket 标签（投影无列可填，T2 归并时自然不影响任何
    trace 列 —— 等价于 _split_worker_info_entries 丢弃未知类型条目）。
    """
    if label not in _BUCKET_LABELS:
        return label
    return _ENTRY_TYPE_TO_LABEL.get(_entry_type_value(entry), label)


def _project(label: str, entry: "tuple | LogEntry", row: dict[str, object]) -> None:
    """把一条 entry 投影进行 dict（只填该 label 声明的列，其余保持 None）。"""
    if label == SDK_LABEL:
        elapsed_us = _get(entry, TupleField.ELAPSED_US)
        total_ms = elapsed_us / 1000.0 if elapsed_us is not None else None
        row["total_ms"] = total_ms
        row["total_latency"] = total_ms
        op_raw = _get(entry, TupleField.OPERATION)
        op = str(op_raw or "").strip().upper()
        row["op"] = op
        row["operation"] = op or None
        # 明确识别 GET 和 SET 操作类型
        if "GET" in op:
            row["op_key"] = "GET"
        elif any(kw in op for kw in ("SET", "CREATE", "PUBLISH")):
            row["op_key"] = "SET"
        else:
            row["op_key"] = None
        ts_raw = _get(entry, TupleField.TIMESTAMP)
        row["bucket_epoch"] = _bucket_epoch_10s(ts_raw)
        row["log_id"] = _get(entry, TupleField.LOG_ID) or ""
        row["status_code"] = _get(entry, TupleField.STATUS_CODE)
        row["timestamp"] = str(ts_raw) if ts_raw else None
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
        data_size = _get(entry, TupleField.DATA_SIZE)
        row["data_size"] = str(data_size) if data_size else None
        row["inflight_count"] = _float(_get(entry, TupleField.INFLIGHT_COUNT))
    elif label == WORKER_ACCESS_LABEL:
        row["worker_total_latency"] = _latency_ms(entry)
        ts_raw = _get(entry, TupleField.TIMESTAMP)
        row["bucket_epoch"] = _bucket_epoch_10s(ts_raw)
        row["timestamp"] = str(ts_raw) if ts_raw else None
        row["log_id"] = _get(entry, TupleField.LOG_ID) or ""
        op_raw = _get(entry, TupleField.OPERATION)
        op = str(op_raw or "").strip().upper()
        row["op"] = op
        row["operation"] = op or None
        # 明确识别 GET 和 SET 操作类型
        if "GET" in op:
            row["op_key"] = "GET"
        elif any(kw in op for kw in ("SET", "CREATE", "PUBLISH")):
            row["op_key"] = "SET"
        else:
            row["op_key"] = None
        row["status_code"] = _get(entry, TupleField.STATUS_CODE)
        # 添加 pod_ip 字段，确保 Worker access log 的 pod_ip 也被收集
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        # 添加 cluster_name 字段
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == URMA_LABEL:
        row["urma_total_latency"] = _latency_ms(entry)
        row["src"] = _clean_addr(_get(entry, TupleField.SRC_ADDR))
        row["dst"] = _clean_addr(_get(entry, TupleField.DST_ADDR))
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == REMOTE_PULL_LABEL:
        row["src"] = _clean_addr(_get(entry, TupleField.SRC_ADDR))
        row["dst"] = _clean_addr(_get(entry, TupleField.DST_ADDR))
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == LINK_LABEL:
        row["urma_link_latency"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == QUERY_META_LABEL:
        row["worker_query_meta_latency"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == SDK_PROCESS_LABEL:
        row["sdk_process"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == SDK_RPC_LABEL:
        row["sdk_rpc"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == LOCAL_WORKER_COST_LABEL:
        row["local_worker_cost"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == LOCAL_WORKER_LOCK_LABEL:
        row["local_worker_lock"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == REMOTE_WORKER_COST_LABEL:
        row["remote_worker_cost"] = _latency_ms(entry)
        row["src"] = _clean_addr(_get(entry, TupleField.SRC_ADDR))
        row["dst"] = _clean_addr(_get(entry, TupleField.DST_ADDR))
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == REMOTE_WORKER_RPC_LABEL:
        row["remote_worker_rpc"] = _latency_ms(entry)
        row["src"] = _clean_addr(_get(entry, TupleField.SRC_ADDR))
        row["dst"] = _clean_addr(_get(entry, TupleField.DST_ADDR))
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == MASTER_PROCESS_LABEL:
        row["master_process"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    elif label == MASTER_RPC_LABEL:
        row["master_rpc_total"] = _latency_ms(entry)
        pod_ip = _get(entry, TupleField.POD_IP)
        row["pod_ip"] = str(pod_ip) if pod_ip else None
        cluster_name = _get(entry, TupleField.CLUSTER_NAME)
        row["cluster_name"] = str(cluster_name) if cluster_name else None
    # 其他 label（未知 bucket entry_type）→ 无列填充


def entries_to_columns(merged: dict[str, list]) -> dict[str, list]:
    """把 ``{label: [entries]}`` 投影为 ``{column: [values]}``。

    每 entry 一行（稀疏 + None 对齐）：该 label 声明的列填投影值，其余
    TRACE_COLUMNS 列填 None；每行带 tid 并打 ``_label`` / ``_src_rank``
    内部列。行序 = merged 的 label 顺序 + label 内 entry 顺序（与
    ``_serialize_entry`` 输出的顺序完全一致，保证 T2 归并 first() 的 parity）。

    额外输出 5 个内部列（不进 ALL_COLUMNS，build_trace_frame 消费）：
    ``_elapsed_us`` / ``_resp_msg`` / ``_rpc_e2e_us`` / ``_rpc_server_exec_us`` /
    ``_rpc_network_us``，供 yuanrong 分段时延分解使用。
    """
    columns: dict[str, list] = {name: [] for name in ALL_COLUMNS}
    columns["_elapsed_us"] = []
    columns["_resp_msg"] = []
    columns["_rpc_e2e_us"] = []
    columns["_rpc_server_exec_us"] = []
    columns["_rpc_network_us"] = []
    for label, entries in merged.items():
        for entry in entries:
            eff_label = _effective_label(label, entry)
            row = dict.fromkeys(TRACE_COLUMNS)  # 全部 None
            row["tid"] = _get(entry, TupleField.TRACE_ID)  # 每行带 tid
            _project(eff_label, entry, row)
            for name in TRACE_COLUMNS:
                columns[name].append(row[name])
            columns["_label"].append(eff_label)
            columns["_src_rank"].append(_SRC_RANK.get(eff_label, 0))
            columns["_elapsed_us"].append(_float(_get(entry, TupleField.ELAPSED_US)))
            resp_msg = _get(entry, TupleField.RESP_MSG)
            columns["_resp_msg"].append(resp_msg)
            e2e, se, nw = _parse_rpc_resp(resp_msg)
            columns["_rpc_e2e_us"].append(e2e)
            columns["_rpc_server_exec_us"].append(se)
            columns["_rpc_network_us"].append(nw)
    return columns


def columns_to_frame(columns: dict[str, list]) -> "pl.DataFrame":
    """列式 dict → polars DataFrame（TRACE_COLUMNS + 内部列）。

    T2 用 ``pl.concat([w1..wN], how="vertical")`` 拼接各 worker 的 frame，
    再 ``group_by("tid")`` 归并成每 trace 一行（df_trace）。
    """
    import polars as pl  # 懒加载 polars

    return pl.DataFrame({name: columns[name] for name in ALL_COLUMNS})
