import asyncio
import logging
import os
from collections import defaultdict
from plugins.latency.schemas.log import LogParseResultModel
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.task.process_handle import ProcessHandler
from latency.parse import (
    SdkAccessLogParser,
    WorkerAccessLogParser,
    UrmaLogParser,
    RemotePullLogParser,
    LinkLogParser,
    QueryMetaLogParser,
    LogCorrelator,
    ParseResultBuilder,
)
from latency.common.ds_log_io import glob_paths, open_log
from latency.common.stats import stats
from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventManager,
)
from latency.database.managers.anomalous_event import AnomalousEventManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainManager
from latency.config.config import Config
from latency.schemas.task import TaskModel
from latency.schemas.log import (
    LogFileModel,
    SrcDstAggregatedEventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
)

logger = logging.getLogger(__name__)

_PROGRESS_UPDATE_LINES = 100_000


def _scan_file(parser, path: str) -> tuple[str, list]:
    pod_ip = parser.extract_pod_ip(path)
    log_file = LogFileModel(file_path=path, file_size=os.path.getsize(path))
    file_name = os.path.basename(path)
    entries = []
    try:
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                if line_no % _PROGRESS_UPDATE_LINES == 0:
                    logger.info(
                        f"[{parser.label}] scanning {file_name} | "
                        f"line {line_no:,} | match {len(entries):,}"
                    )
                entry = parser.match_line(line, pod_ip)
                if entry:
                    entry.log_id = log_file.id
                    entries.append(entry)
    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")
    logger.info(
        f"[{parser.label}] done {file_name} | "
        f"lines scanned | match {len(entries):,}"
    )
    return parser.label, entries


class KVCacheLogParseWorker:
    """
    KVCacheLogParseWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    @staticmethod
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        log_kb_model = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb_model:
            return None

        task = TaskModel(
            kb_id=log_kb_model.id,
            op_id=op_id,
            task_name=f"解析日志文件 {log_file_model.name}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskManager.add_task(task)
        await LogFileManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            return False
        await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await TaskReportManager.update_task_report_status_by_task_id(
            task_id, status=TaskStatusEnum.PENDING
        )
        if task.retry_times > Config().get_config().task_retry_times:
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
            )
            logger.warning(
                f"任务 {task_id} 重试次数 {task.retry_times} 已超过最大重试次数 {Config().get_config().task.task_retry_times}"
            )
            return False
        await LogFileManager.update_log_file(
            task.op_id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    # 解析日志
    @staticmethod
    async def parse_log(
        log_dir: str,
    ) -> list[LogParseResultModel]:
        parsers = [
            SdkAccessLogParser(),
            WorkerAccessLogParser(),
            UrmaLogParser(),
            RemotePullLogParser(),
            LinkLogParser(),
            QueryMetaLogParser(),
        ]

        scan_tasks = []
        for parser in parsers:
            paths = glob_paths(
                [os.path.join(log_dir, p) for p in parser.patterns]
            )
            logger.info(f"[{parser.label}] found {len(paths)} file(s)")
            for path in paths:
                scan_tasks.append(asyncio.to_thread(_scan_file, parser, path))

        total_tasks = len(scan_tasks)
        logger.info(f"=== Stage 1/3: Scanning {total_tasks} file(s) ===")

        scan_results = await asyncio.gather(*scan_tasks)

        parsed: dict[str, list] = {}
        for label, entries in scan_results:
            parsed.setdefault(label, []).extend(entries)
        del scan_results

        for label in parsed:
            parsed[label].sort(key=lambda x: x.timestamp)
            logger.info(f"  {label}: {len(parsed[label]):,} entries")

        logger.info("=== Stage 2/3: Correlating entries ===")
        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()
        logger.info(f"  SDK→Worker: {len(correlated.sdk_worker_map):,}, "
                     f"Worker→URMA: {len(correlated.worker_urma_map):,}")

        sdk_entries = parsed.get("SDK access parse", [])
        worker_entries = parsed.get("Worker access parse", [])

        logger.info("=== Stage 3/3: Building parse results ===")
        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir)
        results = builder.build()

        del parsed, correlated, builder
        logger.info("Released parsed & correlated intermediate data")

        total = len(results)
        anomalous_count = sum(1 for r in results if r.is_anomalous)
        logger.info(f"Parse complete: {total:,} results, {anomalous_count:,} anomalous")

        return results

    # 异常事件检测
    @staticmethod
    async def detect_exception(
        list_log_parse_results: list[LogParseResultModel],
    ) -> list[AnomalousEventModel]:
        """滑动窗口P99两步法检测异常事件

        Step1: 滑动窗口计算P99，找出P99超过阈值的异常区间
        Step1.5: 区间裁剪——从合并区间两端收缩，剔除无异常条目的边缘
        Step1.6: 计算区间异常密度——判断是局部突刺还是整体劣化
        Step2: 密度低则只标记超阈值条目，密度高则整个区间标记为异常
        """
        cfg = Config().get_config().ds_log_analyzer
        window_size = cfg.sliding_window_size
        window_step = cfg.sliding_window_step
        density_threshold = cfg.zone_anomaly_density_threshold
        half_w = window_size // 2
        n = len(list_log_parse_results)

        thresholds = [
            ("total_latency", cfg.total_p99_threshold_ms),
            ("c2w_latency", cfg.c2w_p99_threshold_ms),
            ("w2w_urma_latency", cfg.w2w_p99_threshold_ms),
            ("urma_link_latency", cfg.urma_link_p99_threshold_ms),
            ("worker_query_meta_latency", cfg.query_meta_p99_threshold_ms),
        ]

        # 预提取各指标值数组，避免窗口内反复getattr
        field_arrays: dict[str, list[float | None]] = {}
        for field_name, _ in thresholds:
            field_arrays[field_name] = [getattr(r, field_name, None) for r in list_log_parse_results]

        # Step1: 滑动窗口P99检测，找出异常区间
        degraded_windows: list[tuple[int, int, str, float, float]] = []
        for center in range(0, n, window_step):
            start = max(0, center - half_w)
            end = min(n - 1, center + half_w)
            for field_name, threshold_ms in thresholds:
                values = [v for v in field_arrays[field_name][start:end + 1] if v is not None]
                if not values:
                    continue
                p99 = stats(values)["p99"]
                if p99 is not None and p99 > threshold_ms:
                    degraded_windows.append((start, end, field_name, threshold_ms, p99))

        # 合并相邻异常区间（按start排序，重叠/相邻则合并）
        degraded_windows.sort(key=lambda x: (x[0], x[1]))
        merged_zones: list[tuple[int, int, dict[str, tuple[float, float]]]] = []
        for start, end, field_name, threshold_ms, p99 in degraded_windows:
            if merged_zones and start <= merged_zones[-1][1] + 1:
                prev_start, prev_end, prev_fields = merged_zones[-1]
                new_end = max(prev_end, end)
                prev_fields[field_name] = (threshold_ms, p99)
                merged_zones[-1] = (prev_start, new_end, prev_fields)
            else:
                merged_zones.append((start, end, {field_name: (threshold_ms, p99)}))

        # Step1.5: 区间裁剪——从两端向内扫描，收缩到第一条超过任意阈值的条目
        trimmed_zones: list[tuple[int, int, dict[str, tuple[float, float]]]] = []
        for zone_start, zone_end, zone_fields in merged_zones:
            clip_start = zone_start
            for i in range(zone_start, zone_end + 1):
                if any(
                    field_arrays[fn][i] is not None and field_arrays[fn][i] > tm
                    for fn, tm in thresholds
                ):
                    clip_start = i
                    break
            else:
                continue

            clip_end = zone_end
            for i in range(zone_end, clip_start - 1, -1):
                if any(
                    field_arrays[fn][i] is not None and field_arrays[fn][i] > tm
                    for fn, tm in thresholds
                ):
                    clip_end = i
                    break

            trimmed_zones.append((clip_start, clip_end, zone_fields))

        # Step1.6: 计算区间异常密度
        zone_info: list[tuple[int, int, dict, bool]] = []
        for zone_start, zone_end, zone_fields in trimmed_zones:
            zone_len = zone_end - zone_start + 1
            exceeded = 0
            for i in range(zone_start, zone_end + 1):
                if any(
                    field_arrays[fn][i] is not None and field_arrays[fn][i] > tm
                    for fn, tm in thresholds
                ):
                    exceeded += 1
            density = exceeded / zone_len if zone_len > 0 else 0.0
            is_bulk = density >= density_threshold
            zone_info.append((zone_start, zone_end, zone_fields, is_bulk))

        # Step2: 密度低则只标记超阈值条目，密度高则整个区间标记
        events: list[AnomalousEventModel] = []
        anomalous_count = 0
        bulk_zone_count = 0
        trimmed_cover = 0

        for zone_start, zone_end, zone_fields, is_bulk in zone_info:
            zone_len = zone_end - zone_start + 1
            trimmed_cover += zone_len
            if is_bulk:
                bulk_zone_count += 1

            for idx in range(zone_start, zone_end + 1):
                r = list_log_parse_results[idx]
                reasons: list[str] = []

                if r.is_anomalous and r.anomaly_reason:
                    reasons.append(r.anomaly_reason)

                if r.c2w_latency is not None and r.c2w_latency < 0:
                    reasons.append("Client2WorkerTime(us) < 0")

                if r.c2w_urma_latency is not None:
                    reasons.append(f"c2w_urma_latency={r.c2w_urma_latency:.3f}ms (remote URMA path)")

                for field_name, threshold_ms in thresholds:
                    value = field_arrays[field_name][idx]
                    if value is not None and value > threshold_ms:
                        reasons.append(f"{field_name}={value:.3f}ms > threshold {threshold_ms}ms")

                if not reasons and is_bulk:
                    reasons.append("in bulk degraded zone (density>threshold)")

                if not reasons:
                    continue

                anomalous_count += 1
                log_id = r.log_id or ""

                events.append(AnomalousEventModel(
                    log_id=log_id,
                    aggregated_event_id="",
                    start_log_parse_offset=idx,
                    end_log_parse_offset=idx,
                    anomaly_reason="; ".join(reasons),
                ))

        raw_zone_cover = sum(end - start + 1 for start, end, _ in merged_zones)
        logger.info(
            f"Detect exception: {anomalous_count:,} anomalous entries out of "
            f"{n:,} results | raw zones: {len(merged_zones)} covering {raw_zone_cover:,}, "
            f"trimmed zones: {len(trimmed_zones)} covering {trimmed_cover:,}, "
            f"bulk degraded zones: {bulk_zone_count}"
        )

        return events

    # 异常事件匹配故障
    @staticmethod
    async def match_fault(
        anomalous_events: list[AnomalousEventModel],
    ) -> list[AnomalousEventChainModel]:
        """异常事件匹配故障"""
        pass

    # 异常事件成因分析
    @staticmethod
    async def root_cause_analysis(
        anomalous_event_chains: list[AnomalousEventChainModel],
    ) -> list[AnomalousEventChainModel]:
        """异常事件成因分析"""
        pass

    # 基于src ip和dst ip的生成聚合结果
    @staticmethod
    async def generate_aggregate_result(
        list_log_parse_results: list[LogParseResultModel],
    ) -> list[SrcDstAggregatedEventModel]:
        """按 src_ip/dst_ip 聚合统计"""
        latency_fields = [
            ("total_latency", "total_latency"),
            ("query_meta_latency", "worker_query_meta_latency"),
            ("urma_total_latency", "urma_total_latency"),
            ("urma_link_latency", "urma_link_latency"),
            ("c2w_urma_latency", "c2w_urma_latency"),
            ("w2w_urma_latency", "w2w_urma_latency"),
        ]

        groups: dict[tuple[str, str], list[LogParseResultModel]] = defaultdict[tuple[str, str], list[LogParseResultModel]](list)
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            if not src and not dst:
                continue
            groups[(src, dst)].append(r)

        results: list[SrcDstAggregatedEventModel] = []
        for (src, dst), items in groups.items():
            log_id = items[0].log_id or ""
            total_cnt = len(items)
            anomaly_cnt = sum(1 for r in items if r.is_anomalous)
            anomaly_log_cnt = sum(1 for r in items if r.anomalous_event_id)

            agg: dict[str, float | None] = {}
            for prefix, field_name in latency_fields:
                values = [getattr(r, field_name) for r in items]
                values = [v for v in values if v is not None]
                st = stats(values)
                agg[f"ave_{prefix}"] = st["ave"]
                agg[f"min_{prefix}"] = st["min"]
                agg[f"max_{prefix}"] = st["max"]
                agg[f"p95_{prefix}"] = st["p95"]
                agg[f"p99_{prefix}"] = st["p99"]

            results.append(SrcDstAggregatedEventModel(
                src_ip=src,
                dst_ip=dst,
                log_id=log_id,
                log_parse_result_cnt=total_cnt,
                anomaly_log_parse_result_cnt=anomaly_log_cnt,
                anomaly_cnt=anomaly_cnt,
                **agg,
            ))

        logger.info(f"Aggregate result: {len(results):,} endpoints from "
                     f"{len(list_log_parse_results):,} results")

        return results

    # 存库
    @staticmethod
    async def store_result(
        list_log_parse_results: list[LogParseResultModel],
        anomalous_events: list[AnomalousEventModel],
        anomalous_event_chains: list[AnomalousEventChainModel],
        src_dst_aggregated_events: list[SrcDstAggregatedEventModel],
    ) -> bool:
        """存库

        按引用顺序依次写入：log_parse_results → aggregated_events → anomalous_events → event_chains
        """
        success = True

        if list_log_parse_results:
            try:
                await LogParseResultManager.add_log_parse_results(list_log_parse_results)
                logger.info(f"Stored {len(list_log_parse_results):,} log parse results")
            except Exception as e:
                logger.error(f"Failed to store log parse results: {e}")
                success = False

        if src_dst_aggregated_events:
            try:
                await SrcDstAggregatedEventManager.add_aggregated_events(src_dst_aggregated_events)
                logger.info(f"Stored {len(src_dst_aggregated_events):,} aggregated events")
            except Exception as e:
                logger.error(f"Failed to store aggregated events: {e}")
                success = False

        if anomalous_events:
            try:
                await AnomalousEventManager.add_anomalous_events(anomalous_events)
                logger.info(f"Stored {len(anomalous_events):,} anomalous events")
            except Exception as e:
                logger.error(f"Failed to store anomalous events: {e}")
                success = False

        if anomalous_event_chains:
            try:
                await AnomalousEventChainManager.add_event_chains(anomalous_event_chains)
                logger.info(f"Stored {len(anomalous_event_chains):,} event chains")
            except Exception as e:
                logger.error(f"Failed to store event chains: {e}")
                success = False

        return success

    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务"""
        try:
            task = await TaskManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"任务 {task_id} 不存在")
                return False
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            # TODO: 解析日志存库
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            return True
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行失败: {e}")
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await TaskReportManager.update_task_report_existed_status_by_task_id(
                task_id, existed_status=0
            )
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        return task_id
