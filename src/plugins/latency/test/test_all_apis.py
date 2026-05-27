#!/usr/bin/env python3
"""
测试 latency 插件所有接口
- 先造 mock 数据到数据库（绕过 log_file 解析链路）
- 然后调用每一个接口验证连通性与基本响应
"""
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
import requests

BASE_URL = "http://127.0.0.1:9772"
DB_PATH = "/home/zjq/witty-ub/src/plugins/latency/latency.db"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def db_execute(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ensure_mock_data():
    """插入 mock 数据，用于测试查询类接口"""
    print("[Setup] 准备 mock 数据...")

    # 1) 确保至少有一个 knowledge base
    kb_rows = db_execute("SELECT id FROM log_knowledge_table WHERE existed_status=1 LIMIT 1")
    if not kb_rows:
        kb_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO log_knowledge_table
            (id, image_bytes, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (kb_id, None, "mock_kb", "mock description", 0, 0, 0, 1, now(), now()),
        )
        print(f"  创建 mock kb: {kb_id}")
    else:
        kb_id = kb_rows[0]["id"]
        print(f"  使用已有 kb: {kb_id}")

    # 2) 确保至少有一个 log_file（local 方式，用一个本地真实文件路径）
    lf_rows = db_execute("SELECT id FROM log_file_table WHERE existed_status=1 LIMIT 1")
    if not lf_rows:
        lf_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO log_file_table
            (id, kb_id, name, parse_status, file_path, file_size, anomaly_cnt, existed_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lf_id, kb_id, "mock.log", "pending", "/etc/hostname", 12, 0, 1, now()),
        )
        print(f"  创建 mock log_file: {lf_id}")
    else:
        lf_id = lf_rows[0]["id"]
        print(f"  使用已有 log_file: {lf_id}")

    # 3) 确保至少有一个 log_parse_result
    lpr_rows = db_execute("SELECT id FROM log_parse_result_table WHERE existed_status=1 LIMIT 1")
    if not lpr_rows:
        lpr_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO log_parse_result_table
            (id, log_id, aggregated_event_id, anomalous_event_id, trace_id, timestamp, src_ip, dst_ip, pod_ip,
             total_latency, c2w_latency, worker_query_meta_latency, urma_total_latency, urma_link_latency,
             urma_inflight_count, c2w_urma_latency, w2w_urma_latency, operation, data_size, offset,
             is_anomalous, content, anomaly_reason, anomaly_score, remark, existed_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lpr_id, lf_id, "", "", "trace-1", now(), "192.168.1.1", "192.168.1.2", "10.0.0.1",
                1.5, 0.5, 0.3, 0.4, 0.2, 10, 0.1, 0.2, "READ", "4KB", 1,
                0, "content", "", 0.0, "", 1, now()
            ),
        )
        print(f"  创建 mock log_parse_result: {lpr_id}")
    else:
        lpr_id = lpr_rows[0]["id"]
        print(f"  使用已有 log_parse_result: {lpr_id}")

    # 4) 确保至少有一个 aggregated_event
    ae_rows = db_execute("SELECT id FROM src_dst_aggregated_event_table WHERE existed_status=1 LIMIT 1")
    if not ae_rows:
        ae_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO src_dst_aggregated_event_table
            (id, src_ip, dst_ip, log_id, log_parse_result_cnt, anomaly_log_parse_result_cnt, anomaly_cnt,
             ave_total_latency, min_total_latency, max_total_latency, p99_total_latency, p95_total_latency,
             ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency, p99_query_meta_latency, p95_query_meta_latency,
             ave_urma_total_latency, min_urma_total_latency, max_urma_total_latency, p99_urma_total_latency, p95_urma_total_latency,
             ave_urma_link_latency, min_urma_link_latency, max_urma_link_latency, p99_urma_link_latency, p95_urma_link_latency,
             ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency, p99_c2w_urma_latency, p95_c2w_urma_latency,
             ave_w2w_urma_latency, min_w2w_urma_latency, max_w2w_urma_latency, p99_w2w_urma_latency, p95_w2w_urma_latency,
             existed_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ae_id, "192.168.1.1", "192.168.1.2", lf_id, 1, 0, 0,
                1.5, 0.1, 2.0, 1.9, 1.8,
                0.3, 0.1, 0.5, 0.45, 0.4,
                0.4, 0.1, 0.6, 0.55, 0.5,
                0.2, 0.05, 0.3, 0.28, 0.25,
                0.1, 0.05, 0.15, 0.14, 0.12,
                0.2, 0.05, 0.3, 0.28, 0.25,
                1, now()
            ),
        )
        print(f"  创建 mock aggregated_event: {ae_id}")
    else:
        ae_id = ae_rows[0]["id"]
        print(f"  使用已有 aggregated_event: {ae_id}")

    # 5) 确保至少有一个 anomalous_event
    ane_rows = db_execute("SELECT id FROM anomalous_event_table WHERE existed_status=1 LIMIT 1")
    if not ane_rows:
        ane_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO anomalous_event_table
            (id, log_id, aggregated_event_id, start_log_parse_offset, end_log_parse_offset, anomaly_reason, existed_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ane_id, lf_id, ae_id, 1, 5, "mock anomaly", 1, now()),
        )
        print(f"  创建 mock anomalous_event: {ane_id}")
    else:
        ane_id = ane_rows[0]["id"]
        print(f"  使用已有 anomalous_event: {ane_id}")

    # 6) 确保至少有一个 anomalous_event_chain
    aec_rows = db_execute("SELECT id FROM anomalous_event_chain_table WHERE existed_status=1 LIMIT 1")
    if not aec_rows:
        aec_id = str(uuid.uuid4())
        db_execute(
            """INSERT INTO anomalous_event_chain_table
            (id, log_id, anomalous_event_id, name, description, anomaly_code, offset, existed_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (aec_id, lf_id, ane_id, "chain-1", "desc", "A001", 1, 1, now()),
        )
        print(f"  创建 mock anomalous_event_chain: {aec_id}")
    else:
        aec_id = aec_rows[0]["id"]
        print(f"  使用已有 anomalous_event_chain: {aec_id}")

    return {
        "kb_id": kb_id,
        "log_file_id": lf_id,
        "result_id": lpr_id,
        "aggregated_event_id": ae_id,
        "anomalous_event_id": ane_id,
        "event_chain_id": aec_id,
    }


def call(method, path, payload=None, params=None, desc=""):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=payload, params=params, timeout=10)
        elif method == "PUT":
            r = requests.put(url, json=payload, params=params, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, params=params, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")

        ok = r.status_code == 200
        try:
            body = r.json()
        except Exception:
            body = r.text

        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status} [{method}] {path} -> HTTP {r.status_code}")
        if not ok:
            print(f"       Response: {json.dumps(body, ensure_ascii=False)[:300]}")
        return ok, body
    except Exception as e:
        print(f"  ❌ FAIL [{method}] {path} -> Exception: {e}")
        return False, str(e)


def main():
    print("=" * 60)
    print("Latency Plugin API 全接口测试")
    print("=" * 60)

    # 0. 健康检查
    print("\n[Health Check]")
    ok, body = call("GET", "/health_check", desc="health")
    if not ok:
        print("服务未就绪，退出测试。")
        return

    # 1. 造数据
    ids = ensure_mock_data()
    kb_id = ids["kb_id"]
    log_file_id = ids["log_file_id"]
    result_id = ids["result_id"]
    aggregated_event_id = ids["aggregated_event_id"]
    anomalous_event_id = ids["anomalous_event_id"]
    event_chain_id = ids["event_chain_id"]

    # 2. log_kb 接口
    print("\n[log_kb]")
    call("POST", "/log_kb", payload={"name": "test_kb", "description": "test desc"}, desc="create_log_kb")
    call("GET", f"/log_kb/{kb_id}", desc="get_log_kb")
    call("PUT", f"/log_kb/{kb_id}", payload={"name": "test_kb_updated", "description": "updated desc"}, desc="update_log_kb")
    call("POST", "/log_kb/list", payload={"page_cnt": 10, "page_num": 1}, desc="list_log_kbs")

    # 3. log_file 接口
    print("\n[log_file]")
    # 使用本地真实文件 /etc/hostname 创建 log_file
    call("POST", f"/log_file/{kb_id}", payload={
        "upload_log_file_configs": [
            {"name": "test_local.log", "source_type": "local", "source": "/etc/hostname"}
        ]
    }, desc="upload_log_file")
    call("GET", f"/log_file/{log_file_id}", desc="get_log_file")
    call("POST", f"/log_file/list/{kb_id}", payload={"page_cnt": 10, "page_num": 1}, desc="list_log_files")
    call("PUT", f"/log_file/{log_file_id}", payload={"name": "updated.log"}, desc="update_log_file")
    call("PUT", f"/log_file/run/{log_file_id}", params={"run": "true"}, desc="run_log_file")
    call("PUT", f"/log_file/run/{log_file_id}", params={"run": "false"}, desc="stop_log_file")

    # 4. log_parse_result 接口
    print("\n[log_parse_result]")
    call("POST", "/log_parse_result/list", payload={
        "page_cnt": 10, "page_num": 1,
        "src_ip": "192.168", "is_anomalous": False
    }, desc="list_log_parse_results")
    call("GET", f"/log_parse_result/{result_id}", desc="get_log_parse_result")

    # 5. aggregated_event 接口
    print("\n[aggregated_event]")
    call("POST", "/aggregated_event/list", payload={
        "page_cnt": 10, "page_num": 1,
        "src_ip": "192.168"
    }, desc="list_aggregated_events")
    call("GET", f"/aggregated_event/{aggregated_event_id}", desc="get_aggregated_event")

    # 6. anomalous_event 接口
    print("\n[anomalous_event]")
    call("GET", f"/anomalous_event/{anomalous_event_id}", desc="get_anomalous_event")

    # 7. anomalous_event_chain 接口
    print("\n[anomalous_event_chain]")
    call("POST", "/anomalous_event_chain/list", payload={
        "page_cnt": 10, "page_num": 1
    }, desc="list_anomalous_event_chains")

    # 8. 清理（可选）
    print("\n[Cleanup]")
    # 删除刚才通过接口创建的 log_file（如果有的话）
    # 这里只是演示，删除通过 upload 接口创建的 log_file 记录
    # 由于我们不知道 upload 接口返回的 id，这里就不做复杂处理了
    call("DELETE", f"/log_file/{log_file_id}", desc="delete_log_file")
    # 删除测试时创建的 kb（前面 create_log_kb 返回的 kb_id 需要捕获，这里为了简洁直接 list 后删掉 name=test_kb 的）
    # 不删除原始 mock kb，避免影响其他测试

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
