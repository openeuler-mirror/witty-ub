#!/usr/bin/env python3
"""批量导入 yxh KVCache 日志数据到 witty-ub 系统。

用法:
    python scripts/import_yxh_data.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - 两个数据集目录已就绪:
        /Users/zhaoyujin/Desktop/yxh_new_simplified/
        /Users/zhaoyujin/Desktop/yxh_new_0530_simplified/

特性:
    - 自动跳过已存在的知识库
    - 自动跳过已上传的日志文件（按名称匹配）
    - 上传后自动触发解析
"""

import os
import sys
import time

import requests

API_BASE = "http://127.0.0.1:9772"
UPLOAD_DELAY = 1.0
API_TIMEOUT = 120  # 后端处理可能耗时较长

KNOWLEDGE_BASES = [
    (
        "yxh_new_simplified",
        "yxh_new_simplified数据集",
        "/Users/zhaoyujin/Desktop/yxh_new_simplified",
    ),
    (
        "yxh_new_0530_simplified",
        "yxh_new_0530_simplified数据集",
        "/Users/zhaoyujin/Desktop/yxh_new_0530_simplified",
    ),
]

SKIP_FILES = {"clean_logs.sh", "filter_fault_trace.sh"}


def api_get(path, **kwargs):
    resp = requests.get(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_post(path, **kwargs):
    resp = requests.post(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_put(path, **kwargs):
    resp = requests.put(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def get_or_create_knowledge_base(name: str, description: str) -> str:
    """获取已有知识库 ID 或创建新的，返回 kb_id。"""
    # 列出所有知识库
    data = api_post("/log_kb/list", json={"page_cnt": 200, "page_num": 1})
    if data.get("code") == 200:
        for kb in data["result"].get("kbs", []):
            if kb["name"] == name:
                kb_id = kb["id"]
                print(f"  [SKIP] 知识库已存在: name={name}, kb_id={kb_id}")
                return kb_id

    # 不存在则创建
    data = api_post("/log_kb", json={"name": name, "description": description})
    if data.get("code") != 200:
        raise RuntimeError(f"创建知识库失败: {data}")
    kb_id = data["result"]["kb_id"]
    print(f"  [OK] 知识库已创建: name={name}, kb_id={kb_id}")
    return kb_id


def get_existing_log_file_names(kb_id: str) -> set:
    """获取知识库下已上传的日志文件名称集合。"""
    names = set()
    page = 1
    while True:
        data = api_post(f"/log_file/list/{kb_id}", json={"page_cnt": 100, "page_num": page})
        if data.get("code") != 200:
            break
        files = data["result"].get("log_files", [])
        for f in files:
            names.add(f["name"])
        if len(files) < 100:
            break
        page += 1
    return names


def upload_log_file(kb_id: str, subdir_name: str, subdir_path: str) -> str:
    """上传日志文件，返回 log_file_id。"""
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
    data = api_post(f"/log_file/{kb_id}", json=payload)
    if data.get("code") != 200:
        raise RuntimeError(f"上传日志文件失败: {data}")
    log_file_ids = data["result"]["log_file_ids"]
    if not log_file_ids:
        raise RuntimeError(f"上传日志文件返回空 ID 列表: {data}")
    log_file_id = log_file_ids[0]
    print(f"    [OK] 已上传: {subdir_name} -> {log_file_id}")
    return log_file_id


def run_parse(log_file_id: str) -> str:
    """触发解析任务，返回 task_id。"""
    data = api_put(f"/log_file/run/{log_file_id}", params={"run": True})
    if data.get("code") != 200:
        raise RuntimeError(f"触发解析失败: {data}")
    task_id = data["result"].get("task_id", "")
    print(f"    [OK] 解析已触发: task_id={task_id}")
    return task_id


def process_knowledge_base(name: str, description: str, data_dir: str):
    print(f"\n{'='*60}")
    print(f"处理知识库: {name}")
    print(f"数据目录: {data_dir}")
    print(f"{'='*60}")

    if not os.path.isdir(data_dir):
        print(f"  [ERROR] 数据目录不存在: {data_dir}")
        return

    # 1. 获取或创建知识库
    try:
        kb_id = get_or_create_knowledge_base(name, description)
    except Exception as e:
        print(f"  [ERROR] 知识库操作失败: {e}")
        return

    # 2. 获取已上传的文件名
    try:
        existing_names = get_existing_log_file_names(kb_id)
        print(f"  已上传 {len(existing_names)} 个日志文件")
    except Exception as e:
        print(f"  [WARN] 获取已有文件列表失败: {e}")
        existing_names = set()

    # 3. 遍历子目录
    subdirs = sorted(
        [
            d
            for d in os.listdir(data_dir)
            if os.path.isdir(os.path.join(data_dir, d)) and d not in SKIP_FILES
        ]
    )
    total = len(subdirs)
    print(f"  共发现 {total} 个子目录")

    # 过滤掉已上传的
    to_upload = [d for d in subdirs if d not in existing_names]
    skipped = total - len(to_upload)
    if skipped > 0:
        print(f"  跳过 {skipped} 个已上传的子目录")
    print(f"  待上传 {len(to_upload)} 个子目录")

    success_count = 0
    fail_count = 0

    for idx, subdir_name in enumerate(to_upload, 1):
        subdir_path = os.path.join(data_dir, subdir_name)
        print(f"\n  [{idx}/{len(to_upload)}] {subdir_name}")

        try:
            log_file_id = upload_log_file(kb_id, subdir_name, subdir_path)
            run_parse(log_file_id)
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"    [ERROR] 失败: {e}")
            continue

        if idx < len(to_upload):
            time.sleep(UPLOAD_DELAY)

    print(f"\n  完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skipped}")


def main():
    print("KVCache 日志数据批量导入工具（增量模式）")
    print(f"API: {API_BASE}")

    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    for name, description, data_dir in KNOWLEDGE_BASES:
        process_knowledge_base(name, description, data_dir)

    print(f"\n{'='*60}")
    print("全部处理完毕")


if __name__ == "__main__":
    main()
