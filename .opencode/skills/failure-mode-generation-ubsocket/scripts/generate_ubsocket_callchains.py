#!/usr/bin/env python3

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
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1
OUTPUT_FILE = Path("/tmp/ubsocket_api_callchains.json")
CLANG_COMMAND = "clang++"
MAX_JOBS = min(os.cpu_count() or 1, 8)
ANALYSIS_TIMEOUT = 180
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
API_ROOTS = (
    ("accept", "ock::ubs::SocketBase::Accept"),
    ("connect", "ock::ubs::SocketBase::Connect"),
    ("writev", "ock::ubs::SocketBase::WriteV"),
    ("readv", "ock::ubs::SocketBase::ReadV"),
)
VIRTUAL_BINDINGS = {
    "ock::ubs::AcceptorOps": ("ock::ubs::umq::UmqAcceptorOps",),
    "ock::ubs::ConnectorOps": ("ock::ubs::umq::UmqConnectorOps",),
    "ock::ubs::DataTxOps": ("ock::ubs::umq::UmqTxOps",),
    "ock::ubs::DataRxOps": ("ock::ubs::umq::UmqRxOps",),
}
EXCLUDED_PREFIXES = (
    "ock::ubs::Logger::",
    "ock::ubs::Ref<",
    "ock::ubs::RefConvert",
    "ock::ubs::MakeRef",
)
EXCLUDED_NAMES = {
    "ock::ubs::Func::Error2Str",
}
DROP_ARGUMENTS = {
    "-c",
    "--compile",
    "-MD",
    "-MMD",
    "-MP",
    "-MG",
    "-M",
    "-MM",
    "-fpermissive",
}
DROP_ARGUMENTS_WITH_VALUE = {
    "-o",
    "-MF",
    "-MT",
    "-MQ",
    "-MJ",
    "--serialize-diagnostics",
}
CALL_GRAPH_PATTERN = re.compile(r"^\s*Function: (.*?) calls:(.*)$")
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
        length = len(text)

        while pos < length:
            char = text[pos]
            next_node = node.get(char)
            if next_node is None:
                break
            node = next_node
            pos += 1
            if self.TERMINAL in node and (pos == length or text[pos].isspace()):
                match_end = pos

        if match_end is None:
            return None
        return text[start:match_end]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "读取 compile_commands.json，使用 Clang Static Analyzer 生成 "
            "SocketBase::Accept/Connect/WriteV/ReadV 的函数调用链 JSON。"
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="UBSocket的csrc源码目录，例如/root/openeuler/ubs-comm/src/ubsocket/csrc",
    )
    return parser.parse_args()


def resolve_source_root(path: Path) -> tuple[Path, Path]:
    candidate = path.expanduser().resolve()
    if not candidate.is_dir():
        raise ValueError(f"源码目录不存在：{candidate}")

    if (candidate / "core/ubsocket_socket.h").is_file():
        source_root = candidate.parent
        return source_root, source_root.parent.parent

    if (candidate / "csrc/core/ubsocket_socket.h").is_file():
        return candidate, candidate.parent.parent

    source_root = candidate / "src/ubsocket"
    if (source_root / "csrc/core/ubsocket_socket.h").is_file():
        return source_root, candidate

    raise ValueError(
        "无法定位UBSocket源码，需要传入src/ubsocket/csrc目录："
        f"{candidate}"
    )


def find_compile_database(
    source_root: Path,
    repository_root: Path,
) -> Path:
    candidates = [
        source_root / "build/compile_commands.json",
        repository_root / "tmp_build_dir/compile_commands.json",
        repository_root / "compile_commands.json",
        repository_root / "cmake-build-debug/compile_commands.json",
        repository_root / "cmake-build-release/compile_commands.json",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    searched = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise ValueError(f"未找到compile_commands.json，已检查：\n{searched}")


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


def sanitize_arguments(
    raw_arguments: list[str],
    source: Path,
    directory: Path,
    clang: str,
) -> tuple[str, ...]:
    sanitized = [clang]
    pos = 1

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
        if argument.startswith("-Werror"):
            pos += 1
            continue
        if argument.startswith("-Wp,-M"):
            pos += 1
            continue
        if is_same_path_argument(argument, source, directory):
            pos += 1
            continue

        sanitized.append(argument)
        pos += 1

    sanitized.extend(
        [
            "--analyze",
            "-Xclang",
            "-analyzer-checker=debug.DumpCallGraph",
            "-Wno-everything",
            "-fno-color-diagnostics",
            "-Qunused-arguments",
            "-o",
            "/dev/null",
            str(source),
        ]
    )
    return tuple(sanitized)


def collect_compile_tasks(
    database: list[dict],
    source_root: Path,
    clang: str,
) -> list[CompileTask]:
    csrc_root = (source_root / "csrc").resolve()
    selected: dict[Path, CompileTask] = {}

    for entry in database:
        directory_value = entry.get("directory")
        source_value = entry.get("file")
        if not isinstance(directory_value, str) or not isinstance(source_value, str):
            continue

        directory = Path(directory_value).expanduser().resolve()
        source = path_from_entry(source_value, directory)
        try:
            source.relative_to(csrc_root)
        except ValueError:
            continue
        if source.suffix.lower() not in {".cc", ".cpp", ".cxx"} or not source.is_file():
            continue

        raw_arguments = entry_arguments(entry)
        command = sanitize_arguments(raw_arguments, source, directory, clang)
        selected.setdefault(
            source,
            CompileTask(source=source, directory=directory, command=command),
        )

    if not selected:
        raise ValueError(f"编译数据库中没有找到{csrc_root}下的C++源文件")
    return [selected[source] for source in sorted(selected)]


def parse_call_graph_lines(output: str) -> list[tuple[str, str]]:
    function_calls: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = CALL_GRAPH_PATTERN.match(line)
        if match is None:
            continue
        caller = match.group(1).strip()
        if caller == "< root >":
            continue
        function_calls.append((caller, match.group(2).strip()))
    return function_calls


def analyze_task(task: CompileTask, timeout: int) -> AnalysisResult:
    try:
        process = subprocess.run(
            task.command,
            cwd=task.directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return AnalysisResult(
            source=task.source,
            function_calls=[],
            error=f"Clang分析超时（{timeout}s）",
        )
    except OSError as exc:
        return AnalysisResult(
            source=task.source,
            function_calls=[],
            error=f"无法执行Clang：{exc}",
        )

    function_calls = parse_call_graph_lines(process.stdout)
    if process.returncode != 0:
        diagnostics = "\n".join(process.stdout.splitlines()[-20:])
        return AnalysisResult(
            source=task.source,
            function_calls=function_calls,
            error=f"Clang返回{process.returncode}\n{diagnostics}",
        )
    if not function_calls:
        return AnalysisResult(
            source=task.source,
            function_calls=[],
            error="Clang输出中没有Call graph Dump",
        )
    return AnalysisResult(source=task.source, function_calls=function_calls)


def analyze_all(
    tasks: list[CompileTask],
    jobs: int,
    timeout: int,
) -> list[AnalysisResult]:
    results: list[AnalysisResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_task = {
            executor.submit(analyze_task, task, timeout): task
            for task in tasks
        }
        completed = 0
        for future in concurrent.futures.as_completed(future_to_task):
            result = future.result()
            results.append(result)
            completed += 1
            status = "失败" if result.error else "完成"
            print(
                f"[{completed}/{len(tasks)}] {status}：{result.source.name}",
                file=sys.stderr,
            )
    return sorted(results, key=lambda item: item.source)


def split_callees(tail: str, trie: NameTrie) -> list[str]:
    callees: list[str] = []
    pos = 0
    length = len(tail)

    while pos < length:
        while pos < length and tail[pos].isspace():
            pos += 1
        if pos >= length:
            break

        callee = trie.longest_match(tail, pos)
        if callee is not None:
            callees.append(callee)
            pos += len(callee)
            continue

        end = pos
        while end < length and not tail[end].isspace():
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
            edge_kinds[(caller, callee)] = "direct"

    add_virtual_edges(graph, edge_kinds)
    return graph, edge_kinds


def add_virtual_edges(
    graph: dict[str, set[str]],
    edge_kinds: dict[tuple[str, str], str],
) -> None:
    known_functions = set(graph)
    for base_class, concrete_classes in VIRTUAL_BINDINGS.items():
        prefix = f"{base_class}::"
        for base_function in sorted(name for name in known_functions if name.startswith(prefix)):
            method = base_function[len(prefix):]
            for concrete_class in concrete_classes:
                concrete_function = f"{concrete_class}::{method}"
                if concrete_function not in known_functions:
                    continue
                graph[base_function].add(concrete_function)
                edge_kinds[(base_function, concrete_function)] = "virtual"


def is_relevant_function(name: str) -> bool:
    if not name.startswith("ock::ubs::"):
        return False
    if name in EXCLUDED_NAMES:
        return False
    return not name.startswith(EXCLUDED_PREFIXES)


def relevant_children(
    caller: str,
    graph: dict[str, set[str]],
) -> list[str]:
    return sorted(callee for callee in graph.get(caller, ()) if is_relevant_function(callee))


def short_function_name(qualified_name: str) -> str:
    return qualified_name.rsplit("::", 1)[-1]


def build_chain(
    api: str,
    root: str,
    graph: dict[str, set[str]],
    edge_kinds: dict[tuple[str, str], str],
) -> dict:
    if root not in graph:
        return {
            "api": api,
            "root": root,
            "complete": False,
            "error": "Clang调用图中未找到入口函数",
            "function_count": 0,
            "edge_count": 0,
            "function_names": [],
            "functions": [],
            "edges": [],
        }

    depths = {root: 0}
    predecessors: dict[str, str] = {}
    queue = deque([root])

    while queue:
        caller = queue.popleft()
        for callee in relevant_children(caller, graph):
            if callee in depths:
                continue
            depths[callee] = depths[caller] + 1
            predecessors[callee] = caller
            queue.append(callee)

    reachable = set(depths)
    functions = []
    for function in sorted(reachable, key=lambda name: (depths[name], name)):
        path = [function]
        current = function
        while current != root:
            current = predecessors[current]
            path.append(current)
        path.reverse()
        children = [child for child in relevant_children(function, graph) if child in reachable]
        functions.append(
            {
                "qualified_name": function,
                "function_name": short_function_name(function),
                "depth": depths[function],
                "leaf": not children,
                "path": path,
            }
        )

    edges = []
    for caller in sorted(reachable):
        for callee in relevant_children(caller, graph):
            if callee not in reachable:
                continue
            edges.append(
                {
                    "caller": caller,
                    "callee": callee,
                    "kind": edge_kinds.get((caller, callee), "direct"),
                }
            )

    return {
        "api": api,
        "root": root,
        "complete": True,
        "function_count": len(functions),
        "edge_count": len(edges),
        "function_names": sorted({item["function_name"] for item in functions}),
        "functions": functions,
        "edges": edges,
    }


def relative_source(path: Path, source_root: Path) -> str:
    try:
        return str(path.relative_to(source_root))
    except ValueError:
        return str(path)


def source_fingerprint(source_root: Path, compile_database: Path) -> str:
    digest = hashlib.sha256()
    files = [
        path
        for path in source_root.joinpath("csrc").rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    ]
    files.append(compile_database)

    for path in sorted(files):
        digest.update(str(path).encode("utf-8"))
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_output(
    source_root: Path,
    compile_database: Path,
    tasks: list[CompileTask],
    results: list[AnalysisResult],
    graph: dict[str, set[str]],
    edge_kinds: dict[tuple[str, str], str],
) -> dict:
    failures = [
        {
            "source": relative_source(result.source, source_root),
            "error": result.error,
        }
        for result in results
        if result.error is not None
    ]
    chains = [
        build_chain(api, root, graph, edge_kinds)
        for api, root in API_ROOTS
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generator": "generate_ubsocket_callchains.py",
        "graph_semantics": {
            "kind": "conservative_static_call_graph",
            "branch_sensitive": False,
            "runtime_function_pointers_resolved": False,
            "virtual_dispatch": "expanded_by_project_bindings",
        },
        "source_root": str(source_root),
        "compile_database": str(compile_database),
        "source_fingerprint": source_fingerprint(source_root, compile_database),
        "analysis": {
            "complete": not failures and all(chain["complete"] for chain in chains),
            "translation_units_total": len(tasks),
            "translation_units_succeeded": len(tasks) - len(failures),
            "translation_units_failed": len(failures),
            "failures": failures,
        },
        "virtual_bindings": {
            base: list(concrete)
            for base, concrete in VIRTUAL_BINDINGS.items()
        },
        "call_chains": chains,
    }


def write_json(result: dict, output: Path) -> None:
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
        source_root, repository_root = resolve_source_root(args.source)
        compile_database = find_compile_database(
            source_root,
            repository_root,
        )
        clang = shutil.which(CLANG_COMMAND)
        if clang is None:
            raise ValueError(f"未找到Clang命令：{CLANG_COMMAND}")
        database = load_compile_database(compile_database)
        tasks = collect_compile_tasks(database, source_root, clang)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    print(
        f"使用{clang}分析{len(tasks)}个translation unit，输出：{OUTPUT_FILE}",
        file=sys.stderr,
    )
    results = analyze_all(tasks, min(MAX_JOBS, len(tasks)), ANALYSIS_TIMEOUT)
    graph, edge_kinds = build_graph(results)
    result = build_output(
        source_root,
        compile_database,
        tasks,
        results,
        graph,
        edge_kinds,
    )

    try:
        write_json(result, OUTPUT_FILE)
    except OSError as exc:
        print(f"错误：无法写入{OUTPUT_FILE}：{exc}", file=sys.stderr)
        return 2

    analysis = result["analysis"]
    print(
        "调用链JSON已生成："
        f"{OUTPUT_FILE}（成功{analysis['translation_units_succeeded']}/"
        f"{analysis['translation_units_total']}）",
        file=sys.stderr,
    )

    if not analysis["complete"]:
        print("错误：调用链分析不完整", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
