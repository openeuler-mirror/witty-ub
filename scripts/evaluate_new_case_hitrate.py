#!/usr/bin/env python3
"""评估 new_case 案例在当前案例库上的相似匹配命中率。

直接复用 latency.services.similarity.find_similar_fault_types，
无需后端服务运行。要求设置 WITTY_DIR 指向案例库根目录。

用法:
    WITTY_DIR=/Users/zhaoyujin/Desktop/witty-ub \
    PYTHONPATH=src/plugins python3 scripts/evaluate_new_case_hitrate.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# 确保 latency 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import find_similar_fault_types  # noqa: E402

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"
TOP_K = 100  # 取足够多再在本地截取 Top-5 大类

# new_case 的 root_cause_type（中文）→ 案例库大类 GT 映射
# 注意: 删除 etcd故障/其他 后，案例库剩余 9 个大类
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

    result = await find_similar_fault_types(features, fault_category, top_k=TOP_K)
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

    best = top_matches[0] if top_matches else {}
    return {
        "file": case.get("id", "") + ".json",
        "root_cause_type": rct,
        "gt_cat": gt_cat,
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
    print(f"案例库剩余大类: Client-挂死/网络, Client-退出, UB-UBSe/UBM管理进程故障, "
          f"UB-端口故障, UB-链路故障, Worker-缩容/挂死, Worker-退出/崩溃, Worker-重启, 网络/TCP故障")
    print("=" * 80)

    results = []
    for i, case in enumerate(cases, 1):
        r = await evaluate_one(case)
        results.append(r)
        print(f"[{i}/{len(cases)}] {r['file'][:40]}")
        print(f"    GT: {r['root_cause_type']} → {r['gt_cat']}")
        print(f"    预测Top5大类: {' > '.join(r['predicted_top5_cats']) or '(无)'}")
        print(f"    最佳子类型: {r['best_type']} ({r['best_cat']}) sim={r['best_sim']:.3f}")
        print(f"    命中: Top1={r['top1_hit']} Top3={r['top3_hit']} Top5={r['top5_hit']}")
        print()

    # 汇总
    total = len(results)
    hit1 = sum(1 for r in results if r["top1_hit"])
    hit3 = sum(1 for r in results if r["top3_hit"])
    hit5 = sum(1 for r in results if r["top5_hit"])

    print("=" * 80)
    print("命中率汇总")
    print("=" * 80)
    print(f"  总案例数: {total}")
    print(f"  Top-1 命中率: {hit1}/{total} = {hit1/total*100:.1f}%")
    print(f"  Top-3 命中率: {hit3}/{total} = {hit3/total*100:.1f}%")
    print(f"  Top-5 命中率: {hit5}/{total} = {hit5/total*100:.1f}%")

    # 按大类分组
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
    for cat in sorted(cat_stats.keys(), key=lambda c: cat_stats[c]["hit5"] / max(cat_stats[c]["total"], 1), reverse=True):
        s = cat_stats[cat]
        t1 = f"{s['hit1']}/{s['total']}"
        t3 = f"{s['hit3']}/{s['total']}"
        t5 = f"{s['hit5']}/{s['total']}"
        print(f"  {cat:<28s} {s['total']:>4d} {t1:>6s} {t3:>6s} {t5:>6s}")

    # 未命中案例
    missed = [r for r in results if not r["top5_hit"]]
    if missed:
        print(f"\nTop-5 未命中案例 ({len(missed)} 个):")
        for r in missed:
            print(f"  {r['root_cause_type']} (GT: {r['gt_cat']}) → 预测: {' > '.join(r['predicted_top5_cats']) or '(无)'}")

    # 保存
    output_path = "/Users/zhaoyujin/Desktop/witty-ub/scripts/new_case_hitrate_results.json"
    output = {
        "total": total,
        "top1_hit": hit1,
        "top3_hit": hit3,
        "top5_hit": hit5,
        "top1_rate": hit1 / total if total else 0,
        "top3_rate": hit3 / total if total else 0,
        "top5_rate": hit5 / total if total else 0,
        "cat_stats": cat_stats,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
