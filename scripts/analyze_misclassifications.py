#!/usr/bin/env python3
"""分析误判案例的日志内容差异"""
import psycopg2, os

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "witty-ub")
PG_USER = os.getenv("PG_USER", "witty-ub")
PG_PASSWORD = os.getenv("PG_PASSWORD", "YqnUqVgU1u68IlNVV0HgifWp")

TRAIN_KB = 'bea5fe98-9724-4d67-b5d1-4a9c0d7db5f7'

conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
conn.autocommit = True
cur = conn.cursor()

# 同类误判对
same_cat_pairs = [
    ('dfx_client_write_remote_after_ubm_fault', 'dfx_client_write_remote_after_ubse_fault'),
    ('dfx_client_process_set_exit', 'dfx_worker_process_cross_node_net_card_loss'),
    ('dfx_client_process_set_exit_start', 'dfx_remote_ub_two_socket_single_port_down'),
    ('dfx_worker_process_scale_in_remote_ub_link_down', 'dfx_worker_process_scale_in_remote_ub_nfe'),
    ('dfx_worker_process_remote_ub_single_link_down', 'dfx_worker_process_remote_ub_ce'),
    ('dfx_client_process_scale_in_worker_hang_up', 'dfx_client_write_remote_after_ubm_fault'),
    ('dfx_worker_set_exit', 'dfx_ps_n_n'),
    ('dfx_worker_process_local_get_etcd_main_fail', 'dfx_worker_process_cross_node_net_card_loss'),
]

print("=" * 80)
print("同类误判分析")
print("=" * 80)

for gt_type, pred_type in same_cat_pairs:
    print(f"\n{'='*60}")
    print(f"  {gt_type}  vs  {pred_type}")
    print(f"{'='*60}")
    for rct in [gt_type, pred_type]:
        cur.execute(
            "SELECT lf.id FROM log_file lf WHERE lf.kb_id = %s AND lf.name LIKE %s LIMIT 1",
            (TRAIN_KB, f'lingqu_kvcache_{rct}_%')
        )
        row = cur.fetchone()
        if not row:
            print(f"  {rct}: 未找到")
            continue
        log_id = row[0]
        print(f"\n  --- {rct} (log_id={log_id[:8]}...) ---")

        # TFE
        cur.execute(
            "SELECT failure_mode, status_code, operation, pod_names, host_names "
            "FROM trace_failure_event WHERE log_id = %s LIMIT 5",
            (log_id,)
        )
        tfes = cur.fetchall()
        print(f"  TFE({len(tfes)}):")
        for tfe in tfes[:3]:
            print(f"    fm={tfe[0]}, sc={tfe[1]}, op={tfe[2]}")

        # LFE with distinct failure_mode
        cur.execute(
            "SELECT DISTINCT failure_mode, status_code, level, COUNT(*) as cnt "
            "FROM log_failure_event WHERE log_id = %s GROUP BY failure_mode, status_code, level "
            "ORDER BY cnt DESC LIMIT 5",
            (log_id,)
        )
        lfes = cur.fetchall()
        print(f"  LFE distinct(fm,sc,lv):")
        for lfe in lfes:
            print(f"    fm={lfe[0]}, sc={lfe[1]}, lv={lfe[2]}, cnt={lfe[3]}")

        # LFE message samples
        cur.execute(
            "SELECT message, level FROM log_failure_event WHERE log_id = %s LIMIT 3",
            (log_id,)
        )
        msgs = cur.fetchall()
        print(f"  LFE messages:")
        for msg, lv in msgs:
            print(f"    [{lv}] {(msg or '')[:150]}")

        # Anomalous record samples
        cur.execute(
            "SELECT operation, total_latency, c2w_latency, urma_total_latency, "
            "worker_total_latency, is_anomalous "
            "FROM log_parse_result WHERE log_id = %s AND is_anomalous = true "
            "ORDER BY total_latency DESC LIMIT 3",
            (log_id,)
        )
        anoms = cur.fetchall()
        print(f"  Top anomalous records:")
        for a in anoms:
            print(f"    op={a[0]}, total={a[1]:.1f}, c2w={a[2]}, urma={a[3]}, worker={a[4]}")

conn.close()
