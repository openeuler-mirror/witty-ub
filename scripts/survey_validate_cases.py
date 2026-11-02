#!/usr/bin/env python3
"""调查 yxh_new_val 验证集 581 个 case 资产库的解析状态与故障数分布。

输出:
    - 按 overall_status 的分布
    - 解析完成且 (anomaly_cnt==0 and trace_failure_event_cnt==0) 的 case 清单
"""
import json
import urllib.request

API = "http://127.0.0.1:9772"


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def get(path):
    return json.load(urllib.request.urlopen(API + path, timeout=60))


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

    status_dist = {}
    zero_fault_done = []
    zero_fault_pending = []
    with_fault = []
    failed_or_unknown = []

    for idx, kb in enumerate(cases, 1):
        kb_id = kb["id"]
        name = kb["name"]
        try:
            f = post(f"/log_file/list/{kb_id}", {"page_cnt": 5, "page_num": 1})
            files = f.get("result", {}).get("log_files", [])
        except Exception as e:
            failed_or_unknown.append((name, f"list_err:{e}"))
            continue
        if not files:
            failed_or_unknown.append((name, "no_log_file"))
            continue
        lf = files[0]
        status = lf.get("overall_status", "unknown")
        status_dist[status] = status_dist.get(status, 0) + 1
        anomaly = lf.get("anomaly_cnt", 0) or 0
        fault = lf.get("trace_failure_event_cnt", 0) or 0

        done = status in ("successful", "successful_pending_remove")
        if anomaly == 0 and fault == 0:
            if done:
                zero_fault_done.append((name, anomaly, fault))
            else:
                zero_fault_pending.append((name, status, anomaly, fault))
        else:
            with_fault.append((name, status, anomaly, fault))

        if idx % 100 == 0:
            print(f"  已扫描 {idx}/{len(cases)}", flush=True)

    print("\n=== overall_status 分布 ===")
    for k, v in sorted(status_dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print(f"\n解析完成且双零故障: {len(zero_fault_done)}")
    print(f"双零故障但未完成解析: {len(zero_fault_pending)}")
    print(f"有故障: {len(with_fault)}")
    print(f"异常/无日志: {len(failed_or_unknown)}")

    if zero_fault_pending:
        print("\n=== 双零但未完成解析（按状态分组） ===")
        from collections import Counter
        for k, v in Counter(s for _, s, _, _ in zero_fault_pending).items():
            print(f"  {k}: {v}")

    out = "data/validate_cases_zero_fault_done.json"
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(
            {
                "zero_fault_done": [{"name": n, "anomaly_cnt": a, "trace_failure_event_cnt": f} for n, a, f in zero_fault_done],
                "zero_fault_pending": [{"name": n, "status": s, "anomaly_cnt": a, "trace_failure_event_cnt": f} for n, s, a, f in zero_fault_pending],
                "with_fault": [{"name": n, "status": s, "anomaly_cnt": a, "trace_failure_event_cnt": f} for n, s, a, f in with_fault],
                "failed_or_unknown": failed_or_unknown,
            },
            fp,
            ensure_ascii=False,
            indent=1,
        )
    print(f"\n结果已保存到 {out}")


if __name__ == "__main__":
    main()
