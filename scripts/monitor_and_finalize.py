#!/usr/bin/env python3
"""监控任务完成 → 重试失败 → 删除无故障 → 加入案例库"""

import os, sys, json, time, re
import urllib.request, urllib.parse
import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from rebuild_case_library_v2 import BROAD_CATEGORY, TYPE_CN, extract_root_cause_type
from upload_and_add_cases import NEW_BROAD_CATEGORY, NEW_TYPE_CN, is_skippable, create_case_via_api

API_BASE = "http://127.0.0.1:9772"
KB_NAME = "data_set"
PG_CONFIG = {"host": "127.0.0.1", "port": 15432, "user": "witty-ub", "password": "witty-ub", "dbname": "witty-ub"}

ALL_BROAD = {**BROAD_CATEGORY, **NEW_BROAD_CATEGORY}
ALL_CN = {**TYPE_CN, **NEW_TYPE_CN}


def pg_query(sql, params=None):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def pg_execute(sql, params=None):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    cur.close()
    conn.close()


def get_task_status_counts():
    rows = pg_query("SELECT status, count(*) FROM task GROUP BY status ORDER BY status")
    return {r[0]: r[1] for r in rows}


def api_get(path):
    req = urllib.request.Request(f"{API_BASE}{path}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def api_put(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="PUT")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def api_delete(path):
    req = urllib.request.Request(f"{API_BASE}{path}", method="DELETE")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def find_kb_id(name):
    payload = json.dumps({"page_cnt": 200, "page_num": 1}).encode("utf-8")
    req = urllib.request.Request(f"{API_BASE}/log_kb/list", data=payload,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    for kb in data.get("result", {}).get("kbs", []):
        if kb.get("name") == name:
            return kb["id"]
    return None


def get_log_file_ids(kb_id):
    """获取 KB 下所有 log_file: {log_file_id: (name, overall_status)}"""
    payload = json.dumps({"page_cnt": 500, "page_num": 1}).encode("utf-8")
    req = urllib.request.Request(f"{API_BASE}/log_file/list/{kb_id}", data=payload,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    files = data.get("result", {}).get("log_files", [])
    return {f["id"]: (f["name"], f.get("overall_status", "")) for f in files}


def get_log_file_detail(fid):
    data = api_get(f"/log_file/{fid}")
    return data.get("result", {}).get("log_file", {})


def retry_failed_tasks():
    """将 failed 任务的 log_file 重新触发解析"""
    rows = pg_query("""
        SELECT DISTINCT op_id FROM task
        WHERE status = 'failed' AND task_type = 'kv_cache_log_parse_worker'
    """)
    log_file_ids = [r[0] for r in rows]
    print(f"  需要重试的 failed log_file: {len(log_file_ids)}")

    for i, fid in enumerate(log_file_ids, 1):
        try:
            api_put(f"/log_file/run/{fid}", {"run": True})
            print(f"  [{i}/{len(log_file_ids)}] {fid[:8]}  重新触发")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{i}/{len(log_file_ids)}] {fid[:8]}  FAIL {e}")


def main():
    print("=" * 70)
    print("监控任务完成 → 重试失败 → 删除无故障 → 加入案例库")
    print("=" * 70)

    kb_id = find_kb_id(KB_NAME)
    if not kb_id:
        print(f"[ERROR] 知识库 {KB_NAME} 不存在")
        return
    print(f"\n[0] data_set KB ID: {kb_id}")

    # Phase 1: 等待 pending 任务完成
    print(f"\n[1] 等待 pending 任务完成...")
    while True:
        counts = get_task_status_counts()
        pending = counts.get("pending", 0)
        running = counts.get("running", 0)
        failed = counts.get("failed", 0)
        successful = counts.get("successful", 0)
        print(f"  pending={pending} running={running} failed={failed} successful={successful}")
        if pending == 0 and running == 0:
            break
        time.sleep(30)

    print(f"\n  所有 pending/running 任务完成！")

    # Phase 2: 重试 failed 任务
    print(f"\n[2] 重试 failed 任务...")
    counts = get_task_status_counts()
    failed = counts.get("failed", 0)
    if failed > 0:
        retry_failed_tasks()
        # 等待重试完成
        print(f"\n  等待重试任务完成...")
        while True:
            counts = get_task_status_counts()
            pending = counts.get("pending", 0)
            running = counts.get("running", 0)
            print(f"  pending={pending} running={running} failed={counts.get('failed',0)} successful={counts.get('successful',0)}")
            if pending == 0 and running == 0:
                break
            time.sleep(30)

    # Phase 3: 删除无故障和解析失败的 case
    print(f"\n[3] 删除无故障和解析失败的 case...")
    log_files = get_log_file_ids(kb_id)
    print(f"  KB 中 log_file 总数: {len(log_files)}")

    # 检查每个 log_file 的状态
    to_delete = []
    success_files = {}  # fid -> (name, status)

    for i, (fid, (name, status)) in enumerate(log_files.items(), 1):
        try:
            lf = get_log_file_detail(fid)
            overall = lf.get("overall_status", "")
            anomaly_cnt = lf.get("anomaly_cnt", 0)
            trace_failure_cnt = lf.get("trace_failure_event_cnt", 0)

            if overall in ("failed", "error") or overall == "pending":
                to_delete.append((fid, name, f"status={overall}"))
            elif anomaly_cnt == 0 and trace_failure_cnt == 0:
                to_delete.append((fid, name, f"no_fault(anomaly={anomaly_cnt},trace_failure={trace_failure_cnt})"))
            else:
                success_files[fid] = (name, overall)

            if i % 50 == 0:
                print(f"  检查进度: {i}/{len(log_files)}")
        except Exception as e:
            print(f"  [ERROR] {fid[:8]} {name[:40]}  {e}")

    print(f"\n  解析成功: {len(success_files)}")
    print(f"  需删除（无故障/解析失败）: {len(to_delete)}")

    for fid, name, reason in to_delete:
        try:
            api_delete(f"/log_file/{fid}")
            print(f"  [DEL] {name[:55]}  {reason}")
        except Exception as e:
            print(f"  [DEL FAIL] {name[:55]}  {e}")

    # Phase 4: 将可归类的 case 加入案例库
    print(f"\n[4] 将可归类的 case 加入案例库...")
    created = 0
    skipped = 0
    fail = 0

    for i, (fid, (name, status)) in enumerate(success_files.items(), 1):
        rc = extract_root_cause_type(name)
        if not rc or is_skippable(rc) or rc not in ALL_BROAD:
            skipped += 1
            continue

        broad_cat = ALL_BROAD[rc]
        rc_cn = ALL_CN.get(rc, rc)

        try:
            resp = create_case_via_api(kb_id, fid, rc_cn, broad_cat, name, rc)
            if resp.get("code") == 200:
                created += 1
                has_feat = "有" if resp.get("result", {}).get("features") else "无"
                if i % 20 == 0 or i <= 5:
                    print(f"  [{i}/{len(success_files)}] {name[:55]}  OK  {broad_cat}/{rc_cn}  features={has_feat}")
            else:
                fail += 1
                if fail <= 5:
                    print(f"  [{i}/{len(success_files)}] {name[:55]}  FAIL  {resp.get('message', '')}")
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"  [{i}/{len(success_files)}] {name[:55]}  FAIL  {e}")

    # 汇总
    print(f"\n{'=' * 70}")
    print("完成！")
    print(f"{'=' * 70}")
    print(f"  KB log_file 总数: {len(log_files)}")
    print(f"  解析成功: {len(success_files)}")
    print(f"  删除（无故障/解析失败）: {len(to_delete)}")
    print(f"  加入案例库: {created}")
    print(f"  跳过（不可归类）: {skipped}")
    print(f"  失败: {fail}")


if __name__ == "__main__":
    main()
