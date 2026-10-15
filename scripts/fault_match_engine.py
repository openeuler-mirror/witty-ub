#!/usr/bin/env python3
"""故障模式匹配引擎

1. 加载训练集特征（yxh_new_simplified）
2. 提取测试集特征（yxh_new_0530_simplified）
3. 计算测试案例与每个训练案例的加权相似度
4. 匹配最相似的训练案例的故障类型
5. 与 ground truth 比较计算准确度

用法:
    cd /Users/zhaoyujin/Desktop/witty-ub
    PYTHONPATH=src/plugins PG_HOST=127.0.0.1 PG_PORT=5432 \
    PG_DATABASE=witty-ub PG_USER=witty-ub PG_PASSWORD=... \
    src/plugins/latency/.venv/bin/python3 scripts/fault_match_engine.py
"""

import os
import sys
import json
import asyncio
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import quote_plus

from latency.services.feature_extraction import FeatureExtractionManager
from latency.database.engine import PGManager
from latency.database.models import LogFile

import psycopg2
from sqlalchemy import select, func

# ============================================================
# 配置
# ============================================================

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "witty-ub")
PG_USER = os.getenv("PG_USER", "witty-ub")

PG_PASSWD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deploy", "pg.passwd",
)

TRAIN_KB_ID = "bea5fe98-9724-4d67-b5d1-4a9c0d7db5f7"
TEST_KB_ID = "d8ef4a15-74af-4505-8775-94cef3bb04b4"
TRAIN_CASE_DIR = "/Users/zhaoyujin/Desktop/witty-ub/case_data/case"


def read_pg_password() -> str:
    with open(PG_PASSWD_FILE, "r") as f:
        return f.read().strip()


def extract_root_cause_type(log_name: str) -> str:
    """从文件名提取根因类型: lingqu_kvcache_xxx_NNN_... -> xxx"""
    m = re.match(r"^lingqu_kvcache_(.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$", log_name)
    return m.group(1) if m else log_name


# ============================================================
# 特征归一化与向量化
# ============================================================

def _normalize_counter(counter: dict, total: float | None = None) -> dict:
    """将计数器归一化为比例分布"""
    if not counter:
        return {}
    t = total or sum(counter.values())
    if t == 0:
        return {}
    return {k: v / t for k, v in counter.items()}


def _cosine_sim(a: dict, b: dict) -> float:
    """两个稀疏向量的余弦相似度"""
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaccard_sim(a: set, b: set) -> float:
    """Jaccard 相似度，两个空集返回0（不奖励无特征匹配）"""
    if not a and not b:
        return 0.0  # both empty — no discriminative power
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _scope_sim(a: str, b: str) -> float:
    """空间范围相似度 (exact match = 1, else 0)"""
    return 1.0 if a == b else 0.0


def _log_normalize(value: float, ref: float = 1.0) -> float:
    """对数归一化：log(1 + value/ref)，避免绝对值影响"""
    if value <= 0:
        return 0.0
    return math.log1p(value / ref)


class FeatureVector:
    """将案例特征转化为可比较的向量"""

    def __init__(self, features: dict, fault_category: str):
        self.fault_category = fault_category
        self.latency = features.get("latency")
        self.connectivity = features.get("connectivity")

        # ── 预计算归一化特征 ──
        # 1. fault_category one-hot
        self.cat_latency = 1.0 if fault_category in ("latency", "mixed") else 0.0
        self.cat_connectivity = 1.0 if fault_category in ("connectivity", "mixed") else 0.0

        # 2. Latency features
        self.pod_concentration = self.latency.get("pod_concentration", "") if self.latency else ""
        self.p99_p50 = self.latency.get("p99_p50_ratio") if self.latency else None
        # log-normalize p99_p50
        self.p99_p50_log = _log_normalize(self.p99_p50) if self.p99_p50 else 0.0

        # normalized operation dist
        self.operation_dist = _normalize_counter(
            self.latency.get("affected_operation_dist", {}) if self.latency else {}
        )
        self.operation_set = set(self.operation_dist.keys())

        # timeout segment names (ordered for sequence comparison)
        self.timeout_seg_ordered: list[str] = []
        if self.latency:
            for seg in self.latency.get("timeout_segments", []):
                self.timeout_seg_ordered.append(seg[0])
        self.timeout_seg_set = set(self.timeout_seg_ordered)

        # segment ranking normalized (as proportion vector)
        self.seg_ranking_vec = {}
        self.seg_ranking_ordered: list[str] = []  # ordered by value desc
        # client-side vs server-side dominance
        self.client_side_ratio = 0.0  # (c2w + c2w_urma + sdk_rpc) / total
        self.server_side_ratio = 0.0  # (worker_total + urma_total + remote_worker) / total
        if self.latency:
            segs = self.latency.get("segment_ranking", [])
            total = sum(s[1] for s in segs if s[1] > 0)
            if total > 0:
                self.seg_ranking_vec = {s[0]: s[1] / total for s in segs if s[1] > 0}
                sorted_segs = sorted(self.seg_ranking_vec.items(), key=lambda x: -x[1])
                self.seg_ranking_ordered = [s[0] for s in sorted_segs]
                # client-side latency share
                client_fields = {"c2w_latency", "c2w_urma_latency", "sdk_rpc",
                                 "sdk_process", "local_worker_cost", "local_worker_lock"}
                server_fields = {"worker_total_latency", "urma_total_latency", "urma_link_latency",
                                 "remote_worker_cost", "remote_worker_rpc", "master_process",
                                 "master_rpc_total", "w2w_urma_latency"}
                client_sum = sum(v for k, v in self.seg_ranking_vec.items() if k in client_fields)
                server_sum = sum(v for k, v in self.seg_ranking_vec.items() if k in server_fields)
                self.client_side_ratio = client_sum
                self.server_side_ratio = server_sum

        # 3. Connectivity features
        self.failure_mode_dist = _normalize_counter(
            self.connectivity.get("failure_mode_dist", {}) if self.connectivity else {}
        )
        self.failure_mode_set = set(self.failure_mode_dist.keys())

        self.status_code_dist = _normalize_counter(
            self.connectivity.get("status_code_dist", {}) if self.connectivity else {}
        )
        self.status_code_set = set(self.status_code_dist.keys())

        self.pod_scope = (self.connectivity.get("spatial_pod", {}).get("scope", "")
                          if self.connectivity else "")
        self.host_scope = (self.connectivity.get("spatial_host", {}).get("scope", "")
                           if self.connectivity else "")
        self.cluster_scope = (self.connectivity.get("spatial_cluster", {}).get("scope", "")
                              if self.connectivity else "")

        self.conn_operation_dist = _normalize_counter(
            self.connectivity.get("affected_operation_dist", {}) if self.connectivity else {}
        )
        self.conn_operation_set = set(self.conn_operation_dist.keys())

        # trace context spatial info (latency side)
        self.trace_context_pods = self.latency.get("trace_context_pods_count", 0) if self.latency else 0
        self.trace_context_hosts = self.latency.get("trace_context_hosts_count", 0) if self.latency else 0

        # anomalous_ratio — how much of the log is anomalous
        self.anomalous_ratio = self.latency.get("anomalous_ratio", 0.0) if self.latency else 0.0

        # per-operation P99/P50 ratio dict (log-normalized)
        op_p99 = self.latency.get("op_p99_p50_ratio", {}) if self.latency else {}
        self.op_p99_p50_log = {k: _log_normalize(v) for k, v in op_p99.items() if v and v > 0}


def compute_similarity(a: FeatureVector, b: FeatureVector) -> float:
    """计算两个案例的加权相似度，返回 [0, 1]

    设计原则:
    - fault_category 不匹配 → 乘法门控（×0.25 大幅降权）
    - 一方有 failure_mode/status_code 另一方没有 → 不对称惩罚
    - 空特征不贡献正向分数
    - 数值特征 log 归一化 + 指数衰减
    """

    # ── 加权特征分数 ──
    scores = {}

    # 1. failure_mode_dist 余弦相似度 (weight=6.0)
    a_has_fm = bool(a.failure_mode_dist)
    b_has_fm = bool(b.failure_mode_dist)
    if a_has_fm and b_has_fm:
        fm_sim = _cosine_sim(a.failure_mode_dist, b.failure_mode_dist)
        fm_weight = 6.0
    elif not a_has_fm and not b_has_fm:
        fm_sim = 0.0  # both empty = no discriminative power
        fm_weight = 0.0  # don't count in total_weight
    else:
        fm_sim = 0.0  # asymmetric: one has, other doesn't
        fm_weight = 6.0  # still count to penalize via asym_gate
    scores["failure_mode"] = (fm_sim, fm_weight)
    fm_asym_penalty = 0.3 if (a_has_fm != b_has_fm) else 1.0

    # 2. status_code_dist 余弦相似度 (weight=4.0)
    a_has_sc = bool(a.status_code_dist)
    b_has_sc = bool(b.status_code_dist)
    if a_has_sc and b_has_sc:
        sc_sim = _cosine_sim(a.status_code_dist, b.status_code_dist)
        sc_weight = 4.0
    elif not a_has_sc and not b_has_sc:
        sc_sim = 0.0
        sc_weight = 0.0
    else:
        sc_sim = 0.0
        sc_weight = 4.0
    scores["status_code"] = (sc_sim, sc_weight)
    sc_asym_penalty = 0.4 if (a_has_sc != b_has_sc) else 1.0

    # 3. operation_dist 余弦相似度 (weight=3.0)
    op_sim = _cosine_sim(a.operation_dist, b.operation_dist)
    if not a.operation_dist and not b.operation_dist:
        op_sim = 0.0
    scores["operation"] = (op_sim, 3.0)

    # 4. conn_operation_dist 余弦相似度 (weight=2.0)
    cop_sim = _cosine_sim(a.conn_operation_dist, b.conn_operation_dist)
    if not a.conn_operation_dist and not b.conn_operation_dist:
        cop_sim = 0.0
    scores["conn_operation"] = (cop_sim, 2.0)

    # 5. segment ranking 余弦相似度 (weight=3.0)
    seg_r_sim = _cosine_sim(a.seg_ranking_vec, b.seg_ranking_vec)
    if not a.seg_ranking_vec and not b.seg_ranking_vec:
        seg_r_sim = 0.0
    scores["seg_ranking"] = (seg_r_sim, 3.0)

    # 5b. segment ranking ORDER similarity (weight=3.0) — 排序比比例更稳定
    if a.seg_ranking_ordered and b.seg_ranking_ordered:
        n = min(len(a.seg_ranking_ordered), len(b.seg_ranking_ordered), 5)
        pos_matches = sum(
            1 for i in range(n)
            if i < len(a.seg_ranking_ordered) and i < len(b.seg_ranking_ordered)
            and a.seg_ranking_ordered[i] == b.seg_ranking_ordered[i]
        )
        order_sim = pos_matches / n if n > 0 else 0.0
    else:
        order_sim = 0.0
    scores["seg_order"] = (order_sim, 3.0)

    # 6. timeout segment Jaccard (weight=2.0)
    seg_sim = _jaccard_sim(a.timeout_seg_set, b.timeout_seg_set)
    scores["timeout_seg"] = (seg_sim, 2.0)

    # 7. pod_concentration 匹配 (weight=1.5)
    pc_sim = _scope_sim(a.pod_concentration, b.pod_concentration)
    scores["pod_conc"] = (pc_sim, 1.5)

    # 7b. client_side_ratio similarity (weight=2.5)
    if a.client_side_ratio > 0 or b.client_side_ratio > 0:
        cr_diff = abs(a.client_side_ratio - b.client_side_ratio)
        cr_sim = math.exp(-cr_diff * 6)
    else:
        cr_sim = 0.0
    scores["client_ratio"] = (cr_sim, 2.5)

    # 7c. server_side_ratio similarity (weight=2.5)
    if a.server_side_ratio > 0 or b.server_side_ratio > 0:
        sr_diff = abs(a.server_side_ratio - b.server_side_ratio)
        sr_sim = math.exp(-sr_diff * 6)
    else:
        sr_sim = 0.0
    scores["server_ratio"] = (sr_sim, 2.5)

    # 7d. affected_pods_count similarity (weight=2.5) — log-normalized
    ap_a = _log_normalize(a.trace_context_pods) if a.trace_context_pods > 0 else 0
    ap_b = _log_normalize(b.trace_context_pods) if b.trace_context_pods > 0 else 0
    if ap_a > 0 or ap_b > 0:
        ap_diff = abs(ap_a - ap_b)
        ap_sim = math.exp(-ap_diff * 3)
    else:
        ap_sim = 0.0
    scores["trace_pods"] = (ap_sim, 2.5)

    # 7e. anomalous_ratio similarity (weight=1.5)
    if a.anomalous_ratio > 0 or b.anomalous_ratio > 0:
        ar_diff = abs(a.anomalous_ratio - b.anomalous_ratio)
        ar_sim = math.exp(-ar_diff * 3)
    else:
        ar_sim = 0.0
    scores["anomalous_ratio"] = (ar_sim, 1.5)

    # 8. spatial scopes (weight=1.0 each)
    scores["pod_scope"] = (_scope_sim(a.pod_scope, b.pod_scope), 1.0)
    scores["host_scope"] = (_scope_sim(a.host_scope, b.host_scope), 1.0)
    scores["cluster_scope"] = (_scope_sim(a.cluster_scope, b.cluster_scope), 1.0)

    # 9. p99_p50 log-normalized similarity (weight=2.0)
    if a.p99_p50_log > 0 and b.p99_p50_log > 0:
        diff = abs(a.p99_p50_log - b.p99_p50_log)
        p99_sim = math.exp(-diff * 3)
    elif a.p99_p50_log == 0 and b.p99_p50_log == 0:
        p99_sim = 0.0
    else:
        p99_sim = 0.0
    scores["p99_p50"] = (p99_sim, 2.0)

    # 10. per-operation P99/P50 ratio cosine similarity (weight=4.0) — very discriminative
    op_p99_sim = _cosine_sim(a.op_p99_p50_log, b.op_p99_p50_log)
    if not a.op_p99_p50_log and not b.op_p99_p50_log:
        op_p99_sim = 0.0
    scores["op_p99_p50"] = (op_p99_sim, 4.0)

    # ── 加权平均 ──
    total_weight = sum(w for _, w in scores.values())
    weighted_sum = sum(s * w for s, w in scores.values())
    base_sim = weighted_sum / total_weight if total_weight > 0 else 0.0

    # ── 门控惩罚 ──
    # fault_category 不匹配 → 大幅降权
    cat_gate = 1.0 if a.fault_category == b.fault_category else 0.25

    # 不对称惩罚：一方有故障模式另一方没有
    asym_gate = fm_asym_penalty * sc_asym_penalty

    return base_sim * cat_gate * asym_gate


# ============================================================
# 主流程
# ============================================================

async def main():
    pg_password = read_pg_password()
    dsn_sync = f"host={PG_HOST} port={PG_PORT} dbname={PG_DATABASE} user={PG_USER} password={pg_password}"
    dsn_async = (
        f"postgresql+asyncpg://{PG_USER}:{quote_plus(pg_password)}"
        f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    )

    # ── Step 1: 加载训练集特征 ──
    print("=" * 70)
    print("Step 1: 加载训练集特征")
    print("=" * 70)

    train_cases = []
    for f in sorted(os.listdir(TRAIN_CASE_DIR)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(TRAIN_CASE_DIR, f), "r", encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("features"):
            fv = FeatureVector(d["features"], d.get("fault_category", "unknown"))
            train_cases.append({
                "root_cause_type": d["root_cause_type"],
                "features": d["features"],
                "fault_category": d.get("fault_category", "unknown"),
                "fv": fv,
            })

    print(f"训练案例数: {len(train_cases)}")
    train_types = set(c["root_cause_type"] for c in train_cases)
    print(f"训练故障类型: {len(train_types)}")

    # ── Step 2: 提取测试集特征 ──
    print("\n" + "=" * 70)
    print("Step 2: 提取测试集特征")
    print("=" * 70)

    PGManager.initialize(dsn_async)

    conn = psycopg2.connect(dsn_sync)
    conn.autocommit = True
    cur = conn.cursor()

    # 查找测试集成功任务
    cur.execute(
        """
        SELECT DISTINCT lf.id, lf.name
        FROM log_file lf
        JOIN task t ON t.op_id = lf.id AND t.task_type = 'kv_cache_log_parse_worker'
        WHERE lf.kb_id = %s AND t.status = 'successful'
        ORDER BY lf.name
        """,
        (TEST_KB_ID,),
    )
    test_log_files = cur.fetchall()
    conn.close()

    print(f"测试集成功任务数: {len(test_log_files)}")

    test_cases = []
    for idx, (log_id, log_name) in enumerate(test_log_files, 1):
        rct = extract_root_cause_type(log_name)
        print(f"  [{idx}/{len(test_log_files)}] {log_name} -> {rct}")

        try:
            features = await FeatureExtractionManager.extract_features(log_id)
            fault_category = features.get("fault_category", "unknown") if features else "unknown"
            fv = FeatureVector(features, fault_category) if features else None
            test_cases.append({
                "log_id": log_id,
                "log_name": log_name,
                "root_cause_type": rct,
                "features": features,
                "fault_category": fault_category,
                "fv": fv,
            })
        except Exception as e:
            print(f"    [ERROR] {e}")
            test_cases.append({
                "log_id": log_id,
                "log_name": log_name,
                "root_cause_type": rct,
                "features": None,
                "fault_category": "unknown",
                "fv": None,
            })

    await PGManager.close()

    # ── Step 3: 匹配并验证 ──
    print("\n" + "=" * 70)
    print("Step 3: 故障模式匹配")
    print("=" * 70)

    # 确定有效测试案例（ground truth 在训练类型中）
    valid_test = []
    invalid_test = []
    for tc in test_cases:
        if tc["fv"] is None:
            invalid_test.append((tc, "no_features"))
            continue
        # ground truth: 是否匹配任一训练故障类型
        gt = tc["root_cause_type"]
        if gt in train_types:
            valid_test.append(tc)
        else:
            invalid_test.append((tc, f"type_not_in_train('{gt}')"))

    print(f"有效测试案例: {len(valid_test)}")
    print(f"无效测试案例: {len(invalid_test)}")
    for tc, reason in invalid_test[:10]:
        print(f"  {tc['root_cause_type']}: {reason}")

    # 匹配
    results = []
    for tc in valid_test:
        query_fv = tc["fv"]
        gt = tc["root_cause_type"]

        # 计算与每个训练案例的相似度
        sims = []
        for tr in train_cases:
            sim = compute_similarity(query_fv, tr["fv"])
            sims.append((tr["root_cause_type"], sim))

        # 按相似度排序
        sims.sort(key=lambda x: x[1], reverse=True)
        best_type, best_sim = sims[0]
        second_type, second_sim = sims[1] if len(sims) > 1 else (None, 0)

        is_correct = (best_type == gt)
        results.append({
            "log_name": tc["log_name"],
            "ground_truth": gt,
            "predicted": best_type,
            "confidence": round(best_sim, 4),
            "correct": is_correct,
            "top3_correct": gt in [s[0] for s in sims[:3]],
            "top5_correct": gt in [s[0] for s in sims[:5]],
            "second_type": second_type,
            "second_sim": round(second_sim, 4),
            "top5_candidates": [(s[0], round(s[1], 4)) for s in sims[:5]],
            "test_features": tc["features"],
            "test_fault_category": tc["fault_category"],
        })

    # ── Step 4: 统计准确度 ──
    print("\n" + "=" * 70)
    print("Step 4: 准确度统计")
    print("=" * 70)

    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    top3_correct = sum(1 for r in results if r["top3_correct"])
    top5_correct = sum(1 for r in results if r["top5_correct"])

    print(f"有效测试案例: {total}")
    print(f"Top-1 准确率: {correct}/{total} = {correct/total*100:.1f}%")
    print(f"Top-3 准确率: {top3_correct}/{total} = {top3_correct/total*100:.1f}%")
    print(f"Top-5 准确率: {top5_correct}/{total} = {top5_correct/total*100:.1f}%")

    # 按 fault_category 分组统计
    by_cat = defaultdict(list)
    for r in results:
        # 找测试案例的 fault_category
        tc = next(t for t in valid_test if t["log_name"] == r["log_name"])
        by_cat[tc["fault_category"]].append(r)

    print("\n按故障类别分组:")
    for cat in sorted(by_cat.keys()):
        group = by_cat[cat]
        c = sum(1 for r in group if r["correct"])
        print(f"  {cat}: Top-1={c}/{len(group)}={c/len(group)*100:.1f}%")

    # 错误案例分析
    errors = [r for r in results if not r["correct"]]
    if errors:
        print(f"\n错误案例 ({len(errors)}):")
        for r in errors[:20]:
            print(f"  {r['ground_truth']} -> predicted={r['predicted']} "
                  f"(conf={r['confidence']}, 2nd={r['second_type']}@{r['second_sim']})")

    # 保存详细结果
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "match_results.json",
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_valid": total,
            "top1_accuracy": correct / total if total > 0 else 0,
            "top3_accuracy": top3_correct / total if total > 0 else 0,
            "top5_accuracy": top5_correct / total if total > 0 else 0,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
