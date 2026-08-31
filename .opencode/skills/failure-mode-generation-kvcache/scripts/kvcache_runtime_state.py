#!/usr/bin/env python3
"""Content-addressed JSONL checkpoints for kvcache runtime group analysis."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


SCHEMA_VERSION = 1
HEADER_KIND = "witty-kvcache-runtime-state"
DEFAULT_RUNTIME = Path("/tmp/kvcache_runtime_err.json")
DEFAULT_STATE = Path("/tmp/kvcache_runtime_state.jsonl")
TERMINAL_STATES = {"resolved", "excluded"}
VALID_STATES = {"pending", "resolved", "excluded", "needs_review"}


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value


def read_state(path: Path) -> tuple[dict | None, list[dict]]:
    if not path.is_file():
        return None, []
    header: dict | None = None
    records: list[dict] = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if header is None:
                header = value
            else:
                records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"状态文件损坏 {path}:{number}: {exc}") from exc
    if header is not None and header.get("kind") != HEADER_KIND:
        raise ValueError(f"状态文件类型错误：{path}")
    return header, records


def write_state(path: Path, header: dict, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            for value in [header, *records]:
                stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_runtime(runtime: dict) -> list[dict]:
    if runtime.get("schema_version", 0) < 5 or not isinstance(runtime.get("groups"), list):
        raise ValueError("runtime JSON 缺少 schema_version=5 groups，请重新运行扫描脚本")
    groups = runtime["groups"]
    if any(not group.get("content_hash") for group in groups):
        raise ValueError("runtime groups 缺少 content_hash，请重新运行当前版本扫描脚本")
    return groups


def initialize(runtime: dict, old_records: list[dict]) -> tuple[list[dict], int]:
    groups = validate_runtime(runtime)
    reusable_by_hash: dict[str, list[dict]] = {}
    for record in old_records:
        if record.get("state") in TERMINAL_STATES:
            reusable_by_hash.setdefault(record.get("content_hash", ""), []).append(record)
    new_hash_counts = Counter(group["content_hash"] for group in groups)
    reused = 0
    records: list[dict] = []
    for group in groups:
        matches = reusable_by_hash.get(group["content_hash"], [])
        # Reuse only a one-to-one content match. Duplicate content hashes are
        # deliberately re-queued because their output identity may be ambiguous.
        reusable = len(matches) == 1 and new_hash_counts[group["content_hash"]] == 1
        state = matches[0]["state"] if reusable else (
            "excluded" if group["analysis_lane"] == "excluded_infrastructure" else "pending"
        )
        result = matches[0].get("result") if reusable else None
        reused += int(reusable)
        record = {
            "group_id": group["group_id"],
            "content_hash": group["content_hash"],
            "callable_key": group["callable_key"],
            "analysis_lane": group["analysis_lane"],
            "state": state,
        }
        if result is not None:
            record["result"] = result
        records.append(record)
    return records, reused


def state_header(runtime: dict) -> dict:
    return {
        "kind": HEADER_KIND,
        "schema_version": SCHEMA_VERSION,
        "source_root": runtime.get("source_root"),
        "scan_fingerprint": runtime.get("scan_fingerprint"),
        "group_total": runtime.get("group_total"),
    }


def command_init(args: argparse.Namespace) -> int:
    runtime = read_json(args.runtime)
    _, old_records = read_state(args.state)
    records, reused = initialize(runtime, old_records)
    write_state(args.state, state_header(runtime), records)
    print(f"state initialized: {len(records)} groups, reused {reused}, pending {sum(r['state'] == 'pending' for r in records)}")
    return 0


def load_current(args: argparse.Namespace) -> tuple[dict, dict, list[dict]]:
    runtime = read_json(args.runtime)
    header, records = read_state(args.state)
    if header is None:
        raise ValueError("状态文件不存在，请先运行 init")
    if header.get("scan_fingerprint") != runtime.get("scan_fingerprint"):
        raise ValueError("状态文件与当前扫描 fingerprint 不一致，请重新运行 init")
    return runtime, header, records


def command_status(args: argparse.Namespace) -> int:
    _, _, records = load_current(args)
    counts = Counter(record["state"] for record in records)
    print(json.dumps({state: counts.get(state, 0) for state in sorted(VALID_STATES)}, ensure_ascii=False))
    return 0 if not counts.get("pending") and not counts.get("needs_review") else 2


def command_take(args: argparse.Namespace) -> int:
    runtime, _, records = load_current(args)
    pending_ids = {
        record["group_id"] for record in records
        if record["state"] in {"pending", "needs_review"}
        and (args.lane == "all" or record["analysis_lane"] == args.lane)
    }
    groups_by_id = {group["group_id"]: group for group in runtime["groups"]}
    selected: list[dict] = []
    selected_callables: set[str] = set()
    for record in records:
        if record["group_id"] not in pending_ids:
            continue
        callable_key = record["callable_key"]
        if selected and callable_key not in selected_callables and len(selected) >= args.target_groups:
            break
        selected_callables.add(callable_key)
        selected.extend(
            groups_by_id[item["group_id"]]
            for item in records
            if item["group_id"] in pending_ids and item["callable_key"] == callable_key
            and item["group_id"] not in {group["group_id"] for group in selected}
        )
    print(json.dumps({
        "scan_fingerprint": runtime.get("scan_fingerprint"),
        "group_count": len(selected),
        "groups": selected,
    }, ensure_ascii=False, indent=2))
    return 0


def command_record(args: argparse.Namespace) -> int:
    runtime, header, records = load_current(args)
    matching = [record for record in records if record["group_id"] == args.group_id]
    if len(matching) != 1:
        raise ValueError(f"未知或重复 group_id：{args.group_id}")
    record = matching[0]
    record["state"] = args.state_value
    if args.result is not None:
        record["result"] = read_json(args.result)
    elif args.state_value in TERMINAL_STATES and "result" not in record:
        record["result"] = {"recorded": True}
    write_state(args.state, header, records)
    print(f"recorded {args.group_id}: {args.state_value} ({runtime.get('scan_fingerprint')})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="kvcache runtime 分析 JSONL checkpoint")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init").set_defaults(func=command_init)
    commands.add_parser("status").set_defaults(func=command_status)
    take = commands.add_parser("take")
    take.add_argument("--lane", choices=("all", "deterministic", "semantic"), default="semantic")
    take.add_argument("--target-groups", type=int, default=30)
    take.set_defaults(func=command_take)
    record = commands.add_parser("record")
    record.add_argument("group_id")
    record.add_argument("state_value", choices=sorted(VALID_STATES - {"pending"}))
    record.add_argument("--result", type=Path)
    record.set_defaults(func=command_record)
    args = parser.parse_args()
    args.runtime = args.runtime.expanduser().resolve()
    args.state = args.state.expanduser().resolve()
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
