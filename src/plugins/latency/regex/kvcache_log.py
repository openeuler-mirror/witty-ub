import re

# -------------------------------------------------------------------
# 日志内容提取正则
# -------------------------------------------------------------------

OBJECT_KEY_RE = re.compile(r"[Oo]bject_key:\[?([^\]\},]+)")

NOT_FOUND_RE = re.compile(r"\bK_NOT_FOUND\b|not\s+found|notfound", re.IGNORECASE)

# -------------------------------------------------------------------
# URMA相关正则
# -------------------------------------------------------------------

URMA_RE = re.compile(
    r"\[URMA_ELAPSED_TOTAL\].*?cost\s+([\d.]+)ms.*?"
    r"src\s+address\s*:\s*([^,]*?)\s*,\s*"
    r"(?:target|dst|destination)\s+address\s*:\s*([^,]*?)\s*,.*?"
    r"urma_inflight_wr_count:\s*(\d+)",
    re.IGNORECASE,
)

URMA_LINK_RE = re.compile(
    r"(?:WorkerWorkerExchangeUrmaConnectInfo finish|Worker-worker transport connection exchange success),\s*?"
    r"elapsed ms:\s*([\d.]+)"
)

# -------------------------------------------------------------------
# 远程读写请求正则
# -------------------------------------------------------------------

REMOTE_GET_RE = re.compile(
    r"Remote get request:.*?src[= ]([^,]+),\s*dst[= ]([^,|\]]+)"
)

REMOTE_PULL_RE = re.compile(
    r"Processing pull object\[.*?src[= ]([^,]+),\s*dst[= ]([^,|\]]+)"
)

REMOTE_ENDPOINT_RE = re.compile(
    r"\bsrc\s*(?:=|:|\s+)\s*([^,\]\s]+)\s*,\s*"
    r"dst\s*(?:=|:|\s+)\s*([^,\]\s]+)",
    re.IGNORECASE,
)

# -------------------------------------------------------------------
# 查询元数据正则
# -------------------------------------------------------------------

QUERY_META_RE = re.compile(
    r"cost:\s*([\d.]+)ms?"
)

# -------------------------------------------------------------------
# 通用数值提取正则
# -------------------------------------------------------------------

LEADING_FLOAT_RE = re.compile(r"^\s*([\d.]+)(?:ms)?(?:\(|\s*$)")

# -------------------------------------------------------------------
# 新增时延指标正则 (按用户需求添加)
# -------------------------------------------------------------------

# 1. sdk_process - 关键字: totalCost: Xms
SDK_PROCESS_RE = re.compile(r"totalCost:\s*([\d.]+)ms")

# 2. sdk_rpc - 关键字: Worker to master rpc QueryMeta: Xms
SDK_RPC_RE = re.compile(r"Worker to master rpc QueryMeta:\s*([\d.]+)\s*ms")

# 3. local_worker_cost - 关键字: ProcessGetObjectRequest: Xms
LOCAL_WORKER_COST_RE = re.compile(r"ProcessGetObjectRequest:\s*([\d.]+)\s*ms")

# 4. local_worker_lock - 关键字: worker SafeObject WLock: Xms
LOCAL_WORKER_LOCK_RE = re.compile(r"worker SafeObject WLock:\s*([\d.]+)ms")

# 5. remote_worker_cost - 关键字: [Get/RemotePull] finish ... cost: Xms
REMOTE_WORKER_COST_RE = re.compile(r"\[Get/RemotePull\]\s+finish.*?cost:\s*([\d.]+)ms")

# 6. remote_worker_rpc - 关键字: [Get] Remote done ... cost: Xms
REMOTE_WORKER_RPC_RE = re.compile(r"\[Get\]\s+Remote done.*?cost:\s*([\d.]+)ms")

# 7. master_process - 关键字: QueryMeta done ... cost: Xms
MASTER_PROCESS_RE = re.compile(r"QueryMeta done.*?cost:\s*([\d.]+)ms")

# 8. master_rpc - 关键字: [ZMQ_RPC_FRAMEWORK_SLOW] ... remote_processing_us=X
MASTER_RPC_RE = re.compile(r"\[ZMQ_RPC_FRAMEWORK_SLOW\].*?remote_processing_us=(\d+)")
