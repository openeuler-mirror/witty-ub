#!/usr/bin/env python3
"""Leave-One-Out 评估：对每个测试案例，排除自身 case_id + log_file_id 后匹配，
并过滤 100% 自匹配结果。

用法:
    WITTY_DIR=/Users/zhaoyujin/Desktop/witty-ub \
    PYTHONPATH=src/plugins src/plugins/latency/.venv/bin/python \
    scripts/eval_leave_one_out.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import find_similar_fault_types

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"
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


async def evaluate_one(case: dict) -> dict:
    features = case["features"]
    fault_category = features.get("fault_category", "unknown")
    rct = case.get("root_cause_type", "")
    gt_cat = GT_CATEGORY.get(rct, "未知")
    case_id = case.get("id", "")
    log_file_id = case.get("log_file_id", "")

    # Leave-one-out: 排除自身 case_id + log_file_id，并自动过滤 100% 匹配
    result = await find_similar_fault_types(
        features,
        fault_category,
        top_k=TOP_K,
        exclude_case_ids={case_id},
        exclude_log_file_id=log_file_id,
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
        "top1_hit": gt_cat in seen_cats[:1],
        "top3_hit": gt_cat in seen_cats[:3],
        "top5_hit": gt_cat in seen_cats[:5],
        "best_type": best.get("root_cause_type", ""),
        "best_cat": best.get("case_category", ""),
        "best_sim": best.get("similarity", 0),
        "library_size": result.get("library_size", 0),
    }


async def main():
    cases = load_new_cases()
    print(f"加载 new_case 案例数: {len(cases)}")
    print(f"案例库总数: 174 (159 original + 15 UBM/UBSe)")
    print(f"评估方式: Leave-One-Out (排除 case_id + log_file_id, 过滤 sim>=0.999)")
    print("=" * 100)

    results = []
    for i, case in enumerate(cases, 1):
        r = await evaluate_one(case)
        results.append(r)
        rank_str = f"第{r['gt_rank']}位" if r['gt_rank'] else "未命中"
        print(f"[{i}/{len(cases)}] {r['root_cause_type']:<30s} GT={r['gt_cat']:<24s} "
              f"排位={rank_str:<8s} "
              f"Top1={'Y' if r['top1_hit'] else 'N'} "
              f"Top3={'Y' if r['top3_hit'] else 'N'} "
              f"Top5={'Y' if r['top5_hit'] else 'N'}")
        print(f"    预测: {' > '.join(r['predicted_top5_cats']) or '(无)'}")
        print(f"    最佳: {r['best_type']} [{r['best_cat']}] sim={r['best_sim']:.4f}")
        print()

    total = len(results)
    hit1 = sum(1 for r in results if r["top1_hit"])
    hit3 = sum(1 for r in results if r["top3_hit"])
    hit5 = sum(1 for r in results if r["top5_hit"])

    print("=" * 100)
    print("命中率汇总 (Leave-One-Out)")
    print("=" * 100)
    print(f"  总案例数: {total}")
    print(f"  Top-1 命中率: {hit1}/{total} = {hit1/total*100:.1f}%")
    print(f"  Top-3 命中率: {hit3}/{total} = {hit3/total*100:.1f}%")
    print(f"  Top-5 命中率: {hit5}/{total} = {hit5/total*100:.1f}%")

    print("\n按大类分组命中率:")
    cat_stats = {}
    for r in results:
        gt = r["gt_cat"]
        if gt not in cat_stats:
            cat_stats[gt] = {"total": 0, "hit1": 0, "hit3": 0, "hit5": 0}
        cat_stats[gt]["total"] += 1
        if r["top1_hit"]:
            cat_stats[gt]["hit1"] += 1
        if r["top3_hit"]:
            cat_stats[gt]["hit3"] += 1
        if r["top5_hit"]:
            cat_stats[gt]["hit5"] += 1

    print(f"  {'大类':<28s} {'总数':>4s} {'Top1':>6s} {'Top3':>6s} {'Top5':>6s}")
    print(f"  {'-' * 60}")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        print(f"  {cat:<28s} {s['total']:>4d} {s['hit1']:>3d}/{s['total']:<2d} "
              f"{s['hit3']:>3d}/{s['total']:<2d} {s['hit5']:>3d}/{s['total']:<2d}")

    missed = [r for r in results if not r["top5_hit"]]
    if missed:
        print(f"\nTop-5 未命中案例 ({len(missed)} 个):")
        for r in missed:
            print(f"  {r['root_cause_type']} (GT: {r['gt_cat']}) → "
                  f"预测: {' > '.join(r['predicted_top5_cats']) or '(无)'}")


if __name__ == "__main__":
    asyncio.run(main())
