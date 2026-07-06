"""KVCacheLogParseWorker cProfile performance test.

Usage:
    python test_kv_cache_log_parse_worker_profile.py parse <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py detect <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py aggregate <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py pipeline <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py run <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py compare <log_id|log_dir>

Examples:
    python test_kv_cache_log_parse_worker_profile.py parse /data/logs/sample
    python test_kv_cache_log_parse_worker_profile.py pipeline <log_id> \
        --output /data/profiles/pipeline.prof --limit 50
    python test_kv_cache_log_parse_worker_profile.py run /data/logs/sample \
        --output /data/profiles/run.prof --limit 50
    python test_kv_cache_log_parse_worker_profile.py compare /data/logs/sample \
        --comparison-modes single,2,auto --comparison-repeats 3 \
        --comparison-json /data/profiles/scanner-comparison.json \
        --comparison-markdown /data/profiles/scanner-comparison.md

The detect and aggregate commands prepare parse results before enabling cProfile,
so their reports contain only the requested stage. The pipeline command profiles
parse, anomaly detection, and aggregation together. It does not write to the
database. The run command profiles the same complete workflow as the run command
in test_kv_cache_log_parse_worker.py, including database storage. When run receives
a local path, it automatically registers that path as a log file so all stored
results have a valid log ID. The compare command does not use cProfile. It rotates
scanner modes between rounds, checks result-count equality, and compares wall-clock
medians. The all command remains an alias of pipeline.
"""

import argparse
import asyncio
import cProfile
from datetime import datetime
import gc
import json
import logging
import multiprocessing
import os
from pathlib import Path
import platform
import pstats
import shutil
import statistics
import sys
import tempfile
import time
from typing import Awaitable, Callable


_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

ProfileOperation = Callable[[], Awaitable[dict[str, object]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "parse",
            "detect",
            "aggregate",
            "pipeline",
            "run",
            "all",
            "compare",
        ),
        help=(
            "Stage to profile; run stores results, all is an alias of pipeline, "
            "compare benchmarks scanner process modes without cProfile"
        ),
    )
    parser.add_argument("target", help="Database log ID or local log directory")
    parser.add_argument(
        "--output",
        type=Path,
        help="Binary .prof output path; defaults to /tmp/witty-ub-cprofile",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Text report path; defaults to the .prof path with a .txt suffix",
    )
    parser.add_argument(
        "--sort",
        choices=("cumulative", "tottime", "calls", "name"),
        default="cumulative",
        help="Console report sort order",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Number of functions printed in each report section",
    )
    parser.add_argument(
        "--comparison-modes",
        default="single,2,auto",
        help=(
            "Comma-separated scanner modes for compare: single, auto, or a "
            "positive integer process cap"
        ),
    )
    parser.add_argument(
        "--comparison-repeats",
        type=int,
        default=3,
        help="Measured rounds per scanner mode; use 5 or more for strict evidence",
    )
    parser.add_argument(
        "--expected-results",
        type=int,
        help="Optional required parse-result count for every comparison run",
    )
    parser.add_argument(
        "--decision-threshold-percent",
        type=float,
        default=15.0,
        help="Minimum median improvement required to recommend a mode change",
    )
    parser.add_argument(
        "--comparison-json",
        type=Path,
        help="Machine-readable comparison output path",
    )
    parser.add_argument(
        "--comparison-markdown",
        type=Path,
        help="Mentor-facing comparison output path",
    )
    return parser.parse_args()


def default_profile_path(command: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    profile_dir = Path(tempfile.gettempdir()) / "witty-ub-cprofile"
    return profile_dir / f"{command}-{timestamp}-{os.getpid()}.prof"


async def parse_target(target: str):
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    target_path = Path(target).expanduser()
    if target_path.exists():
        return await KVCacheLogParseWorker.parse_log(log_dir=str(target_path.resolve()))
    return await KVCacheLogParseWorker.parse_log(log_id=target)


async def prepare_run_target(target: str) -> tuple[str, bool]:
    """Return a database log ID, registering a local path when necessary."""
    target_path = Path(target).expanduser()
    if not target_path.exists():
        if target_path.is_absolute() or len(target_path.parts) > 1:
            raise FileNotFoundError(f"Local log path does not exist: {target_path}")
        return target, False

    from latency.database.engine import AsyncSQLiteSingleton
    from latency.database.managers.log_file import LogFileManager
    from latency.schemas.log import LogFileModel

    resolved_path = target_path.resolve()
    database = AsyncSQLiteSingleton()
    if not await database.init_database():
        raise RuntimeError("Failed to initialize the profile database")

    log_file = LogFileModel(
        name=resolved_path.name,
        file_path=str(resolved_path),
    )
    if not await LogFileManager.add_log_file(log_file):
        raise RuntimeError(f"Failed to register local log path: {resolved_path}")

    logger.info(
        "Registered local log path for run profile: log_id=%s, path=%s",
        log_file.id,
        resolved_path,
    )
    return log_file.id, True


def write_text_report(
    profile_path: Path,
    report_path: Path,
    command: str,
    target: str,
    elapsed: float,
    summary: dict[str, object],
    limit: int,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as stream:
        stream.write("KVCacheLogParseWorker cProfile report\n")
        stream.write(f"command: {command}\n")
        stream.write(f"target: {target}\n")
        stream.write(f"elapsed_seconds: {elapsed:.6f}\n")
        stream.write(f"summary: {summary}\n\n")

        stats = pstats.Stats(str(profile_path), stream=stream).strip_dirs()
        stream.write("Top functions by cumulative time\n")
        stats.sort_stats("cumulative").print_stats(limit)
        stream.write("\nTop functions by internal time\n")
        stats.sort_stats("tottime").print_stats(limit)


def combine_profile_stats(
    parent_profile_path: Path,
    worker_profile_dir: Path,
    profile_path: Path,
) -> int:
    worker_profiles = sorted(worker_profile_dir.glob("*.prof"))
    stats = pstats.Stats(str(parent_profile_path))
    for worker_profile in worker_profiles:
        stats.add(str(worker_profile))
    stats.dump_stats(str(profile_path))
    return len(worker_profiles)


async def profile_operation(
    operation: ProfileOperation,
    command: str,
    target: str,
    profile_path: Path,
    report_path: Path,
    sort_by: str,
    limit: int,
) -> dict[str, object]:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    parent_profile_path = profile_path.with_name(
        f"{profile_path.stem}-parent{profile_path.suffix}"
    )
    worker_profile_dir = profile_path.with_name(
        f"{profile_path.stem}-workers"
    )
    shutil.rmtree(worker_profile_dir, ignore_errors=True)
    worker_profile_dir.mkdir(parents=True, exist_ok=True)

    previous_worker_profile_dir = os.environ.get("WITTY_UB_CPROFILE_DIR")
    os.environ["WITTY_UB_CPROFILE_DIR"] = str(worker_profile_dir)
    profiler = cProfile.Profile()
    started = time.perf_counter()

    profiler.enable()
    try:
        summary = await operation()
    finally:
        profiler.disable()
        profiler.dump_stats(str(parent_profile_path))
        if previous_worker_profile_dir is None:
            os.environ.pop("WITTY_UB_CPROFILE_DIR", None)
        else:
            os.environ["WITTY_UB_CPROFILE_DIR"] = previous_worker_profile_dir

    elapsed = time.perf_counter() - started
    worker_profile_count = combine_profile_stats(
        parent_profile_path=parent_profile_path,
        worker_profile_dir=worker_profile_dir,
        profile_path=profile_path,
    )
    summary = {
        **summary,
        "profile_scope": "parent_and_process_pool_workers",
        "worker_profile_count": worker_profile_count,
    }
    write_text_report(
        profile_path=profile_path,
        report_path=report_path,
        command=command,
        target=target,
        elapsed=elapsed,
        summary=summary,
        limit=limit,
    )

    logger.info("Profile complete in %.3fs: %s", elapsed, summary)
    logger.info(
        "Combined binary profile: %s (parent + %d worker profiles)",
        profile_path,
        worker_profile_count,
    )
    logger.info("Text report: %s", report_path)
    logger.info(
        "cProfile adds runtime overhead; use the report to locate investigation "
        "targets, not as production latency evidence"
    )

    pstats.Stats(str(profile_path)).strip_dirs().sort_stats(sort_by).print_stats(limit)
    parent_profile_path.unlink(missing_ok=True)
    shutil.rmtree(worker_profile_dir, ignore_errors=True)
    return summary


async def run_profile(args: argparse.Namespace) -> dict[str, object]:
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    command = "pipeline" if args.command == "all" else args.command
    profile_path = (args.output or default_profile_path(command)).expanduser().resolve()
    report_path = (
        args.report.expanduser().resolve()
        if args.report
        else profile_path.with_suffix(".txt")
    )

    if args.limit <= 0:
        raise ValueError("--limit must be greater than zero")

    if command == "parse":
        async def operation() -> dict[str, object]:
            results = await parse_target(args.target)
            return {"parse_results": len(results)}

    elif command == "detect":
        logger.info("Preparing parse results outside cProfile")
        results = await parse_target(args.target)

        async def operation() -> dict[str, object]:
            events = await KVCacheLogParseWorker.detect_exception(results)
            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
            }

    elif command == "aggregate":
        logger.info("Preparing parse and detection results outside cProfile")
        results = await parse_target(args.target)
        events = await KVCacheLogParseWorker.detect_exception(results)

        async def operation() -> dict[str, object]:
            aggregates, _ = await KVCacheLogParseWorker.generate_aggregate_result(results)
            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
            }

    elif command == "pipeline":
        async def operation() -> dict[str, object]:
            parse_started = time.perf_counter()
            results = await parse_target(args.target)
            parse_elapsed = time.perf_counter() - parse_started

            detect_started = time.perf_counter()
            events = await KVCacheLogParseWorker.detect_exception(results)
            detect_elapsed = time.perf_counter() - detect_started

            aggregate_started = time.perf_counter()
            aggregates, _ = await KVCacheLogParseWorker.generate_aggregate_result(results)
            aggregate_elapsed = time.perf_counter() - aggregate_started

            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
                "parse_seconds": round(parse_elapsed, 6),
                "detect_seconds": round(detect_elapsed, 6),
                "aggregate_seconds": round(aggregate_elapsed, 6),
            }

    elif command == "run":
        log_id, registered_local_path = await prepare_run_target(args.target)

        async def operation() -> dict[str, object]:
            parse_started = time.perf_counter()
            results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
            parse_elapsed = time.perf_counter() - parse_started

            detect_started = time.perf_counter()
            events = await KVCacheLogParseWorker.detect_exception(results)
            detect_elapsed = time.perf_counter() - detect_started

            aggregate_started = time.perf_counter()
            aggregates, src_dst_map = (
                await KVCacheLogParseWorker.generate_aggregate_result(results)
            )
            aggregate_elapsed = time.perf_counter() - aggregate_started

            link_started = time.perf_counter()
            for event in events:
                idx = event.start_log_parse_offset
                if 0 <= idx < len(results):
                    result = results[idx]
                    event.aggregated_event_id = src_dst_map.get(
                        (result.src_ip, result.dst_ip), ""
                    )
            link_elapsed = time.perf_counter() - link_started

            store_started = time.perf_counter()
            stored = await KVCacheLogParseWorker.store_result(
                list_log_parse_results=results,
                anomalous_events=events,
                anomalous_event_chains=[],
                src_dst_aggregated_events=aggregates,
            )
            store_elapsed = time.perf_counter() - store_started

            return {
                "log_id": log_id,
                "registered_local_path": registered_local_path,
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
                "stored": stored,
                "parse_seconds": round(parse_elapsed, 6),
                "detect_seconds": round(detect_elapsed, 6),
                "aggregate_seconds": round(aggregate_elapsed, 6),
                "link_seconds": round(link_elapsed, 6),
                "store_seconds": round(store_elapsed, 6),
            }

    return await profile_operation(
        operation=operation,
        command=command,
        target=args.target,
        profile_path=profile_path,
        report_path=report_path,
        sort_by=args.sort,
        limit=args.limit,
    )


def parse_comparison_modes(raw_modes: str) -> list[str]:
    modes: list[str] = []
    for raw_mode in raw_modes.split(","):
        mode = raw_mode.strip().lower()
        if not mode:
            continue
        if mode == "1":
            mode = "single"
        if mode not in {"single", "auto"}:
            try:
                process_count = int(mode)
            except ValueError as exc:
                raise ValueError(
                    f"invalid comparison mode {raw_mode!r}; "
                    "use single, auto, or a positive integer"
                ) from exc
            if process_count < 2:
                raise ValueError(
                    f"invalid comparison process count: {process_count}"
                )
            mode = str(process_count)
        if mode not in modes:
            modes.append(mode)
    if "auto" not in modes:
        raise ValueError("--comparison-modes must include auto as the baseline")
    if len(modes) < 2:
        raise ValueError("--comparison-modes must include at least two modes")
    return modes


def comparison_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    output_dir = Path(tempfile.gettempdir()) / "witty-ub-scanner-comparison"
    json_path = (
        args.comparison_json.expanduser().resolve()
        if args.comparison_json
        else output_dir / "scanner-comparison.json"
    )
    markdown_path = (
        args.comparison_markdown.expanduser().resolve()
        if args.comparison_markdown
        else output_dir / "scanner-comparison.md"
    )
    return json_path, markdown_path


async def run_parse_with_scanner_mode(
    target: str,
    mode: str,
) -> tuple[int, float]:
    from latency.ENUM.task import TaskSplitStrategy
    from latency.parse.parallel_scanner import ParallelFileScanner
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    original_factory = KVCacheLogParseWorker._new_parallel_scanner
    if mode == "single":
        max_processes = 1
        use_multiprocessing = False
    elif mode == "auto":
        max_processes = None
        use_multiprocessing = True
    else:
        max_processes = int(mode)
        use_multiprocessing = True

    if mode != "auto":

        def comparison_factory() -> ParallelFileScanner:
            return ParallelFileScanner(
                max_processes=max_processes,
                split_strategy=TaskSplitStrategy.BY_FILE_SIZE,
                use_multiprocessing=use_multiprocessing,
                decompress=False,
            )

        KVCacheLogParseWorker._new_parallel_scanner = staticmethod(
            comparison_factory
        )

    try:
        gc.collect()
        await asyncio.sleep(0)
        started = time.perf_counter()
        results = await parse_target(target)
        elapsed = time.perf_counter() - started
        result_count = len(results)
        del results
        return result_count, elapsed
    finally:
        KVCacheLogParseWorker._new_parallel_scanner = staticmethod(
            original_factory
        )


def summarize_mode_runs(runs: list[dict[str, object]]) -> dict[str, object]:
    successful = [run for run in runs if run["status"] == "passed"]
    durations = [float(run["elapsed_seconds"]) for run in successful]
    counts = sorted({int(run["parse_results"]) for run in successful})
    if not durations:
        return {
            "status": "failed",
            "successful_runs": 0,
            "parse_result_counts": counts,
        }
    return {
        "status": "passed" if len(successful) == len(runs) else "failed",
        "successful_runs": len(successful),
        "parse_result_counts": counts,
        "median_seconds": round(statistics.median(durations), 6),
        "mean_seconds": round(statistics.fmean(durations), 6),
        "minimum_seconds": round(min(durations), 6),
        "maximum_seconds": round(max(durations), 6),
        "population_stdev_seconds": round(
            statistics.pstdev(durations),
            6,
        ),
    }


def build_comparison_decision(
    mode_summaries: dict[str, dict[str, object]],
    repeats: int,
    threshold_percent: float,
) -> dict[str, object]:
    auto_summary = mode_summaries["auto"]
    if auto_summary.get("status") != "passed":
        return {
            "status": "invalid",
            "selected_mode": None,
            "improvement_vs_auto_percent": None,
            "plain_conclusion": "自动进程数基线没有完整跑通，当前不能比较。",
            "code_change": None,
        }

    complete_modes = {
        mode: summary
        for mode, summary in mode_summaries.items()
        if summary.get("status") == "passed"
    }
    selected_mode, selected_summary = min(
        complete_modes.items(),
        key=lambda item: float(item[1]["median_seconds"]),
    )
    auto_median = float(auto_summary["median_seconds"])
    selected_median = float(selected_summary["median_seconds"])
    improvement = (
        (auto_median - selected_median) * 100.0 / auto_median
        if auto_median
        else 0.0
    )
    improvement = round(improvement, 3)
    actionable = (
        selected_mode != "auto" and improvement >= threshold_percent
    )
    evidence_level = "strict" if repeats >= 5 else "quick"

    if actionable and selected_mode == "single":
        code_change = {
            "file": "src/plugins/latency/parse/parallel_scanner/scanner.py",
            "symbol": "ParallelFileScanner.scan_all",
            "change": (
                "在 file_parser_map 和总字节数已知后增加可配置的小任务阈值；"
                "低于阈值时跳过 ProcessPoolExecutor，走现有 asyncio 单进程路径。"
            ),
            "reason": (
                "同一输入下单进程中位耗时达到判定阈值，说明当前数据规模"
                "不足以摊薄多进程调度成本。"
            ),
        }
        plain_conclusion = (
            f"单进程最快，比自动进程数快 {improvement:.1f}%。"
            "建议先实现“小任务走单进程”的可配置阈值。"
        )
    elif actionable:
        code_change = {
            "file": (
                "src/plugins/latency/task/worker/"
                "kv_cache_log_parse_worker.py"
            ),
            "symbol": "KVCacheLogParseWorker._new_parallel_scanner",
            "change": (
                f"把解析 worker 的最大进程数改为可配置项，并先以 "
                f"{selected_mode} 个进程作为该日志规模的候选上限；"
                "不要把实验值直接硬编码为全局常量。"
            ),
            "reason": (
                f"同一输入下 {selected_mode} 个进程的中位耗时达到判定阈值，"
                "继续增加进程没有带来收益。"
            ),
        }
        plain_conclusion = (
            f"{selected_mode} 个进程最快，比自动进程数快 "
            f"{improvement:.1f}%。建议把进程上限做成配置项后复验。"
        )
    else:
        code_change = {
            "file": None,
            "symbol": None,
            "change": (
                "暂不修改进程策略；保留当前实现，继续分析 worker 文件读取"
                "和逐行解析的自身耗时。"
            ),
            "reason": (
                f"最快模式相对自动基线只改善 {improvement:.1f}%，"
                f"未达到 {threshold_percent:.1f}% 的修改阈值。"
            ),
        }
        plain_conclusion = (
            f"进程数调整的最大收益为 {improvement:.1f}%，没有达到 "
            f"{threshold_percent:.1f}% 阈值；现在不建议改进程策略。"
        )

    return {
        "status": "actionable_candidate" if actionable else "no_change",
        "evidence_level": evidence_level,
        "selected_mode": selected_mode,
        "selected_median_seconds": selected_median,
        "auto_median_seconds": auto_median,
        "improvement_vs_auto_percent": improvement,
        "threshold_percent": threshold_percent,
        "plain_conclusion": plain_conclusion,
        "code_change": code_change,
        "confirmation": (
            "五轮及以上可作为当前日志集和当前运行环境的严格进程策略证据；"
            "生产修改仍需在 Jenkins 目标环境复验。"
            if repeats >= 5
            else "当前是三轮快速判断；合入生产修改前在 Jenkins 目标环境用五轮复验。"
        ),
    }


def render_comparison_markdown(report: dict[str, object]) -> str:
    decision = report["decision"]
    lines = [
        "# Witty-UB 扫描进程数对照结果",
        "",
        "## 一句话结论",
        "",
        f"**{decision['plain_conclusion']}**",
        "",
        f"- 日志目标：`{report['target']}`",
        f"- 每种模式运行：`{report['repeats']}` 次",
        f"- 结果一致性：`{report['result_consistency']}`",
        f"- 证据级别：`{decision.get('evidence_level', 'invalid')}`",
        f"- 运行系统：`{report['environment']['platform']}`",
        f"- Python：`{report['environment']['python_version']}`",
        f"- 多进程启动方式：`{report['environment']['multiprocessing_start_method']}`",
        f"- 可见 CPU 数：`{report['environment']['cpu_count']}`",
        "",
        "## 实测结果",
        "",
        "| 模式 | 中位耗时(s) | 最快(s) | 最慢(s) | 解析结果数 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "single": "单进程",
        "auto": "当前自动进程数",
    }
    for mode in report["modes"]:
        summary = report["mode_summaries"][mode]
        label = labels.get(mode, f"{mode} 个进程")
        if summary.get("status") != "passed":
            lines.append(f"| {label} | 失败 | - | - | - |")
            continue
        counts = ",".join(str(value) for value in summary["parse_result_counts"])
        lines.append(
            f"| {label} | {summary['median_seconds']:.6f} | "
            f"{summary['minimum_seconds']:.6f} | "
            f"{summary['maximum_seconds']:.6f} | {counts} |"
        )

    code_change = decision.get("code_change")
    lines.extend(["", "## 具体怎么改", ""])
    if code_change:
        if code_change.get("file"):
            lines.append(f"- 文件：`{code_change['file']}`")
            lines.append(f"- 函数：`{code_change['symbol']}`")
        lines.append(f"- 修改：{code_change['change']}")
        lines.append(f"- 原因：{code_change['reason']}")
    else:
        lines.append("- 本次基线无效，先修复实验环境，不改产品源码。")

    lines.extend(
        [
            "",
            "## 怎么判断可以合入",
            "",
            f"- {decision.get('confirmation', '先取得完整自动基线。')}",
            "- 所有模式的解析结果数量必须完全一致。",
            "- 固定同一日志目录、源码版本、CPU/内存限制和运行轮数。",
            "- 这份对照只判断进程策略，不替代完整调用栈和源码诊断。",
            "",
        ]
    )
    return "\n".join(lines)


async def run_comparison(args: argparse.Namespace) -> dict[str, object]:
    modes = parse_comparison_modes(args.comparison_modes)
    if args.comparison_repeats <= 0:
        raise ValueError("--comparison-repeats must be greater than zero")
    if args.decision_threshold_percent <= 0:
        raise ValueError("--decision-threshold-percent must be greater than zero")

    runs_by_mode: dict[str, list[dict[str, object]]] = {
        mode: [] for mode in modes
    }
    all_runs: list[dict[str, object]] = []
    for round_index in range(args.comparison_repeats):
        offset = round_index % len(modes)
        round_modes = modes[offset:] + modes[:offset]
        for position, mode in enumerate(round_modes, start=1):
            logger.info(
                "Comparison round %d/%d, position %d/%d, mode=%s",
                round_index + 1,
                args.comparison_repeats,
                position,
                len(round_modes),
                mode,
            )
            run: dict[str, object] = {
                "round": round_index + 1,
                "position": position,
                "mode": mode,
            }
            try:
                result_count, elapsed = await run_parse_with_scanner_mode(
                    args.target,
                    mode,
                )
                run.update(
                    {
                        "status": "passed",
                        "elapsed_seconds": round(elapsed, 6),
                        "parse_results": result_count,
                    }
                )
            except Exception as exc:
                logger.exception("Scanner comparison failed for mode=%s", mode)
                run.update(
                    {
                        "status": "failed",
                        "error": str(exc),
                    }
                )
            runs_by_mode[mode].append(run)
            all_runs.append(run)

    mode_summaries = {
        mode: summarize_mode_runs(runs_by_mode[mode]) for mode in modes
    }
    successful_counts = {
        int(run["parse_results"])
        for run in all_runs
        if run["status"] == "passed"
    }
    all_runs_passed = all(run["status"] == "passed" for run in all_runs)
    expected_matches = (
        args.expected_results is None
        or successful_counts == {args.expected_results}
    )
    result_consistency = (
        "passed"
        if all_runs_passed
        and len(successful_counts) == 1
        and expected_matches
        else "failed"
    )
    decision = build_comparison_decision(
        mode_summaries,
        args.comparison_repeats,
        args.decision_threshold_percent,
    )
    if result_consistency != "passed":
        decision = {
            "status": "invalid",
            "selected_mode": None,
            "improvement_vs_auto_percent": None,
            "plain_conclusion": (
                "不同模式的解析结果不一致或存在失败，性能数字无效，"
                "当前不能修改产品代码。"
            ),
            "code_change": None,
        }

    report: dict[str, object] = {
        "schema_version": "1.0",
        "artifact_type": "witty_ub_scanner_mode_comparison",
        "status": "passed" if result_consistency == "passed" else "failed",
        "target": args.target,
        "modes": modes,
        "repeats": args.comparison_repeats,
        "run_order_strategy": "rotating_mode_order_per_round",
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "multiprocessing_start_method": multiprocessing.get_start_method(),
            "cpu_count": os.cpu_count(),
        },
        "expected_results": args.expected_results,
        "observed_result_counts": sorted(successful_counts),
        "result_consistency": result_consistency,
        "runs": all_runs,
        "mode_summaries": mode_summaries,
        "decision": decision,
        "limitations": [
            "Wall-clock results apply to this source revision, input, and resource limit.",
            "Three repeats are a quick decision; use five or more before changing production defaults.",
            "The comparison isolates scanner process mode, not every cause in the call stack.",
        ],
    }
    json_path, markdown_path = comparison_output_paths(args)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_comparison_markdown(report),
        encoding="utf-8",
    )
    logger.info("Comparison JSON: %s", json_path)
    logger.info("Comparison Markdown: %s", markdown_path)
    print(
        json.dumps(
            {
                "status": report["status"],
                "result_consistency": result_consistency,
                "decision": decision["status"],
                "selected_mode": decision.get("selected_mode"),
                "json_report": str(json_path),
                "markdown_report": str(markdown_path),
            },
            ensure_ascii=False,
        )
    )
    if report["status"] != "passed":
        raise RuntimeError("scanner comparison failed integrity checks")
    return report


def main() -> None:
    args = parse_args()
    if args.command == "compare":
        asyncio.run(run_comparison(args))
    else:
        asyncio.run(run_profile(args))


if __name__ == "__main__":
    main()
