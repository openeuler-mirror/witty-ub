#!/usr/bin/env python3
"""从 data_set 重新上传+解析+提取特征+构建案例库。

流程:
  1. 清空 case 目录
  2. 上传 data_set 中所有案例（排除 etcd/其他大类）到后端
  3. 触发解析并轮询等待完成
  4. 对每个已解析的 log_file_id 调用 CaseServiceManager.create_case（自动提取特征）
  5. 生成 _categories.json

用法:
    WITTY_DIR=/Users/zhaoyujin/Desktop/witty-ub \
    src/plugins/latency/.venv/bin/python scripts/rebuild_case_library_from_dataset.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - data_set 目录: /Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set/yxh_new
"""

import os
import sys
import json
import time
import uuid
import re
import shutil
import asyncio
import urllib.request
import urllib.error
from datetime import datetime

# 确保能导入 latency 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.case_service import CaseServiceManager, CASE_DIR  # noqa: E402
from latency.config.config import Config  # noqa: E402
from latency.database.engine import PGManager  # noqa: E402
from latency.database.init import init_postgresql_database  # noqa: E402

# ============================================================
# 配置
# ============================================================

API_BASE = "http://127.0.0.1:9772"
API_TIMEOUT = 300
UPLOAD_DELAY = 0.3
POLL_INTERVAL = 10
POLL_MAX_WAIT = 3600

DATA_SET_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set"
DATA_SUBDIRS = ["yxh_new", "yxh_new_0530"]  # 两个子目录，合计 135 个案例
KB_NAME = "data_set_rebuild"
KB_DESC = "data_set 重建案例库（排除etcd/其他）"

# ============================================================
# 故障大类映射（排除 etcd故障 和 其他）
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

TYPE_CN = {
    "dfx_local_ub_single_port_down": "本地UB单端口down",
    "dfx_local_ub_all_port_unavailable": "本地UB全部端口不可用",
    "dfx_local_ub_two_port_flashdown": "本地UB双端口闪断",
    "dfx_local_ub_single_socket_two_port_down": "本地UB单socket双端口down",
    "dfx_local_ub_two_socket_single_port_down": "本地UB双socket单端口down",
    "dfx_remote_ub_single_port_down": "远端UB单端口down",
    "dfx_remote_ub_two_socket_single_port_down": "远端UB双socket单端口down",
    "dfx_remote_ub_single_socket_two_port_down": "远端UB单socket双端口down",
    "dfx_remote_ub_all_port_down": "远端UB全部端口down",
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
    "dfx_client_process_get_ubse_failure": "Client获取UBSe失败",
    "dfx_client_process_get_ubm_failure": "Client获取UBM失败",
    "dfx_client_write_remote_after_ubse_fault": "Client远端写入后UBSe故障",
    "dfx_client_write_remote_after_ubm_fault": "Client远端写入后UBM故障",
    "dfx_worker_set_exit": "Worker进程退出",
    "dfx_worker_set_kill": "Worker进程被kill",
    "dfx_worker_process_set_exit": "Worker进程退出",
    "dfx_worker_process_exit_single_node": "Worker单节点进程退出",
    "dfx_worker_pod_reboot": "Worker Pod重启",
    "dfx_worker_pod_reboot_l2": "Worker Pod重启(L2)",
    "dfx_worker_reboot_single_node": "Worker单节点重启",
    "dfx_r_worker_process_set_exit": "Worker进程退出",
    "dfx_r_discovery_worker_process_hangup": "Worker发现进程挂死",
    "dfx_worker_process_scale_in_client_exit": "Worker缩容Client退出",
    "dfx_worker_process_scale_in_tcp_loss": "Worker缩容TCP丢包",
    "dfx_worker_process_scale_in_client_hang_up": "Worker缩容Client挂死",
    "dfx_worker_process_scale_in_tcp_down": "Worker缩容TCP down",
    "dfx_client_process_set_exit": "Client进程退出",
    "dfx_client_process_set_exit_start": "Client进程退出启动",
    "dfx_client_process_get_exit_start": "Client获取退出启动",
    "dfx_client_process_set_hangs": "Client进程挂死",
    "dfx_client_process_get_hangup": "Client获取挂死",
    "dfx_client_process_tcp_down": "Client TCP down",
    "dfx_client_scale_in_tcp_down": "Client缩容TCP down",
    "dfx_client_write_remote_worker_etcd_main_fault": "Client远端写入Worker etcd主故障",
    "dfx_write_remote_tcp_dalay": "远端写入TCP延迟",
    "dfx_worker_process_cross_node_net_card_loss": "Worker跨节点网卡丢包",
    "dfx_worker_process_write_net_card_loss": "Worker写入网卡丢包",
    "dfx_worker_process_net_card_loss": "Worker网卡丢包",
}

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


# ============================================================
# API 工具
# ============================================================

def api_get(path, **kwargs):
    url = f"{API_BASE}{path}"
    with urllib.request.urlopen(url, timeout=API_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(path, payload=None, is_json=True):
    url = f"{API_BASE}{path}"
    data = None
    headers = {}
    if payload is not None:
        if is_json:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            data = payload.encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_put(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        import urllib.parse
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    req = urllib.request.Request(url, method="PUT")
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_log_files_in_kb(kb_id, page_cnt=200):
    """列出知识库中所有日志文件，返回 {name: log_file_info} 映射。"""
    result = {}
    page_num = 1
    while True:
        data = api_post(f"/log_file/list/{kb_id}", {
            "page_cnt": page_cnt,
            "page_num": page_num,
        })
        if data.get("code") != 200:
            break
        log_files = data.get("result", {}).get("log_files", [])
        if not log_files:
            break
        for f in log_files:
            result[f.get("name", "")] = f
        if len(log_files) < page_cnt:
            break
        page_num += 1
    return result


def get_or_create_knowledge_base(name, description):
    data = api_post("/log_kb/list", {"page_cnt": 200, "page_num": 1})
    if data.get("code") == 200:
        for kb in data["result"].get("kbs", []):
            if kb["name"] == name:
                print(f"  [SKIP] 知识库已存在: name={name}, kb_id={kb['id']}")
                return kb["id"]
    data = api_post("/log_kb", {"name": name, "description": description})
    if data.get("code") != 200:
        raise RuntimeError(f"创建知识库失败: {data}")
    kb_id = data["result"]["kb_id"]
    print(f"  [OK] 知识库已创建: name={name}, kb_id={kb_id}")
    return kb_id


def upload_log_file(kb_id, subdir_name, subdir_path):
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
    data = api_post(f"/log_file/{kb_id}", payload)
    if data.get("code") != 200:
        raise RuntimeError(f"上传日志文件失败: {data}")
    log_file_ids = data["result"]["log_file_ids"]
    if not log_file_ids:
        raise RuntimeError(f"上传日志文件返回空 ID 列表: {data}")
    return log_file_ids[0]


def run_parse(log_file_id):
    data = api_put(f"/log_file/run/{log_file_id}", params={"run": True})
    if data.get("code") != 200:
        raise RuntimeError(f"触发解析失败: {data}")
    return data["result"].get("task_id", "")


def list_tasks_by_kb(kb_id):
    data = api_post("/task/list", {"kb_id": kb_id, "page_cnt": 200, "page_num": 1})
    if data.get("code") != 200:
        return []
    return data.get("result", {}).get("tasks", [])


def wait_for_parse_complete(kb_id, log_file_ids, max_wait=POLL_MAX_WAIT):
    """轮询等待指定 log_file_id 的解析完成（通过日志文件的 parse_status 判断）。"""
    print(f"\n  等待 {len(log_file_ids)} 个日志文件解析完成...")
    start = time.time()
    target_ids = set(log_file_ids)

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            print(f"  [TIMEOUT] 等待超过 {max_wait}s")
            break

        # 查询知识库中所有日志文件
        all_files = list_log_files_in_kb(kb_id)
        # 只关注目标 log_file_id
        target_files = {fid: all_files.get(name) for fid, name in
                        ((fid, None) for fid in target_ids)}

        # 通过 log_file_id 查询每个文件的状态
        done = 0
        running = 0
        pending = 0
        failed = 0
        for fid in target_ids:
            try:
                data = api_get(f"/log_file/{fid}")
                if data.get("code") != 200:
                    pending += 1
                    continue
                lf = data.get("result", {})
                # 检查 parse_status 或 task_status
                status = lf.get("parse_status") or lf.get("task_status") or ""
                if status in ("successful", "success", "completed", "done"):
                    done += 1
                elif status in ("running", "in_progress"):
                    running += 1
                elif status in ("failed", "error"):
                    failed += 1
                    done += 1  # failed 也算结束
                else:
                    pending += 1
            except Exception:
                pending += 1

        print(f"  [{elapsed:.0f}s] 总数={len(target_ids)} 完成={done} 运行中={running} "
              f"失败={failed} 待处理={pending}")

        if done >= len(target_ids):
            print(f"  [OK] 所有 {done} 个日志文件解析已完成")
            break

        if not running and pending == 0 and done >= len(target_ids):
            print(f"  [OK] 所有日志文件解析已完成")
            break

        time.sleep(POLL_INTERVAL)


def generate_categories_json(case_infos):
    """生成 _categories.json"""
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
    return len(categories_meta), len(types_meta)


async def main():
    print("=" * 70)
    print("从 data_set 重新上传+解析+提取特征+构建案例库")
    print(f"WITTY_DIR={os.getenv('WITTY_DIR', '(未设置)')}")
    print(f"CASE_DIR={CASE_DIR}")
    print("=" * 70)

    # 初始化数据库连接
    print("\n[Step 0] 初始化数据库连接...")
    config = Config().get_config()
    PGManager.initialize(
        config.db.pg_dsn_url(),
        pool_size=config.db.pg_pool_size,
        max_overflow=config.db.pg_max_overflow,
    )
    await PGManager.init_timezone()
    await init_postgresql_database()
    print("  数据库初始化完成")

    # 健康检查
    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # Step 1: 清空 case 目录
    print("\n[Step 1] 清空 case 目录...")
    if os.path.isdir(CASE_DIR):
        for fname in os.listdir(CASE_DIR):
            if fname.endswith(".json"):
                os.remove(os.path.join(CASE_DIR, fname))
        print(f"  已清空 case 目录中的所有 JSON 文件")
    else:
        os.makedirs(CASE_DIR, exist_ok=True)
        print(f"  已创建 case 目录")

    # Step 2: 收集 data_set 中需要上传的案例（排除 etcd/其他）
    print("\n[Step 2] 收集 data_set 案例信息（排除 etcd/其他）...")
    case_infos = []
    skipped = []
    seen_dir_names = set()  # 去重（两个子目录可能有同名）

    for sub in DATA_SUBDIRS:
        sub_dir = os.path.join(DATA_SET_DIR, sub)
        if not os.path.isdir(sub_dir):
            print(f"  [WARN] 子目录不存在: {sub_dir}")
            continue
        ds_cases = sorted([
            d for d in os.listdir(sub_dir)
            if os.path.isdir(os.path.join(sub_dir, d))
        ])
        print(f"  子目录 {sub}/: {len(ds_cases)} 个案例目录")

        for dir_name in ds_cases:
            if dir_name in seen_dir_names:
                print(f"    [SKIP] 重复案例名: {dir_name}")
                continue
            seen_dir_names.add(dir_name)
            rct_en = extract_root_cause_type(dir_name)
            if rct_en not in BROAD_CATEGORY:
                skipped.append((dir_name, rct_en, sub))
                continue
            broad_cat = BROAD_CATEGORY[rct_en]
            rct_cn = TYPE_CN.get(rct_en, rct_en)
            case_infos.append({
                "dir_name": dir_name,
                "rct_en": rct_en,
                "rct_cn": rct_cn,
                "broad_cat": broad_cat,
                "subdir_path": os.path.join(sub_dir, dir_name),
                "source_sub": sub,
            })

    total_scanned = len(seen_dir_names)
    print(f"  两个子目录共扫描 {total_scanned} 个案例目录（去重后）")
    if skipped:
        print(f"  跳过 {len(skipped)} 个案例（etcd/其他）:")
        for dn, rct, sub in skipped:
            print(f"    - {sub}/{dn}  ({rct})")
    print(f"  待上传 {len(case_infos)} 个案例")

    # Step 3: 创建知识库
    print("\n[Step 3] 创建知识库...")
    kb_id = get_or_create_knowledge_base(KB_NAME, KB_DESC)

    # Step 4: 上传并触发解析（复用已上传的文件）
    print("\n[Step 4] 上传日志文件并触发解析（复用已上传文件）...")
    print("  查询知识库中已有的日志文件...")
    existing_files = list_log_files_in_kb(kb_id)
    print(f"  知识库中已有 {len(existing_files)} 个日志文件")

    uploaded = {}  # log_file_id → case_info
    success_count = 0
    fail_count = 0
    reused_count = 0

    for idx, ci in enumerate(case_infos, 1):
        print(f"\n  [{idx}/{len(case_infos)}] {ci['dir_name']}")
        try:
            # 检查是否已上传过
            if ci["dir_name"] in existing_files:
                existing = existing_files[ci["dir_name"]]
                log_file_id = existing["id"]
                task_id = existing.get("task_id", "")
                # 如果已有任务但状态是 pending/failed，重新触发解析
                parse_status = existing.get("parse_status", "")
                if parse_status in ("", "pending", "failed"):
                    try:
                        task_id = run_parse(log_file_id)
                    except Exception:
                        pass
                uploaded[log_file_id] = {**ci, "task_id": task_id, "kb_id": kb_id}
                success_count += 1
                reused_count += 1
                print(f"    [REUSE] log_file_id={log_file_id}, task_id={task_id}, parse_status={parse_status}")
            else:
                log_file_id = upload_log_file(kb_id, ci["dir_name"], ci["subdir_path"])
                task_id = run_parse(log_file_id)
                uploaded[log_file_id] = {**ci, "task_id": task_id, "kb_id": kb_id}
                success_count += 1
                print(f"    [NEW] log_file_id={log_file_id}, task_id={task_id}")
        except Exception as e:
            fail_count += 1
            print(f"    [ERROR] {e}")
            continue

        if idx < len(case_infos):
            time.sleep(UPLOAD_DELAY)

    print(f"\n  上传完成: 成功 {success_count} (复用 {reused_count}, 新增 {success_count - reused_count}), 失败 {fail_count}")

    if success_count == 0:
        print("[ERROR] 没有成功上传的案例，退出")
        sys.exit(1)

    # Step 5: 等待解析完成
    print("\n[Step 5] 等待解析完成...")
    wait_for_parse_complete(kb_id, list(uploaded.keys()))

    # Step 6: 通过 CaseServiceManager.create_case 创建案例（自动提取特征）
    print("\n[Step 6] 创建案例并提取特征...")
    created_count = 0
    with_features = 0
    without_features = 0

    for idx, (log_file_id, ci) in enumerate(uploaded.items(), 1):
        print(f"\n  [{idx}/{len(uploaded)}] {ci['dir_name']}")
        try:
            case_record = await CaseServiceManager.create_case(
                kb_id=kb_id,
                root_cause_type=ci["rct_cn"],
                description=f"自动导入: {ci['rct_en']}",
                task_ids=[ci.get("task_id", "")],
                task_names=[f"{ci.get('source_sub', 'yxh_new')}/{ci['dir_name']}"],
                log_file_id=log_file_id,
                log_file_name=ci["dir_name"],
                attachment_path=None,
                case_category=ci["broad_cat"],
            )
            created_count += 1
            if case_record.get("features"):
                with_features += 1
                print(f"    [OK] case_id={case_record['id'][:8]} 特征提取成功")
            else:
                without_features += 1
                print(f"    [WARN] case_id={case_record['id'][:8]} 无特征")
        except Exception as e:
            print(f"    [ERROR] {e}")
            without_features += 1

    # Step 7: 生成 _categories.json
    print("\n[Step 7] 生成 _categories.json...")
    cat_count, type_count = generate_categories_json(case_infos)
    print(f"  已生成 {cat_count} 个大类, {type_count} 个小类")

    # 验证
    final_files = [f for f in os.listdir(CASE_DIR) if f.endswith(".json")]
    case_files = [f for f in final_files if f != "_categories.json"]

    print(f"\n{'=' * 70}")
    print("构建完成！")
    print(f"{'=' * 70}")
    print(f"  上传成功: {success_count}")
    print(f"  案例创建: {created_count}")
    print(f"  有特征: {with_features}")
    print(f"  无特征: {without_features}")
    print(f"  大类数: {cat_count}")
    print(f"  小类数: {type_count}")
    print(f"  知识库 ID: {kb_id}")
    print(f"  case 目录文件数: {len(final_files)}（含 _categories.json）")

    # 大类分布
    print(f"\n  大类分布:")
    cat_dist = {}
    for ci in case_infos:
        cat_dist[ci["broad_cat"]] = cat_dist.get(ci["broad_cat"], 0) + 1
    for cat in sorted(cat_dist.keys()):
        print(f"    {cat}: {cat_dist[cat]}")

    # 保存 log_file_id 映射
    log_file_map_path = os.path.join(CASE_DIR, "_log_file_map.json")
    serializable_map = {}
    for log_file_id, ci in uploaded.items():
        serializable_map[log_file_id] = {
            "dir_name": ci["dir_name"],
            "rct_en": ci["rct_en"],
            "rct_cn": ci["rct_cn"],
            "broad_cat": ci["broad_cat"],
            "task_id": ci.get("task_id", ""),
            "kb_id": ci.get("kb_id", ""),
        }
    with open(log_file_map_path, "w", encoding="utf-8") as f:
        json.dump(serializable_map, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
