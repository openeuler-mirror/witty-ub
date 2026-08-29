#!/usr/bin/env python3
"""Create callable-local batches from kvcache runtime candidate groups."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SCHEMA_VERSION = 1
MANIFEST_KIND = "witty-kvcache-runtime-batches"
DEFAULT_RUNTIME = Path("/tmp/kvcache_runtime_err.json")
DEFAULT_OUTPUT_DIR = Path("/tmp/kvcache_runtime_batches")


def read_runtime(path: Path) -> dict:
    try:
        runtime = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 runtime JSON {path}: {exc}") from exc
    if runtime.get("schema_version", 0) < 5 or not isinstance(runtime.get("groups"), list):
        raise ValueError("runtime JSON 不含 schema_version=5 的 groups；请先重跑 find_kvcache_runtime_err.py")
    return runtime


def selected_groups(runtime: dict, lane: str) -> list[dict]:
    groups = runtime["groups"]
    return groups if lane == "all" else [group for group in groups if group.get("analysis_lane") == lane]


def group_by_callable(groups: list[dict]) -> list[list[dict]]:
    order: list[str] = []
    by_callable: dict[str, list[dict]] = {}
    for group in groups:
        key = group.get("callable_key") or f"{group.get('file')}::{group.get('callable_start_line')}"
        if key not in by_callable:
            order.append(key)
            by_callable[key] = []
        by_callable[key].append(group)
    return [by_callable[key] for key in order]


def make_batches(callables: list[list[dict]], target_groups: int) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    for callable_groups in callables:
        if current and len(current) + len(callable_groups) > target_groups:
            batches.append(current)
            current = []
        current.extend(callable_groups)
        if len(current) >= target_groups:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    return batches


def initialize_output(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    existing = list(directory.iterdir())
    if not existing:
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"输出目录非空且没有有效 manifest，拒绝覆盖：{directory}") from exc
    if manifest.get("kind") != MANIFEST_KIND:
        raise ValueError(f"输出目录不属于本脚本，拒绝覆盖：{directory}")
    for path in directory.glob("batch-*.json"):
        path.unlink()


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_batch(runtime: dict, groups: list[dict], index: int, lane: str,
                entries_by_id: dict[str, dict]) -> dict:
    hydrated_groups: list[dict] = []
    for group in groups:
        hydrated = dict(group)
        hydrated["entries"] = [entries_by_id[candidate_id] for candidate_id in group["candidate_ids"]]
        hydrated_groups.append(hydrated)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "source_root": runtime.get("source_root"),
        "scan_fingerprint": runtime.get("scan_fingerprint"),
        "lane": lane,
        "batch_index": index,
        "group_count": len(groups),
        "candidate_count": sum(group["candidate_count"] for group in groups),
        "groups": hydrated_groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按 callable 生成 kvcache runtime 分析批次")
    parser.add_argument("runtime", nargs="?", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--lane", choices=("all", "deterministic", "semantic", "excluded_infrastructure"),
        default="semantic", help="默认只生成需要语义分析的批次",
    )
    parser.add_argument("--target-groups", type=int, default=30,
                        help="每批目标聚合组数；同一 callable 永不拆批")
    args = parser.parse_args()
    if args.target_groups < 1:
        parser.error("--target-groups 必须大于 0")
    try:
        runtime = read_runtime(args.runtime.expanduser().resolve())
        groups = selected_groups(runtime, args.lane)
        callables = group_by_callable(groups)
        batches = make_batches(callables, args.target_groups)
        output_dir = args.output_dir.expanduser().resolve()
        initialize_output(output_dir)
        entries_by_id = {entry["candidate_id"]: entry for entry in runtime["entries"]}
        batch_files: list[str] = []
        for index, batch_groups in enumerate(batches, start=1):
            name = f"batch-{index:04d}.json"
            write_json_atomic(
                output_dir / name,
                build_batch(runtime, batch_groups, index, args.lane, entries_by_id),
            )
            batch_files.append(name)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "kind": MANIFEST_KIND,
            "source_root": runtime.get("source_root"),
            "scan_fingerprint": runtime.get("scan_fingerprint"),
            "lane": args.lane,
            "target_groups": args.target_groups,
            "group_count": len(groups),
            "candidate_count": sum(group["candidate_count"] for group in groups),
            "callable_count": len(callables),
            "batch_count": len(batches),
            "batches": batch_files,
        }
        write_json_atomic(output_dir / "manifest.json", manifest)
    except (KeyError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    print(
        f"生成 {len(batches)} 个批次：{len(groups)} 个聚合组，"
        f"{sum(group['candidate_count'] for group in groups)} 个物理点，输出 {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
