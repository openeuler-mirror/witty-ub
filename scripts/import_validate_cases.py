#!/usr/bin/env python3
"""批量导入 yxh_new_val 验证集：每个 case 目录解析为独立资产库。

用法:
    python scripts/import_validate_cases.py

前提:
    - witty-ub FastAPI 服务已在 http://127.0.0.1:9772 运行
    - 数据已解压到 data/validate_cases/yxh_new_val/<case>/，每个 case 目录含各 pod 日志

特性:
    - 每个 case 目录创建独立资产库（名称 = case 目录名）
    - 自动跳过已存在的资产库（幂等，可断点续跑）
    - 上传目录日志后由后端自动创建解析任务（KVCache 解析 + 故障诊断 + trace 存储）
"""

import os
import sys
import time

import requests

API_BASE = "http://127.0.0.1:9772"
DATA_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "validate_cases",
    "yxh_new_val",
)
UPLOAD_DELAY = 0.5
API_TIMEOUT = 300


def api_get(path, **kwargs):
    resp = requests.get(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def api_post(path, **kwargs):
    resp = requests.post(f"{API_BASE}{path}", timeout=API_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def list_existing_kb_names() -> set:
    """返回当前系统所有资产库名称集合。"""
    names = set()
    page = 1
    while True:
        data = api_post("/log_kb/list", json={"page_cnt": 200, "page_num": page})
        if data.get("code") != 200:
            break
        kbs = data["result"].get("kbs", [])
        for kb in kbs:
            names.add(kb["name"])
        if len(kbs) < 200:
            break
        page += 1
    return names


def create_kb(name: str) -> str:
    """创建资产库，返回 kb_id。"""
    data = api_post(
        "/log_kb",
        json={"name": name, "description": f"yxh_new_val 验证集 case：{name}"},
    )
    if data.get("code") != 200:
        raise RuntimeError(f"创建资产库失败: {data}")
    return data["result"]["kb_id"]


def upload_case_dir(kb_id: str, case_name: str, case_path: str) -> list:
    """上传 case 目录日志，返回 log_file_ids（上传即自动创建解析任务）。"""
    payload = {
        "upload_log_file_configs": [
            {
                "name": case_name,
                "source_type": "local",
                "source": case_path,
                "log_type": "KVCache",
            }
        ]
    }
    data = api_post(f"/log_file/{kb_id}", json=payload)
    if data.get("code") != 200:
        raise RuntimeError(f"上传日志失败: {data}")
    log_file_ids = data["result"].get("log_file_ids", [])
    if not log_file_ids:
        raise RuntimeError(f"上传日志返回空 ID 列表: {data}")
    return log_file_ids


def main():
    print("yxh_new_val 验证集批量导入（每个 case 一个独立资产库）")
    print(f"API: {API_BASE}")
    print(f"数据目录: {DATA_ROOT}")

    try:
        api_get("/health_check")
        print("API 健康检查通过")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    if not os.path.isdir(DATA_ROOT):
        print(f"[ERROR] 数据目录不存在: {DATA_ROOT}")
        sys.exit(1)

    cases = sorted(
        d for d in os.listdir(DATA_ROOT)
        if os.path.isdir(os.path.join(DATA_ROOT, d))
    )
    total = len(cases)
    print(f"共发现 {total} 个 case 目录")

    try:
        existing_names = list_existing_kb_names()
        print(f"系统已有 {len(existing_names)} 个资产库")
    except Exception as e:
        print(f"[WARN] 获取已有资产库列表失败，按全部新建处理: {e}")
        existing_names = set()

    to_import = [c for c in cases if c not in existing_names]
    skipped = total - len(to_import)
    print(f"待导入 {len(to_import)} 个（跳过已存在的 {skipped} 个）")

    success = 0
    failed = []

    for idx, case_name in enumerate(to_import, 1):
        case_path = os.path.join(DATA_ROOT, case_name)
        print(f"\n[{idx}/{len(to_import)}] {case_name}")

        try:
            kb_id = create_kb(case_name)
            log_file_ids = upload_case_dir(kb_id, case_name, case_path)
            success += 1
            print(f"  [OK] kb_id={kb_id} log_file_ids={log_file_ids}")
        except Exception as e:
            failed.append((case_name, str(e)))
            print(f"  [ERROR] {e}")

        if idx < len(to_import):
            time.sleep(UPLOAD_DELAY)

    print(f"\n{'='*60}")
    print(f"完成: 成功 {success}, 失败 {len(failed)}, 跳过 {skipped}")
    if failed:
        print("失败清单:")
        for case_name, err in failed:
            print(f"  - {case_name}: {err}")


if __name__ == "__main__":
    main()
