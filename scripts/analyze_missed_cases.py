#!/usr/bin/env python3
"""详细分析未命中案例的匹配情况，展示每个维度的得分。"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import find_similar_fault_types

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"

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

MISSED_FILES = [
    "282ec9a1-f966-4ea4-b868-3ab9ac8b189c.json",  # SDK初始化配置错误
    "8d0ecae9-8a56-48f5-b3ba-3bcb82624ce3.json",  # UB链路故障
    "b8a2bfc9-ad70-43f2-9e23-d124b37e5f1e.json",  # 端侧到L1端口故障
    "e8620e4d-e6d2-43e5-ba60-b287fdab5c0c.json",  # UB交换机L1上行端口闪断
    "f012208a-243f-457a-a45c-f164a9c4072f.json",  # L1-L2互联链路闪断
]


async def analyze():
    for fname in MISSED_FILES:
        fpath = os.path.join(NEW_CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            case = json.load(f)

        features = case["features"]
        fault_category = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")

        result = await find_similar_fault_types(features, fault_category, top_k=10)
        top_matches = result.get("top_matches", [])

        print("=" * 100)
        print(f"案例: {rct}  (文件: {fname[:12]}...)")
        print(f"GT大类: {gt_cat}")
        print(f"fault_category: {fault_category}")
        print(f"特征摘要: latency={'有' if features.get('latency') else '无'} "
              f"connectivity={'有' if features.get('connectivity') else '无'}")
        if features.get("latency"):
            lat = features["latency"]
            print(f"  latency: seg_ranking={[s[0] for s in lat.get('segment_ranking', [])][:5]}")
            print(f"           p99_p50={lat.get('p99_p50_ratio', 'N/A'):.3f} "
                  f"pod_conc={lat.get('pod_concentration')} "
                  f"anom_ratio={lat.get('anomalous_ratio', 0):.3f}")
        if features.get("connectivity"):
            conn = features["connectivity"]
            fm_top = dict(sorted(conn.get("failure_mode_dist", {}).items(), key=lambda x: -x[1])[:5])
            print(f"  connectivity: fm_dist_top={fm_top}")
            print(f"                sc_dist={conn.get('status_code_dist', {})}")
            print(f"                pod_scope={conn.get('spatial_pod', {}).get('scope')} "
                  f"host_scope={conn.get('spatial_host', {}).get('scope')}")
        print()

        # 找 GT 大类在 top_matches 中的排位
        gt_rank = None
        gt_matches = []
        for i, m in enumerate(top_matches):
            if m.get("case_category") == gt_cat:
                if gt_rank is None:
                    gt_rank = i + 1
                gt_matches.append(m)

        print(f"GT大类在预测中的排位: {'第' + str(gt_rank) + '位' if gt_rank else '未进入Top10'}")
        if gt_matches:
            print(f"GT大类最佳匹配案例: {gt_matches[0]['root_cause_type']} "
                  f"sim={gt_matches[0]['similarity']:.4f}")
        print()

        # 展示 Top5 预测
        print("预测 Top5:")
        for m in top_matches[:5]:
            cat = m.get("case_category", "")
            is_gt = " ← GT" if cat == gt_cat else ""
            print(f"  #{m['rank']} [{cat}] {m['root_cause_type']} "
                  f"sim={m['similarity']:.4f} base={m['base_score']:.4f} "
                  f"gate={m['cat_gate']:.2f}{is_gt}")
            # 展示 top3 维度
            breakdown = m.get("breakdown", [])
            for d in breakdown[:5]:
                print(f"       {d.get('label', d['name']):<18s} score={d['score']:.3f} "
                      f"weight={d['weight']:.1f} w_score={d['weighted_score']:.3f}")
            print(f"       reason: {m['reason'][:150]}")
        print()

        # 如果 GT 大类有匹配但不在 Top5，展示 GT 最佳匹配的维度详情
        if gt_matches and gt_rank and gt_rank > 5:
            gm = gt_matches[0]
            print(f"GT大类最佳匹配维度详情 (sim={gm['similarity']:.4f}):")
            for d in gm.get("breakdown", []):
                print(f"  {d.get('label', d['name']):<18s} score={d['score']:.3f} weight={d['weight']:.1f} "
                      f"w_score={d['weighted_score']:.3f}")
            print()

    # 汇总案例库中各大类案例
    print("\n" + "=" * 100)
    print("案例库中 UB-端口故障 和 UB-链路故障 的案例:")
    case_dir = os.path.join(os.path.dirname(__file__), "..", "case")
    for fname_lib in sorted(os.listdir(case_dir)):
        if not fname_lib.endswith(".json") or fname_lib == "_categories.json":
            continue
        with open(os.path.join(case_dir, fname_lib), "r", encoding="utf-8") as f:
            c = json.load(f)
        cat = c.get("case_category", "")
        if cat in ("UB-端口故障", "UB-链路故障"):
            feat = c.get("features", {})
            lat = feat.get("latency") or {}
            conn = feat.get("connectivity") or {}
            seg = [s[0] for s in lat.get("segment_ranking", [])][:5]
            fm = dict(sorted(conn.get("failure_mode_dist", {}).items(),
                            key=lambda x: -x[1])[:3]) if conn else {}
            sc = conn.get("status_code_dist", {}) if conn else {}
            print(f"  [{cat}] {c['root_cause_type']:<30s} "
                  f"fc={feat.get('fault_category','?'):<5s} "
                  f"seg={seg}")
            if fm:
                print(f"    fm_top={fm}  sc={sc}  "
                      f"pod_scope={conn.get('spatial_pod',{}).get('scope','?')}")


if __name__ == "__main__":
    asyncio.run(analyze())
