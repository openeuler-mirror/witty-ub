#!/usr/bin/env python3
"""高级评估：测试多种匹配策略以提升 Top1/3/5 命中率。

策略：
1. 基线（当前算法，op_p99_weight=5.0）
2. 类别投票法：取 top-N 个体案例，按类别加权求和排名
3. 类别质心法：对每个类别计算平均特征向量，与查询匹配
4. 两阶段法：先用 latency-only 特征筛选候选类别，再用全特征精排
5. 混合法：基线分数 + 类别投票加分
"""
from __future__ import annotations

import asyncio
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
    compute_similarity_detailed, DIMENSION_LABELS,
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


# ============================================================
# Strategy 1: Baseline (current algorithm)
# ============================================================
def evaluate_baseline(cases, library_cases, top_k=5):
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
            detail = compute_similarity_detailed(qfv, lib_fv)
            if detail["final_score"] >= 0.999:
                continue
            scored.append((detail["final_score"], lib_case.get("case_category", ""), merge_fault_type(lib_case["root_cause_type"])))

        scored.sort(key=lambda x: -x[0])
        seen_cats = []
        for sim, cat, rct_name in scored:
            if cat and cat not in seen_cats:
                seen_cats.append(cat)
            if len(seen_cats) >= top_k:
                break

        top1 = gt_cat in seen_cats[:1]
        top3 = gt_cat in seen_cats[:3]
        top5 = gt_cat in seen_cats[:5]
        results.append((rct, gt_cat, seen_cats[:5], top1, top3, top5))

    n = len(results)
    return results, sum(1 for r in results if r[3]), sum(1 for r in results if r[4]), sum(1 for r in results if r[5])


# ============================================================
# Strategy 2: Category Voting (weighted sum of top-N cases)
# ============================================================
def evaluate_category_voting(cases, library_cases, top_k=5, vote_n=20, vote_weight=0.3):
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
            detail = compute_similarity_detailed(qfv, lib_fv)
            if detail["final_score"] >= 0.999:
                continue
            scored.append((detail["final_score"], lib_case.get("case_category", ""), merge_fault_type(lib_case["root_cause_type"])))

        scored.sort(key=lambda x: -x[0])

        # Standard dedup (top-1 per category)
        seen_cats = {}
        for sim, cat, rct_name in scored:
            if cat and cat not in seen_cats:
                seen_cats[cat] = sim

        # Voting: sum of top-N cases per category
        cat_votes = defaultdict(lambda: {"sum": 0.0, "count": 0, "max": 0.0})
        for sim, cat, rct_name in scored[:vote_n]:
            if cat:
                cat_votes[cat]["sum"] += sim
                cat_votes[cat]["count"] += 1
                cat_votes[cat]["max"] = max(cat_votes[cat]["max"], sim)

        # Combined score: max_score + vote_weight * (sum - max) / vote_n
        cat_combined = {}
        for cat, votes in cat_votes.items():
            bonus = vote_weight * (votes["sum"] - votes["max"]) / max(votes["count"], 1)
            cat_combined[cat] = votes["max"] + bonus

        ranked = sorted(cat_combined.items(), key=lambda x: -x[1])
        final_cats = [c for c, _ in ranked[:top_k]]

        top1 = gt_cat in final_cats[:1]
        top3 = gt_cat in final_cats[:3]
        top5 = gt_cat in final_cats[:5]
        results.append((rct, gt_cat, final_cats, top1, top3, top5))

    n = len(results)
    return results, sum(1 for r in results if r[3]), sum(1 for r in results if r[4]), sum(1 for r in results if r[5])


# ============================================================
# Strategy 3: Category Centroid (match against category average)
# ============================================================
def build_category_centroids(library_cases):
    """Build average FeatureVector per case_category."""
    cat_cases = defaultdict(list)
    for lc in library_cases:
        cat = lc.get("case_category", "")
        if cat:
            cat_cases[cat].append(lc)

    centroids = {}
    for cat, cases_list in cat_cases.items():
        # Average all numeric features
        n = len(cases_list)
        avg_features = {
            "failure_mode_dist": _avg_dist([c["features"].get("failure_mode_dist", {}) for c in cases_list]),
            "status_code_dist": _avg_dist([c["features"].get("status_code_dist", {}) for c in cases_list]),
            "operation_dist": _avg_dist([c["features"].get("operation_dist", {}) for c in cases_list]),
            "conn_operation_dist": _avg_dist([c["features"].get("conn_operation_dist", {}) for c in cases_list]),
            "seg_ranking": _avg_list([c["features"].get("seg_ranking", []) for c in cases_list]),
            "timeout_seg": _avg_set([c["features"].get("timeout_seg", []) for c in cases_list]),
            "pod_concentration": _avg_dict([c["features"].get("pod_concentration", {}) for c in cases_list]),
            "fault_category": cases_list[0].get("fault_category", "unknown"),
        }
        # Numeric averages
        for field in ["client_side_ratio", "server_side_ratio", "trace_context_pods",
                       "anomalous_ratio", "p99_p50_log"]:
            vals = [c["features"].get(field, 0) for c in cases_list]
            avg_features[field] = sum(vals) / n

        # op_p99_p50_log
        op_p99 = [c["features"].get("op_p99_p50_log", {}) for c in cases_list]
        avg_features["op_p99_p50_log"] = _avg_dist(op_p99)

        # seg_ranking_ordered (use most common ordering)
        orderings = [c["features"].get("seg_ranking_ordered", []) for c in cases_list]
        avg_features["seg_ranking_ordered"] = _avg_ordering(orderings)

        # scopes
        for scope_field in ["pod_scope", "host_scope", "cluster_scope"]:
            avg_features[scope_field] = _avg_dict([c["features"].get(scope_field, {}) for c in cases_list])

        centroids[cat] = FeatureVector(avg_features, avg_features["fault_category"])

    return centroids


def _avg_dist(dicts):
    result = defaultdict(float)
    n = len(dicts)
    for d in dicts:
        for k, v in d.items():
            result[k] += v / n
    return dict(result)


def _avg_list(lists):
    if not lists or not any(lists):
        return []
    max_len = max(len(l) for l in lists if l)
    result = []
    for i in range(max_len):
        vals = [l[i] for l in lists if l and i < len(l)]
        result.append(sum(vals) / len(vals) if vals else 0.0)
    return result


def _avg_set(lists):
    result = defaultdict(float)
    n = len(lists)
    for l in lists:
        for item in l:
            result[item] += 1.0 / n
    return dict(result)


def _avg_dict(dicts):
    result = defaultdict(float)
    n = len(dicts)
    for d in dicts:
        for k, v in d.items():
            result[k] += v / n
    return dict(result)


def _avg_ordering(orderings):
    """Use the most common first element, then most common second, etc."""
    result = []
    used = set()
    for i in range(5):
        counts = defaultdict(int)
        for ordering in orderings:
            if ordering and i < len(ordering) and ordering[i] not in used:
                counts[ordering[i]] += 1
        if counts:
            best = max(counts, key=counts.get)
            result.append(best)
            used.add(best)
        else:
            break
    return result


def evaluate_centroid(cases, library_cases, top_k=5, centroid_weight=0.5):
    centroids = build_category_centroids(library_cases)

    results = []
    for case in cases:
        features = case["features"]
        fc = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")
        case_id = case.get("id", "")
        log_file_id = case.get("log_file_id", "")

        qfv = FeatureVector(features, fc)

        # Individual case matching (standard)
        scored = []
        for lib_case in library_cases:
            if lib_case.get("id") == case_id or lib_case.get("log_file_id") == log_file_id:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))
            detail = compute_similarity_detailed(qfv, lib_fv)
            if detail["final_score"] >= 0.999:
                continue
            cat = lib_case.get("case_category", "")
            scored.append((detail["final_score"], cat, merge_fault_type(lib_case["root_cause_type"])))

        scored.sort(key=lambda x: -x[0])

        # Standard dedup
        seen_cats = {}
        for sim, cat, rct_name in scored:
            if cat and cat not in seen_cats:
                seen_cats[cat] = sim

        # Centroid matching
        centroid_scores = {}
        for cat, centroid_fv in centroids.items():
            detail = compute_similarity_detailed(qfv, centroid_fv)
            centroid_scores[cat] = detail["final_score"]

        # Combined: individual_score * (1 - centroid_weight) + centroid_score * centroid_weight
        all_cats = set(seen_cats.keys()) | set(centroid_scores.keys())
        combined = {}
        for cat in all_cats:
            ind_score = seen_cats.get(cat, 0.0)
            cent_score = centroid_scores.get(cat, 0.0)
            combined[cat] = ind_score * (1 - centroid_weight) + cent_score * centroid_weight

        ranked = sorted(combined.items(), key=lambda x: -x[1])
        final_cats = [c for c, _ in ranked[:top_k]]

        top1 = gt_cat in final_cats[:1]
        top3 = gt_cat in final_cats[:3]
        top5 = gt_cat in final_cats[:5]
        results.append((rct, gt_cat, final_cats, top1, top3, top5))

    n = len(results)
    return results, sum(1 for r in results if r[3]), sum(1 for r in results if r[4]), sum(1 for r in results if r[5])


# ============================================================
# Strategy 4: Two-stage (latency-only filter, then full re-rank)
# ============================================================
def evaluate_two_stage(cases, library_cases, top_k=5, filter_ratio=3.0):
    """First stage: rank by latency-only features (seg, op_p99, p99).
    Second stage: take top (filter_ratio * top_k) categories, re-rank with full features."""
    results = []
    for case in cases:
        features = case["features"]
        fc = features.get("fault_category", "unknown")
        rct = case.get("root_cause_type", "")
        gt_cat = GT_CATEGORY.get(rct, "未知")
        case_id = case.get("id", "")
        log_file_id = case.get("log_file_id", "")

        qfv = FeatureVector(features, fc)

        # Stage 1: latency-only scoring
        latency_scored = []
        for lib_case in library_cases:
            if lib_case.get("id") == case_id or lib_case.get("log_file_id") == log_file_id:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))

            # Latency-only dimensions
            seg_r_sim = _cosine_sim(qfv.seg_ranking_vec, lib_fv.seg_ranking_vec)
            if not qfv.seg_ranking_vec and not lib_fv.seg_ranking_vec:
                seg_r_sim = 0.0

            if qfv.seg_ranking_ordered and lib_fv.seg_ranking_ordered:
                n = min(len(qfv.seg_ranking_ordered), len(lib_fv.seg_ranking_ordered), 5)
                pos = sum(1 for i in range(n) if qfv.seg_ranking_ordered[i] == lib_fv.seg_ranking_ordered[i])
                order_sim = pos / n if n > 0 else 0.0
            else:
                order_sim = 0.0

            op_p99_sim = _cosine_sim(qfv.op_p99_p50_log, lib_fv.op_p99_p50_log)
            if not qfv.op_p99_p50_log and not lib_fv.op_p99_p50_log:
                op_p99_sim = 0.0

            if qfv.p99_p50_log > 0 and lib_fv.p99_p50_log > 0:
                p99_sim = math.exp(-abs(qfv.p99_p50_log - lib_fv.p99_p50_log) * 3)
            else:
                p99_sim = 0.0

            latency_score = (seg_r_sim * 3.0 + order_sim * 3.0 + op_p99_sim * 5.0 + p99_sim * 2.0) / 13.0
            cat = lib_case.get("case_category", "")
            latency_scored.append((latency_score, cat, lib_case))

        latency_scored.sort(key=lambda x: -x[0])

        # Get candidate categories from top-N latency matches
        candidate_cats = []
        for score, cat, _ in latency_scored:
            if cat and cat not in candidate_cats:
                candidate_cats.append(cat)
            if len(candidate_cats) >= int(filter_ratio * top_k):
                break

        # Stage 2: full-feature re-rank within candidate categories
        full_scored = []
        for score, cat, lib_case in latency_scored:
            if cat not in candidate_cats:
                continue
            lib_fv = FeatureVector(lib_case["features"], lib_case.get("fault_category", "unknown"))
            detail = compute_similarity_detailed(qfv, lib_fv)
            if detail["final_score"] >= 0.999:
                continue
            full_scored.append((detail["final_score"], cat, merge_fault_type(lib_case["root_cause_type"])))

        full_scored.sort(key=lambda x: -x[0])

        seen_cats = []
        for sim, cat, rct_name in full_scored:
            if cat and cat not in seen_cats:
                seen_cats.append(cat)
            if len(seen_cats) >= top_k:
                break

        top1 = gt_cat in seen_cats[:1]
        top3 = gt_cat in seen_cats[:3]
        top5 = gt_cat in seen_cats[:5]
        results.append((rct, gt_cat, seen_cats[:5], top1, top3, top5))

    n = len(results)
    return results, sum(1 for r in results if r[3]), sum(1 for r in results if r[4]), sum(1 for r in results if r[5])


# ============================================================
# Strategy 5: Hybrid (baseline + category count bonus)
# ============================================================
def evaluate_hybrid(cases, library_cases, top_k=5, count_bonus=0.05, count_n=10):
    """Standard dedup + bonus for categories with multiple high-similarity cases."""
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
            detail = compute_similarity_detailed(qfv, lib_fv)
            if detail["final_score"] >= 0.999:
                continue
            cat = lib_case.get("case_category", "")
            scored.append((detail["final_score"], cat, merge_fault_type(lib_case["root_cause_type"])))

        scored.sort(key=lambda x: -x[0])

        # Count top-N cases per category
        cat_counts = defaultdict(int)
        cat_max = {}
        for sim, cat, rct_name in scored[:count_n]:
            if cat:
                cat_counts[cat] += 1
                if cat not in cat_max or sim > cat_max[cat]:
                    cat_max[cat] = sim

        # Combined: max_score + count_bonus * (count - 1)
        combined = {}
        for cat in cat_max:
            combined[cat] = cat_max[cat] + count_bonus * (cat_counts[cat] - 1)

        # Also include categories that have cases but not in top-N
        seen_cats_dedup = {}
        for sim, cat, rct_name in scored:
            if cat and cat not in seen_cats_dedup:
                seen_cats_dedup[cat] = sim
        for cat, sim in seen_cats_dedup.items():
            if cat not in combined:
                combined[cat] = sim

        ranked = sorted(combined.items(), key=lambda x: -x[1])
        final_cats = [c for c, _ in ranked[:top_k]]

        top1 = gt_cat in final_cats[:1]
        top3 = gt_cat in final_cats[:3]
        top5 = gt_cat in final_cats[:5]
        results.append((rct, gt_cat, final_cats, top1, top3, top5))

    n = len(results)
    return results, sum(1 for r in results if r[3]), sum(1 for r in results if r[4]), sum(1 for r in results if r[5])


async def main():
    cases = load_new_cases()
    library_cases = load_case_library()
    print(f"测试案例: {len(cases)}, 案例库: {len(library_cases)}")
    print("=" * 100)

    # Strategy 1: Baseline
    print("\n[策略1] 基线（op_p99_weight=5.0）")
    results, h1, h3, h5 = evaluate_baseline(cases, library_cases)
    print(f"  Top1={h1} Top3={h3} Top5={h5}  ({h1*10}/{h3*10}/{h5*10}%)")
    for rct, gt_cat, top5, t1, t3, t5 in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct}  GT={gt_cat}  top5={top5}")

    # Strategy 2: Category Voting
    print("\n[策略2] 类别投票法")
    best_v = (0, 0, 0, None)
    for vote_n in [10, 15, 20, 30, 50]:
        for vote_weight in [0.1, 0.2, 0.3, 0.5, 0.8]:
            results, h1, h3, h5 = evaluate_category_voting(cases, library_cases, vote_n=vote_n, vote_weight=vote_weight)
            if h5 > best_v[2] or (h5 == best_v[2] and h3 > best_v[1]):
                best_v = (h1, h3, h5, (vote_n, vote_weight))
            if vote_n == 20 and vote_weight == 0.3:
                print(f"  vote_n={vote_n} weight={vote_weight}: Top1={h1} Top3={h3} Top5={h5}")
    print(f"  最优: vote_n={best_v[3][0]} weight={best_v[3][1]}: Top1={best_v[0]} Top3={best_v[1]} Top5={best_v[2]}")
    results, _, _, _ = evaluate_category_voting(cases, library_cases, vote_n=best_v[3][0], vote_weight=best_v[3][1])
    for rct, gt_cat, top5, t1, t3, t5 in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct}  GT={gt_cat}  top5={top5}")

    # Strategy 3: Centroid
    print("\n[策略3] 类别质心法")
    best_c = (0, 0, 0, None)
    for cw in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        results, h1, h3, h5 = evaluate_centroid(cases, library_cases, centroid_weight=cw)
        if h5 > best_c[2] or (h5 == best_c[2] and h3 > best_c[1]):
            best_c = (h1, h3, h5, cw)
        print(f"  centroid_weight={cw}: Top1={h1} Top3={h3} Top5={h5}")
    print(f"  最优: centroid_weight={best_c[3]}: Top1={best_c[0]} Top3={best_c[1]} Top5={best_c[2]}")
    results, _, _, _ = evaluate_centroid(cases, library_cases, centroid_weight=best_c[3])
    for rct, gt_cat, top5, t1, t3, t5 in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct}  GT={gt_cat}  top5={top5}")

    # Strategy 4: Two-stage
    print("\n[策略4] 两阶段法（latency-only → full re-rank）")
    best_ts = (0, 0, 0, None)
    for fr in [2.0, 3.0, 4.0, 5.0, 8.0]:
        results, h1, h3, h5 = evaluate_two_stage(cases, library_cases, filter_ratio=fr)
        if h5 > best_ts[2] or (h5 == best_ts[2] and h3 > best_ts[1]):
            best_ts = (h1, h3, h5, fr)
        print(f"  filter_ratio={fr}: Top1={h1} Top3={h3} Top5={h5}")
    print(f"  最优: filter_ratio={best_ts[3]}: Top1={best_ts[0]} Top3={best_ts[1]} Top5={best_ts[2]}")
    results, _, _, _ = evaluate_two_stage(cases, library_cases, filter_ratio=best_ts[3])
    for rct, gt_cat, top5, t1, t3, t5 in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct}  GT={gt_cat}  top5={top5}")

    # Strategy 5: Hybrid (count bonus)
    print("\n[策略5] 混合法（基线 + 类别计数加分）")
    best_h = (0, 0, 0, None)
    for cb in [0.02, 0.03, 0.05, 0.08, 0.1]:
        for cn in [5, 10, 15, 20]:
            results, h1, h3, h5 = evaluate_hybrid(cases, library_cases, count_bonus=cb, count_n=cn)
            if h5 > best_h[2] or (h5 == best_h[2] and h3 > best_h[1]):
                best_h = (h1, h3, h5, (cb, cn))
    print(f"  最优: count_bonus={best_h[3][0]} count_n={best_h[3][1]}: Top1={best_h[0]} Top3={best_h[1]} Top5={best_h[2]}")
    results, _, _, _ = evaluate_hybrid(cases, library_cases, count_bonus=best_h[3][0], count_n=best_h[3][1])
    for rct, gt_cat, top5, t1, t3, t5 in results:
        hit = "✓" if t5 else "✗"
        print(f"    {hit} {rct}  GT={gt_cat}  top5={top5}")

    # Summary
    print("\n" + "=" * 100)
    print("汇总:")
    print(f"  策略1 基线:          Top1={h1} Top3={h3} Top5={h5}")
    print(f"  策略2 类别投票:       Top1={best_v[0]} Top3={best_v[1]} Top5={best_v[2]}")
    print(f"  策略3 类别质心:       Top1={best_c[0]} Top3={best_c[1]} Top5={best_c[2]}")
    print(f"  策略4 两阶段:         Top1={best_ts[0]} Top3={best_ts[1]} Top5={best_ts[2]}")
    print(f"  策略5 混合法:         Top1={best_h[0]} Top3={best_h[1]} Top5={best_h[2]}")


if __name__ == "__main__":
    asyncio.run(main())
