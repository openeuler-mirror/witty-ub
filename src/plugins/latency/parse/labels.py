"""label 契约：解析器 label 常量 + label → 列集。

**P1 契约层（2026-09-16）**：本文件是 label 相关**数据**的唯一来源，
值全部从下面两个文件**搬运**（一字未改），原文件改为从这里 import：

- `parse/worker_info_parser.py:28-53`（13 个 info/rpc label + `TIMED_LABELS`）
- `parse/parallel_scanner/columnar.py:44-49`（access/client 的 4 个 label）与
  `columnar.py:99-119`（`LABEL_TO_COLUMNS`）

为什么要有这个文件：`parse/parallel_scanner/**` 只是想拿几个 label 字符串，
却要 import 老解析器实现（`worker_info_parser`）——把「列名契约」挂在了
「老实现」上。收敛到本文件后，扫描器子树与老解析器之间不再有 import 边。

边界（本文件**只放数据**，不放行为）：label 的**使用**方式（entry_type→label 路由、
src 优先级 rank）仍在 `columnar.py`；老解析器类本身仍在各自文件里。
"""

# ── access / client 侧 label（来源 columnar.py:44-49）────────────────────
SDK_LABEL = "SDK access parse"
WORKER_ACCESS_LABEL = "Worker access parse"
INFO_BUCKET_LABEL = "Worker info parse"  # WorkerInfoParser.label，按 entry_type 路由
CLIENT_INFO_BUCKET_LABEL = "Client info parse"  # ClientInfoParser.label（polars 路径下同为 bucket）
# 需要按 entry_type 再路由到子 label 的 bucket 标签
BUCKET_LABELS = frozenset({INFO_BUCKET_LABEL, CLIENT_INFO_BUCKET_LABEL})

# ── Worker info / rpc 侧 label（来源 worker_info_parser.py:28-40）────────
URMA_LABEL = "Worker urma parse"
REMOTE_PULL_LABEL = "Worker remote pull parse"
LINK_LABEL = "Worker link parse"
QUERY_META_LABEL = "Worker query meta parse"
SDK_PROCESS_LABEL = "Worker sdk process parse"
SDK_RPC_LABEL = "Worker sdk rpc parse"
LOCAL_WORKER_COST_LABEL = "Worker local worker cost parse"
LOCAL_WORKER_LOCK_LABEL = "Worker local worker lock parse"
REMOTE_WORKER_COST_LABEL = "Worker remote worker cost parse"
REMOTE_WORKER_RPC_LABEL = "Worker remote worker rpc parse"
MASTER_PROCESS_LABEL = "Worker master process parse"
MASTER_RPC_LABEL = "Worker master rpc parse"
CLIENT_RPC_LABEL = "Client rpc parse"

# 带独立耗时列（可直接做时延统计）的 label 子集（来源 worker_info_parser.py:42-52）
TIMED_LABELS = (
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
)

# 每个 label 的日志行填哪些列（来源 columnar.py:99-119，值一字未改）
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
