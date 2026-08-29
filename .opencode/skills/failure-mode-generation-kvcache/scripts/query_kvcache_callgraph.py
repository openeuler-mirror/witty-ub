#!/usr/bin/env python3
"""Emit a candidate-local slice of the full kvcache call graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path


DEFAULT_GRAPH = Path("/tmp/kvcache_callchains.json")
DEFAULT_RUNTIME = Path("/tmp/kvcache_runtime_err.json")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value


def callable_suffix(callable_signature: str | None, fallback: str | None) -> str | None:
    if callable_signature:
        prefix = callable_signature.split("(", 1)[0]
        match = re.search(r"((?:[A-Za-z_~][A-Za-z0-9_~]*::)*[A-Za-z_~][A-Za-z0-9_~]*)\s*$", prefix)
        if match is not None:
            return match.group(1)
    return fallback


def function_match_index(functions: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    by_bare: dict[str, list[str]] = {}
    by_suffix: dict[str, list[str]] = {}
    for function in functions:
        name = function["qualified_name"]
        by_bare.setdefault(function.get("function_name", ""), []).append(name)
        parts = name.split("::")
        for start in range(len(parts)):
            by_suffix.setdefault("::".join(parts[start:]), []).append(name)
    return by_bare, by_suffix


def matches_for_group(
    group: dict,
    match_index: tuple[dict[str, list[str]], dict[str, list[str]]],
) -> list[str]:
    suffix = callable_suffix(group.get("callable"), group.get("function"))
    if not suffix:
        return []
    by_bare, by_suffix = match_index
    if "::" in suffix:
        exact_suffix = by_suffix.get(suffix, [])
        if exact_suffix:
            return list(exact_suffix)
    return list(by_bare.get(group.get("function", ""), []))


def graph_indexes(callgraph: dict) -> tuple[dict[str, dict], dict[str, set[str]], dict[str, set[str]], dict[tuple[str, str], str]]:
    functions = {item["qualified_name"]: item for item in callgraph.get("functions", [])}
    callers = {name: set(item.get("callers", [])) for name, item in functions.items()}
    callees = {name: set(item.get("callees", [])) for name, item in functions.items()}
    kinds = {
        (edge["caller"], edge["callee"]): edge.get("kind", "direct")
        for edge in callgraph.get("edges", [])
    }
    return functions, callers, callees, kinds


def traverse(roots: set[str], adjacency: dict[str, set[str]], depth: int) -> set[str]:
    visited = set(roots)
    queue = deque((root, 0) for root in roots)
    while queue:
        node, level = queue.popleft()
        if level >= depth:
            continue
        for neighbor in adjacency.get(node, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, level + 1))
    return visited


def select_groups(runtime: dict, group_ids: list[str], batch: Path | None) -> list[dict]:
    if batch is not None:
        value = read_json(batch)
        groups = value.get("groups")
        if not isinstance(groups, list):
            raise ValueError(f"批次缺少 groups：{batch}")
        return groups
    groups_by_id = {group["group_id"]: group for group in runtime.get("groups", [])}
    missing = [group_id for group_id in group_ids if group_id not in groups_by_id]
    if missing:
        raise ValueError("未知 group_id：" + ", ".join(missing))
    return [groups_by_id[group_id] for group_id in group_ids]


def build_slice(callgraph: dict, runtime: dict, groups: list[dict], depth: int,
                direction: str) -> dict:
    functions, callers, callees, kinds = graph_indexes(callgraph)
    all_function_records = list(functions.values())
    match_index = function_match_index(all_function_records)
    group_matches = {
        group["group_id"]: matches_for_group(group, match_index)
        for group in groups
    }
    roots = {name for matches in group_matches.values() for name in matches}
    selected = set(roots)
    if direction in {"callers", "both"}:
        selected.update(traverse(roots, callers, depth))
    if direction in {"callees", "both"}:
        selected.update(traverse(roots, callees, depth))

    runtime_groups_by_function: dict[str, list[str]] = {}
    for group in runtime.get("groups", []):
        for name in matches_for_group(group, match_index):
            if name in selected:
                runtime_groups_by_function.setdefault(name, []).append(group["group_id"])

    edges: list[dict] = []
    for caller in sorted(selected):
        for callee in sorted(callees.get(caller, set()) & selected):
            edges.append({
                "caller": caller,
                "callee": callee,
                "kind": kinds.get((caller, callee), "direct"),
            })
    return {
        "schema_version": 1,
        "source_fingerprint": callgraph.get("source_fingerprint"),
        "runtime_scan_fingerprint": runtime.get("scan_fingerprint"),
        "depth": depth,
        "direction": direction,
        "requested_groups": [group["group_id"] for group in groups],
        "root_matches": [
            {
                "group_id": group["group_id"],
                "callable": group.get("callable"),
                "matches": group_matches[group["group_id"]],
                "ambiguous": len(group_matches[group["group_id"]]) != 1,
            }
            for group in groups
        ],
        "function_count": len(selected),
        "edge_count": len(edges),
        "functions": [
            {
                "qualified_name": name,
                "entry": functions[name].get("entry", False),
                "failure_group_ids": sorted(runtime_groups_by_function.get(name, [])),
            }
            for name in sorted(selected)
        ],
        "edges": edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按 runtime group 查询局部 kvcache 调用图")
    parser.add_argument("--callgraph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--group-id", action="append", default=[])
    selector.add_argument("--batch", type=Path)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--direction", choices=("callers", "callees", "both"), default="callers")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    if args.depth < 0:
        parser.error("--depth 不能小于 0")
    try:
        callgraph = read_json(args.callgraph.expanduser().resolve())
        runtime = read_json(args.runtime.expanduser().resolve())
        groups = select_groups(runtime, args.group_id, args.batch.expanduser().resolve() if args.batch else None)
        result = build_slice(callgraph, runtime, groups, args.depth, args.direction)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.expanduser().resolve().write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
