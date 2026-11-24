#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KVCache 日志清洗脚本（按故障 trace 裁剪 + 丢弃 ubse 日志）。

背景
----
输入目录的每一个「一级子目录」表示一个案例（case）。每个案例内有若干按节点
划分的子目录（如 ``*-data-worker1`` / ``*-kvclient-1``），其中存放 worker 与
client 的运行日志和接口（访问）日志：

    <case>/
    ├── <node>-data-worker<N>/
    │   ├── kvcache.INFO.log            # worker 运行日志
    │   └── access.log                  # worker 接口日志
    └── <node>-kvclient-<N>/
        ├── ds_client_<pid>.INFO.log    # client 运行日志
        └── ds_client_access_<pid>.log  # client 接口日志

清洗规则
--------
1) 故障 trace 识别：扫描案例内所有 client 接口日志（``ds_client_access*.log``），
   逐行按 ``|`` 解析，满足以下条件的 trace 记为故障 trace：
       - action（第 9 个字段）∈ {"DS_KV_CLIENT_GET", "DS_OBJECT_CLIENT_GET", "DS_KV_CLIENT_SET"}
       - 且存在故障：status_code（第 8 个字段）非 0，或 cost（第 10 个字段）> 阈值（默认 2.5ms=2500us）
   仅统计 trace_id（第 6 个字段）非空的行。
2) 若案例没有任何故障 trace → 整个案例丢弃（输出中不出现该案例）。
3) 对保留的案例：
   - 核心 4 类日志（worker/client 的运行日志与接口日志）只保留属于故障 trace 的行；
   - 其余文件按原样全量采集；
   - 文件名中（忽略大小写）含 ``ubse`` 的文件一律丢弃；
   - 过滤后无命中行的日志仍写出空文件，保持目录结构完整。

用法
----
    python clean_kvcache_logs.py <src_folder>            # 输出到同级 <src_folder>_cleaned
    python clean_kvcache_logs.py <src_folder> -o OUT     # 指定输出目录
    python clean_kvcache_logs.py <src_folder> --dry-run  # 只统计，不落盘
    python clean_kvcache_logs.py <src_folder> --cost-us 3000   # 自定义 cost 阈值（单位 us）
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

# ────────────────────────── 规则配置 ──────────────────────────
# 触发故障判定的 client 接口 action
FAULT_ACTIONS = {"DS_KV_CLIENT_GET", "DS_OBJECT_CLIENT_GET", "DS_KV_CLIENT_SET"}
# cost 阈值：2.5ms = 2500us（access 日志 cost 字段单位 us）
COST_THRESHOLD_US = 2500.0
# 文件名含该关键字（忽略大小写）即丢弃
UBSE_KEYWORD = "ubse"

# 核心 4 类日志的文件名匹配（按 basename）
RUNTIME_RE = re.compile(r"^(kvcache\.INFO\.log|ds_client.*\.INFO\.log)$", re.IGNORECASE)
ACCESS_RE = re.compile(r"^(access\.log|ds_client_access.*\.log)$", re.IGNORECASE)
# 故障 trace 识别只扫描 client 接口日志
CLIENT_ACCESS_RE = re.compile(r"^ds_client_access.*\.log$", re.IGNORECASE)

# 日志字段下标（以 ``|`` 分隔，0 基）
IDX_TIME, IDX_TRACE, IDX_STATUS, IDX_ACTION, IDX_COST = 0, 5, 7, 8, 9


def is_filtered_log(filename: str) -> bool:
    """是否是核心 4 类日志（需要对行做 trace 过滤）。"""
    return bool(RUNTIME_RE.match(filename) or ACCESS_RE.match(filename))


def is_client_access_log(filename: str) -> bool:
    """是否是 client 接口日志（用于识别故障 trace）。"""
    return bool(CLIENT_ACCESS_RE.match(filename))


def iter_files(root: Path):
    """递归遍历目录下的普通文件，跳过隐藏文件/目录（.DS_Store 等）。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            yield Path(dirpath) / fn


def scan_fault_traces(case_dir: Path, cost_threshold: float) -> set[str]:
    """扫描案例内的 client 接口日志，返回故障 trace_id 集合。"""
    traces: set[str] = set()
    for path in iter_files(case_dir):
        if not is_client_access_log(path.name):
            continue
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    fields = line.split("|")
                    if len(fields) <= IDX_COST:
                        continue
                    trace = fields[IDX_TRACE].strip()
                    action = fields[IDX_ACTION].strip()
                    if not trace or action not in FAULT_ACTIONS:
                        continue
                    try:
                        status = int(fields[IDX_STATUS].strip())
                    except ValueError:
                        continue
                    try:
                        cost = float(fields[IDX_COST].strip())
                    except ValueError:
                        cost = 0.0
                    if status != 0 or cost > cost_threshold:
                        traces.add(trace)
        except OSError as exc:
            print(f"    [WARN] 读取失败，跳过: {path} ({exc})", file=sys.stderr)
    return traces


def write_filtered(src: Path, dst: Path, traces: set[str]) -> int:
    """按 trace 过滤写出日志，返回保留的行数。"""
    kept = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8", errors="replace") as fin, \
            dst.open("w", encoding="utf-8", newline="") as fout:
        for line in fin:
            fields = line.split("|")
            if len(fields) > IDX_TRACE and fields[IDX_TRACE].strip() in traces:
                fout.write(line)
                kept += 1
    return kept


def clean_case(case_dir: Path, out_case_dir: Path, dry_run: bool, cost_threshold: float) -> dict:
    """清洗单个案例，返回统计信息。"""
    stat = {"traces": 0, "kept": False, "filtered": 0, "copied": 0,
            "skipped_ubse": 0, "lines_kept": 0}
    traces = scan_fault_traces(case_dir, cost_threshold)
    stat["traces"] = len(traces)
    if not traces:
        return stat  # 无故障 trace → 整案例丢弃
    stat["kept"] = True
    if dry_run:
        return stat

    for src in iter_files(case_dir):
        if UBSE_KEYWORD in src.name.lower():
            stat["skipped_ubse"] += 1
            continue
        rel = src.relative_to(case_dir)
        dst = out_case_dir / rel
        if is_filtered_log(src.name):
            stat["lines_kept"] += write_filtered(src, dst, traces)
            stat["filtered"] += 1
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            stat["copied"] += 1
    return stat


def main() -> int:
    ap = argparse.ArgumentParser(description="KVCache 日志清洗（故障 trace 裁剪 + 丢弃 ubse 日志）")
    ap.add_argument("src", help="源文件夹（其一级子目录被视为案例）")
    ap.add_argument("-o", "--out", default=None,
                    help="输出目录（默认：同级 <src>_cleaned）")
    ap.add_argument("--cost-us", type=float, default=COST_THRESHOLD_US,
                    help=f"cost 故障阈值，单位 us（默认 {COST_THRESHOLD_US:.0f} = 2.5ms）")
    ap.add_argument("--dry-run", action="store_true", help="只统计，不落盘")
    args = ap.parse_args()
    cost_threshold = args.cost_us

    src = Path(args.src).expanduser().resolve()
    if not src.is_dir():
        print(f"[错误] 源文件夹不存在或不是目录: {src}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser().resolve() if args.out else src.with_name(src.name + "_cleaned")

    cases = sorted(p for p in src.iterdir() if p.is_dir() and not p.name.startswith("."))
    print(f"[配置] 源={src}")
    print(f"[配置] 输出={out}" + ("   [dry-run 未落盘]" if args.dry_run else ""))
    print(f"[配置] cost 阈值={cost_threshold:.0f}us  action={sorted(FAULT_ACTIONS)}")
    print(f"[配置] 案例数={len(cases)}\n")

    total = {"kept": 0, "dropped": 0, "traces": 0, "filtered": 0,
             "copied": 0, "skipped_ubse": 0, "lines_kept": 0}
    for case in cases:
        stat = clean_case(case, out / case.name, args.dry_run, cost_threshold)
        if stat["kept"]:
            total["kept"] += 1
            total["traces"] += stat["traces"]
            total["filtered"] += stat["filtered"]
            total["copied"] += stat["copied"]
            total["skipped_ubse"] += stat["skipped_ubse"]
            total["lines_kept"] += stat["lines_kept"]
            print(f"  [保留] {case.name}  故障 trace={stat['traces']}  "
                  f"过滤日志={stat['filtered']}  采集文件={stat['copied']}  "
                  f"丢弃ubse={stat['skipped_ubse']}  保留行={stat['lines_kept']}")
        else:
            total["dropped"] += 1
            print(f"  [丢弃] {case.name}  （无故障 trace）")

    print("\n[完成] 案例：保留 {kept} / 丢弃 {dropped}；故障 trace 合计 {traces}；"
          "过滤日志 {filtered} 个（保留行 {lines}），采集其它文件 {copied} 个，"
          "丢弃 ubse {ubse} 个。".format(
              kept=total["kept"], dropped=total["dropped"], traces=total["traces"],
              filtered=total["filtered"], lines=total["lines_kept"],
              copied=total["copied"], ubse=total["skipped_ubse"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
