#!/usr/bin/env python3
"""监控 yxh_new_val 剩余 case 资产库解析进度，全部终态后输出汇总。

终态: successful / successful_pending_remove / failed / failed_pending_remove / cancelled
非终态: pending / running / retrying / unknown
"""
import json
import time
import urllib.request

API = "http://127.0.0.1:9772"
TERMINAL = {
    "successful",
    "successful_pending_remove",
    "failed",
    "failed_pending_remove",
    "cancelled",
}
POLL_INTERVAL = 60


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def list_all_kbs():
    all_kbs = []
    page = 1
    while True:
        d = post("/log_kb/list", {"page_cnt": 200, "page_num": page})
        kbs = d.get("result", {}).get("kbs", [])
        all_kbs += kbs
        if len(kbs) < 200:
            break
        page += 1
    return all_kbs


def main():
    kbs = [kb for kb in list_all_kbs() if kb["name"].startswith("lingqu_kvcache_dfx_")]
    print(f"监控开始: {len(kbs)} 个 case", flush=True)
    kb_ids = [kb["id"] for kb in kbs]
    names = {kb["id"]: kb["name"] for kb in kbs}

    state = {}  # kb_id -> {status, anomaly, fault}
    round_no = 0
    while True:
        round_no += 1
        dist = {}
        non_terminal = 0
        for kb_id in kb_ids:
            try:
                f = post(f"/log_file/list/{kb_id}", {"page_cnt": 5, "page_num": 1})
                files = f.get("result", {}).get("log_files", [])
            except Exception as e:
                state[kb_id] = {"status": f"err:{e}", "anomaly": 0, "fault": 0}
                dist["err"] = dist.get("err", 0) + 1
                non_terminal += 1
                continue
            if not files:
                state[kb_id] = {"status": "no_log_file", "anomaly": 0, "fault": 0}
                dist["no_log_file"] = dist.get("no_log_file", 0) + 1
                non_terminal += 1
                continue
            lf = files[0]
            status = lf.get("overall_status", "unknown")
            anomaly = lf.get("anomaly_cnt", 0) or 0
            fault = lf.get("trace_failure_event_cnt", 0) or 0
            state[kb_id] = {"status": status, "anomaly": anomaly, "fault": fault}
            dist[status] = dist.get(status, 0) + 1
            if status not in TERMINAL:
                non_terminal += 1

        order = ["successful", "failed", "cancelled", "retrying", "running", "pending", "unknown", "err", "no_log_file"]
        summary = " ".join(f"{s}={dist.get(s, 0)}" for s in order if dist.get(s))
        print(
            f"[轮次{round_no} {time.strftime('%H:%M:%S')}] {summary} | 非终态={non_terminal}",
            flush=True,
        )

        # 持久化快照
        with open("data/validate_cases_monitor_snapshot.json", "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "round": round_no,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "dist": dist,
                    "non_terminal": non_terminal,
                    "state": {
                        names[kid]: state[kid] for kid in kb_ids
                    },
                },
                fp,
                ensure_ascii=False,
            )

        if non_terminal == 0:
            print(f"全部 {len(kb_ids)} 个 case 已达终态，监控结束", flush=True)
            # 统计终态明细
            zero = sum(1 for s in state.values() if s["status"] in ("successful", "successful_pending_remove") and s["anomaly"] == 0 and s["fault"] == 0)
            with_fault = sum(1 for s in state.values() if s["anomaly"] > 0 or s["fault"] > 0)
            print(f"终态汇总: 双零可删={zero}, 有故障={with_fault}", flush=True)
            break

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
