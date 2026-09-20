"""access 三类记录（SDK access / Worker access / Client rpc）的**列运算**解析。

设计要点（性能）
----------------
**一个 label = 一条 lazy 链 + 一次 ``collect()``。** 早期实现是"每一步 eager 操作各跑
一遍"，实测在 207 万行上会触发 38 次计划执行（5.1 s）—— 因为每次执行都要把 519 MB 的
``line`` 列整体重算。现在：

1. 切列/门禁/派生全部写进同一张计划，``line`` 在链里尽早被 ``select`` 掉；
2. Python 兜底（时间戳非 ISO 形状、``isdigit`` 但 ``int()`` 失败的状态码）改成
   **探针 + 表达式**：先用一次只读单列的 ``select`` 拿"唯一可疑值"，数量非 0 才把映射
   写成 ``replace_strict`` 表达式；常见情况下探针结果为 0，链上不多一分钱。

语义契约（与老路径逐值对齐；等价性由 40 列逐列 sha1 闸门验证，见 commit 说明与报告）
------------------------------------------------------------------
* 段数闸门：access 13 段（``|`` ≥ 12）/ run 8 段（``|`` ≥ 7）；少一段即丢行。
* access 行：``splitn("|", 14)`` —— ``field_12`` 恰好是 ``parts[12]``，第 14 段丢弃
  （等价 Python ``line.split("|")`` 后只取前 13 段）。
* run 行：``field_7`` = 剩余整段 = ``"|".join(parts[7:])``（message 里可再含 ``|``）。
* ``trace_id``：格式列 → 行内显式 ``trace_id=`` → 行内首个 UUID；空则该行不产出。
* 时间戳：``parse_timestamp``（``fromisoformat(ts.replace(" ","T",1))``），失败丢行；
  ``timestamp`` 列 = ``str(datetime)``（微秒为 0 → 无小数位，否则恒 6 位）；
  ``bucket_epoch`` = 墙钟当 UTC 的 10s 对齐。
* 毫秒列一律用**同长度物化除数**（polars 的 ``col/scalar`` 差 1 ulp，实测 12.29% 的行）。
* ``_rpc_*`` 复用 ``columnar._parse_rpc_resp`` 的语义（按唯一值映射，避免逐行 Python）。
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Sequence

import polars as pl

from latency.ENUM.ds_log import StatusCode
from latency.parse import (
    ClientInfoParser,
    SdkAccessLogParser,
    WorkerAccessLogParser,
)
from latency.parse.keywords import (
    SDK_ACCESS_KEYWORDS,
    SDK_GET_OPS,
    SDK_SET_OPS,
    TRACE_FIELD_RE,
    UUID_RE,
    WORKER_ACCESS_KEYWORDS,
    WORKER_GET_OPS,
    WORKER_SET_OPS,
    AccessCol,
)
from latency.parse.parallel_scanner.columnar import (
    ALL_COLUMNS,
    CLIENT_RPC_LABEL,
    LABEL_TO_COLUMNS,
    SDK_LABEL,
    TRACE_COLUMNS,
    WORKER_ACCESS_LABEL,
    _SRC_RANK,
    _parse_rpc_resp,
)
from latency.parse.columns import LIGHT_COLUMNS
from latency.parse.keywords import MASTER_RPC_RE

if TYPE_CHECKING:  # 仅注解使用，运行时不导入
    from latency.parse.base_parser import LogParser

__all__ = ["access_label_columns"]

_FILE_COLUMN = "__file"
_ROW_COLUMN = "__row"
_RANK_COLUMN = "__rank"

_INTERNAL_COLUMNS: tuple[str, ...] = (
    "_elapsed_us",
    "_resp_msg",
    "_rpc_e2e_us",
    "_rpc_server_exec_us",
    "_rpc_network_us",
)
_OUTPUT_COLUMNS: tuple[str, ...] = (*ALL_COLUMNS, *_INTERNAL_COLUMNS, _FILE_COLUMN, _ROW_COLUMN)

#: light 模式的列集与输出列序（第一遍只算这些，宽列留给第二遍）。
#: ``_LIGHT_OUTPUT_COLUMNS`` 取 ``_OUTPUT_COLUMNS`` 的**子序列**，保持既有相对列序。
_LIGHT_SET = frozenset(LIGHT_COLUMNS)
_LIGHT_OUTPUT_COLUMNS: tuple[str, ...] = tuple(
    name for name in _OUTPUT_COLUMNS if name in _LIGHT_SET
)

_ACCESS_PIPES = 12          # 13 段的 '|' 数
_RUN_PIPES = 7              # 8 段的 '|' 数
_STRICT_TS_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$"
_TRACE_STRIP = "[]{}()\"'"
_ZMQ_KEYWORD = "[ZMQ_RPC_FRAMEWORK_SLOW]"
_DIGITS_RE = r"^\d+$"

# op 白名单 = 各解析器的 get/set 集合（StrEnum 成员，取字符串）
_SDK_OPS = sorted({str(op) for op in (SDK_GET_OPS | SDK_SET_OPS)})
_WORKER_OPS = sorted({str(op) for op in (WORKER_GET_OPS | WORKER_SET_OPS)})

# 关键字正则 = 各解析器 ``_keywords`` 的交替（与扫描器的行闸门同一份来源）
# P1：关键字取自 ``parse/keywords.py``，不再绕道解析器类属性。
_SDK_KW_RE = "|".join(SDK_ACCESS_KEYWORDS)
_WORKER_KW_RE = "|".join(WORKER_ACCESS_KEYWORDS)

# trace_id 提取正则（与 base_parser.LogParser 同源）。
# 注意：polars 的 str.extract 需要**捕获组**；base_parser 的两个 pattern 里
# 只有 trace 字段那个自带 (?P<trace>)，UUID 那个没有 —— 必须自己包一层，
# 否则 str.extract 恒返回 null（实测），UUID 回退静默失效、整行被丢。
V_UUID_RE = "(" + UUID_RE.pattern + ")"
V_TRACE_FIELD_RE = TRACE_FIELD_RE.pattern

_LATENCY_COLUMNS: dict[str, tuple[str, ...]] = {
    SDK_LABEL: ("total_ms", "total_latency"),
    WORKER_ACCESS_LABEL: ("worker_total_latency",),
    CLIENT_RPC_LABEL: (),
}
_MASTER_RPC_FIELDS: tuple[str, ...] = tuple(
    name for name in MASTER_RPC_RE.groupindex
)
_TIMED_RESP_EXCLUDED_FIELDS = frozenset({"cost", "src", "dst"})


#: 恢复 chunk 结构的片数（= 字符串算子的并行粒度上限）


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------

def _lit_null(dtype: type[pl.DataType]) -> pl.Expr:
    return pl.lit(None, dtype=dtype)


def _ms_from_us(elapsed_us: pl.Series) -> pl.Series:
    """``elapsed_us / 1000.0``：同长度物化除数（避免 ``col/scalar`` 的 1 ulp 偏差）。"""
    height = len(elapsed_us)
    if height == 0:
        return elapsed_us
    return elapsed_us / pl.select(pl.repeat(1000.0, height)).to_series()


def _clean(expr: pl.Expr) -> pl.Expr:
    stripped = expr.str.strip_chars()
    return (
        pl.when(stripped.is_not_null() & (stripped != ""))
        .then(stripped)
        .otherwise(_lit_null(pl.Utf8))
    )


def _op_key(op: pl.Expr) -> pl.Expr:
    return (
        pl.when(op.str.contains("GET", literal=True))
        .then(pl.lit("GET", dtype=pl.Utf8))
        .when(op.str.contains("SET", literal=True) | op.str.contains("CREATE", literal=True)
              | op.str.contains("PUBLISH", literal=True))
        .then(pl.lit("SET", dtype=pl.Utf8))
        .otherwise(_lit_null(pl.Utf8))
    )


def _explicit_trace_id(expr: pl.Expr) -> pl.Expr:
    return (
        expr.str.extract(V_TRACE_FIELD_RE)
        .str.strip_chars()
        .str.strip_chars(_TRACE_STRIP)
    )


def _trace_id_expr(head: str, sources: Sequence[str]) -> pl.Expr:
    """``resolve_trace_id`` 的列运算版：显式字段（按 sources 顺序）→ 格式列 → 首个 UUID。"""
    import polars as pl  # 用途待确认（模块顶层已导入 polars，此处为重复导入）

    explicit = pl.coalesce([_explicit_trace_id(pl.col(src)) for src in sources])
    head_col = pl.col(head)
    head_ok = head_col.is_not_null() & (head_col != "")
    # Polars evaluates both when branches. Null the regex input first so
    # records already carrying a trace column never scan for a UUID fallback.
    uuid = pl.coalesce([
        pl.when(head_ok).then(None).otherwise(pl.col(src)).str.extract(V_UUID_RE, 1)
        for src in sources
    ])
    explicit_ok = explicit.is_not_null() & (explicit != "")
    uuid_ok = uuid.is_not_null() & (uuid != "")
    return (
        pl.when(explicit_ok).then(explicit)
        .when(head_ok).then(head_col)
        .when(uuid_ok).then(uuid)
        .otherwise(pl.lit("", dtype=pl.Utf8))
    )


def _format_timed_resp_msg(groups: pl.Expr) -> pl.Expr:
    """``_format_timed_resp_msg``：按**正则组顺序**拼 ``k=v``，排除 cost/src/dst。"""
    parts = []
    for name in _MASTER_RPC_FIELDS:
        if name in _TIMED_RESP_EXCLUDED_FIELDS:
            continue
        value = _clean(groups.struct.field(name))
        parts.append(
            pl.when(value.is_not_null())
            .then(pl.lit(f"{name}=", dtype=pl.Utf8) + value)
            .otherwise(_lit_null(pl.Utf8))
        )
    if not parts:
        return _lit_null(pl.Utf8)
    joined = parts[0]
    for expr in parts[1:]:
        joined = pl.concat_str([joined, expr], separator=", ", ignore_nulls=True)
    return pl.when(joined.is_not_null() & (joined != "")).then(joined).otherwise(_lit_null(pl.Utf8))


def _pod_ip_expr(pod_name: pl.Expr) -> pl.Expr:
    value = pl.when(pod_name.is_not_null() & (pod_name != "")).then(pod_name).otherwise(
        pl.col("_file_pod_ip")
    )
    return pl.when(value != "").then(value).otherwise(_lit_null(pl.Utf8))


def _cluster_expr(cluster: pl.Expr) -> pl.Expr:
    return pl.when(cluster.is_not_null() & (cluster != "")).then(cluster).otherwise(
        _lit_null(pl.Utf8)
    )


def _log_id_expr() -> pl.Expr:
    """log_id 已由 _prepare_candidates 的 join 挂成 ``_log_id`` 列（避开 replace_strict）。"""
    return pl.col("_log_id")


def _parts_alias(line: pl.Expr, count: int) -> pl.Expr:
    """``splitn`` 只算一次：先物化成 ``_parts`` 列，字段再从它取。

    直接把 ``line.str.splitn(...).struct.field(i)`` 写进 10 个字段表达式，等于让
    polars 对每行切 10 遍（实测 phase1 从 0.44s/337k 行降到 ~0.08s）。
    """
    return line.str.splitn("|", count).alias("_parts")


def _splitn_fields(count: int) -> list[pl.Expr]:
    """从 ``_parts`` 列取 ``count`` 个字段（最后一个 = "剩余整段"）。"""
    parts = pl.col("_parts")
    return [parts.struct.field(f"field_{index}") for index in range(count)]


def _access_base_fields(parts: list[pl.Expr]) -> dict[str, pl.Expr]:
    col = AccessCol
    return {
        "_ts_raw": parts[col.TIMESTAMP].str.strip_chars(),
        "_pod_name": parts[col.POD_NAME].str.strip_chars(),
        "_trace_col": parts[col.TRACE_ID].str.strip_chars(),
        "_cluster": parts[col.CLUSTER_NAME].str.strip_chars(),
        "_status_raw": parts[col.STATUS_CODE].str.strip_chars(),
        "_handle": parts[col.HANDLE].str.strip_chars(),
        "_elapsed_raw": parts[col.ELAPSED].str.strip_chars(),
        "_size": parts[col.SIZE].str.strip_chars(),
        "_req_msg": parts[col.REQ_MSG].str.strip_chars(),
        "_resp_msg_raw": parts[col.RESP_MSG].str.strip_chars(),
    }


def _empty_frame(light: bool = False) -> pl.DataFrame:
    columns = _LIGHT_OUTPUT_COLUMNS if light else _OUTPUT_COLUMNS
    return pl.DataFrame(
        {name: pl.Series(name, [], dtype=_dtype_of(name)) for name in columns}
    ).with_columns(pl.Series(_RANK_COLUMN, [], dtype=pl.Int64))


def _dtype_of(name: str) -> type[pl.DataType]:
    if name in ("__row",):
        return pl.Int64
    if name in ("bucket_epoch", "status_code"):
        return pl.Int64
    if name in ("_elapsed_us", "_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us",
                "total_ms", "total_latency", "worker_total_latency"):
        return pl.Float64
    if name == "_src_rank":
        return pl.Int64
    return pl.Utf8


# ---------------------------------------------------------------------------
# 时间戳 / 状态码：表达式快路径 + 探针触发的 Python 兜底
# ---------------------------------------------------------------------------

def _ts_fast_exprs(src: str) -> tuple[pl.Expr, pl.Expr, pl.Expr, pl.Expr]:
    """严格 ISO 形状的快路径 → ``(ok, timestamp_str, bucket_epoch)``。"""
    norm = pl.col(src).str.replace(" ", "T", literal=True, n=1)
    dt = norm.str.to_datetime(format="%Y-%m-%dT%H:%M:%S%.f", strict=False)
    ok = (norm.str.contains(_STRICT_TS_RE) & dt.is_not_null()).fill_null(False)
    ts_sec = dt.dt.truncate("1s")
    ts_str = (
        pl.when(dt.is_null() | (dt != ts_sec))
        .then(dt.dt.to_string("%Y-%m-%d %H:%M:%S.%6f"))
        .otherwise(dt.dt.to_string("%Y-%m-%d %H:%M:%S"))
    )
    epoch_s = dt.dt.epoch("s").cast(pl.Int64)
    bucket = ((epoch_s // 10) * 10).cast(pl.Int64)
    return ok, ts_str, bucket, epoch_s


def _ts_exprs(src: str) -> tuple[pl.Expr, pl.Expr, pl.Expr, pl.Expr]:
    """时间戳列 → (ok, 串, 桶, epoch秒)：只保留严格 ISO 快路径。

    删除的两段：
    * 探针 `lf.select((~ok).sum()).collect()`：先把整列时间戳在**默认引擎**上解析一遍，
      只为数"有多少行不合法"。默认引擎不给字符串/日期 kernel 做纵向并行（见 _collect
      注释），实测 3.97M 行要 1.045s，平均活跃线程只有 1.35。
    * Python 兜底：对探针捞出的坏值用 `parse_timestamp` 重算，再 4 次 replace_strict 回填；
      真实语料两个数据集均 0 次命中（改动前后 40 列 sha1 完全一致）。

    删掉后这四个表达式随调用方的 _collect() 一起进入 streaming，拿回纵向并行。
    """
    return _ts_fast_exprs(src)


def _status_exprs(src: str) -> tuple[pl.Expr, pl.Expr]:
    """(status_value, invalid_mask) —— 与原逐行实现等价，且不再跑查询。

    原实现先 lf.filter(...).select(col.unique()).collect() 把状态码的全部唯一值捞出来，
    再据此建映射表。实测（jingpai 样本：85,951 行非数字状态 / 55,886 个唯一值）那张表算出的
    值恒等于 int(StatusCode.OK)，与这里 otherwise(lit(OK)) 完全相同 —— 纯冗余，而探针还要
    把整列读一遍。

    invalid 复刻"isdigit() 为真但 int() 失败"（上标/圈号数字）→ 原逐行实现抛异常 → 丢行。
    改成表达式判定，不跑查询；真实语料两个数据集均为 0 例。
    """
    fast = (
        pl.when(pl.col(src).is_not_null() & pl.col(src).str.contains(_DIGITS_RE))
        .then(pl.col(src).cast(pl.Int64, strict=False))
        .otherwise(pl.lit(int(StatusCode.OK), dtype=pl.Int64))
    )
    invalid = (
        pl.col(src).is_not_null()
        & pl.col(src).str.contains(_DIGITS_RE)
        & pl.col(src).cast(pl.Int64, strict=False).is_null()
    )
    return fast, invalid




def _collect(lf: pl.LazyFrame) -> pl.DataFrame:
    """优先用 streaming 引擎执行：polars 的字符串/日期 kernel 本身单线程，但 streaming
    引擎会做**纵向并行**（按 chunk 切给 rayon），实测单 chunk 下 `extract_groups`
    1.01 核 → 13.42 核、`to_datetime` 0.92 → 12.40 核、`dt.to_string` 0.93 → 16.05 核。
    官方 issue #17235：kernel "process the strings in a single thread"，并行由执行器提供。
    不支持时退回默认引擎（行为不变，只降并行度）。
    """
    try:
        return lf.collect(engine="streaming")
    except Exception:  # noqa: BLE001
        return lf.collect()




# ---------------------------------------------------------------------------
# per-file 元数据
# ---------------------------------------------------------------------------

class _FileMeta:
    __slots__ = ("pod_ip", "rank", "sdk_paths", "worker_paths", "client_paths")

    def __init__(self: "_FileMeta") -> None:
        self.pod_ip: dict[str, str] = {}
        self.rank: dict[str, int] = {}
        self.sdk_paths: list[str] = []
        self.worker_paths: list[str] = []
        self.client_paths: list[str] = []


def _normalize_inputs(files: Sequence, parsers: Sequence) -> tuple[list[str], list[list[LogParser]]]:
    paths: list[str] = []
    for item in files:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, (tuple, list)) and item:
            paths.append(str(item[0]))
        else:
            raise TypeError(f"access_label_columns: 无法识别的 files 元素 {type(item)!r}")
    if isinstance(parsers, (list, tuple)) and parsers and isinstance(parsers[0], (list, tuple)):
        per_file = [list(group) for group in parsers]
    else:
        per_file = [list(parsers or ())] * len(paths)
    if len(per_file) != len(paths):
        raise ValueError(
            f"access_label_columns: files({len(paths)}) 与 parsers({len(per_file)}) 长度不一致"
        )
    return paths, per_file


def _guard_parser(parser: LogParser | None) -> None:
    if getattr(parser, "_start_dt", None) is not None or getattr(parser, "_end_dt", None) is not None:
        raise NotImplementedError("access_label_columns: 时间窗过滤请回退逐行路径")
    if getattr(parser, "min_elapsed_us", None) is not None:
        raise NotImplementedError("access_label_columns: min_elapsed_ms 请回退逐行路径")


def _file_meta(paths: list[str], per_file: list[list[LogParser]],
               file_rank: dict[str, int]) -> _FileMeta:
    meta = _FileMeta()
    for index, path in enumerate(paths):
        group = per_file[index]
        for parser in group:
            _guard_parser(parser)
        first = group[0] if group else None
        try:
            meta.pod_ip[path] = first.extract_pod_ip(path) if first else ""
        except Exception:  # noqa: BLE001
            meta.pod_ip[path] = ""
        rank = file_rank.get(path)
        meta.rank[path] = int(rank) if rank is not None else index
        if any(isinstance(p, SdkAccessLogParser) for p in group):
            meta.sdk_paths.append(path)
        if any(isinstance(p, WorkerAccessLogParser) for p in group):
            meta.worker_paths.append(path)
        if any(isinstance(p, ClientInfoParser) for p in group):
            meta.client_paths.append(path)
    return meta


def _prepare_candidates(
    frame: pl.DataFrame,
    paths: list[str],
    per_file: list[list[LogParser]],
    file_rank: dict[str, int],
    log_ids: dict[str, str] | None = None,
) -> tuple[pl.LazyFrame, _FileMeta]:
    """候选帧 → **惰性**基帧（带 __file / __row / __rank / _file_pod_ip / _log_id）。

    原实现在这里就把帧物化：pl.DataFrame({...}) 复制一份 line 列、str.replace 归一化路径、
    再 join 一张"每文件一行"的小表 —— 三件都在默认引擎上跑，实测 3.97M 行 0.459s、
    平均活跃线程 2.73。现在整体保持惰性，这些算子随调用方第一次 _collect()（streaming）
    一起并行执行；chunk 结构由执行器决定，原来手工 _rechunk_k 那一步也不再需要。
    """
    categorical_paths = (
        _FILE_COLUMN in frame.columns
        and frame.schema[_FILE_COLUMN] == pl.Categorical
        and not any("\\" in path for path in frame[_FILE_COLUMN].unique() if path is not None)
    )
    if _FILE_COLUMN in frame.columns:
        # polars 的 include_file_paths 在 Windows 上给正斜杠，而调用方传的是
        # os.path.join 风格的反斜杠 → is_in/join 全部命中不到，表现为"access 三个 label 全空"。
        # 统一归一成 posix 形式后比较。
        base = frame.lazy().select(
            pl.col("line").cast(pl.Utf8),
            (pl.col(_FILE_COLUMN) if categorical_paths else
             pl.col(_FILE_COLUMN).cast(pl.Utf8).str.replace("\\", "/", literal=True)),
            *([pl.col(_ROW_COLUMN).cast(pl.Int64)] if _ROW_COLUMN in frame.columns else []),
        )
    elif len(paths) == 1:
        base = frame.lazy().select(
            pl.col("line").cast(pl.Utf8),
            pl.lit(paths[0], dtype=pl.Utf8).alias(_FILE_COLUMN),
            *([pl.col(_ROW_COLUMN).cast(pl.Int64)] if _ROW_COLUMN in frame.columns else []),
        )
    else:
        raise ValueError("access_label_columns: frame 缺少 '__file' 且 files 不唯一")

    if _ROW_COLUMN in frame.columns:
        base = base.with_columns(pl.col(_ROW_COLUMN).cast(pl.Int64))
    else:
        # int_range 是 elementwise；cum_count().over() 是窗口函数 → 会让执行器把纵向
        # 并行整块关掉（polars lp.rs:538）。输入帧本来就是"文件序 + 文件内行序"，
        # 全局行号足以充当排序键，语义不变。
        base = base.with_columns(pl.int_range(pl.len(), dtype=pl.Int64).alias(_ROW_COLUMN))

    posix_paths = [p.replace("\\", "/") for p in paths]
    meta = _file_meta(posix_paths, per_file,
                      {p.replace("\\", "/"): r for p, r in file_rank.items()})
    fallback_pod_ip = meta.pod_ip.get(paths[0], "") if paths else ""
    for path in posix_paths:
        if path in meta.pod_ip:
            continue
        parser = per_file[0][0] if per_file and per_file[0] else None
        try:
            meta.pod_ip[path] = parser.extract_pod_ip(path) if parser else fallback_pod_ip
        except Exception:  # noqa: BLE001
            meta.pod_ip[path] = fallback_pod_ip
        meta.rank[path] = len(meta.rank)

    # join 一张"每文件一行"的小表（表大小 = 文件数，不是行数）：replace_strict 是非
    # elementwise，会把纵向并行关掉；join 是并行的。
    meta_frame = pl.DataFrame(
        {
            _FILE_COLUMN: list(meta.pod_ip),
            _RANK_COLUMN: [meta.rank.get(path) for path in meta.pod_ip],
            "_file_pod_ip": [meta.pod_ip[path] for path in meta.pod_ip],
            "_log_id": [(log_ids or {}).get(path) or (log_ids or {}).get(path.replace("/", "\\"))
                        for path in meta.pod_ip],
        }
    ).with_columns(
        pl.col(_RANK_COLUMN).cast(pl.Int64),
        pl.col("_file_pod_ip").cast(pl.Utf8),
        pl.col("_log_id").cast(pl.Utf8),
    )
    if categorical_paths:
        # Scanner source paths are already dictionary encoded. Join their
        # integer keys before expanding the public string output column.
        meta_frame = meta_frame.with_columns(pl.col(_FILE_COLUMN).cast(pl.Categorical))
    base = base.join(meta_frame.lazy(), on=_FILE_COLUMN, how="left")
    if categorical_paths:
        base = base.with_columns(pl.col(_FILE_COLUMN).cast(pl.String))
    return base, meta



# ---------------------------------------------------------------------------
# 投影（链内完成，毫秒列在 collect 之后用物化除数补）
# ---------------------------------------------------------------------------

def _light_columns(label: str) -> frozenset[str]:
    """light 模式下该 label 要投影的列 = ``parse/columns.LIGHT_COLUMNS`` ∩ 该 label 契约列。

    ``tid`` 恒在：``_project_exprs`` 对任何 label 都输出 tid（那里的漂移断言把 tid 排除在
    "该 label 产出的列"之外），light 必须保持同一套行列语义。
    """
    return (frozenset(LIGHT_COLUMNS) & set(LABEL_TO_COLUMNS.get(label, ()))) | {"tid"}


def _project_exprs(label: str, values: dict[str, pl.Expr], *,
                   light: bool = False) -> list[pl.Expr]:
    expected = set(LABEL_TO_COLUMNS.get(label, ()))
    latency = set(_LATENCY_COLUMNS.get(label, ()))
    actual = (set(values) - {"tid", "_elapsed_us", "_resp_msg"}) | latency
    if expected != actual:
        raise AssertionError(
            f"access_label_columns: {label} 投影列集与 columnar.LABEL_TO_COLUMNS 漂移："
            f"多 {sorted(actual - expected)} 少 {sorted(expected - actual)}"
        )
    select: list[pl.Expr] = [
        pl.col(_FILE_COLUMN),
        pl.col(_ROW_COLUMN),
        pl.col(_RANK_COLUMN),
    ]
    if light:
        # light：只投影轻列（+ tid），别的列**一个表达式都不 select** —— polars 会把
        # 它们整条剪掉，而不是铺 null（铺 null 正是要省的开销）。行集由门禁与 valid
        # 决定，与本处 select 无关，故与 light=False 逐行一致。
        lights = _light_columns(label)
        missing = lights - actual - {"tid"}
        if missing:  # 理论上恒空（上面刚断言 actual == expected）
            raise AssertionError(
                f"access_label_columns: {label} 的 light 列集越出该 label 的产出："
                f"{sorted(missing)}"
            )
        for name in TRACE_COLUMNS:
            if name not in lights:
                continue
            if name in latency:
                select.append(_lit_null(pl.Float64).alias(name))   # 稍后用物化除数补
            elif name in values:
                select.append(values[name].alias(name))
        select.append(pl.lit(_SRC_RANK.get(label, 0), dtype=pl.Int64).alias("_src_rank"))
        # _elapsed_us 只为算毫秒列而进计划（_finish 里算完即丢）；
        # _label / _resp_msg / _rpc_* 是宽列，light 一律不算。
        select.append(values["_elapsed_us"].alias("_elapsed_us"))
        return select
    for name in TRACE_COLUMNS:
        if name in latency:
            select.append(_lit_null(pl.Float64).alias(name))   # 稍后用物化除数补
        elif name in values:
            select.append(values[name].alias(name))
        # 该 label 没有的列**不在这里生成 null**：一个 label 通常只填 3~6 列，
        # 直接铺 40 列等于每行白算 ~30 个 null（实测占 final collect 的 2/3）。
        # 缺列统一交给 scan_vector._normalize 一次性补（带类型）。
    select.append(pl.lit(label, dtype=pl.Utf8).alias("_label"))
    select.append(pl.lit(_SRC_RANK.get(label, 0), dtype=pl.Int64).alias("_src_rank"))
    select.append(values["_elapsed_us"].alias("_elapsed_us"))
    select.append(values["_resp_msg"].alias("_resp_msg"))
    return select


def _rpc_expr(src: str, key: str, alias: str) -> pl.Expr:
    """``columnar._parse_rpc_resp`` 的纯列运算版：**单次 ``str.extract``**（elementwise）。

    ``extract_all`` + ``list.last`` 是 list 算子（非 elementwise），会被执行器一票否决；
    重复键语义由"后者覆盖"变为"取第一个" —— 真实数据无重复键，由 40 列 sha1 闸门兜住。
    """
    import polars as pl  # 用途待确认（模块顶层已导入 polars，此处为重复导入）

    pattern = r"\b" + key + r"\s*=\s*(-?\d+)\s*(?:,|$)"
    return pl.col(src).str.extract(pattern, 1).cast(pl.Float64, strict=False).alias(alias)


def _finish(out: pl.DataFrame, label: str, *, light: bool = False) -> pl.DataFrame:
    """collect 之后：补毫秒列（物化除数）+ ``_rpc_*``（唯一值映射，不逐行）。

    ``light``：毫秒列仍用**同一套** ``_ms_from_us``（同长度物化除数）补，宽列
    （``_label`` / ``_resp_msg`` / ``_rpc_*``）一个不算，``_elapsed_us`` 用过即丢。
    """
    if out.height == 0:
        return out
    latency = tuple(
        name for name in _LATENCY_COLUMNS.get(label, ())
        if not light or name in _LIGHT_SET
    )
    if latency:
        ms = _ms_from_us(out["_elapsed_us"])
        out = out.with_columns([ms.alias(name) for name in latency])
    if not light:
        # 原本这里是 to_list() + Python 字典循环（逐行 Python）；改成三条列表达式。
        out = out.with_columns(
            _rpc_expr("_resp_msg", key, column)
            for key, column in (
                ("e2e_us", "_rpc_e2e_us"),
                ("server_exec_us", "_rpc_server_exec_us"),
                ("network_residual_us", "_rpc_network_us"),
            ) if column not in out.columns
        )
    # 只保留真实存在的列；缺列由 scan_vector._normalize 补齐（避免每行铺 null）
    wanted = [
        *(_LIGHT_OUTPUT_COLUMNS if light else _OUTPUT_COLUMNS),
        _FILE_COLUMN, _ROW_COLUMN, _RANK_COLUMN,
    ]
    keep: list[str] = []
    for name in wanted:                      # 顺序敏感 + 去重（_OUTPUT_COLUMNS 已含 __file/__row）
        if name in out.columns and name not in keep:
            keep.append(name)
    return out.select(keep)


# ---------------------------------------------------------------------------
# 三个 label：各一条链 + 一次 collect
# ---------------------------------------------------------------------------

def _access_rows(base: pl.LazyFrame, meta: _FileMeta, log_ids: dict[str, str] | None, *,
                 ops: list[str], kw_re: str, paths: list[str], label: str, latency_op: str,
                 window: tuple[int, int] | None = None,
                 min_elapsed_us: float | None = None,
                 light: bool = False) -> pl.DataFrame | None:
    if not paths:
        return None
    lf = base.filter(pl.col(_FILE_COLUMN).is_in(paths))
    line = pl.col("line")
    lf = lf.with_columns(_parts_alias(line, 14))
    parts = _splitn_fields(14)
    fields = _access_base_fields(parts)
    gate = (
        line.str.starts_with("2")
        & parts[_ACCESS_PIPES].is_not_null()
        & line.str.contains(kw_re)
        & fields["_handle"].is_in(ops)
    )
    # Keep projection in the same lazy plan: light mode never needs to allocate
    # wide-only intermediate strings such as pod, cluster, or response fields.
    lf = (
        lf.with_columns(**fields)
        .filter(gate.fill_null(False))
        .select([_FILE_COLUMN, _ROW_COLUMN, _RANK_COLUMN, "_file_pod_ip", "_log_id", *fields.keys()])
    )

    ok_ts, ts_str, ts_bucket, ts_epoch = _ts_exprs("_ts_raw")
    status_expr, status_invalid = _status_exprs("_status_raw")
    elapsed_expr = pl.col("_elapsed_raw").cast(pl.Int64, strict=False)
    lf = lf.with_columns(
        _trace_id_expr("_trace_col", ["_req_msg", "_resp_msg_raw"]).alias("_trace_id")
    )
    trace_id = pl.col("_trace_id")

    valid = elapsed_expr.is_not_null() & ok_ts & (trace_id != "")
    if min_elapsed_us is not None:
        valid = valid & (elapsed_expr >= int(min_elapsed_us))
    if window is not None:
        start_s, end_s = window
        valid = valid & (ts_epoch >= start_s) & (ts_epoch <= end_s) & ~status_invalid
    if min_elapsed_us is not None:
        valid = valid & (elapsed_expr >= int(min_elapsed_us))
    if window is not None:
        start_s, end_s = window
        valid = valid & (ts_epoch >= start_s) & (ts_epoch <= end_s)
    op = pl.col("_handle").str.to_uppercase()
    values: dict[str, pl.Expr] = {
        "tid": trace_id,
        "op": op,
        "operation": pl.when(op != "").then(op).otherwise(_lit_null(pl.Utf8)),
        "op_key": _op_key(op),
        "bucket_epoch": ts_bucket,
        "timestamp": ts_str,
        "log_id": _log_id_expr(),
        "status_code": status_expr,
        "pod_ip": _pod_ip_expr(pl.col("_pod_name")),
        "cluster_name": _cluster_expr(pl.col("_cluster")),
        "_elapsed_us": elapsed_expr.cast(pl.Float64),
        "_resp_msg": pl.col("_resp_msg_raw"),
    }
    if latency_op == "sdk":
        size = pl.col("_size")
        values["data_size"] = (
            pl.when(size.is_not_null() & (size != "")).then(size).otherwise(_lit_null(pl.Utf8))
        )
        values["inflight_count"] = _lit_null(pl.Float64)

    plan = lf.filter(valid.fill_null(False)).select(
        _project_exprs(label, values, light=light)
    )
    return _finish(_collect(plan), label, light=light)


def _client_rpc_rows(base: pl.LazyFrame, meta: _FileMeta, log_ids: dict[str, str] | None, *,
                     window: tuple[int, int] | None = None,
                     min_elapsed_us: float | None = None,
                     light: bool = False, defer_unused: bool = False,
                     sparse: bool = False) -> pl.DataFrame | None:
    paths = meta.client_paths
    if not paths:
        return None
    lf = base.filter(pl.col(_FILE_COLUMN).is_in(paths))
    line = pl.col("line")
    lf = lf.with_columns(_parts_alias(line, 8))
    parts = _splitn_fields(8)
    ts_raw = parts[0].str.strip_chars()
    pod_name = parts[3].str.strip_chars()
    trace_col = parts[5].str.strip_chars()
    cluster = parts[6].str.strip_chars()
    msg = parts[7].str.strip_chars()
    lf = lf.with_columns(
        ts_raw.alias("_ts_raw"), pod_name.alias("_pod_name"), trace_col.alias("_trace_col"),
        cluster.alias("_cluster"), msg.alias("_msg"),
    )
    gate = (
        line.str.starts_with("2")
        & parts[_RUN_PIPES].is_not_null()
        & line.str.contains(_ZMQ_KEYWORD, literal=True)
    )
    if light and defer_unused:
        # RPC records have no light metrics. Keep their source locator; the
        # selected wide pass still performs full timing/format validation.
        # scan_frame removes these rank-zero rows before light aggregation.
        return _collect(lf.filter(gate.fill_null(False)).select(
            _trace_id_expr("_trace_col", ["line"]).alias("tid"),
            pl.lit(0, dtype=pl.Int64).alias("_src_rank"),
            pl.col(_FILE_COLUMN), pl.col(_ROW_COLUMN), pl.col(_RANK_COLUMN),
        ))
    lf = lf.filter(gate.fill_null(False)).with_columns(
        pl.col("_msg").str.extract_groups(MASTER_RPC_RE.pattern).alias("_groups")
    )
    lf = (
        lf.filter(pl.col("_groups").struct.field("remote_processing_us").is_not_null())
        .select([_FILE_COLUMN, _ROW_COLUMN, _RANK_COLUMN, "_file_pod_ip", "_log_id", "_ts_raw",
                 "_pod_name", "_trace_col", "_cluster", "_msg", "_groups", "line"])
    )
    ok_ts, ts_str, ts_bucket, ts_epoch = _ts_exprs("_ts_raw")
    elapsed_expr = (
        pl.col("_groups").struct.field("remote_processing_us")
        .cast(pl.Int64, strict=False)
    )
    lf = lf.with_columns(
        _trace_id_expr("_trace_col", ["line"]).alias("_trace_id")
    )
    trace_id = pl.col("_trace_id")
    valid = elapsed_expr.is_not_null() & ok_ts & (trace_id != "")

    values: dict[str, pl.Expr] = {
        "tid": trace_id,
        "_elapsed_us": elapsed_expr.cast(pl.Float64),
        "_resp_msg": _format_timed_resp_msg(pl.col("_groups")),
    }
    exprs = _project_exprs(CLIENT_RPC_LABEL, values, light=light)
    if not light:
        if sparse:
            exprs = [expr for expr in exprs if expr.meta.output_name() != "_resp_msg"]
        # RPC response text is itself built from these captures. Keep the
        # numeric values directly instead of formatting then extracting them.
        exprs.extend(
            pl.coalesce(
                # Preserve first-match behavior if unusual trace text itself
                # contains a comma-separated RPC key before the real field.
                pl.col("_groups").struct.field("rpc_trace_id")
                .str.extract(r"\b" + key + r"\s*=\s*(-?\d+)\s*(?:,|$)", 1),
                pl.col("_groups").struct.field(key),
            ).cast(pl.Float64, strict=False).alias(column)
            for key, column in (
                ("e2e_us", "_rpc_e2e_us"),
                ("server_exec_us", "_rpc_server_exec_us"),
                ("network_residual_us", "_rpc_network_us"),
            )
        )
    plan = lf.filter(valid.fill_null(False)).select(exprs)
    return _finish(_collect(plan), CLIENT_RPC_LABEL, light=light)


def access_label_columns(
    frame: pl.DataFrame,
    files: Sequence,
    parsers: Sequence,
    *,
    file_rank: dict[str, int],
    log_ids: dict[str, str] | None = None,
    window: tuple[int, int] | None = None,
    min_elapsed_us: float | None = None,
    light: bool = False,
    defer_unused: bool = False,
    sparse: bool = False,
) -> pl.DataFrame:
    """access 三类记录（SDK / Worker access / Client rpc）的列式解析。

    ``light=True``：只算 ``parse/columns.LIGHT_COLUMNS`` 中该 label 产出的列（外加
    行序键 ``__file``/``__row``/``__rank`` 与 ``_src_rank``），宽列（``_label`` /
    ``_elapsed_us`` / ``_resp_msg`` / ``_rpc_*`` 等）**一个表达式都不 select**；
    行集与 ``light=False`` 逐行一致（门禁、有效性判定、过滤条件一字未改）。
    ``defer_unused=True`` lets the worker keep only source locators for light
    RPC candidates, postponing full validation until selected wide projection.
    These metric-free candidates must be excluded from light aggregation.
    """
    paths, per_file = _normalize_inputs(files, parsers)
    base, meta = _prepare_candidates(frame, paths, per_file, file_rank, log_ids)
    # base 现在是惰性帧（行数要执行才知道）：空输入由下面"没有 builder 产出"的分支兜底。

    frames: list[pl.DataFrame] = []
    for builder in (_sdk_rows, _worker_access_rows, _client_rpc_rows):
        part = builder(base, meta, log_ids, window=window,
                       min_elapsed_us=min_elapsed_us, light=light,
                       **({"defer_unused": defer_unused, "sparse": sparse}
                          if builder is _client_rpc_rows else {}))
        if part is not None and part.height:
            frames.append(part)
    if not frames:
        return _empty_frame(light)
    # 行序/定位键在 light 下也必须保留：__rank 在 _OUTPUT_COLUMNS 之外的这两列
    # （__file/__row）只能显式补进来，否则第二遍没法按 (__file, __row) 回定位。
    wanted = [
        *(_LIGHT_OUTPUT_COLUMNS if light else _OUTPUT_COLUMNS),
        _FILE_COLUMN, _ROW_COLUMN, _RANK_COLUMN,
    ]
    keep: list[str] = []
    for frame in frames:
        for name in wanted:
            if name in frame.columns and name not in keep:
                keep.append(name)
    # SDK 与 Worker access 的列集不同（data_size/inflight_count 只有 SDK 有）
    out = pl.concat(frames, how="diagonal_relaxed")
    out = out.sort([_RANK_COLUMN, _ROW_COLUMN])
    return out.select(keep)


def _sdk_rows(base: pl.LazyFrame, meta: _FileMeta, log_ids: dict[str, str] | None, *,
              window: tuple[int, int] | None = None,
              min_elapsed_us: float | None = None,
              light: bool = False) -> pl.DataFrame | None:
    return _access_rows(base, meta, log_ids, ops=_SDK_OPS, kw_re=_SDK_KW_RE,
                        paths=meta.sdk_paths, label=SDK_LABEL, latency_op="sdk",
                        window=window, min_elapsed_us=min_elapsed_us, light=light)


def _worker_access_rows(base: pl.LazyFrame, meta: _FileMeta, log_ids: dict[str, str] | None, *,
                        window: tuple[int, int] | None = None,
                        min_elapsed_us: float | None = None,
                        light: bool = False) -> pl.DataFrame | None:
    return _access_rows(base, meta, log_ids, ops=_WORKER_OPS, kw_re=_WORKER_KW_RE,
                        paths=meta.worker_paths, label=WORKER_ACCESS_LABEL, latency_op="worker",
                        window=window, min_elapsed_us=min_elapsed_us, light=light)
