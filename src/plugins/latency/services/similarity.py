"""相似案例分析服务：FeatureVector + compute_similarity + 原因生成。

从 scripts/run_dataset_match.py 提取并增强，增加按维度分数明细和原因说明生成。
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from typing import Any

from latency.services.case_service import CaseServiceManager, CASE_DIR


# ============================================================
# 故障类型合并映射（与 run_dataset_match.py 保持一致）
# ============================================================
FAULT_TYPE_MERGE_MAP = {
    "dfx_client_process_get_ubm_failure": "dfx_client_process_get_ub_failure",
    "dfx_client_process_get_ubse_failure": "dfx_client_process_get_ub_failure",
    "dfx_local_ub_all_port_down": "dfx_local_ub_all_port_unavailable",
    "dfx_local_ub_all_port_lanedown": "dfx_local_ub_all_port_unavailable",
    "dfx_local_ub_all_port_link_loss": "dfx_local_ub_all_port_unavailable",
    "dfx_worker_process_remote_ub_ce": "dfx_worker_process_remote_ub_signal_error",
    "dfx_worker_process_remote_ub_fe": "dfx_worker_process_remote_ub_signal_error",
    "dfx_worker_process_remote_ub_nfe": "dfx_worker_process_remote_ub_signal_error",
}


def merge_fault_type(ft: str) -> str:
    """将原始故障类型映射为合并后的类型。"""
    return FAULT_TYPE_MERGE_MAP.get(ft, ft)


# ============================================================
# 相似度辅助函数
# ============================================================

def _normalize_counter(counter: dict, total: float | None = None) -> dict:
    if not counter:
        return {}
    t = total or sum(counter.values())
    if t == 0:
        return {}
    return {k: v / t for k, v in counter.items()}


def _cosine_sim(a: dict, b: dict) -> float:
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
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _scope_sim(a: str, b: str) -> float:
    return 1.0 if a == b else 0.0


def _log_normalize(value: float, ref: float = 1.0) -> float:
    if value <= 0:
        return 0.0
    return math.log1p(value / ref)


# ============================================================
# FeatureVector
# ============================================================

class FeatureVector:
    """将案例特征转化为可比较的向量。"""

    def __init__(self, features: dict, fault_category: str):
        self.fault_category = fault_category
        self.latency = features.get("latency")
        self.connectivity = features.get("connectivity")

        self.cat_latency = 1.0 if fault_category in ("latency", "mixed") else 0.0
        self.cat_connectivity = 1.0 if fault_category in ("connectivity", "mixed") else 0.0

        self.pod_concentration = self.latency.get("pod_concentration", "") if self.latency else ""
        self.p99_p50 = self.latency.get("p99_p50_ratio") if self.latency else None
        self.p99_p50_log = _log_normalize(self.p99_p50) if self.p99_p50 else 0.0

        self.operation_dist = _normalize_counter(
            self.latency.get("affected_operation_dist", {}) if self.latency else {}
        )
        self.operation_set = set(self.operation_dist.keys())

        self.timeout_seg_ordered: list[str] = []
        if self.latency:
            for seg in self.latency.get("timeout_segments", []):
                self.timeout_seg_ordered.append(seg[0])
        self.timeout_seg_set = set(self.timeout_seg_ordered)

        self.seg_ranking_vec = {}
        self.seg_ranking_ordered: list[str] = []
        self.client_side_ratio = 0.0
        self.server_side_ratio = 0.0
        if self.latency:
            segs = self.latency.get("segment_ranking", [])
            total = sum(s[1] for s in segs if s[1] > 0)
            if total > 0:
                self.seg_ranking_vec = {s[0]: s[1] / total for s in segs if s[1] > 0}
                sorted_segs = sorted(self.seg_ranking_vec.items(), key=lambda x: -x[1])
                self.seg_ranking_ordered = [s[0] for s in sorted_segs]
                client_fields = {"c2w_latency", "c2w_urma_latency", "sdk_rpc",
                                 "sdk_process", "local_worker_cost", "local_worker_lock"}
                server_fields = {"worker_total_latency", "urma_total_latency", "urma_link_latency",
                                 "remote_worker_cost", "remote_worker_rpc", "master_process",
                                 "master_rpc_total", "w2w_urma_latency"}
                client_sum = sum(v for k, v in self.seg_ranking_vec.items() if k in client_fields)
                server_sum = sum(v for k, v in self.seg_ranking_vec.items() if k in server_fields)
                self.client_side_ratio = client_sum
                self.server_side_ratio = server_sum

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

        self.trace_context_pods = self.latency.get("trace_context_pods_count", 0) if self.latency else 0
        self.trace_context_hosts = self.latency.get("trace_context_hosts_count", 0) if self.latency else 0

        self.anomalous_ratio = self.latency.get("anomalous_ratio", 0.0) if self.latency else 0.0

        op_p99 = self.latency.get("op_p99_p50_ratio", {}) if self.latency else {}
        self.op_p99_p50_log = {k: _log_normalize(v) for k, v in op_p99.items() if v and v > 0}


# ============================================================
# 相似度计算（返回带维度明细的结果）
# ============================================================

# 维度名称映射（用于生成可读原因）
DIMENSION_LABELS = {
    "failure_mode": "故障模式分布",
    "status_code": "状态码分布",
    "operation": "时延操作分布",
    "conn_operation": "连接层操作分布",
    "seg_ranking": "段排名比例",
    "seg_order": "段排名顺序",
    "timeout_seg": "超时段集合",
    "pod_conc": "Pod 集中度",
    "client_ratio": "客户端时延占比",
    "server_ratio": "服务端时延占比",
    "trace_pods": "Trace Pod 空间",
    "anomalous_ratio": "异常比例",
    "pod_scope": "Pod 空间范围",
    "host_scope": "主机空间范围",
    "cluster_scope": "集群空间范围",
    "p99_p50": "P99/P50 比",
    "op_p99_p50": "操作分组 P99/P50 比",
}


def compute_similarity_detailed(a: FeatureVector, b: FeatureVector) -> dict:
    """计算两个特征向量的相似度，返回包含各维度明细的 dict。

    返回结构:
    {
        "final_score": float,
        "base_score": float,
        "cat_gate": float,
        "asym_gate": float,
        "dimensions": [
            {"name": str, "label": str, "score": float, "weight": float, "weighted_score": float},
            ...
        ],
        "reason": str,  # 可读的原因说明
    }
    """
    dimensions = []

    # --- failure_mode ---
    a_has_fm = bool(a.failure_mode_dist)
    b_has_fm = bool(b.failure_mode_dist)
    if a_has_fm and b_has_fm:
        fm_sim = _cosine_sim(a.failure_mode_dist, b.failure_mode_dist)
        fm_weight = 6.0
    elif not a_has_fm and not b_has_fm:
        fm_sim = 0.0
        fm_weight = 0.0
    else:
        fm_sim = 0.0
        fm_weight = 6.0
    fm_asym_penalty = 0.3 if (a_has_fm != b_has_fm) else 1.0
    dimensions.append({"name": "failure_mode", "score": fm_sim, "weight": fm_weight})

    # --- status_code ---
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
    sc_asym_penalty = 0.4 if (a_has_sc != b_has_sc) else 1.0
    dimensions.append({"name": "status_code", "score": sc_sim, "weight": sc_weight})

    # --- operation ---
    op_sim = _cosine_sim(a.operation_dist, b.operation_dist)
    if not a.operation_dist and not b.operation_dist:
        op_sim = 0.0
    dimensions.append({"name": "operation", "score": op_sim, "weight": 3.0})

    # --- conn_operation ---
    cop_sim = _cosine_sim(a.conn_operation_dist, b.conn_operation_dist)
    if not a.conn_operation_dist and not b.conn_operation_dist:
        cop_sim = 0.0
    dimensions.append({"name": "conn_operation", "score": cop_sim, "weight": 2.0})

    # --- seg_ranking ---
    seg_r_sim = _cosine_sim(a.seg_ranking_vec, b.seg_ranking_vec)
    if not a.seg_ranking_vec and not b.seg_ranking_vec:
        seg_r_sim = 0.0
    dimensions.append({"name": "seg_ranking", "score": seg_r_sim, "weight": 3.0})

    # --- seg_order ---
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
    dimensions.append({"name": "seg_order", "score": order_sim, "weight": 3.0})

    # --- timeout_seg ---
    seg_sim = _jaccard_sim(a.timeout_seg_set, b.timeout_seg_set)
    dimensions.append({"name": "timeout_seg", "score": seg_sim, "weight": 2.0})

    # --- pod_conc ---
    pc_sim = _scope_sim(a.pod_concentration, b.pod_concentration)
    dimensions.append({"name": "pod_conc", "score": pc_sim, "weight": 1.5})

    # --- client_ratio ---
    if a.client_side_ratio > 0 or b.client_side_ratio > 0:
        cr_diff = abs(a.client_side_ratio - b.client_side_ratio)
        cr_sim = math.exp(-cr_diff * 6)
    else:
        cr_sim = 0.0
    dimensions.append({"name": "client_ratio", "score": cr_sim, "weight": 2.5})

    # --- server_ratio ---
    if a.server_side_ratio > 0 or b.server_side_ratio > 0:
        sr_diff = abs(a.server_side_ratio - b.server_side_ratio)
        sr_sim = math.exp(-sr_diff * 6)
    else:
        sr_sim = 0.0
    dimensions.append({"name": "server_ratio", "score": sr_sim, "weight": 2.5})

    # --- trace_pods ---
    ap_a = _log_normalize(a.trace_context_pods) if a.trace_context_pods > 0 else 0
    ap_b = _log_normalize(b.trace_context_pods) if b.trace_context_pods > 0 else 0
    if ap_a > 0 or ap_b > 0:
        ap_diff = abs(ap_a - ap_b)
        ap_sim = math.exp(-ap_diff * 3)
    else:
        ap_sim = 0.0
    dimensions.append({"name": "trace_pods", "score": ap_sim, "weight": 2.5})

    # --- anomalous_ratio ---
    if a.anomalous_ratio > 0 or b.anomalous_ratio > 0:
        ar_diff = abs(a.anomalous_ratio - b.anomalous_ratio)
        ar_sim = math.exp(-ar_diff * 3)
    else:
        ar_sim = 0.0
    dimensions.append({"name": "anomalous_ratio", "score": ar_sim, "weight": 1.5})

    # --- scope dimensions ---
    dimensions.append({"name": "pod_scope", "score": _scope_sim(a.pod_scope, b.pod_scope), "weight": 1.0})
    dimensions.append({"name": "host_scope", "score": _scope_sim(a.host_scope, b.host_scope), "weight": 1.0})
    dimensions.append({"name": "cluster_scope", "score": _scope_sim(a.cluster_scope, b.cluster_scope), "weight": 1.0})

    # --- p99_p50 ---
    if a.p99_p50_log > 0 and b.p99_p50_log > 0:
        diff = abs(a.p99_p50_log - b.p99_p50_log)
        p99_sim = math.exp(-diff * 3)
    elif a.p99_p50_log == 0 and b.p99_p50_log == 0:
        p99_sim = 0.0
    else:
        p99_sim = 0.0
    dimensions.append({"name": "p99_p50", "score": p99_sim, "weight": 2.0})

    # --- op_p99_p50 ---
    op_p99_sim = _cosine_sim(a.op_p99_p50_log, b.op_p99_p50_log)
    if not a.op_p99_p50_log and not b.op_p99_p50_log:
        op_p99_sim = 0.0
    dimensions.append({"name": "op_p99_p50", "score": op_p99_sim, "weight": 4.0})

    # 计算加权分数
    total_weight = sum(d["weight"] for d in dimensions)
    for d in dimensions:
        d["weighted_score"] = d["score"] * d["weight"]
    base_score = sum(d["weighted_score"] for d in dimensions) / total_weight if total_weight > 0 else 0.0

    cat_gate = 1.0 if a.fault_category == b.fault_category else 0.25
    asym_gate = fm_asym_penalty * sc_asym_penalty
    final_score = base_score * cat_gate * asym_gate

    # 排序并添加 label
    dimensions.sort(key=lambda x: -x["weighted_score"])
    for d in dimensions:
        d["label"] = DIMENSION_LABELS.get(d["name"], d["name"])

    # 生成原因说明
    reason = _generate_reason(a, b, dimensions, final_score, cat_gate, asym_gate)

    return {
        "final_score": round(final_score, 4),
        "base_score": round(base_score, 4),
        "cat_gate": cat_gate,
        "asym_gate": asym_gate,
        "dimensions": dimensions,
        "reason": reason,
    }


def _generate_reason(a: FeatureVector, b: FeatureVector, dimensions: list, final_score: float,
                     cat_gate: float, asym_gate: float) -> str:
    """生成人类可读的相似度原因说明。"""
    parts = []

    # 类别匹配
    if cat_gate == 1.0:
        parts.append(f"故障类别一致（{b.fault_category}）")
    else:
        parts.append(f"故障类别不匹配（{a.fault_category} vs {b.fault_category}），已降权至 25%")

    # 找出贡献最大的 3 个维度
    top_dims = [d for d in dimensions if d["weight"] > 0][:3]
    for d in top_dims:
        if d["score"] >= 0.7:
            parts.append(f"{d['label']}高度匹配（{d['score']:.2f}，权重{d['weight']:.1f}）")
        elif d["score"] >= 0.4:
            parts.append(f"{d['label']}部分匹配（{d['score']:.2f}，权重{d['weight']:.1f}）")

    # 不对称惩罚
    if asym_gate < 1.0:
        parts.append(f"特征不对称惩罚（{asym_gate:.2f}），部分维度仅一方有数据")

    return "; ".join(parts) + f"。最终相似度 {final_score:.2f}"


# ============================================================
# 案例库检索
# ============================================================

def load_case_library() -> list[dict]:
    """从 CASE_DIR 加载所有案例（含 features）。"""
    CaseServiceManager.ensure_case_dir()
    cases = []
    for filename in sorted(os.listdir(CASE_DIR)):
        if not filename.endswith(".json"):
            continue
        fpath = os.path.join(CASE_DIR, filename)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                case = json.load(f)
            if case.get("features"):
                cases.append(case)
        except (json.JSONDecodeError, OSError):
            continue
    return cases


async def find_similar_fault_types(
    features: dict,
    fault_category: str,
    top_k: int = 3,
    exclude_case_ids: set[str] | None = None,
    exclude_log_file_id: str | None = None,
) -> dict:
    """给定当前解析结果的特征，在案例库中查找最相似的 Top-K 故障类型。

    参数:
        exclude_case_ids: 需要排除的案例 ID 集合（leave-one-out 评估用）
        exclude_log_file_id: 需要排除的 log_file_id（API 调用时自动排除同源案例）
    """
    query_fv = FeatureVector(features, fault_category)
    cases = load_case_library()

    # 排除自身案例：按 case_id 和 log_file_id 双重过滤
    if exclude_case_ids:
        cases = [c for c in cases if c.get("id", "") not in exclude_case_ids]
    if exclude_log_file_id:
        cases = [c for c in cases if c.get("log_file_id", "") != exclude_log_file_id]

    if not cases:
        return {"top_matches": [], "library_size": 0}

    results = []
    for case in cases:
        case_fv = FeatureVector(case["features"], case.get("fault_category", "unknown"))
        detail = compute_similarity_detailed(query_fv, case_fv)
        results.append({
            "root_cause_type": merge_fault_type(case["root_cause_type"]),
            "fault_category": case.get("fault_category", "unknown"),
            "case_category": case.get("case_category", ""),
            "case_id": case.get("id", ""),
            "log_file_id": case.get("log_file_id", ""),
            "log_file_name": case.get("log_file_name", ""),
            "attachment_path": case.get("attachment_path", ""),
            "description": case.get("description", ""),
            **detail,
        })

    # 过滤 100% 匹配（防止自匹配穿帮）
    results = [r for r in results if r["final_score"] < 0.999]

    # 按相似度排序
    results.sort(key=lambda x: -x["final_score"])

    # 按大类分组：每大类内同小类只取最高分一条
    from collections import OrderedDict
    grouped: dict[str, OrderedDict] = OrderedDict()
    for r in results:
        bc = r.get("case_category") or r["root_cause_type"]
        rct = r["root_cause_type"]
        if bc not in grouped:
            grouped[bc] = OrderedDict()
        if rct not in grouped[bc]:
            grouped[bc][rct] = r  # 同小类只保留第一个（最高分）

    # 大类排序：取每大类最高分排序
    ranked_categories = sorted(grouped.items(), key=lambda kv: -next(iter(kv[1].values()))["final_score"])

    # Top5 大类，共取前10个小类：保证每大类至少1个，剩余按分数从高到低补
    top_k_cats = [(cat_name, list(cat_types.values())) for cat_name, cat_types in ranked_categories[:top_k]]
    # 展平所有候选，按分数降序
    all_candidates = sorted(
        ((cat_name, cm) for cat_name, cat_list in top_k_cats for cm in cat_list),
        key=lambda x: -x[1]["final_score"],
    )
    # 第一轮：每大类取最高分1条（保证5大类都出现）
    selected = []
    seen_cats: set[str] = set()
    for cat_name, cm in all_candidates:
        if cat_name not in seen_cats:
            seen_cats.add(cat_name)
            selected.append((cat_name, cm))
        if len(selected) >= min(top_k, len(top_k_cats)):
            break
    # 第二轮：从剩余候选中按分数补到10条
    selected_cats_types = {(c, cm["root_cause_type"]) for c, cm in selected}
    for cat_name, cm in all_candidates:
        if (cat_name, cm["root_cause_type"]) in selected_cats_types:
            continue
        selected.append((cat_name, cm))
        selected_cats_types.add((cat_name, cm["root_cause_type"]))
        if len(selected) >= 10:
            break

    top_matches = []
    for rank, (cat_name, cm) in enumerate(selected[:10], 1):
        top_matches.append({
            "rank": rank,
            "root_cause_type": cm["root_cause_type"],
            "fault_category": cm["fault_category"],
            "case_category": cat_name,
            "case_id": cm.get("case_id", ""),
            "log_file_id": cm.get("log_file_id", ""),
            "log_file_name": cm.get("log_file_name", ""),
            "attachment_path": cm.get("attachment_path", ""),
            "description": cm.get("description", ""),
            "similarity": cm["final_score"],
            "base_score": cm["base_score"],
            "cat_gate": cm["cat_gate"],
            "reason": cm["reason"],
            "breakdown": cm["dimensions"],
        })

    return {
        "top_matches": top_matches,
        "library_size": len(cases),
        "unique_types_count": len(grouped),
    }
