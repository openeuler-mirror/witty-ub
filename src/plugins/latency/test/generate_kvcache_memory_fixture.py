"""Generate deterministic, dense KVCache logs: 100% matched and anomalous traces.

Every trace crosses four files, includes two worker access records and two
client RPCs, and exercises all Worker INFO timing categories. No noise padding.
The SDK and INFO files use independent shard permutations so a trace cannot be
completed by processing one file at a time. Only writes under the output path.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path


def records(i):
    tid = f"{i:08x}-9094-41bf-8204-e6b2ff438207"
    stamp = f"2026-05-10T12:{(i // 60) % 60:02d}:{i % 60:02d}.934807"
    header = f"{stamp} | I | benchmark.cpp:1 | pod | 3941:3949 | {tid} | cluster | "
    operation = "DS_KV_CLIENT_SET" if i % 2 else "DS_KV_CLIENT_GET"
    worker_operation = "DS_POSIX_PUBLISH" if i % 2 else "DS_POSIX_GET"
    elapsed = 10_000 + i % 50_000
    sdk = (header + f"0 | {operation} | {elapsed} | 8395125 | "
           f"{{Object_key:object-{i},timeout:0,transportType:SHM}} | \n")
    worker = "".join(header + f"0 | {worker_operation} | {cost} | 8395125 | "
                     f"{{Object_key:object-{i}}} | \n" for cost in (3200, 4800))

    def rpc(e2e, processing, execution, network):
        return (
            f"[ZMQ_RPC_FRAMEWORK_SLOW] trace_id={tid} framework_us=200 "
            f"e2e_us={e2e} client_req_framework_us=50 "
            f"remote_processing_us={processing} client_rsp_framework_us=50 "
            f"server_req_queue_us=100 server_exec_us={execution} "
            f"server_rsp_queue_us=100 network_residual_us={network}"
        )

    client = header + rpc(6000, 4300, 4100, 1400) + "\n"
    client += header + rpc(2000, 1200, 1000, 500) + "\n"
    messages = [
        "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, "
        "dst address: 10.0.0.2, urma_inflight_wr_count:3",
        "Remote get request: object=key, src=10.0.0.1, dst=10.0.0.2",
        "Worker-worker transport connection exchange success, elapsed ms: 0.1",
        "Master query done, cost:0.2ms",
        "[Get] Done, clientId:client, objects:1, transferPath:SHM, "
        "totalCost:10.0ms, inflightRemoteGet:2 exceed 1ms: {item:1.2}",
        "Worker to master rpc QueryMeta: 0.3ms",
        "ProcessGetObjectRequest: 3.5ms",
        "worker SafeObject WLock: 0.1ms",
        "[Get/RemotePull] finish, count:1, firstObjectKey:key, payload size:8395125, "
        "start remainingTime:3000, cost:2.5ms, src=10.0.0.1, dst=10.0.0.2",
        "[Get] Remote done, count:1, path:URMA, cost:2.7ms, "
        "src=10.0.0.1, dst=10.0.0.2",
        "QueryMeta done, target num 1, success num 1, cost:0.2ms",
        rpc(900, 700, 500, 100),
    ]
    info = "".join(header + message + "\n" for message in messages)
    return sdk, worker, client, info


def generate(output, traces=None, target_mib=300, shards=16, with_failures=False):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite nonempty directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    if traces is None:
        bytes_per_trace = sum(len(value.encode()) for value in records(99_999))
        traces = max(1, int(target_mib * 1024**2 / bytes_per_trace))
    total_bytes = 0
    with ExitStack() as stack:
        files = []
        for shard in range(shards):
            sdk_dir = output / f"SDK_{shard:02d}_10.0.0.1"
            worker_dir = output / f"worker_{shard:02d}_10.0.0.2"
            sdk_dir.mkdir()
            worker_dir.mkdir()
            paths = [sdk_dir / "ds_client_access.log", worker_dir / "access.log",
                     sdk_dir / "ds_client.INFO.log", worker_dir / "kvcache.INFO.log"]
            files.append([stack.enter_context(path.open("w", buffering=1024**2))
                          for path in paths])
        failures = stack.enter_context((output / "failure_trace.log").open("w", buffering=1024**2)) if with_failures else None
        for i in range(traces):
            for family, (text, shift) in enumerate(zip(records(i), (0, 7, 3, 11))):
                files[(i + shift) % shards][family].write(text)
                total_bytes += len(text.encode())
                if failures is not None:
                    for line in text.splitlines():
                        failures.write("benchmark_failure | " + line + "\n")
    manifest = {
        "traces": traces,
        "lines": traces * 17,
        "files": shards * 4,
        "bytes": total_bytes,
        "mib": total_bytes / 1024**2,
        "expected_anomaly_fraction": 1.0,
        "minimum_sdk_latency_ms": 10.0,
        "threshold_ms": 5.0,
        "records_per_trace": {"sdk_access": 1, "worker_access": 2,
                              "client_rpc": 2, "worker_info": 12},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"path": str(output), **manifest}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="/tmp/kvcache-memory-dense")
    parser.add_argument("--traces", type=int)
    parser.add_argument("--target-mib", type=float, default=300)
    parser.add_argument("--shards", type=int, default=16)
    parser.add_argument("--with-failures", action="store_true", help="Write every log line into failure_trace.log as a diagnostic hit.")
    args = parser.parse_args()
    generate(args.output, traces=args.traces, target_mib=args.target_mib, shards=args.shards, with_failures=args.with_failures)
