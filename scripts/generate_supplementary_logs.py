#!/usr/bin/env python3
"""
Generate supplementary worker/cluster logs for a given SDK client access log.
Produces: datasystem_worker.INFO.log, ds_client_10411.INFO.log, and access.log
(worker-side) with controlled fault types and latency correlations.

Usage:
    python scripts/generate_supplementary_logs.py \
        data/logs/daas/SDK_6.62.222.228/ds_client_access_3941.20260511105357.log \
        --worker-ratio 0.10 \
        --fault-ratio 0.03 \
        --output-dir data/logs/daas/SDK_6.62.222.228/
"""
import argparse
import os
import random
import sys
from collections import defaultdict

# Fault types and their error messages for worker INFO / client INFO logs
FAULT_TYPES_WORKER = [
    ("RPC_RECV_TIMEOUT", "[RPC_RECV_TIMEOUT] client timeout: 5000ms, peer worker alive"),
    ("TCP_CONNECT_RESET", "[TCP_CONNECT_RESET] connection reset by peer {ip}:8080"),
    ("ETCD_TIMEOUT", "etcd is timeout, retry: 3, duration: 5000ms"),
    ("ETCD_UNAVAILABLE", "etcd is unavailable, retry timeout"),
    ("SOCK_WAIT_TIMEOUT", "[SOCK_CONN_WAIT_TIMEOUT] connection wait timeout 10000ms"),
    ("ZMQ_DISCONNECT", "zmq_gateway_recreate_total=+5, zmq_event_disconnect_total=+3"),
    ("MMAP_FAILED", "Get mmap entry failed for objectKey: test, errno=12"),
    ("SEND_BUFFER_FULL", "[SEND_BUFFER_FULL] send buffer exhausted, dropped: 15 packets"),
    ("LINK_RESET", "[LINK_RESET] URMA link reset detected, recovering"),
]

FAULT_TYPES_CLIENT = [
    ("OBJECT_NOT_FOUND", "Can't find object, objectKey: test_key"),
    ("CONN_NOT_CONFIGURED", "ConnectOptions was not configured"),
    ("TIMEOUT_CLIENT", "[RPC_RECV_TIMEOUT] client timeout: 5000ms, peer worker alive"),
    ("TCP_RESET", "[TCP_CONNECT_RESET] connection reset by peer 10.0.0.2:8080"),
    ("SHM_QUEUE_FULL", "[SHM_QUEUE_FULL] shared memory queue full, capacity 1024"),
    ("INFLIGHT_LIMIT", "[INFLIGHT_LIMIT] too many in-flight requests: 256/256"),
]

# Worker operations (mirrors SDK operations)
OP_MAP = {
    "DS_KV_CLIENT_GET": "DS_POSIX_GET",
    "DS_KV_CLIENT_SET": "DS_POSIX_PUBLISH",
    "DS_KV_CLIENT_CREATE": "DS_POSIX_CREATE",
}


def parse_sdk_line(line: str) -> dict | None:
    """Parse one SDK access log line, return dict of fields or None."""
    parts = line.rstrip("\n").split(" | ")
    if len(parts) < 11:
        return None
    try:
        return {
            "timestamp": parts[0].strip(),
            "pod_ip": parts[3].strip(),
            "pid_tid": parts[4].strip(),
            "trace_id": parts[5].strip(),
            "cluster": parts[6].strip(),
            "status_code": parts[7].strip(),
            "operation": parts[8].strip(),
            "latency_us": int(parts[9].strip()),
            "data_size": parts[10].strip(),
            "metadata": parts[11].strip() if len(parts) > 11 else "",
            "error_msg": parts[12].strip() if len(parts) > 12 else "",
        }
    except (ValueError, IndexError):
        return None


def generate_worker_access(log_entry: dict) -> str:
    """Generate a worker-side access log line matching the SDK entry."""
    worker_op = OP_MAP.get(log_entry["operation"], "DS_POSIX_GET")
    worker_latency = max(50, int(log_entry["latency_us"] * random.uniform(0.3, 0.7)))
    return (
        f"{log_entry['timestamp']} | I | access_recorder.cpp:220 | "
        f"{log_entry['pod_ip']} | {log_entry['pid_tid']} | "
        f"{log_entry['trace_id']} | {log_entry['cluster']} | "
        f"{log_entry['status_code']} | {worker_op} | {worker_latency} | "
        f"{log_entry['data_size']} | {log_entry['metadata']} | "
        f"{log_entry['error_msg']}"
    )


def generate_faulty_worker_access(log_entry: dict, fault_type: str) -> str:
    """Generate worker access log with elevated latency for fault scenarios."""
    worker_op = OP_MAP.get(log_entry["operation"], "DS_POSIX_GET")
    if fault_type in ("RPC_RECV_TIMEOUT", "SOCK_WAIT_TIMEOUT", "LINK_RESET"):
        worker_latency = random.randint(5000, 15000)
    elif fault_type in ("TCP_CONNECT_RESET", "ETCD_UNAVAILABLE"):
        worker_latency = random.randint(3000, 10000)
    else:
        worker_latency = random.randint(1500, 5000)
    return (
        f"{log_entry['timestamp']} | I | access_recorder.cpp:220 | "
        f"{log_entry['pod_ip']} | {log_entry['pid_tid']} | "
        f"{log_entry['trace_id']} | {log_entry['cluster']} | "
        f"{log_entry['status_code']} | {worker_op} | {worker_latency} | "
        f"{log_entry['data_size']} | {log_entry['metadata']} | "
    )


def generate_info_line(log_entry: dict, fault_msg: str, source_file: str = "worker_impl.cpp:100") -> str:
    """Generate a component INFO log line with a fault message."""
    ts = log_entry["timestamp"]
    if "." in ts:
        base, frac = ts.rsplit(".", 1)
        frac_us = int(frac.ljust(6, "0")[:6])
        frac_us += random.randint(100, 900)
        ts = f"{base}.{frac_us:06d}"
    return (
        f"{ts} | I | {source_file} | {log_entry['pod_ip']} | "
        f"{log_entry['pid_tid']} | {log_entry['trace_id']} | "
        f"{log_entry['cluster']} | {fault_msg}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate supplementary worker/cluster logs for SDK access logs"
    )
    parser.add_argument("input_file", help="Path to the SDK client access log")
    parser.add_argument(
        "--worker-ratio", type=float, default=0.10,
        help="Fraction of traces to generate worker access logs for (default: 0.10)"
    )
    parser.add_argument(
        "--fault-ratio", type=float, default=0.03,
        help="Fraction of worker-traced entries to generate faults for (default: 0.03)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: same as input file)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    args = parser.parse_args()

    random.seed(args.seed)
    input_file = os.path.abspath(args.input_file)
    out_dir = args.output_dir or os.path.dirname(input_file)
    os.makedirs(out_dir, exist_ok=True)

    pod_ip = None
    trace_ids = []
    all_entries = []
    start_ts = None
    end_ts = None

    print(f"Reading: {input_file}")
    with open(input_file, "r") as f:
        for line in f:
            entry = parse_sdk_line(line)
            if entry is None:
                continue
            all_entries.append(entry)
            trace_ids.append(entry["trace_id"])
            if pod_ip is None:
                pod_ip = entry["pod_ip"]
                pid_tid_prefix = entry["pid_tid"]
            if start_ts is None:
                start_ts = entry["timestamp"]
            end_ts = entry["timestamp"]

    unique_traces = list(dict.fromkeys(trace_ids))
    total_traces = len(unique_traces)
    total_lines = len(all_entries)

    print(f"  Total lines: {total_lines}")
    print(f"  Unique traces: {total_traces}")
    print(f"  Pod IP: {pod_ip}")
    print(f"  PID:TID prefix: {pid_tid_prefix}")

    # Determine which traces get worker-side representation
    n_worker = max(50, int(total_traces * args.worker_ratio))
    n_fault = max(10, int(n_worker * args.fault_ratio))

    sampled_worker = set(random.sample(unique_traces, n_worker))
    sampled_fault = set(random.sample(list(sampled_worker), n_fault))
    sampled_client_fault = set(random.sample(list(sampled_worker), n_fault // 2))

    print(f"  Traces with worker access: {len(sampled_worker)}")
    print(f"  Traces with worker fault: {len(sampled_fault)}")
    print(f"  Traces with client fault: {len(sampled_client_fault)}")

    # Build trace → entries index
    trace_index: dict[str, list[dict]] = defaultdict(list)
    for entry in all_entries:
        trace_index[entry["trace_id"]].append(entry)

    worker_access_lines: list[str] = []
    worker_info_lines: list[str] = []
    client_info_lines: list[str] = []

    for tid in sampled_worker:
        entries = trace_index.get(tid, [])
        if not entries:
            continue
        first = entries[0]
        pod = first["pod_ip"]
        pid_tid = first["pid_tid"]

        for entry in entries:
            if tid in sampled_fault:
                fault_type, fault_msg = random.choice(FAULT_TYPES_WORKER)
                wline = generate_faulty_worker_access(entry, fault_type)
            else:
                wline = generate_worker_access(entry)
            worker_access_lines.append(wline)

        # Worker INFO log for fault traces
        if tid in sampled_fault:
            _, fault_msg = random.choice(FAULT_TYPES_WORKER)
            worker_info_lines.append(
                generate_info_line(first, fault_msg, "worker_impl.cpp:100")
            )

        # Client INFO log for a subset
        if tid in sampled_client_fault:
            _, fault_msg = random.choice(FAULT_TYPES_CLIENT)
            client_info_lines.append(
                generate_info_line(first, fault_msg, "worker_impl.cpp:100")
            )

    # Write output files
    worker_access_path = os.path.join(out_dir, "access.log")
    worker_info_path = os.path.join(out_dir, "datasystem_worker.INFO.log")
    client_info_path = os.path.join(out_dir, "ds_client_10411.INFO.log")

    with open(worker_access_path, "w") as f:
        f.write("\n".join(sorted(worker_access_lines)) + "\n")

    with open(worker_info_path, "w") as f:
        f.write("\n".join(sorted(worker_info_lines)) + "\n")

    with open(client_info_path, "w") as f:
        f.write("\n".join(sorted(client_info_lines)) + "\n")

    wc_size = os.path.getsize(worker_access_path)
    wi_size = os.path.getsize(worker_info_path)
    ci_size = os.path.getsize(client_info_path)

    print(f"\nGenerated files in {out_dir}:")
    print(f"  access.log:                  {len(worker_access_lines):>8} lines  ({wc_size:>10} bytes)")
    print(f"  datasystem_worker.INFO.log:  {len(worker_info_lines):>8} lines  ({wi_size:>10} bytes)")
    print(f"  ds_client_10411.INFO.log:    {len(client_info_lines):>8} lines  ({ci_size:>10} bytes)")

    # Write expected_result.txt
    expected_path = os.path.join(out_dir, "expected_result.txt")
    with open(expected_path, "w") as f:
        f.write(f"input: {os.path.basename(input_file)}\n")
        f.write(f"total_lines: {total_lines}\n")
        f.write(f"unique_traces: {total_traces}\n")
        f.write(f"worker_traces: {len(sampled_worker)}\n")
        f.write(f"fault_traces: {len(sampled_fault)}\n")
        f.write(f"expected_src_dst_groups: 2\n")
        f.write(f"expected_tw_groups: ~36000\n")
        f.write(f"expected_anomalous_events: >={len(sampled_fault)}\n")
        f.write(f"expected_trace_failure_events: >={len(sampled_fault)}\n")
    print(f"  expected_result.txt: written")


if __name__ == "__main__":
    main()
