#!/usr/bin/env python3
"""将 new_case 的10个案例永久加入案例库，设置 case_category。
同时将缺失的 UB-UBSe/UBM管理进程故障 大类加入 _categories.json。
"""
import json
import os
import shutil

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"
CASE_DIR = os.path.join(os.path.dirname(__file__), "..", "case")

GT_CATEGORY = {
    "CPU挂死": "Worker-缩容/挂死",
    "SDK初始化配置错误": "UB-UBSe/UBM管理进程故障",
    "UB端口down": "UB-端口故障",
    "UB链路故障": "UB-链路故障",
    "端侧到L1端口故障": "UB-端口故障",
    "TCPdown": "网络/TCP故障",
    "UB交换机L1的上行端口闪断": "UB-端口故障",
    "worker进程异常退出": "Worker-退出/崩溃",
    "L1-L2互联链路反复shutdown模拟链路闪断": "UB-链路故障",
}


def update_categories():
    """在 _categories.json 中增加 UB-UBSe/UBM管理进程故障 大类。"""
    cat_path = os.path.join(CASE_DIR, "_categories.json")
    with open(cat_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    existing_names = {c["name"] for c in meta["categories"]}
    if "UB-UBSe/UBM管理进程故障" not in existing_names:
        import uuid
        new_cat = {
            "id": str(uuid.uuid4()),
            "name": "UB-UBSe/UBM管理进程故障",
            "description": "UBSe/UBM管理进程级别的故障，包括SDK初始化配置错误等",
            "sort_order": 2,
        }
        meta["categories"].append(new_cat)
        meta["categories"].sort(key=lambda c: c.get("sort_order", 0))
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"已添加大类: UB-UBSe/UBM管理进程故障")
    else:
        print("大类 UB-UBSe/UBM管理进程故障 已存在，跳过")


def copy_cases():
    """将 new_case 的案例复制到案例库，设置 case_category。"""
    count = 0
    for fname in sorted(os.listdir(NEW_CASE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(NEW_CASE_DIR, fname), "r", encoding="utf-8") as f:
            case = json.load(f)
        if not case.get("features"):
            continue

        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "")
        case["case_category"] = gt_cat

        case_id = case.get("id", "")
        dest = os.path.join(CASE_DIR, f"{case_id}.json")

        if os.path.exists(dest):
            print(f"  跳过（已存在）: {case_id}.json [{rct}] → {gt_cat}")
            continue

        with open(dest, "w", encoding="utf-8") as f:
            json.dump(case, f, ensure_ascii=False, indent=2)
        print(f"  已添加: {case_id}.json [{rct}] → {gt_cat}")
        count += 1

    print(f"\n共添加 {count} 个案例到案例库")
    total = len([f for f in os.listdir(CASE_DIR) if f.endswith(".json")])
    print(f"案例库当前总数: {total} 个案例 (+ _categories.json)")


if __name__ == "__main__":
    print("=" * 60)
    print("步骤 1: 更新 _categories.json")
    print("=" * 60)
    update_categories()

    print()
    print("=" * 60)
    print("步骤 2: 复制 new_case 到案例库")
    print("=" * 60)
    copy_cases()
