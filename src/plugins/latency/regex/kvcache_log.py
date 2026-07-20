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

# SET 请求的 Master 端 CreateMetaReq 日志，提取 src/dst 端点（不含端口）
CREATE_META_REQ_RE = re.compile(
    r"Processing CreateMetaReq,.*?src=([^:]+):\d+,\s*dst=([^:]+):\d+",
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

# 1. sdk_process - 关键字: [Get] Done ... totalCost: Xms
SDK_PROCESS_RE = re.compile(
    r"(?:\[Get\]\s+Done,\s*"
    r"clientId:\s*(?P<client_id>[^,\s]+),\s*"
    r"objects:\s*(?P<objects>\d+),\s*"
    r"transferPath:\s*(?P<transfer_path>[^,]+),\s*)?"
    r"totalCost:\s*(?P<cost>[\d.]+)ms"
    r"(?:,\s*inflightRemoteGet:\s*(?P<inflight_remote_get>\d+)"
    r"(?:\s+exceed\s+[\d.]+ms:\s*\{(?P<slow_items>.*?)\})?)?"
)

# 2. sdk_rpc - 关键字: Worker to master rpc QueryMeta: Xms
SDK_RPC_RE = re.compile(r"Worker to master rpc QueryMeta:\s*(?P<cost>[\d.]+)\s*ms")

# 3. local_worker_cost - 关键字: ProcessGetObjectRequest: Xms
LOCAL_WORKER_COST_RE = re.compile(r"ProcessGetObjectRequest:\s*(?P<cost>[\d.]+)\s*ms")

# 4. local_worker_lock - 关键字: worker SafeObject WLock: Xms
LOCAL_WORKER_LOCK_RE = re.compile(r"worker SafeObject WLock:\s*(?P<cost>[\d.]+)\s*ms")

# 5. remote_worker_cost - 关键字: [Get/RemotePull] finish ... cost: Xms
REMOTE_WORKER_COST_RE = re.compile(
    r"\[Get/RemotePull\]\s+finish"
    r"(?:,\s*count:\s*(?P<count>\d+),\s*"
    r"firstObjectKey:\s*(?P<first_object_key>[^,]*),\s*"
    r"payload size:\s*(?P<payload_size>\d+),\s*"
    r"start remainingTime:\s*(?P<start_remaining_time>[^,]+))?"
    r".*?cost:\s*(?P<cost>[\d.]+)ms"
    r"(?:,\s*src\s*=\s*(?P<src>[^,\s]+),\s*dst\s*=\s*(?P<dst>[^,\s]+))?"
)

# 6. remote_worker_rpc - 关键字: [Get] Remote done ... cost: Xms
REMOTE_WORKER_RPC_RE = re.compile(
    r"\[Get\]\s+Remote done"
    r"(?:,\s*count:\s*(?P<count>\d+),\s*path:\s*(?P<path>[^,]+))?"
    r".*?cost:\s*(?P<cost>[\d.]+)ms"
    r"(?:,\s*src\s*=\s*(?P<src>[^,\s]+),\s*dst\s*=\s*(?P<dst>[^,\s]+))?"
)

# 7. master_process - 关键字: QueryMeta done ... cost: Xms
MASTER_PROCESS_RE = re.compile(
    r"QueryMeta done"
    r"(?:,\s*target num\s*(?P<target_num>\d+),\s*"
    r"success num\s*(?P<success_num>\d+))?"
    r".*?cost:\s*(?P<cost>[\d.]+)ms"
)

# 8. master_rpc - 关键字: [ZMQ_RPC_FRAMEWORK_SLOW] ... remote_processing_us=X
MASTER_RPC_RE = re.compile(
    r"\[ZMQ_RPC_FRAMEWORK_SLOW\]\s+"
    r"trace_id=(?P<rpc_trace_id>\S+)\s+"
    r"framework_us=(?P<framework_us>\d+)\s+"
    r"e2e_us=(?P<e2e_us>\d+)\s+"
    r"client_req_framework_us=(?P<client_req_framework_us>\d+)\s+"
    r"remote_processing_us=(?P<remote_processing_us>\d+)\s+"
    r"client_rsp_framework_us=(?P<client_rsp_framework_us>\d+)\s+"
    r"server_req_queue_us=(?P<server_req_queue_us>\d+)\s+"
    r"server_exec_us=(?P<server_exec_us>\d+)\s+"
    r"server_rsp_queue_us=(?P<server_rsp_queue_us>\d+)\s+"
    r"network_residual_us=(?P<network_residual_us>\d+)"
)
