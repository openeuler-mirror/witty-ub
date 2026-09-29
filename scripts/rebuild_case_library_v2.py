#!/usr/bin/env python3
"""重建案例库：从 data_set（yxh_new + yxh_new_0530）导入所有案例到案例库。

- 使用 reset_case_library.py 中的大类分类
- 新增 5 个类型映射（UB端口/链路的新变体 + Worker缩容挂死）
- 删除 etcd 和无法归类（dfx_ps_n_n）的故障
- 翻译故障类型名为中文
- 关联 data_set KB 中的 log_file_id

用法:
    python3 scripts/rebuild_case_library_v2.py
"""

import os
import json
import uuid
import re
import shutil
import urllib.request
import urllib.error
from datetime import datetime

# ============================================================
# 配置
# ============================================================

CASE_DIR = "/Users/zhaoyujin/Desktop/witty-ub/case"
DATA_SET_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set"
DATA_SET_KB_ID = "fb3749dc-3264-4509-89fb-c34680865271"
API = "http://127.0.0.1:9772"

# ============================================================
# 故障大类映射（在 reset_case_library.py 基础上新增 5 个类型）
# ============================================================

BROAD_CATEGORY = {
    # UB-端口故障
    "dfx_local_ub_single_port_down": "UB-端口故障",
    "dfx_local_ub_all_port_unavailable": "UB-端口故障",
    "dfx_local_ub_all_port_down": "UB-端口故障",              # 新增
    "dfx_local_ub_all_port_lanedown": "UB-端口故障",           # 新增
    "dfx_local_ub_all_port_link_loss": "UB-端口故障",          # 新增
    "dfx_local_ub_two_port_flashdown": "UB-端口故障",
    "dfx_local_ub_single_socket_two_port_down": "UB-端口故障",
    "dfx_local_ub_two_socket_single_port_down": "UB-端口故障",
    "dfx_remote_ub_single_port_down": "UB-端口故障",
    "dfx_remote_ub_two_socket_single_port_down": "UB-端口故障",
    "dfx_remote_ub_single_socket_two_port_down": "UB-端口故障",
    "dfx_remote_ub_all_port_down": "UB-端口故障",

    # UB-链路故障
    "dfx_worker_process_local_ub_link_down": "UB-链路故障",
    "dfx_worker_process_remote_ub_single_link_down": "UB-链路故障",
    "dfx_worker_process_remote_ub_signal_error": "UB-链路故障",
    "dfx_worker_process_remote_ub_nfe": "UB-链路故障",
    "dfx_worker_process_remote_ub_ce": "UB-链路故障",
    "dfx_worker_process_remote_ub_fe": "UB-链路故障",          # 新增
    "dfx_worker_process_remote_local_ub_single_port_down": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_link_loss": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_flash_down": "UB-链路故障",
    "dfx_worker_process_remote_local_ub_lane_down": "UB-链路故障",  # 新增
    "dfx_worker_process_remote_remote_ub_single_port_down": "UB-链路故障",
    "dfx_worker_process_scale_in_remote_ub_nfe": "UB-链路故障",
    "dfx_worker_process_scale_in_remote_ub_link_down": "UB-链路故障",
    "dfx_client_process_get_ub_failure": "UB-链路故障",

    # UB-UBSe/UBM管理进程故障
    "dfx_client_process_get_ubse_failure": "UB-UBSe/UBM管理进程故障",
    "dfx_client_process_get_ubm_failure": "UB-UBSe/UBM管理进程故障",
    "dfx_client_write_remote_after_ubse_fault": "UB-UBSe/UBM管理进程故障",
    "dfx_client_write_remote_after_ubm_fault": "UB-UBSe/UBM管理进程故障",

    # Worker-退出/崩溃
    "dfx_worker_set_exit": "Worker-退出/崩溃",
    "dfx_worker_set_kill": "Worker-退出/崩溃",
    "dfx_worker_process_set_exit": "Worker-退出/崩溃",
    "dfx_worker_process_exit_single_node": "Worker-退出/崩溃",
    "dfx_r_worker_process_set_exit": "Worker-退出/崩溃",

    # Worker-重启
    "dfx_worker_pod_reboot": "Worker-重启",
    "dfx_worker_pod_reboot_l2": "Worker-重启",
    "dfx_worker_reboot_single_node": "Worker-重启",

    # Worker-缩容/挂死
    "dfx_r_discovery_worker_process_hangup": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_client_exit": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_tcp_loss": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_client_hang_up": "Worker-缩容/挂死",
    "dfx_worker_process_scale_in_tcp_down": "Worker-缩容/挂死",
    "dfx_client_process_scale_in_worker_hang_up": "Worker-缩容/挂死",  # 新增

    # Client-退出
    "dfx_client_process_set_exit": "Client-退出",
    "dfx_client_process_set_exit_start": "Client-退出",
    "dfx_client_process_get_exit_start": "Client-退出",

    # Client-挂死/网络
    "dfx_client_process_set_hangs": "Client-挂死/网络",
    "dfx_client_process_get_hangup": "Client-挂死/网络",
    "dfx_client_process_tcp_down": "Client-挂死/网络",
    "dfx_client_scale_in_tcp_down": "Client-挂死/网络",

    # 网络/TCP故障
    "dfx_write_remote_tcp_dalay": "网络/TCP故障",
    "dfx_worker_process_cross_node_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_write_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_net_card_loss": "网络/TCP故障",
}

# ============================================================
# 小类中文翻译
# ============================================================

TYPE_CN = {
    # UB-端口故障
    "dfx_local_ub_single_port_down": "本地UB单端口down",
    "dfx_local_ub_all_port_unavailable": "本地UB全部端口不可用",
    "dfx_local_ub_all_port_down": "本地UB全部端口down",
    "dfx_local_ub_all_port_lanedown": "本地UB全部端口lane down",
    "dfx_local_ub_all_port_link_loss": "本地UB全部端口链路丢失",
    "dfx_local_ub_two_port_flashdown": "本地UB双端口闪断",
    "dfx_local_ub_single_socket_two_port_down": "本地UB单socket双端口down",
    "dfx_local_ub_two_socket_single_port_down": "本地UB双socket单端口down",
    "dfx_remote_ub_single_port_down": "远端UB单端口down",
    "dfx_remote_ub_two_socket_single_port_down": "远端UB双socket单端口down",
    "dfx_remote_ub_single_socket_two_port_down": "远端UB单socket双端口down",
    "dfx_remote_ub_all_port_down": "远端UB全部端口down",

    # UB-链路故障
    "dfx_worker_process_local_ub_link_down": "Worker本地UB链路down",
    "dfx_worker_process_remote_ub_single_link_down": "Worker远端UB单链路down",
    "dfx_worker_process_remote_ub_signal_error": "Worker远端UB信号错误",
    "dfx_worker_process_remote_ub_nfe": "Worker远端UB NFE",
    "dfx_worker_process_remote_ub_ce": "Worker远端UB CE",
    "dfx_worker_process_remote_ub_fe": "Worker远端UB FE",
    "dfx_worker_process_remote_local_ub_single_port_down": "Worker远端本地UB单端口down",
    "dfx_worker_process_remote_local_ub_link_loss": "Worker远端本地UB链路丢失",
    "dfx_worker_process_remote_local_ub_flash_down": "Worker远端本地UB链路闪断",
    "dfx_worker_process_remote_local_ub_lane_down": "Worker远端本地UB lane down",
    "dfx_worker_process_remote_remote_ub_single_port_down": "Worker远端远端UB单端口down",
    "dfx_worker_process_scale_in_remote_ub_nfe": "Worker缩容远端UB NFE",
    "dfx_worker_process_scale_in_remote_ub_link_down": "Worker缩容远端UB链路down",
    "dfx_client_process_get_ub_failure": "Client获取UB失败",

    # UB-UBSe/UBM管理进程故障
    "dfx_client_process_get_ubse_failure": "Client获取UBSe失败",
    "dfx_client_process_get_ubm_failure": "Client获取UBM失败",
    "dfx_client_write_remote_after_ubse_fault": "Client远端写入后UBSe故障",
    "dfx_client_write_remote_after_ubm_fault": "Client远端写入后UBM故障",

    # Worker-退出/崩溃
    "dfx_worker_set_exit": "Worker进程退出",
    "dfx_worker_set_kill": "Worker进程被kill",
    "dfx_worker_process_set_exit": "Worker进程退出",
    "dfx_worker_process_exit_single_node": "Worker单节点进程退出",
    "dfx_r_worker_process_set_exit": "Worker进程退出",

    # Worker-重启
    "dfx_worker_pod_reboot": "Worker Pod重启",
    "dfx_worker_pod_reboot_l2": "Worker Pod重启(L2)",
    "dfx_worker_reboot_single_node": "Worker单节点重启",

    # Worker-缩容/挂死
    "dfx_r_discovery_worker_process_hangup": "Worker发现进程挂死",
    "dfx_worker_process_scale_in_client_exit": "Worker缩容Client退出",
    "dfx_worker_process_scale_in_tcp_loss": "Worker缩容TCP丢包",
    "dfx_worker_process_scale_in_client_hang_up": "Worker缩容Client挂死",
    "dfx_worker_process_scale_in_tcp_down": "Worker缩容TCP down",
    "dfx_client_process_scale_in_worker_hang_up": "Client缩容Worker挂死",

    # Client-退出
    "dfx_client_process_set_exit": "Client进程退出",
    "dfx_client_process_set_exit_start": "Client进程退出启动",
    "dfx_client_process_get_exit_start": "Client获取退出启动",

    # Client-挂死/网络
    "dfx_client_process_set_hangs": "Client进程挂死",
    "dfx_client_process_get_hangup": "Client获取挂死",
    "dfx_client_process_tcp_down": "Client TCP down",
    "dfx_client_scale_in_tcp_down": "Client缩容TCP down",

    # 网络/TCP故障
    "dfx_write_remote_tcp_dalay": "远端写入TCP延迟",
    "dfx_worker_process_cross_node_net_card_loss": "Worker跨节点网卡丢包",
    "dfx_worker_process_write_net_card_loss": "Worker写入网卡丢包",
    "dfx_worker_process_net_card_loss": "Worker网卡丢包",
}

CATEGORY_DESC = {
    "UB-端口故障": "UB端口级别的故障，包括本地和远端端口的down、闪断、不可用等",
    "UB-链路故障": "UB链路级别的故障，包括Worker侧链路down、信号错误、NFE/CE/FE等",
    "UB-UBSe/UBM管理进程故障": "UBSe/UBM管理进程故障，包括获取失败、写入后故障等",
    "Worker-退出/崩溃": "Worker进程退出或崩溃，包括单节点和多节点退出",
    "Worker-重启": "Worker Pod或节点重启",
    "Worker-缩容/挂死": "Worker缩容过程中的进程退出、挂死、网络中断等",
    "Client-退出": "Client进程退出相关故障",
    "Client-挂死/网络": "Client进程挂死或网络故障",
    "网络/TCP故障": "网络和TCP层面的故障，包括网卡丢包、TCP延迟等",
}

RC_PATTERN = re.compile(r"^lingqu_kvcache_(.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$")


def extract_root_cause_type(name: str) -> str:
    m = RC_PATTERN.match(name)
    return m.group(1) if m else name


def fetch_log_file_map(kb_id: str) -> dict:
    """从 API 查询 KB 下所有 log_file，构建 name → log_file_id 映射。"""
    import json as _json
    url = f"{API}/log_file/list/{kb_id}"
    payload = _json.dumps({"page_cnt": 500, "page_num": 1}).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = _json.loads(r.read().decode("utf-8"))
    files = data.get("result", {}).get("log_files", [])
    mapping = {f["name"]: f["id"] for f in files}
    print(f"  从 API 获取 {len(mapping)} 个 log_file 映射")
    return mapping


def main():
    print("=" * 70)
    print("重建案例库：从 data_set 导入（yxh_new + yxh_new_0530）")
    print("=" * 70)

    # 1. 清空 case 目录
    print("\n[1/5] 清空 case 目录...")
    if os.path.isdir(CASE_DIR):
        for fname in os.listdir(CASE_DIR):
            if fname.endswith(".json"):
                os.remove(os.path.join(CASE_DIR, fname))
        print(f"  已清空 case 目录中的所有 JSON 文件")
    else:
        os.makedirs(CASE_DIR, exist_ok=True)

    # 2. 获取 log_file 映射
    print("\n[2/5] 获取 data_set KB 的 log_file 映射...")
    log_file_map = fetch_log_file_map(DATA_SET_KB_ID)

    # 3. 遍历 data_set，收集所有案例信息
    print("\n[3/5] 遍历 data_set 收集案例信息...")
    case_infos = []
    skipped = []
    for sub_dir in ["yxh_new", "yxh_new_0530"]:
        sub_path = os.path.join(DATA_SET_DIR, sub_dir)
        if not os.path.isdir(sub_path):
            continue
        for dir_name in sorted(os.listdir(sub_path)):
            if not os.path.isdir(os.path.join(sub_path, dir_name)):
                continue
            rct_en = extract_root_cause_type(dir_name)
            if rct_en not in BROAD_CATEGORY:
                skipped.append((sub_dir, dir_name, rct_en))
                continue
            broad_cat = BROAD_CATEGORY[rct_en]
            rct_cn = TYPE_CN.get(rct_en, rct_en)
            task_name = f"{sub_dir}/{dir_name}"
            log_file_id = log_file_map.get(dir_name, "")
            case_infos.append({
                "dir_name": dir_name,
                "rct_en": rct_en,
                "rct_cn": rct_cn,
                "broad_cat": broad_cat,
                "task_name": task_name,
                "log_file_id": log_file_id,
            })

    print(f"  有效案例: {len(case_infos)} 个")
    print(f"  跳过（etcd/无法归类）: {len(skipped)} 个")
    if skipped:
        etcd_count = sum(1 for _, _, rct in skipped if "etcd" in rct)
        other_count = len(skipped) - etcd_count
        print(f"    其中 etcd 相关: {etcd_count} 个")
        print(f"    其中其他无法归类: {other_count} 个")
        for sub, dn, rct in skipped:
            print(f"      - {sub}/{dn}  ({rct})")

    # 4. 生成 _categories.json
    print("\n[4/5] 生成分类元数据 _categories.json...")
    categories_set = set()
    types_set = set()
    for ci in case_infos:
        categories_set.add(ci["broad_cat"])
        types_set.add((ci["broad_cat"], ci["rct_cn"], ci["rct_en"]))

    sorted_cats = sorted(categories_set)
    categories_meta = []
    cat_name_to_id = {}
    for idx, cat_name in enumerate(sorted_cats):
        cat_id = str(uuid.uuid4())
        cat_name_to_id[cat_name] = cat_id
        categories_meta.append({
            "id": cat_id,
            "name": cat_name,
            "description": CATEGORY_DESC.get(cat_name, ""),
            "sort_order": idx,
        })

    sorted_types = sorted(types_set, key=lambda x: (x[0], x[1]))
    types_meta = []
    for idx, (broad_cat, type_cn, type_en) in enumerate(sorted_types):
        type_id = str(uuid.uuid4())
        types_meta.append({
            "id": type_id,
            "category_id": cat_name_to_id[broad_cat],
            "name": type_cn,
            "description": f"英文标识: {type_en}",
            "sort_order": idx,
        })

    meta = {"categories": categories_meta, "types": types_meta}
    meta_path = os.path.join(CASE_DIR, "_categories.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  已生成 {len(categories_meta)} 个大类, {len(types_meta)} 个小类")
    for cat in categories_meta:
        type_count = sum(1 for t in types_meta if t["category_id"] == cat["id"])
        print(f"    {cat['name']}: {type_count} 个小类")

    # 5. 通过后端 API 创建案例（后端自动提取 features）
    print(f"\n[5/5] 通过 API 创建案例（后端自动提取 features）...")
    created = 0
    linked = 0
    with_features = 0
    fail = 0
    for i, ci in enumerate(case_infos, 1):
        case_data = {
            "kb_id": DATA_SET_KB_ID if ci["log_file_id"] else "",
            "root_cause_type": ci["rct_cn"],
            "description": f"自动导入: {ci['rct_en']}",
            "task_ids": [],
            "task_names": [ci["task_name"]],
            "log_file_id": ci["log_file_id"],
            "log_file_name": ci["dir_name"],
            "case_category": ci["broad_cat"],
        }
        payload = {"data": json.dumps(case_data)}
        # 使用 multipart/form-data
        boundary = "----RebuildBoundary"
        body_parts = []
        for key, val in payload.items():
            body_parts.append(f"--{boundary}\r\n"
                              f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                              f"{val}\r\n")
        body_parts.append(f"--{boundary}--\r\n")
        body = "\r\n".join(body_parts).encode("utf-8")
        req = urllib.request.Request(
            f"{API}/case_library",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read().decode("utf-8"))
            if resp.get("code") == 200:
                created += 1
                if ci["log_file_id"]:
                    linked += 1
                case_record = resp.get("result", {})
                if case_record.get("features"):
                    with_features += 1
                    fc = case_record["features"].get("fault_category", "?")
                    print(f"  [{i}/{len(case_infos)}] {ci['dir_name'][:50]}  OK  fc={fc}")
                else:
                    print(f"  [{i}/{len(case_infos)}] {ci['dir_name'][:50]}  OK  无features")
            else:
                fail += 1
                print(f"  [{i}/{len(case_infos)}] {ci['dir_name'][:50]}  FAIL  {resp.get('message','')}")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(case_infos)}] {ci['dir_name'][:50]}  FAIL  {e}")

    print(f"\n{'=' * 70}")
    print("重建完成！")
    print(f"{'=' * 70}")
    print(f"  总案例数: {created}")
    print(f"  关联 log_file: {linked}")
    print(f"  含 features: {with_features}")
    print(f"  失败: {fail}")
    print(f"  跳过（etcd/无法归类）: {len(skipped)}")
    print(f"  大类数: {len(categories_meta)}")
    print(f"  小类数: {len(types_meta)}")


if __name__ == "__main__":
    main()
