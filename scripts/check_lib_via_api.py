#!/usr/bin/env python3
"""通过后端 API 检查真实案例库的分布情况。"""

from __future__ import annotations

import json
import urllib.request
from collections import Counter, defaultdict

API = "http://127.0.0.1:9772"


def api_list_cases():
    req = urllib.request.Request(f"{API}/case_library/list", method="GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("result", []) or []


def main():
    cases = api_list_cases()
    print(f"案例库共 {len(cases)} 个案例")

    # 检查 features 完整性
    no_features = [c for c in cases if not c.get("features")]
    has_features = [c for c in cases if c.get("features")]
    print(f"  有 features: {len(has_features)} 个")
    print(f"  无 features: {len(no_features)} 个")

    # 按 case_category 分布
    by_cat = defaultdict(list)
    for c in cases:
        cc = c.get("case_category", "(无)")
        by_cat[cc].append(c)

    print(f"\n各大类案例数（按数量降序）:")
    for cat, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        has_feat = sum(1 for c in items if c.get("features"))
        print(f"  {cat:35s}  {len(items):4d} 个  (有features: {has_feat})")

    # 检查是否混入 etcd/UBM/UBSe/ps_n_n
    print(f"\n检查是否混入应删除的类别:")
    for bad_cat in ["etcd故障", "UB-UBSe/UBM管理进程故障", "其他"]:
        items = by_cat.get(bad_cat, [])
        if items:
            print(f"  ⚠ {bad_cat}: {len(items)} 个 (应删除)")
        else:
            print(f"  ✓ {bad_cat}: 0 个")

    # 检查 root_cause_type 中是否混入 ps_n_n, etcd 等
    print(f"\n检查 root_cause_type 中是否混入垃圾数据:")
    bad_rcts = []
    for c in cases:
        rct = c.get("root_cause_type", "")
        if "etcd" in rct or "ps_n_n" in rct or "UBSe" in rct or "UBM" in rct:
            bad_rcts.append((c.get("id", "")[:12], rct, c.get("case_category", "")))
    if bad_rcts:
        print(f"  ⚠ 发现 {len(bad_rcts)} 个混入的案例:")
        for cid, rct, cc in bad_rcts[:20]:
            print(f"    - {cid}  rct={rct:30s}  cat={cc}")
    else:
        print(f"  ✓ 未发现混入的垃圾数据")


if __name__ == "__main__":
    main()
