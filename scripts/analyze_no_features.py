#!/usr/bin/env python3
"""分析案例库中无 features 的 97 个案例的 root_cause_type 分布。

用法:
    src/plugins/latency/.venv/bin/python scripts/analyze_no_features.py
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.case_service import CASE_DIR


def main():
    case_files = [
        f for f in sorted(os.listdir(CASE_DIR))
        if f.endswith(".json") and not f.startswith("_")
    ]
    print(f"案例库共 {len(case_files)} 个案例\n")

    no_features = []
    has_features = []
    for fname in case_files:
        fpath = os.path.join(CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            case = json.load(f)
        rct = case.get("root_cause_type", "")
        log_file_id = case.get("log_file_id", "")
        case_category = case.get("case_category", "")
        features = case.get("features")
        if features:
            has_features.append((fname, rct, case_category, log_file_id))
        else:
            no_features.append((fname, rct, case_category, log_file_id))

    print(f"有 features 的案例: {len(has_features)} 个")
    print(f"无 features 的案例: {len(no_features)} 个")

    # 无 features 的案例按 case_category 分组
    by_cat = defaultdict(list)
    for fname, rct, cc, lfid in no_features:
        by_cat[cc if cc else "(无 case_category)"].append((fname, rct, lfid))

    print(f"\n无 features 的案例按 case_category(大类) 分布:")
    for cat, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        print(f"  {cat:30s}  {len(items):3d} 个案例")

    # 列出有 features 的案例按 case_category 分布
    by_cat2 = defaultdict(list)
    for fname, rct, cc, lfid in has_features:
        by_cat2[cc if cc else "(无 case_category)"].append((fname, rct, lfid))

    print(f"\n有 features 的案例按 case_category(大类) 分布:")
    for cat, items in sorted(by_cat2.items(), key=lambda x: -len(x[1])):
        print(f"  {cat:30s}  {len(items):3d} 个案例")

    # 列出有 features 案例的 root_cause_type
    print(f"\n有 features 案例的 root_cause_type 列表:")
    rct_counter = Counter(rct for _, rct, _, _ in has_features)
    for rct, n in rct_counter.most_common():
        print(f"  {rct:40s}  {n:3d} 个")


if __name__ == "__main__":
    main()
