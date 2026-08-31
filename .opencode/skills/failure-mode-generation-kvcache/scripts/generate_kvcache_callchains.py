#!/usr/bin/env python3

"""Generate a full conservative C++ call graph for src/datasystem.

The graph is NOT rooted at public APIs: every function definition found by the
Clang Static Analyzer is a first-class node, including RPC handlers, background
thread entries and asynchronous callbacks that are unreachable from
``datasystem::KVClient``.  Functions without callers are reported as top-level
entries; the consumer attaches the topmost failure nodes to access-log roots by
error code and hangs the remaining failure nodes under their upstream callers.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


SCHEMA_VERSION = 2
CACHE_SCHEMA_VERSION = 1
CACHE_DIRECTORY_NAME = ".witty-kvcache-callgraph-cache"
CACHE_MANIFEST_NAME = "manifest.json"
CACHE_MANIFEST_KIND = "witty-kvcache-callgraph-cache"
OUTPUT_FILE = Path("/tmp/kvcache_callchains.json")
SCAN_ROOT = Path("src/datasystem")
STATUS_HEADER = Path("include/datasystem/utils/status.h")
CLANG_COMMAND = "clang++"
MAX_JOBS = min(os.cpu_count() or 1, 8)
ANALYSIS_TIMEOUT = 300
TIMEOUT_RETRIES = 1
CPP_SUFFIXES = {".cc", ".cpp", ".cxx"}
FINGERPRINT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
}

# Clang's debug.DumpCallGraph records the statically selected virtual member.
# These project-specific bindings conservatively connect the interfaces used by
# ObjectClientImpl to the implementations instantiated by the KV client.
VIRTUAL_BINDINGS = {
    "datasystem::object_cache::IClientWorkerApi": (
        "datasystem::object_cache::ClientWorkerBaseApi",
        "datasystem::object_cache::ClientWorkerLocalApi",
        "datasystem::object_cache::ClientWorkerRemoteApi",
    ),
    "datasystem::client::IClientWorkerCommonApi": (
        "datasystem::client::ClientWorkerLocalCommonApi",
        "datasystem::client::ClientWorkerRemoteCommonApi",
        "datasystem::object_cache::ClientWorkerLocalApi",
        "datasystem::object_cache::ClientWorkerRemoteApi",
    ),
    "datasystem::object_cache::IExistRouting": (
        "datasystem::object_cache::(anonymous namespace)::RoutingExistAdapter",
    ),
    "datasystem::object_cache::IExistTransport": (
        "datasystem::object_cache::(anonymous namespace)::TransportLayerExistAdapter",
    ),
}

# Logging, metric and tracing helpers are terminal instrumentation, rather than
# business-call graph members. Keeping them out prevents nearly every function
# from reaching logger-internal diagnostic descendants.
EXCLUDED_PREFIXES = (
    "datasystem::AccessRecorder::",
    "datasystem::AccessRecorderManager::",
    "datasystem::ObjectAccessRecorder::",
    "datasystem::DeviceAccessRecorder::",
    "datasystem::RpcAccessRecorder::",
    "datasystem::LogHelper::",
    "datasystem::LogManager::",
    "datasystem::LogMessage::",
    "datasystem::LogMessageImpl::",
    "datasystem::LogSampler::",
    "datasystem::Logging::",
    "datasystem::OperationLogger::",
    "datasystem::PerfPoint::",
    "datasystem::Trace::",
    "datasystem::TraceGuard::",
    "datasystem::metrics::",
)

# The KV client reaches the real or mock URMA implementation through global
# ds_urma_* shims. Keep those call sites in the graph, but stop at the shim so
# mock-only dispatch helpers and external URMA implementation details do not
# pollute the KV-cache call graph.
TERMINAL_PREFIXES = (
    "ds_urma_",
)

DROP_ARGUMENTS = {
    "-c", "--compile", "-MD", "-MMD", "-MP", "-MG", "-M", "-MM",
    "-fpermissive",
}
DROP_ARGUMENTS_WITH_VALUE = {
    "-o", "-MF", "-MT", "-MQ", "-MJ", "--serialize-diagnostics",
}
COMPILER_LAUNCHERS = {"ccache", "sccache", "distcc", "icecc"}
CALL_GRAPH_PATTERN = re.compile(r"^\s*Function: (.*?) calls:(.*)$")
CALL_GRAPH_DUMP_PATTERN = re.compile(r"^\s*--- Call graph Dump ---\s*$", re.MULTILINE)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


@dataclass(frozen=True)
class CompileTask:
    source: Path
    directory: Path
    command: tuple[str, ...]


@dataclass
class AnalysisResult:
    source: Path
    function_calls: list[tuple[str, str]]
    error: str | None = None
    timed_out: bool = False
    duration_seconds: float = 0.0
    dependencies: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class CacheLookup:
    result: AnalysisResult | None
    previous_duration: float


class AnalysisCache:
    def __init__(self, root: Path, compiler_identity: str):
        self.root = root.expanduser().resolve()
        self.compiler_identity = compiler_identity
        self.entries = self.root / "entries"
        self.temporary = self.root / "tmp"

    def initialize(self, clear: bool) -> None:
        manifest = self.root / CACHE_MANIFEST_NAME
        if self.root.exists() and not self.root.is_dir():
            raise ValueError(f"缓存路径不是目录：{self.root}")
        if manifest.exists():
            data = self._read_json(manifest)
            if not isinstance(data, dict) or data.get("kind") != CACHE_MANIFEST_KIND:
                raise ValueError(f"缓存目录manifest无效，拒绝使用或清理：{manifest}")
        elif self.root.exists() and any(self.root.iterdir()):
            raise ValueError(
                f"缓存目录非空且不属于本脚本，拒绝使用或清理：{self.root}"
            )
        else:
            self.root.mkdir(parents=True, exist_ok=True)
            self._write_json_atomic(
                manifest,
                {
                    "kind": CACHE_MANIFEST_KIND,
                    "cache_schema_version": CACHE_SCHEMA_VERSION,
                },
            )

        if clear:
            for owned_path in (self.entries, self.temporary):
                if owned_path.exists():
                    shutil.rmtree(owned_path)
        self.entries.mkdir(parents=True, exist_ok=True)
        self.temporary.mkdir(parents=True, exist_ok=True)
        probe = self.temporary / f".write-test.{os.getpid()}.{time.time_ns()}"
        try:
            with probe.open("x", encoding="utf-8") as file:
                file.write("ok\n")
        finally:
            if probe.exists():
                probe.unlink()

    def lookup(self, task: CompileTask) -> CacheLookup:
        entry_path = self._entry_path(task)
        if not entry_path.is_file():
            return CacheLookup(None, 0.0)
        try:
            entry = self._read_json(entry_path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"警告：忽略损坏的分析缓存{entry_path}：{exc}", file=sys.stderr)
            return CacheLookup(None, 0.0)
        if not isinstance(entry, dict):
            return CacheLookup(None, 0.0)

        duration = entry.get("duration_seconds", 0.0)
        previous_duration = (
            float(duration) if isinstance(duration, (int, float)) else 0.0
        )
        if (
            entry.get("cache_schema_version") != CACHE_SCHEMA_VERSION
            or entry.get("command_digest") != self._command_digest(task)
            or not self._dependencies_unchanged(entry.get("dependencies"))
        ):
            return CacheLookup(None, previous_duration)

        raw_calls = entry.get("function_calls")
        if not isinstance(raw_calls, list):
            return CacheLookup(None, previous_duration)
        function_calls: list[tuple[str, str]] = []
        for raw_call in raw_calls:
            if (
                not isinstance(raw_call, list)
                or len(raw_call) != 2
                or not all(isinstance(item, str) for item in raw_call)
            ):
                return CacheLookup(None, previous_duration)
            function_calls.append((raw_call[0], raw_call[1]))
        return CacheLookup(
            AnalysisResult(
                source=task.source,
                function_calls=function_calls,
                duration_seconds=previous_duration,
            ),
            previous_duration,
        )

    def dependency_file(self, task: CompileTask) -> Path:
        task_id = self._task_id(task)
        return self.temporary / f"{task_id}.{os.getpid()}.d"

    def store(self, task: CompileTask, result: AnalysisResult) -> None:
        if result.error is not None or not result.dependencies:
            return
        dependencies = self._dependency_states(result.dependencies)
        if dependencies is None:
            return
        entry = {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "source": str(task.source),
            "command_digest": self._command_digest(task),
            "duration_seconds": result.duration_seconds,
            "dependencies": dependencies,
            "function_calls": result.function_calls,
        }
        entry_path = self._entry_path(task)
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json_atomic(entry_path, entry)

    def _task_id(self, task: CompileTask) -> str:
        return hashlib.sha256(str(task.source).encode("utf-8")).hexdigest()

    def _entry_path(self, task: CompileTask) -> Path:
        task_id = self._task_id(task)
        return self.entries / task_id[:2] / f"{task_id}.json"

    def _command_digest(self, task: CompileTask) -> str:
        digest = hashlib.sha256()
        digest.update(self.compiler_identity.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(task.directory).encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        for argument in task.command:
            digest.update(argument.encode("utf-8", errors="surrogateescape"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _dependency_states(self, dependencies: list[Path]) -> list[dict] | None:
        states: list[dict] = []
        for dependency in sorted(set(dependencies)):
            try:
                stat = dependency.stat()
            except OSError as exc:
                print(
                    f"警告：无法记录依赖{dependency}，本次结果不缓存：{exc}",
                    file=sys.stderr,
                )
                return None
            states.append({
                "path": str(dependency),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "ctime_ns": stat.st_ctime_ns,
            })
        return states

    def _dependencies_unchanged(self, raw_dependencies: object) -> bool:
        if not isinstance(raw_dependencies, list) or not raw_dependencies:
            return False
        for dependency in raw_dependencies:
            if not isinstance(dependency, dict):
                return False
            path = dependency.get("path")
            if not isinstance(path, str):
                return False
            try:
                stat = Path(path).stat()
            except OSError:
                return False
            if (
                dependency.get("size") != stat.st_size
                or dependency.get("mtime_ns") != stat.st_mtime_ns
                or dependency.get("ctime_ns") != stat.st_ctime_ns
            ):
                return False
        return True

    @staticmethod
    def _read_json(path: Path) -> object:
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _write_json_atomic(path: Path, result: object) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(result, file, ensure_ascii=False, separators=(",", ":"))
                file.write("\n")
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()


class NameTrie:
    TERMINAL = "\0"

    def __init__(self, names: set[str]):
        self.root: dict[str, dict] = {}
        for name in names:
            node = self.root
            for char in name:
                node = node.setdefault(char, {})
            node[self.TERMINAL] = {}

    def longest_match(self, text: str, start: int) -> str | None:
        node = self.root
        pos = start
        match_end: int | None = None
        while pos < len(text):
            next_node = node.get(text[pos])
            if next_node is None:
                break
            node = next_node
            pos += 1
            if self.TERMINAL in node and (pos == len(text) or text[pos].isspace()):
                match_end = pos
        return None if match_end is None else text[start:match_end]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "读取yuanrong-datasystem仓库根的compile_commands.json，使用Clang Static "
            "Analyzer生成src/datasystem的全量保守调用图JSON：所有函数一视同仁，"
            "无调用者的函数标记为顶层入口（RPC handler、后台线程、公共API实现等）。"
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="yuanrong-datasystem仓库根目录",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=OUTPUT_FILE,
        help=f"输出JSON路径，默认{OUTPUT_FILE}",
    )
    parser.add_argument(
        "--compile-database",
        type=Path,
        help="compile_commands.json路径；未指定时从常见构建目录查找",
    )
    parser.add_argument(
        "--jobs", type=int, default=MAX_JOBS,
        help=f"并行Clang任务数，默认{MAX_JOBS}",
    )
    parser.add_argument(
        "--timeout", type=int, default=ANALYSIS_TIMEOUT,
        help=f"单次Clang分析超时秒数，默认{ANALYSIS_TIMEOUT}",
    )
    parser.add_argument(
        "--timeout-retries", type=int, default=TIMEOUT_RETRIES,
        help=(
            "并发阶段超时的translation unit在其他任务结束后串行重试次数，"
            f"默认{TIMEOUT_RETRIES}"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help=(
            "逐translation unit分析缓存目录；默认使用compile_commands.json所在目录下的"
            f"{CACHE_DIRECTORY_NAME}"
        ),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用分析缓存，强制重新运行全部Clang任务",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="运行前清空本脚本拥有的分析缓存",
    )
    return parser.parse_args()


def is_repository_root(root: Path) -> bool:
    return (root / SCAN_ROOT).is_dir() and (root / STATUS_HEADER).is_file()


def resolve_repository_root(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.is_dir():
        raise ValueError(f"目录不存在：{candidate}")

    for root in [candidate, *candidate.parents]:
        if is_repository_root(root):
            return root
    raise ValueError(
        "无法定位yuanrong-datasystem仓库根；需要同时存在"
        f"{SCAN_ROOT}和{STATUS_HEADER}：{candidate}"
    )


def find_compile_database(repository_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        if not candidate.is_file():
            raise ValueError(f"编译数据库不存在：{candidate}")
        return candidate

    candidates = [
        repository_root / "compile_commands.json",
        repository_root / "build/compile_commands.json",
        repository_root / "build_release/compile_commands.json",
        repository_root / "build_debug/compile_commands.json",
        repository_root / "cmake-build-debug/compile_commands.json",
        repository_root / "cmake-build-release/compile_commands.json",
        repository_root / "tmp_build_dir/compile_commands.json",
    ]
    candidates.extend(sorted(repository_root.glob("build*/compile_commands.json")))
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    searched = "\n".join(f"  - {item}" for item in candidates)
    raise ValueError(
        "未找到compile_commands.json；可通过--compile-database显式指定。"
        f"已检查：\n{searched}"
    )


def load_compile_database(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8") as file:
            database = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取编译数据库{path}：{exc}") from exc
    if not isinstance(database, list):
        raise ValueError(f"编译数据库顶层必须是JSON数组：{path}")
    return database


def entry_arguments(entry: dict) -> list[str]:
    arguments = entry.get("arguments")
    if isinstance(arguments, list) and all(isinstance(item, str) for item in arguments):
        return list(arguments)
    command = entry.get("command")
    if not isinstance(command, str):
        raise ValueError("编译数据库entry缺少command或arguments")
    return shlex.split(command)


def path_from_entry(value: str, directory: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = directory / path
    return path.resolve()


def is_same_path_argument(argument: str, source: Path, directory: Path) -> bool:
    if argument.startswith("-"):
        return False
    try:
        return path_from_entry(argument, directory) == source
    except (OSError, RuntimeError):
        return False


def compiler_arguments_start(raw_arguments: list[str]) -> int:
    if not raw_arguments:
        return 0
    if Path(raw_arguments[0]).name in COMPILER_LAUNCHERS and len(raw_arguments) > 1:
        return 2
    return 1


def sanitize_arguments(
    raw_arguments: list[str], source: Path, directory: Path, clang: str,
) -> tuple[str, ...]:
    sanitized = [clang]
    pos = compiler_arguments_start(raw_arguments)
    while pos < len(raw_arguments):
        argument = raw_arguments[pos]
        if argument in DROP_ARGUMENTS_WITH_VALUE:
            pos += 2
            continue
        if argument in DROP_ARGUMENTS:
            pos += 1
            continue
        if argument.startswith("-o") and argument != "-O0":
            pos += 1
            continue
        if argument.startswith("-Werror") or argument.startswith("-Wp,-M"):
            pos += 1
            continue
        if is_same_path_argument(argument, source, directory):
            pos += 1
            continue
        sanitized.append(argument)
        pos += 1
    sanitized.extend([
        "--analyze",
        "-Xclang", "-analyzer-checker=debug.DumpCallGraph",
        "-Wno-everything",
        "-fno-color-diagnostics",
        "-Qunused-arguments",
        "-o", "/dev/null",
        str(source),
    ])
    return tuple(sanitized)


def collect_compile_tasks(
    database: list[dict], repository_root: Path, clang: str,
) -> list[CompileTask]:
    code_root = (repository_root / "src/datasystem").resolve()
    selected: dict[Path, CompileTask] = {}
    for entry in database:
        directory_value = entry.get("directory")
        source_value = entry.get("file")
        if not isinstance(directory_value, str) or not isinstance(source_value, str):
            continue
        directory = Path(directory_value).expanduser().resolve()
        source = path_from_entry(source_value, directory)
        try:
            source.relative_to(code_root)
        except ValueError:
            continue
        if source.suffix.lower() not in CPP_SUFFIXES or not source.is_file():
            continue
        command = sanitize_arguments(entry_arguments(entry), source, directory, clang)
        selected.setdefault(source, CompileTask(source, directory, command))
    if not selected:
        raise ValueError(f"编译数据库中没有找到{code_root}下的C++源文件")
    return [selected[source] for source in sorted(selected)]


def compiler_identity(clang: str) -> str:
    try:
        process = subprocess.run(
            [clang, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
        )
        stat = Path(clang).resolve().stat()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(
            f"无法确定Clang版本，不能安全使用分析缓存：{exc}"
        ) from exc
    if process.returncode != 0:
        raise ValueError(
            f"无法确定Clang版本，不能安全使用分析缓存：返回{process.returncode}"
        )
    identity = {
        "path": str(Path(clang).resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "version": process.stdout,
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()


def parse_call_graph_lines(output: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = CALL_GRAPH_PATTERN.match(line)
        if match is None:
            continue
        caller = match.group(1).strip()
        if caller != "< root >":
            records.append((caller, match.group(2).strip()))
    return records


def parse_dependency_file(path: Path, directory: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    text = text.replace("\\\r\n", "").replace("\\\n", "")
    separator = text.find(":")
    if separator < 0:
        raise ValueError("依赖文件缺少target分隔符")
    dependencies: list[Path] = []
    for value in shlex.split(text[separator + 1:], comments=False, posix=True):
        dependency = Path(value)
        if not dependency.is_absolute():
            dependency = directory / dependency
        dependencies.append(dependency.resolve())
    if not dependencies:
        raise ValueError("依赖文件中没有源码或头文件")
    return dependencies


def remove_dependency_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"警告：无法删除临时依赖文件{path}：{exc}", file=sys.stderr)


def analyze_task(
    task: CompileTask, timeout: int, dependency_file: Path | None = None,
) -> AnalysisResult:
    command = task.command
    if dependency_file is not None:
        command = (
            *task.command[:-1],
            "-MD", "-MF", str(dependency_file),
            task.command[-1],
        )
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=task.directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        remove_dependency_file(dependency_file)
        return AnalysisResult(
            task.source,
            [],
            f"Clang分析超时（{timeout}s）",
            timed_out=True,
            duration_seconds=time.monotonic() - started,
        )
    except OSError as exc:
        remove_dependency_file(dependency_file)
        return AnalysisResult(
            task.source,
            [],
            f"无法执行Clang：{exc}",
            duration_seconds=time.monotonic() - started,
        )

    duration = time.monotonic() - started
    function_calls = parse_call_graph_lines(process.stdout)
    if process.returncode != 0:
        diagnostics = "\n".join(process.stdout.splitlines()[-20:])
        remove_dependency_file(dependency_file)
        return AnalysisResult(
            task.source,
            function_calls,
            f"Clang返回{process.returncode}\n{diagnostics}",
            duration_seconds=duration,
        )
    # A translation unit may intentionally contain no definitions after
    # preprocessing. Clang still emits the dump header and an empty root node;
    # that is a valid empty graph, not an analysis failure. Keep treating a
    # successful process with no dump marker as an error so output-format
    # changes and unexpected analyzer behavior remain visible.
    if not function_calls and CALL_GRAPH_DUMP_PATTERN.search(process.stdout) is None:
        remove_dependency_file(dependency_file)
        return AnalysisResult(
            task.source,
            [],
            "Clang输出中没有Call graph Dump",
            duration_seconds=duration,
        )

    dependencies: list[Path] = []
    if dependency_file is not None:
        try:
            dependencies = parse_dependency_file(dependency_file, task.directory)
        except (OSError, ValueError) as exc:
            print(
                f"警告：无法解析{task.source.name}的依赖，结果不缓存：{exc}",
                file=sys.stderr,
            )
        finally:
            remove_dependency_file(dependency_file)
    return AnalysisResult(
        task.source,
        function_calls,
        duration_seconds=duration,
        dependencies=dependencies,
    )


def analyze_all(
    tasks: list[CompileTask],
    jobs: int,
    timeout: int,
    timeout_retries: int,
    cache: AnalysisCache | None,
) -> tuple[list[AnalysisResult], dict]:
    results: list[AnalysisResult] = []
    pending: list[tuple[CompileTask, float]] = []
    if cache is None:
        pending = [(task, 0.0) for task in tasks]
    else:
        for task in tasks:
            lookup = cache.lookup(task)
            if lookup.result is not None:
                results.append(lookup.result)
            else:
                pending.append((task, lookup.previous_duration))
        print(
            f"分析缓存：命中{len(results)}，需运行{len(pending)}，目录：{cache.root}",
            file=sys.stderr,
        )

    # Longest-processing-time-first reduces the tail when historical timings
    # are available, while the source path keeps first-run ordering stable.
    pending.sort(key=lambda item: (-item[1], str(item[0].source)))
    completed = len(results)
    if pending:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(jobs, len(pending)),
        ) as executor:
            futures = {}
            for task, _ in pending:
                dependency_file = (
                    cache.dependency_file(task) if cache is not None else None
                )
                future = executor.submit(analyze_task, task, timeout, dependency_file)
                futures[future] = task
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                result = future.result()
                results.append(result)
                if cache is not None:
                    try:
                        cache.store(task, result)
                    except OSError as exc:
                        print(
                            f"警告：无法写入{task.source.name}的分析缓存：{exc}",
                            file=sys.stderr,
                        )
                completed += 1
                status = "失败" if result.error else "完成"
                print(
                    f"[{completed}/{len(tasks)}] {status}：{result.source.name} "
                    f"({result.duration_seconds:.1f}s)",
                    file=sys.stderr,
                )

    # Large translation units can exceed the deadline only while several
    # Clang analyzers compete for CPU and memory. Retry those failures after
    # the parallel pool has drained, one at a time, without rerunning genuine
    # compiler errors.
    task_by_source = {task.source: task for task in tasks}
    for attempt in range(1, timeout_retries + 1):
        retry_indexes = [
            index for index, result in enumerate(results) if result.timed_out
        ]
        if not retry_indexes:
            break
        for retry_pos, index in enumerate(retry_indexes, start=1):
            previous = results[index]
            print(
                f"[超时重试{attempt}/{timeout_retries}，{retry_pos}/{len(retry_indexes)}] "
                f"串行分析：{previous.source.name}",
                file=sys.stderr,
            )
            task = task_by_source[previous.source]
            dependency_file = (
                cache.dependency_file(task) if cache is not None else None
            )
            retried = analyze_task(task, timeout, dependency_file)
            results[index] = retried
            if cache is not None:
                try:
                    cache.store(task, retried)
                except OSError as exc:
                    print(
                        f"警告：无法写入{task.source.name}的分析缓存：{exc}",
                        file=sys.stderr,
                    )
            status = "失败" if retried.error else "完成"
            print(f"[超时重试] {status}：{retried.source.name}", file=sys.stderr)
    cache_stats = {
        "enabled": cache is not None,
        "directory": str(cache.root) if cache is not None else None,
        "hits": len(tasks) - len(pending),
        "misses": len(pending),
    }
    return sorted(results, key=lambda item: item.source), cache_stats


def split_callees(tail: str, trie: NameTrie) -> list[str]:
    callees: list[str] = []
    pos = 0
    while pos < len(tail):
        while pos < len(tail) and tail[pos].isspace():
            pos += 1
        if pos >= len(tail):
            break
        callee = trie.longest_match(tail, pos)
        if callee is not None:
            callees.append(callee)
            pos += len(callee)
            continue
        end = pos
        while end < len(tail) and not tail[end].isspace():
            end += 1
        if end > pos:
            callees.append(tail[pos:end])
        pos = end
    return callees


def build_graph(
    results: list[AnalysisResult],
) -> tuple[dict[str, set[str]], dict[tuple[str, str], str]]:
    raw_records: list[tuple[str, str]] = []
    names: set[str] = set()
    for result in results:
        for caller, tail in result.function_calls:
            raw_records.append((caller, tail))
            names.add(caller)
    trie = NameTrie(names)
    graph: dict[str, set[str]] = defaultdict(set)
    edge_kinds: dict[tuple[str, str], str] = {}
    for caller, tail in raw_records:
        graph.setdefault(caller, set())
        for callee in split_callees(tail, trie):
            graph[caller].add(callee)
            # Pure virtual declarations and external leaves may occur only as
            # callees. Keeping them as graph nodes allows project bindings to
            # expand a pure-interface call to its concrete implementation.
            graph.setdefault(callee, set())
            edge_kinds[(caller, callee)] = "direct"
    add_virtual_edges(graph, edge_kinds)
    return graph, edge_kinds


def add_virtual_edges(
    graph: dict[str, set[str]], edge_kinds: dict[tuple[str, str], str],
) -> None:
    known = set(graph)
    for interface, implementations in VIRTUAL_BINDINGS.items():
        prefix = f"{interface}::"
        for interface_function in sorted(name for name in known if name.startswith(prefix)):
            method = interface_function[len(prefix):]
            for implementation in implementations:
                target = f"{implementation}::{method}"
                if target not in known:
                    continue
                graph[interface_function].add(target)
                edge_kinds[(interface_function, target)] = "virtual"


def is_relevant_function(name: str) -> bool:
    if name.startswith(TERMINAL_PREFIXES):
        return True
    if not name.startswith("datasystem::"):
        return False
    return not name.startswith(EXCLUDED_PREFIXES)


def relevant_children(caller: str, graph: dict[str, set[str]]) -> list[str]:
    if caller.startswith(TERMINAL_PREFIXES):
        return []
    return sorted(callee for callee in graph.get(caller, ()) if is_relevant_function(callee))


def short_function_name(qualified_name: str) -> str:
    return qualified_name.rsplit("::", 1)[-1]


def build_full_graph(
    graph: dict[str, set[str]],
    edge_kinds: dict[tuple[str, str], str],
) -> tuple[list[dict], list[dict], int]:
    """Return (functions, edges, entry_count) over all relevant functions.

    Every function is treated equally regardless of reachability from public
    APIs.  A function without callers is a top-level entry: RPC handlers,
    background thread entries, public API implementations, static
    initializers and callbacks installed on external frameworks all qualify.
    """
    relevant_functions = sorted(
        name for name in graph if is_relevant_function(name)
    )
    callers_of: dict[str, set[str]] = defaultdict(set)
    for caller in relevant_functions:
        for callee in relevant_children(caller, graph):
            callers_of[callee].add(caller)

    functions: list[dict] = []
    edges: list[dict] = []
    for name in relevant_functions:
        callees = sorted(relevant_children(name, graph))
        callers = sorted(callers_of.get(name, ()))
        functions.append({
            "qualified_name": name,
            "function_name": short_function_name(name),
            "entry": not callers,
            "callers": callers,
            "callees": callees,
        })
    for caller in relevant_functions:
        for callee in sorted(relevant_children(caller, graph)):
            edges.append({
                "caller": caller,
                "callee": callee,
                "kind": edge_kinds.get((caller, callee), "direct"),
            })
    entry_count = sum(1 for function in functions if function["entry"])
    return functions, edges, entry_count


def relative_source(path: Path, repository_root: Path) -> str:
    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return str(path)


def source_fingerprint(repository_root: Path, compile_database: Path) -> str:
    digest = hashlib.sha256()
    roots = [repository_root / "include/datasystem", repository_root / "src/datasystem"]
    files = [
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in FINGERPRINT_SUFFIXES
    ]
    files.append(compile_database)
    for path in sorted(set(files)):
        digest.update(relative_source(path, repository_root).encode("utf-8"))
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_output(
    repository_root: Path,
    compile_database: Path,
    tasks: list[CompileTask],
    results: list[AnalysisResult],
    graph: dict[str, set[str]],
    edge_kinds: dict[tuple[str, str], str],
    cache_stats: dict,
) -> dict:
    failures = [
        {
            "source": relative_source(result.source, repository_root),
            "error": result.error,
        }
        for result in results
        if result.error is not None
    ]
    functions, edges, entry_count = build_full_graph(graph, edge_kinds)
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": "generate_kvcache_callchains.py",
        "graph_semantics": {
            "kind": "full_conservative_static_call_graph",
            "branch_sensitive": False,
            "overloads": "merged_by_clang_qualified_name",
            "runtime_function_pointers_resolved": False,
            "virtual_dispatch": "expanded_by_project_bindings",
            "entry_definition": (
                "无调用者的函数即顶层入口（RPC handler、后台线程入口、公共API实现、"
                "静态初始化等），不要求从公共API可达"
            ),
            "limitations": [
                "候选调用图不证明错误或状态一定沿该路径传播",
                "运行时函数指针、回调与跨TU实例化的部分调用边可能缺失，无调用者记录的函数按顶层入口处理",
                "虚调用只展开脚本中列出的接口与实现绑定",
                "日志、指标、性能与trace基础设施被排除以避免诊断噪声扩散",
            ],
        },
        "source_root": str(repository_root),
        "scan_root": SCAN_ROOT.as_posix(),
        "compile_database": str(compile_database),
        "source_fingerprint": source_fingerprint(repository_root, compile_database),
        "analysis": {
            "complete": not failures,
            "translation_units_total": len(tasks),
            "translation_units_succeeded": len(tasks) - len(failures),
            "translation_units_failed": len(failures),
            "failures": failures,
            "cache": cache_stats,
        },
        "virtual_bindings": {
            interface: list(implementations)
            for interface, implementations in VIRTUAL_BINDINGS.items()
        },
        "excluded_prefixes": list(EXCLUDED_PREFIXES),
        "terminal_prefixes": list(TERMINAL_PREFIXES),
        "function_count": len(functions),
        "entry_count": entry_count,
        "edge_count": len(edges),
        "functions": functions,
        "edges": edges,
    }


def write_json(result: dict, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_arguments()
    try:
        if args.jobs <= 0:
            raise ValueError("--jobs必须大于0")
        if args.timeout <= 0:
            raise ValueError("--timeout必须大于0")
        if args.timeout_retries < 0:
            raise ValueError("--timeout-retries不能小于0")
        if args.no_cache and args.clear_cache:
            raise ValueError("--no-cache与--clear-cache不能同时使用")
        repository_root = resolve_repository_root(args.source)
        compile_database = find_compile_database(repository_root, args.compile_database)
        clang = shutil.which(CLANG_COMMAND)
        if clang is None:
            raise ValueError(f"未找到Clang命令：{CLANG_COMMAND}")
        database = load_compile_database(compile_database)
        tasks = collect_compile_tasks(database, repository_root, clang)

        cache: AnalysisCache | None = None
        if not args.no_cache:
            cache_root = (
                args.cache_dir
                if args.cache_dir is not None
                else compile_database.parent / CACHE_DIRECTORY_NAME
            )
            try:
                cache = AnalysisCache(cache_root, compiler_identity(clang))
                cache.initialize(args.clear_cache)
            except (OSError, ValueError) as exc:
                if args.cache_dir is not None or args.clear_cache:
                    raise ValueError(f"无法初始化分析缓存：{exc}") from exc
                print(
                    f"警告：无法初始化默认分析缓存，将禁用缓存：{exc}",
                    file=sys.stderr,
                )
                cache = None
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    output = args.output.expanduser().resolve()
    print(
        f"使用{clang}分析{len(tasks)}个translation unit，"
        f"生成{SCAN_ROOT.as_posix()}全量调用图，输出：{output}",
        file=sys.stderr,
    )
    results, cache_stats = analyze_all(
        tasks,
        min(args.jobs, len(tasks)),
        args.timeout,
        args.timeout_retries,
        cache,
    )
    graph, edge_kinds = build_graph(results)
    result = build_output(
        repository_root,
        compile_database,
        tasks,
        results,
        graph,
        edge_kinds,
        cache_stats,
    )
    try:
        write_json(result, output)
    except OSError as exc:
        print(f"错误：无法写入{output}：{exc}", file=sys.stderr)
        return 2

    analysis = result["analysis"]
    print(
        "全量调用图JSON已生成："
        f"{output}（函数{result['function_count']}个，顶层入口{result['entry_count']}个，"
        f"边{result['edge_count']}条；成功"
        f"{analysis['translation_units_succeeded']}/"
        f"{analysis['translation_units_total']}）",
        file=sys.stderr,
    )
    if not analysis["complete"]:
        print("错误：调用图分析不完整", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
