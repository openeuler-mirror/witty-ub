#!/usr/bin/env python3
"""批量上传 test_set 日志数据到 witty-ub 系统。

用法:
    python scripts/upload_test_set.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - test_set 目录: /Users/zhaoyujin/Desktop/yxh_new_data_complete/test_set/yxh_new_0530
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:9772"
UPLOAD_DELAY = 0.5
API_TIMEOUT = 300

DATA_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete/test_set/yxh_new_0530"
KB_NAME = "test_set_0530"
KB_DESC = "test_set 验证数据集 (0530)"

SKIP_FILES = {"clean_logs.sh", "filter_fault_trace.sh"}


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


def get_existing_log_file_names(kb_id):
    names = set()
    page = 1
    while True:
        data = api_post(f"/log_file/list/{kb_id}", {"page_cnt": 100, "page_num": page})
        if data.get("code") != 200:
            break
        files = data["result"].get("log_files", [])
        for f in files:
            names.add(f["name"])
        if len(files) < 100:
            break
        page += 1
    return names


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


def check_parse_status(log_file_id):
    """检查日志文件解析状态"""
    try:
        data = api_post(f"/log_file/list", {"page_cnt": 1, "page_num": 1})
    except Exception:
        return "unknown"
    return "unknown"


def main():
    print("=" * 60)
    print("test_set 批量上传工具")
    print(f"数据目录: {DATA_DIR}")
    print(f"API: {API_BASE}")
    print("=" * 60)

    # 健康检查
    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    if not os.path.isdir(DATA_DIR):
        print(f"[ERROR] 数据目录不存在: {DATA_DIR}")
        sys.exit(1)

    # 1. 获取或创建知识库
    kb_id = get_or_create_knowledge_base(KB_NAME, KB_DESC)

    # 2. 获取已上传的文件名
    existing_names = get_existing_log_file_names(kb_id)
    print(f"  已上传 {len(existing_names)} 个日志文件")

    # 3. 遍历子目录
    subdirs = sorted([
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d)) and d not in SKIP_FILES
    ])
    print(f"  共发现 {len(subdirs)} 个子目录")

    to_upload = [d for d in subdirs if d not in existing_names]
    skipped = len(subdirs) - len(to_upload)
    print(f"  跳过 {skipped} 个已上传的子目录")
    print(f"  待上传 {len(to_upload)} 个子目录")

    # 保存上传结果 (log_file_name → log_file_id 映射)
    result_file = "/Users/zhaoyujin/Desktop/witty-ub/scripts/test_set_upload_results.json"
    results = {}

    success_count = 0
    fail_count = 0

    for idx, subdir_name in enumerate(to_upload, 1):
        subdir_path = os.path.join(DATA_DIR, subdir_name)
        print(f"\n  [{idx}/{len(to_upload)}] {subdir_name}")

        try:
            log_file_id = upload_log_file(kb_id, subdir_name, subdir_path)
            task_id = run_parse(log_file_id)
            results[subdir_name] = {
                "log_file_id": log_file_id,
                "task_id": task_id,
                "kb_id": kb_id,
            }
            success_count += 1
            print(f"    [OK] log_file_id={log_file_id}, task_id={task_id}")
        except Exception as e:
            fail_count += 1
            print(f"    [ERROR] {e}")
            continue

        if idx < len(to_upload):
            time.sleep(UPLOAD_DELAY)

    # 保存结果
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  上传结果已保存: {result_file}")
    print(f"\n  完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skipped}")
    print(f"\n  注意: 解析任务已触发，需要等待后端完成解析后才能使用相似案例分析功能。")
    print(f"  可通过 /log_file/list/{kb_id} 查看解析状态。")


if __name__ == "__main__":
    main()
