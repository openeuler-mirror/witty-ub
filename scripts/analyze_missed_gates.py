#!/usr/bin/env python3
"""分析未命中案例的维度得分，定位 cat_gate 和 asym_gate 的影响。"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.case_service import CASE_DIR
from latency.services.similarity import (
    FeatureVector,
    compute_similarity_detailed,
    load_case_library,
)

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"

# 大类映射（与 run_new_case_match.py 一致）
TYPE_TO_BROAD = {
    "本地UB单端口down": "UB-端口故障",
    "本地UB全部端口不可用": "UB-端口故障",
    "本地UB全部端口down": "UB-端口故障",
    "本地UB全部端口lane down": "UB-端口故障",
    "本地UB全部端口链路丢失": "UB-端口故障",
    "本地UB双端口闪断": "UB-端口故障",
    "本地UB单socket双端口down": "UB-端口故障",
    "本地UB双socket单端口down": "UB-端口故障",
    "远端UB单端口down": "UB-端口故障",
    "远端UB双socket单端口down": "UB-端口故障",
    "远端UB单socket双端口down": "UB-端口故障",
    "远端UB全部端口down": "UB-端口故障",
    "Worker本地UB链路down": "UB-链路故障",
    "Worker远端UB单链路down": "UB-链路故障",
    "Worker远端UB信号错误": "UB-链路故障",
    "Worker远端UB NFE": "UB-链路故障",
    "Worker远端UB CE": "UB-链路故障",
    "Worker远端UB FE": "UB-链路故障",
    "Worker远端本地UB单端口down": "UB-链路故障",
    "Worker远端本地UB链路丢失": "UB-链路故障",
    "Worker远端本地UB链路闪断": "UB-链路故障",
    "Worker远端本地UB lane down": "UB-链路故障",
    "Worker远端远端UB单端口down": "UB-链路故障",
    "Worker缩容远端UB NFE": "UB-链路故障",
    "Worker缩容远端UB链路down": "UB-链路故障",
    "Client获取UB失败": "UB-链路故障",
    "Worker进程退出": "Worker-退出/崩溃",
    "Worker进程被kill": "Worker-退出/崩溃",
    "Worker单节点进程退出": "Worker-退出/崩溃",
    "Worker Pod重启": "Worker-重启",
    "Worker Pod重启(L2)": "Worker-重启",
    "Worker单节点重启": "Worker-重启",
    "Worker发现进程挂死": "Worker-缩容/挂死",
    "Worker缩容Client退出": "Worker-缩容/挂死",
    "Worker缩容TCP丢包": "Worker-缩容/挂死",
    "Worker缩容Client挂死": "Worker-缩容/挂死",
    "Worker缩容TCP down": "Worker-缩容/挂死",
    "Client缩容Worker挂死": "Worker-缩容/挂死",
    "Client进程退出": "Client-退出",
    "Client进程退出启动": "Client-退出",
    "Client获取退出启动": "Client-退出",
    "Client进程挂死": "Client-挂死/网络",
    "Client获取挂死": "Client-挂死/网络",
    "Client TCP down": "Client-挂死/网络",
    "Client缩容TCP down": "Client-挂死/网络",
    "远端写入TCP延迟": "网络/TCP故障",
    "Worker跨节点网卡丢包": "网络/TCP故障",
    "Worker写入网卡丢包": "网络/TCP故障",
    "Worker网卡丢包": "网络/TCP故障",
    "Client Pod重启": "Client-退出",
    "Client进程跨节点退出": "Client-退出",
    "Client进程挂死(r)": "Client-挂死/网络",
    "SDK安装TCP网络down": "网络/TCP故障",
    "Worker带宽限制": "网络/TCP故障",
    "Worker UB端口闪断故障": "UB-端口故障",
    "Worker获取退出启动": "Worker-退出/崩溃",
    "Worker远端UB链路down": "UB-链路故障",
    "Client进程退出(跨节点)": "Client-退出",
    "Worker进程退出(跨节点)": "Worker-退出/崩溃",
    "Worker Pod L2重启": "Worker-重启",
    "Worker单节点重启": "Worker-重启",
    "远端Worker进程Set退出": "Worker-缩容/挂死",
    "Worker进程退出单节点": "Worker-退出/崩溃",
    "Worker进程Set退出": "Worker-退出/崩溃",
    "Worker Set退出": "Worker-退出/崩溃",
    "本地UB单Socket双端口Down": "UB-端口故障",
    "远端UB单Socket双端口Down": "UB-端口故障",
    "远端UB双Socket单端口Down": "UB-端口故障",
    "远端UB全端口Down": "UB-端口故障",
    "远端UB单端口Down": "UB-端口故障",
    "本地UB全端口Down": "UB-端口故障",
    "本地UB全端口Lane Down": "UB-端口故障",
    "本地UB全端口链路丢失": "UB-端口故障",
    "Client进程Set退出": "Client-退出",
    "Client进程Set退出启动": "Client-退出",
    "Client进程Get退出启动": "Client-退出",
    "Client进程Get挂死": "Client-挂死/网络",
    "Client进程Set挂死": "Client-挂死/网络",
    "Client进程TCP Down": "Client-挂死/网络",
    "Client缩容TCP Down": "Client-挂死/网络",
    "Worker进程跨节点网卡丢失": "网络/TCP故障",
    "Worker进程写网卡丢失": "网络/TCP故障",
    "Worker进程网卡丢失": "网络/TCP故障",
    "写远端TCP延迟": "网络/TCP故障",
    "Worker进程本地UB链路Down": "UB-链路故障",
    "Worker进程远端本地UB链路丢失": "UB-链路故障",
    "Worker进程远端本地UB闪断": "UB-链路故障",
    "Worker进程远端UB NFE故障": "UB-链路故障",
    "Worker进程远端UB CE故障": "UB-链路故障",
    "Worker进程远端UB单链路Down": "UB-链路故障",
    "Worker进程缩容远端UB链路Down": "UB-链路故障",
    "Worker进程缩容远端UB NFE故障": "UB-链路故障",
    "Worker进程远端远端UB单端口Down": "UB-链路故障",
    "Worker进程缩容Client退出": "Worker-缩容/挂死",
    "Worker进程缩容Client挂起": "Worker-缩容/挂死",
    "Worker进程缩容TCP丢包": "Worker-缩容/挂死",
    "Worker进程缩容TCP Down": "Worker-缩容/挂死",
}


def infer_expected_broad(rct: str) -> str:
    rct_lower = rct.lower() if rct else ""
    if "cpu" in rct_lower and "挂" in rct:
        return "Worker-缩容/挂死"
    if "sdk" in rct_lower and ("初始化" in rct or "配置" in rct):
        return "SDK初始化配置错误"
    if "ub端口" in rct_lower or "ub" in rct_lower and "端口" in rct:
        return "UB-端口故障"
    if "ub链路" in rct_lower or ("ub" in rct_lower and "链路" in rct):
        return "UB-链路故障"
    if "l1" in rct_lower and ("端口" in rct or "闪断" in rct or "shutdown" in rct_lower):
        return "网络/TCP故障"
    if "端侧" in rct and "l1" in rct_lower:
        return "网络/TCP故障"
    if "tcp" in rct_lower and "down" in rct_lower:
        return "网络/TCP故障"
    if "worker" in rct_lower and ("退出" in rct or "异常" in rct):
        return "Worker-退出/崩溃"
    if "交换机" in rct and "l1" in rct_lower:
        return "网络/TCP故障"
    return "未知"


def main():
    print("=" * 70)
    print("未命中案例的维度得分分析")
    print("=" * 70)

    # 加载案例库
    library_cases = load_case_library()
    print(f"案例库: {len(library_cases)} 个案例")

    # 按大类组织
    broad_cases = defaultdict(list)
    for case in library_cases:
        rct = case.get("root_cause_type", "")
        broad = TYPE_TO_BROAD.get(rct, "未分类")
        broad_cases[broad].append(case)

    print(f"\n各大类案例数:")
    for broad, items in sorted(broad_cases.items(), key=lambda x: -len(x[1])):
        # 统计 fault_category 分布
        fc_counter = defaultdict(int)
        for c in items:
            fc = c.get("fault_category", "?")
            fc_counter[fc] += 1
        fc_str = ", ".join(f"{k}={v}" for k, v in sorted(fc_counter.items()))
        print(f"  {broad:25s}  {len(items):3d} 个  ({fc_str})")

    # 加载测试案例
    with open("/Users/zhaoyujin/Desktop/witty-ub/scripts/new_case_hitrate_results.json",
              "r", encoding="utf-8") as f:
        results = json.load(f)

    missed_fnames = {r["test_case"] for r in results["results"] if not r["hit5"]}
    print(f"\n未命中(Top5)的测试案例: {len(missed_fnames)} 个")

    for fname in sorted(missed_fnames):
        fpath = os.path.join(NEW_CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            tc = json.load(f)

        rct = tc.get("root_cause_type", "")
        expected_broad = infer_expected_broad(rct)
        tc_fc = tc.get("fault_category", "?")

        print(f"\n{'=' * 70}")
        print(f"测试案例: {fname[:12]}  rct={rct}  预期={expected_broad}")
        print(f"  fault_category={tc_fc}")
        print(f"  has_latency={bool(tc.get('features', {}).get('latency'))}")
        print(f"  has_connectivity={bool(tc.get('features', {}).get('connectivity'))}")

        query_fv = FeatureVector(tc["features"], tc_fc)

        # 找出预期大类的案例，看 cat_gate 和 asym_gate
        if expected_broad in broad_cases:
            expected_items = broad_cases[expected_broad]
            print(f"\n  预期大类 {expected_broad} 的 {len(expected_items)} 个案例的 gate 统计:")
            cat_gates = []
            asym_gates = []
            final_scores = []
            base_scores = []
            for case in expected_items:
                case_fv = FeatureVector(case["features"], case.get("fault_category", "unknown"))
                detail = compute_similarity_detailed(query_fv, case_fv)
                cat_gates.append(detail["cat_gate"])
                asym_gates.append(detail["asym_gate"])
                final_scores.append(detail["final_score"])
                base_scores.append(detail["base_score"])

            print(f"    cat_gate: min={min(cat_gates):.2f} max={max(cat_gates):.2f} avg={sum(cat_gates)/len(cat_gates):.2f}")
            print(f"    asym_gate: min={min(asym_gates):.2f} max={max(asym_gates):.2f} avg={sum(asym_gates)/len(asym_gates):.2f}")
            print(f"    base_score: min={min(base_scores):.4f} max={max(base_scores):.4f} avg={sum(base_scores)/len(base_scores):.4f}")
            print(f"    final_score: min={min(final_scores):.4f} max={max(final_scores):.4f} avg={sum(final_scores)/len(final_scores):.4f}")

            # 对比：Top1 大类（误判大类）的 gate 统计
            top1_broad = results["results"][
                [r["test_case"] for r in results["results"]].index(fname)
            ]["top1"]
            if top1_broad in broad_cases:
                top1_items = broad_cases[top1_broad]
                print(f"\n  误判 Top1 大类 {top1_broad} 的 {len(top1_items)} 个案例的 gate 统计:")
                cat_gates2 = []
                asym_gates2 = []
                final_scores2 = []
                base_scores2 = []
                for case in top1_items:
                    case_fv = FeatureVector(case["features"], case.get("fault_category", "unknown"))
                    detail = compute_similarity_detailed(query_fv, case_fv)
                    cat_gates2.append(detail["cat_gate"])
                    asym_gates2.append(detail["asym_gate"])
                    final_scores2.append(detail["final_score"])
                    base_scores2.append(detail["base_score"])

                print(f"    cat_gate: min={min(cat_gates2):.2f} max={max(cat_gates2):.2f} avg={sum(cat_gates2)/len(cat_gates2):.2f}")
                print(f"    asym_gate: min={min(asym_gates2):.2f} max={max(asym_gates2):.2f} avg={sum(asym_gates2)/len(asym_gates2):.2f}")
                print(f"    base_score: min={min(base_scores2):.4f} max={max(base_scores2):.4f} avg={sum(base_scores2)/len(base_scores2):.4f}")
                print(f"    final_score: min={min(final_scores2):.4f} max={max(final_scores2):.4f} avg={sum(final_scores2)/len(final_scores2):.4f}")

                # 对比分析
                print(f"\n  对比分析:")
                exp_avg = sum(final_scores)/len(final_scores)
                top1_avg = sum(final_scores2)/len(final_scores2)
                print(f"    预期大类 avg_final={exp_avg:.4f}  vs  Top1大类 avg_final={top1_avg:.4f}")
                print(f"    预期大类 avg_cat_gate={sum(cat_gates)/len(cat_gates):.2f}  vs  Top1大类 avg_cat_gate={sum(cat_gates2)/len(cat_gates2):.2f}")
                print(f"    预期大类 avg_asym_gate={sum(asym_gates)/len(asym_gates):.2f}  vs  Top1大类 avg_asym_gate={sum(asym_gates2)/len(asym_gates2):.2f}")
        else:
            print(f"  ⚠ 案例库中没有 {expected_broad} 大类的案例！")


if __name__ == "__main__":
    main()
