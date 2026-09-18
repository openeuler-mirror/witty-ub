import asyncio
import os
import logging
import uuid
import time
import shutil

from collections.abc import Iterator
from typing import Any

from latency.task.worker.base import BaseWorker
from latency.config.config import Config
from latency.common.trace_context import match_trace_context_trace_id
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.task.worker.kv_cache_log_event_diagnosis_worker import KVCacheLogEventDiagnosisWorker
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.schemas.log import LogFileModel
from latency.schemas.task import TaskModel
from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgePGManager
from latency.task.log_preprocessor import cleanup_preprocess_dir
from latency.common.stage_timing import StageTimer


logger = logging.getLogger(__name__)
WITTY_DIR_DEFAULT = "/var/witty-ub"
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)

# 扫描实现开关：默认走 polars（WITTY_STORE_POLARS=0 回退旧逐行实现）
STORE_POLARS_ENV = "WITTY_STORE_POLARS"


def store_polars_enabled() -> bool:
    return os.getenv(STORE_POLARS_ENV, "1").strip().lower() not in {"0", "false", "no"}

SUCCESS_STATUSES = {
    TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
    TaskStatusEnum.SUCCESSFUL,
}
FAILED_STATUSES = {
    TaskStatusEnum.FAILED_PENDING_REMOVE,
    TaskStatusEnum.FAILED,
    TaskStatusEnum.CANCELLED,
}
MONITOR_INTERVAL_SECONDS = 1


class ContextStoreError(RuntimeError):
    """A failed write must fail the task, rather than skip a raw log line."""


def cleanup_temp_dirs(output_log_path: str, log_file_id: str) -> None:
    """清理临时文件夹，包括诊断输出和预处理的日志"""
    if output_log_path and os.path.exists(output_log_path):
        try:
            shutil.rmtree(output_log_path)
            logger.info("清理诊断输出目录: %s", output_log_path)
        except OSError as e:
            logger.error("清理诊断输出目录 %s 失败: %s", output_log_path, e)
    
    if log_file_id:
        cleanup_preprocess_dir(log_file_id)


class StoreTraceContextLogsWorker(BaseWorker):
    """
    Worker for storing trace context logs.
    """

    name = TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER

    @staticmethod
    async def _generate_trace_id_set_diagnosis(output_log_path: str) -> tuple[set[str], dict[str, list[str]]]:
        trace_id_set = set()
        trace_failure_id = dict()
        if not os.path.exists(output_log_path):
            logger.error(f"输出日志路径不存在: {output_log_path}")
            return set(), dict()
        
        failure_trace_path = os.path.join(output_log_path, "failure_trace.log")
        if os.path.exists(failure_trace_path):
            try:
                with open(failure_trace_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            raw_text = parts[1].strip()
                            raw_parts = raw_text.split('|')
                            trace_failure_id[raw_text] = list(dict.fromkeys(
                                mode.strip()
                                for mode in parts[0].split(",")
                                if mode.strip()
                            ))
                            if len(raw_parts) >= 6:
                                trace_id = raw_parts[5].strip()
                                if trace_id:
                                    trace_id_set.add(trace_id)
                
                logger.info(f"从 failure_trace.log 提取到 {len(trace_id_set)} 个 trace_id")
            
            except Exception as e:
                logger.error(f"解析 failure_trace.log 失败: {e}")

        return trace_id_set, trace_failure_id

    @staticmethod
    def _context_scan_frame(
        log_files: list[tuple[str, str]],
        trace_id_set: set,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> Any:
        """用 polars 一次扫完输出目录，挑出 trace_id 命中的行。

        与旧的逐行实现**逐字段等价**（口径逐条对齐）：
          - 只取顶层文件、跳过 failure_trace.log，顺序 = 传入顺序（= os.listdir 顺序）
          - 行闸门：按 '|' 切开 ≥7 段；trace_id = 第 6 段 strip 后非空且 ∈ trace_id_set
          - access 文件（文件名匹配 worker/client access 模式）的行必须 ≥8 段，否则丢
          - pid/tid：pid:tid 恰好两段才拆，否则 tid=""
          - status_code：仅 access 文件取第 8 段；message：第 8 段起的原文（strip）
          - timestamp：第 1 段 strip 后把 "T" 换成空格
          - src_ip/dst_ip：src= / src address: / srcAddress= 三种模式，**两者都取到才算**
          - operation：第 9 段 strip 后在 GET/SET 集合里
        """
        # 用途待确认（实测：导入本模块时 polars 已被传递加载，不是为了省子进程启动成本）
        import polars as pl

        # 用途待确认（实测：本模块导入时 keywords 已被传递加载）
        from latency.parse.keywords import (
            SDK_GET_OPS,
            SDK_SET_OPS,
            WORKER_GET_OPS,
            WORKER_SET_OPS,
        )

        out_cols = (
            "log_file", "raw_text", "timestamp", "level", "filename", "pod_name",
            "pid", "tid", "trace_id", "cluster_name", "message", "status_code",
            "src_ip", "dst_ip", "operation",
        )
        paths = [
            path
            for _name, path in log_files
            if os.path.isfile(path) and os.path.getsize(path) > 0
        ]
        if not paths or not trace_id_set:
            logger.info("上下文扫描：没有可读文件或 trace 集合为空")
            return pl.DataFrame({name: [] for name in out_cols})

        access_names = [
            name
            for name, _path in log_files
            if KVCacheLogEventDiagnosisWorker._matches_any(name, worker_access_patterns)
            or KVCacheLogEventDiagnosisWorker._matches_any(name, client_access_patterns)
        ]
        ids_df = pl.DataFrame({"trace_id": sorted(trace_id_set)})

        ip = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        strip = lambda expr: expr.str.strip_chars()  # noqa: E731

        def field(index: int):
            return pl.col("_p").struct.field(f"field_{index}")

        f4 = strip(field(4))
        two_parts = f4.str.count_matches(":") == 1
        src = pl.coalesce([
            pl.col("line").str.extract(r"(?i)src=" + ip, 1),
            pl.col("line").str.extract(r"(?i)src address:" + ip, 1),
            pl.col("line").str.extract(r"(?i)srcAddress\s*=\s*" + ip, 1),
        ])
        dst = pl.coalesce([
            pl.col("line").str.extract(r"(?i)dst=" + ip, 1),
            pl.col("line").str.extract(r"(?i)target address:" + ip, 1),
            pl.col("line").str.extract(r"(?i)targetAddress\s*=\s*" + ip, 1),
        ])
        both = src.is_not_null() & dst.is_not_null()
        sub7 = field(7).str.split("|")
        handle = strip(sub7.list.get(1, null_on_oob=True))
        is_access = pl.col("log_file").is_in(access_names)
        get_vals = sorted({op.value for op in (*SDK_GET_OPS, *WORKER_GET_OPS)})
        set_vals = sorted({op.value for op in (*SDK_SET_OPS, *WORKER_SET_OPS)})

        # splitn 只切一次（抄 parse/parallel_scanner 的做法），后面都从 _p 取字段
        lf = pl.scan_lines(paths, include_file_paths="_path").with_columns(
            log_file=pl.col("_path").str.extract(r"([^/\\]+)$", 1),
            _p=pl.col("line").str.splitn("|", 8),
        )
        return (
            lf.with_columns([field(index).alias(f"_f{index}") for index in range(8)])
            .filter(pl.col("_f6").is_not_null())  # ≥7 段
            .with_columns(trace_id=strip(pl.col("_f5")))
            .filter(pl.col("trace_id") != "")
            .join(ids_df.lazy(), on="trace_id", how="semi")
            .filter(~(is_access & pl.col("_f7").is_null()))  # access 行必须 ≥8 段
            .select([
                pl.col("log_file"),
                # 与旧实现一致：raw_text 是 strip() 之后的整行
                strip(pl.col("line")).alias("raw_text"),
                strip(pl.col("_f0")).str.replace_all("T", " ").alias("timestamp"),
                strip(pl.col("_f1")).alias("level"),
                strip(pl.col("_f2")).alias("filename"),
                strip(pl.col("_f3")).alias("pod_name"),
                pl.when(two_parts).then(f4.str.split(":").list.get(0, null_on_oob=True)).otherwise(f4).alias("pid"),
                pl.when(two_parts).then(f4.str.split(":").list.get(1, null_on_oob=True)).otherwise(pl.lit("")).alias("tid"),
                pl.col("trace_id"),
                strip(pl.col("_f6")).alias("cluster_name"),
                strip(pl.col("_f7").fill_null("")).alias("message"),
                pl.when(is_access)
                .then(strip(sub7.list.get(0, null_on_oob=True)))
                .otherwise(pl.lit(""))
                .alias("status_code"),
                pl.when(both).then(src).otherwise(pl.lit("")).alias("src_ip"),
                pl.when(both).then(dst).otherwise(pl.lit("")).alias("dst_ip"),
                pl.when(handle.is_in(get_vals)).then(pl.lit("GET"))
                .when(handle.is_in(set_vals)).then(pl.lit("SET"))
                .otherwise(pl.lit(""))
                .alias("operation"),
            ])
            .collect()
        )

    @staticmethod
    def _legacy_row_batches(
        log_files: list[tuple[str, str]],
        trace_id_set: set,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> Iterator[list[dict]]:
        """旧的逐行扫描（WITTY_STORE_POLARS=0 回退用）：一个文件 yield 一批 dict。"""
        for log_file_name, log_file_path in log_files:
            try:
                is_access_log = False
                if KVCacheLogEventDiagnosisWorker._matches_any(
                    log_file_name, worker_access_patterns
                ):
                    is_access_log = True
                if KVCacheLogEventDiagnosisWorker._matches_any(
                    log_file_name, client_access_patterns
                ):
                    is_access_log = True
                rows = []
                # errors='replace'：非 UTF-8 字符不让整批崩掉
                with open(log_file_path, "r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        try:
                            raw_line = line.strip()
                            if not raw_line:
                                continue
                            parts = raw_line.split("|", 8)
                            if len(parts) < 7:
                                continue
                            trace_id = match_trace_context_trace_id(
                                parts[5].strip() if len(parts) > 5 else "",
                                raw_line,
                                trace_id_set,
                            )
                            if not trace_id:
                                continue
                            pid_tid = parts[4].strip()
                            pid_tid_parts = pid_tid.split(":")
                            if len(pid_tid_parts) == 2:
                                pid, tid = pid_tid_parts
                            else:
                                pid, tid = pid_tid, ""
                            if is_access_log:
                                if len(parts) > 7:
                                    status_code = parts[7].strip()
                                    message = "|".join(parts[7:])
                                else:
                                    logger.warning(
                                        f"access log格式不正确，字段不足: {raw_line}"
                                    )
                                    continue
                            else:
                                status_code = ""
                                message = "|".join(parts[7:]) if len(parts) > 7 else ""
                            rows.append({
                                "log_file": log_file_name,
                                "raw_text": raw_line,
                                "timestamp": parts[0].strip().replace("T", " "),
                                "level": parts[1].strip(),
                                "filename": parts[2].strip(),
                                "pod_name": parts[3].strip(),
                                "pid": pid,
                                "tid": tid,
                                "trace_id": trace_id,
                                "cluster_name": parts[6].strip() if len(parts) > 6 else "",
                                "message": message.strip(),
                                "status_code": status_code,
                            })
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                f"读取日志文件 {log_file_path} 行失败: {line}, 错误: {exc}"
                            )
                            continue
                if rows:
                    yield rows
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"读取日志文件 {log_file_path} 失败: {exc}")
                continue

    @staticmethod
    async def _load_store_context(
        output_log_path: str,
        log_id: str,
    ) -> tuple[list[str], list[str], dict, list[tuple[str, str]]]:
        """输入：输出目录 + log_id → 输出：(access 模式, failure_mode_cache, 待扫文件)。"""
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_id)
        config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(
            log_file_model.kb_id if log_file_model else None
        )
        failure_mode_cache = await FailureModeKnowledgePGManager.get_all_failure_modes()
        worker_access_patterns = config.get("ds_worker_access_log_file", [])
        client_access_patterns = config.get("ds_client_access_log_file", [])

        log_files = []
        for file in os.listdir(output_log_path):
            file_path = os.path.join(output_log_path, file)
            if os.path.isfile(file_path) and file != "failure_trace.log":
                log_files.append((file, file_path))
        return worker_access_patterns, client_access_patterns, failure_mode_cache, log_files

    @staticmethod
    def _scan_context_rows(
        log_files: list[tuple[str, str]],
        trace_id_set: set[str],
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> tuple[int, bool, Any]:
        """输入：文件清单 + trace 集合 + access 模式 → 输出：(总行数, 是否走 polars, frame)。

        polars 路径走 `_context_scan_frame`（frame.height 即进度条分母），
        旧路径走 `_count_log_failure_events` 数行（WITTY_STORE_POLARS=0 回退）。
        """
        use_polars = store_polars_enabled()
        if not use_polars:
            total_log_failure_events = (
                KVCacheLogEventDiagnosisWorker._count_log_failure_events(
                    log_files,
                    trace_id_set,
                    worker_access_patterns,
                    client_access_patterns,
                )
            )
            return total_log_failure_events, use_polars, None

        frame = StoreTraceContextLogsWorker._context_scan_frame(
            log_files,
            trace_id_set,
            worker_access_patterns,
            client_access_patterns,
        )
        return frame.height, use_polars, frame

    @staticmethod
    async def _ingest_log_failure_events(
        log_files: list[tuple[str, str]],
        trace_id_set: set[str],
        trace_failure_id: dict[str, list[str]] | None,
        failure_mode_cache: dict,
        log_id: str,
        task_id: str | None,
        use_polars: bool,
        frame: Any,
        total_log_failure_events: int,
        progress_base: float,
        progress_end: float,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> tuple[int, dict[str, dict]]:
        """输入：扫描结果 + 进度区间 → 输出：(已落库行数, trace 级合并结果)。"""
        log_failure_events = []
        trace_failure_events_map: dict[str, dict] = {}
        total_inserted = 0
        batch_size = 8192

        async def _write_batch(batch):
            try:
                await LogFailureEventPGManager.add_log_failure_event_raw(batch)
            except Exception as exc:
                raise ContextStoreError("Failed to store trace context batch") from exc

        def _report_progress(inserted: int) -> None:
            if not task_id or total_log_failure_events <= 0:
                return
            progress = progress_base + (progress_end - progress_base) * (
                inserted / total_log_failure_events
            )
            asyncio.create_task(
                BaseWorker.report(
                    task_id,
                    f"Trace context logs stored {inserted}/{total_log_failure_events}",
                    min(progress, progress_end),
                )
            )

        async def _consume_row(row: dict) -> None:
            """一行日志 → 库记录：组装字段、并入 trace 级统计、凑批落库。"""
            nonlocal log_failure_events, total_inserted
            raw_line = row["raw_text"]
            log_failure_event = {
                "id": str(uuid.uuid4()),
                "log_id": log_id,
                "log_file": row["log_file"],
                "raw_text": raw_line,
                "host_name": "Unknown",
                "timestamp": row["timestamp"],
                "level": row["level"],
                "filename": row["filename"],
                "pod_name": row["pod_name"],
                "pid": row["pid"],
                "tid": row["tid"],
                "trace_id": row["trace_id"],
                "cluster_name": row["cluster_name"],
                "message": row["message"],
                "status_code": row["status_code"],
                "failure_mode": (
                    trace_failure_id.get(raw_line, []) if trace_failure_id else None
                ),
            }
            if "src_ip" in row:
                # 扫描侧已向量化算好（含"确实为空"），合并那步不再逐行跑正则
                log_failure_event["src_ip"] = row["src_ip"]
                log_failure_event["dst_ip"] = row["dst_ip"]
                log_failure_event["operation"] = row["operation"]
            KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(
                trace_failure_events_map,
                log_failure_event,
                failure_mode_cache,
            )
            log_failure_events.append(log_failure_event)

            if len(log_failure_events) >= batch_size:
                await _write_batch(log_failure_events)
                total_inserted += len(log_failure_events)
                progress_msg = (
                    f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
                )
                logger.info(progress_msg)
                _report_progress(total_inserted)
                log_failure_events = []

        if use_polars:
            # 一批 batch_size 行地取，内存与旧实现同量级
            for offset in range(0, frame.height, batch_size):
                for row in frame.slice(offset, batch_size).to_dicts():
                    await _consume_row(row)
        else:
            for rows in StoreTraceContextLogsWorker._legacy_row_batches(
                log_files,
                trace_id_set,
                worker_access_patterns,
                client_access_patterns,
            ):
                for row in rows:
                    await _consume_row(row)

        if log_failure_events:
            await _write_batch(log_failure_events)
            total_inserted += len(log_failure_events)
            progress_msg = (
                f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
            )
            logger.info(progress_msg)
            _report_progress(total_inserted)

        return total_inserted, trace_failure_events_map

    @staticmethod
    async def _write_trace_failure_events(
        trace_failure_events_map: dict[str, dict],
        failure_mode_cache: dict,
        total_inserted: int,
        total_log_failure_events: int,
        store_started_at: float,
        task_id: str | None,
        progress_end: float,
    ) -> None:
        """输入：trace 级合并结果 → 输出：无（剪枝故障模式、写 trace 表、报总进度与总耗时）。"""
        trace_failure_events = list(trace_failure_events_map.values())
        for trace_failure_event in trace_failure_events:
            # 跨日志剪枝：某模式在 trace 中存在更深层命中（如 access 根与
            # runtime 子节点同时命中）时，只保留更深的子节点。
            trace_failure_event["failure_mode"] = (
                KVCacheLogEventDiagnosisWorker._leaf_failure_modes(
                    trace_failure_event.get("failure_mode") or [], failure_mode_cache
                )
            )
            # 聚合故障码的口径是 access 日志命中的故障模式；
            # runtime 模式仍保留在 failure_mode 中供 trace 详情展示。
            access_failure_modes = trace_failure_event.pop(
                "_access_failure_modes", []
            )
            trace_failure_event["status_code"] = (
                KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
                    access_failure_modes, failure_mode_cache
                )
            )
        if trace_failure_events:
            trace_store_start = time.perf_counter()
            await LogFailureEventPGManager.add_trace_failure_event_raw(trace_failure_events)
            logger.info(
                "成功插入 %s 条trace故障事件，耗时 %.3fs",
                len(trace_failure_events),
                time.perf_counter() - trace_store_start,
            )

        logger.info(
            "Trace context logs store done: %s log_failure_events, %s trace_failure_events, total %.3fs",
            total_inserted,
            len(trace_failure_events),
            time.perf_counter() - store_started_at,
        )

        if task_id:
            await BaseWorker.report(
                task_id,
                f"Trace context logs stored {total_inserted}/{total_log_failure_events}",
                progress_end,
            )

    @staticmethod
    async def _store_trace_context_logs(
        output_log_path: str,
        log_id: str,
        trace_id_set: set,
        trace_failure_id: dict[str, list[str]],
        task_id: str | None = None,
        progress_base: float = 0.0,
        progress_end: float = 100.0,
    ) -> None:
        # 将output_log_path下，除了failure_trace.log以外的所有日志读到log_failure_event_table数据库中
        # 除了failure_trace.log以外，output_log_path目录下的日志都是以下模板："timestamp | level | filename | pod_name | pid:tid | trace_id | cluster_name | message"，  
        # 对应LogFailureEventModel数据结构中的相应字段。除了这些字段以外，log_id对应函数参数输入，log_file对应日志文件名，raw_text对应原始日志。
        # status_code的读取方式略微复杂。仅当log_file对应的日志文件名能够匹配parse_filepath_config()得到的字典中，键为ds-worker-access-log-file和
        # ds-client-access-log-file的值所表示的正则表达式，即为access log日志时，日志才有status_code字段。具体而言，status_code字段是message字段中以" | "分割的第一个字段
        # 将failure_trace.log中的故障模式字段添加到数据库中
        # 将output_log_path下的failure_trace.log中是解析到的所有故障日志。每行日志的格式为failure_mode | raw_text，即将failure_mode字段添加到raw_text对应行的数据库条目中。你应该需要在
        # LogFailureEventManager中加入一个update_failure_mode_by_raw_log函数来完成数据库更新的操作。
        try:
            if not trace_id_set:
                logger.info("failure_trace.log 中没有可落库的 trace_id")
                return

            (
                worker_access_patterns,
                client_access_patterns,
                failure_mode_cache,
                log_files,
            ) = await StoreTraceContextLogsWorker._load_store_context(output_log_path, log_id)

            (
                total_log_failure_events,
                use_polars,
                frame,
            ) = StoreTraceContextLogsWorker._scan_context_rows(
                log_files, trace_id_set, worker_access_patterns, client_access_patterns
            )

            logger.info(
                f"开始日志落库，共{len(trace_id_set)}条故障trace，{total_log_failure_events}条日志事件"
                f"（扫描={'polars' if use_polars else 'legacy'}）"
            )
            t_store_start = time.perf_counter()

            (
                total_inserted,
                trace_failure_events_map,
            ) = await StoreTraceContextLogsWorker._ingest_log_failure_events(
                log_files=log_files,
                trace_id_set=trace_id_set,
                trace_failure_id=trace_failure_id,
                failure_mode_cache=failure_mode_cache,
                log_id=log_id,
                task_id=task_id,
                use_polars=use_polars,
                frame=frame,
                total_log_failure_events=total_log_failure_events,
                progress_base=progress_base,
                progress_end=progress_end,
                worker_access_patterns=worker_access_patterns,
                client_access_patterns=client_access_patterns,
            )

            await StoreTraceContextLogsWorker._write_trace_failure_events(
                trace_failure_events_map=trace_failure_events_map,
                failure_mode_cache=failure_mode_cache,
                total_inserted=total_inserted,
                total_log_failure_events=total_log_failure_events,
                store_started_at=t_store_start,
                task_id=task_id,
                progress_end=progress_end,
            )

            return

        except Exception as e:
            # 不打第二套机制：上下文留全后照旧外抛，由 run() 统一落失败原因
            logger.exception(
                "parse_log_failure_events 执行失败: %s (task_id=%s, log_id=%s, output_log_path=%s)",
                e,
                task_id,
                log_id,
                output_log_path,
            )
            raise

        return

    @staticmethod
    async def init(op_id: str) -> str | None:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None

        task = TaskModel(
            kb_id=log_file_model.kb_id,
            op_id=op_id,
            task_name=f"Store trace context logs: {log_file_model.name}",
            task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        if task.retry_times > Config().get_config().task.task_retry_times:
            logger.warning(
                "Task %s retry count %s exceeded max retries %s",
                task_id,
                task.retry_times,
                Config().get_config().task.task_retry_times,
            )
            return False
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        return task_id

    @staticmethod
    async def _wait_for_worker_success(
        op_id: str,
        task_type: TaskTypeEnum,
        dependency_name: str,
        monitor_task_id: str,
        progress: float,
    ) -> bool:
        while True:
            task = await TaskPGManager.get_current_task_by_op_id(op_id, task_type)
            if not task:
                await BaseWorker.report(
                    monitor_task_id,
                    f"Waiting for {dependency_name} task to be created",
                    progress,
                )
                await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
                continue

            if task.status in SUCCESS_STATUSES:
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task completed",
                    progress,
                )
                return True

            if task.status in FAILED_STATUSES:
                logger.error(
                    "%s task %s ended with status %s",
                    dependency_name,
                    task.id,
                    task.status,
                )
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task ended with status {task.status}",
                    progress,
                )
                return False

            await BaseWorker.report(
                monitor_task_id,
                f"Waiting for {dependency_name} task, current status: {task.status}",
                progress,
            )
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        output_log_path = None
        log_file_id = None
        log_id = None
        t_run_start = time.perf_counter()  # [timing] 阶段偏移的基准 = run() 起点
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task:
                logger.error("Task %s not found", task_id)
                return False

            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "Task running", 5.0)
            # [timing] 三段在这里登记（契约见 common/stage_timing.py）：
            # 等诊断/等解析 → 生成 trace_id 集合 → 落库；任务成功结束前 emit。
            timer = StageTimer(
                started_at=t_run_start,
                wall_started_at=getattr(task, "created_at", None),
                task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER.value,
            )

            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error("LogFile %s not found", task.op_id)
                await TaskPGManager.mark_failed_with_report(
                    task_id,
                    f"任务失败：日志文件不存在（{task.op_id}）",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(None, task.op_id)
                return False

            log_id = log_file.id
            log_file_id = log_file.id
            random_str = log_file.id[:8]
            output_log_path = os.path.join(witty_dir, "log_" + random_str)

            diagnosis_trace_ids = await StoreTraceContextLogsWorker._stage_after_diagnosis(
                task, timer, output_log_path, log_id, log_file_id
            )
            if diagnosis_trace_ids is None:  # None=已按失败收敛；空集合是合法结果
                return False

            if not await StoreTraceContextLogsWorker._stage_after_parse(
                task, timer, output_log_path, log_id, log_file_id, diagnosis_trace_ids
            ):
                return False

            await StoreTraceContextLogsWorker._finish_run(
                task, log_file, output_log_path, log_file_id, timer
            )
            return True
        except Exception as e:
            # 该吞还得吞：更新任务状态后返回 False，但栈与定位信息留全
            logger.exception(
                "Task %s failed (log_id=%s, output_log_path=%s): %s",
                task_id,
                log_id,
                output_log_path,
                e,
            )
            await TaskPGManager.mark_failed_with_report(
                task_id,
                f"任务失败：Trace 上下文落库异常，{type(e).__name__}: {e}",
                status=TaskStatusEnum.FAILED_PENDING_REMOVE,
            )
            return False

    @staticmethod
    async def _stage_after_diagnosis(
        task: TaskModel,
        timer: StageTimer,
        output_log_path: str,
        log_id: str,
        log_file_id: str,
    ) -> set[str] | None:
        """输入：任务 + 计时器 + 输出目录 → 输出：定界 trace_id 集合；失败收敛时返回 None。"""
        with timer.stage("trace_store_wait") as wait_scope:
            wait_scope.detail = "等故障定界完成"
            diagnosis_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
                "diagnosis",
                task.id,
                20.0,
            )
            if not diagnosis_done:
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    "任务失败：依赖的故障诊断任务未成功完成",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

            # 检查任务是否被取消
            current_task = await TaskPGManager.get_task_by_task_id(task.id)
            if not current_task or current_task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task.id} 已被取消或不存在，停止执行")
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

            if not os.path.isdir(output_log_path) or not os.listdir(output_log_path):
                logger.error(f"诊断输出目录不存在或为空: {output_log_path}")
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    f"任务失败：诊断输出目录不存在或为空（{output_log_path}）",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

        with timer.stage("trace_store_collect") as collect_scope:
            trace_id_set, trace_failure_id = await StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(
                output_log_path=output_log_path,
            )
            collect_scope.detail = f"定界产出 {len(trace_id_set)} 个故障 trace"

        with timer.stage("trace_store_write") as write_scope:
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=trace_failure_id,
                task_id=task.id,
                progress_base=20.0,
                progress_end=45.0,
            )
            # Raw diagnostic lines are no longer needed while waiting for parse.
            del trace_failure_id
            await LogFilePGManager.update_log_file(
                task.op_id, {
                    "failure_count": len(trace_id_set),
                    "trace_failure_event_cnt": len(trace_id_set),
                }
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after diagnosis: {len(trace_id_set)}",
                45.0,
            )
            write_scope.detail = f"故障 trace {len(trace_id_set)} 条落库"

        return trace_id_set

    @staticmethod
    async def _stage_after_parse(
        task: TaskModel,
        timer: StageTimer,
        output_log_path: str,
        log_id: str,
        log_file_id: str,
        diagnosis_trace_id_set: set[str],
    ) -> bool:
        """输入：任务 + 计时器 + 定界 trace 集合 → 输出：True=可以收尾，False=已按失败收敛。"""
        with timer.stage("trace_store_wait") as wait_scope:
            wait_scope.detail = "等解析完成"
            parse_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
                "parse",
                task.id,
                65.0,
            )
            if not parse_done:
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    "任务失败：依赖的日志解析任务未成功完成",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

            # 检查任务是否被取消
            current_task = await TaskPGManager.get_task_by_task_id(task.id)
            if not current_task or current_task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task.id} 已被取消或不存在，停止执行")
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

        with timer.stage("trace_store_collect") as collect_scope:
            t_ids = time.perf_counter()
            latency_anomalous_trace_id_set = await LogParseResultPGManager.list_anomalous_trace_ids_by_log_id(
                log_id
            )
            anomalous_trace_count = len(latency_anomalous_trace_id_set)
            trace_id_set = latency_anomalous_trace_id_set - diagnosis_trace_id_set
            collect_scope.detail = f"解析新增时延异常 {len(trace_id_set)} 个 trace_id"
            logger.info(
                "新增 %s 个时延异常 trace_id",
                len(trace_id_set),
            )
            logger.info("[perf][context.ids] new_traces=%d elapsed_s=%.3f",
                        len(trace_id_set), time.perf_counter() - t_ids)

        with timer.stage("trace_store_write") as write_scope:
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=None,
                task_id=task.id,
                progress_base=65.0,
                progress_end=90.0,
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after parse: {anomalous_trace_count}",
                90.0,
            )
            write_scope.detail = f"时延异常 trace {len(trace_id_set)} 条落库"
        return True

    @staticmethod
    async def _finish_run(
        task: TaskModel,
        log_file: LogFileModel,
        output_log_path: str,
        log_file_id: str,
        timer: StageTimer,
    ) -> None:
        """输入：任务 + 日志文件 + 计时器 → 输出：无（清临时目录、置成功、发 [timing] 打点）。"""
        if log_file.kb_id:
            # failure_count 刚更新到 log_file，重新聚合保证 KB 计数同步。
            await LogKnowledgePGManager.refresh_kb_counters(log_file.kb_id)

        cleanup_temp_dirs(output_log_path, log_file_id)
        await BaseWorker.report(task.id, "Task completed successfully", 100.0)
        await TaskPGManager.update_task(
            task.id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
        )
        try:  # 打点失败绝不影响任务成败
            await timer.emit(task.id, rows=0)
        except Exception:
            logger.warning("[timing] emit failed for %s", task.id, exc_info=True)

    @staticmethod
    async def stop(task_id: str) -> str | None:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return None
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        return task_id
