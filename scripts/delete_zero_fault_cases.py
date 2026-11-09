#!/usr/bin/env python3
"""删除已解析完成且双零故障的 yxh_new_val case 资产库。

安全策略:
    - 删除前逐 case 重新校验 overall_status == successful 且双零故障
    - 不满足条件的 case 跳过并记录，防止误删
    - 通过 DELETE /log_kb/{kb_id} 级联删除
"""
import json
import time
import urllib.request

API = "http://127.0.0.1:9772"
SAFE_STATUS = ("successful", "successful_pending_remove")
DELAY = 0.2


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def delete(path):
    req = urllib.request.Request(API + path, method="DELETE")
    return json.load(urllib.request.urlopen(req, timeout=120))


def main():
    # 1. 分页拉取全部资产库
    all_kbs = []
    page = 1
    while True:
        d = post("/log_kb/list", {"page_cnt": 200, "page_num": page})
        kbs = d.get("result", {}).get("kbs", [])
        all_kbs += kbs
        if len(kbs) < 200:
            break
        page += 1

    cases = [kb for kb in all_kbs if kb["name"].startswith("lingqu_kvcache_dfx_")]
    print(f"case 资产库总数: {len(cases)}")

    # 2. 逐 case 校验并收集待删除
    to_delete = []
    skipped = []
    for kb in cases:
        kb_id = kb["id"]
        name = kb["name"]
        try:
            f = post(f"/log_file/list/{kb_id}", {"page_cnt": 5, "page_num": 1})
            files = f.get("result", {}).get("log_files", [])
        except Exception as e:
            skipped.append((name, f"list_err:{e}"))
            continue
        if not files:
            skipped.append((name, "no_log_file"))
            continue
        lf = files[0]
        status = lf.get("overall_status", "unknown")
        anomaly = lf.get("anomaly_cnt", 0) or 0
        fault = lf.get("trace_failure_event_cnt", 0) or 0
        if status in SAFE_STATUS and anomaly == 0 and fault == 0:
            to_delete.append((name, kb_id))
        else:
            skipped.append((name, f"status={status} anomaly={anomaly} fault={fault}"))

    print(f"待删除: {len(to_delete)}，跳过: {len(skipped)}")
    if skipped:
        print("跳过明细（前 10）:")
        for name, why in skipped[:10]:
            print(f"  - {name}: {why}")

    # 3. 执行删除
    ok = 0
    failed = []
    for idx, (name, kb_id) in enumerate(to_delete, 1):
        try:
            r = delete(f"/log_kb/{kb_id}")
            ok += 1
            if idx % 50 == 0 or idx == len(to_delete):
                print(f"  已删除 {idx}/{len(to_delete)}", flush=True)
        except Exception as e:
            failed.append((name, str(e)))
            print(f"  [ERROR] {name}: {e}")
        time.sleep(DELAY)

    print(f"\n完成: 删除成功 {ok}, 失败 {len(failed)}")
    if failed:
        print("失败清单:")
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
