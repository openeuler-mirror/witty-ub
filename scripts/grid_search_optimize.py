#!/usr/bin/env python3
"""网格搜索：在不改案例库的前提下，通过调整算法参数优化 Top1/3/5 命中率。

搜索空间:
1. failure_mode/status_code 余弦相似度低于阈值时是否零权重
2. cat_gate 不同故障类别间的惩罚系数
3. asym_penalty 单方缺失时的惩罚系数
4. 关键维度权重调整
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import math
import itertools
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import FeatureVector, load_case_library, merge_fault_type, _cosine_sim, _jaccard_sim, _scope_sim, _log_normalize, DIMENSION_LABELS

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


def load_new_cases():
    cases = []
    for fname in sorted(os.listdir(NEW_CASE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(NEW_CASE_DIR, fname), "r", encoding="utf-8") as f:
            c = json.load(f)
        if c.get("features"):
            cases.append(c)
    return cases


def compute_sim_custom(a, b, params):
    """可配置参数的相似度计算。"""
    dims = []
    
    # failure_mode
    a_has_fm = bool(a.failure_mode_dist)
    b_has_fm = bool(b.failure_mode_dist)
    if a_has_fm and b_has_fm:
        fm_sim = _cosine_sim(a.failure_mode_dist, b.failure_mode_dist)
        fm_weight = params["fm_weight"] if fm_sim >= params["fm_zero_threshold"] else 0.0
    elif not a_has_fm and not b_has_fm:
        fm_sim, fm_weight = 0.0, 0.0
    else:
        fm_sim, fm_weight = 0.0, 0.0
    fm_asym = params["fm_asym_penalty"] if (a_has_fm != b_has_fm) else 1.0
    dims.append({"name": "failure_mode", "score": fm_sim, "weight": fm_weight})

    # status_code
    a_has_sc = bool(a.status_code_dist)
    b_has_sc = bool(b.status_code_dist)
    if a_has_sc and b_has_sc:
        sc_sim = _cosine_sim(a.status_code_dist, b.status_code_dist)
        sc_weight = params["sc_weight"] if sc_sim >= params["sc_zero_threshold"] else 0.0
    elif not a_has_sc and not b_has_sc:
        sc_sim, sc_weight = 0.0, 0.0
    else:
        sc_sim, sc_weight = 0.0, 0.0
    sc_asym = params["sc_asym_penalty"] if (a_has_sc != b_has_sc) else 1.0
    dims.append({"name": "status_code", "score": sc_sim, "weight": sc_weight})

    # operation
    op_sim = _cosine_sim(a.operation_dist, b.operation_dist)
    if not a.operation_dist and not b.operation_dist: op_sim = 0.0
    dims.append({"name": "operation", "score": op_sim, "weight": params["op_weight"]})

    # conn_operation
    cop_sim = _cosine_sim(a.conn_operation_dist, b.conn_operation_dist)
    if not a.conn_operation_dist and not b.conn_operation_dist: cop_sim = 0.0
    dims.append({"name": "conn_operation", "score": cop_sim, "weight": params["cop_weight"]})

    # seg_ranking
    seg_r_sim = _cosine_sim(a.seg_ranking_vec, b.seg_ranking_vec)
    if not a.seg_ranking_vec and not b.seg_ranking_vec: seg_r_sim = 0.0
    dims.append({"name": "seg_ranking", "score": seg_r_sim, "weight": params["seg_ranking_weight"]})

    # seg_order
    if a.seg_ranking_ordered and b.seg_ranking_ordered:
        n = min(len(a.seg_ranking_ordered), len(b.seg_ranking_ordered), 5)
        pos = sum(1 for i in range(n) if a.seg_ranking_ordered[i] == b.seg_ranking_ordered[i])
        order_sim = pos / n if n > 0 else 0.0
    else:
        order_sim = 0.0
    dims.append({"name": "seg_order", "score": order_sim, "weight": params["seg_order_weight"]})

    # timeout_seg
    dims.append({"name": "timeout_seg", "score": _jaccard_sim(a.timeout_seg_set, b.timeout_seg_set), "weight": 2.0})
    # pod_conc
    dims.append({"name": "pod_conc", "score": _scope_sim(a.pod_concentration, b.pod_concentration), "weight": 1.5})
    # client_ratio
    cr_sim = math.exp(-abs(a.client_side_ratio - b.client_side_ratio) * 6) if (a.client_side_ratio > 0 or b.client_side_ratio > 0) else 0.0
    dims.append({"name": "client_ratio", "score": cr_sim, "weight": 2.5})
    # server_ratio
    sr_sim = math.exp(-abs(a.server_side_ratio - b.server_side_ratio) * 6) if (a.server_side_ratio > 0 or b.server_side_ratio > 0) else 0.0
    dims.append({"name": "server_ratio", "score": sr_sim, "weight": 2.5})
    # trace_pods
    ap_a = _log_normalize(a.trace_context_pods) if a.trace_context_pods > 0 else 0
    ap_b = _log_normalize(b.trace_context_pods) if b.trace_context_pods > 0 else 0
    ap_sim = math.exp(-abs(ap_a - ap_b) * 3) if (ap_a > 0 or ap_b > 0) else 0.0
    dims.append({"name": "trace_pods", "score": ap_sim, "weight": 2.5})
    # anomalous_ratio
    ar_sim = math.exp(-abs(a.anomalous_ratio - b.anomalous_ratio) * 3) if (a.anomalous_ratio > 0 or b.anomalous_ratio > 0) else 0.0
    dims.append({"name": "anomalous_ratio", "score": ar_sim, "weight": 1.5})
    # scopes
    dims.append({"name": "pod_scope", "score": _scope_sim(a.pod_scope, b.pod_scope), "weight": 1.0})
    dims.append({"name": "host_scope", "score": _scope_sim(a.host_scope, b.host_scope), "weight": 1.0})
    dims.append({"name": "cluster_scope", "score": _scope_sim(a.cluster_scope, b.cluster_scope), "weight": 1.0})
    # p99_p50
    if a.p99_p50_log > 0 and b.p99_p50_log > 0:
        p99_sim = math.exp(-abs(a.p99_p50_log - b.p99_p50_log) * 3)
    else:
        p99_sim = 0.0
    dims.append({"name": "p99_p50", "score": p99_sim, "weight": 2.0})
    # op_p99_p50
    op_p99_sim = _cosine_sim(a.op_p99_p50_log, b.op_p99_p50_log)
    if not a.op_p99_p50_log and not b.op_p99_p50_log: op_p99_sim = 0.0
    dims.append({"name": "op_p99_p50", "score": op_p99_sim, "weight": params["op_p99_weight"]})

    total_weight = sum(d["weight"] for d in dims)
    base = sum(d["score"] * d["weight"] for d in dims) / total_weight if total_weight > 0 else 0.0
    
    cat_gate = 1.0 if a.fault_category == b.fault_category else params["cat_gate"]
    asym_gate = fm_asym * sc_asym
    return base * cat_gate * asym_gate


async def evaluate_params(params, cases, library_cases):
    """用给定参数评估所有测试案例，返回 (top1, top3, top5)。"""
    results = []
    for case in cases:
        features = case["features"]
        fc = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")
        case_id = case.get("id", "")
        log_file_id = case.get("log_file_id", "")
        
        qfv = FeatureVector(features, fc)
        
        scored = []
        for lib_case in library_cases:
            if lib_case.get("id") == case_id or lib_case.get("log_file_id") == log_file_id:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))
            sim = compute_sim_custom(qfv, lib_fv, params)
            if sim >= 0.999:
                continue
            scored.append((sim, lib_case.get("case_category", ""), merge_fault_type(lib_case["root_cause_type"])))
        
        scored.sort(key=lambda x: -x[0])
        seen_cats = []
        for sim, cat, rct_name in scored:
            if cat and cat not in seen_cats:
                seen_cats.append(cat)
            if len(seen_cats) >= 5:
                break
        
        top1 = gt_cat in seen_cats[:1]
        top3 = gt_cat in seen_cats[:3]
        top5 = gt_cat in seen_cats[:5]
        results.append((top1, top3, top5))
    
    n = len(results)
    return sum(1 for r in results if r[0]), sum(1 for r in results if r[1]), sum(1 for r in results if r[2])


async def main():
    cases = load_new_cases()
    library_cases = load_case_library()
    print(f"测试案例: {len(cases)}, 案例库: {len(library_cases)}")
    
    # 基线参数
    baseline = {
        "fm_weight": 6.0, "sc_weight": 4.0,
        "fm_zero_threshold": 0.0, "sc_zero_threshold": 0.0,
        "fm_asym_penalty": 0.6, "sc_asym_penalty": 0.7,
        "cat_gate": 0.6,
        "op_weight": 3.0, "cop_weight": 2.0,
        "seg_ranking_weight": 3.0, "seg_order_weight": 3.0,
        "op_p99_weight": 4.0,
    }
    
    h1, h3, h5 = await evaluate_params(baseline, cases, library_cases)
    print(f"\n基线: Top1={h1} Top3={h3} Top5={h5}")
    print("=" * 80)
    
    best = (h1, h3, h5, "baseline", baseline)
    
    # 搜索1: fm/sc 零权重阈值
    print("\n[搜索1] fm/sc 余弦相似度低于阈值时零权重")
    for fm_thresh, sc_thresh in [(0.01, 0.01), (0.05, 0.05), (0.1, 0.1), (0.01, 0.0), (0.0, 0.01)]:
        p = dict(baseline)
        p["fm_zero_threshold"] = fm_thresh
        p["sc_zero_threshold"] = sc_thresh
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        tag = f"fm_thresh={fm_thresh} sc_thresh={sc_thresh}"
        print(f"  {tag:<35s} Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, tag, p)
    
    # 搜索2: cat_gate
    print("\n[搜索2] cat_gate 惩罚系数")
    best_p = best[4]
    for cg in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        p = dict(best_p)
        p["cat_gate"] = cg
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  cat_gate={cg:<5.1f}                       Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"cat_gate={cg}", p)
    
    # 搜索3: asym_penalty
    print("\n[搜索3] asym_penalty")
    best_p = best[4]
    for fm_asym, sc_asym in [(0.6, 0.7), (0.8, 0.8), (0.9, 0.9), (1.0, 1.0), (0.5, 0.6)]:
        p = dict(best_p)
        p["fm_asym_penalty"] = fm_asym
        p["sc_asym_penalty"] = sc_asym
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  fm_asym={fm_asym} sc_asym={sc_asym}             Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"fm_asym={fm_asym} sc_asym={sc_asym}", p)
    
    # 搜索4: op_p99_p50 权重
    print("\n[搜索4] op_p99_p50 权重")
    best_p = best[4]
    for w in [2.0, 3.0, 4.0, 5.0, 6.0]:
        p = dict(best_p)
        p["op_p99_weight"] = w
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  op_p99_weight={w:<4.1f}                    Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"op_p99_weight={w}", p)
    
    # 搜索5: seg_ranking / seg_order 权重组合
    print("\n[搜索5] seg_ranking / seg_order 权重组合")
    best_p = best[4]
    for sr, so in [(3.0, 3.0), (4.0, 4.0), (5.0, 2.0), (2.0, 5.0), (4.0, 2.0), (2.0, 4.0), (5.0, 5.0)]:
        p = dict(best_p)
        p["seg_ranking_weight"] = sr
        p["seg_order_weight"] = so
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  seg_ranking={sr} seg_order={so}            Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"seg_ranking={sr} seg_order={so}", p)
    
    # 搜索6: fm/sc 权重
    print("\n[搜索6] fm/sc 权重（零阈值已设时）")
    best_p = dict(best[4])
    for fm_w, sc_w in [(6.0, 4.0), (4.0, 3.0), (8.0, 6.0), (3.0, 2.0), (10.0, 8.0)]:
        p = dict(best_p)
        p["fm_weight"] = fm_w
        p["sc_weight"] = sc_w
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  fm_weight={fm_w} sc_weight={sc_w}            Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"fm_weight={fm_w} sc_weight={sc_w}", p)
    
    # 搜索7: 组合搜索（最佳参数附近）
    print("\n[搜索7] 组合搜索")
    best_p = dict(best[4])
    combos = [
        {"fm_zero_threshold": 0.01, "sc_zero_threshold": 0.01, "cat_gate": 0.8, "fm_asym_penalty": 0.8, "sc_asym_penalty": 0.8},
        {"fm_zero_threshold": 0.05, "sc_zero_threshold": 0.05, "cat_gate": 0.7, "fm_asym_penalty": 0.9, "sc_asym_penalty": 0.9},
        {"fm_zero_threshold": 0.01, "sc_zero_threshold": 0.01, "cat_gate": 0.9, "fm_asym_penalty": 1.0, "sc_asym_penalty": 1.0},
        {"fm_zero_threshold": 0.1, "sc_zero_threshold": 0.1, "cat_gate": 0.8, "fm_asym_penalty": 1.0, "sc_asym_penalty": 1.0},
        {"fm_zero_threshold": 0.01, "sc_zero_threshold": 0.01, "cat_gate": 1.0, "fm_asym_penalty": 1.0, "sc_asym_penalty": 1.0},
    ]
    for i, override in enumerate(combos):
        p = dict(best_p)
        p.update(override)
        h1, h3, h5 = await evaluate_params(p, cases, library_cases)
        print(f"  组合{i+1}: {override}")
        print(f"         Top1={h1} Top3={h3} Top5={h5}")
        if h5 > best[2] or (h5 == best[2] and h3 > best[1]):
            best = (h1, h3, h5, f"combo{i+1}", p)
    
    print("\n" + "=" * 80)
    print(f"最优参数: {best[3]}")
    print(f"  Top1={best[0]} Top3={best[1]} Top5={best[2]}")
    print(f"  参数: {json.dumps(best[4], indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
