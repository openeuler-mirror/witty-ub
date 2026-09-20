#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
"""bRPC RPC 阶段深挖脚本（latency-analysis Skill 阶段 4.5 工具）。

背景：KVC 解析管线（26 us 字段模型）当前未解析新版 bRPC perf 行
（`[BRPC_RPC_FRAMEWORK_SLOW]`，brpc_perf_trace.h:377，19 字段格式，
嵌于 ds_client_*.INFO.log）。本脚本旁路直扫原始日志，按父 trace 聚合
RPC 子过程，输出阶段归因，作为 /stats/stages 轻量粗分后的深度下钻。

阶段拆解口径（与 docs/design/trace-light-api.md §9 项 7 对齐结论一致）：
  - QueryMeta        = QueryAndGet 的 e2e − 框架分量
                      （框架分量 = network_residual + server_req_queue + client_req_framework；
                       超时无响应时三分量无测量=0，QueryMeta 吸收全额等待）
  - RPC网络          = network_residual_us
  - RPC排队/框架     = server_req_queue_us + client_req_framework_us
  - Master元数据写   = Create/Publish 的 e2e − 框架分量
  - DataWorker处理   = GetObjectRemote 的 e2e − 框架分量
每条 trace 按 winner-take-all 归入唯一主导桶。

用法:
  python3 brpc_stage_drill.py <日志目录|zip> [--slow-ms 1.5] [--failed-only]
                              [--top 10] [--json out.json] [--quiet]

输出: 桶分布（含治理指引）、错误分布（cntl_error_code）、每桶 top 样例 trace。
仅依赖 Python 标准库。
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import sys
import zipfile

# [BRPC_RPC_FRAMEWORK_SLOW] trace_id=<parent>;<span> method=... 19 字段
_BRPC_RE = re.compile(
    r"\[BRPC_RPC_FRAMEWORK_SLOW\]\s+"
    r"trace_id=(?P<trace_id>[^\s;]+)(?:;(?P<span>\S+))?\s+"
    r"method=(?P<method>\S+)\s+"
    r"framework_us=(?P<framework_us>\d+)\s+"
    r"e2e_us=(?P<e2e_us>\d+)\s+"
    r"client_req_framework_us=(?P<client_req_fw_us>\d+)\s+"
    r"remote_processing_us=(?P<remote_proc_us>\d+)\s+"
    r"server_req_queue_us=(?P<server_queue_us>\d+)\s+"
    r"server_exec_us=(?P<server_exec_us>\d+)\s+"
    r"network_residual_us=(?P<network_us>\d+)\s+"
    r"cntl_timeout_ms=(?P<timeout_ms>\d+)\s+"
    r"cntl_deadline_us=(?P<deadline_us>\d+)\s+"
    r"cntl_error_code=(?P<error_code>\d+)\s+"
    r"cntl_failed=(?P<failed>\d+)"
)

# 桶定义：(key, 显示名, 治理指引) —— 指引文案与 /stats/stages 桶定义表同源
_BUCKETS: dict[str, tuple[str, str]] = {
    "query_meta": (
        "QueryMeta",
        "排查 Meta Worker 响应、元数据锁竞争、路由刷新与 metadata RPC。",
    ),
    "rpc_network": (
        "RPC网络",
        "优先排查 bRPC 网络、调度、响应通知和 framework residual。",
    ),
    "rpc_queue": (
        "RPC排队",
        "排查服务端请求队列、执行线程池饱和与 handler 调度。",
    ),
    "master_write": (
        "Master元数据写",
        "排查 Master 端 Create/Publish 处理、元数据持久化与复制链路。",
    ),
    "data_worker": (
        "DataWorker处理",
        "排查对象查找、buffer 准备、重试与远端 Worker 调度。",
    ),
    "urma": (
        "URMA链路",
        "排查 URMA 连接建立/completion、send lane 与线程调度。",
    ),
    "rpc_other": (
        "其他RPC",
        "未归类 method；结合 method 名人工判断归属阶段。",
    ),
}

# method → 业务段归属（e2e−框架分量 记入哪个桶）
_METHOD_DIM = (
    ("QueryAndGet", "query_meta"),
    ("Create", "master_write"),
    ("Publish", "master_write"),
    ("GetObjectRemote", "data_worker"),
    ("WorkerWorkerExchangeUrmaConnectInfo", "urma"),
)


def _method_bucket(method: str) -> str:
    for name, bucket in _METHOD_DIM:
        if name in method:
            return bucket
    return "rpc_other"


def _iter_log_files(path: str):
    """支持目录递归与 zip 包两种输入。"""
    if os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for name in files:
                yield os.path.join(root, name), None
    elif os.path.isfile(path) and path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                with zf.open(info) as fh:
                    yield info.filename, io.TextIOWrapper(fh, errors="replace")
    else:
        raise SystemExit(f"输入不存在或不支持的类型: {path}")


def extract(path: str) -> dict[str, dict]:
    """扫描日志，按父 trace_id 聚合 RPC 子过程。"""
    traces: dict[str, dict] = {}
    stats = {"files": 0, "info_files": 0, "lines": 0}
    for fname, opened in _iter_log_files(path):
        stats["files"] += 1
        base = os.path.basename(fname)
        # bRPC perf 行只出现在 SDK 侧 INFO/runtime 日志；access/worker 日志跳过可提速
        if not (".INFO" in base or "runtime" in base or base.endswith(".log")):
            continue
        try:
            fh = opened or open(fname, errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                m = _BRPC_RE.search(line)
                if not m:
                    continue
                stats["info_files"] = stats["info_files"] or 1
                stats["lines"] += 1
                tid = m.group("trace_id")
                e2e = int(m.group("e2e_us"))
                net = int(m.group("network_us"))
                queue = int(m.group("server_queue_us"))
                cl_fw = int(m.group("client_req_fw_us"))
                exec_us = int(m.group("server_exec_us"))
                method = m.group("method")
                rec = traces.setdefault(tid, {"rpcs": [], "max_e2e_ms": 0.0})
                rec["rpcs"].append(
                    {
                        "method": method.split(".")[-1],
                        "e2e_ms": e2e / 1000.0,
                        "net_ms": net / 1000.0,
                        "queue_ms": (queue + cl_fw) / 1000.0,
                        "exec_ms": exec_us / 1000.0,
                        # 业务段 = e2e − 框架分量（超时无响应时框架分量=0，全额归业务段）
                        "biz_ms": max(e2e - net - queue - cl_fw, 0) / 1000.0,
                        "bucket": _method_bucket(method),
                        "failed": m.group("failed") == "1",
                        "error_code": int(m.group("error_code")),
                        "timeout_ms": int(m.group("timeout_ms")),
                    }
                )
                rec["max_e2e_ms"] = max(rec["max_e2e_ms"], e2e / 1000.0)
    stats["info_files"] = sum(1 for _ in ()) or stats["info_files"]
    traces["_stats"] = stats  # type: ignore[assignment]
    return traces


def classify(traces: dict, slow_ms: float, failed_only: bool) -> list[dict]:
    """winner-take-all：每 trace 归入主导桶。"""
    rows = []
    for tid, rec in traces.items():
        if tid == "_stats":
            continue
        rpcs = rec["rpcs"]
        if failed_only and not any(r["failed"] for r in rpcs):
            continue
        if rec["max_e2e_ms"] < slow_ms:
            continue
        dims = collections.Counter()
        for r in rpcs:
            dims["rpc_network"] += r["net_ms"]
            dims["rpc_queue"] += r["queue_ms"]
            dims[r["bucket"]] += r["biz_ms"]
        if not dims:
            continue
        winner = max(dims, key=lambda k: dims[k])
        total = sum(dims.values())
        rows.append(
            {
                "trace_id": tid,
                "dominant": winner,
                "dominant_ms": round(dims[winner], 3),
                "dims_ms": {k: round(v, 3) for k, v in dims.items() if v > 0},
                "share": round(dims[winner] / total, 3) if total else 0.0,
                "rpc_count": len(rpcs),
                "any_failed": any(r["failed"] for r in rpcs),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="bRPC RPC 阶段深挖")
    ap.add_argument("path", help="日志目录或 zip 包")
    ap.add_argument("--slow-ms", type=float, default=1.5,
                    help="慢 RPC 阈值(ms)，按 trace 内最大 e2e 过滤（默认 1.5）")
    ap.add_argument("--failed-only", action="store_true",
                    help="只统计含失败 RPC（cntl_failed=1）的 trace")
    ap.add_argument("--top", type=int, default=10, help="每桶样例 trace 条数")
    ap.add_argument("--json", dest="json_out", help="结果另存 JSON 文件")
    ap.add_argument("--quiet", action="store_true", help="只输出 JSON（配合 --json）")
    args = ap.parse_args()

    traces = extract(args.path)
    stats = traces.pop("_stats", {"files": 0, "lines": 0})
    rows = classify(traces, args.slow_ms, args.failed_only)

    buckets = collections.Counter(r["dominant"] for r in rows)
    errors = collections.Counter()
    for rec in traces.values():
        for r in rec["rpcs"]:
            if r["failed"]:
                errors[r["error_code"]] += 1

    samples: dict[str, list] = collections.defaultdict(list)
    for r in sorted(rows, key=lambda x: -x["dominant_ms"]):
        if len(samples[r["dominant"]]) < args.top:
            samples[r["dominant"]].append(r)

    result = {
        "input": args.path,
        "scan": {"files": stats["files"], "brpc_lines": stats["lines"],
                 "parent_traces": len(traces)},
        "filter": {"slow_ms": args.slow_ms, "failed_only": args.failed_only,
                   "matched_traces": len(rows)},
        "buckets": [
            {"key": k, "name": _BUCKETS[k][0], "count": buckets.get(k, 0),
             "guidance": _BUCKETS[k][1],
             "top_traces": [
                 {"trace_id": t["trace_id"], "dominant_ms": t["dominant_ms"],
                  "share": t["share"], "rpc_count": t["rpc_count"],
                  "dims_ms": t["dims_ms"]}
                 for t in samples.get(k, [])
             ]}
            for k in _BUCKETS
        ],
        "rpc_error_codes": [
            {"code": c, "count": n, "note": "1008=deadline 截止（RPC截止超时）"
             if c == 1008 else ""}
            for c, n in errors.most_common()
        ],
    }

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    if not args.quiet:
        print(f"扫描: {stats['files']} 文件 / {stats['lines']} 条 bRPC perf 行 / "
              f"{len(traces)} 个父 trace")
        print(f"过滤: slow≥{args.slow_ms}ms"
              f"{' 且含失败 RPC' if args.failed_only else ''} → 命中 {len(rows)} trace")
        print()
        print(f"{'桶':<14}{'trace数':>8}   治理指引")
        for b in result["buckets"]:
            if b["count"] or b["key"] in ("query_meta", "rpc_network"):
                print(f"{b['name']:<14}{b['count']:>8}   {b['guidance']}")
        if result["rpc_error_codes"]:
            print()
            print("RPC 错误码分布:", ", ".join(
                f"{e['code']}×{e['count']}" for e in result["rpc_error_codes"]))
        if not args.quiet and not args.json_out:
            print()
            print("每桶 top 样例:")
            for b in result["buckets"]:
                for t in b["top_traces"][:3]:
                    print(f"  [{b['name']}] {t['trace_id']} "
                          f"主导 {t['dominant_ms']}ms (占比{t['share']:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
