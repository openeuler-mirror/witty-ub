"""列式 worker 输出 — per-line 31 列投影。

T1 (polars-pipeline-rewrite): 扫描 worker 直产列式结果。每条日志 entry 被
投影成一行"稀疏 + None 对齐"的 TRACE_COLUMNS 列（带 ``_label`` / ``_src_rank``
内部列），替代 ``{label: [tuple]}`` 的按 label 分桶输出。T2 用
``pl.concat + group_by("tid")`` 从这些列重建每 trace 一行（df_trace）。

TRACE_COLUMNS 是冻结契约：必须等于 ``KVCacheLogParseWorker._build_flat_trace_index``
产出的平铺 dict 全部键（聚合标量 + 全部时延 + 明细字段），逐列对齐才能保证
T2/T3/T4/T5 与 golden fixture 的字段级 parity。实测平铺 dict 为 31 键
（计划里的 29 是估算偏差；总时延/op 有派生副本列，去重后仍全部需要）。

内部列：
- ``_label``: 该行的源 label（"Worker info parse" 桶按 entry_type 路由为子 label）
- ``_src_rank``: src/dst 取源优先级（URMA=2 > RemotePull=1 > 其他 0），
  T2 按 max-rank 挑该 trace 的 src/dst，复现 ``_extract_trace_metrics`` 的
  URMA→RemotePull→"" 链
"""

import logging
from datetime import timezone

from latency.ENUM.ds_log import EntryType, TupleField
from latency.database.utils import parse_timestamp
from latency.parse.worker_info_parser import (
    URMA_LABEL,
    REMOTE_PULL_LABEL,
    LINK_LABEL,
    QUERY_META_LABEL,
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
)

logger = logging.getLogger(__name__)

# 扫描器 label 常量（与各 parser 的 ``.label`` 一致）
SDK_LABEL = "SDK access parse"
WORKER_ACCESS_LABEL = "Worker access parse"
INFO_BUCKET_LABEL = "Worker info parse"  # WorkerInfoParser.label，按 entry_type 路由

# 归并结果中列式输出的保留键
COLUMNS_KEY = "columns"

# ── 冻结契约：平铺 dict 的全部 33 键（与 _build_flat_trace_index 逐键对齐）──
TRACE_COLUMNS: tuple[str, ...] = (
    # 聚合标量 + 明细字段
    "tid",
    "total_ms",
    "total_latency",
    "src",
    "dst",
    "op",
    "operation",
    "op_key",
    "bucket_epoch",
    "log_id",
    "status_code",
    "timestamp",
    "pod_ip",
    "cluster_name",
    "host",
    "data_size",
    "inflight_count",
    # 全部时延字段
    "c2w_urma_latency",
    "urma_total_latency",
    "urma_link_latency",
    "worker_query_meta_latency",
    "worker_total_latency",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    "w2w_urma_latency",
    "create_latency",
    "publish_latency",
)

# 内部辅助列（不进冻结契约，T2 归并时消费）
INTERNAL_COLUMNS: tuple[str, ...] = ("_label", "_src_rank")

ALL_COLUMNS: tuple[str, ...] = (*TRACE_COLUMNS, *INTERNAL_COLUMNS)

# 每个 label 的日志行填哪些列
LABEL_TO_COLUMNS: dict[str, tuple[str, ...]] = {
    SDK_LABEL: (
        "total_ms", "total_latency", "op", "operation", "op_key",
        "bucket_epoch", "log_id", "status_code", "timestamp", "pod_ip",
        "cluster_name", "data_size", "inflight_count",
    ),
    WORKER_ACCESS_LABEL: ("worker_total_latency", "bucket_epoch", "timestamp", "log_id", "op", "operation", "op_key", "status_code", "pod_ip", "cluster_name"),
    # Worker info labels 也需要添加 pod_ip 和 cluster_name，确保所有相关 pod 和集群都被记录
    URMA_LABEL: ("urma_total_latency", "src", "dst", "pod_ip", "cluster_name"),
    REMOTE_PULL_LABEL: ("src", "dst", "pod_ip", "cluster_name"),
    LINK_LABEL: ("urma_link_latency", "pod_ip", "cluster_name"),
    QUERY_META_LABEL: ("worker_query_meta_latency", "pod_ip", "cluster_name"),
    SDK_PROCESS_LABEL: ("sdk_process", "pod_ip", "cluster_name"),
    SDK_RPC_LABEL: ("sdk_rpc", "pod_ip", "cluster_name"),
    LOCAL_WORKER_COST_LABEL: ("local_worker_cost", "pod_ip", "cluster_name"),
    LOCAL_WORKER_LOCK_LABEL: ("local_worker_lock", "pod_ip", "cluster_name"),
    REMOTE_WORKER_COST_LABEL: ("remote_worker_cost", "src", "dst", "pod_ip", "cluster_name"),
    REMOTE_WORKER_RPC_LABEL: ("remote_worker_rpc", "src", "dst", "pod_ip", "cluster_name"),
    MASTER_PROCESS_LABEL: ("master_process", "pod_ip", "cluster_name"),
    MASTER_RPC_LABEL: ("master_rpc_total", "pod_ip", "cluster_name"),
}

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
}

# src/dst 取源优先级：URMA=2 > RemotePull/RemoteWorkerCost/RemoteWorkerRpc=1 > 其他 0
_SRC_RANK: dict[str, int] = {
    URMA_LABEL: 2,
    REMOTE_PULL_LABEL: 1,
    REMOTE_WORKER_COST_LABEL: 1,
    REMOTE_WORKER_RPC_LABEL: 1,
}


# 预计算 TupleField → LogEntry 属性名（避免每次 _get 都做 field.name.lower()）。
# TupleField 是 IntEnum，可直接作为 list 索引（__index__ → int）。
_ATTR_NAMES: tuple[str, ...] = tuple(f.name.lower() for f in TupleField)

# 预计算每个 label 填充的 TRACE_COLUMNS 子集与互补集（None 列），避免每条 entry
# 分配 dict.fromkeys(TRACE_COLUMNS) 再逐列拷贝。none_cols 是 tuple，迭代最快。
_TID_COL = "tid"
_LABEL_FILL_COLS: dict[str, frozenset[str]] = {
    label: frozenset(cols) for label, cols in LABEL_TO_COLUMNS.items()
}
_LABEL_NONE_COLS: dict[str, tuple[str, ...]] = {}
for _lbl, _fill in _LABEL_FILL_COLS.items():
    _LABEL_NONE_COLS[_lbl] = tuple(
        c for c in TRACE_COLUMNS if c not in _fill and c != _TID_COL
    )
# INFO_BUCKET_LABEL 自身无列填充（路由到子 label），其 none_cols = 全部非 tid 列
_LABEL_NONE_COLS[INFO_BUCKET_LABEL] = tuple(
    c for c in TRACE_COLUMNS if c != _TID_COL
)


def _float(value) -> float | None:
    """统一数值列类型，避免 polars 从混合 int/float list 推断错误。"""
    if value is None:
        return None
    return float(value)


def _parse_rpc_resp(resp_msg: str | None) -> tuple[float | None, float | None, float | None]:
    """解析 RPC 响应消息，提取 e2e_us / server_exec_us / network_residual_us。

    输入形如 "e2e_us=123,server_exec_us=100,network_residual_us=23"。
    返回 (e2e_us, server_exec_us, network_us)，不存在时对应值为 None。

    性能：绝大多数日志行（SDK/Worker access 的 resp_msg 通常是 "resp" 或空）
    不含 e2e_us，用 ``"e2e_us" not in resp_msg`` 单次子串扫描短路，跳过
    split/partition 循环（profile 实测该函数占 entries_to_columns 60%+ 耗时）。
    """
    if not resp_msg or "e2e_us" not in resp_msg:
        return (None, None, None)
    d: dict[str, int | None] = {}
    for part in resp_msg.split(","):
        k, sep, v = part.strip().partition("=")
        if sep and v.strip().lstrip("-").isdigit():
            d[k.strip()] = int(v.strip())
    return (_float(d.get("e2e_us")), _float(d.get("server_exec_us")),
            _float(d.get("network_residual_us")))


def _get(entry, field):
    """从 tuple（_serialize_entry 产物）或 dataclass（LogEntry）读取字段值。

    使用预计算的 ``_ATTR_NAMES`` 避免每次调用 ``field.name.lower()``（profile
    实测该路径在 18 万 entry 上被调用 150 万次，.name.lower() 占 0.33s）。
    ``field`` 是 TupleField (IntEnum)，tuple/dataclass 路径均可直接用作索引。
    """
    if isinstance(entry, tuple):
        return entry[field]
    return getattr(entry, _ATTR_NAMES[field])


def _entry_type_value(entry) -> str | None:
    value = _get(entry, TupleField.ENTRY_TYPE)
    if isinstance(value, EntryType):
        return value.value
    return value


def _latency_ms(entry) -> float | None:
    """ELAPSED_US → ms（与 _resolve_snapshot 的 ``/ 1000.0`` 一致）。"""
    elapsed_us = _get(entry, TupleField.ELAPSED_US)
    if elapsed_us is None:
        return None
    return elapsed_us / 1000.0


def _clean_addr(value) -> str:
    """src/dst 归一化：strip 后空串兜底（与 _extract_trace_metrics 一致）。"""
    return str(value or "").strip() or ""


def _bucket_epoch_10s(ts_raw) -> int | None:
    """Wall-clock 10s-aligned bucket epoch（复刻 worker 的 _bucket_epoch_10s）。"""
    ts = parse_timestamp(ts_raw)
    if ts is not None:
        epoch_sec = int(ts.replace(tzinfo=timezone.utc).timestamp())
        return (epoch_sec // 10) * 10
    return None


def _effective_label(label: str, entry) -> str:
    """bucket（"Worker info parse"）按 entry_type 路由到子 label。

    未知 entry_type 保持 bucket 标签（投影无列可填，T2 归并时自然不影响任何
    trace 列 —— 等价于 _split_worker_info_entries 丢弃未知类型条目）。
    """
    if label != INFO_BUCKET_LABEL:
        return label
    return _ENTRY_TYPE_TO_LABEL.get(_entry_type_value(entry), INFO_BUCKET_LABEL)


def _get_tuple(entry, field):
    """tuple 路径字段读取（模块级，避免每 entry 创建闭包）。"""
    return entry[field]


def _get_dc(entry, field):
    """dataclass 路径字段读取（用预计算 _ATTR_NAMES，避免 .name.lower()）。"""
    return getattr(entry, _ATTR_NAMES[field])


def _project(label: str, entry, columns: dict[str, list], getter) -> None:
    """把一条 entry 投影直接 append 到 columns（只填该 label 声明的列）。

    ``getter`` 是 ``_get_tuple`` 或 ``_get_dc``，由调用方每条 entries 列表
    只绑定一次（避免每 entry 创建闭包，profile 实测节省 ~0.15s/18 万 entry）。
    """
    g = getter
    if label == SDK_LABEL:
        elapsed_us = g(entry, TupleField.ELAPSED_US)
        total_ms = elapsed_us / 1000.0 if elapsed_us is not None else None
        columns["total_ms"].append(total_ms)
        columns["total_latency"].append(total_ms)
        op_raw = g(entry, TupleField.OPERATION)
        op = str(op_raw or "").strip().upper()
        columns["op"].append(op)
        columns["operation"].append(op or None)
        if "GET" in op:
            columns["op_key"].append("GET")
        elif "SET" in op or "CREATE" in op or "PUBLISH" in op:
            columns["op_key"].append("SET")
        else:
            columns["op_key"].append(None)
        ts_raw = g(entry, TupleField.TIMESTAMP)
        columns["bucket_epoch"].append(_bucket_epoch_10s(ts_raw))
        _log_id = g(entry, TupleField.LOG_ID)
        columns["log_id"].append(_log_id or "")
        columns["status_code"].append(g(entry, TupleField.STATUS_CODE))
        columns["timestamp"].append(str(ts_raw) if ts_raw else None)
        pod_ip = g(entry, TupleField.POD_IP)
        columns["pod_ip"].append(str(pod_ip) if pod_ip else None)
        cluster_name = g(entry, TupleField.CLUSTER_NAME)
        columns["cluster_name"].append(str(cluster_name) if cluster_name else None)
        data_size = g(entry, TupleField.DATA_SIZE)
        columns["data_size"].append(str(data_size) if data_size else None)
        columns["inflight_count"].append(_float(g(entry, TupleField.INFLIGHT_COUNT)))
    elif label == WORKER_ACCESS_LABEL:
        columns["worker_total_latency"].append(_latency_ms_get(entry, g))
        ts_raw = g(entry, TupleField.TIMESTAMP)
        columns["bucket_epoch"].append(_bucket_epoch_10s(ts_raw))
        columns["timestamp"].append(str(ts_raw) if ts_raw else None)
        columns["log_id"].append(g(entry, TupleField.LOG_ID) or "")
        op_raw = g(entry, TupleField.OPERATION)
        op = str(op_raw or "").strip().upper()
        columns["op"].append(op)
        columns["operation"].append(op or None)
        if "GET" in op:
            columns["op_key"].append("GET")
        elif "SET" in op or "CREATE" in op or "PUBLISH" in op:
            columns["op_key"].append("SET")
        else:
            columns["op_key"].append(None)
        columns["status_code"].append(g(entry, TupleField.STATUS_CODE))
        pod_ip = g(entry, TupleField.POD_IP)
        columns["pod_ip"].append(str(pod_ip) if pod_ip else None)
        cluster_name = g(entry, TupleField.CLUSTER_NAME)
        columns["cluster_name"].append(str(cluster_name) if cluster_name else None)
    elif label == URMA_LABEL:
        columns["urma_total_latency"].append(_latency_ms_get(entry, g))
        columns["src"].append(_clean_addr(g(entry, TupleField.SRC_ADDR)))
        columns["dst"].append(_clean_addr(g(entry, TupleField.DST_ADDR)))
        _append_pod_cluster(entry, g, columns)
    elif label == REMOTE_PULL_LABEL:
        columns["src"].append(_clean_addr(g(entry, TupleField.SRC_ADDR)))
        columns["dst"].append(_clean_addr(g(entry, TupleField.DST_ADDR)))
        _append_pod_cluster(entry, g, columns)
    elif label == LINK_LABEL:
        columns["urma_link_latency"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == QUERY_META_LABEL:
        columns["worker_query_meta_latency"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == SDK_PROCESS_LABEL:
        columns["sdk_process"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == SDK_RPC_LABEL:
        columns["sdk_rpc"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == LOCAL_WORKER_COST_LABEL:
        columns["local_worker_cost"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == LOCAL_WORKER_LOCK_LABEL:
        columns["local_worker_lock"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == REMOTE_WORKER_COST_LABEL:
        columns["remote_worker_cost"].append(_latency_ms_get(entry, g))
        columns["src"].append(_clean_addr(g(entry, TupleField.SRC_ADDR)))
        columns["dst"].append(_clean_addr(g(entry, TupleField.DST_ADDR)))
        _append_pod_cluster(entry, g, columns)
    elif label == REMOTE_WORKER_RPC_LABEL:
        columns["remote_worker_rpc"].append(_latency_ms_get(entry, g))
        columns["src"].append(_clean_addr(g(entry, TupleField.SRC_ADDR)))
        columns["dst"].append(_clean_addr(g(entry, TupleField.DST_ADDR)))
        _append_pod_cluster(entry, g, columns)
    elif label == MASTER_PROCESS_LABEL:
        columns["master_process"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    elif label == MASTER_RPC_LABEL:
        columns["master_rpc_total"].append(_latency_ms_get(entry, g))
        _append_pod_cluster(entry, g, columns)
    # 其他 label（未知 bucket entry_type）→ 无列填充（none_cols 已处理 None）


def _append_pod_cluster(entry, g, columns: dict[str, list]) -> None:
    """公共：pod_ip + cluster_name 两列投影（11 个 timed/master 子 label 共用）。"""
    pod_ip = g(entry, TupleField.POD_IP)
    columns["pod_ip"].append(str(pod_ip) if pod_ip else None)
    cluster_name = g(entry, TupleField.CLUSTER_NAME)
    columns["cluster_name"].append(str(cluster_name) if cluster_name else None)


def _latency_ms_get(entry, g) -> float | None:
    """``_latency_ms`` 的 getter 友好版本（避免重复 _get isinstance）。"""
    elapsed_us = g(entry, TupleField.ELAPSED_US)
    if elapsed_us is None:
        return None
    return elapsed_us / 1000.0


def entries_to_columns(merged: dict[str, list]) -> dict[str, list]:
    """把 ``{label: [entries]}`` 投影为 ``{column: [values]}``。

    每 entry 一行（稀疏 + None 对齐）：该 label 声明的列填投影值，其余
    TRACE_COLUMNS 列填 None；每行带 tid 并打 ``_label`` / ``_src_rank``
    内部列。行序 = merged 的 label 顺序 + label 内 entry 顺序（与
    ``_serialize_entry`` 输出的顺序完全一致，保证 T2 归并 first() 的 parity）。

    额外输出 5 个内部列（不进 ALL_COLUMNS，build_trace_frame 消费）：
    ``_elapsed_us`` / ``_resp_msg`` / ``_rpc_e2e_us`` / ``_rpc_server_exec_us`` /
    ``_rpc_network_us``，供 yuanrong 分段时延分解使用。

    性能优化（不变更输出契约）：
    - 预计算每 label 的 none_cols（TRACE_COLUMNS 中不被该 label 填充的列），
      直接批量 append None，避免每条 entry 分配 dict.fromkeys(TRACE_COLUMNS)
      再逐列拷贝（原实现占 entries_to_columns ~25% 耗时）。
    - ``_get`` 使用预计算 _ATTR_NAMES，避免 .name.lower() 每次调用。
    - ``_parse_rpc_resp`` 用 ``"e2e_us" not in resp_msg`` 短路（占原 60% 耗时）。
    """
    columns: dict[str, list] = {name: [] for name in ALL_COLUMNS}
    columns["_elapsed_us"] = []
    columns["_resp_msg"] = []
    columns["_rpc_e2e_us"] = []
    columns["_rpc_server_exec_us"] = []
    columns["_rpc_network_us"] = []
    # 预绑定内部列 list 对象到局部变量（热路径，每条 entry 都写）
    c_tid = columns["tid"]
    c_label = columns["_label"]
    c_src_rank = columns["_src_rank"]
    c_elapsed_us = columns["_elapsed_us"]
    c_resp_msg = columns["_resp_msg"]
    c_rpc_e2e = columns["_rpc_e2e_us"]
    c_rpc_se = columns["_rpc_server_exec_us"]
    c_rpc_nw = columns["_rpc_network_us"]
    # 预计算每 label 的 none_lists（list 对象列表，直接 append 无 dict 查找）
    # 原 6M dict.__getitem__ 调用（每 entry × 28 none_cols）替换为直接 list.append。
    none_cols_get = _LABEL_NONE_COLS.get
    _default_none = _LABEL_NONE_COLS[INFO_BUCKET_LABEL]
    none_lists_cache: dict[str, list] = {}
    src_rank_get = _SRC_RANK.get
    entry_type_map = _ENTRY_TYPE_TO_LABEL
    for label, entries in merged.items():
        if not entries:
            continue
        is_bucket = label is INFO_BUCKET_LABEL
        is_tuple = isinstance(entries[0], tuple)
        # 每条 entries 列表只绑定一次 getter（避免每 entry 创建闭包）
        getter = _get_tuple if is_tuple else _get_dc
        # 非 bucket label 的 none_lists 与 eff_label 在整个 entries 列表内恒定
        if not is_bucket:
            eff_label_fixed = label
            src_rank_fixed = src_rank_get(label, 0)
            none_col_names = none_cols_get(label, _default_none)
            none_lists = none_lists_cache.get(label)
            if none_lists is None:
                none_lists = [columns[c] for c in none_col_names]
                none_lists_cache[label] = none_lists
        for entry in entries:
            if is_bucket:
                _et = entry[TupleField.ENTRY_TYPE] if is_tuple else _entry_type_value(entry)
                _et_val = _et.value if isinstance(_et, EntryType) else _et
                eff_label = entry_type_map.get(_et_val, label)
                none_lists = none_lists_cache.get(eff_label)
                if none_lists is None:
                    none_col_names = none_cols_get(eff_label, _default_none)
                    none_lists = [columns[c] for c in none_col_names]
                    none_lists_cache[eff_label] = none_lists
                src_rank_fixed = src_rank_get(eff_label, 0)
            else:
                eff_label = eff_label_fixed
            # tid（每行都填）
            c_tid.append(getter(entry, TupleField.TRACE_ID))
            # None 填充该 label 不声明的列（预绑定 list 对象，无 dict 查找）
            for lst in none_lists:
                lst.append(None)
            # 投影该 label 声明的列（直接 append，不经过中间 dict）
            _project(eff_label, entry, columns, getter)
            # 内部列
            c_label.append(eff_label)
            c_src_rank.append(src_rank_fixed)
            _elapsed = getter(entry, TupleField.ELAPSED_US)
            c_elapsed_us.append(_float(_elapsed))
            _resp = getter(entry, TupleField.RESP_MSG)
            c_resp_msg.append(_resp)
            e2e, se, nw = _parse_rpc_resp(_resp)
            c_rpc_e2e.append(e2e)
            c_rpc_se.append(se)
            c_rpc_nw.append(nw)
    return columns


def columns_to_frame(columns: dict[str, list]):
    """列式 dict → polars DataFrame（TRACE_COLUMNS + 内部列）。

    T2 用 ``pl.concat([w1..wN], how="vertical")`` 拼接各 worker 的 frame，
    再 ``group_by("tid")`` 归并成每 trace 一行（df_trace）。
    """
    import polars as pl

    return pl.DataFrame({name: columns[name] for name in ALL_COLUMNS})
