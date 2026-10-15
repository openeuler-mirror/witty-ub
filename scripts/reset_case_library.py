#!/usr/bin/env python3
"""重置案例库：清空所有数据，从 data_set 重新导入，使用大类+中文小类两级分类。

用法:
    python scripts/reset_case_library.py

前提:
    - data_set 目录: /Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set/yxh_new
    - 现有案例目录: /Users/zhaoyujin/Desktop/witty-ub/case（会被清空重建）
"""

import os
import json
import uuid
import re
import shutil
from datetime import datetime

# ============================================================
# 配置
# ============================================================

CASE_DIR = "/Users/zhaoyujin/Desktop/witty-ub/case"
DATA_SET_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set/yxh_new"
BACKUP_DIR = "/Users/zhaoyujin/Desktop/witty-ub/case_backup"

# ============================================================
# 故障大类映射（与 run_new_case_match.py 一致）
# ============================================================

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

    "dfx_r_worker_process_set_exit": "Worker-退出/崩溃",
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

    "dfx_write_remote_tcp_dalay": "网络/TCP故障",
    "dfx_worker_process_cross_node_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_write_net_card_loss": "网络/TCP故障",
    "dfx_worker_process_net_card_loss": "网络/TCP故障",
}

# ============================================================
# 小类中文翻译（去掉 dfx_ 前缀，翻译剩余部分）
# ============================================================

TYPE_CN = {
    # UB-端口故障
    "dfx_local_ub_single_port_down": "本地UB单端口down",
    "dfx_local_ub_all_port_unavailable": "本地UB全部端口不可用",
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
    "dfx_worker_process_remote_local_ub_single_port_down": "Worker远端本地UB单端口down",
    "dfx_worker_process_remote_local_ub_link_loss": "Worker远端本地UB链路丢失",
    "dfx_worker_process_remote_local_ub_flash_down": "Worker远端本地UB链路闪断",
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

    # Worker-重启
    "dfx_worker_pod_reboot": "Worker Pod重启",
    "dfx_worker_pod_reboot_l2": "Worker Pod重启(L2)",
    "dfx_worker_reboot_single_node": "Worker单节点重启",

    # Worker-缩容/挂死
    "dfx_r_worker_process_set_exit": "Worker进程退出",
    "dfx_r_discovery_worker_process_hangup": "Worker发现进程挂死",
    "dfx_worker_process_scale_in_client_exit": "Worker缩容Client退出",
    "dfx_worker_process_scale_in_tcp_loss": "Worker缩容TCP丢包",
    "dfx_worker_process_scale_in_client_hang_up": "Worker缩容Client挂死",
    "dfx_worker_process_scale_in_tcp_down": "Worker缩容TCP down",

    # Client-退出
    "dfx_client_process_set_exit": "Client进程退出",
    "dfx_client_process_set_exit_start": "Client进程退出启动",
    "dfx_client_process_get_exit_start": "Client获取退出启动",

    # Client-挂死/网络
    "dfx_client_process_set_hangs": "Client进程挂死",
    "dfx_client_process_get_hangup": "Client获取挂死",
    "dfx_client_process_tcp_down": "Client TCP down",
    "dfx_client_scale_in_tcp_down": "Client缩容TCP down",
    "dfx_client_write_remote_worker_etcd_main_fault": "Client远端写入Worker etcd主故障",

    # 网络/TCP故障
    "dfx_write_remote_tcp_dalay": "远端写入TCP延迟",
    "dfx_worker_process_cross_node_net_card_loss": "Worker跨节点网卡丢包",
    "dfx_worker_process_write_net_card_loss": "Worker写入网卡丢包",
    "dfx_worker_process_net_card_loss": "Worker网卡丢包",
}

# 大类描述
CATEGORY_DESC = {
    "UB-端口故障": "UB端口级别的故障，包括本地和远端端口的down、闪断、不可用等",
    "UB-链路故障": "UB链路级别的故障，包括Worker侧链路down、信号错误、NFE/CE等",
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


def main():
    print("=" * 70)
    print("重置案例库：清空 + 从 data_set 重新导入")
    print("=" * 70)

    # 1. 读取现有案例到内存（建立 task_names → 案例数据映射）
    print("\n[1/5] 读取现有案例数据...")
    existing_cases = {}  # task_name → case_data
    if os.path.isdir(CASE_DIR):
        for fname in os.listdir(CASE_DIR):
            if not fname.endswith(".json") or fname.startswith("_"):
                continue
            fpath = os.path.join(CASE_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                for tn in d.get("task_names", []):
                    existing_cases[tn] = d
            except (json.JSONDecodeError, OSError):
                continue
    print(f"  读取到 {len(existing_cases)} 个现有案例的 task_names 映射")

    # 2. 备份并清空 case 目录
    print("\n[2/5] 备份并清空 case 目录...")
    if os.path.isdir(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR)
    if os.path.isdir(CASE_DIR):
        shutil.copytree(CASE_DIR, BACKUP_DIR)
        print(f"  已备份到: {BACKUP_DIR}")
        # 删除所有 .json 文件
        for fname in os.listdir(CASE_DIR):
            if fname.endswith(".json"):
                os.remove(os.path.join(CASE_DIR, fname))
        print(f"  已清空 case 目录中的所有 JSON 文件")
    else:
        os.makedirs(CASE_DIR, exist_ok=True)

    # 3. 遍历 data_set，收集所有案例信息
    print("\n[3/5] 遍历 data_set 收集案例信息...")
    ds_cases = sorted([
        d for d in os.listdir(DATA_SET_DIR)
        if os.path.isdir(os.path.join(DATA_SET_DIR, d))
    ])
    print(f"  data_set 中有 {len(ds_cases)} 个案例目录")

    # 收集所有需要创建的大类和小类
    categories_set = set()  # (大类名)
    types_set = set()  # (大类名, 小类中文名, 英文名)
    case_infos = []  # [{ dir_name, rct_en, rct_cn, broad_cat, task_name }]

    skipped = []
    for dir_name in ds_cases:
        rct_en = extract_root_cause_type(dir_name)
        # 跳过未在 BROAD_CATEGORY 中映射的类型（etcd、其他等已删除的大类）
        if rct_en not in BROAD_CATEGORY:
            skipped.append((dir_name, rct_en))
            continue
        broad_cat = BROAD_CATEGORY[rct_en]
        rct_cn = TYPE_CN.get(rct_en, rct_en)
        task_name = f"yxh_new/{dir_name}"
        categories_set.add(broad_cat)
        types_set.add((broad_cat, rct_cn, rct_en))
        case_infos.append({
            "dir_name": dir_name,
            "rct_en": rct_en,
            "rct_cn": rct_cn,
            "broad_cat": broad_cat,
            "task_name": task_name,
        })

    # 4. 生成 _categories.json
    print("\n[4/5] 生成分类元数据 _categories.json...")
    if skipped:
        print(f"  跳过 {len(skipped)} 个案例（未在 BROAD_CATEGORY 中映射，etcd/其他等）:")
        for dn, rct in skipped:
            print(f"    - {dn}  ({rct})")
    # 按大类名称排序
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

    # 按大类排序，同一大类内按小类名排序
    sorted_types = sorted(types_set, key=lambda x: (x[0], x[1]))
    types_meta = []
    type_cn_to_id = {}
    for idx, (broad_cat, type_cn, type_en) in enumerate(sorted_types):
        type_id = str(uuid.uuid4())
        type_cn_to_id[type_cn] = type_id
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

    # 5. 创建案例 JSON
    print(f"\n[5/5] 创建案例 JSON...")
    created = 0
    with_features = 0
    without_features = 0
    skipped_rct = set()  # 没有翻译的英文类型

    for ci in case_infos:
        case_id = str(uuid.uuid4())
        rct_cn = ci["rct_cn"]
        broad_cat = ci["broad_cat"]
        task_name = ci["task_name"]

        # 查找现有案例的 features
        old_case = existing_cases.get(task_name)
        if old_case and old_case.get("features"):
            features = old_case["features"]
            fault_category = old_case.get("fault_category")
            log_file_id = old_case.get("log_file_id", "")
            kb_id = old_case.get("kb_id", "")
            with_features += 1
        else:
            features = None
            fault_category = None
            log_file_id = ""
            kb_id = ""
            without_features += 1
            if ci["rct_en"] not in TYPE_CN:
                skipped_rct.add(ci["rct_en"])

        case_record = {
            "id": case_id,
            "kb_id": kb_id,
            "root_cause_type": rct_cn,
            "description": f"自动导入: {ci['rct_en']}",
            "task_ids": [],
            "task_names": [task_name],
            "log_file_id": log_file_id,
            "log_file_name": ci["dir_name"],
            "attachment_path": None,
            "fault_category": fault_category,
            "case_category": broad_cat,
            "features": features,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        json_path = os.path.join(CASE_DIR, f"{case_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(case_record, f, ensure_ascii=False, indent=2)
        created += 1

    print(f"\n{'=' * 70}")
    print("重置完成！")
    print(f"{'=' * 70}")
    print(f"  总案例数: {created}")
    print(f"  有特征: {with_features}")
    print(f"  无特征: {without_features}")
    if without_features > 0:
        print(f"  无特征案例（可能需要通过后端重新提取）:")
        for ci in case_infos:
            task_name = ci["task_name"]
            if task_name not in existing_cases or not existing_cases[task_name].get("features"):
                print(f"    - {ci['dir_name']}")

    # 验证
    print(f"\n验证:")
    final_files = [f for f in os.listdir(CASE_DIR) if f.endswith(".json")]
    print(f"  case 目录中 JSON 文件数: {len(final_files)}")
    print(f"  其中 _categories.json: 1")
    print(f"  案例文件: {len(final_files) - 1}")
    print(f"  备份位置: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
