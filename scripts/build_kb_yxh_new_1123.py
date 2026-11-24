#!/usr/bin/env python3
"""新建资产库 yxh_new_1123，并把该目录下所有 lingqu_xxx 案例上传解析。

流程:
  1. 健康检查 http://127.0.0.1:9772
  2. 新建知识库 yxh_new_1123（若同名已存在则直接退出，避免误删）
  3. 将 /Users/zhaoyujin/Desktop/witty_validate_data/yxh_new_1123 下的
     每个 lingqu_xxx 文件夹作为一个任务（log_file）以 local 路径上传
  4. 逐个触发解析，并轮询等待全部完成

用法:
    python scripts/build_kb_yxh_new_1123.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - 数据目录已按「每个 lingqu_xxx 文件夹一个案例」组织好
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
UPLOAD_DELAY = 0.3
POLL_INTERVAL = 10
POLL_MAX_WAIT = 7200

DATA_DIR = "/Users/zhaoyujin/Desktop/witty_validate_data/yxh_new_1123"
KB_NAME = "yxh_new_1123"
KB_DESC = "yxh_new_1123 资产库（lingqu_xxx 文件夹，每个文件夹一个任务）"
LOG_TYPE = "KVCache"

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


def api_post(path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    return _request("POST", f"{API_BASE}{path}", data=data, headers=headers)


def api_put(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return _request("PUT", url)


# ============================================================
# 知识库 / 日志文件操作
# ============================================================

def find_kb_id_by_name(name):
    data = api_post("/log_kb/list", {"page_cnt": 200, "page_num": 1})
    if data.get("code") != 200:
        return None
    for kb in data.get("result", {}).get("kbs", []):
        if kb.get("name") == name:
            return kb["id"]
    return None


def create_kb(name, description):
    data = api_post("/log_kb", {"name": name, "description": description})
    if data.get("code") != 200:
        raise RuntimeError(f"创建知识库失败: {data}")
    kb_id = data["result"]["kb_id"]
    print(f"    [OK] 已创建知识库: name={name}, kb_id={kb_id}")
    return kb_id


def upload_log_file(kb_id, name, source_path):
    payload = {
        "upload_log_file_configs": [
            {
                "name": name,
                "source_type": "local",
                "source": source_path,
                "log_type": LOG_TYPE,
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
    target_ids = list(log_file_ids)
    print(f"\n  等待 {len(target_ids)} 个日志文件解析完成...")
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_MAX_WAIT:
            print(f"  [TIMEOUT] 等待超过 {POLL_MAX_WAIT}s")
            break
        done = running = pending = failed = 0
        for fid in target_ids:
            try:
                data = get_log_file(fid)
                if data.get("code") != 200:
                    pending += 1
                    continue
                lf = data.get("result", {}).get("log_file", {})
                status = (
                    lf.get("overall_status")
                    or (lf.get("task") or {}).get("status")
                    or ""
                )
                if status in DONE_STATUSES:
                    done += 1
                elif status in RUNNING_STATUSES:
                    running += 1
                elif status in FAILED_STATUSES:
                    failed += 1
                    done += 1
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
    print("新建资产库 yxh_new_1123 并解析全部 lingqu_xxx 案例")
    print("=" * 70)

    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # Step 1: 新建知识库
    print(f"\n[Step 1] 新建知识库: {KB_NAME}")
    existing = find_kb_id_by_name(KB_NAME)
    if existing:
        print(f"[ERROR] 同名知识库已存在: kb_id={existing}，为避免误删已退出。")
        sys.exit(1)
    kb_id = create_kb(KB_NAME, KB_DESC)

    # Step 2: 收集案例文件夹
    print(f"\n[Step 2] 收集 {DATA_DIR} 下的 lingqu_xxx 文件夹...")
    if not os.path.isdir(DATA_DIR):
        print(f"[ERROR] 数据目录不存在: {DATA_DIR}")
        sys.exit(1)
    case_infos = sorted(
        d for d in os.listdir(DATA_DIR)
        if d.startswith("lingqu") and os.path.isdir(os.path.join(DATA_DIR, d))
    )
    print(f"  共发现 {len(case_infos)} 个案例")
    if not case_infos:
        print("[ERROR] 没有可上传的案例，退出")
        sys.exit(1)

    # Step 3: 上传并触发解析
    print("\n[Step 3] 上传日志文件并触发解析...")
    uploaded = {}
    success_count = fail_count = 0
    for idx, dir_name in enumerate(case_infos, 1):
        src = os.path.join(DATA_DIR, dir_name)
        print(f"\n  [{idx}/{len(case_infos)}] {dir_name}")
        try:
            log_file_id = upload_log_file(kb_id, dir_name, src)
            task_id = run_parse(log_file_id)
            uploaded[log_file_id] = {"dir_name": dir_name, "task_id": task_id}
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

    # Step 4: 等待解析完成
    print("\n[Step 4] 等待解析完成...")
    wait_for_parse_complete(list(uploaded.keys()))

    print(f"\n{'=' * 70}")
    print("完成！")
    print(f"  新建知识库: {KB_NAME} (kb_id={kb_id})")
    print(f"  上传成功: {success_count}  失败: {fail_count}")

    map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_yxh_new_1123_log_file_map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump({fid: {**ci, "kb_id": kb_id} for fid, ci in uploaded.items()},
                  f, ensure_ascii=False, indent=2)
    print(f"  log_file 映射已保存: {map_path}")


if __name__ == "__main__":
    main()
