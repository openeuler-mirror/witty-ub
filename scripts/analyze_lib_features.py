#!/usr/bin/env python3
"""列出案例库中每个大类的具体案例和特征质量，特别关注 UB-链路故障 / 网络/TCP故障 / UB-端口故障。

用法:
    src/plugins/latency/.venv/bin/python scripts/analyze_lib_features.py
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.case_service import CASE_DIR


def main():
    case_files = [
        f for f in sorted(os.listdir(CASE_DIR))
        if f.endswith(".json") and not f.startswith("_")
    ]
    print(f"案例库共 {len(case_files)} 个案例\n")

    # 按 case_category 分组
    by_cat = defaultdict(list)
    for fname in case_files:
        fpath = os.path.join(CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            case = json.load(f)
        cc = case.get("case_category", "(无)")
        by_cat[cc].append((fname, case))

    # 重点分析这几个大类
    focus_cats = ["UB-链路故障", "网络/TCP故障", "UB-端口故障",
                  "Worker-退出/崩溃", "Worker-缩容/挂死", "Worker-重启",
                  "Client-挂死/网络", "Client-退出"]

    for cat in focus_cats:
        items = by_cat.get(cat, [])
        print(f"\n{'=' * 70}")
        print(f"大类: {cat}  ({len(items)} 个案例)")
        print(f"{'=' * 70}")
        for fname, case in items:
            rct = case.get("root_cause_type", "")
            lfid = case.get("log_file_id", "")
            lname = case.get("log_file_name", "")
            feats = case.get("features")
            fc = feats.get("fault_category", "?") if feats else "无"
            lat = feats.get("latency") if feats else None
            conn = feats.get("connectivity") if feats else None
            lat_ok = "✓" if lat else "✗"
            conn_ok = "✓" if conn else "✗"
            print(f"  {fname[:12]}  rct={rct:25s}  log={lname[:20]:20s}  "
                  f"fc={fc:10s}  lat={lat_ok}  conn={conn_ok}  lfid={'有' if lfid else '无'}")

    # 列出"etcd故障"、"UB-UBSe/UBM管理进程故障"、"其他" 这三个不应有的类
    print(f"\n{'=' * 70}")
    print(f"以下类别应被删除:")
    print(f"{'=' * 70}")
    for cat in ["etcd故障", "UB-UBSe/UBM管理进程故障", "其他"]:
        items = by_cat.get(cat, [])
        print(f"\n  {cat}  ({len(items)} 个案例):")
        for fname, case in items[:5]:
            rct = case.get("root_cause_type", "")
            print(f"    {fname[:12]}  rct={rct}")
        if len(items) > 5:
            print(f"    ... 还有 {len(items) - 5} 个")


if __name__ == "__main__":
    main()
