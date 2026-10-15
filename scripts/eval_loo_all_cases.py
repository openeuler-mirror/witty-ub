#!/usr/bin/env python3
"""Leave-One-Out 评估：对案例库中每个案例，排除自身后匹配，评估大类匹配准确性。

用法:
    WITTY_DIR=/Users/zhaoyujin/Desktop/witty-ub \
    PYTHONPATH=src/plugins src/plugins/latency/.venv/bin/python \
    scripts/eval_loo_all_cases.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import find_similar_fault_types, load_case_library, merge_fault_type

TOP_K = 100


async def evaluate_one(case: dict, idx: int, total: int) -> dict:
    features = case["features"]
    fault_category = features.get("fault_category", "unknown")
    gt_cat = case.get("case_category", "")
    rct = case.get("root_cause_type", "")
    case_id = case.get("id", "")
    log_file_id = case.get("log_file_id", "")

    if not gt_cat:
        print(f"[{idx}/{total}] {rct} — 无 case_category，跳过")
        return None

    gt_type = merge_fault_type(rct)

    result = await find_similar_fault_types(
        features,
        fault_category,
        top_k=TOP_K,
        exclude_case_ids={case_id},
        exclude_log_file_id=log_file_id,
    )
    top_matches = result.get("top_matches", [])

    # 大类排名
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

    # 小类排名（去重保序）
    seen_types = []
    for m in top_matches:
        t = m.get("root_cause_type", "")
        if t and t not in seen_types:
            seen_types.append(t)
        if len(seen_types) >= 10:
            break

    gt_type_rank = None
    for i, t in enumerate(seen_types):
        if t == gt_type:
            gt_type_rank = i + 1
            break

    best = top_matches[0] if top_matches else {}
    print(f"[{idx}/{total}] {rct:<36s} GT={gt_cat:<24s} "
          f"排位={'第'+str(gt_rank)+'位' if gt_rank else '未命中':<8s} "
          f"Top1={'Y' if gt_cat in seen_cats[:1] else 'N'} "
          f"Top3={'Y' if gt_cat in seen_cats[:3] else 'N'} "
          f"Top5={'Y' if gt_cat in seen_cats[:5] else 'N'}")
    if not top_matches:
        print(f"    (无匹配结果)")
    else:
        print(f"    预测: {' > '.join(seen_cats[:5]) or '(无)'}")
        print(f"    最佳: {best.get('root_cause_type', '')} [{best.get('case_category', '')}] sim={best.get('similarity', 0):.4f}")

    return {
        "root_cause_type": rct,
        "gt_type": gt_type,
        "gt_cat": gt_cat,
        "gt_rank": gt_rank,
        "gt_type_rank": gt_type_rank,
        "predicted_top5_cats": seen_cats[:5],
        "predicted_top10_types": seen_types[:10],
        "top1_hit": gt_cat in seen_cats[:1],
        "top3_hit": gt_cat in seen_cats[:3],
        "top5_hit": gt_cat in seen_cats[:5],
        "type_top1_hit": gt_type in seen_types[:1],
        "type_top3_hit": gt_type in seen_types[:3],
        "type_top5_hit": gt_type in seen_types[:5],
        "type_top10_hit": gt_type in seen_types[:10],
        "best_sim": best.get("similarity", 0),
    }


async def main():
    cases = load_case_library()
    total = len(cases)
    print(f"案例库总数: {total}")
    print(f"评估方式: Leave-One-Out (排除 case_id + log_file_id, 过滤 sim>=0.999)")
    print("=" * 110)

    results = []
    for i, case in enumerate(cases, 1):
        r = await evaluate_one(case, i, total)
        if r is not None:
            results.append(r)

    valid = len(results)
    hit1 = sum(1 for r in results if r["top1_hit"])
    hit3 = sum(1 for r in results if r["top3_hit"])
    hit5 = sum(1 for r in results if r["top5_hit"])

    thit1 = sum(1 for r in results if r["type_top1_hit"])
    thit3 = sum(1 for r in results if r["type_top3_hit"])
    thit5 = sum(1 for r in results if r["type_top5_hit"])
    thit10 = sum(1 for r in results if r["type_top10_hit"])

    print("=" * 110)
    print("命中率汇总 (Leave-One-Out, 全案例库)")
    print("=" * 110)
    print(f"  有效案例数: {valid}")
    print(f"\n  --- 大类 (case_category) ---")
    print(f"  Top-1 命中率: {hit1}/{valid} = {hit1/valid*100:.1f}%")
    print(f"  Top-3 命中率: {hit3}/{valid} = {hit3/valid*100:.1f}%")
    print(f"  Top-5 命中率: {hit5}/{valid} = {hit5/valid*100:.1f}%")
    print(f"\n  --- 小类 (root_cause_type) ---")
    print(f"  Top-1  命中率: {thit1}/{valid} = {thit1/valid*100:.1f}%")
    print(f"  Top-3  命中率: {thit3}/{valid} = {thit3/valid*100:.1f}%")
    print(f"  Top-5  命中率: {thit5}/{valid} = {thit5/valid*100:.1f}%")
    print(f"  Top-10 命中率: {thit10}/{valid} = {thit10/valid*100:.1f}%")

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

    print(f"  {'大类':<28s} {'总数':>4s} {'Top1':>8s} {'Top3':>8s} {'Top5':>8s} {'Top1%':>7s} {'Top3%':>7s} {'Top5%':>7s}")
    print(f"  {'-' * 85}")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        p1 = s['hit1'] / s['total'] * 100 if s['total'] > 0 else 0
        p3 = s['hit3'] / s['total'] * 100 if s['total'] > 0 else 0
        p5 = s['hit5'] / s['total'] * 100 if s['total'] > 0 else 0
        print(f"  {cat:<28s} {s['total']:>4d} {s['hit1']:>3d}/{s['total']:<3d} {s['hit3']:>3d}/{s['total']:<3d} {s['hit5']:>3d}/{s['total']:<3d} {p1:>6.1f}% {p3:>6.1f}% {p5:>6.1f}%")

    missed = [r for r in results if not r["top5_hit"]]
    if missed:
        print(f"\n大类 Top-5 未命中案例 ({len(missed)} 个):")
        for r in missed:
            print(f"  {r['root_cause_type']:<36s} (GT: {r['gt_cat']}) -> 预测: {' > '.join(r['predicted_top5_cats']) or '(无)'}")

    print(f"\n按大类分组小类命中率:")
    type_cat_stats = {}
    for r in results:
        gt = r["gt_cat"]
        if gt not in type_cat_stats:
            type_cat_stats[gt] = {"total": 0, "t1": 0, "t3": 0, "t5": 0, "t10": 0}
        type_cat_stats[gt]["total"] += 1
        if r["type_top1_hit"]:
            type_cat_stats[gt]["t1"] += 1
        if r["type_top3_hit"]:
            type_cat_stats[gt]["t3"] += 1
        if r["type_top5_hit"]:
            type_cat_stats[gt]["t5"] += 1
        if r["type_top10_hit"]:
            type_cat_stats[gt]["t10"] += 1

    print(f"  {'大类':<28s} {'总数':>4s} {'T1':>8s} {'T3':>8s} {'T5':>8s} {'T10':>8s} {'T1%':>7s} {'T3%':>7s} {'T5%':>7s} {'T10%':>7s}")
    print(f"  {'-' * 100}")
    for cat in sorted(type_cat_stats.keys()):
        s = type_cat_stats[cat]
        p1 = s['t1'] / s['total'] * 100 if s['total'] > 0 else 0
        p3 = s['t3'] / s['total'] * 100 if s['total'] > 0 else 0
        p5 = s['t5'] / s['total'] * 100 if s['total'] > 0 else 0
        p10 = s['t10'] / s['total'] * 100 if s['total'] > 0 else 0
        print(f"  {cat:<28s} {s['total']:>4d} {s['t1']:>3d}/{s['total']:<3d} {s['t3']:>3d}/{s['total']:<3d} {s['t5']:>3d}/{s['total']:<3d} {s['t10']:>3d}/{s['total']:<3d} {p1:>6.1f}% {p3:>6.1f}% {p5:>6.1f}% {p10:>6.1f}%")

    tmissed = [r for r in results if not r["type_top10_hit"]]
    if tmissed:
        print(f"\n小类 Top-10 未命中案例 ({len(tmissed)} 个):")
        for r in tmissed:
            print(f"  {r['root_cause_type']:<36s} (GT小类: {r['gt_type']}) -> 预测Top5: {' > '.join(r['predicted_top10_types'][:5]) or '(无)'}")


if __name__ == "__main__":
    asyncio.run(main())
