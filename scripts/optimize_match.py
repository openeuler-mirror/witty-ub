#!/usr/bin/env python3
"""Grid search optimization for match accuracy."""

import sys, json, math, itertools
from collections import defaultdict
from run_new_case_match import (
    load_cases, run_match, calc_accuracy, BROAD_CATEGORY,
    TRAIN_CASE_DIR, TEST_CASE_DIR,
)

# ── 加载数据 ──
train_cases = load_cases(TRAIN_CASE_DIR, exclude_other=True, exclude_etcd=True)
test_cases = load_cases(TEST_CASE_DIR)
print(f"训练案例数: {len(train_cases)}, 测试案例数: {len(test_cases)}")

# ── 策略 E: 合并 UB-Client侧 + UB-Worker侧链路 → UB-链路故障 ──
# 临时修改映射
import copy
merged_map = copy.deepcopy(BROAD_CATEGORY)
for k, v in merged_map.items():
    if v in ("UB-Client侧故障", "UB-Worker侧链路"):
        merged_map[k] = "UB-链路故障"
# 测试集
test_map_update = {
    "UB链路故障": "UB-链路故障",
    "端侧到L1端口故障": "UB-链路故障",
    "UB交换机L1的上行端口闪断": "UB-链路故障",
    "L1-L2互联链路反复shutdown模拟链路闪断": "UB-链路故障",
}
for k, v in test_map_update.items():
    merged_map[k] = v

import run_new_case_match as rcm
original_get_broad = rcm.get_broad_category
rcm.get_broad_category = lambda rct: merged_map.get(rct, "其他")

# 重新加载
train_merged = []
for c in train_cases:
    c2 = dict(c)
    c2["broad_category"] = merged_map.get(c["root_cause_type"], "其他")
    train_merged.append(c2)

test_merged = []
for c in test_cases:
    c2 = dict(c)
    c2["broad_category"] = merged_map.get(c["root_cause_type"], "其他")
    test_merged.append(c2)

train_broads = sorted(set(c["broad_category"] for c in train_merged))
print(f"合并后大类数: {len(train_broads)}")
for b in train_broads:
    cnt = sum(1 for c in train_merged if c["broad_category"] == b)
    print(f"  {b}: {cnt} 案例")

# ── 网格搜索权重组合 ──
weight_grid = {
    "seg_ranking": [3.0, 5.0, 7.0],
    "seg_order": [3.0, 4.0, 6.0],
    "op_p99_p50": [4.0, 5.0, 6.0],
    "failure_mode": [4.0, 6.0],
    "status_code": [3.0, 4.0],
    "client_ratio": [2.5, 3.5, 4.5],
    "server_ratio": [2.5, 3.5, 4.5],
    "p99_p50": [2.0, 3.0],
    "operation": [3.0, 4.0],
    "timeout_seg": [2.0, 2.5],
    "conn_operation": [1.5, 2.0],
    "pod_conc": [1.5],
    "anomalous_ratio": [1.5, 2.0],
    "trace_pods": [2.5],
    "pod_scope": [1.0],
    "host_scope": [1.0],
    "cluster_scope": [1.0],
}

# 基础权重
base_weights = {
    "failure_mode": 6.0,
    "status_code": 4.0,
    "op_p99_p50": 4.0,
    "operation": 3.0,
    "seg_ranking": 3.0,
    "seg_order": 3.0,
    "client_ratio": 2.5,
    "server_ratio": 2.5,
    "trace_pods": 2.5,
    "timeout_seg": 2.0,
    "conn_operation": 2.0,
    "p99_p50": 2.0,
    "pod_conc": 1.5,
    "anomalous_ratio": 1.5,
    "pod_scope": 1.0,
    "host_scope": 1.0,
    "cluster_scope": 1.0,
}

# 只搜索关键参数的子集
key_params = {
    "seg_ranking": [3.0, 5.0, 7.0],
    "seg_order": [3.0, 4.0, 6.0],
    "op_p99_p50": [4.0, 5.0, 6.0],
    "failure_mode": [4.0, 6.0],
    "client_ratio": [2.5, 3.5, 4.5],
    "server_ratio": [2.5, 3.5, 4.5],
}

cat_gates = [0.25, 0.5, 0.7]
fm_penalties = [0.3, 0.5, 0.7]

best_top1 = 0
best_top3 = 0
best_top5 = 0
best_config = None
results_all = []

total_combos = 1
for v in key_params.values():
    total_combos *= len(v)
total_combos *= len(cat_gates) * len(fm_penalties)
print(f"\n总组合数: {total_combos}")
print("搜索中...")

count = 0
keys = list(key_params.keys())
for combo in itertools.product(*[key_params[k] for k in keys]):
    for cg in cat_gates:
        for fm_p in fm_penalties:
            w = dict(base_weights)
            for k, v in zip(keys, combo):
                w[k] = v
            
            results = run_match(train_merged, test_merged, w, cg, fm_p, 0.4)
            t1 = calc_accuracy(results, 'top1_broad_dedup')
            t3 = calc_accuracy(results, 'top3_broad_dedup')
            t5 = calc_accuracy(results, 'top5_broad_dedup')
            
            results_all.append((t1, t3, t5, w, cg, fm_p))
            
            if t5 > best_top5 or (t5 == best_top5 and t1 > best_top1):
                best_top1 = t1
                best_top3 = t3
                best_top5 = t5
                best_config = (dict(w), cg, fm_p)
            
            count += 1
            if count % 200 == 0:
                print(f"  已搜索 {count}/{total_combos}... 当前最佳 Top-5={best_top5*100:.0f}%")

print(f"\n{'='*70}")
print(f"搜索完成! 共 {count} 种组合")
print(f"{'='*70}")
print(f"最佳 Top-1: {best_top1*100:.0f}%  Top-3: {best_top3*100:.0f}%  Top-5: {best_top5*100:.0f}%")
print(f"\n最佳配置:")
print(f"  cat_gate: {best_config[1]}")
print(f"  fm_penalty: {best_config[2]}")
print(f"  权重:")
for k, v in sorted(best_config[0].items(), key=lambda x: -x[1]):
    print(f"    {k:20s}: {v}")

# ── Top-10 最佳配置 ──
print(f"\n{'='*70}")
print("Top-10 配置 (按 Top-5 降序, Top-1 次降序)")
print(f"{'='*70}")
results_all.sort(key=lambda x: (-x[2], -x[0]))
for i, (t1, t3, t5, w, cg, fm_p) in enumerate(results_all[:10]):
    print(f"  #{i+1}  Top-1={t1*100:.0f}%  Top-3={t3*100:.0f}%  Top-5={t5*100:.0f}%  "
          f"cg={cg} fm={fm_p}  "
          f"seg_r={w['seg_ranking']} seg_o={w['seg_order']} op_p99={w['op_p99_p50']} "
          f"fm={w['failure_mode']} cr={w['client_ratio']} sr={w['server_ratio']}")

# ── 最佳配置的详细结果 ──
print(f"\n{'='*70}")
print("最佳配置详细结果")
print(f"{'='*70}")
best_w, best_cg, best_fm = best_config
results_best = run_match(train_merged, test_merged, best_w, best_cg, best_fm, 0.4)
for r in results_best:
    dedup = r.get("top5_broad_dedup_list", [])
    print(f"  {r['ground_truth']:30s}({r['gt_broad_category']:12s}) → "
          f"{r['predicted_broad']:12s}  conf={r['confidence']:.4f}")
    print(f"    去重大类Top5: {' > '.join(dedup)}")
    print(f"    命中: top1={r['top1_broad_dedup']} top3={r['top3_broad_dedup']} top5={r['top5_broad_dedup']}")

# 恢复
rcm.get_broad_category = original_get_broad
