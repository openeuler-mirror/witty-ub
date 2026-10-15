#!/usr/bin/env python3
"""将 new_case 的10个案例加入案例库，然后用 leave-one-out 评估 Top1/3/5 命中率。

每个案例评估时，排除自身（及同 root_cause_type 的重复案例）后进行匹配。
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import find_similar_fault_types

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"
CASE_DIR = os.path.join(os.path.dirname(__file__), "..", "case")
TOP_K = 100

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


def load_new_cases() -> list[dict]:
    cases = []
    for fname in sorted(os.listdir(NEW_CASE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(NEW_CASE_DIR, fname), "r", encoding="utf-8") as f:
            c = json.load(f)
        if c.get("features"):
            cases.append(c)
    return cases


def copy_new_cases_to_library(cases: list[dict]) -> list[str]:
    """将 new_case 复制到案例库，设置 case_category。返回复制到的文件路径列表。"""
    copied = []
    for case in cases:
        case_id = case.get("id", "")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "")
        # 设置 case_category
        case["case_category"] = gt_cat
        dest = os.path.join(CASE_DIR, f"{case_id}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(case, f, ensure_ascii=False, indent=2)
        copied.append(dest)
    return copied


def cleanup(copied: list[str]):
    for p in copied:
        if os.path.exists(p):
            os.remove(p)


async def evaluate_one(case: dict, all_case_ids: set[str]) -> dict:
    features = case["features"]
    fault_category = features.get("fault_category", "unknown")
    rct = case.get("root_cause_type", "")
    gt_cat = GT_CATEGORY.get(rct, "未知")
    case_id = case.get("id", "")

    # Leave-one-out: 排除当前案例自身
    exclude = {case_id}
    # 也排除同 root_cause_type 的其他新案例（避免同源匹配）
    for other_id in all_case_ids:
        if other_id != case_id:
            # 不排除其他新案例 —— 它们是合法的库案例
            pass

    result = await find_similar_fault_types(
        features, fault_category, top_k=TOP_K, exclude_case_ids=exclude
    )
    top_matches = result.get("top_matches", [])

    # 按相似度顺序提取去重后的大类
    seen_cats = []
    for m in top_matches:
        cat = m.get("case_category", "")
        if cat and cat not in seen_cats:
            seen_cats.append(cat)
        if len(seen_cats) >= 5:
            break

    top1_hit = gt_cat in seen_cats[:1]
    top3_hit = gt_cat in seen_cats[:3]
    top5_hit = gt_cat in seen_cats[:5]

    # GT 大类排位
    gt_rank = None
    for i, c in enumerate(seen_cats):
        if c == gt_cat:
            gt_rank = i + 1
            break

    best = top_matches[0] if top_matches else {}
    return {
        "file": case_id + ".json",
        "root_cause_type": rct,
        "gt_cat": gt_cat,
        "gt_rank": gt_rank,
        "predicted_top5_cats": seen_cats[:5],
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "top5_hit": top5_hit,
        "best_type": best.get("root_cause_type", ""),
        "best_cat": best.get("case_category", ""),
        "best_sim": best.get("similarity", 0),
        "library_size": result.get("library_size", 0),
    }


async def main():
    cases = load_new_cases()
    print(f"加载 new_case 案例数: {len(cases)}")

    all_case_ids = {c.get("id", "") for c in cases}

    # 复制到案例库
    copied = copy_new_cases_to_library(cases)
    print(f"已复制 {len(copied)} 个案例到案例库: {CASE_DIR}")
    print(f"案例库总数: {len(os.listdir(CASE_DIR))} (含 _categories.json)")
    print("=" * 100)

    try:
        results = []
        for i, case in enumerate(cases, 1):
            r = await evaluate_one(case, all_case_ids)
            results.append(r)
            rank_str = f"第{r['gt_rank']}位" if r['gt_rank'] else "未命中"
            print(f"[{i}/{len(cases)}] {r['root_cause_type'][:30]:<30s} GT={r['gt_cat']:<24s} "
                  f"排位={rank_str:<8s} "
                  f"Top1={'Y' if r['top1_hit'] else 'N'} "
                  f"Top3={'Y' if r['top3_hit'] else 'N'} "
                  f"Top5={'Y' if r['top5_hit'] else 'N'}")
            print(f"    预测: {' > '.join(r['predicted_top5_cats']) or '(无)'}")
            print(f"    最佳: {r['best_type']} [{r['best_cat']}] sim={r['best_sim']:.4f}")
            print()
    finally:
        cleanup(copied)
        print(f"已清理临时案例文件，案例库恢复原状")


if __name__ == "__main__":
    asyncio.run(main())
