#!/usr/bin/env python3
"""重建资产库：删除 data_set_rebuild 知识库，新建 data_set 知识库并上传所有 lingqu_xxx 文件夹。

流程:
  1. 删除 data_set_rebuild 知识库（整体删除，级联清理 log_file/任务/解析产物）
  2. 若 data_set 知识库已存在，先删除，再新建
  3. 上传 data_set 下所有 lingqu_xxx 文件夹（yxh_new + yxh_new_0530，共 135 个）
  4. 触发解析并轮询等待全部完成

用法:
    python scripts/rebuild_dataset_kb.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - data_set 目录: /Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set
    - 每个 lingqu_xxx 文件夹作为一个任务（log_file）上传
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse

# ============================================================
# 配置
# ============================================================

API_BASE = "http://127.0.0.1:9772"
API_TIMEOUT = 300
DELETE_KB_TIMEOUT = 1800  # 删除知识库级联清理耗时较长，单独设置 30 分钟
UPLOAD_DELAY = 0.3
POLL_INTERVAL = 10
POLL_MAX_WAIT = 7200

DATA_SET_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/data_set"
DATA_SUBDIRS = ["yxh_new", "yxh_new_0530"]

KB_NAME_DELETE = "data_set_rebuild"
KB_NAME_NEW = "data_set"
KB_DESC = "data_set 资产库（lingqu_xxx 文件夹，每个文件夹一个任务）"

DONE_STATUSES = ("successful", "success", "completed", "done")
RUNNING_STATUSES = ("running", "in_progress")
FAILED_STATUSES = ("failed", "error")


# ============================================================
# API 工具
# ============================================================

def _request(method, url, data=None, headers=None, timeout=API_TIMEOUT):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def api_get(path):
    return _request("GET", f"{API_BASE}{path}")


def api_post(path, payload=None, is_json=True):
    data = None
    headers = {}
    if payload is not None:
        if is_json:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            data = payload.encode("utf-8")
    return _request("POST", f"{API_BASE}{path}", data=data, headers=headers)


def api_put(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return _request("PUT", url)


def api_delete(path, timeout=DELETE_KB_TIMEOUT):
    return _request("DELETE", f"{API_BASE}{path}", timeout=timeout)


# ============================================================
# 知识库操作
# ============================================================

def list_kbs(page_cnt=200):
    data = api_post("/log_kb/list", {"page_cnt": page_cnt, "page_num": 1})
    if data.get("code") != 200:
        return []
    return data.get("result", {}).get("kbs", [])


def find_kb_id_by_name(name):
    for kb in list_kbs():
        if kb.get("name") == name:
            return kb["id"]
    return None


def delete_kb(kb_id):
    print(f"    正在删除知识库 kb_id={kb_id}（级联清理 log_file/任务/解析产物，可能需要数分钟）...")
    data = api_delete(f"/log_kb/{kb_id}")
    return data.get("code") == 200


def delete_kb_by_name(name):
    """按名称查找并整体删除知识库，返回是否删除成功（不存在也算成功）。"""
    kb_id = find_kb_id_by_name(name)
    if not kb_id:
        print(f"    [SKIP] 知识库不存在: {name}")
        return True
    ok = delete_kb(kb_id)
    if ok:
        print(f"    [OK] 已删除知识库: name={name}, kb_id={kb_id}")
    else:
        print(f"    [ERROR] 删除知识库失败: name={name}, kb_id={kb_id}")
    return ok


def create_kb(name, description):
    data = api_post("/log_kb", {"name": name, "description": description})
    if data.get("code") != 200:
        raise RuntimeError(f"创建知识库失败: {data}")
    kb_id = data["result"]["kb_id"]
    print(f"    [OK] 已创建知识库: name={name}, kb_id={kb_id}")
    return kb_id


# ============================================================
# 日志文件操作
# ============================================================

def upload_log_file(kb_id, name, source_path):
    payload = {
        "upload_log_file_configs": [
            {
                "name": name,
                "source_type": "local",
                "source": source_path,
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
    return data.get("result", {}).get("task_id", "")


def get_log_file(log_file_id):
    return api_get(f"/log_file/{log_file_id}")


def wait_for_parse_complete(log_file_ids):
    """轮询等待指定 log_file_id 的解析完成。"""
    target_ids = list(log_file_ids)
    print(f"\n  等待 {len(target_ids)} 个日志文件解析完成...")
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > POLL_MAX_WAIT:
            print(f"  [TIMEOUT] 等待超过 {POLL_MAX_WAIT}s")
            break

        done = 0
        running = 0
        pending = 0
        failed = 0
        for fid in target_ids:
            try:
                data = get_log_file(fid)
                if data.get("code") != 200:
                    pending += 1
                    continue
                lf = data.get("result", {})
                status = lf.get("parse_status") or lf.get("task_status") or ""
                if status in DONE_STATUSES:
                    done += 1
                elif status in RUNNING_STATUSES:
                    running += 1
                elif status in FAILED_STATUSES:
                    failed += 1
                    done += 1  # 失败也算结束
                else:
                    pending += 1
            except Exception:
                pending += 1

        print(f"  [{elapsed:.0f}s] 总数={len(target_ids)} 完成={done} "
              f"运行中={running} 失败={failed} 待处理={pending}")

        if done >= len(target_ids):
            print(f"  [OK] 所有 {done} 个日志文件解析已完成")
            break

        time.sleep(POLL_INTERVAL)


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 70)
    print("重建资产库：删除 data_set_rebuild + 新建 data_set + 上传 lingqu_xxx")
    print("=" * 70)

    # 健康检查
    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # Step 1: 删除 data_set_rebuild 知识库（整体删除）
    print(f"\n[Step 1] 删除知识库: {KB_NAME_DELETE}")
    if not delete_kb_by_name(KB_NAME_DELETE):
        print(f"[ERROR] 删除 {KB_NAME_DELETE} 失败，退出")
        sys.exit(1)

    # Step 2: 新建 data_set 知识库（若已存在先删除）
    print(f"\n[Step 2] 新建知识库: {KB_NAME_NEW}")
    if not delete_kb_by_name(KB_NAME_NEW):
        print(f"[ERROR] 清理已存在的 {KB_NAME_NEW} 失败，退出")
        sys.exit(1)
    kb_id = create_kb(KB_NAME_NEW, KB_DESC)

    # Step 3: 收集所有 lingqu_xxx 文件夹
    print("\n[Step 3] 收集 data_set 下所有 lingqu_xxx 文件夹...")
    case_infos = []
    seen_dir_names = set()  # 去重（防止两个子目录有同名）

    for sub in DATA_SUBDIRS:
        sub_dir = os.path.join(DATA_SET_DIR, sub)
        if not os.path.isdir(sub_dir):
            print(f"  [WARN] 子目录不存在: {sub_dir}")
            continue
        ds_cases = sorted([
            d for d in os.listdir(sub_dir)
            if d.startswith("lingqu") and os.path.isdir(os.path.join(sub_dir, d))
        ])
        print(f"  子目录 {sub}/: {len(ds_cases)} 个 lingqu 文件夹")

        for dir_name in ds_cases:
            if dir_name in seen_dir_names:
                print(f"    [SKIP] 重复案例名: {dir_name}")
                continue
            seen_dir_names.add(dir_name)
            case_infos.append({
                "dir_name": dir_name,
                "subdir_path": os.path.join(sub_dir, dir_name),
                "source_sub": sub,
            })

    total_scanned = len(seen_dir_names)
    print(f"  两个子目录共扫描 {total_scanned} 个 lingqu 文件夹（去重后）")
    print(f"  待上传 {len(case_infos)} 个案例")

    if not case_infos:
        print("[ERROR] 没有可上传的案例，退出")
        sys.exit(1)

    # Step 4: 上传并触发解析
    print(f"\n[Step 4] 上传日志文件并触发解析...")
    uploaded = {}  # log_file_id → case_info
    success_count = 0
    fail_count = 0

    for idx, ci in enumerate(case_infos, 1):
        print(f"\n  [{idx}/{len(case_infos)}] {ci['dir_name']}")
        try:
            log_file_id = upload_log_file(kb_id, ci["dir_name"], ci["subdir_path"])
            task_id = run_parse(log_file_id)
            uploaded[log_file_id] = {**ci, "task_id": task_id}
            success_count += 1
            print(f"    [OK] log_file_id={log_file_id}, task_id={task_id}")
        except Exception as e:
            fail_count += 1
            print(f"    [ERROR] {e}")

        if idx < len(case_infos):
            time.sleep(UPLOAD_DELAY)

    print(f"\n  上传完成: 成功 {success_count}, 失败 {fail_count}")

    if success_count == 0:
        print("[ERROR] 没有成功上传的案例，退出")
        sys.exit(1)

    # Step 5: 等待解析完成
    print("\n[Step 5] 等待解析完成...")
    wait_for_parse_complete(list(uploaded.keys()))

    # 汇总
    print(f"\n{'=' * 70}")
    print("重建完成！")
    print(f"{'=' * 70}")
    print(f"  已删除知识库: {KB_NAME_DELETE}")
    print(f"  新建知识库: {KB_NAME_NEW} (kb_id={kb_id})")
    print(f"  上传成功: {success_count}")
    print(f"  上传失败: {fail_count}")
    print(f"  解析等待: {len(uploaded)} 个")

    # 保存 log_file_id 映射
    map_path = os.path.join(os.path.dirname(__file__), "_dataset_kb_log_file_map.json")
    serializable_map = {}
    for log_file_id, ci in uploaded.items():
        serializable_map[log_file_id] = {
            "dir_name": ci["dir_name"],
            "source_sub": ci.get("source_sub", ""),
            "task_id": ci.get("task_id", ""),
            "kb_id": kb_id,
        }
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(serializable_map, f, ensure_ascii=False, indent=2)
    print(f"  log_file 映射已保存: {map_path}")


if __name__ == "__main__":
    main()
