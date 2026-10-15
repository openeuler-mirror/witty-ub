#!/usr/bin/env python3
"""统计并去重案例库中重复的 log_file_name，保留最早创建的案例。

用法:
    python3 scripts/dedup_cases.py            # 预览（dry-run）
    python3 scripts/dedup_cases.py --apply    # 实际执行删除
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import argparse
from collections import defaultdict

API = "http://127.0.0.1:9772"


def api_list_cases() -> list:
    """通过 API 获取所有案例。"""
    req = urllib.request.Request(f"{API}/case_library/list", method="GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("result", []) or []


def api_delete_case(case_id: str) -> bool:
    """通过 API 删除案例。"""
    req = urllib.request.Request(
        f"{API}/case_library/{case_id}",
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp.get("code") == 200
    except urllib.error.HTTPError:
        return False


def main():
    parser = argparse.ArgumentParser(description="案例库去重：保留最早创建的案例")
    parser.add_argument("--apply", action="store_true",
                        help="实际执行删除（默认 dry-run 仅预览）")
    args = parser.parse_args()

    print("=" * 70)
    print("案例库去重：按 log_file_name 去重，保留最早创建的案例")
    print("=" * 70)

    # 1. 获取所有案例
    print("\n[1/3] 通过 API 获取所有案例...")
    cases = api_list_cases()
    print(f"  案例库共 {len(cases)} 个案例")

    # 2. 按 log_file_name 分组（忽略空 log_file_name）
    print("\n[2/3] 按 log_file_name 分组统计重复...")
    by_lfn = defaultdict(list)
    no_lfn = []
    for c in cases:
        lfn = c.get("log_file_name", "")
        if not lfn:
            no_lfn.append(c)
            continue
        by_lfn[lfn].append(c)

    # 找出重复的 log_file_name
    duplicates = {lfn: items for lfn, items in by_lfn.items() if len(items) > 1}
    print(f"  无 log_file_name 的案例: {len(no_lfn)} 个")
    print(f"  唯一 log_file_name 数: {len(by_lfn)} 个")
    print(f"  重复的 log_file_name 数: {len(duplicates)} 个")

    total_to_delete = sum(len(items) - 1 for items in duplicates.values())
    print(f"  需删除的重复案例数: {total_to_delete} 个")
    print(f"  保留案例数: {len(cases) - total_to_delete} 个")

    if not duplicates:
        print("\n无重复案例，无需去重。")
        return

    # 显示重复详情（前 30 个）
    print(f"\n重复案例详情（按 log_file_name 分组，仅显示前 30 组）:")
    for i, (lfn, items) in enumerate(sorted(duplicates.items(), key=lambda x: -len(x[1])), 1):
        if i > 30:
            print(f"  ... 还有 {len(duplicates) - 30} 组")
            break
        # 按 created_at 升序，保留最早的
        items_sorted = sorted(items, key=lambda x: x.get("created_at", ""))
        keep = items_sorted[0]
        delete = items_sorted[1:]
        rct = keep.get("root_cause_type", "")
        cc = keep.get("case_category", "")
        print(f"  [{i}] {lfn[:60]}")
        print(f"      重复数: {len(items)}  根因: {rct}  大类: {cc}")
        print(f"      保留: {keep.get('id', '')[:12]}  created={keep.get('created_at', '')}")
        for d in delete:
            print(f"      删除: {d.get('id', '')[:12]}  created={d.get('created_at', '')}")

    if not args.apply:
        print(f"\n{'=' * 70}")
        print("Dry-run 模式：未实际删除。")
        print(f"如需实际执行删除，请运行: python3 scripts/dedup_cases.py --apply")
        print(f"{'=' * 70}")
        return

    # 3. 实际执行删除
    print(f"\n[3/3] 执行删除（共 {total_to_delete} 个）...")
    success = 0
    fail = 0
    for lfn, items in sorted(duplicates.items(), key=lambda x: -len(x[1])):
        items_sorted = sorted(items, key=lambda x: x.get("created_at", ""))
        # 保留最早的，删除其余
        to_delete = items_sorted[1:]
        for c in to_delete:
            case_id = c.get("id", "")
            if api_delete_case(case_id):
                success += 1
                print(f"  ✓ 删除 {case_id[:12]}  lfn={lfn[:50]}")
            else:
                fail += 1
                print(f"  ✗ 删除失败 {case_id[:12]}  lfn={lfn[:50]}")

    print(f"\n{'=' * 70}")
    print("去重完成！")
    print(f"{'=' * 70}")
    print(f"  删除成功: {success} 个")
    print(f"  删除失败: {fail} 个")
    print(f"  原案例数: {len(cases)}")
    print(f"  现案例数: {len(cases) - success}")

    # 验证
    remaining = api_list_cases()
    print(f"\n验证: API 返回案例数 = {len(remaining)}")


if __name__ == "__main__":
    main()
