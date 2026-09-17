"""关键字 / 切段位次 / 正则门禁 契约。

**P1 契约层（2026-09-16）**：本文件是「怎么切一行、怎么判一行属于哪类」这些
**数据**的唯一来源，值全部从下面几处**搬运**（一字未改），原处改为从这里 import：

- `parse/base_parser.py:20-25`：4 个 OPS 集合、`ACCESS_LOG_MIN_PARTS`、`RUN_LOG_MIN_PARTS`
- `parse/base_parser.py:66-77`：`LogParser._UUID_RE` / `_TRACE_FIELD_RE`
- `parse/base_parser.py:95-126`：`LogParser.AccessCol` / `LogParser.RunCol`（切段位次）
- `parse/worker_info_parser.py:55-66`：`BASE_KEYWORDS` / `TIMED_KEYWORDS` / `ALL_KEYWORDS`
- `parse/worker_info_parser.py:69`：`_IP_ENDPOINT_RE`
- `regex/kvcache_log.py`：`MASTER_RPC_RE`（**原地**，本文件只是再导出，避免扫描器
  绕道 `worker_info_parser` 去拿正则）

为什么要有这个文件：`parse/parallel_scanner/**` 只是想拿「关键字 / 正则 / 段位次」，
却要 import 老解析器实现（`base_parser` / `worker_info_parser`）。收敛到本文件后，
扫描器子树与老解析器之间不再有 import 边。

边界（本文件**只放数据**）：`LogParser` 类本身的解析行为留在 `base_parser.py`。
"""

import re
from enum import IntEnum

from latency.ENUM.ds_log import OpType
from latency.regex.kvcache_log import MASTER_RPC_RE

__all__ = [
    "SDK_GET_OPS",
    "SDK_SET_OPS",
    "WORKER_GET_OPS",
    "WORKER_SET_OPS",
    "ACCESS_LOG_MIN_PARTS",
    "RUN_LOG_MIN_PARTS",
    "SDK_ACCESS_KEYWORDS",
    "WORKER_ACCESS_KEYWORDS",
    "BASE_KEYWORDS",
    "TIMED_KEYWORDS",
    "ALL_KEYWORDS",
    "MASTER_RPC_RE",
    "IP_ENDPOINT_RE",
    "UUID_RE",
    "TRACE_FIELD_RE",
    "AccessCol",
    "RunCol",
]

# ── 操作类型集合（来源 base_parser.py:20-23）──────────────────────────────
SDK_GET_OPS = frozenset({OpType.DS_KV_CLIENT_GET, OpType.DS_OBJECT_CLIENT_GET})
WORKER_GET_OPS = frozenset({OpType.DS_POSIX_GET})
SDK_SET_OPS = frozenset({OpType.DS_KV_CLIENT_SET})
WORKER_SET_OPS = frozenset({OpType.DS_POSIX_CREATE, OpType.DS_POSIX_PUBLISH})

# ── 切段门禁（来源 base_parser.py:24-25）─────────────────────────────────
ACCESS_LOG_MIN_PARTS = 13
RUN_LOG_MIN_PARTS = 8

# ── 行闸门关键字（来源 worker_info_parser.py:55-66）──────────────────────
# 基础关键字（WorkerInfoParser 使用）
BASE_KEYWORDS = (
    "URMA_ELAPSED_TOTAL", "Processing CreateMetaReq", "Remote get request", "Processing pull object[",
    "elapsed ms:", "Master query done",
)

# 细分耗时关键字（每个关键字对应一个明确的 Worker info label）
TIMED_KEYWORDS = (
    "totalCost:", "Worker to master rpc QueryMeta:",
    "ProcessGetObjectRequest:", "worker SafeObject WLock:",
    "[Get/RemotePull] finish", "[Get] Remote done",
    "QueryMeta done", "[ZMQ_RPC_FRAMEWORK_SLOW]",
)

ALL_KEYWORDS = BASE_KEYWORDS + TIMED_KEYWORDS

# access 类解析器的行关键字（来源 sdk_access_log_parser.py:22 /
# worker_access_log_parser.py:22；扫描器原先绕道解析器类去拿）
SDK_ACCESS_KEYWORDS = ("DS_KV_CLIENT_GET", "DS_OBJECT_CLIENT_GET", "DS_KV_CLIENT_SET")
WORKER_ACCESS_KEYWORDS = ("DS_POSIX_GET", "DS_POSIX_CREATE", "DS_POSIX_PUBLISH")

# ── 正则门禁 ─────────────────────────────────────────────────────────────
# trace_id / ip:port 抽取（来源 base_parser.py:66-77 与 worker_info_parser.py:69）
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
TRACE_FIELD_RE = re.compile(
    r"\btrace[_-]?id\s*(?:=|:)\s*(?P<trace>[^,\s\]\}\)]+)",
    re.IGNORECASE,
)
IP_ENDPOINT_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")


# ── 切段位次（来源 base_parser.py:95-126，原为 LogParser 的嵌套类）────────
class AccessCol(IntEnum):
    """Access 格式日志列索引

    格式: timestamp | level | filename:lineno | pod_name | pid:tid | trace_id | cluster_name | status_code | handle | elapsed | size | req_msg | resp_msg
    """
    TIMESTAMP = 0
    LEVEL = 1
    FILENAME = 2
    POD_NAME = 3
    PID_TID = 4
    TRACE_ID = 5
    CLUSTER_NAME = 6
    STATUS_CODE = 7
    HANDLE = 8
    ELAPSED = 9
    SIZE = 10
    REQ_MSG = 11
    RESP_MSG = 12


class RunCol(IntEnum):
    """Run 格式日志列索引

    格式: timestamp | level | filename:lineno | pod_name | pid:tid | trace_id | cluster_name | msg
    """
    TIMESTAMP = 0
    LEVEL = 1
    FILENAME = 2
    POD_NAME = 3
    PID_TID = 4
    TRACE_ID = 5
    CLUSTER_NAME = 6
    MSG = 7
