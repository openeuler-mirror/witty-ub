#!/usr/bin/env python3
"""修复案例库中无 features 的案例：删除旧案例 + 通过 API 重新创建并触发后端自动提取 features。

前提:
    - 后端 API 服务运行中（端口 9772）
    - data_set KB 中已上传并解析完毕日志文件

用法:
    python3 scripts/fix_missing_features.py
"""

from __future__ import annotations

import os
import json
import urllib.request
import urllib.error

# ============================================================
# 配置
# ============================================================

DATA_SET_KB_ID = "fb3749dc-3264-4509-89fb-c34680865271"
API = "http://127.0.0.1:9772"


def fetch_log_file_map(kb_id: str) -> dict:
    """从 API 查询 KB 下所有 log_file，构建 name → log_file_id 映射。"""
    url = f"{API}/log_file/list/{kb_id}"
    payload = json.dumps({"page_cnt": 500, "page_num": 1}).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    files = data.get("result", {}).get("log_files", [])
    mapping = {f["name"]: f["id"] for f in files}
    print(f"  从 API 获取 {len(mapping)} 个 log_file 映射")
    return mapping


def api_list_cases() -> list:
    """通过 GET /case_library/list 获取所有案例。"""
    req = urllib.request.Request(f"{API}/case_library/list", method="GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("result", []) or []


def api_create_case(case_data: dict):
    """通过 POST /case_library API 创建案例，后端自动提取 features。"""
    payload = {"data": json.dumps(case_data)}
    boundary = "----FixBoundary"
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
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            return err_body
        except Exception:
            return {"code": e.code, "message": str(e)}


def api_delete_case(case_id: str) -> bool:
    """删除案例。"""
    req = urllib.request.Request(
        f"{API}/case_library/{case_id}",
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp.get("code") == 200
    except urllib.error.HTTPError:
        return False


def main():
    print("=" * 70)
    print("修复无 features 案例：重新调用 API 创建并触发后端特征提取")
    print("=" * 70)

    # 1. 通过 API 获取所有案例，找出无 features 的
    print("\n[1/4] 通过 API 获取所有案例，识别无 features 案例...")
    cases = api_list_cases()
    print(f"  案例库共 {len(cases)} 个案例")

    no_features_cases = []
    has_features_count = 0
    for case in cases:
        if case.get("features"):
            has_features_count += 1
        else:
            no_features_cases.append(case)

    print(f"  有 features: {has_features_count} 个")
    print(f"  无 features: {len(no_features_cases)} 个 (待修复)")

    if not no_features_cases:
        print("\n所有案例都有 features，无需修复。")
        return

    # 2. 获取 log_file 映射
    print("\n[2/4] 获取 data_set KB 的 log_file 映射...")
    try:
        log_file_map = fetch_log_file_map(DATA_SET_KB_ID)
    except Exception as e:
        print(f"  ✗ 获取 log_file 映射失败: {e}")
        print("  请确认后端 API 服务运行中且 data_set KB 存在")
        return

    # 3. 统计无 features 案例的 log_file_name 在映射中的覆盖率
    print("\n[3/4] 检查 log_file_name 在映射中的覆盖率...")
    no_lfid = []
    will_fix = []
    for case in no_features_cases:
        log_file_name = case.get("log_file_name", "")
        log_file_id = log_file_map.get(log_file_name, "")
        if log_file_id:
            will_fix.append((case, log_file_id))
        else:
            no_lfid.append((case, log_file_name))

    print(f"  可修复（找到 log_file_id）: {len(will_fix)} 个")
    print(f"  无法修复（KB 中找不到 log_file）: {len(no_lfid)} 个")
    if no_lfid:
        print(f"\n  无法修复的案例 log_file_name 列表:")
        for case, lfn in no_lfid[:20]:
            rct = case.get("root_cause_type", "")
            print(f"    - {case.get('id', '')[:12]}  rct={rct:25s}  log_file_name={lfn}")
        if len(no_lfid) > 20:
            print(f"    ... 还有 {len(no_lfid) - 20} 个")

    if not will_fix:
        print("\n没有可修复的案例。可能需要先重新上传日志到 data_set KB。")
        return

    # 4. 逐个修复：删除旧案例 + 重新创建（带 log_file_id）
    print(f"\n[4/4] 逐个修复 {len(will_fix)} 个案例（删除+重建）...")
    success = 0
    fail = 0
    fail_details = []
    for i, (case, log_file_id) in enumerate(will_fix, 1):
        case_id = case.get("id", "")
        rct = case.get("root_cause_type", "")
        cc = case.get("case_category", "")
        log_file_name = case.get("log_file_name", "")

        # 4a. 删除旧案例
        if not api_delete_case(case_id):
            print(f"  [{i}/{len(will_fix)}] {log_file_name[:50]}  删除旧案例失败，跳过")
            fail += 1
            fail_details.append((case_id, rct, "delete_failed"))
            continue

        # 4b. 创建新案例（带 log_file_id），后端自动提取 features
        case_data = {
            "kb_id": DATA_SET_KB_ID,
            "root_cause_type": rct,
            "description": case.get("description", ""),
            "task_ids": case.get("task_ids", []),
            "task_names": case.get("task_names", []),
            "log_file_id": log_file_id,
            "log_file_name": log_file_name,
            "case_category": cc,
        }
        resp = api_create_case(case_data)
        if resp and resp.get("code") == 200:
            new_case = resp.get("result", {})
            if new_case.get("features"):
                fc = new_case["features"].get("fault_category", "?")
                print(f"  [{i}/{len(will_fix)}] {log_file_name[:50]}  OK  fc={fc}")
                success += 1
            else:
                print(f"  [{i}/{len(will_fix)}] {log_file_name[:50]}  OK 但无features")
                fail += 1
                fail_details.append((case_id, rct, "no_features_after_create"))
        else:
            msg = resp.get("message", "") if resp else ""
            print(f"  [{i}/{len(will_fix)}] {log_file_name[:50]}  FAIL  {msg}")
            fail += 1
            fail_details.append((case_id, rct, f"create_failed: {msg}"))

    # 总结
    print(f"\n{'=' * 70}")
    print("修复完成！")
    print(f"{'=' * 70}")
    print(f"  原无 features 案例: {len(no_features_cases)} 个")
    print(f"  KB 中找到 log_file_id: {len(will_fix)} 个")
    print(f"  成功提取 features: {success} 个")
    print(f"  失败: {fail} 个")
    print(f"  KB 中找不到 log_file: {len(no_lfid)} 个（需重新上传日志）")
    if fail_details:
        print(f"\n  失败详情:")
        for case_id, rct, reason in fail_details[:20]:
            print(f"    - {case_id[:12]}  rct={rct:25s}  reason={reason}")


if __name__ == "__main__":
    main()
