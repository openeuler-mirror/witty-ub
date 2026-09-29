#!/usr/bin/env python3
"""批量导入 data_set / test_set 到 witty-ub 系统并运行匹配验证。

用法:
    python scripts/run_dataset_match.py [--skip-upload] [--skip-cases] [--skip-match]

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - data_set 和 test_set 目录已就绪

流程:
    1. 创建知识库，上传日志文件，触发解析
    2. 等待解析完成
    3. 从 data_set 提取特征创建案例（JSON）
    4. 从 test_set 提取特征，运行匹配引擎验证
"""

import os
import sys
import re
import json
import time
import asyncio
import math
import argparse
from collections import Counter, defaultdict
from urllib.parse import quote_plus

import requests

# ============================================================
# 配置
# ============================================================

API_BASE = "http://127.0.0.1:9772"
API_TIMEOUT = 120
UPLOAD_DELAY = 0.5
POLL_INTERVAL = 5  # 秒
POLL_MAX_WAIT = 3600  # 最长等待1小时

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "witty-ub")
PG_USER = os.getenv("PG_USER", "witty-ub")

PG_PASSWD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deploy", "pg.passwd",
)

BASE_DATA_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete"
DATA_SET_DIR = os.path.join(BASE_DATA_DIR, "data_set")
TEST_SET_DIR = os.path.join(BASE_DATA_DIR, "test_set")

# 案例输出目录
WITTY_DIR = os.getenv("WITTY_DIR", "/Users/zhaoyujin/Desktop/witty-ub/case_data")
CASE_DIR = os.path.join(WITTY_DIR, "case")

SKIP_FILES = {"clean_logs.sh", "filter_fault_trace.sh"}


def read_pg_password() -> str:
    with open(PG_PASSWD_FILE, "r") as f:
        return f.read().strip()


# ============================================================
# API 辅助函数
# ============================================================

def api_get(path, **kwargs):
    resp = requests.get(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_post(path, **kwargs):
    resp = requests.post(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_put(path, **kwargs):
    resp = requests.put(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_delete(path, **kwargs):
    resp = requests.delete(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


# ============================================================
# Phase 1: 上传数据集
# ============================================================

def get_or_create_knowledge_base(name: str, description: str) -> str:
    data = api_post("/log_kb/list", json={"page_cnt": 200, "page_num": 1})
    if data.get("code") == 200:
        for kb in data["result"].get("kbs", []):
            if kb["name"] == name:
                kb_id = kb["id"]
                print(f"  [SKIP] 知识库已存在: name={name}, kb_id={kb_id}")
                return kb_id

    data = api_post("/log_kb", json={"name": name, "description": description})
    if data.get("code") != 200:
        raise RuntimeError(f"创建知识库失败: {data}")
    kb_id = data["result"]["kb_id"]
    print(f"  [OK] 知识库已创建: name={name}, kb_id={kb_id}")
    return kb_id


def get_existing_log_file_names(kb_id: str) -> set:
    names = set()
    page = 1
    while True:
        data = api_post(f"/log_file/list/{kb_id}", json={"page_cnt": 100, "page_num": page})
        if data.get("code") != 200:
            break
        files = data["result"].get("log_files", [])
        for f in files:
            names.add(f["name"])
        if len(files) < 100:
            break
        page += 1
    return names


def upload_log_file(kb_id: str, subdir_name: str, subdir_path: str) -> str:
    payload = {
        "upload_log_file_configs": [
            {
                "name": subdir_name,
                "source_type": "local",
                "source": subdir_path,
                "log_type": "KVCache",
            }
        ]
    }
    data = api_post(f"/log_file/{kb_id}", json=payload)
    if data.get("code") != 200:
        raise RuntimeError(f"上传日志文件失败: {data}")
    log_file_ids = data["result"]["log_file_ids"]
    if not log_file_ids:
        raise RuntimeError(f"上传日志文件返回空 ID 列表: {data}")
    return log_file_ids[0]


def run_parse(log_file_id: str) -> str:
    data = api_put(f"/log_file/run/{log_file_id}", params={"run": True})
    if data.get("code") != 200:
        raise RuntimeError(f"触发解析失败: {data}")
    return data["result"].get("task_id", "")


def upload_dataset(data_dir: str, kb_name: str, kb_desc: str) -> str:
    """上传数据集到知识库，返回 kb_id。"""
    print(f"\n{'='*60}")
    print(f"上传数据集: {kb_name}")
    print(f"目录: {data_dir}")
    print(f"{'='*60}")

    if not os.path.isdir(data_dir):
        print(f"  [ERROR] 目录不存在: {data_dir}")
        return ""

    kb_id = get_or_create_knowledge_base(kb_name, kb_desc)

    # 查找案例目录：data_dir/{source}/lingqu_kvcache_xxx/ 格式
    # source = yxh_new 或 yxh_new_0530
    all_subdirs = []
    for source_dir in sorted(os.listdir(data_dir)):
        source_path = os.path.join(data_dir, source_dir)
        if not os.path.isdir(source_path):
            continue
        for case_dir in sorted(os.listdir(source_path)):
            case_path = os.path.join(source_path, case_dir)
            if not os.path.isdir(case_path):
                continue
            rel = os.path.relpath(case_path, data_dir)
            all_subdirs.append((rel, case_path))

    existing_names = get_existing_log_file_names(kb_id)
    print(f"  已上传 {len(existing_names)} 个日志文件")

    to_upload = [(rel, full) for rel, full in all_subdirs if rel not in existing_names]
    print(f"  待上传 {len(to_upload)}/{len(all_subdirs)} 个子目录")

    success = 0
    fail = 0
    for idx, (subdir_name, subdir_path) in enumerate(to_upload, 1):
        print(f"  [{idx}/{len(to_upload)}] {subdir_name}", end="", flush=True)
        try:
            log_file_id = upload_log_file(kb_id, subdir_name, subdir_path)
            run_parse(log_file_id)
            success += 1
            print(f" -> OK")
        except Exception as e:
            fail += 1
            print(f" -> FAIL: {e}")
        if idx < len(to_upload):
            time.sleep(UPLOAD_DELAY)

    print(f"  完成: 成功={success}, 失败={fail}, 跳过={len(all_subdirs)-len(to_upload)}")
    return kb_id


def wait_for_parsing(kb_id: str, kb_name: str):
    """等待知识库下所有任务解析完成。"""
    print(f"\n等待解析完成: {kb_name} (kb_id={kb_id})")
    start = time.time()
    while True:
        data = api_post("/task/list", json={
            "kb_id": kb_id,
            "page_cnt": 500,
            "page_num": 1,
        })
        if data.get("code") != 200:
            print(f"  [WARN] 查询任务列表失败，继续等待...")
            time.sleep(POLL_INTERVAL)
            continue

        tasks = data["result"].get("tasks", [])
        if not tasks:
            elapsed = time.time() - start
            if elapsed > 30:
                print(f"  [WARN] 30秒内无任务，可能尚未创建")
                break
            time.sleep(POLL_INTERVAL)
            continue

        total = len(tasks)
        pending = sum(1 for t in tasks if t.get("status") not in ("successful", "failed"))
        successful = sum(1 for t in tasks if t.get("status") == "successful")
        failed = sum(1 for t in tasks if t.get("status") == "failed")

        elapsed = time.time() - start
        print(f"  [{elapsed:.0f}s] 总={total}, 成功={successful}, 失败={failed}, 进行中={pending}")

        if pending == 0:
            print(f"  解析全部完成! 成功={successful}, 失败={failed}")
            return

        if elapsed > POLL_MAX_WAIT:
            print(f"  [WARN] 等待超时({POLL_MAX_WAIT}s)，仍有 {pending} 个任务未完成")
            return

        time.sleep(POLL_INTERVAL)


# ============================================================
# Phase 2: 提取 data_set 特征创建案例
# ============================================================

# ============================================================
# 故障类型合并映射（业务等价的近亲类型）
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


def extract_root_cause_type(log_name: str) -> str:
    # 去掉来源前缀: yxh_new/xxx 或 yxh_new_0530/xxx -> xxx
    base = log_name.rsplit("/", 1)[-1] if "/" in log_name else log_name
    m = re.match(r"^lingqu_kvcache_(.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$", base)
    raw = m.group(1) if m else base
    return merge_fault_type(raw)


async def create_cases_from_dataset(kb_id: str, kb_name: str):
    """从 data_set 知识库提取特征创建案例。"""
    import psycopg2
    from latency.services.case_service import CaseServiceManager
    from latency.database.engine import PGManager

    print(f"\n{'='*60}")
    print(f"从 {kb_name} 创建案例")
    print(f"{'='*60}")

    pg_password = read_pg_password()
    dsn_sync = f"host={PG_HOST} port={PG_PORT} dbname={PG_DATABASE} user={PG_USER} password={pg_password}"
    dsn_async = (
        f"postgresql+asyncpg://{PG_USER}:{quote_plus(pg_password)}"
        f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    )

    PGManager.initialize(dsn_async)

    conn = psycopg2.connect(dsn_sync)
    conn.autocommit = True
    cur = conn.cursor()

    # 查找解析成功的 log_file
    cur.execute(
        """
        SELECT DISTINCT lf.id, lf.name
        FROM log_file lf
        JOIN task t ON t.op_id = lf.id AND t.task_type = 'kv_cache_log_parse_worker'
        WHERE lf.kb_id = %s AND t.status = 'successful'
        ORDER BY lf.name
        """,
        (kb_id,),
    )
    log_files = cur.fetchall()
    conn.close()

    print(f"找到 {len(log_files)} 个解析成功的 log_file")

    os.makedirs(CASE_DIR, exist_ok=True)

    skipped = 0
    created = 0
    failed = 0
    results = []

    for idx, (log_id, log_name) in enumerate(log_files, 1):
        rct = extract_root_cause_type(log_name)
        print(f"  [{idx}/{len(log_files)}] {log_name} ({rct})", end="", flush=True)

        # 跳过已有案例
        existing_id = CaseServiceManager.find_existing_case_by_log_name(log_name)
        if existing_id:
            jp = os.path.join(CASE_DIR, f"{existing_id}.json")
            try:
                with open(jp, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
                if existing.get("features") is not None:
                    print(f" -> SKIP (已有)")
                    skipped += 1
                    continue
                else:
                    os.remove(jp)
            except Exception:
                pass

        try:
            case_record = await CaseServiceManager.create_case(
                kb_id=kb_id,
                root_cause_type=rct,
                description=f"自动导入: {rct}",
                task_names=[log_name],
                log_file_id=log_id,
                log_file_name=log_name,
            )
            fault_cat = case_record.get("fault_category", "unknown")
            print(f" -> OK ({fault_cat})")
            created += 1
            results.append({"root_cause_type": rct, "fault_category": fault_cat})
        except Exception as e:
            failed += 1
            print(f" -> FAIL: {e}")

    print(f"\n  汇总: 跳过={skipped}, 新建={created}, 失败={failed}")
    if results:
        cat_counter = Counter(r["fault_category"] for r in results)
        print(f"  故障类别分布:")
        for cat, cnt in cat_counter.most_common():
            print(f"    {cat}: {cnt}")

    await PGManager.close()
    return created


# ============================================================
# Phase 3: 匹配引擎
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


class FeatureVector:
    """将案例特征转化为可比较的向量"""

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


def compute_similarity(a: FeatureVector, b: FeatureVector) -> float:
    scores = {}

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
    scores["failure_mode"] = (fm_sim, fm_weight)
    fm_asym_penalty = 0.3 if (a_has_fm != b_has_fm) else 1.0

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

    op_sim = _cosine_sim(a.operation_dist, b.operation_dist)
    if not a.operation_dist and not b.operation_dist:
        op_sim = 0.0
    scores["operation"] = (op_sim, 3.0)

    cop_sim = _cosine_sim(a.conn_operation_dist, b.conn_operation_dist)
    if not a.conn_operation_dist and not b.conn_operation_dist:
        cop_sim = 0.0
    scores["conn_operation"] = (cop_sim, 2.0)

    seg_r_sim = _cosine_sim(a.seg_ranking_vec, b.seg_ranking_vec)
    if not a.seg_ranking_vec and not b.seg_ranking_vec:
        seg_r_sim = 0.0
    scores["seg_ranking"] = (seg_r_sim, 3.0)

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

    seg_sim = _jaccard_sim(a.timeout_seg_set, b.timeout_seg_set)
    scores["timeout_seg"] = (seg_sim, 2.0)

    pc_sim = _scope_sim(a.pod_concentration, b.pod_concentration)
    scores["pod_conc"] = (pc_sim, 1.5)

    if a.client_side_ratio > 0 or b.client_side_ratio > 0:
        cr_diff = abs(a.client_side_ratio - b.client_side_ratio)
        cr_sim = math.exp(-cr_diff * 6)
    else:
        cr_sim = 0.0
    scores["client_ratio"] = (cr_sim, 2.5)

    if a.server_side_ratio > 0 or b.server_side_ratio > 0:
        sr_diff = abs(a.server_side_ratio - b.server_side_ratio)
        sr_sim = math.exp(-sr_diff * 6)
    else:
        sr_sim = 0.0
    scores["server_ratio"] = (sr_sim, 2.5)

    ap_a = _log_normalize(a.trace_context_pods) if a.trace_context_pods > 0 else 0
    ap_b = _log_normalize(b.trace_context_pods) if b.trace_context_pods > 0 else 0
    if ap_a > 0 or ap_b > 0:
        ap_diff = abs(ap_a - ap_b)
        ap_sim = math.exp(-ap_diff * 3)
    else:
        ap_sim = 0.0
    scores["trace_pods"] = (ap_sim, 2.5)

    if a.anomalous_ratio > 0 or b.anomalous_ratio > 0:
        ar_diff = abs(a.anomalous_ratio - b.anomalous_ratio)
        ar_sim = math.exp(-ar_diff * 3)
    else:
        ar_sim = 0.0
    scores["anomalous_ratio"] = (ar_sim, 1.5)

    scores["pod_scope"] = (_scope_sim(a.pod_scope, b.pod_scope), 1.0)
    scores["host_scope"] = (_scope_sim(a.host_scope, b.host_scope), 1.0)
    scores["cluster_scope"] = (_scope_sim(a.cluster_scope, b.cluster_scope), 1.0)

    if a.p99_p50_log > 0 and b.p99_p50_log > 0:
        diff = abs(a.p99_p50_log - b.p99_p50_log)
        p99_sim = math.exp(-diff * 3)
    elif a.p99_p50_log == 0 and b.p99_p50_log == 0:
        p99_sim = 0.0
    else:
        p99_sim = 0.0
    scores["p99_p50"] = (p99_sim, 2.0)

    op_p99_sim = _cosine_sim(a.op_p99_p50_log, b.op_p99_p50_log)
    if not a.op_p99_p50_log and not b.op_p99_p50_log:
        op_p99_sim = 0.0
    scores["op_p99_p50"] = (op_p99_sim, 4.0)

    total_weight = sum(w for _, w in scores.values())
    weighted_sum = sum(s * w for s, w in scores.values())
    base_sim = weighted_sum / total_weight if total_weight > 0 else 0.0

    cat_gate = 1.0 if a.fault_category == b.fault_category else 0.25
    asym_gate = fm_asym_penalty * sc_asym_penalty

    return base_sim * cat_gate * asym_gate


async def run_match_engine(data_kb_id: str, test_kb_id: str):
    """运行匹配引擎。"""
    import psycopg2
    from latency.services.feature_extraction import FeatureExtractionManager
    from latency.database.engine import PGManager

    print(f"\n{'='*60}")
    print(f"运行匹配引擎")
    print(f"{'='*60}")

    # Step 1: 加载训练集特征（从案例 JSON）
    train_cases = []
    for f in sorted(os.listdir(CASE_DIR)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(CASE_DIR, f), "r", encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("features"):
            fv = FeatureVector(d["features"], d.get("fault_category", "unknown"))
            train_cases.append({
                "root_cause_type": merge_fault_type(d["root_cause_type"]),
                "features": d["features"],
                "fault_category": d.get("fault_category", "unknown"),
                "fv": fv,
            })

    print(f"训练案例数: {len(train_cases)}")
    train_types = set(c["root_cause_type"] for c in train_cases)
    print(f"训练故障类型: {len(train_types)}")

    # Step 2: 提取测试集特征
    pg_password = read_pg_password()
    dsn_sync = f"host={PG_HOST} port={PG_PORT} dbname={PG_DATABASE} user={PG_USER} password={pg_password}"
    dsn_async = (
        f"postgresql+asyncpg://{PG_USER}:{quote_plus(pg_password)}"
        f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    )

    PGManager.initialize(dsn_async)

    conn = psycopg2.connect(dsn_sync)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        """
        SELECT DISTINCT lf.id, lf.name
        FROM log_file lf
        JOIN task t ON t.op_id = lf.id AND t.task_type = 'kv_cache_log_parse_worker'
        WHERE lf.kb_id = %s AND t.status = 'successful'
        ORDER BY lf.name
        """,
        (test_kb_id,),
    )
    test_log_files = cur.fetchall()
    conn.close()

    print(f"测试集成功任务数: {len(test_log_files)}")

    test_cases = []
    for idx, (log_id, log_name) in enumerate(test_log_files, 1):
        rct = extract_root_cause_type(log_name)
        print(f"  [{idx}/{len(test_log_files)}] {log_name} -> {rct}", end="", flush=True)
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
            print(f" -> OK")
        except Exception as e:
            print(f" -> FAIL: {e}")
            test_cases.append({
                "log_id": log_id,
                "log_name": log_name,
                "root_cause_type": rct,
                "features": None,
                "fault_category": "unknown",
                "fv": None,
            })

    await PGManager.close()

    # Step 3: 匹配
    valid_test = [tc for tc in test_cases if tc["fv"] is not None and tc["root_cause_type"] in train_types]
    invalid_test = [tc for tc in test_cases if tc not in valid_test]

    print(f"\n有效测试案例: {len(valid_test)}")
    print(f"无效测试案例: {len(invalid_test)}")

    results = []
    for tc in valid_test:
        query_fv = tc["fv"]
        gt = tc["root_cause_type"]

        sims = []
        for tr in train_cases:
            sim = compute_similarity(query_fv, tr["fv"])
            sims.append((tr["root_cause_type"], sim))

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

    # Step 4: 统计
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    top3_correct = sum(1 for r in results if r["top3_correct"])
    top5_correct = sum(1 for r in results if r["top5_correct"])

    print(f"\n{'='*60}")
    print(f"准确度统计")
    print(f"{'='*60}")
    print(f"有效测试案例: {total}")
    if total > 0:
        print(f"Top-1 准确率: {correct}/{total} = {correct/total*100:.1f}%")
        print(f"Top-3 准确率: {top3_correct}/{total} = {top3_correct/total*100:.1f}%")
        print(f"Top-5 准确率: {top5_correct}/{total} = {top5_correct/total*100:.1f}%")

    by_cat = defaultdict(list)
    for r in results:
        tc = next(t for t in valid_test if t["log_name"] == r["log_name"])
        by_cat[tc["fault_category"]].append(r)

    print(f"\n按故障类别分组:")
    for cat in sorted(by_cat.keys()):
        group = by_cat[cat]
        c = sum(1 for r in group if r["correct"])
        print(f"  {cat}: Top-1={c}/{len(group)}={c/len(group)*100:.1f}%")

    errors = [r for r in results if not r["correct"]]
    if errors:
        print(f"\n错误案例 ({len(errors)}):")
        for r in errors[:20]:
            print(f"  {r['ground_truth']} -> predicted={r['predicted']} "
                  f"(conf={r['confidence']})")

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "match_results_v2.json",
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_valid": total,
            "top1_accuracy": correct / total if total > 0 else 0,
            "top3_accuracy": top3_correct / total if total > 0 else 0,
            "top5_accuracy": top5_correct / total if total > 0 else 0,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


# ============================================================
# 主函数
# ============================================================

async def async_main(args):
    # 健康检查
    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # Phase 1: 上传
    data_kb_id = None
    test_kb_id = None

    if not args.skip_upload:
        data_kb_id = upload_dataset(DATA_SET_DIR, "data_set", "data_set 训练验证集")
        test_kb_id = upload_dataset(TEST_SET_DIR, "test_set", "test_set 测试集")
        wait_for_parsing(data_kb_id, "data_set")
        wait_for_parsing(test_kb_id, "test_set")
    else:
        # 查找已有知识库
        data = api_post("/log_kb/list", json={"page_cnt": 200, "page_num": 1})
        for kb in data["result"].get("kbs", []):
            if kb["name"] == "data_set":
                data_kb_id = kb["id"]
            elif kb["name"] == "test_set":
                test_kb_id = kb["id"]
        print(f"跳过上传，使用已有知识库: data_set={data_kb_id}, test_set={test_kb_id}")

    if not data_kb_id or not test_kb_id:
        print("[ERROR] 知识库 ID 未找到，请先上传或检查知识库名称")
        sys.exit(1)

    # Phase 2: 创建案例
    if not args.skip_cases:
        await create_cases_from_dataset(data_kb_id, "data_set")
    else:
        print("跳过案例创建")

    # Phase 3: 匹配
    if not args.skip_match:
        await run_match_engine(data_kb_id, test_kb_id)
    else:
        print("跳过匹配")


def main():
    parser = argparse.ArgumentParser(description="批量导入数据集并运行匹配验证")
    parser.add_argument("--skip-upload", action="store_true", help="跳过上传阶段")
    parser.add_argument("--skip-cases", action="store_true", help="跳过案例创建阶段")
    parser.add_argument("--skip-match", action="store_true", help="跳过匹配阶段")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
