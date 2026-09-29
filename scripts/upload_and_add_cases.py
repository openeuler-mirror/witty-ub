#!/usr/bin/env python3
"""上传 test_set + 新类型 case 到 data_set KB，解析后删除失败 case，将可归类的加入案例库。

流程:
  1. 收集 test_set 全部 case + yxh_new/yxh_new_0530 中故障类型不在已有案例库的 case
  2. 上传到 data_set KB 并触发解析
  3. 轮询等待解析完成
  4. 删除解析失败的 case
  5. 将能归类到已有大类的 case 通过 API 加入案例库

用法:
    python3 scripts/upload_and_add_cases.py
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse

# 复用 rebuild_dataset_kb 的 API 工具
sys.path.insert(0, os.path.dirname(__file__))
from rebuild_dataset_kb import (
    api_get, api_post, api_put, api_delete,
    upload_log_file, run_parse, get_log_file, wait_for_parse_complete,
    list_kbs, find_kb_id_by_name,
    DONE_STATUSES, FAILED_STATUSES,
)

# 复用 rebuild_case_library_v2 的映射
from rebuild_case_library_v2 import BROAD_CATEGORY, TYPE_CN, extract_root_cause_type

API_BASE = "http://127.0.0.1:9772"
KB_NAME = "data_set"

TEST_SET_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/test_set/yxh_new_0530"
YXH_NEW_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/yxh_new"
YXH_NEW_0530_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/yxh_new_0530"

# ============================================================
# 新增故障类型映射（已有大类中的新子类型）
# ============================================================

NEW_BROAD_CATEGORY = {
    # UB-端口故障
    "dfx_worker_process_upgrade_ub_local_double_port_down": "UB-端口故障",
    "dfx_worker_process_upgrade_ub_local_reduce_lane": "UB-端口故障",
    "dfx_worker_ub_port_flash_failure": "UB-端口故障",

    # UB-链路故障
    "dfx_worker_process_remote_ub_link_down": "UB-链路故障",
    "dfx_worker_process_upgrade_ub_flapping": "UB-链路故障",
    "dfx_worker_process_upgrade_ub_local_loss": "UB-链路故障",

    # Worker-退出/崩溃
    "dfx_worker_process_exit_l2": "Worker-退出/崩溃",
    "dfx_worker_process_get_exit_start": "Worker-退出/崩溃",

    # Worker-缩容/挂死
    "dfx_worker_process_scale_in_after_ubm": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_after_ubse": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_before_ubm": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_before_ubse": "Worker-缩容/挂死",
    "dfx_worker_process_scale_out_tcp_down": "Worker-缩容/挂死",
    "dfx_worker_process_upgrade_tcp_down": "Worker-缩容/挂死",

    # Client-退出
    "dfx_client_process_set_exit_cross_node": "Client-退出",
    "dfx_client_pod_reboot": "Client-退出",

    # Client-挂死/网络
    "dfx_r_client_process_set_hangup": "Client-挂死/网络",

    # 网络/TCP故障
    "dfx_worker_process_remote_local_tcp_net_card_down": "网络/TCP故障",
    "dfx_worker_process_bandwidth_limit": "网络/TCP故障",
    "dfx_sdk_install_tcp_net_down": "网络/TCP故障",
    "dfx_sdk_install_tcp_net_loss": "网络/TCP故障",
}

NEW_TYPE_CN = {
    # UB-端口故障
    "dfx_worker_process_upgrade_ub_local_double_port_down": "升级UB本地双端口down",
    "dfx_worker_process_upgrade_ub_local_reduce_lane": "升级UB本地减少lane",
    "dfx_worker_ub_port_flash_failure": "Worker UB端口闪断故障",

    # UB-链路故障
    "dfx_worker_process_remote_ub_link_down": "Worker远端UB链路down",
    "dfx_worker_process_upgrade_ub_flapping": "升级UB链路flapping",
    "dfx_worker_process_upgrade_ub_local_loss": "升级UB本地链路丢失",

    # Worker-退出/崩溃
    "dfx_worker_process_exit_l2": "Worker进程退出(L2)",
    "dfx_worker_process_get_exit_start": "Worker获取退出启动",

    # Worker-缩容/挂死
    "dfx_worker_process_scale_in_after_ubm": "Worker缩容后UBM故障",
    "dfx_worker_process_scale_in_after_ubse": "Worker缩容后UBSe故障",
    "dfx_worker_process_scale_in_before_ubm": "Worker缩容前UBM故障",
    "dfx_worker_process_scale_in_before_ubse": "Worker缩容前UBSe故障",
    "dfx_worker_process_scale_out_tcp_down": "Worker缩容TCP down",
    "dfx_worker_process_upgrade_tcp_down": "Worker升级TCP down",

    # Client-退出
    "dfx_client_process_set_exit_cross_node": "Client进程跨节点退出",
    "dfx_client_pod_reboot": "Client Pod重启",

    # Client-挂死/网络
    "dfx_r_client_process_set_hangup": "Client进程挂死(r)",

    # 网络/TCP故障
    "dfx_worker_process_remote_local_tcp_net_card_down": "Worker远端本地TCP网卡down",
    "dfx_worker_process_bandwidth_limit": "Worker带宽限制",
    "dfx_sdk_install_tcp_net_down": "SDK安装TCP网络down",
    "dfx_sdk_install_tcp_net_loss": "SDK安装TCP网络丢包",
}

# 合并已有 + 新增映射
ALL_BROAD = {**BROAD_CATEGORY, **NEW_BROAD_CATEGORY}
ALL_CN = {**TYPE_CN, **NEW_TYPE_CN}

# 需要跳过的故障类型（etcd、dfx_ps_n_n、UBM/UBSe专属、r_client_update等无法归类）
SKIP_PREFIXES = ("dfx_client_init_etcd", "dfx_etcd", "dfx_worker_deploy_etcd",
                 "dfx_worker_init_etcd", "dfx_sdk_install_etcd",
                 "dfx_worker_process_local_get_etcd", "dfx_worker_process_remote_get_etcd",
                 "dfx_client_write_remote_worker_etcd", "dfx_worker_process_scale_in_etcd",
                 "dfx_worker_process_scale_out_etcd", "dfx_worker_process_upgrade_etcd",
                 "dfx_worker_scale_in_etcd", "dfx_client_remote_etcd",
                 "dfx_r_etcd", "dfx_ps_n_n", "dfx_r_client_update",
                 "dfx_r_worker_process_set_UBM", "dfx_r_worker_process_set_UBSE",
                 "dfx_worker_process_upgrade_ubm", "dfx_worker_process_upgrade_ubse")


def is_skippable(rc):
    """判断故障类型是否需要跳过（etcd、无法归类等）"""
    for prefix in SKIP_PREFIXES:
        if rc.startswith(prefix):
            return True
    return False


def collect_folders_to_upload():
    """收集需要上传的文件夹列表: [(source_dir, folder_name), ...]"""
    existing_dfx_types = set(BROAD_CATEGORY.keys())  # 已有案例库的 dfx 类型
    folders = []

    # 1. test_set 全部
    for name in sorted(os.listdir(TEST_SET_DIR)):
        rc = extract_root_cause_type(name)
        if rc:
            folders.append((TEST_SET_DIR, name))

    # 2. yxh_new / yxh_new_0530 中故障类型不在已有案例库的
    for src_dir in [YXH_NEW_DIR, YXH_NEW_0530_DIR]:
        for name in sorted(os.listdir(src_dir)):
            rc = extract_root_cause_type(name)
            if rc and rc not in existing_dfx_types:
                folders.append((src_dir, name))

    return folders


def get_existing_log_file_names(kb_id):
    """获取 KB 中已有的 log_file 名称集合"""
    payload = json.dumps({"page_cnt": 500, "page_num": 1}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/log_file/list/{kb_id}",
        data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    files = data.get("result", {}).get("log_files", [])
    return {f["name"] for f in files}


def delete_log_file(log_file_id):
    """删除单个 log_file"""
    try:
        api_delete(f"/log_file/{log_file_id}")
        return True
    except Exception as e:
        print(f"    删除 log_file {log_file_id} 失败: {e}")
        return False


def create_case_via_api(kb_id, log_file_id, root_cause_type_cn, broad_cat, dir_name, rc_en):
    """通过 API 创建案例（后端自动提取 features）"""
    case_data = {
        "kb_id": kb_id,
        "root_cause_type": root_cause_type_cn,
        "description": f"自动导入: {rc_en}",
        "task_ids": [],
        "task_names": [dir_name],
        "log_file_id": log_file_id,
        "log_file_name": dir_name,
        "case_category": broad_cat,
    }
    payload = {"data": json.dumps(case_data)}
    boundary = "----UploadBoundary"
    body_parts = []
    for key, val in payload.items():
        body_parts.append(f"--{boundary}\r\n"
                          f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                          f"{val}\r\n")
    body_parts.append(f"--{boundary}--\r\n")
    body = "\r\n".join(body_parts).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/case_library",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode("utf-8"))
    return resp


def main():
    print("=" * 70)
    print("上传 test_set + 新类型 case，解析后加入案例库")
    print("=" * 70)

    # Step 0: 获取 data_set KB ID
    kb_id = find_kb_id_by_name(KB_NAME)
    if not kb_id:
        print(f"[ERROR] 知识库 {KB_NAME} 不存在")
        return
    print(f"\n[0] data_set KB ID: {kb_id}")

    # Step 1: 收集需要上传的文件夹
    print(f"\n[1] 收集需要上传的文件夹...")
    folders = collect_folders_to_upload()
    print(f"    总计需要上传: {len(folders)} 个文件夹")

    # 获取已有 log_file 名称，跳过重复
    existing_names = get_existing_log_file_names(kb_id)
    print(f"    KB 中已有 log_file: {len(existing_names)} 个")

    to_upload = [(d, n) for d, n in folders if n not in existing_names]
    already_exists = [(d, n) for d, n in folders if n in existing_names]
    print(f"    需要新上传: {len(to_upload)} 个")
    print(f"    已存在跳过: {len(already_exists)} 个")

    # Step 2: 上传并触发解析
    print(f"\n[2] 上传并触发解析...")
    uploaded = {}  # folder_name -> log_file_id
    for i, (src_dir, name) in enumerate(to_upload, 1):
        src_path = os.path.join(src_dir, name)
        try:
            fid = upload_log_file(kb_id, name, src_path)
            uploaded[name] = fid
            run_parse(fid)
            print(f"  [{i}/{len(to_upload)}] {name[:60]}  OK  fid={fid[:8]}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{i}/{len(to_upload)}] {name[:60]}  FAIL  {e}")

    print(f"\n  上传成功: {len(uploaded)}/{len(to_upload)}")

    # Step 3: 等待解析完成
    if uploaded:
        print(f"\n[3] 等待 {len(uploaded)} 个新上传的解析完成...")
        wait_for_parse_complete(list(uploaded.values()))

    # Step 4: 检查所有上传的 case 解析状态，删除失败的
    print(f"\n[4] 检查解析状态，删除失败的 case...")
    failed_count = 0
    success_log_files = {}  # folder_name -> (log_file_id, parse_status)

    # 检查新上传的
    for name, fid in uploaded.items():
        try:
            data = get_log_file(fid)
            lf = data.get("result", {})
            status = lf.get("parse_status") or lf.get("task_status") or ""
            if status in FAILED_STATUSES or status in ("", "pending"):
                print(f"  [FAIL] {name[:60]}  status={status}  → 删除")
                delete_log_file(fid)
                failed_count += 1
            else:
                success_log_files[name] = (fid, status)
        except Exception as e:
            print(f"  [ERROR] {name[:60]}  {e}")
            failed_count += 1

    # 也检查已存在的（可能之前解析失败的）
    for src_dir, name in already_exists:
        # 已存在的需要通过 API 查找 log_file_id
        pass  # 跳过，已存在的 case 之前已经处理过

    print(f"  删除失败: {failed_count}")
    print(f"  解析成功: {len(success_log_files)}")

    # Step 5: 将可归类的 case 加入案例库
    print(f"\n[5] 将可归类的 case 加入案例库（通过 API，后端自动提取 features）...")
    created = 0
    skipped = 0
    fail = 0

    # 获取所有上传成功的 case（包括新上传和之前已存在的）
    # 先处理新上传成功的
    all_cases = list(success_log_files.items())

    # 也处理已存在的文件夹（需要找到对应的 log_file_id）
    for src_dir, name in already_exists:
        rc = extract_root_cause_type(name)
        if rc and not is_skippable(rc) and rc in ALL_BROAD:
            # 已存在的文件夹需要通过 API 查找 log_file_id
            # 先跳过，后续可以处理
            pass

    for i, (name, (fid, status)) in enumerate(all_cases, 1):
        rc = extract_root_cause_type(name)
        if not rc:
            skipped += 1
            continue
        if is_skippable(rc):
            skipped += 1
            continue
        if rc not in ALL_BROAD:
            skipped += 1
            continue

        broad_cat = ALL_BROAD[rc]
        rc_cn = ALL_CN.get(rc, rc)
        dir_name = name

        try:
            resp = create_case_via_api(kb_id, fid, rc_cn, broad_cat, dir_name, rc)
            if resp.get("code") == 200:
                created += 1
                fc = resp.get("result", {}).get("features", {})
                has_feat = "有" if fc else "无"
                print(f"  [{i}/{len(all_cases)}] {dir_name[:55]}  OK  {broad_cat}/{rc_cn}  features={has_feat}")
            else:
                fail += 1
                print(f"  [{i}/{len(all_cases)}] {dir_name[:55]}  FAIL  {resp.get('message', '')}")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(all_cases)}] {dir_name[:55]}  FAIL  {e}")

    # 汇总
    print(f"\n{'=' * 70}")
    print("完成！")
    print(f"{'=' * 70}")
    print(f"  上传: {len(uploaded)} 个新 case")
    print(f"  解析失败已删除: {failed_count}")
    print(f"  解析成功: {len(success_log_files)}")
    print(f"  加入案例库: {created}")
    print(f"  跳过（不可归类）: {skipped}")
    print(f"  失败: {fail}")


if __name__ == "__main__":
    main()
