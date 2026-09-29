#!/usr/bin/env python3
"""批量计算 test_set 的相似案例匹配命中率。

对 test_set 中每个已上传的日志文件调用相似案例分析 API，计算 Top-1/3/5 大类命中率。

用法:
    python scripts/calculate_test_set_hitrate.py

前提:
    - test_set 日志已上传且解析完成
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
"""

import os
import sys
import json
import re
import time
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:9772"
API_TIMEOUT = 120
UPLOAD_RESULTS_PATH = "/Users/zhaoyujin/Desktop/witty-ub/scripts/test_set_upload_results.json"

# 大类映射（与 reset_case_library.py 一致）
BROAD_CATEGORY = {
    "dfx_local_ub_single_port_down": "UB-端口故障",
    "dfx_local_ub_all_port_unavailable": "UB-端口故障",
    "dfx_local_ub_two_port_flashdown": "UB-端口故障",
    "dfx_local_ub_single_socket_two_port_down": "UB-端口故障",
    "dfx_local_ub_two_socket_single_port_down": "UB-端口故障",
    "dfx_remote_ub_single_port_down": "UB-端口故障",
    "dfx_remote_ub_two_socket_single_port_down": "UB-端口故障",
    "dfx_remote_ub_single_socket_two_port_down": "UB-端口故障",
    "dfx_remote_ub_all_port_down": "UB-端口故障",
    "dfx_worker_process_local_ub_link_down": "UB-链路故障",
    "dfx_worker_process_remote_ub_single_link_down": "UB-链路故障",
    "dfx_worker_process_remote_ub_signal_error": "UB-链路故障",
    "dfx_worker_process_remote_ub_nfe": "UB-链路故障",
    "dfx_worker_process_remote_ub_ce": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_single_port_down": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_link_loss": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_flash_down": "UB-链路故障",
    "dfx_worker_process_remote_remote_ub_single_port_down": "UB-链路故障",
    "dfx_worker_process_scale_in_remote_ub_nfe": "UB-链路故障",
    "dfx_worker_process_scale_in_remote_ub_link_down": "UB-链路故障",
    "dfx_client_process_get_ub_failure": "UB-链路故障",
    "dfx_client_process_get_ubse_failure": "UB-UBSe/UBM管理进程故障",
    "dfx_client_process_get_ubm_failure": "UB-UBSe/UBM管理进程故障",
    "dfx_client_write_remote_after_ubse_fault": "UB-UBSe/UBM管理进程故障",
    "dfx_client_write_remote_after_ubm_fault": "UB-UBSe/UBM管理进程故障",
    "dfx_worker_set_exit": "Worker-退出/崩溃",
    "dfx_worker_set_kill": "Worker-退出/崩溃",
    "dfx_worker_process_set_exit": "Worker-退出/崩溃",
    "dfx_worker_process_exit_single_node": "Worker-退出/崩溃",
    "dfx_worker_pod_reboot": "Worker-重启",
    "dfx_worker_pod_reboot_l2": "Worker-重启",
    "dfx_worker_reboot_single_node": "Worker-重启",
    "dfx_r_worker_process_set_exit": "Worker-缩容/挂死",
    "dfx_r_discovery_worker_process_hangup": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_client_exit": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_tcp_loss": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_client_hang_up": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_tcp_down": "Worker-缩容/挂死",
    "dfx_client_process_set_exit": "Client-退出",
    "dfx_client_process_set_exit_start": "Client-退出",
    "dfx_client_process_get_exit_start": "Client-退出",
    "dfx_client_process_set_hangs": "Client-挂死/网络",
    "dfx_client_process_get_hangup": "Client-挂死/网络",
    "dfx_client_process_tcp_down": "Client-挂死/网络",
    "dfx_client_scale_in_tcp_down": "Client-挂死/网络",
    "dfx_client_write_remote_worker_etcd_main_fault": "Client-挂死/网络",
    "dfx_client_init_etcd_cluster_fail": "etcd故障",
    "dfx_etcd_cluster_exit": "etcd故障",
    "dfx_etcd_cluster_exit_before_set": "etcd故障",
    "dfx_sdk_install_etcd_down": "etcd故障",
    "dfx_sdk_install_etcd_unavailable": "etcd故障",
    "dfx_worker_process_local_get_etcd_main_fail": "etcd故障",
    "dfx_worker_process_remote_get_etcd_main_fail": "etcd故障",
    "dfx_worker_deploy_etcd_cluster_fail": "etcd故障",
    "dfx_worker_process_upgrade_etcd_fault": "etcd故障",
    "dfx_r_etcd_fail_client_update": "etcd故障",
    "dfx_write_remote_tcp_dalay": "网络/TCP故障",
    "dfx_worker_process_cross_node_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_write_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_net_card_loss": "网络/TCP故障",
    "dfx_ps_n_n": "其他",
    "11111": "其他",
}

RC_PATTERN = re.compile(r"^lingqu_kvcache_(.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$")


def extract_root_cause_type(name: str) -> str:
    m = RC_PATTERN.match(name)
    return m.group(1) if m else name


def api_post(path, payload):
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 70)
    print("批量计算 test_set 相似案例匹配命中率")
    print("=" * 70)

    # 加载上传结果
    if not os.path.exists(UPLOAD_RESULTS_PATH):
        print(f"[ERROR] 上传结果文件不存在: {UPLOAD_RESULTS_PATH}")
        sys.exit(1)

    with open(UPLOAD_RESULTS_PATH, "r", encoding="utf-8") as f:
        upload_results = json.load(f)

    print(f"已加载 {len(upload_results)} 个上传结果")

    # 健康检查
    try:
        url = f"{API_BASE}/health_check"
        with urllib.request.urlopen(url, timeout=10) as resp:
            print(f"API 健康检查: {json.loads(resp.read().decode('utf-8')).get('status', 'unknown')}")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # 逐个调用相似案例分析 API
    results = []
    total = len(upload_results)
    hit1 = 0
    hit3 = 0
    hit5 = 0
    errors = 0

    for idx, (log_name, info) in enumerate(sorted(upload_results.items()), 1):
        log_file_id = info["log_file_id"]
        rct_en = extract_root_cause_type(log_name)
        gt_cat = BROAD_CATEGORY.get(rct_en, "其他")

        print(f"\n  [{idx}/{total}] {log_name}")
        print(f"    GT: {rct_en} → {gt_cat}")

        try:
            resp = api_post("/similarity_analysis", {
                "log_file_id": log_file_id,
                "top_k": 50,
            })
            if resp.get("code") != 200:
                print(f"    [ERROR] API返回错误: {resp.get('message', '')}")
                errors += 1
                results.append({
                    "log_name": log_name,
                    "rct_en": rct_en,
                    "gt_cat": gt_cat,
                    "error": resp.get("message", "API错误"),
                })
                continue

            top_matches = resp.get("result", {}).get("top_matches", [])

            # 提取去重后的大类列表（按相似度排序）
            seen_cats = []
            for m in top_matches:
                cat = m.get("case_category", "")
                if cat and cat not in seen_cats:
                    seen_cats.append(cat)
                if len(seen_cats) >= 5:
                    break

            top1_hit = gt_cat in seen_cats[:1]
            top3_hit = gt_cat in seen_cats[:3]
            top5_hit = gt_cat in seen_cats[:5]

            if top1_hit: hit1 += 1
            if top3_hit: hit3 += 1
            if top5_hit: hit5 += 1

            predicted_cats = " > ".join(seen_cats[:5])
            print(f"    预测Top5大类: {predicted_cats}")
            print(f"    命中: Top1={top1_hit} Top3={top3_hit} Top5={top5_hit}")

            # 取第一个子类型
            best_type = top_matches[0]["root_cause_type"] if top_matches else ""
            best_cat = top_matches[0].get("case_category", "") if top_matches else ""
            best_sim = top_matches[0]["similarity"] if top_matches else 0

            results.append({
                "log_name": log_name,
                "rct_en": rct_en,
                "gt_cat": gt_cat,
                "predicted_top1_cat": best_cat,
                "predicted_top5_cats": seen_cats[:5],
                "top1_hit": top1_hit,
                "top3_hit": top3_hit,
                "top5_hit": top5_hit,
                "best_type": best_type,
                "best_sim": best_sim,
                "top5_types": [m["root_cause_type"] for m in top_matches[:5]],
            })

        except Exception as e:
            print(f"    [ERROR] {e}")
            errors += 1
            results.append({
                "log_name": log_name,
                "rct_en": rct_en,
                "gt_cat": gt_cat,
                "error": str(e),
            })

        time.sleep(0.3)

    # 汇总
    valid = total - errors
    print(f"\n{'=' * 70}")
    print("命中率汇总")
    print(f"{'=' * 70}")
    print(f"  总案例数: {total}")
    print(f"  有效案例: {valid}")
    print(f"  错误案例: {errors}")
    if valid > 0:
        print(f"  Top-1 命中率: {hit1}/{valid} = {hit1/valid*100:.1f}%")
        print(f"  Top-3 命中率: {hit3}/{valid} = {hit3/valid*100:.1f}%")
        print(f"  Top-5 命中率: {hit5}/{valid} = {hit5/valid*100:.1f}%")

    # 按大类分组统计
    print(f"\n按大类分组命中率:")
    cat_stats = {}
    for r in results:
        if "error" in r:
            continue
        gt = r["gt_cat"]
        if gt not in cat_stats:
            cat_stats[gt] = {"total": 0, "hit1": 0, "hit3": 0, "hit5": 0}
        cat_stats[gt]["total"] += 1
        if r["top1_hit"]: cat_stats[gt]["hit1"] += 1
        if r["top3_hit"]: cat_stats[gt]["hit3"] += 1
        if r["top5_hit"]: cat_stats[gt]["hit5"] += 1

    print(f"  {'大类':<25s} {'总数':>4s} {'Top1':>6s} {'Top3':>6s} {'Top5':>6s}")
    print(f"  {'-'*55}")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        t1 = f"{s['hit1']}/{s['total']}"
        t3 = f"{s['hit3']}/{s['total']}"
        t5 = f"{s['hit5']}/{s['total']}"
        print(f"  {cat:<25s} {s['total']:>4d} {t1:>6s} {t3:>6s} {t5:>6s}")

    # 未命中的案例
    missed = [r for r in results if "error" not in r and not r["top5_hit"]]
    if missed:
        print(f"\nTop-5 未命中案例 ({len(missed)} 个):")
        for r in missed:
            print(f"  {r['rct_en']} (GT: {r['gt_cat']}) → 预测: {' > '.join(r['predicted_top5_cats'])}")

    # 保存结果
    output_path = "/Users/zhaoyujin/Desktop/witty-ub/scripts/test_set_hitrate_results.json"
    output = {
        "total": total,
        "valid": valid,
        "errors": errors,
        "top1_hit": hit1,
        "top3_hit": hit3,
        "top5_hit": hit5,
        "top1_rate": hit1 / valid if valid > 0 else 0,
        "top3_rate": hit3 / valid if valid > 0 else 0,
        "top5_rate": hit5 / valid if valid > 0 else 0,
        "cat_stats": cat_stats,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
