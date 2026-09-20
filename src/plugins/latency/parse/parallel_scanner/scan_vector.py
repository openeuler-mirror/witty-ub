"""扫描侧「两步法」：一次读 + 一条列表达式链，替代逐文件读 + 逐行 Python 解析。

```
① SCAN   pl.scan_lines(全部文件, include_file_paths="__file")  →  行闸门
② PARSE  切列 → 字段 → 门禁 → 派生 → 40 列投影 → 一次 collect
```

分派规则（**按解析器，不按文件**）
--------------------------------
一个文件可能被多个解析器认领，甚至跨类（例如预处理产生的
``*_split_runtime.log`` 同时被 ``WorkerInfoParser`` 与 ``ClientInfoParser`` 认领）。
因此这里**逐个解析器**分派：同一个文件若同时属于两类，就分别交给两个模块处理
（两个模块产出的 label 不相交），而不是整目录回退。

不支持即回退
------------
时间窗 / ``scan_scope`` / ``min_elapsed_ms`` / 未知解析器 → 抛
:class:`ScanVectorUnsupported`，调用方回到逐行路径（绝不静默算错）。

行序
----
输出行序 = 「worker → label 首次出现序 → 文件序 → 文件内行序」，与现状多进程路径
（父进程逐列拼接各 worker、worker 内部 label-major）一致。
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from latency.parse import (
    ClientInfoParser,
    SdkAccessLogParser,
    WorkerAccessLogParser,
    WorkerInfoParser,
)
from latency.schemas.request import ParseConfig

from latency.parse.columns import (
    FLOAT_COLUMNS,
    INT_COLUMNS,
    LIGHT_COLUMNS,
    OUTPUT_COLUMNS,
    SCANNER_INTERNAL_COLUMNS,
)

from .columnar import ALL_COLUMNS
from .scan_vector_access import access_label_columns
from .scan_vector_info import info_label_columns

if TYPE_CHECKING:  # 仅注解使用，运行时不导入（避免与解析器包互相 import）
    from collections.abc import Callable
    from datetime import datetime

    from latency.parse.base_parser import LogParser

logger = logging.getLogger(__name__)

# P1 契约层（2026-09-16）：40 列契约与 dtype 表搬到 ``parse/columns.py``
# （唯一来源），这里 import 回来并保留同名局部名（``_OUTPUT_COLUMNS`` 等既有
# 用法与外部脚本一字不改）。
_INTERNAL_COLUMNS = SCANNER_INTERNAL_COLUMNS
_OUTPUT_COLUMNS = OUTPUT_COLUMNS
_FLOAT_COLUMNS = FLOAT_COLUMNS
_INT_COLUMNS = INT_COLUMNS



class ScanVectorUnsupported(RuntimeError):
    """当前批次形态不支持列运算扫描（调用方回退逐行路径）。"""


def _kind_of(parser: LogParser) -> str:
    if isinstance(parser, (SdkAccessLogParser, WorkerAccessLogParser, ClientInfoParser)):
        return "access"
    if isinstance(parser, WorkerInfoParser):
        return "info"
    raise ScanVectorUnsupported(f"unsupported parser {type(parser).__name__}")


def _check_guards(parsers: list, scan_scope: dict | None) -> None:
    """只剩真正没实现的东西才抛：``scan_scope``（只扫部分 trace/pod 的优化）。

    时间窗与 ``min_elapsed_ms`` 已用列运算实现（见 ``_window_bounds`` /
    ``_min_elapsed_us``），不再属于"不支持"。
    """
    if scan_scope:
        raise ScanVectorUnsupported("scan_scope is not supported by the vector path")
    for parser in parsers:
        if getattr(parser, "_keywords", None) is None:
            raise ScanVectorUnsupported(f"parser without keywords: {type(parser).__name__}")


def _window_bounds(parse_config: ParseConfig | None) -> tuple[int, int] | None:
    """``parse_config`` 的时间窗 → ``(start_epoch, end_epoch)`` 秒；未启用返回 None。

    与老路径 ``LogParser._filter_by_time`` 的 datetime 比较等价（含端点）。
    """
    if parse_config is None:
        return None
    if getattr(parse_config, "start_time", None) and getattr(parse_config, "end_time", None):
        import datetime as _dt  # 用途待确认

        def _epoch(value: str | datetime) -> int:
            parsed = value if isinstance(value, _dt.datetime) else _dt.datetime.fromisoformat(
                str(value).replace(" ", "T", 1)
            )
            return int(parsed.replace(tzinfo=_dt.timezone.utc).timestamp())

        return _epoch(parse_config.start_time), _epoch(parse_config.end_time)
    return None


def _min_elapsed_us(parse_config: ParseConfig | None) -> float | None:
    value = getattr(parse_config, "min_elapsed_ms", None) if parse_config else None
    return None if value is None else float(value) * 1000.0


def _gate_expr(parsers: list) -> pl.Expr:
    import polars as pl  # 懒加载 polars

    keywords: list[str] = []
    for parser in parsers:
        keywords.extend(getattr(parser, "_keywords", None) or [])
    gate = pl.col("line").str.starts_with("2")
    if not keywords:
        return gate
    pattern = "|".join(re.escape(k) for k in dict.fromkeys(keywords))
    inner = pl.col("line").str.contains(pattern)
    if any(getattr(p, "_line_may_match", None) is not None for p in parsers):
        inner = inner | (pl.col("line").str.contains("src")
                         & pl.col("line").str.contains("dst"))
    return gate & inner


# ── 分批并发读（为进度可见性）──────────────────────────────────────────────
#: 每批至少这么多文件；批数 = clamp(文件数 // _FILES_PER_BATCH, 2, _MAX_BATCHES)
_FILES_PER_BATCH = 4
_MAX_BATCHES = 32


def _split_paths_by_size(paths: list[str], k: int) -> list[list[str]]:
    """按文件序（= rank 序）把路径切成 k 个**连续**、大小大致均衡的批。

    连续性让 read 产物天然按 (rank, 文件内行序) 有序：`_project_light` 与
    `iter_wide` 的恢复排序可用 O(n) is_sorted 探测直接跳过（省两次全量
    排序拷贝）。均衡用目标字节数贪心近似；批内文件不跨批，文件内行序
    不变，行序契约 (rank, row) 与负载均衡分法完全一致。
    """
    import os

    sized: list[tuple[int, str]] = []
    for path in paths:
        try:
            sized.append((os.path.getsize(path), path))
        except OSError:
            sized.append((0, path))
    if not sized:
        return []
    total = sum(size for size, _ in sized)
    target = max(total / k, 1.0)
    count = len(sized)
    batches: list[list[str]] = []
    current: list[str] = []
    acc = 0
    for index, (size, path) in enumerate(sized):
        current.append(path)
        acc += size
        files_left = count - index - 1
        batches_left = k - len(batches) - 1
        if acc >= target and batches_left > 0 and files_left >= batches_left:
            batches.append(current)
            current, acc = [], 0
    if current:
        batches.append(current)
    return batches


def _emit_progress(progress_cb: Callable[[float], object] | None, fraction: float) -> None:
    """调用进度回调。回调可能是 async（scanner.scan_all 传进来的就是），
    这种情况用 create_task 派发到当前事件循环（fire-and-forget，进度上报是尽力而为）。
    """
    import inspect  # 用途待确认

    result = progress_cb(fraction)
    if inspect.isawaitable(result):
        import asyncio  # 用途待确认

        try:
            asyncio.get_running_loop().create_task(result)
        except RuntimeError:      # 没有运行中的事件循环（同步调用方给了异步回调）
            asyncio.run(result)


def _read_batch(paths: list[str], gate: pl.Expr) -> pl.DataFrame:
    """一批文件的读 + 行闸门（各自一次 collect）。"""
    import polars as pl  # 懒加载 polars

    return (
        pl.scan_lines(paths, include_file_paths="__file")
        .filter(gate)
        .with_columns(
            # File names repeat for every line; retain one dictionary entry per
            # file instead of a 16-byte string view per record.
            pl.col("__file").cast(pl.Categorical),
            # Filtered StringViews otherwise pin buffers containing discarded
            # lines, including arbitrarily large unrelated runtime messages.
            pl.concat_str([pl.col("line"), pl.lit("")]).alias("line"),
        )
        .collect(engine="streaming")
    )


#: 被跳过的坏文件：(路径, 原因摘要)。原因带异常类型，可直接展示给用户
SkippedFile = tuple[str, str]


def _empty_line_frame() -> pl.DataFrame:
    """一行都没读出来时的空帧（列与 scan_lines 一致），避免把 None 传到下游。"""
    import polars as pl  # 懒加载 polars

    return pl.DataFrame({
        "line": pl.Series([], dtype=pl.Utf8),
        "__file": pl.Series([], dtype=pl.Categorical),
    })


def _read_batch_safely(
    paths: list[str], gate: pl.Expr
) -> tuple[pl.DataFrame | None, list[SkippedFile]]:
    """读一批文件；失败就二分拆分，定位到**具体哪个文件**坏。

    为什么要拆：polars 一次读多个文件时**报错文本里没有文件名**（实测只有
    ``OSError: unexpected end of file`` / ``ComputeError: invalid utf8``），
    不逐文件重试就无法告诉用户是谁坏了。坏文件跳过、其余照常返回 ——
    避免"一两个坏日志让整次解析失败"。

    返回 ``(帧, [(路径, 原因)])``；帧为 ``None`` 表示这一批全读不出来。
    """
    import polars as pl  # 懒加载 polars

    if not paths:
        return None, []
    try:
        return _read_batch(paths, gate), []
    except MemoryError:
        raise  # 内存不足是环境问题，不许当成"坏文件"跳过
    except Exception as exc:  # noqa: BLE001 坏文件不该拖垮整批
        if len(paths) == 1:
            return None, [(paths[0], f"{type(exc).__name__}: {exc}")]
        mid = len(paths) // 2
        left, left_skipped = _read_batch_safely(paths[:mid], gate)
        right, right_skipped = _read_batch_safely(paths[mid:], gate)
        kept = [frame for frame in (left, right) if frame is not None]
        skipped = [*left_skipped, *right_skipped]
        if not kept:
            return None, skipped
        merged = kept[0] if len(kept) == 1 else pl.concat(kept, how="vertical")
        return merged, skipped


def _read_with_progress(paths: list[str], gate: pl.Expr,
                        progress_cb: Callable[[float], object] | None
                        ) -> tuple[pl.DataFrame, list[SkippedFile]]:
    """并发分批读；每完成一批回调一次（已读字节 / 总字节）。返回合并后的帧。

    批与批之间**并发**（polars 在 collect 时释放 GIL），所以总并行度不掉 —— 实测本机
    31 文件 986MB：一批到底 0.509s / 16.2 核；并发 8 批 0.460s / 18.0 核。
    行序契约不受批顺序影响：下游按 (label, 文件序号, 文件内行号) 排序。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed  # 用途待确认

    import os  # 用途待确认

    sizes = {}
    for path in paths:
        try:
            sizes[path] = os.path.getsize(path)
        except OSError:
            sizes[path] = 0
    total = sum(sizes.values()) or 1

    k = min(_MAX_BATCHES, max(2, len(paths) // _FILES_PER_BATCH))
    batches = _split_paths_by_size(paths, k)
    frames = [None] * len(batches)
    skipped: list[SkippedFile] = []
    done = 0
    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = {executor.submit(_read_batch_safely, batch, gate): i
                   for i, batch in enumerate(batches)}
        for future in as_completed(futures):
            index = futures[future]
            frame, batch_skipped = future.result()
            frames[index] = frame
            skipped.extend(batch_skipped)
            done += sum(sizes[p] for p in batches[index])
            if progress_cb is not None:
                _emit_progress(progress_cb, min(1.0, done / total))
    import polars as pl  # 懒加载 polars

    kept = [frame for frame in frames if frame is not None]
    if not kept:
        return _empty_line_frame(), skipped
    if len(kept) == 1:
        return kept[0], skipped
    return pl.concat(kept, how="vertical"), skipped


_LIGHT_BATCH_ROWS = 262_144


def _path_filter(frame, paths):
    """Keep dictionary-encoded scan paths without expanding one string per row."""
    import polars as pl

    posix_paths = [path.replace("\\", "/") for path in paths]
    column = pl.col("__file")
    if frame.schema["__file"] == pl.Categorical and not any(
        "\\" in path for path in frame["__file"].cat.get_categories()
    ):
        return column.is_in(posix_paths)
    return column.cast(pl.String).str.replace("\\", "/", literal=True).is_in(posix_paths)


def _project_light(project, frame, paths, parsers, **kwargs):
    """Filter parser families before allocating path/field string arrays."""
    import polars as pl

    source = frame.with_row_index("__row").filter(_path_filter(frame, paths))
    if source.height <= _LIGHT_BATCH_ROWS:
        return project(source, paths, parsers, light=True, **kwargs)
    # Bound the temporary split/regex columns, which are much larger than the
    # emitted light metrics. Progress reads may interleave file groups, so
    # restore parser file/row order after concatenating the bounded projections.
    parts = [project(batch, paths, parsers, light=True, **kwargs)
             for batch in source.iter_slices(_LIGHT_BATCH_ROWS)]
    out = pl.concat(parts, how="diagonal_relaxed")
    # Read batches are file-rank contiguous, so the common case is already in
    # (__rank, __row) order; the O(n) probe skips the full sort copy.
    rank = out["__rank"]
    if rank.null_count() or not rank.is_sorted():
        return out.sort(["__rank", "__row"], maintain_order=True)
    return out

def scan_frame(file_group_files: list, parsers: list, parse_config: ParseConfig | None = None,
               scan_scope: dict | None = None,
               progress_cb: Callable[[float], object] | None = None,
               light: bool = False
               ) -> tuple[pl.DataFrame, list[SkippedFile], ScanContext | None]:
    """两步扫描：一次读 + 一条链 + 一次 collect。

    返回 ``(DataFrame, [(被跳过文件路径, 原因)], scan_ctx)``：读不出来的文件跳过
    并记账，由调用方告警 —— 不再让一个坏文件把整次解析拖死。

    ``light=True`` 时只投影轻列（``LIGHT_COLUMNS``，全量消费者唯一读到的那些），
    并把**read 产物**装进返回的 :class:`ScanContext` —— 宽列随后按需用
    :func:`materialize_wide` 从这份产物上再算一次，不重读文件。
    """
    import polars as pl  # 懒加载 polars

    # 兼容两种入参：[[(path, indices), ...], ...]（按 worker 分组）或 [(path, indices), ...]
    flat: list[tuple[int, str, list]] = []
    for group_idx, group in enumerate(file_group_files):
        if isinstance(group, (list, tuple)) and group and isinstance(group[0], (list, tuple)):
            for item in group:
                flat.append((group_idx, item[0], item[1]))
        else:
            flat.append((group_idx, group[0], group[1]))
    pairs = [(path, indices) for _, path, indices in flat]
    worker_index_of = {path: group_idx for group_idx, path, _ in flat}
    # 一个文件可同时进 access / info 两侧（跨类解析器）
    access_pairs: list[list] = []
    info_pairs: list[list] = []
    access_bucket: dict[str, str] = {}
    info_bucket: dict[str, str] = {}
    label_rank: dict[tuple[str, str], tuple[int, int]] = {}
    seen_paths: list[str] = []
    seen_parsers: list = []
    for group_idx, path, indices in flat:
        worker_idx = group_idx
        if path not in seen_paths:
            seen_paths.append(path)
        file_parsers = [parsers[i] for i in indices] if indices is not None else list(parsers)
        acc_idx, inf_idx = [], []
        for index, parser in zip(
            indices if indices is not None else range(len(parsers)), file_parsers
        ):
            kind = _kind_of(parser)
            if kind == "access":
                acc_idx.append(index)
                access_bucket.setdefault(path, parser.label)
            else:
                inf_idx.append(index)
                info_bucket.setdefault(path, parser.label)
            if parser not in seen_parsers:
                seen_parsers.append(parser)
            label_rank.setdefault((path, parser.label), (worker_idx, len(label_rank)))
        if acc_idx:
            access_pairs.append([path, acc_idx])
        if inf_idx:
            info_pairs.append([path, inf_idx])

    _check_guards(seen_parsers, scan_scope)
    window = _window_bounds(parse_config)
    min_elapsed_us = _min_elapsed_us(parse_config)
    if not access_pairs and not info_pairs:
        raise ScanVectorUnsupported("no parseable files")

    file_rank = {path: rank for rank, path in enumerate(seen_paths)}
    log_ids = {path: str(uuid.uuid4()) for path in seen_paths}

    # 行序键 = [worker][该 worker 内 label 首次出现序]，编码成一个整数：
    # 复刻现状多进程路径的物理行序（父进程逐列拼接各 worker，worker 内部 label-major）。
    worker_of = {path: group_idx for path, group_idx in worker_index_of.items()}
    bucket_rank: dict[str, int] = {}
    per_worker_seen: dict[int, int] = {}
    for key, (worker_idx, _seq) in sorted(label_rank.items(), key=lambda kv: kv[1][1]):
        path, label = key
        seq = per_worker_seen.get(worker_idx, 0)
        per_worker_seen[worker_idx] = seq + 1
        bucket_rank[f"{worker_of.get(path, 0)}|{label}"] = worker_idx * 4096 + seq

    gate = _gate_expr(seen_parsers)
    if progress_cb is not None and len(seen_paths) > _FILES_PER_BATCH:
        # 分批并发读：每批完成回调一次进度（前端看得到"在读第几批"而不是卡在 0%）
        frame, skipped = _read_with_progress(seen_paths, gate, progress_cb)
    else:
        frame, skipped = _read_batch_safely(seen_paths, gate)
        if frame is None:
            frame = _empty_line_frame()
    if skipped:
        # 坏文件从 file_rank / log_ids / 解析器配对里彻底摘掉：不给读不出来的
        # 文件生成 log_id，也不在它身上再算一遍列。
        bad = {path for path, _ in skipped}
        seen_paths = [path for path in seen_paths if path not in bad]
        access_pairs = [pair for pair in access_pairs if pair[0] not in bad]
        info_pairs = [pair for pair in info_pairs if pair[0] not in bad]
        log_ids = {path: value for path, value in log_ids.items() if path not in bad}
        logger.warning(
            "[skip] %d 个日志文件读取失败已跳过: %s",
            len(skipped),
            ", ".join(f"{path}({reason})" for path, reason in skipped),
        )
    if light:
        light_parts: list = []
        info_cache = None
        if access_pairs:
            rows = _project_light(access_label_columns,
                frame, [p for p, _ in access_pairs],
                [[parsers[i] for i in idx] for _, idx in access_pairs],
                file_rank=file_rank, log_ids=log_ids,
                window=window, min_elapsed_us=min_elapsed_us,
                defer_unused=True,
            )
            if rows.height:
                light_parts.append(rows)
        if info_pairs:
            rows = _project_light(info_label_columns,
                frame, [p for p, _ in info_pairs],
                [[parsers[i] for i in idx] for _, idx in info_pairs],
                file_rank=file_rank,
                defer_unused=True,
                cache_classification=True,
            )
            if rows.height:
                light_parts.append(rows)
                # Retain classification and trace identity from the light
                # pass; the wide pass still validates its numeric extractors.
                # The tid values share the existing locator's string buffers.
                info_cache = rows.select(
                    "__row", "__info_cat", pl.col("tid").alias("__info_tid"),
                )
        # Metric-free rows still need locators for exact wide parsing. They do
        # not contribute to first(non-null), endpoint rank, or latency fallback;
        # avoid allocating eleven typed columns for those INFO/RPC records.
        locator = (
            pl.concat([part.select("tid", "__row") for part in light_parts])
            if light_parts else _empty_light_frame().select("tid", "__row")
        )
        projected = []
        for part in light_parts:
            metrics = [name for name in LIGHT_COLUMNS if name not in {"tid", "_src_rank"} and name in part.columns]
            active = pl.col("_src_rank") != 0
            if metrics:
                active = active | pl.any_horizontal(pl.col(name).is_not_null() for name in metrics)
            projected.append(_normalize_light(part.filter(active)))
        light_rows = (
            pl.concat(
                projected, how="vertical"
            ).select([*_LIGHT_KEYS, *LIGHT_COLUMNS])
            if light_parts
            else _empty_light_frame()
        )
        return light_rows.select(LIGHT_COLUMNS), skipped, ScanContext(
            lines=frame.with_row_index("__row") if info_cache is not None else frame,
            light_rows=locator,
            parsers=tuple(parsers),
            access_pairs=access_pairs,
            info_pairs=info_pairs,
            file_rank=file_rank,
            log_ids=log_ids,
            window=window,
            min_elapsed_us=min_elapsed_us,
            info_cache=info_cache,
        )

    if frame.height == 0:
        return _empty_frame(), skipped, None

    parts: list = []
    if access_pairs:
        rows = access_label_columns(
            frame, [p for p, _ in access_pairs],
            [[parsers[i] for i in idx] for _, idx in access_pairs],
            file_rank=file_rank, log_ids=log_ids,
            window=window, min_elapsed_us=min_elapsed_us,
        )
        if rows.height:
            parts.append(rows)
    if info_pairs:
        rows = info_label_columns(
            frame, [p for p, _ in info_pairs],
            [[parsers[i] for i in idx] for _, idx in info_pairs],
            file_rank=file_rank,
        )
        if rows.height:
            parts.append(rows)
    del frame
    if not parts:
        return _empty_frame(), skipped, None

    # 2026-09-17：删掉"行序键 + 全量 sort"。
    # 旧实现为了复现多进程路径的物理行序，给每行额外挂了 __file/__row/__rank/__bucket
    # 四列（两个字符串列 + 两个整数列）再全量排序；533MB/184 万行实测这套占 497 MB
    # （scan 分步探针 A1 步）。而 polars scan_lines 按给定文件顺序成块输出、批内
    # 文件序+行内序天然成立、批间顺序由 concat 决定（设计文档 §3.1 实测），
    # 所以这一套可以整体去掉。等价性由 40 列 + df_trace 逐列 sha1 验证。
    return pl.concat([_normalize(part) for part in parts], how="vertical").select(
        list(_OUTPUT_COLUMNS)
    ), skipped, None


def _tag(rows: pl.DataFrame, bucket_of: dict) -> pl.DataFrame:
    """给每行打上它所属**解析器标签**（= 现状 merged 的键），供行序排序使用。"""
    import polars as pl  # 懒加载 polars

    return rows.with_columns(
        pl.col("__file").replace_strict(bucket_of, default="", return_dtype=pl.Utf8)
        .alias("__bucket")
    )


def _normalize(part: pl.DataFrame) -> pl.DataFrame:
    """统一列集（缺列补带类型的 null，多列去掉），避免两端列宽不一致。"""
    import polars as pl  # 懒加载 polars

    # 行序键（__file/__row/__rank/__bucket）已随 sort 一并去掉：polars scan_lines
    # 按给定文件顺序成块输出，批内文件序+行内序天然成立，批间由 concat 顺序决定。
    keep = [*_OUTPUT_COLUMNS]
    missing = [name for name in keep if name not in part.columns]
    if missing:
        part = part.with_columns([
            pl.lit(None, dtype=pl.Float64 if name in _FLOAT_COLUMNS
                   else pl.Int64 if name in _INT_COLUMNS else pl.Utf8).alias(name)
            for name in missing
        ])
    return part.select(keep)


# ── 轻列通道：read 产物保留 + 第二次投影 ────────────────────────────────
#: 轻列帧必须带上的行序/定位键（第二次投影靠 __row 定位到 read 产物里的行）
_LIGHT_KEYS: tuple[str, ...] = ("__file", "__row", "__rank")


@dataclass
class ScanContext:
    """轻列扫描留下的现场：**read 产物**（原文行帧）+ 解析器路由，供第二次投影复用。

    这是一次读入、两次投影的支点：宽列只对需要的 trace 算时，不再重读文件。
    """

    lines: pl.DataFrame | None           # read 产物：line + dictionary-encoded __file
    light_rows: pl.DataFrame | None      # 仅 tid + __row；宽列流式消费后释放
    parsers: tuple                       # **原始** parsers 列表（access/info pairs 里的 index 相对它）
    access_pairs: list                   # [(path, [parser_index, ...]), ...]
    info_pairs: list                     # 同上（worker info 侧）
    file_rank: dict                      # 文件 → 序号
    log_ids: dict                        # 文件 → log_id（第二次投影必须沿用同一批，否则 log_id 变）
    window: tuple | None                 # parse_config 的时间窗
    min_elapsed_us: float | None         # parse_config 的最小耗时过滤
    info_cache: pl.DataFrame | None = None  # validated INFO category/tid by source row


def _normalize_light(part: pl.DataFrame) -> pl.DataFrame:
    """轻列帧统一列集（缺列补带类型的 null，多列去掉，列序固定）。"""
    import polars as pl  # 懒加载 polars

    keep = [*_LIGHT_KEYS, *LIGHT_COLUMNS]
    missing = [name for name in keep if name not in part.columns]
    if missing:
        part = part.with_columns([
            pl.lit(None, dtype=pl.Float64 if name in _FLOAT_COLUMNS
                   else pl.Int64 if name in _INT_COLUMNS else pl.Utf8).alias(name)
            for name in missing
        ])
    return part.select([name for name in keep if name in part.columns])


def _empty_light_frame() -> pl.DataFrame:
    """空轻列帧（列与 _normalize_light 的输出一致）。"""
    import polars as pl  # 懒加载 polars

    return pl.DataFrame({
        name: pl.Series([], dtype=pl.Float64 if name in _FLOAT_COLUMNS
                        else pl.Int64 if name in _INT_COLUMNS else pl.Utf8)
        for name in [*_LIGHT_KEYS, *LIGHT_COLUMNS]
    })


def materialize_wide(ctx: ScanContext, tids, *, selected_rows=None) -> pl.DataFrame:
    """**第二次投影**：只对给定 tid 的行算满 40 列（不重读文件）。

    做法：用第一次投影留下的 ``__row``（= read 产物的行号）把 read 产物里这些行
    切出来，再跑与全量路径**同一套**列表达式链。返回的帧只含这些行。
    """
    import polars as pl  # 懒加载 polars

    from .memory_scan import _wanted_series

    if ctx.light_rows is None or ctx.lines is None or ctx.light_rows.height == 0:
        return _empty_frame()
    if selected_rows is None:
        wanted = _wanted_series(tids)
        if wanted.is_empty():
            return _empty_frame()
        selected_rows = ctx.light_rows.filter(pl.col("tid").is_in(wanted.implode()))
    keep = (
        selected_rows
        .select("__row")
        .unique()
        .sort("__row")
    )
    if keep.height == 0:
        return _empty_frame()
    sub = ctx.lines if keep.height == ctx.lines.height else ctx.lines[keep.to_series()]
    if sub.height == 0:
        return _empty_frame()

    parts: list = []
    if ctx.access_pairs:
        rows = access_label_columns(
            sub, [p for p, _ in ctx.access_pairs],
            [[ctx.parsers[i] for i in idx] for _, idx in ctx.access_pairs],
            file_rank=ctx.file_rank, log_ids=ctx.log_ids,
            window=ctx.window, min_elapsed_us=ctx.min_elapsed_us,
        )
        if rows.height:
            parts.append(rows)
    if ctx.info_pairs:
        info_source = sub
        if ctx.info_cache is not None:
            info_source = sub.join(
                ctx.info_cache, on="__row", how="left", maintain_order="left",
            )
        rows = info_label_columns(
            info_source, [p for p, _ in ctx.info_pairs],
            [[ctx.parsers[i] for i in idx] for _, idx in ctx.info_pairs],
            file_rank=ctx.file_rank,
        )
        if rows.height:
            parts.append(rows)
    if not parts:
        return _empty_frame()
    return pl.concat([_normalize(part) for part in parts], how="vertical").select(
        list(_OUTPUT_COLUMNS)
    )


def _empty_frame() -> pl.DataFrame:
    """空结果：**列名齐全且 dtype 正确**，下游 build_trace_frame 能直接吃。"""
    import polars as pl  # 懒加载 polars

    return pl.DataFrame({
        name: pl.Series([], dtype=pl.Float64 if name in _FLOAT_COLUMNS
                        else pl.Int64 if name in _INT_COLUMNS else pl.Utf8)
        for name in _OUTPUT_COLUMNS
    })
