#!/usr/bin/env python3
"""Use libclang ASTs to derive conservative StatusCode evidence for runtime groups."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RUNTIME = Path("/tmp/kvcache_runtime_err.json")
DEFAULT_OUTPUT = Path("/tmp/kvcache_status_ast.json")
CPP_SUFFIXES = {".cc", ".cpp", ".cxx"}
DROP_FLAGS = {"-c", "--compile", "-MD", "-MMD", "-MP", "-MG", "-M", "-MM"}
DROP_WITH_VALUE = {"-o", "-MF", "-MT", "-MQ", "-MJ", "--serialize-diagnostics"}
LAUNCHERS = {"ccache", "sccache", "distcc", "icecc"}
IGNORED_STATUS_CALLEES = {"Status", "GetCode", "ToString", "GetMsg", "IsError", "IsOk"}


@dataclass(frozen=True)
class ParseTask:
    source: Path
    directory: Path
    arguments: tuple[str, ...]


def load_clang():
    try:
        from clang import cindex
    except ImportError as exc:
        raise ValueError("缺少 clang Python binding，无法运行 AST 分析") from exc
    if not cindex.Config.loaded:
        candidates = [
            Path("/usr/lib64/libclang.so.17"), Path("/usr/lib64/libclang.so"),
            Path("/usr/lib/libclang.so.17"), Path("/usr/lib/libclang.so"),
        ]
        library = next((path for path in candidates if path.is_file()), None)
        if library is None:
            raise ValueError("找不到 libclang.so")
        cindex.Config.set_library_file(str(library))
    return cindex


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc


def find_compile_database(root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if path.is_file():
            return path
        raise ValueError(f"编译数据库不存在：{path}")
    candidates = [
        root / "compile_commands.json", root / "build/compile_commands.json",
        root / "build_release/compile_commands.json", root / "build_debug/compile_commands.json",
    ]
    candidates.extend(sorted(root.glob("build*/compile_commands.json")))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError("找不到 compile_commands.json；请通过 --compile-database 指定")


def entry_arguments(entry: dict) -> list[str]:
    if isinstance(entry.get("arguments"), list):
        return list(entry["arguments"])
    if isinstance(entry.get("command"), str):
        return shlex.split(entry["command"])
    raise ValueError("compile_commands entry 缺少 arguments/command")


def resolved_path(value: str, directory: Path) -> Path:
    path = Path(value)
    return (directory / path).resolve() if not path.is_absolute() else path.resolve()


def parse_arguments_for_tu(entry: dict, source: Path, directory: Path,
                           resource_dir: str | None = None) -> tuple[str, ...]:
    raw = entry_arguments(entry)
    start = 2 if raw and Path(raw[0]).name in LAUNCHERS else 1
    result: list[str] = []
    pos = start
    while pos < len(raw):
        argument = raw[pos]
        if argument in DROP_WITH_VALUE:
            pos += 2
            continue
        if argument in DROP_FLAGS:
            pos += 1
            continue
        if argument.startswith("-o") and argument != "-O0":
            pos += 1
            continue
        if argument.startswith("-Werror") or argument.startswith("-Wp,-M"):
            pos += 1
            continue
        if not argument.startswith("-"):
            try:
                if resolved_path(argument, directory) == source:
                    pos += 1
                    continue
            except OSError:
                pass
        result.append(argument)
        pos += 1
    result.extend(["-Wno-everything", "-fno-color-diagnostics"])
    if resource_dir and not any(argument.startswith("-resource-dir") for argument in result):
        result.extend(["-resource-dir", resource_dir])
    return tuple(result)


def compile_tasks(database: list[dict], wanted: set[Path],
                  resource_dir: str | None = None) -> list[ParseTask]:
    tasks: dict[Path, ParseTask] = {}
    for entry in database:
        if not isinstance(entry, dict) or not isinstance(entry.get("directory"), str) \
                or not isinstance(entry.get("file"), str):
            continue
        directory = Path(entry["directory"]).expanduser().resolve()
        source = resolved_path(entry["file"], directory)
        if source not in wanted:
            continue
        tasks[source] = ParseTask(
            source, directory, parse_arguments_for_tu(entry, source, directory, resource_dir)
        )
    return [tasks[source] for source in sorted(tasks)]


def compiler_resource_dir(clang: str) -> str:
    try:
        process = subprocess.run(
            [clang, "-print-resource-dir"], check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"无法查询 Clang resource dir：{exc}") from exc
    value = process.stdout.strip()
    if process.returncode != 0 or not Path(value).is_dir():
        raise ValueError(f"Clang resource dir 无效：{value or process.stderr.strip()}")
    return value


def cursor_file(cursor) -> str | None:
    location = cursor.location
    return str(Path(location.file.name).resolve()) if location.file is not None else None


def qualified_name(cursor) -> str:
    names = [cursor.spelling or cursor.displayname]
    parent = cursor.semantic_parent
    while parent is not None and cursor_kind_name(parent) != "CursorKind.TRANSLATION_UNIT":
        if parent.spelling:
            names.append(parent.spelling)
        parent = parent.semantic_parent
    return "::".join(reversed([name for name in names if name]))


def cursor_kind_name(cursor) -> str:
    # Some vendor Clang 17 builds expose extension cursor ids that the matching
    # Python package does not name. They are irrelevant to this analysis but
    # must not abort traversal.
    try:
        return str(cursor.kind)
    except ValueError:
        return f"CursorKind.UNKNOWN_{getattr(cursor, '_kind_id', 'unknown')}"


def walk(cursor, skip_nested_functions: bool = False):
    function_kinds = {
        "CursorKind.FUNCTION_DECL", "CursorKind.CXX_METHOD", "CursorKind.CONSTRUCTOR",
        "CursorKind.DESTRUCTOR", "CursorKind.FUNCTION_TEMPLATE",
    }
    for child in cursor.get_children():
        if skip_nested_functions and cursor_kind_name(child) in function_kinds:
            continue
        yield child
        yield from walk(child, skip_nested_functions=skip_nested_functions)


def tokens(cursor) -> list[str]:
    try:
        return [token.spelling for token in cursor.get_tokens()]
    except Exception:
        return []


def is_status_type(spelling: str) -> bool:
    return bool(re.search(r"(?:^|::)Status(?:Code)?(?:\s|$|[<&*])", spelling))


def symbolic_source(cursor) -> tuple[set[str], set[str], set[str]]:
    codes: set[str] = set()
    callees: set[str] = set()
    variables: set[str] = set()
    nodes = [cursor, *walk(cursor, skip_nested_functions=True)]
    spellings = tokens(cursor)
    codes.update(token for token in spellings if re.fullmatch(r"K_[A-Z0-9_]+", token))
    if "OK" in spellings and "Status" in spellings:
        codes.add("K_OK")
    for node in nodes:
        kind = cursor_kind_name(node)
        if kind == "CursorKind.CALL_EXPR":
            referenced = node.referenced
            if referenced is not None and referenced.spelling not in IGNORED_STATUS_CALLEES \
                    and is_status_type(referenced.result_type.spelling):
                usr = referenced.get_usr()
                if usr:
                    callees.add(usr)
        elif kind == "CursorKind.DECL_REF_EXPR":
            referenced = node.referenced
            if referenced is not None and cursor_kind_name(referenced) == "CursorKind.VAR_DECL":
                variables.add(referenced.get_usr() or referenced.spelling)
    return codes, callees, variables


def merge_symbolic(target: dict, source: tuple[set[str], set[str], set[str]]) -> None:
    target["codes"].update(source[0])
    target["callees"].update(source[1])
    target["variables"].update(source[2])


def function_summary(cursor) -> dict:
    variable_sources: dict[str, dict] = {}
    descendants = list(walk(cursor, skip_nested_functions=True))
    for node in descendants:
        kind = cursor_kind_name(node)
        if kind == "CursorKind.VAR_DECL":
            key = node.get_usr() or node.spelling
            value = {"codes": set(), "callees": set(), "variables": set()}
            for child in node.get_children():
                merge_symbolic(value, symbolic_source(child))
            variable_sources.setdefault(key, {"codes": set(), "callees": set(), "variables": set()})
            for field in value:
                variable_sources[key][field].update(value[field])
        elif kind == "CursorKind.BINARY_OPERATOR" and "=" in tokens(node):
            children = list(node.get_children())
            if len(children) >= 2 and cursor_kind_name(children[0]) == "CursorKind.DECL_REF_EXPR":
                referenced = children[0].referenced
                key = (referenced.get_usr() if referenced is not None else "") or children[0].spelling
                value = variable_sources.setdefault(
                    key, {"codes": set(), "callees": set(), "variables": set()}
                )
                merge_symbolic(value, symbolic_source(children[-1]))

    def expand_variables(value: dict) -> dict:
        pending = list(value["variables"])
        visited: set[str] = set()
        unknown = False
        while pending:
            variable = pending.pop()
            if variable in visited:
                continue
            visited.add(variable)
            source = variable_sources.get(variable)
            if source is None:
                unknown = True
                continue
            value["codes"].update(source["codes"])
            value["callees"].update(source["callees"])
            pending.extend(source["variables"])
        value["unknown"] = unknown or not value["codes"] and not value["callees"]
        value.pop("variables", None)
        return value

    return_paths: list[dict] = []
    callsites: list[dict] = []
    for node in descendants:
        kind = cursor_kind_name(node)
        if kind == "CursorKind.RETURN_STMT":
            value = {"codes": set(), "callees": set(), "variables": set()}
            merge_symbolic(value, symbolic_source(node))
            expanded = expand_variables(value)
            return_paths.append({
                "codes": sorted(expanded["codes"]),
                "callees": sorted(expanded["callees"]),
                "unknown": expanded["unknown"],
            })
        elif kind == "CursorKind.CALL_EXPR":
            referenced = node.referenced
            if referenced is None or referenced.spelling in IGNORED_STATUS_CALLEES \
                    or not is_status_type(referenced.result_type.spelling):
                continue
            usr = referenced.get_usr()
            location_file = cursor_file(node)
            if usr and location_file:
                callsites.append({
                    "file": location_file,
                    "line": node.location.line,
                    "column": node.location.column,
                    "callee_usr": usr,
                    "callee": qualified_name(referenced),
                })
    return {
        "usr": cursor.get_usr(),
        "qualified_name": qualified_name(cursor),
        "function_name": cursor.spelling,
        "file": cursor_file(cursor),
        "line": cursor.location.line,
        "result_type": cursor.result_type.spelling,
        "return_paths": return_paths,
        "callsites": callsites,
    }


def analyze_task(task: ParseTask) -> dict:
    cindex = load_clang()
    try:
        index = cindex.Index.create()
        translation_unit = index.parse(str(task.source), args=list(task.arguments))
    except Exception as exc:
        return {"source": str(task.source), "error": str(exc), "summaries": []}
    diagnostics = [str(item) for item in translation_unit.diagnostics if item.severity >= item.Error]
    summaries: list[dict] = []
    function_kinds = {
        "CursorKind.FUNCTION_DECL", "CursorKind.CXX_METHOD", "CursorKind.CONSTRUCTOR",
        "CursorKind.DESTRUCTOR", "CursorKind.FUNCTION_TEMPLATE",
    }
    for cursor in walk(translation_unit.cursor):
        if cursor_kind_name(cursor) not in function_kinds or not cursor.is_definition() or not cursor.get_usr():
            continue
        if not is_status_type(cursor.result_type.spelling):
            # Keep non-Status containing functions only when they have a Status
            # callsite; this is populated below by function_summary.
            summary = function_summary(cursor)
            if summary["callsites"]:
                summaries.append(summary)
            continue
        summaries.append(function_summary(cursor))
    return {
        "source": str(task.source),
        "error": "\n".join(diagnostics[-10:]) if diagnostics else None,
        "summaries": summaries,
    }


def analyze_task_subprocess(task: ParseTask, timeout: int) -> dict:
    payload = json.dumps({
        "source": str(task.source),
        "directory": str(task.directory),
        "arguments": list(task.arguments),
    })
    try:
        process = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"source": str(task.source), "error": f"AST 分析超时（{timeout}s）", "summaries": []}
    if process.returncode != 0:
        return {
            "source": str(task.source),
            "error": f"AST worker 返回 {process.returncode}: {process.stderr[-2000:]}",
            "summaries": [],
        }
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        return {
            "source": str(task.source),
            "error": f"AST worker 输出无效：{exc}: {process.stdout[-1000:]}",
            "summaries": [],
        }


def worker_main() -> int:
    try:
        value = json.loads(sys.stdin.read())
        task = ParseTask(
            Path(value["source"]), Path(value["directory"]), tuple(value["arguments"])
        )
        sys.stdout.write(json.dumps(analyze_task(task), ensure_ascii=False, separators=(",", ":")))
        return 0
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"worker error: {exc}", file=sys.stderr)
        return 1


def solve_summaries(summaries: dict[str, dict]) -> None:
    for summary in summaries.values():
        summary["possible_codes"] = sorted({
            code for path in summary["return_paths"] for code in path["codes"]
        })
        summary["complete"] = False
    for _ in range(len(summaries) + 1):
        changed = False
        for summary in summaries.values():
            codes = set(summary["possible_codes"])
            complete = bool(summary["return_paths"])
            for path in summary["return_paths"]:
                path_complete = not path["unknown"]
                for callee in path["callees"]:
                    callee_summary = summaries.get(callee)
                    if callee_summary is None or not callee_summary["complete"]:
                        path_complete = False
                    elif callee_summary is not None:
                        codes.update(callee_summary["possible_codes"])
                if not path["codes"] and not path["callees"]:
                    path_complete = False
                complete = complete and path_complete
            new_codes = sorted(codes)
            if new_codes != summary["possible_codes"] or complete != summary["complete"]:
                summary["possible_codes"] = new_codes
                summary["complete"] = complete
                changed = True
        if not changed:
            break


def candidate_evidence(entry: dict, callsites: dict[tuple[str, int], list[dict]],
                       summaries: dict[str, dict], definitions: dict[str, int]) -> dict:
    source_root = Path(entry["_source_root"])
    file = str((source_root / entry["file"]).resolve())
    sites = [
        site for line in range(entry["line"], entry.get("statement_end_line", entry["line"]) + 1)
        for site in callsites.get((file, line), [])
    ]
    unique_sites = {(site["callee_usr"], site["line"], site["column"]): site for site in sites}
    sites = list(unique_sites.values())
    possible: set[str] = set()
    complete = bool(sites)
    rendered_sites: list[dict] = []
    for site in sites:
        summary = summaries.get(site["callee_usr"])
        if summary is None:
            complete = False
            rendered_sites.append({**site, "complete": False, "possible_codes": []})
            continue
        possible.update(summary["possible_codes"])
        complete = complete and summary["complete"]
        rendered_sites.append({
            "callee": site["callee"],
            "line": site["line"],
            "column": site["column"],
            "complete": summary["complete"],
            "possible_codes": summary["possible_codes"],
        })
    nonzero = sorted(
        (code for code in possible if definitions.get(code) not in {None, 0}),
        key=lambda code: definitions[code],
    )
    auto = nonzero[0] if complete and len(nonzero) == 1 else None
    return {
        "candidate_id": entry["candidate_id"],
        "group_id": entry["group_id"],
        "complete": complete,
        "possible_codes": sorted(possible, key=lambda code: definitions.get(code, 1 << 30)),
        "auto_error_code": auto,
        "auto_error_code_value": definitions.get(auto) if auto else None,
        "calls": rendered_sites,
        "reason": "complete_singleton" if auto else "no_status_call_at_site" if not sites else "incomplete_or_non_singleton",
    }


def build_result(runtime: dict, task_results: list[dict], source_root: Path,
                 compile_database: Path) -> dict:
    summaries: dict[str, dict] = {}
    failures: list[dict] = []
    for result in task_results:
        if result["error"]:
            failures.append({"source": result["source"], "error": result["error"]})
        for summary in result["summaries"]:
            summaries.setdefault(summary["usr"], summary)
    solve_summaries(summaries)
    callsites: dict[tuple[str, int], list[dict]] = {}
    for summary in summaries.values():
        for site in summary["callsites"]:
            callsites.setdefault((site["file"], site["line"]), []).append(site)
    definitions = runtime.get("error_definitions", {})
    semantic_entries = []
    for entry in runtime.get("entries", []):
        if entry.get("analysis_lane") != "semantic":
            continue
        enriched = dict(entry)
        enriched["_source_root"] = str(source_root)
        semantic_entries.append(enriched)
    entry_results = [
        candidate_evidence(entry, callsites, summaries, definitions)
        for entry in semantic_entries
    ]
    evidence_by_candidate = {entry["candidate_id"]: entry for entry in entry_results}
    group_results: list[dict] = []
    for group in runtime.get("groups", []):
        if group.get("analysis_lane") != "semantic":
            continue
        evidence = [evidence_by_candidate[candidate_id] for candidate_id in group["candidate_ids"]]
        autos = {item["auto_error_code"] for item in evidence}
        auto = next(iter(autos)) if len(autos) == 1 and None not in autos else None
        group_results.append({
            "group_id": group["group_id"],
            "content_hash": group["content_hash"],
            "complete": all(item["complete"] for item in evidence),
            "auto_error_code": auto,
            "auto_error_code_value": definitions.get(auto) if auto else None,
            "candidate_evidence": evidence,
        })
    return {
        "schema_version": 1,
        "generator": "analyze_kvcache_status_ast.py",
        "source_root": str(source_root),
        "runtime_scan_fingerprint": runtime.get("scan_fingerprint"),
        "compile_database": str(compile_database),
        "translation_units_total": len(task_results),
        "translation_units_failed": len(failures),
        "failures": failures,
        "function_summary_total": len(summaries),
        "semantic_group_total": len(group_results),
        "auto_resolved_group_total": sum(item["auto_error_code"] is not None for item in group_results),
        "groups": group_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="使用 libclang AST 自动归纳 kvcache 动态 Status 错误码")
    parser.add_argument("source", type=Path, help="yuanrong-datasystem 仓库根")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--compile-database", type=Path)
    parser.add_argument("--clang", default="clang++")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 4))
    parser.add_argument("--timeout", type=int, default=300, help="单个 TU AST 分析超时秒数")
    parser.add_argument("--max-files", type=int, default=0, help="仅用于抽样验证；0 表示全部")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        root = args.source.expanduser().resolve()
        source_root = root / "src/datasystem"
        runtime = read_json(args.runtime.expanduser().resolve())
        if not isinstance(runtime, dict) or runtime.get("schema_version", 0) < 5:
            raise ValueError("runtime JSON 必须是 schema_version=5")
        compile_database = find_compile_database(root, args.compile_database)
        database = read_json(compile_database)
        if not isinstance(database, list):
            raise ValueError("compile_commands.json 顶层必须是数组")
        wanted = {
            (source_root / entry["file"]).resolve()
            for entry in runtime.get("entries", [])
            if entry.get("analysis_lane") == "semantic" and Path(entry["file"]).suffix.lower() in CPP_SUFFIXES
        }
        tasks = compile_tasks(database, wanted, compiler_resource_dir(args.clang))
        if args.max_files > 0:
            tasks = tasks[:args.max_files]
        task_results: list[dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
            futures = {
                executor.submit(analyze_task_subprocess, task, args.timeout): task
                for task in tasks
            }
            for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                result = future.result()
                task_results.append(result)
                print(
                    f"[{completed}/{len(tasks)}] AST完成：{Path(result['source']).name}"
                    + ("（有诊断）" if result.get("error") else ""),
                    file=sys.stderr,
                )
        result = build_result(runtime, task_results, source_root, compile_database)
        output = args.output.expanduser().resolve()
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    print(
        f"AST分析 {result['translation_units_total']} 个TU，函数摘要 {result['function_summary_total']}，"
        f"自动唯一归码 {result['auto_resolved_group_total']}/{result['semantic_group_total']}，输出 {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(worker_main() if sys.argv[1:] == ["--worker"] else main())
