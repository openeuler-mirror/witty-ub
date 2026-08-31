#!/usr/bin/env python3
"""Deterministic completeness checks for the kvcache generation pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


NO_STABLE_KEYWORD_PHENOMENON = "无稳定关键字（按文件名、函数名和ERROR/FATAL级别定位）"
LOG_MATCH_KEY = "日志匹配"


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc


def validate_runtime(runtime: dict) -> list[str]:
    errors: list[str] = []
    entries = runtime.get("entries", [])
    groups = runtime.get("groups", [])
    if runtime.get("schema_version") != 5:
        errors.append("runtime schema_version 必须为 5")
    if runtime.get("total") != len(entries):
        errors.append("runtime total 与 entries 数量不一致")
    candidate_ids = [entry.get("candidate_id") for entry in entries]
    group_ids = [group.get("group_id") for group in groups]
    if len(set(candidate_ids)) != len(candidate_ids) or None in candidate_ids:
        errors.append("candidate_id 缺失或重复")
    if len(set(group_ids)) != len(group_ids) or None in group_ids:
        errors.append("group_id 缺失或重复")
    if runtime.get("group_total") != len(groups):
        errors.append("group_total 与 groups 数量不一致")
    if sum(group.get("candidate_count", -1) for group in groups) != len(entries):
        errors.append("group candidate_count 总和与 entries 不一致")
    grouped_candidates = [candidate for group in groups for candidate in group.get("candidate_ids", [])]
    if Counter(grouped_candidates) != Counter(candidate_ids):
        errors.append("物理候选未被 groups 恰好覆盖一次")
    entries_by_id = {entry.get("candidate_id"): entry for entry in entries}
    for group in groups:
        if not group.get("content_hash"):
            errors.append(f"{group.get('group_id')} 缺少 content_hash")
        tasks = {task.get("task") for task in group.get("skill_analysis", [])}
        if group.get("template_confidence") == "dynamic_only" and \
                group.get("analysis_lane") != "excluded_infrastructure":
            if "resolve_log_template" not in tasks:
                errors.append(f"{group.get('group_id')} dynamic_only 缺少 resolve_log_template 任务")
            if not group.get("need_skill") or group.get("analysis_lane") != "semantic":
                errors.append(f"{group.get('group_id')} dynamic_only 未进入 semantic lane")
        for candidate_id in group.get("candidate_ids", []):
            if entries_by_id.get(candidate_id, {}).get("group_id") != group.get("group_id"):
                errors.append(f"{candidate_id} 的 entry/group 归属不一致")
    expected_lanes = {
        lane: sum(group.get("analysis_lane") == lane for group in groups)
        for lane in ("deterministic", "semantic", "excluded_infrastructure")
    }
    if runtime.get("lane_totals") != expected_lanes:
        errors.append("lane_totals 不一致")
    return errors


def validate_batches(runtime: dict, directory: Path) -> list[str]:
    errors: list[str] = []
    manifest = read_json(directory / "manifest.json")
    if manifest.get("scan_fingerprint") != runtime.get("scan_fingerprint"):
        errors.append("batch manifest fingerprint 与 runtime 不一致")
    expected = {
        group["group_id"] for group in runtime["groups"]
        if group.get("analysis_lane") == manifest.get("lane") or manifest.get("lane") == "all"
    }
    seen: list[str] = []
    callable_batches: dict[str, set[str]] = {}
    for name in manifest.get("batches", []):
        batch = read_json(directory / name)
        if batch.get("scan_fingerprint") != runtime.get("scan_fingerprint"):
            errors.append(f"{name} fingerprint 不一致")
        for group in batch.get("groups", []):
            seen.append(group["group_id"])
            callable_batches.setdefault(group["callable_key"], set()).add(name)
    if Counter(seen) != Counter(expected):
        errors.append("batch 未恰好覆盖目标 lane groups")
    split = [key for key, names in callable_batches.items() if len(names) > 1]
    if split:
        errors.append(f"同一 callable 跨批：{split[:5]}")
    return errors


def read_state(path: Path) -> tuple[dict, list[dict]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not values:
        raise ValueError(f"状态文件为空：{path}")
    return values[0], values[1:]


def validate_state(runtime: dict, path: Path, require_complete: bool) -> list[str]:
    errors: list[str] = []
    header, records = read_state(path)
    if header.get("scan_fingerprint") != runtime.get("scan_fingerprint"):
        errors.append("state fingerprint 与 runtime 不一致")
    groups = {group["group_id"]: group for group in runtime["groups"]}
    if Counter(record.get("group_id") for record in records) != Counter(groups.keys()):
        errors.append("state 未恰好覆盖 runtime groups")
    for record in records:
        group = groups.get(record.get("group_id"))
        if group and record.get("content_hash") != group.get("content_hash"):
            errors.append(f"state content_hash 不一致：{record.get('group_id')}")
        if require_complete and record.get("state") not in {"resolved", "excluded"}:
            errors.append(f"state 未完成：{record.get('group_id')}={record.get('state')}")
        tasks = {task.get("task") for task in (group or {}).get("skill_analysis", [])}
        if "resolve_log_template" in tasks and record.get("state") == "resolved":
            result = record.get("result")
            analysis = result.get("log_template") if isinstance(result, dict) else None
            if not isinstance(analysis, dict):
                errors.append(f"state 缺少日志模板分析：{record.get('group_id')}")
                continue
            literals = analysis.get("stable_literals")
            evidence = analysis.get("evidence")
            if not isinstance(literals, list) or not all(isinstance(item, str) and item for item in literals):
                errors.append(f"日志模板 stable_literals 无效：{record.get('group_id')}")
            if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item for item in evidence):
                errors.append(f"日志模板缺少源码证据：{record.get('group_id')}")
            if isinstance(literals, list) and literals:
                if not isinstance(analysis.get("normalized_template"), str) or not analysis["normalized_template"]:
                    errors.append(f"日志模板 normalized_template 缺失：{record.get('group_id')}")
                if analysis.get("match_enabled") is False:
                    errors.append(f"有稳定关键字却禁用匹配：{record.get('group_id')}")
            elif analysis.get("match_enabled") is not False or not isinstance(analysis.get("reason"), str) or \
                    not analysis["reason"].strip():
                errors.append(f"无稳定关键字未显式禁用并说明原因：{record.get('group_id')}")
    return errors


def validate_ast(runtime: dict, ast_result: dict) -> list[str]:
    errors: list[str] = []
    if ast_result.get("runtime_scan_fingerprint") != runtime.get("scan_fingerprint"):
        errors.append("AST fingerprint 与 runtime 不一致")
    groups = {group["group_id"]: group for group in runtime["groups"]}
    for evidence in ast_result.get("groups", []):
        group = groups.get(evidence.get("group_id"))
        if group is None or group.get("analysis_lane") != "semantic":
            errors.append(f"AST 引用未知或非 semantic group：{evidence.get('group_id')}")
        elif evidence.get("content_hash") != group.get("content_hash"):
            errors.append(f"AST content_hash 不一致：{evidence.get('group_id')}")
        if evidence.get("auto_error_code") and not evidence.get("complete"):
            errors.append(f"AST 不完整组错误地自动归码：{evidence.get('group_id')}")
    return errors


def validate_callgraph(callgraph: dict) -> list[str]:
    errors: list[str] = []
    if callgraph.get("schema_version") != 2:
        errors.append("callgraph schema_version 必须为 2")
    if not callgraph.get("analysis", {}).get("complete"):
        errors.append("callgraph analysis.complete 不为 true")
    if callgraph.get("edge_count") != len(callgraph.get("edges", [])):
        errors.append("callgraph edge_count 不一致")
    if callgraph.get("function_count") != len(callgraph.get("functions", [])):
        errors.append("callgraph function_count 不一致")
    return errors


def validate_final(nodes: list[dict], tree: dict) -> list[str]:
    errors: list[str] = []
    ids = [node.get("故障编号") for node in nodes]
    if len(set(ids)) != len(ids) or None in ids:
        errors.append("最终节点编号缺失或重复")
    for prefix, kind in (("kvcache_access_", "access_log_entry"), ("kvcache_runtime_", "runtime_log")):
        numbers = [int(match.group(1)) for node in nodes if node.get("节点类型") == kind
                   if (match := re.fullmatch(re.escape(prefix) + r"(\d+)", node.get("故障编号", "")))]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{kind} 编号不连续或顺序错误")
    expected_partial_success_condition = {"status_code": 0, "resp_msg_nonempty": True}
    conditional_nodes = [node for node in nodes if "匹配条件" in node]
    if len(conditional_nodes) != 1 or conditional_nodes[0].get("节点类型") != "access_log_entry" or \
            conditional_nodes[0].get("匹配条件") != expected_partial_success_condition:
        errors.append("code=0 + respMsg 非空根的匹配条件缺失、重复或无效")
    elif conditional_nodes[0].get("错误码") != "K_OK(0)":
        errors.append("code=0 + respMsg 非空根的错误码必须为 K_OK(0)")
    k_ok_nodes = [node for node in nodes if node.get("错误码") == "K_OK(0)"]
    if len(k_ok_nodes) != 1 or len(conditional_nodes) != 1 or k_ok_nodes[0] is not conditional_nodes[0]:
        errors.append("仅 code=0 + respMsg 非空根可使用 K_OK(0)")
    runtime_nodes = [node for node in nodes if node.get("节点类型") == "runtime_log"]
    runtime_names = [node.get("故障名称") for node in runtime_nodes]
    duplicates = [name for name, count in Counter(runtime_names).items() if name is not None and count > 1]
    if duplicates:
        errors.append(f"runtime 故障名称重复：{duplicates[:5]}")
    for node in runtime_nodes:
        node_id = node.get("故障编号")
        name = node.get("故障名称")
        if not isinstance(name, str) or not name or len(name) > 20 or "时" not in name or "运行操作时" in name:
            errors.append(f"runtime 故障名称不符合“具体操作时原因”或超过20字：{node_id}")
        cause = node.get("故障原因")
        if not isinstance(cause, str) or not cause.endswith("。") or len(re.findall(r"[。！？!?]", cause)) != 1:
            errors.append(f"runtime 故障原因不是完整单句：{node_id}")
    for node in nodes:
        phenomenon = node.get("故障现象")
        match_config = node.get(LOG_MATCH_KEY)
        if phenomenon == NO_STABLE_KEYWORD_PHENOMENON:
            if node.get("节点类型") != "runtime_log" or not isinstance(match_config, dict) or \
                    match_config.get("enabled") is not False or not isinstance(match_config.get("reason"), str) or \
                    not match_config["reason"].strip():
                errors.append(f"无稳定关键字节点未显式禁用日志匹配：{node.get('故障编号')}")
        elif match_config is not None:
            errors.append(f"仅无稳定关键字 runtime 节点可设置日志匹配：{node.get('故障编号')}")
        elif node.get("节点类型") == "runtime_log" and not re.fullmatch(
                r"依次匹配`[^`]+`(?:、`[^`]+`)*", phenomenon or "", re.S):
            errors.append(f"runtime 故障现象不符合依次匹配关键字格式：{node.get('故障编号')}")
    graph = tree.get("kvcache")
    if not isinstance(graph, dict) or list(graph) != ids:
        errors.append("tree.kvcache key 未按节点数组完整覆盖")
        return errors
    known_tree_ids = {
        node_id
        for module in tree.values()
        if isinstance(module, dict)
        for node_id in module
    }
    inbound = Counter(child for children in graph.values() for child in children)
    for parent, children in graph.items():
        if not isinstance(children, list) or len(children) != len(set(children)):
            errors.append(f"tree value 非数组或有重复：{parent}")
            continue
        for child in children:
            if child not in known_tree_ids or child == parent:
                errors.append(f"tree 引用无效或自引用：{parent}->{child}")
    for node in nodes:
        if node.get("节点类型") == "runtime_log" and not inbound[node["故障编号"]]:
            errors.append(f"runtime 节点无父：{node['故障编号']}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        cyclic = any(visit(child) for child in graph.get(node, []))
        visiting.remove(node)
        visited.add(node)
        return cyclic

    if any(visit(node) for node in graph):
        errors.append("tree.kvcache 存在环")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 kvcache 生成流水线")
    parser.add_argument("--runtime", type=Path, default=Path("/tmp/kvcache_runtime_err.json"))
    parser.add_argument("--batches", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--ast", type=Path)
    parser.add_argument("--callgraph", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--nodes", type=Path)
    parser.add_argument("--tree", type=Path)
    args = parser.parse_args()
    try:
        runtime = read_json(args.runtime)
        errors = validate_runtime(runtime)
        if args.batches:
            errors.extend(validate_batches(runtime, args.batches))
        if args.state:
            errors.extend(validate_state(runtime, args.state, args.require_complete))
        if args.ast:
            errors.extend(validate_ast(runtime, read_json(args.ast)))
        if args.callgraph:
            errors.extend(validate_callgraph(read_json(args.callgraph)))
        if bool(args.nodes) != bool(args.tree):
            raise ValueError("--nodes 和 --tree 必须同时提供")
        if args.nodes:
            errors.extend(validate_final(read_json(args.nodes), read_json(args.tree)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print("FAIL: " + error)
        return 1
    print("OK: kvcache pipeline invariants passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
