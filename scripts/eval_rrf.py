#!/usr/bin/env python3
"""Reciprocal Rank Fusion (RRF) 策略评估。

对每个维度独立计算类别排名，然后用 RRF 公式融合：
  RRF(cat) = sum( 1/(k + rank_d(cat)) ) for each dimension d

优势：当不同维度给出冲突的排名时（如 fm 说 UB-链路#1，seg 说 UB-端口#1），
RRF 能让两个类别都获得高分，而不是被单一高权重维度主导。
"""
from __future__ import annotations

import json
import os
import sys
import math
from collections import defaultdict
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.similarity import (
    FeatureVector, load_case_library, merge_fault_type,
    _cosine_sim, _jaccard_sim, _scope_sim, _log_normalize,
)

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


def compute_dim_scores(a, b):
    """返回每个维度的 (score, weight) 字典。"""
    dims = {}

    # failure_mode
    a_has_fm, b_has_fm = bool(a.failure_mode_dist), bool(b.failure_mode_dist)
    if a_has_fm and b_has_fm:
        dims["fm"] = _cosine_sim(a.failure_mode_dist, b.failure_mode_dist)
    else:
        dims["fm"] = 0.0

    # status_code
    a_has_sc, b_has_sc = bool(a.status_code_dist), bool(b.status_code_dist)
    if a_has_sc and b_has_sc:
        dims["sc"] = _cosine_sim(a.status_code_dist, b.status_code_dist)
    else:
        dims["sc"] = 0.0

    # operation
    op_sim = _cosine_sim(a.operation_dist, b.operation_dist)
    if not a.operation_dist and not b.operation_dist:
        op_sim = 0.0
    dims["op"] = op_sim

    # conn_operation
    cop_sim = _cosine_sim(a.conn_operation_dist, b.conn_operation_dist)
    if not a.conn_operation_dist and not b.conn_operation_dist:
        cop_sim = 0.0
    dims["cop"] = cop_sim

    # seg_ranking
    sr = _cosine_sim(a.seg_ranking_vec, b.seg_ranking_vec)
    if not a.seg_ranking_vec and not b.seg_ranking_vec:
        sr = 0.0
    dims["seg_r"] = sr

    # seg_order
    if a.seg_ranking_ordered and b.seg_ranking_ordered:
        n = min(len(a.seg_ranking_ordered), len(b.seg_ranking_ordered), 5)
        pos = sum(1 for i in range(n) if a.seg_ranking_ordered[i] == b.seg_ranking_ordered[i])
        dims["seg_o"] = pos / n if n > 0 else 0.0
    else:
        dims["seg_o"] = 0.0

    # timeout_seg
    dims["ts"] = _jaccard_sim(a.timeout_seg_set, b.timeout_seg_set)

    # pod_conc
    dims["pc"] = _scope_sim(a.pod_concentration, b.pod_concentration)

    # client_ratio
    if a.client_side_ratio > 0 or b.client_side_ratio > 0:
        dims["cr"] = math.exp(-abs(a.client_side_ratio - b.client_side_ratio) * 6)
    else:
        dims["cr"] = 0.0

    # server_ratio
    if a.server_side_ratio > 0 or b.server_side_ratio > 0:
        dims["sr_ratio"] = math.exp(-abs(a.server_side_ratio - b.server_side_ratio) * 6)
    else:
        dims["sr_ratio"] = 0.0

    # trace_pods
    ap_a = _log_normalize(a.trace_context_pods) if a.trace_context_pods > 0 else 0
    ap_b = _log_normalize(b.trace_context_pods) if b.trace_context_pods > 0 else 0
    if ap_a > 0 or ap_b > 0:
        dims["tp"] = math.exp(-abs(ap_a - ap_b) * 3)
    else:
        dims["tp"] = 0.0

    # anomalous
    if a.anomalous_ratio > 0 or b.anomalous_ratio > 0:
        dims["ar"] = math.exp(-abs(a.anomalous_ratio - b.anomalous_ratio) * 3)
    else:
        dims["ar"] = 0.0

    # p99_p50
    if a.p99_p50_log > 0 and b.p99_p50_log > 0:
        dims["p99"] = math.exp(-abs(a.p99_p50_log - b.p99_p50_log) * 3)
    else:
        dims["p99"] = 0.0

    # op_p99_p50
    op99 = _cosine_sim(a.op_p99_p50_log, b.op_p99_p50_log)
    if not a.op_p99_p50_log and not b.op_p99_p50_log:
        op99 = 0.0
    dims["op99"] = op99

    # scopes
    dims["pod_sc"] = _scope_sim(a.pod_scope, b.pod_scope)
    dims["host_sc"] = _scope_sim(a.host_scope, b.host_scope)
    dims["cluster_sc"] = _scope_sim(a.cluster_scope, b.cluster_scope)

    return dims


def evaluate_rrf(cases, library_cases, top_k=5, k_param=10, dim_weights=None):
    """RRF 策略评估。

    对每个维度：计算每个库案例的分数 → 按类别取最高 → 类别排名 → RRF 融合。
    """
    if dim_weights is None:
        # Default: all dimensions equally weighted
        dim_weights = {d: 1.0 for d in ["fm", "sc", "op", "cop", "seg_r", "seg_o", "ts", "pc", "cr", "sr_ratio", "tp", "ar", "p99", "op99", "pod_sc", "host_sc", "cluster_sc"]}

    results = []
    for case in cases:
        features = case["features"]
        fc = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")
        case_id = case.get("id", "")
        log_file_id = case.get("log_file_id", "")
        qfv = FeatureVector(features, fc)

        # Step 1: For each library case, compute all dimension scores
        case_dims = []
        for lib_case in library_cases:
            if lib_case.get("id") == case_id or lib_case.get("log_file_id") == log_file_id:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))
            cat = lib_case.get("case_category", "")
            dims = compute_dim_scores(qfv, lib_fv)
            case_dims.append((cat, dims))

        # Step 2: For each dimension, compute category-level best score
        dim_names = list(dim_weights.keys())
        dim_cat_scores = {d: defaultdict(float) for d in dim_names}
        for cat, dims in case_dims:
            for d in dim_names:
                if dims[d] > dim_cat_scores[d][cat]:
                    dim_cat_scores[d][cat] = dims[d]

        # Step 3: For each dimension, rank categories
        dim_cat_ranks = {}
        for d in dim_names:
            sorted_cats = sorted(dim_cat_scores[d].items(), key=lambda x: -x[1])
            dim_cat_ranks[d] = {cat: i + 1 for i, (cat, _) in enumerate(sorted_cats)}

        # Step 4: RRF fusion
        all_cats = set()
        for d in dim_names:
            all_cats.update(dim_cat_ranks[d].keys())

        rrf_scores = {}
        for cat in all_cats:
            rrf = 0.0
            for d in dim_names:
                rank = dim_cat_ranks[d].get(cat, 999)
                w = dim_weights[d]
                rrf += w / (k_param + rank)
            rrf_scores[cat] = rrf

        ranked = sorted(rrf_scores.items(), key=lambda x: -x[1])
        final_cats = [c for c, _ in ranked[:top_k]]

        t1 = gt_cat in final_cats[:1]
        t3 = gt_cat in final_cats[:3]
        t5 = gt_cat in final_cats[:5]
        pos = final_cats.index(gt_cat) + 1 if gt_cat in final_cats else 0
        results.append((rct, gt_cat, final_cats, t1, t3, t5, pos))

    h1 = sum(1 for r in results if r[3])
    h3 = sum(1 for r in results if r[4])
    h5 = sum(1 for r in results if r[5])
    return h1, h3, h5, results


def evaluate_hybrid_rrf(cases, library_cases, top_k=5, k_param=10, rrf_weight=0.3):
    """混合策略：加权平均分 * (1-rrf_weight) + RRF * rrf_weight"""
    results = []
    for case in cases:
        features = case["features"]
        fc = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")
        case_id = case.get("id", "")
        log_file_id = case.get("log_file_id", "")
        qfv = FeatureVector(features, fc)

        # Compute per-case dimension scores
        case_dims = []
        for lib_case in library_cases:
            if lib_case.get("id") == case_id or lib_case.get("log_file_id") == log_file_id:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))
            cat = lib_case.get("case_category", "")
            dims = compute_dim_scores(qfv, lib_fv)
            # Also compute weighted score (same as current algorithm)
            weights = {"fm": 6.0, "sc": 4.0, "op": 3.0, "cop": 2.0, "seg_r": 3.0, "seg_o": 3.0,
                       "ts": 3.0, "pc": 1.5, "cr": 2.5, "sr_ratio": 2.5, "tp": 1.5, "ar": 0.5,
                       "p99": 2.0, "op99": 5.0, "pod_sc": 1.0, "host_sc": 1.0, "cluster_sc": 1.0}
            total_w = sum(weights[d] for d in dims)
            weighted_score = sum(dims[d] * weights[d] for d in dims) / total_w if total_w > 0 else 0.0
            cat_gate = 1.0 if fc == lib_case.get("fault_category", "unknown") else 0.6
            final_score = weighted_score * cat_gate
            case_dims.append((cat, final_score, dims))

        # Standard dedup with count_bonus
        case_dims.sort(key=lambda x: -x[1])
        case_dims = [(c, s, d) for c, s, d in case_dims if s < 0.999]
        cc = defaultdict(int)
        for s, c, d in [(s, c, d) for c, s, d in case_dims[:5]]:
            if c:
                cc[c] += 1
        std_scores = {}
        for c, s, d in case_dims:
            if c and c not in std_scores:
                std_scores[c] = s + 0.02 * max(cc.get(c, 1) - 1, 0)

        # RRF per-dimension ranking
        dim_names = ["fm", "sc", "op", "cop", "seg_r", "seg_o", "ts", "pc", "cr", "sr_ratio", "tp", "ar", "p99", "op99", "pod_sc", "host_sc", "cluster_sc"]
        dim_cat_scores = {d: defaultdict(float) for d in dim_names}
        for cat, s, dims in case_dims:
            for d in dim_names:
                if dims[d] > dim_cat_scores[d][cat]:
                    dim_cat_scores[d][cat] = dims[d]

        dim_cat_ranks = {}
        for d in dim_names:
            sorted_cats = sorted(dim_cat_scores[d].items(), key=lambda x: -x[1])
            dim_cat_ranks[d] = {cat: i + 1 for i, (cat, _) in enumerate(sorted_cats)}

        all_cats = set(std_scores.keys())
        for d in dim_names:
            all_cats.update(dim_cat_ranks[d].keys())

        combined = {}
        for cat in all_cats:
            std_s = std_scores.get(cat, 0.0)
            rrf = 0.0
            for d in dim_names:
                rank = dim_cat_ranks[d].get(cat, 999)
                rrf += 1.0 / (k_param + rank)
            # Normalize RRF to 0-1 range (max possible = sum(1/(k+1)) for each dim)
            max_rrf = len(dim_names) / (k_param + 1)
            rrf_norm = rrf / max_rrf if max_rrf > 0 else 0.0
            combined[cat] = std_s * (1 - rrf_weight) + rrf_norm * rrf_weight

        ranked = sorted(combined.items(), key=lambda x: -x[1])
        final_cats = [c for c, _ in ranked[:top_k]]

        t1 = gt_cat in final_cats[:1]
        t3 = gt_cat in final_cats[:3]
        t5 = gt_cat in final_cats[:5]
        pos = final_cats.index(gt_cat) + 1 if gt_cat in final_cats else 0
        results.append((rct, gt_cat, final_cats, t1, t3, t5, pos))

    h1 = sum(1 for r in results if r[3])
    h3 = sum(1 for r in results if r[4])
    h5 = sum(1 for r in results if r[5])
    return h1, h3, h5, results


async def main():
    cases = load_new_cases()
    library_cases = load_case_library()
    print(f"测试案例: {len(cases)}, 案例库: {len(library_cases)}")
    print("=" * 100)

    # Strategy 1: Pure RRF with different k values
    print("\n[策略1] 纯 RRF（不同 k 参数）")
    best_rrf = (0, 0, 0, None)
    for k_param in [1, 3, 5, 10, 20, 30, 60]:
        h1, h3, h5, results = evaluate_rrf(cases, library_cases, k_param=k_param)
        target_info = []
        for rct, gt, cats, t1, t3, t5, pos in results:
            if rct in ("端侧到L1端口故障", "UB交换机L1的上行端口闪断", "L1-L2互联链路反复shutdown模拟链路闪断"):
                target_info.append(f"{rct[:6]}={pos if pos else 'X'}")
        print(f"  k={k_param:<3d}: Top1={h1} Top3={h3} Top5={h5}  [{', '.join(target_info)}]")
        if h5 > best_rrf[2] or (h5 == best_rrf[2] and h3 > best_rrf[1]) or (h5 == best_rrf[2] and h3 == best_rrf[1] and h1 > best_rrf[0]):
            best_rrf = (h1, h3, h5, k_param)

    # Show details for best k
    print(f"\n  最优 k={best_rrf[3]}: Top1={best_rrf[0]} Top3={best_rrf[1]} Top5={best_rrf[2]}")
    h1, h3, h5, results = evaluate_rrf(cases, library_cases, k_param=best_rrf[3])
    for rct, gt, cats, t1, t3, t5, pos in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct:30s} GT={gt:25s} pos={pos if pos else 'miss'}  top5={cats}")

    # Strategy 2: Weighted RRF (emphasize seg dimensions)
    print("\n[策略2] 加权 RRF（seg 维度加权）")
    seg_weights = {"seg_r": 2.0, "seg_o": 2.0, "ts": 1.5, "op99": 1.5, "fm": 0.5, "sc": 0.5}
    dim_w = {d: 1.0 for d in ["fm", "sc", "op", "cop", "seg_r", "seg_o", "ts", "pc", "cr", "sr_ratio", "tp", "ar", "p99", "op99", "pod_sc", "host_sc", "cluster_sc"]}
    dim_w.update(seg_weights)
    best_wr = (0, 0, 0, None)
    for k_param in [1, 3, 5, 10, 20]:
        h1, h3, h5, results = evaluate_rrf(cases, library_cases, k_param=k_param, dim_weights=dim_w)
        target_info = []
        for rct, gt, cats, t1, t3, t5, pos in results:
            if rct in ("端侧到L1端口故障", "UB交换机L1的上行端口闪断", "L1-L2互联链路反复shutdown模拟链路闪断"):
                target_info.append(f"{rct[:6]}={pos if pos else 'X'}")
        print(f"  k={k_param:<3d}: Top1={h1} Top3={h3} Top5={h5}  [{', '.join(target_info)}]")
        if h5 > best_wr[2] or (h5 == best_wr[2] and h3 > best_wr[1]) or (h5 == best_wr[2] and h3 == best_wr[1] and h1 > best_wr[0]):
            best_wr = (h1, h3, h5, k_param)

    # Strategy 3: Hybrid (standard score + RRF)
    print("\n[策略3] 混合（标准分数 + RRF）")
    best_hy = (0, 0, 0, None)
    for rrf_w in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        for k_param in [3, 5, 10]:
            h1, h3, h5, results = evaluate_hybrid_rrf(cases, library_cases, k_param=k_param, rrf_weight=rrf_w)
            if h5 > best_hy[2] or (h5 == best_hy[2] and h3 > best_hy[1]) or (h5 == best_hy[2] and h3 == best_hy[1] and h1 > best_hy[0]):
                best_hy = (h1, h3, h5, (rrf_w, k_param))
            if rrf_w in [0.2, 0.3, 0.5] and k_param == 10:
                target_info = []
                for rct, gt, cats, t1, t3, t5, pos in results:
                    if rct in ("端侧到L1端口故障", "UB交换机L1的上行端口闪断", "L1-L2互联链路反复shutdown模拟链路闪断"):
                        target_info.append(f"{rct[:6]}={pos if pos else 'X'}")
                print(f"  rrf_w={rrf_w} k={k_param}: Top1={h1} Top3={h3} Top5={h5}  [{', '.join(target_info)}]")

    print(f"\n  最优: rrf_w={best_hy[3][0]} k={best_hy[3][1]}: Top1={best_hy[0]} Top3={best_hy[1]} Top5={best_hy[2]}")
    h1, h3, h5, results = evaluate_hybrid_rrf(cases, library_cases, k_param=best_hy[3][1], rrf_weight=best_hy[3][0])
    for rct, gt, cats, t1, t3, t5, pos in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct:30s} GT={gt:25s} pos={pos if pos else 'miss'}  top5={cats}")

    # Summary
    print("\n" + "=" * 100)
    print("汇总:")
    print(f"  当前最优(标准+count_bonus):           Top1=4 Top3=5 Top5=6")
    print(f"  纯RRF(k={best_rrf[3]}):              Top1={best_rrf[0]} Top3={best_rrf[1]} Top5={best_rrf[2]}")
    print(f"  加权RRF(k={best_wr[3]}):              Top1={best_wr[0]} Top3={best_wr[1]} Top5={best_wr[2]}")
    print(f"  混合(rrf_w={best_hy[3][0]},k={best_hy[3][1]}):  Top1={best_hy[0]} Top3={best_hy[1]} Top5={best_hy[2]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
