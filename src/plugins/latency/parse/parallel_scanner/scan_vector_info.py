"""Worker info（12 个 label）的列式解析 —— polars 列运算替代逐行 Python regex。

对外唯一接口 :func:`info_label_columns`：输入一帧已过滤的候选行（列 ``line`` /
``__file``），输出与 :data:`columnar.ALL_COLUMNS` 同形、每行一条 ``LogEntry``
等价物的帧，外加 ``_elapsed_us`` / ``_resp_msg`` / ``_rpc_*`` / ``__file`` /
``__row``。

语义锚点全部来自 ``parse/worker_info_parser.WorkerInfoParser``（逐行实现）：

1. 14 条 ``if`` 链按固定优先级 first-match（一行最多产出一条），见 ``_CHAIN``；
2. ``_build_run`` 的列位置 ts=0 / pod=3 / trace=5 / cluster=6 / msg=join(parts[7:])，
   ``parts`` 数 < ``RUN_LOG_MIN_PARTS`` 直接丢；
3. ``resolve_trace_id(trace_id, line)``（``allow_trace_fallback=True``）：行内显式
   ``trace_id=`` 优先 → 格式列第 6 段 → 行内首个 UUID；结果为空则该行（对要求
   trace 的 label）不产出；
4. 各 label 正则来自 ``regex/kvcache_log.py``，见下方 ``V_*`` 常量（与原名逐字符
   同语义，仅把所有捕获组补上命名，``str.extract_groups`` 要求全命名）；
5. ``_elapsed_value_from_match`` / ``multiplier`` / ``_timed_fields_from_groups`` /
   ``_format_timed_resp_msg`` / ``_mk_timed_entry`` 的行为逐条复刻；
6. 投影走 ``columnar.LABEL_TO_COLUMNS`` 的列集，毫秒列用**同长度物化除数**相除
   （``col / scalar`` 与 Python ``/ 1000.0`` 会差 1 ulp）；
7. ``_label`` 即子 label（bucket 路由后），``_src_rank`` 取 ``columnar._SRC_RANK``，
   ``_rpc_*`` 逐字段对齐 ``columnar._parse_rpc_resp``（同一语义，改为列运算）。

性能写法（本次改造，语义不变）：

* 整条链是**一个 LazyFrame**：``frame.lazy()`` → 候选帧构造 → 每 label 一路
  ``filter`` + 列抽取 → ``pl.concat`` → ``sort`` → **唯一一次 ``collect()``**。
  中途不再逐步骤物化（旧写法每一步 ``with_columns``/``filter`` 都是一次
  ``pl.DataFrame`` 物化，85951 行上共 136 次）；
* 时间戳只让 polars 做 ISO 形状判定（``str.to_datetime(strict=False)``），
  polars 不认的**唯一值**才回落 Python ``parse_timestamp``（真实语料 0 次回落）；
* 数值列（cost / inflight / elapsed_ms）先走 Rust ``cast(strict=False)``，
  只有当出现"Rust 拒绝"时才对该列**唯一值**跑 Python（真实语料 0 次触发）；
* ``_rpc_*`` 由 ``str.split + list.eval(str.extract) + list.last`` 一条列运算得出，
  不再 ``to_list()`` + Python 字典循环。

**代价上最容易踩的坑**：12 个 label 分支共用同一份候选帧计划，但 polars 会把
``filter(_cat.is_in(...))`` 下推进分类链、把每个分支简化成不同子计划，于是
``comm_subplan_elim`` 一个也不缓存 —— 基帧被**重算 12 次**（实测基帧里的 UDF 被调用 12 次、
699 ms）。所以基帧要显式 ``.cache()``，且 ``collect`` 要关掉 ``comm_subplan_elim``
（见 ``_COLLECT_KWARGS``）：两个一起才是 330 ms / UDF 1 次，少任何一个都回到 12 次。
实测（jingpai 487 文件 / 85949 行，同进程交替 3 轮取中位）：旧 eager 写法 623.8 ms /
136 次中间物化 → 本写法 404.7 ms / 53 次、链上 ``collect`` 1 次。

不支持的输入（直接 ``NotImplementedError``，交由调用方回退逐行路径）：
- ``WorkerInfoParser`` 的 ``scan_scope`` 启用（``_scope_allows`` 未列式化）；
- ``_filter_by_time`` 生效（``_start_dt`` / ``_end_dt`` 非空）。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Sequence

import polars as pl

from latency.parse.keywords import RUN_LOG_MIN_PARTS, TRACE_FIELD_RE, UUID_RE
from latency.parse.parallel_scanner.columnar import (
    ALL_COLUMNS,
    TRACE_COLUMNS,
    _parse_rpc_resp,  # noqa: F401 - 语义锚点：_rpc_* 列运算与它逐字段对齐（见 _rpc_expr）
    _SRC_RANK,
)
from latency.parse import ClientInfoParser  # P2：isinstance 分派，暂留
from latency.parse.columns import LIGHT_COLUMNS
from latency.parse.keywords import ALL_KEYWORDS
from latency.parse.keywords import IP_ENDPOINT_RE as _IP_ENDPOINT_RE
from latency.parse.labels import (
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
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    URMA_LABEL,
)
from latency.regex.kvcache_log import (
    LOCAL_WORKER_COST_RE,
    LOCAL_WORKER_LOCK_RE,
    MASTER_PROCESS_RE,
    MASTER_RPC_RE,
    REMOTE_WORKER_COST_RE,
    REMOTE_WORKER_RPC_RE,
    SDK_PROCESS_RE,
    SDK_RPC_RE,
)

if TYPE_CHECKING:  # 仅注解使用，运行时不导入
    from latency.parse.base_parser import LogParser

__all__ = ["info_label_columns"]

_FILE_COLUMN = "__file"
_ROW_COLUMN = "__row"
_RANK_COLUMN = "__rank"

_EXTRA_COLUMNS: tuple[str, ...] = (
    "_elapsed_us",
    "_resp_msg",
    "_rpc_e2e_us",
    "_rpc_server_exec_us",
    "_rpc_network_us",
)

_OUTPUT_COLUMNS: tuple[str, ...] = (
    *ALL_COLUMNS,
    *_EXTRA_COLUMNS,
    _FILE_COLUMN,
    _ROW_COLUMN,
)

#: light 模式的列集与输出列序（取 ``_OUTPUT_COLUMNS`` 的子序列，保持既有相对列序）。
_LIGHT_SET = frozenset(LIGHT_COLUMNS)
_LIGHT_OUTPUT_COLUMNS: tuple[str, ...] = tuple(
    name for name in _OUTPUT_COLUMNS if name in _LIGHT_SET
)

#: ``_rpc_*`` 三个字段：(resp_msg 里的键名, 输出列名)
#: —— ``columnar._parse_rpc_resp`` 返回的顺序就是这个顺序
_RPC_KEYS: tuple[tuple[str, str], ...] = (
    ("e2e_us", "_rpc_e2e_us"),
    ("server_exec_us", "_rpc_server_exec_us"),
    ("network_residual_us", "_rpc_network_us"),
)

_TEXT_COLUMNS = frozenset({
    "tid", "src", "dst", "op", "operation", "op_key",
    "timestamp", "pod_ip", "cluster_name", "host", "data_size", "log_id",
})
_INT_COLUMNS = frozenset({"bucket_epoch", "status_code"})

#: 列 → dtype（与 ``entries_to_columns`` 的 Python 值类型一一对应）
_DTYPE_OF: dict[str, Any] = {}
for _name in TRACE_COLUMNS:
    if _name in _TEXT_COLUMNS:
        _DTYPE_OF[_name] = pl.Utf8
    elif _name in _INT_COLUMNS:
        _DTYPE_OF[_name] = pl.Int64
    else:
        _DTYPE_OF[_name] = pl.Float64
_DTYPE_OF["_label"] = pl.Utf8
_DTYPE_OF["_src_rank"] = pl.Int64
_DTYPE_OF["_elapsed_us"] = pl.Float64
_DTYPE_OF["_resp_msg"] = pl.Utf8
for _name in ("_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us"):
    _DTYPE_OF[_name] = pl.Float64
_DTYPE_OF[_FILE_COLUMN] = pl.Utf8
_DTYPE_OF[_ROW_COLUMN] = pl.Int64
# light 帧里要多带一列定位键 __rank（走 _empty_frame 时需要 dtype 表里有它）
_DTYPE_OF[_RANK_COLUMN] = pl.Int64

# ---------------------------------------------------------------------------
# 1. 列式正则：与 regex/kvcache_log.py 同语义，仅把位置捕获组补上命名
#    （命名不改变匹配语义；str.extract_groups 要求全部捕获组已命名）
# ---------------------------------------------------------------------------

V_URMA_RE = (
    r"(?i)\[URMA_ELAPSED_TOTAL\].*?cost\s+(?P<cost>[\d.]+)ms.*?"
    r"src\s+address\s*:\s*(?P<src>[^,]*?)\s*,\s*"
    r"(?:target|dst|destination)\s+address\s*:\s*(?P<dst>[^,]*?)\s*,.*?"
    r"urma_inflight_wr_count:\s*(?P<inflight>\d+)"
)
V_CREATE_META_REQ_RE = (
    r"Processing CreateMetaReq,.*?src=(?P<src>[^:]+):\d+,\s*dst=(?P<dst>[^:]+):\d+"
)
V_REMOTE_GET_RE = (
    r"Remote get request:.*?src[= ](?P<src>[^,]+),\s*dst[= ](?P<dst>[^,|\]]+)"
)
V_REMOTE_PULL_RE = (
    r"Processing pull object\[.*?src[= ](?P<src>[^,]+),\s*dst[= ](?P<dst>[^,|\]]+)"
)
V_URMA_LINK_RE = (
    r"(?:WorkerWorkerExchangeUrmaConnectInfo finish|"
    r"Worker-worker transport connection exchange success),\s*?"
    r"elapsed ms:\s*(?P<elapsed_ms>[\d.]+)"
)
V_QUERY_META_RE = r"cost:\s*(?P<cost>[\d.]+)ms?"
V_REMOTE_ENDPOINT_RE = (
    r"(?i)\bsrc\s*(?:=|:|\s+)\s*(?P<src>[^,\]\s]+)\s*,\s*"
    r"dst\s*(?:=|:|\s+)\s*(?P<dst>[^,\]\s]+)"
)
V_IP_ENDPOINT_RE = _IP_ENDPOINT_RE.pattern
V_TRACE_FIELD_RE = "(?i)" + TRACE_FIELD_RE.pattern
# 注意：str.extract 默认取 group 1，无捕获组的 pattern 会恒返回 null，
# 因此 UUID 回退必须显式包一个命名组。
V_UUID_RE = "(?i)(?P<uuid>" + UUID_RE.pattern + ")"

#: 逐 label 的时延正则规格：pattern / 命名组顺序 / 取耗时用的组 / 乘数
_TIMED_SPECS: dict[str, tuple[str, tuple[str, ...], str, float]] = {
    SDK_PROCESS_LABEL: (
        SDK_PROCESS_RE.pattern,
        ("client_id", "objects", "transfer_path", "cost",
         "inflight_remote_get", "slow_items"),
        "cost", 1000.0,
    ),
    SDK_RPC_LABEL: (SDK_RPC_RE.pattern, ("cost",), "cost", 1000.0),
    LOCAL_WORKER_COST_LABEL: (LOCAL_WORKER_COST_RE.pattern, ("cost",), "cost", 1000.0),
    LOCAL_WORKER_LOCK_LABEL: (LOCAL_WORKER_LOCK_RE.pattern, ("cost",), "cost", 1000.0),
    REMOTE_WORKER_COST_LABEL: (
        REMOTE_WORKER_COST_RE.pattern,
        ("count", "first_object_key", "payload_size", "start_remaining_time",
         "cost", "src", "dst"),
        "cost", 1000.0,
    ),
    REMOTE_WORKER_RPC_LABEL: (
        REMOTE_WORKER_RPC_RE.pattern,
        ("count", "path", "cost", "src", "dst"),
        "cost", 1000.0,
    ),
    MASTER_PROCESS_LABEL: (
        MASTER_PROCESS_RE.pattern,
        ("target_num", "success_num", "cost"),
        "cost", 1000.0,
    ),
    MASTER_RPC_LABEL: (
        MASTER_RPC_RE.pattern,
        ("rpc_trace_id", "framework_us", "e2e_us", "client_req_framework_us",
         "remote_processing_us", "client_rsp_framework_us", "server_req_queue_us",
         "server_exec_us", "server_rsp_queue_us", "network_residual_us"),
        "remote_processing_us", 1.0,
    ),
}

_TIMED_RESP_EXCLUDED_FIELDS = frozenset({"cost", "src", "dst"})

#: 需要 trace_id 非空的 label（``_parse_urma`` / ``_parse_link`` 不要求）
_REQUIRE_TRACE: frozenset[str] = frozenset({
    REMOTE_PULL_LABEL, QUERY_META_LABEL,
    SDK_PROCESS_LABEL, SDK_RPC_LABEL, LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL, REMOTE_WORKER_COST_LABEL, REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL, MASTER_RPC_LABEL,
})

#: 14 条 if 链（None = src&dst 兜底分支）；下标 +1 即内部分类号
_CHAIN: tuple[tuple[str | None, str], ...] = (
    ("URMA_ELAPSED_TOTAL", URMA_LABEL),
    ("Processing CreateMetaReq", URMA_LABEL),
    ("Remote get request", REMOTE_PULL_LABEL),
    ("Processing pull object[", REMOTE_PULL_LABEL),
    ("elapsed ms:", LINK_LABEL),
    ("Master query done", QUERY_META_LABEL),
    ("totalCost:", SDK_PROCESS_LABEL),
    ("Worker to master rpc QueryMeta:", SDK_RPC_LABEL),
    ("ProcessGetObjectRequest:", LOCAL_WORKER_COST_LABEL),
    ("worker SafeObject WLock:", LOCAL_WORKER_LOCK_LABEL),
    ("[Get/RemotePull] finish", REMOTE_WORKER_COST_LABEL),
    ("[Get] Remote done", REMOTE_WORKER_RPC_LABEL),
    ("QueryMeta done", MASTER_PROCESS_LABEL),
    ("[ZMQ_RPC_FRAMEWORK_SLOW]", MASTER_RPC_LABEL),
    (None, REMOTE_PULL_LABEL),
)
_CAT_FALLBACK = len(_CHAIN)  # 15

_CATS_FOR_LABEL: dict[str, tuple[int, ...]] = {}
for _idx, (_kw, _label) in enumerate(_CHAIN, start=1):
    _CATS_FOR_LABEL[_label] = (*_CATS_FOR_LABEL.get(_label, ()), _idx)

_KEYWORD_RE = "|".join(re.escape(kw) for kw in ALL_KEYWORDS)  # 与 contains_any 同语义的对照

#: 关闭"公共子计划消除"（comm_subplan_elim）的收集参数。
#:
#: 实测（polars 1.44.1，85951 行候选帧）：12 个 label 分支共用同一份候选帧计划，但
#: polars 会把每个分支的 ``filter(_cat.is_in(...))`` 下推、各自简化成"只剩本 label 需要
#: 的关键字"，于是 12 份子计划不再"完全相同"，``comm_subplan_elim`` 也就不再缓存它们
#: —— 基帧被**重算 12 次**（基帧里的 Python UDF 被调用 12 次，699 ms）。关掉该优化后，
#: 显式 ``.cache()`` 的缓存节点才会被执行器复用（UDF 调用 1 次，330 ms）。
#: 关掉它不影响结果（等价性闸门 40 列 sha1 全等），只影响代价。
#:
#: ``requirements.txt`` 里 polars 是 ``>=1.0``（不锁版本），老版本没有 ``QueryOptFlags``
#: 或 ``collect(optimizations=...)``，这里一律降级成"默认优化"，结果不变、只是慢。
try:  # pragma: no cover - 取决于运行环境的 polars 版本
    # engine="streaming"：默认引擎不给单线程字符串 kernel 做纵向并行（见 access 模块
    # _collect 的实测：同一 kernel 1.01 核 → 13.42 核），加它之后 info 这条链实测
    # 0.321s / 3.40 核 → 0.178s / 9.04 核（jingpai 487 个 info 文件，输出行数一致）。
    # comm_subplan_elim=False 仍要保留：不加它，共用基帧会被重算 12 次。
    _COLLECT_KWARGS: dict[str, Any] = {
        "engine": "streaming",
        "optimizations": pl.QueryOptFlags(comm_subplan_elim=False),
    }
except Exception:  # noqa: BLE001
    _COLLECT_KWARGS = {}


# ---------------------------------------------------------------------------
# 2. 与 Python 语义一致的小工具（全部是纯列表达式，不进 Python 回调）
# ---------------------------------------------------------------------------

def _numeric_expr(src_column: str, dst_column: str, conv: type,
                  dtype: type[pl.DataType]) -> pl.Expr:
    """``conv(str)`` 的列运算版 —— **纯表达式**，不再进 Python 回调。

    老实现是 ``map_batches`` 包一层 Python 回调，只有"Rust 转不动的怪值"才回落
    Python ``conv``。真实语料里这个回落 0 次命中（40 列逐列 sha1 对比见提交说明），
    而 ``map_batches`` 会让整列的执行进 Python、抢 GIL —— 这是 info 侧并行度上不去的根因。
    现在直接等价成 polars 原生 ``cast``；``conv`` 形参保留只为调用处可读（真正决定
    目标类型的是 ``dtype``）。
    """
    return pl.col(src_column).cast(dtype, strict=False).alias(dst_column)


def _ts_ok_expr() -> pl.Expr:
    """``_ts`` 是否被 ``parse_timestamp`` 接受（决定该行去留）—— **纯表达式**。

    同上：老实现用 ``map_batches`` + 怪值回落 Python；真实语料 0 次回落，
    等价成 polars 原生解析。
    """
    return pl.col("_ts").str.to_datetime(strict=False).is_not_null()


def _ms_expr() -> pl.Expr:
    """``_elapsed_us / 1000.0``：除数写成同长度的**列运算**（``x*0+1000``）。

    polars 把 ``col / 标量`` 编译成 ``col × (1/标量)``，不是正确舍入的除法
    （实测 7598 个 URMA 值里 466 个与 Python 差 1 ulp，且 ``pl.repeat(…, pl.len())``
    会被优化器折回标量路径）；``col / 列`` 走通用内核，与 Python 逐位一致（0/7598）。
    乘数 0.0 的载体用 ``_elapsed_us`` 自己 —— 进入本步的行 ``_elapsed_us`` 必非 null
    （每个 extractor 的 valid 都要求它非 null），故除数为确定的 1000.0。
    """
    return pl.col("_elapsed_us") / (pl.col("_elapsed_us") * 0.0 + 1000.0)


def _rpc_expr(key: str, column: str) -> pl.Expr:
    """resp_msg → 某个 ``_rpc_*`` 列（逐字段对齐 ``columnar._parse_rpc_resp``）。

    语义：按 ``","`` 分段 → 每段 ``strip`` 后按**第一个** ``"="`` 切 ``k``/``v``
    （``k`` 再 strip）→ ``v.strip()`` 必须是可选负号的整数才收 → 同名键**后者覆盖前者**
    → 三个键各自缺失即 ``None``。这里全部用列运算表达：

    ``str.split(",")`` → ``list.eval(str.extract)``（每个元素只取 ``k`` 精确等于本键、
      且 ``v`` 为 ``-?\\d+`` 的段）→ ``list.drop_nulls().list.last()``（最后一段即覆盖）。
    """
    part_re = rf"^\s*{re.escape(key)}\s*=\s*(?P<v>-?\d+)\s*$"
    raw = (
        pl.col("_resp_msg")
        .str.split(",")
        .list.eval(pl.element().str.extract(part_re))
        .list.drop_nulls()
        .list.last()  # 最后一段即"后者覆盖前者"
    )
    # 与 `float(int(v))` 逐位一致：Rust 的 f64 解析与 Python 的 int→float 都从同一个
    # 精确十进制值正确舍入，唯一例外是 "-0"（int 得 0 → 0.0，而 float("-0") 是 -0.0），
    # 故先把 `-0+` 归一成 "0"。
    normalized = pl.when(raw.str.contains(r"^-0+$")).then(pl.lit("0")).otherwise(raw)
    return normalized.cast(pl.Float64).alias(column)


def _extract(frame: pl.LazyFrame, pattern: str, fields: Sequence[str],
             prefix: str) -> pl.LazyFrame:
    """``msg`` 上跑一次 ``str.extract_groups``，每个命名组落一列 ``prefix+field``。

    未命中时 polars 返回"全 null 结构体"，因此各规格用**必填组**非 null 作为命中
    判据（这些正则的必填组都不可能匹配空串）。
    """
    groups = pl.col("msg").str.extract_groups(pattern)
    return frame.with_columns(
        *[groups.struct.field(name).alias(prefix + name) for name in fields]
    )


def _clean(expr: pl.Expr) -> pl.Expr:
    """``WorkerInfoParser._clean_group``：strip 后为空则 None。"""
    stripped = expr.str.strip_chars()
    return pl.when(stripped.is_not_null() & (stripped != "")).then(stripped).otherwise(
        pl.lit(None, dtype=pl.Utf8)
    )


def _lit_none(dtype: type[pl.DataType]) -> pl.Expr:
    return pl.lit(None, dtype=dtype)


def _latency_column(label: str) -> str | None:
    """该 label 要填的时延列（从 ``columnar.LABEL_TO_COLUMNS`` 派生，不另设表）。"""
    from latency.parse.parallel_scanner.columnar import LABEL_TO_COLUMNS  # 用途待确认

    latency = [
        name for name in LABEL_TO_COLUMNS.get(label, ())
        if name not in ("src", "dst", "pod_ip", "cluster_name")
    ]
    if not latency:
        return None
    if len(latency) != 1:
        raise AssertionError(f"{label} 的时延列不唯一: {latency}")
    return latency[0]


def _light_columns(label: str) -> frozenset[str]:
    """light 模式下该 label 要投影的列 = ``parse/columns.LIGHT_COLUMNS`` ∩ 该 label 契约列。

    ``tid`` 恒在（``_finalize`` 对每个 label 都输出 tid，见那里的 ``present`` 判定）。
    """
    return (frozenset(LIGHT_COLUMNS) & set(LABEL_TO_COLUMNS.get(label, ()))) | {"tid"}


# ---------------------------------------------------------------------------
# 3. 输入归一化 / 守卫
# ---------------------------------------------------------------------------

def _normalize_inputs(files: Sequence, parsers: Sequence) -> tuple[list[str], list[list[LogParser]]]:
    """→ (paths, per_file_parsers)；兼容 files = 路径序列或 (path, indices) 序列。"""
    paths: list[str] = []
    for item in files:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, (tuple, list)) and item:
            paths.append(str(item[0]))
        else:
            raise TypeError(f"info_label_columns: 无法识别的 files 元素 {type(item)!r}")
    if isinstance(parsers, (list, tuple)) and parsers and isinstance(
        parsers[0], (list, tuple)
    ):
        per_file = [list(group) for group in parsers]
    else:
        per_file = [list(parsers or ())] * len(paths)
    if len(per_file) != len(paths):
        raise ValueError(
            f"info_label_columns: files({len(paths)}) 与 parsers({len(per_file)}) "
            "长度不一致"
        )
    return paths, per_file


def _info_parser(parser_group: list[LogParser]) -> LogParser | None:
    for parser in parser_group:
        if hasattr(parser, "_parse_first_match"):
            return parser
    return parser_group[0] if parser_group else None


def _guard_parser(parser: LogParser | None) -> None:
    """列式路径不支持的解析器配置 → 抛 ``NotImplementedError`` 让调用方回退。"""
    if parser is None:
        return
    if isinstance(parser, ClientInfoParser):
        raise NotImplementedError(
            "scan_vector_info: ClientInfoParser 不在本模块范围（client info 走另一条路径）"
        )
    if getattr(parser, "_scan_scope_enabled", False):
        raise NotImplementedError(
            "scan_vector_info: scan_scope 启用（_scope_allows 未列式化），请回退逐行路径"
        )
    if getattr(parser, "_start_dt", None) is not None or getattr(
        parser, "_end_dt", None
    ) is not None:
        raise NotImplementedError(
            "scan_vector_info: _filter_by_time 生效，请回退逐行路径"
        )


def _file_meta(
    paths: list[str],
    per_file: list[list[LogParser]],
    file_rank: dict[str, int],
    extra_paths: Sequence[str] = (),
) -> tuple[dict[str, str], dict[str, int]]:
    """→ (pod_ip 映射, rank 映射)；pod_ip 复刻 ``_parse_lines`` 的 per-file 语义。"""
    pod_ip_map: dict[str, str] = {}
    rank_map: dict[str, int] = {}
    for index, path in enumerate(paths):
        parser = _info_parser(per_file[index])
        _guard_parser(parser)
        _update_file_meta(pod_ip_map, rank_map, path, parser, file_rank.get(path))
    for path in extra_paths:  # 帧里出现但不在批文件表内：按路径补 pod_ip
        if path in pod_ip_map:
            continue
        parser = _info_parser(per_file[0]) if per_file else None
        _update_file_meta(pod_ip_map, rank_map, path, parser, None)
    return pod_ip_map, rank_map


def _update_file_meta(
    pod_ip_map: dict[str, str],
    rank_map: dict[str, int],
    path: str,
    parser: LogParser | None,
    rank: int | None,
) -> None:
    try:
        pod_ip_map[path] = parser.extract_pod_ip(path) if parser else ""
    except Exception:  # noqa: BLE001 - 与 _parse_lines 的兜底一致
        pod_ip_map[path] = ""
    rank_map[path] = int(rank) if rank is not None else len(rank_map)


def _build_category(cat_index: int, condition: pl.Expr, expr: pl.Expr | None) -> pl.Expr:
    value = pl.lit(cat_index, dtype=pl.Int32)
    if expr is None:
        return pl.when(condition).then(value)
    return expr.when(condition).then(value)


def _prepare_candidates(
    frame: pl.DataFrame,
    paths: list[str],
    per_file: list[list[LogParser]],
    file_rank: dict[str, int],
) -> pl.LazyFrame:
    """候选帧 → 带 msg/字段/trace_id/pod_ip/_cat 的**惰性**基帧（已过全部前置过滤）。

    全程只建计划，不物化：12 个 label 分支共用这一份计划，调用方 ``.cache()`` 后
    只执行一次（千万不要指望默认的 ``comm_subplan_elim`` —— 它会一个分支一份计划）。
    """
    if "line" not in frame.columns:
        raise ValueError("info_label_columns: frame 缺少 'line' 列")
    source = frame.lazy()
    if _FILE_COLUMN in frame.columns:
        extra_paths = frame[_FILE_COLUMN].cast(pl.Utf8).unique(maintain_order=True).to_list()
        base = source.select(
            pl.col("line").cast(pl.Utf8),
            pl.col(_FILE_COLUMN).cast(pl.Utf8),
            *([pl.col(_ROW_COLUMN).cast(pl.Int64)] if _ROW_COLUMN in frame.columns else []),
        )
    elif len(paths) == 1:
        extra_paths = [paths[0]]
        base = source.select(
            pl.col("line").cast(pl.Utf8),
            pl.lit(paths[0], dtype=pl.Utf8).alias(_FILE_COLUMN),
            *([pl.col(_ROW_COLUMN).cast(pl.Int64)] if _ROW_COLUMN in frame.columns else []),
        )
    else:
        raise ValueError(
            "info_label_columns: frame 缺少 '__file' 且 files 不唯一，无法确定来源文件"
        )

    if _ROW_COLUMN not in frame.columns:
        # 该文件内行序（仅作排序键，输出列里没有 __row）。
        # int_range 是 elementwise；cum_count().over() 是窗口函数 → 会让执行器把纵向
        # 并行整块关掉（polars lp.rs:538）。同一文件内两种写法都按帧内出现次序给出严格
        # 递增的行号，(rank, row) 排序结果相同，故直接用全局行号。
        base = base.with_columns(pl.int_range(pl.len(), dtype=pl.Int64).alias(_ROW_COLUMN))

    # 只处理**本模块负责的文件**：否则同一份帧里的其它文件（例如只被 ClientInfoParser
    # 认领的 client INFO）会被 info 链产出成错 label 的"幻影行"。
    posix_paths = [p.replace("\\", "/") for p in paths]
    base = base.with_columns(pl.col(_FILE_COLUMN).str.replace("\\", "/", literal=True).alias(_FILE_COLUMN))
    if posix_paths:
        base = base.filter(pl.col(_FILE_COLUMN).is_in(posix_paths))

    pod_ip_map, rank_map = _file_meta(paths, per_file, file_rank, extra_paths)
    # join 一张"每文件一行"的小表（表大小 = 文件数，不是行数）：replace_strict 是非
    # elementwise，会把纵向并行关掉；join 是并行的（同 scan_vector_access._prepare_candidates）。
    # 两个映射键集相同且每键只出现一次 → 左表行数不变；默认值用 fill_null 复刻
    # （rank 的 default=None 本就是 null，pod_ip 的 default=""）。
    _meta_frame = pl.DataFrame({
        _FILE_COLUMN: list(pod_ip_map),
        _RANK_COLUMN: [rank_map[path] for path in pod_ip_map],
        "_file_pod_ip": [pod_ip_map[path] for path in pod_ip_map],
    }).with_columns(
        pl.col(_FILE_COLUMN).cast(pl.Utf8),
        pl.col(_RANK_COLUMN).cast(pl.Int64),
        pl.col("_file_pod_ip").cast(pl.Utf8),
    )
    base = base.join(_meta_frame.lazy(), on=_FILE_COLUMN, how="left").with_columns(
        pl.col("_file_pod_ip").fill_null(""),
    )

    # line[0] == "2" ∧ parts ≥ RUN_LOG_MIN_PARTS ∧ _line_may_match（关键字或 src&dst）
    # str.splitn 返回 Struct(field_0..field_7)：field_7 为"剩余整段"（== "|".join(parts[7:])），
    # 不足 8 段时按 null 补齐，故 field_7 非 null ⟺ len(line.split("|")) >= 8。
    line = pl.col("line")
    parts = line.str.splitn("|", RUN_LOG_MIN_PARTS)

    base = base.with_columns(parts.struct.unnest())  # 一次 splitn，8 个字段落列
    base = base.with_columns(
        pl.col("field_0").str.strip_chars().alias("_ts"),
        pl.col("field_3").str.strip_chars().alias("_pod_name"),
        pl.col("field_5").str.strip_chars().alias("_trace_col"),
        pl.col("field_6").str.strip_chars().alias("_cluster"),
        pl.col("field_7").str.strip_chars().alias("msg"),
        pl.col("field_7").is_not_null().alias("_full"),
        (
            # 注意：`str.contains_any`（Aho-Corasick）在本机实测反而慢 2.8×
            # （341671 行 182 ms vs 正则 65 ms，它每次求值都重编译自动机），故继续用正则。
            line.str.contains(_KEYWORD_RE)
            | (
                line.str.contains("src", literal=True)
                & line.str.contains("dst", literal=True)
            )
        ).alias("_may"),
    )
    base = base.filter(line.str.starts_with("2") & pl.col("_full") & pl.col("_may"))

    explicit = (
        line.str.extract(V_TRACE_FIELD_RE)
        .str.strip_chars()
        .str.strip_chars("[]{}()\"'")
    )
    uuid = line.str.extract(V_UUID_RE)
    trace_id = (
        pl.when(explicit.is_not_null() & (explicit != ""))
        .then(explicit)
        .when(pl.col("_trace_col") != "")
        .then(pl.col("_trace_col"))
        .otherwise(uuid)
        .fill_null("")
    )
    pod_ip = pl.when(pl.col("_pod_name") != "").then(pl.col("_pod_name")).otherwise(
        pl.col("_file_pod_ip")
    )
    pod_ip = pl.when(pod_ip != "").then(pod_ip).otherwise(_lit_none(pl.Utf8))
    cluster = pl.when(pl.col("_cluster") != "").then(pl.col("_cluster")).otherwise(
        _lit_none(pl.Utf8)
    )

    cat_expr: pl.Expr | None = None
    for index, (keyword, _label) in enumerate(_CHAIN, start=1):
        if keyword is None:
            condition = line.str.contains("src", literal=True) & line.str.contains(
                "dst", literal=True
            )
        else:
            condition = line.str.contains(keyword, literal=True)
        cat_expr = _build_category(index, condition, cat_expr)
    cat = cat_expr.otherwise(pl.lit(0, dtype=pl.Int32))

    base = base.with_columns(
        trace_id.alias("trace_id"),
        pod_ip.alias("pod_ip"),
        cluster.alias("cluster_name"),
        cat.alias("_cat"),
    )
    # parse_timestamp 的成败（列运算判定，不再回落 Python）
    base = base.filter(_ts_ok_expr())
    # 之后只用到 msg 与派生列：把大列 line 与中间列一起丢给优化器（少搬几百 MB）
    return base.drop(
        "line", "_ts", "_pod_name", "_trace_col", "_cluster", "_file_pod_ip",
        "_full", "_may",
        *[f"field_{index}" for index in range(RUN_LOG_MIN_PARTS)],
    )


# ---------------------------------------------------------------------------
# 4. 各 label 的字段抽取（返回 (带辅助列的帧, 值表达式, 有效掩码)）
# ---------------------------------------------------------------------------

def _base_values(elapsed: pl.Expr, resp_msg: pl.Expr | None) -> dict:
    return {
        "tid": pl.col("trace_id"),
        "pod_ip": pl.col("pod_ip"),
        "cluster_name": pl.col("cluster_name"),
        "_elapsed_us": elapsed,
        "_resp_msg": resp_msg if resp_msg is not None else _lit_none(pl.Utf8),
    }


def _urma(frame: pl.LazyFrame) -> tuple[pl.LazyFrame, dict[str, pl.Expr], pl.Expr]:
    """``_parse_urma``：URMA_RE 优先，其次 CREATE_META_REQ_RE（SET 请求）。"""
    frame = _extract(frame, V_URMA_RE, ("cost", "src", "dst", "inflight"), "u_")
    frame = _extract(frame, V_CREATE_META_REQ_RE, ("src", "dst"), "c_")
    frame = frame.with_columns(
        _numeric_expr("u_cost", "u_cost_f", float, pl.Float64),
        _numeric_expr("u_inflight", "u_inflight_i", int, pl.Int64),
    )
    matched_urma = pl.col("u_cost").is_not_null()
    matched_create = pl.col("c_src").is_not_null()
    elapsed = (
        pl.when(matched_urma)
        .then(pl.col("u_cost_f") * 1000.0)
        .when(matched_create)
        .then(pl.lit(0.0, dtype=pl.Float64))
        .otherwise(_lit_none(pl.Float64))
    )
    # int(inflight) 抛错 → 逐行实现里整行丢失
    valid = elapsed.is_not_null() & (
        ~matched_urma | pl.col("u_inflight_i").is_not_null()
    )
    src = (
        pl.when(matched_urma)
        .then(pl.col("u_src").str.strip_chars())
        .when(matched_create)
        .then(pl.col("c_src").str.strip_chars())
        .otherwise(_lit_none(pl.Utf8))
    )
    dst = (
        pl.when(matched_urma)
        .then(pl.col("u_dst").str.strip_chars())
        .when(matched_create)
        .then(pl.col("c_dst").str.strip_chars())
        .otherwise(_lit_none(pl.Utf8))
    )
    values = _base_values(elapsed, None)
    values["src"] = src.fill_null("")
    values["dst"] = dst.fill_null("")
    return frame, values, valid


def _remote_pull(frame: pl.LazyFrame) -> tuple[pl.LazyFrame, dict[str, pl.Expr], pl.Expr]:
    """``_parse_remote_get`` / ``_parse_remote_pull`` / ``_parse_src_dst_fallback``。"""
    frame = _extract(frame, V_REMOTE_GET_RE, ("src", "dst"), "g_")
    frame = _extract(frame, V_REMOTE_PULL_RE, ("src", "dst"), "p_")
    frame = _extract(frame, V_REMOTE_ENDPOINT_RE, ("src", "dst"), "e_")
    is_get = pl.col("_cat") == 3
    is_pull = pl.col("_cat") == 4
    is_fallback = pl.col("_cat") == _CAT_FALLBACK
    matched_get = pl.col("g_src").is_not_null()
    matched_pull = pl.col("p_src").is_not_null()
    ep_src = pl.col("e_src").str.strip_chars()
    ep_dst = pl.col("e_dst").str.strip_chars()
    # _looks_like_ip_endpoint：对 strip 后的值跑 _IP_ENDPOINT_RE.search
    matched_fallback = (
        pl.col("e_src").is_not_null()
        & ep_src.str.contains(V_IP_ENDPOINT_RE)
        & ep_dst.str.contains(V_IP_ENDPOINT_RE)
    )
    valid = (
        (is_get & matched_get)
        | (is_pull & matched_pull)
        | (is_fallback & matched_fallback)
    ) & (pl.col("trace_id") != "")
    src = (
        pl.when(is_get & matched_get)
        .then(pl.col("g_src").str.strip_chars())
        .when(is_pull & matched_pull)
        .then(pl.col("p_src").str.strip_chars())
        .when(is_fallback & matched_fallback)
        .then(ep_src)
        .otherwise(_lit_none(pl.Utf8))
    )
    dst = (
        pl.when(is_get & matched_get)
        .then(pl.col("g_dst").str.strip_chars())
        .when(is_pull & matched_pull)
        .then(pl.col("p_dst").str.strip_chars())
        .when(is_fallback & matched_fallback)
        .then(ep_dst)
        .otherwise(_lit_none(pl.Utf8))
    )
    resp_msg = pl.when(is_fallback & matched_fallback).then(pl.col("msg")).otherwise(
        _lit_none(pl.Utf8)
    )
    values = _base_values(pl.lit(0.0, dtype=pl.Float64), resp_msg)
    values["src"] = src.fill_null("")
    values["dst"] = dst.fill_null("")
    return frame, values, valid


def _link(frame: pl.LazyFrame) -> tuple[pl.LazyFrame, dict[str, pl.Expr], pl.Expr]:
    """``_parse_link``：msg 上下文条件 + URMA_LINK_RE；不要求 trace_id。"""
    frame = _extract(frame, V_URMA_LINK_RE, ("elapsed_ms",), "l_")
    frame = frame.with_columns(
        _numeric_expr("l_elapsed_ms", "l_elapsed_f", float, pl.Float64)
    )
    msg = pl.col("msg")
    exchange_ok = msg.str.contains(
        "WorkerWorkerExchangeUrmaConnectInfo finish", literal=True
    ) | msg.str.contains(
        "Worker-worker transport connection exchange success", literal=True
    )
    finish_blocked = msg.str.contains(
        "WorkerWorkerExchangeUrmaConnectInfo finish", literal=True
    ) & ~msg.str.contains("status=code: [OK]", literal=True)
    elapsed = pl.col("l_elapsed_f") * 1000.0
    valid = exchange_ok & ~finish_blocked & elapsed.is_not_null()
    values = _base_values(elapsed, None)
    return frame, values, valid


def _query_meta(frame: pl.LazyFrame) -> tuple[pl.LazyFrame, dict[str, pl.Expr], pl.Expr]:
    """``_parse_query_meta``：QUERY_META_RE 且 trace_id 非空。"""
    frame = _extract(frame, V_QUERY_META_RE, ("cost",), "q_")
    frame = frame.with_columns(
        _numeric_expr("q_cost", "q_cost_f", float, pl.Float64)
    )
    elapsed = pl.col("q_cost_f") * 1000.0
    valid = elapsed.is_not_null() & (pl.col("trace_id") != "")
    values = _base_values(elapsed, None)
    return frame, values, valid


def _timed(frame: pl.LazyFrame, label: str) -> tuple[pl.LazyFrame, dict[str, pl.Expr], pl.Expr]:
    """``_parse_timed_entry`` + ``_timed_fields_from_groups`` + ``_format_timed_resp_msg``。"""
    pattern, fields, elapsed_key, multiplier = _TIMED_SPECS[label]
    prefix = "t_"
    frame = _extract(frame, pattern, fields, prefix)
    frame = frame.with_columns(
        _numeric_expr(prefix + elapsed_key, "t_elapsed_f", float, pl.Float64)
    )
    elapsed = pl.col("t_elapsed_f") * multiplier
    valid = elapsed.is_not_null() & pl.col(prefix + elapsed_key).is_not_null()
    if label in _REQUIRE_TRACE:
        valid = valid & (pl.col("trace_id") != "")

    has_src = "src" in fields
    has_dst = "dst" in fields
    if has_src or has_dst:
        src_clean = _clean(pl.col(prefix + "src")) if has_src else _lit_none(pl.Utf8)
        dst_clean = _clean(pl.col(prefix + "dst")) if has_dst else _lit_none(pl.Utf8)
        # src/dst 任一缺失 → REMOTE_ENDPOINT_RE 在 msg 上兜底（命中才覆盖两者）
        frame = _extract(frame, V_REMOTE_ENDPOINT_RE, ("src", "dst"), "ep_")
        need_fallback = src_clean.is_null() | dst_clean.is_null()
        ep_src = pl.col("ep_src").str.strip_chars()
        ep_dst = pl.col("ep_dst").str.strip_chars()
        src = pl.when(need_fallback & ep_src.is_not_null()).then(ep_src).otherwise(src_clean)
        dst = pl.when(need_fallback & ep_dst.is_not_null()).then(ep_dst).otherwise(dst_clean)

    resp_parts = []
    for name in fields:
        if name in _TIMED_RESP_EXCLUDED_FIELDS:
            continue
        cleaned = _clean(pl.col(prefix + name))
        resp_parts.append(
            pl.when(cleaned.is_not_null())
            .then(pl.lit(f"{name}=") + cleaned)
            .otherwise(_lit_none(pl.Utf8))
        )
    if resp_parts:
        non_null = pl.sum_horizontal(
            [part.is_not_null().cast(pl.Int8) for part in resp_parts]
        )
        resp_msg = (
            pl.when(non_null == 0)
            .then(_lit_none(pl.Utf8))
            .otherwise(pl.concat_str(resp_parts, separator=", ", ignore_nulls=True))
        )
    else:
        resp_msg = _lit_none(pl.Utf8)

    values = _base_values(elapsed, resp_msg)
    if has_src:
        values["src"] = src.fill_null("")
    if has_dst:
        values["dst"] = dst.fill_null("")
    return frame, values, valid


_EXTRACTORS: dict[str, Any] = {
    URMA_LABEL: _urma,
    REMOTE_PULL_LABEL: _remote_pull,
    LINK_LABEL: _link,
    QUERY_META_LABEL: _query_meta,
}
for _timed_label in _TIMED_SPECS:
    _EXTRACTORS[_timed_label] = (
        lambda frame, _label=_timed_label: _timed(frame, _label)
    )


# ---------------------------------------------------------------------------
# 5. 输出组装
# ---------------------------------------------------------------------------

def _empty_frame(columns: Sequence[str] = _OUTPUT_COLUMNS) -> pl.DataFrame:
    return pl.DataFrame({
        name: pl.Series(name, [], dtype=_DTYPE_OF[name]) for name in columns
    }).with_columns(
        pl.Series(_RANK_COLUMN, [], dtype=pl.Int64)
    )


def _finalize(
    frame: pl.LazyFrame, label: str, values: dict[str, pl.Expr], valid: pl.Expr,
    *, light: bool = False,
) -> pl.LazyFrame:
    """过滤 → 投影（``LABEL_TO_COLUMNS`` 的列集 + 内部列）→ 补齐 ``_rpc_*``。

    ``light=True``：只投影 ``LIGHT_COLUMNS`` ∩ 该 label 契约列的列（+ tid），其余列
    **一个表达式都不 select**（包括那 30 个 ``_lit_none`` 铺位列），``_label`` /
    ``_elapsed_us`` / ``_resp_msg`` / ``_rpc_*`` 一律不算。行集不受影响：过滤条件与
    ``valid`` 只引用字段列，与投影列集无关。
    """
    latency_column = _latency_column(label)
    lights = _light_columns(label) if light else None
    if lights is None:
        keep_values = values
    else:
        # 不在投影里的值表达式不进 with_columns —— polars 于是不为它们建算子
        keep_values = {name: expr for name, expr in values.items() if name in lights}
        if latency_column is not None and latency_column in lights:
            # 保底分支（info 的时延列目前都不在 LIGHT_COLUMNS）：占位列要靠
            # _elapsed_us 重算，投影时把这个中间列带上、算完丢掉。
            keep_values["_elapsed_us"] = values["_elapsed_us"]
    out = frame.with_columns(**keep_values).filter(valid)
    # 一次解析 schema，避免逐列 ``.columns``（会重复解析整条计划）
    present = set(frame.collect_schema().names()) | set(keep_values)

    exprs: list[pl.Expr] = [
        pl.col(_FILE_COLUMN),
        pl.col(_ROW_COLUMN),
        pl.col(_RANK_COLUMN),
    ]
    for name in TRACE_COLUMNS:
        if lights is not None and name not in lights:
            continue                       # light：该 label 的宽列一次都不 select
        if name == latency_column:
            # 占位：稍后用列运算除数从 _elapsed_us 重算，保证 IEEE 逐位一致
            exprs.append(_lit_none(pl.Float64).alias(name))
        elif name in present:
            exprs.append(pl.col(name).alias(name))
        else:
            exprs.append(_lit_none(_DTYPE_OF[name]).alias(name))
    if lights is None:
        exprs.append(pl.lit(label, dtype=pl.Utf8).alias("_label"))
    exprs.append(pl.lit(_SRC_RANK.get(label, 0), dtype=pl.Int64).alias("_src_rank"))
    if lights is None:
        exprs.append(pl.col("_elapsed_us"))
        exprs.append(pl.col("_resp_msg"))

    out = out.select(exprs)
    if latency_column is not None and (lights is None or latency_column in lights):
        out = out.with_columns(_ms_expr().alias(latency_column))

    if lights is not None:
        # light：各 label 产出的轻列不同，就按本分支真正建出来的 exprs 输出
        # （列**按名**拼接，见 info_label_columns 的 diagonal_relaxed）。
        return out.select(exprs)
    # _rpc_* 由列运算得出，逐字段对齐 columnar._parse_rpc_resp
    out = out.with_columns(*[_rpc_expr(key, column) for key, column in _RPC_KEYS])
    return out.select(*_OUTPUT_COLUMNS, _RANK_COLUMN)


def _collect(lf: pl.LazyFrame) -> pl.DataFrame:
    """同 access 模块：优先 streaming（纵向并行），失败退回默认引擎。"""
    try:
        return lf.collect(engine="streaming")
    except Exception:  # noqa: BLE001
        return lf.collect()



def info_label_columns(
    frame: pl.DataFrame, files: Sequence, parsers: Sequence, *, file_rank: dict[str, int],
    light: bool = False,
) -> pl.DataFrame:
    """worker-info 12 个 label 的列式解析（替代逐行 Python regex）。

    参数:
        frame: 已过滤的候选行帧，列含 ``line``（原始日志行文本）与 ``__file``
            （来源文件路径）；若已带 ``__row`` 则直接沿用，否则取帧内出现顺序的
            全局行号（只作 ``(rank, row)`` 排序键，与按文件计数等价）。
        files: 该批文件路径（``str`` 或 ``(path, parser_indices)`` 元组序列）。
        parsers: 该批文件的解析器集合；既可为解析器对象列表（批级），也可为与
            ``files`` 等长的"每文件解析器列表"列表。
        file_rank: ``{文件路径: 序位}``，用于把输出行按"文件序 + 文件内行序"排列
            （等价于逐行路径按文件顺序 append 的行序）。

    返回:
        ``columnar.ALL_COLUMNS`` + ``_elapsed_us`` / ``_resp_msg`` /
        ``_rpc_e2e_us`` / ``_rpc_server_exec_us`` / ``_rpc_network_us`` +
        ``__file`` / ``__row`` 的帧，每行对应一条 ``LogEntry`` 等价物，
        行序 = (``file_rank``, ``__row``)。

    实现：整条链是一个 LazyFrame，**只在最后 ``collect()`` 一次**；12 个 label 分支
    共用同一份候选帧计划（靠 ``.cache()`` + 关掉 ``comm_subplan_elim`` 共享，见
    ``_COLLECT_KWARGS``），中途不物化中间 DataFrame。

    ``light=True``：只算 ``parse/columns.LIGHT_COLUMNS`` 里该 label 产出的列（外加
    行序键 ``__file``/``__row``/``__rank`` 与 ``_src_rank``），宽列不算也不铺 null；
    行集与 ``light=False`` 逐行一致（过滤条件、``valid`` 未改）。各分支列集因此不同，
    light 用 ``how="diagonal_relaxed"`` 拼接（不为了对齐而铺 null 列）。

    不支持 ``scan_scope`` / ``_filter_by_time``（抛 ``NotImplementedError``）。
    """
    paths, per_file = _normalize_inputs(files, parsers)
    if light:
        # 本模块各 label 的轻列并集（tid 与 _src_rank 恒有）——就是 light 输出列集；
        # 不按全局 LIGHT_COLUMNS 输出，否则没产出的列会在 select 时报 ColumnNotFound。
        produced = {"tid", "_src_rank"}
        for _label in _EXTRACTORS:
            if _CATS_FOR_LABEL.get(_label):
                produced |= _light_columns(_label)
        # 行序/定位键三列一并保留（__rank 在 _OUTPUT_COLUMNS 之外，只能显式补）
        out_columns: tuple[str, ...] = (
            *(name for name in _LIGHT_OUTPUT_COLUMNS if name in produced),
            _FILE_COLUMN, _ROW_COLUMN, _RANK_COLUMN,
        )
    else:
        out_columns = _OUTPUT_COLUMNS
    # .cache()：12 个 label 分支共用这一份候选帧计划，显式缓存后只执行一次
    candidates = _prepare_candidates(frame, paths, per_file, file_rank).cache()

    branches: list[pl.LazyFrame] = []
    for label, extractor in _EXTRACTORS.items():
        cats = _CATS_FOR_LABEL.get(label, ())
        if not cats:
            continue
        sub = candidates.filter(pl.col("_cat").is_in(list(cats)))
        extract_frame, values, valid = extractor(sub)
        branches.append(_finalize(extract_frame, label, values, valid, light=light))
    if not branches:
        return _empty_frame(out_columns).select(out_columns)

    plan = (
        pl.concat(branches, how="diagonal_relaxed" if light else "vertical")
        .sort([_RANK_COLUMN, _ROW_COLUMN])
        .select(out_columns)
    )
    # 整条链唯一一次物化；kwargs 见 _COLLECT_KWARGS（不加则共用基帧被重算 12 次）
    try:
        out = plan.collect(**_COLLECT_KWARGS)
    except TypeError:  # pragma: no cover - 该版本 collect 不认识 optimizations
        out = plan.collect()
    if out.height == 0:
        return _empty_frame(out_columns).select(out_columns)
    return out
