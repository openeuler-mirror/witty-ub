"""列契约：扫描输出的 40 列 + dtype 集合。

**P1 契约层（2026-09-16）**：本文件是列名/列序的唯一来源，值全部从下面两处
**搬运**（一字未改），原处改为从这里 import：

- `parse/parallel_scanner/columnar.py:55-96`：`TRACE_COLUMNS`(33) / `INTERNAL_COLUMNS` / `ALL_COLUMNS`
- `parse/parallel_scanner/scan_vector.py:45-64`：扫描器内部 5 列 + `_FLOAT_COLUMNS` / `_INT_COLUMNS`

40 列 = 33 契约列（`TRACE_COLUMNS`，与 `_build_flat_trace_index` 的平铺 dict 逐键对齐）
+ 2 归并列（`INTERNAL_COLUMNS`）
+ 5 扫描内部列（`SCANNER_INTERNAL_COLUMNS`，读行时用、归并前不再需要）。

为什么要有这个文件：列契约被 merge / aggregate / detail / bucket 共用，不只 read 段用；
放在 `parse/` 顶层（而不是 `parallel_scanner/` 里）才不会让下游为了拿列名去 import 扫描器。

`TRACE_COLUMNS` 是**冻结契约**：必须等于 `KVCacheLogParseWorker._build_flat_trace_index`
产出的平铺 dict 全部键，逐列对齐才能保证与 golden fixture 的字段级 parity。
"""

# ── 冻结契约：平铺 dict 的全部 33 键（来源 columnar.py:55-91）────────────
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

# 内部辅助列（不进冻结契约，T2 归并时消费；来源 columnar.py:93-94）
INTERNAL_COLUMNS: tuple[str, ...] = ("_label", "_src_rank")

ALL_COLUMNS: tuple[str, ...] = (*TRACE_COLUMNS, *INTERNAL_COLUMNS)

# 扫描内部列：只在读行时用，产出 40 列后归并阶段不再需要（来源 scan_vector.py:45-51）
SCANNER_INTERNAL_COLUMNS: tuple[str, ...] = (
    "_elapsed_us",
    "_resp_msg",
    "_rpc_e2e_us",
    "_rpc_server_exec_us",
    "_rpc_network_us",
)

# 扫描的最终输出列（40 列，来源 scan_vector.py:53）
OUTPUT_COLUMNS: tuple[str, ...] = (*ALL_COLUMNS, *SCANNER_INTERNAL_COLUMNS)

# ── 轻列（扫描瘦身，2026-09-17）──────────────────────────────────────────
# 只有这些列被"全量消费者"读到：src_dst 聚合按 (src,dst,op_key) 分组；time_window
# 聚合只对 total_latency 出 ave/min/max/p95/p99；分桶排序键是 (total_latency, tid)。
# 其余 30 列只服务明细子集与分桶代表行 → 不必给全量行算（见 p2-40col-consumer-map.md）。
# 注意 ``worker_total_latency``：归并后 total_ms/total_latency 为空时会退回它，故属轻列。
LIGHT_COLUMNS: tuple[str, ...] = (
    "tid",
    "total_ms",
    "total_latency",
    "worker_total_latency",
    "src",
    "dst",
    "op_key",
    "operation",
    "bucket_epoch",
    "log_id",
    "_src_rank",
)

# dtype 表：哪些列是浮点 / 整型（来源 scan_vector.py:54-64）
FLOAT_COLUMNS = frozenset({
    "total_ms", "total_latency", "worker_total_latency", "c2w_urma_latency",
    "urma_total_latency", "urma_link_latency", "worker_query_meta_latency",
    "sdk_process", "sdk_rpc", "local_worker_cost", "local_worker_lock",
    "remote_worker_cost", "remote_worker_rpc", "master_process",
    "master_rpc_total", "w2w_urma_latency", "create_latency", "publish_latency",
    "inflight_count", "_elapsed_us", "_rpc_e2e_us", "_rpc_server_exec_us",
    "_rpc_network_us",
})
INT_COLUMNS = frozenset({"bucket_epoch", "status_code", "_src_rank", "__row"})
