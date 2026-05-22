#!/usr/bin/env python3
import matplotlib.pyplot as plt
import csv
"""DataSystem log analyzer

Subcommands:
    collect Collect SDK/Worker logs from k8s pods
    parse Parse logs and correlate latency segments to CSV
    plot Generate per-node P99 latency chart from CSV
    latency Latency stats and trend chart from access log
"""

import concurrent
from dataclasses import dataclass
from gc import collect
import stat
import subprocess
import io
from datetime import datetime
import sys
import re
import os
import glob
from unittest import result
# -------------------------------------------------------------------
# Shared constants
# -------------------------------------------------------------------
SDK_GET_OPS = frozenset({"DS_KV_CLIENT_GET","DS_OBJECT_CLIENT_GET"})
WORKER_GET_OPS = frozenset({"DS_POSIX_GET"})

OBJECT_KEY_RE = re.compile(r"Object_key:\[?([^\]]+)]")
NOT_FOUND_RE = re.compile(r"\bK_NOT_FOUND\b|not\s+found|notfound",re.IGNORECASE)

URMA_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}).*?"
    r"\[URMA_ELAPSED_TOTAL\].*?cost\s+([\d.]+)ms.*?"
    r"src address:([^,]*?)\s*,\s*target address:([^,]*?)\s*,.*?"
    r"urma_inflight_wr_count:\s*(\d+)"
    )

REMOTE_GET_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}).*?"
    r"Remote get request:.*?src[= ]([^,]+,\s*dst[= ]([^,|\]])+)"
    )

REMOTE_PULL_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}).*?"
    r"Remote pull request:.*?src[= ]([^,]+,\s*dst[= ]([^,|\]])+)"
    )

URMA_LINK_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}).*?"
    r"(?:WorkerWorkerExchangeUrmaConnectInfo finish|Worker-worker transport connection exchange success),\s"
    r"elapsed ms: \s*([\d.]+)"
    )

QUERY_META_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}).*?"
    r"cost:\s*([\d.]+)ms?"
    )

LEADING_FLOAT_RE = re.compile(r"^\s*([\d.]+)(?:ms)?(?:\(|\s*$)")

COL_TIMESTAMP = 0
COL_TRACE_ID = 5
COL_STATUS_CODE = 7
COL_HANDLE = 8
COL_ELAPSED = 9
COL_SIZE = 10
COL_REQ_MSG = 11
COL_RESP_MSG = 12
COL_MIN_PARTS = 13
STATUS_OK = 0
SLOW_P99_THRESHOLD_US = 2000.0
PROGRESS_UPDATE_LINES = 100_000

class Process:
    def __init__(self, label : str, total_file = None):
        self.label  = label
        self.total_file = total_file
        self.last_len = 0
    
    def update(self, file_idx = None,path = None,line = None,row = None,match = None):
        parts = [self.label]
        if file_idx is not None and self.total_file is not None:
            parts.append(f"file {file_idx}/{self.total_file}")
        if path is not None:
            parts.append(f"path {os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}")
        if line is not None:
            parts.append(f"line {line:,}")
        if row is not None:
            parts.append(f"row {row:,}")
        if match is not None:
            parts.append(f"match {match:,}")  
        msg = " "+"|".join(parts)
        sys.stdout.write("\r"+msg+" "*max(0,self.last_len-len(parts)))
        sys.stdout.flush()
        self.last_len = len(msg)
    
    def done(self, match = None,rows = None):
        parts = [self.label,"done"]
        if rows is not None:
            parts.append(f"rows {rows:,}")
        if match is not None:
            parts.append(f"match {match:,}")
        msg = " "+"|".join(parts)
        sys.stdout.write("\r"+msg+" "*max(0,self.last_len-len(parts)))
        sys.stdout.flush()
        self.last_len = 0




def _glob_paths(patterns : list[str])-> list[str]:
    paths = []
    seen = set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            if path not in seen:
                paths.append(path)
                seen.add(path)
    return paths

def _parse_timestamp(ts : str)-> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts,fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid timestamp: {ts}")

def _open_log(path : str):
    if path.endswith(".gz"):
        import gzip
        try:
            return gzip.open(path,"rt",encoding="utf-8")
        except OSError as e:
            print(f"Warning: Corrupted gzip file {path} - {e}",file=sys.stderr)
            return io.StringIO("")
    return open(path,"r",errors="replace")


# -------------------------------------------------------------------
# COLLECT MODELS
# -------------------------------------------------------------------

def _kubectl(args,namespace,timeout=120):
    cmd = ["kubectl","--namespace",namespace]+args
    return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)

def _discover_pods(name_pattern,namespace):
    try:
        pod_name_re = re.compile(name_pattern)
    except re.error as e:
        print(f"ERROR: invalid pod name regex '{name_pattern}': {e}",file=sys.stderr)
        sys.exit(1)
    
    cp = _kubectl([
        "get","pods","--no-headers",
        "-o","custom-columns=NAME:.metadata.name,IP:.status.podIP,STATUS:.status.phase",
    ],namespace)

    if cp.returncode != 0:
        return []
    pods = []
    for line in cp.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and pod_name_re.search(parts[0]) and parts[2] == "Running":
            pods.append((parts[0],parts[1]))
    return pods

def _resolve_log_dir(pod_name,namespace,log_dir_pattern):
    if "*" not in log_dir_pattern and "?" not in log_dir_pattern:
        return log_dir_pattern
    ls_cp = _kubectl([
        "exec",pod_name,"--","bash","-c",f"ls -1d {log_dir_pattern} 2>/dev/null"
    ],namespace,timeout=15)

    if ls_cp.returncode == 0:
        lines = [l.strip() for l in ls_cp.stdout.splitlines() if l.strip()]
        if lines:
            return lines[0]
    return log_dir_pattern


def _collect_pod_logs(
    pod_name,
    pod_ip,
    dest_dir,
    patterns,
    latest_patterns,
    namespace,
    log_dir,
    start_time = None,
    end_time = None):
    os.makedirs(dest_dir,exist_ok=True)

    log_dir = _resolve_log_dir(pod_name,namespace,log_dir)

    all_files = []

    for pat in patterns:
        ls_cmd = f"ls -1 {log_dir}/{pat}{log_dir}/{pat}.gz 2>/dev/null"
        ls_cp = _kubectl(["exec",pod_name,"--","bash","-c",ls_cmd],namespace,timeout=0)
        if ls_cp.returncode == 0:
            lines = [l.strip() for l in ls_cp.stdout.splitlines() if l.strip()]
            if lines:
                all_files.append(lines[0])
    
    for pat in latest_patterns:
        ls_cmd = f"ls -1 {log_dir}/{pat}{log_dir}/{pat}.gz 2>/dev/null | head -1"
        ls_cp = _kubectl(["exec",pod_name,"--","bash","-c",ls_cmd],namespace,timeout=0)
        if ls_cp.returncode == 0:
            lines = [l.strip() for l in ls_cp.stdout.splitlines() if l.strip()]
            if lines:
                all_files.append(lines[0])

    all_files = list(set(all_files))

    if not all_files:
        print(f"No files found")
        return pod_name,0,"No files found"
    
    if start_time is None and end_time is None:
        filtered_files = []
        for f in all_files:
            # 使用stat 获取文件修改时间（秒级时间戳）
            stat_cmd = f"stat -c %Y {log_dir}/{f}"
            stat_cp = _kubectl([
                "exec",pod_name,"--","bash","-c",stat_cmd],namespace,timeout=10)
            if stat_cp.returncode == 0 and stat_cp.stdout.strip():
                try:
                    mtime = int(stat_cp.stdout.strip())
                    mtime_dt = datetime.fromtimestamp(mtime)
                    if start_time is None or mtime_dt < start_time:
                        continue
                    if end_time is None or mtime_dt > end_time:
                        continue
                    filtered_files.append(f)
                except ValueError:
                    continue
            else:
                filtered_files.append(f)
            

        all_files = filtered_files
        print(f"Time filter:{start_time} ~ {end_time},kept {len(filtered_files)} files")
    if not all_files:
        return pod_name,0,"No files match time filter"
    
    collected_count = 0
    for f in all_files:
        fname = os.path.basename(f)
        if fname.endswith(".gz"):
            fname = fname[:-3]
        out_path = os.path.join(dest_dir,fname)

        if os.path.exists(out_path):
            collected_count += 1
            continue

        try:
            if f.endswith(".gz"):
                cat_cmd = f"zcat {f} 2>/dev/null"
            else:
                cat_cmd = f"cat {f}"
            cp = _kubectl([
                "exec",pod_name,"--","bash","-c",
                cat_cmd
            ],namespace,timeout=120)
            if cp.returncode == 0 and cp.stdout:
                with open(out_path,"w",encoding="utf-8") as out:
                    out.write(cp.stdout)
                collected_count += 1
        except Exception as e:
            print(f"Warning: failed to collect {f} - {e}")
            continue
    return pod_name,collected_count,None if collected_count > 0 else "0 files collected"


def _collect_type(type_label,name_pattern,patterns,latest_patterns,namespace,out_dir,log_dir,max_parallel,start_time = None,end_time = None):
    pods = _discover_pods(name_pattern,namespace)
    if not pods:
        print(f"No Running pods found matching regex: {name_pattern} ")
        return 0
    failed = 0
    count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {}
        for pod_name,pod_ip in pods:
            dest = os.path.join(out_dir,f"{type_label}_{pod_ip}")
            print(f"{type_label} Pod: {pod_name} ({pod_ip})")
            log_dir_new = log_dir
            if type_label == "Worker":
                log_dir_new = f"{log_dir}/{pod_ip}/log"
            print(f"{dest} Patterns: {patterns} Latest_patterns: {latest_patterns} Namespace: {namespace} Log_dir: {log_dir_new}")
            if start_time is None and end_time is None:
                print(f"File time filter: {start_time} ~ {end_time}")
            fut = executor.submit(
                _collect_pod_logs,
                pod_name,
                pod_ip,
                dest,
                patterns,
                latest_patterns,
                namespace,
                log_dir_new,
                start_time,
                end_time
            )
            futures[fut] = pod_name
            count += 1

        for fut in concurrent.futures.as_completed(futures):
            pod_name,file_count,err = fut.result()
            if err:
                print(f" [WARN] {pod_name}: {err}")
                failed += 1
            else:
                print(f" [OK] {pod_name}: {file_count} file(s)")
    if failed:
        print(f" [WARN] {failed}/{count} pods failed")
    return count


def collect_cmd(args):
    if not shutil.which("kubectl"):
        print("ERROR: kubectl not found in PATH",file=sys.stderr)
        sys.exit(1)

    start_time = None
    end_time = None

    if args.start:
        try:
            for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%d %H:%M:%S.%f"):
                try:
                    start_time = datetime.strptime(args.start,fmt)
                    break
                except ValueError:
                    continue
            if start_time is None:
                raise ValueError(f"Unrecognized format: {args.start}")
            print(f"Collect files modified after: {start_time}")
        except ValueError as e:
            print(f"ERROR: invalid start time format: {e}",file=sys.stderr)
            print("  Expected: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS",file=sys.stderr)
            sys.exit(1)
        
    if args.end:
        try:
            for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%d %H:%M:%S.%f"):
                try:
                    end_time = datetime.strptime(args.end,fmt)
                    break
                except ValueError:
                    continue
            if end_time is None:
                raise ValueError(f"Unrecognized format: {args.end}")
            print(f"Collect files modified before: {end_time}")
        except ValueError as e:
            print(f"ERROR: invalid end time format: {e}",file=sys.stderr)
            print("  Expected: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS",file=sys.stderr)
            sys.exit(1)

    if start_time is None and end_time is None and start_time > end_time:
        print("ERROR: --start time must be before --end time",file=sys.stderr)
        sys.exit(1)

    if start_time is None and end_time is None:
        print(f"Collecting logs with file modification time fileter: {start_time} ~ {end_time}")
        sdk_log_pattern = ["ds_client.INFO.log","ds_client_INFO.log.gz",
        "ds_client_INFO.*.log.gz",
        "ds_client_*.INFO.log","ds_client_*.INFO.log.gz",
        "ds_client_access.log",
        "ds_client_access.log.gz",
        "ds_client_access.*.log.gz",
        "ds_client.access_*.log",
        "ds_client.access_*.log.gz",
        ]
    print(f"=== Collecting SDK logs (sdk_log_dir: {args.sdk_log_dir}) ===")
    print(f"===Collecting SDK logs (pod regex: {args.sdk_prefix})===")
    sdk_count = _collect_type(
        "SDK",
        args.sdk_prefix,
        sdk_log_pattern,
        [],
        args.namespace,
        args.output_dir,
        args.sdk_log_dir,
        args.parallel,
        start_time,
        end_time
    )

    print(f"=== Collecting Worker logs (worker_log_dir: {args.worker_log_dir}) ===")
    print(f"===Collecting Worker logs (pod regex: {args.worker_prefix})===")
    worker_log_pattern = [
        "access.log",
        "access.log.gz",
        "datasystem_worker.INFO.log",
        "datasystem_worker.INFO.log.gz",
        "kvcache.INFO.log",
        "kvcache.INFO.log.gz",
        "resource.log",
        "resource.log.gz",
        "pidstat.log",
        "pidstat.log.gz",
        ]
    worker_count = _collect_type(
        "Worker",
        args.worker_prefix,
        worker_log_pattern,
        [],
        args.namespace,
        args.output_dir,
        args.worker_log_dir,
        args.parallel,
        start_time,
        end_time
    )

    print(f"\n=== Collection summary ===\n"
        f"SDK: {sdk_count} pods, {sdk_count * len(sdk_log_pattern)} files\n"
        f"Worker: {worker_count} pods, {worker_count * len(worker_log_pattern)} files\n"
        f"Total: {sdk_count + worker_count} pods, "
        f"{(sdk_count * len(sdk_log_pattern)) + (worker_count * len(worker_log_pattern))} files")
    
# ==================================================================
# PARSING MODELS
# ==================================================================

@dataclass
class SdkGetEntry:
    timestamp: datetime
    operation: str
    total_time_us:int
    data_size: str
    object_key: str
    trace_id: str
    pod_ip: str
    status_code: int
    resp_msg: str

@dataclass
class WorkerGetEntry:
    timestamp: datetime
    worker_time_us:int
    object_key: str
    trace_id: str
    pod_ip: str
    status_code: int
    resp_msg: str

@dataclass
class UrmaEntry:
    timestamp: datetime
    elapsed_ms: float
    src_addr: str
    dst_addr: str
    inflight_count: int
    pod_ip: str
    trace_id: str

@dataclass
class RemotePullEntry:
    timestamp: datetime
    object_key: str
    request_size: str
    read_src_addr: str
    read_dst_addr: str
    pod_ip: str
    trace_id: str

@dataclass
class LinkEntry:
    timestamp: datetime
    elapsed_ms: float
    pod_ip: str
    trace_id: str

@dataclass
class QueryMetaEntry:
    timestamp: datetime
    elapsed_ms: float
    pod_ip: str
    trace_id: str

def _parse_status_code(raw: str)-> int:
    if raw.isdigit():
        return int(raw)
    return STATUS_OK


def _is_success_status(status_code: int,resp_msg: str)-> bool:
    return status_code == STATUS_OK and NOT_FOUND_RE.search(resp_msg) is None

def _infer_local_host_port(pod_ip: str,peer_addr: str)-> str:
    if not pod_ip:
        return ""
    port = ""
    if ":" in peer_addr:
        port = peer_addr.split(":")[-1].strip()
    return f"{pod_ip}:{port}" if port else pod_ip

def _parse_access_line(line: str):
    if len(line) < 80 or line[0] != "2":
        return None
    parts = line.split()
    if len(parts) < COL_MIN_PARTS:
        return None
    handle = parts[COL_HANDLE].strip()
    return {
        "timestamp": parts[COL_TIMESTAMP].strip(),
        "trace_id": parts[COL_TRACE_ID].strip(),
        "status_code": parts[COL_STATUS_CODE].strip(),
        "handle": handle,
        "elapsed": parts[COL_ELAPSED].strip(),
        "size": parts[COL_SIZE].strip(),
        "req_msg": parts[COL_REQ_MSG].strip(),
        "resp_msg": parts[COL_RESP_MSG].strip(),
    }

def _extract_object_key(req_msg: str)-> str:
    match = OBJECT_KEY_RE.search(req_msg or "")
    return match.group(1) if match else ""

def _extract_trace_id_from_log_line(line: str)-> str:
    uuid_pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",re.IGNORECASE)
    match = uuid_pattern.search(line)
    return match.group(0) if match else ""

def _parse_sdk_logs(
    input_dir: str, 
    start_time: datetime = None, 
    end_time: datetime = None, 
    min_total_time_ms: float = None
    )-> list[SdkGetEntry]:
    entries = []
    pattern = [
        os.path.join(input_dir,"SDK_*","ds_client_access_*.log"),
        os.path.join(input_dir,"SDK_*","ds_client_access_*.log.gz"),
        os.path.join(input_dir,"SDK_*","ds_client.log"),
        os.path.join(input_dir,"SDK_*","ds_client.log.gz"),
        os.path.join(input_dir,"SDK_*","ds_client_access.log"),
        os.path.join(input_dir,"SDK_*","ds_client_access.*.log.gz"),
    ]
    paths = _glob_paths(pattern)
    progress = Process("SDK access parse",len(paths))
    filtered_by_time = 0
    filtered_by_total = 0

    min_total_time_us = min_total_time_ms * 1000 if min_total_time_ms is not None else None

    for file_idx, path in enumerate(paths,1):
        pod_ip = os.path.basename(os.path.dirname(path)).replace("SDK_","")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        with _open_log(path) as f:
            for line_no, line in enumerate(f,1):
                progress.update(file_idx,path,lines = line_no,match = len(entries))
            parsed = _parse_access_line(line)
            if not parsed or parsed["handle"] != SDK_GET_OPS:
                continue
            if start_time or end_time:
                ts = _parse_timestamp(parsed["timestamp"])
                if (start_time and ts < start_time) or (end_time and ts > end_time):
                    filtered_by_time += 1
                    continue
            
            total_time_us = int(float(parsed["elapsed"]))
            if min_total_time_us is not None and total_time_us < min_total_time_us:
                filtered_by_total += 1
                continue
            
            try:
                elapsed = int(parsed["elapsed"])
            except ValueError:
                continue

            if min_total_time_us is not None and elapsed < min_total_time_us:
                filtered_by_total += 1
                continue

            trace_id = parsed["trace_id"]
            if not trace_id:
                continue
            entries.append(SdkGetEntry(
                timestamp = ts,
                operation = parsed["handle"],
                total_time_us = total_time_us,
                data_size = parsed["size"],
                object_key = _extract_object_key(parsed["req_msg"]),
                trace_id = trace_id,
                pod_ip = pod_ip,
                status_code = _parse_status_code(parsed["status_code"]),
                resp_msg = parsed["resp_msg"],
            ))
        progress.update(file_idx,path,match = len(entries))
    
    if filtered_by_time > 0:
        print(f"Filtered out {filtered_by_time} entries by time")
    if filtered_by_total > 0:
        print(f"Filtered out {filtered_by_total} entries by total time")

    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries

def _parse_worker_access_logs(
    input_dir: str, 
    start_time: datetime = None, 
    end_time: datetime = None, 
    )-> list[WorkerGetEntry]:
    entries = []
    pattern = [
        os.path.join(input_dir,"*Worker_*","access.log"),
        os.path.join(input_dir,"*Worker_*","access.log.gz"),
    ]
    paths = _glob_paths(pattern)
    progress = Process("Worker access parse",len(paths))
    filtered_by_time = 0

    for file_idx, path in enumerate(paths,1):
        _dir = os.path.basename(os.path.dirname(path))
        pod_ip = _dir.removeprefix("dsworker_").removesuffix("worker_")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        with _open_log(path) as f:
            for line_no, line in enumerate(f,1):
                if line_no % PROGRESS_UPDATE_LINES == 0:
                    progress.update(file_idx,path,lines = line_no,match = len(entries))
                parsed = _parse_access_line(line)
                if not parsed or parsed["handle"] != WORKER_GET_OPS:
                    continue
                if start_time or end_time:
                    ts = _parse_timestamp(parsed["timestamp"])
                    if (start_time and ts < start_time) or (end_time and ts > end_time):
                        filtered_by_time += 1
                        continue
                
                try:
                    elapsed = int(parsed["elapsed"])
                except ValueError:
                    continue
                
                trace_id = parsed["trace_id"]
                if not trace_id:
                    continue
                entries.append(WorkerGetEntry(
                    timestamp = _parse_timestamp(parsed["timestamp"]),
                    worker_time_us = elapsed,
                    object_key = _extract_object_key(parsed["req_msg"]),
                    trace_id = trace_id,
                    pod_ip = pod_ip,
                    status_code = _parse_status_code(parsed["status_code"]),
                    resp_msg = parsed["resp_msg"],
                ))
        progress.update(file_idx,path,match = len(entries))
    
    if filtered_by_time > 0:
        print(f"Filtered out {filtered_by_time} entries by time")

    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries

def _parse_worker_urma_logs(
    input_dir: str, 
    )-> list[UrmaEntry]:
    entries = []
    paths = _glob_paths([
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*"),
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*.gz"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*.gz"),
    ])
    progress = Process("Worker urma parse",len(paths))
    for file_idx, path in enumerate(paths,1):
        _dir = os.path.basename(os.path.dirname(path))
        pod_ip = _dir.removeprefix("dsworker_").removesuffix("worker_")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        try:
            with _open_log(path) as f:
                for line_no, line in enumerate(f, 1):
                    if line_no % PROGRESS_UPDATE_LINES == 0:
                        progress.update(file_idx, path, lines=line_no, matched=len(entries))
                    if 'URMA_ELAPSED_TOTAL' not in line:
                        continue
                    m = URMA_RE.search(line)
                    if not m:
                        continue
                    ts_str, elapsed_ms, src, dst, inflight = m.groups()
                    trace_id=_extract_trace_id_from_log_line(line)
                    entries.append(UrmaEntry(
                        timestamp=_parse_timestamp(ts_str),
                        elapsed_ms=float(elapsed_ms),
                        src_addr=src.strip(),
                        dst_addr=dst.strip(),
                        inflight_count=int(inflight),
                        pod_ip=pod_ip,
                        trace_id=trace_id,
                    ))
        except EOFError as e:
            print(f"WARNING: Skipping corrupted file {path} : {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"WARNING: Error reading {path} - {e}",file=sys.stderr)
            continue
        progress.update(file_idx,path,match = len(entries))
    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries

def _parse_worker_remote_pull_logs(
    input_dir: str, 
    )-> list[RemotePullEntry]:
    entries = []
    paths = _glob_paths([
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*"),
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*.gz"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*.gz"),
    ])
    progress = Process("Worker remote pull parse",len(paths))
    for file_idx, path in enumerate(paths,1):
        _dir = os.path.basename(os.path.dirname(path))
        pod_ip = _dir.removeprefix("dsworker_").removesuffix("worker_")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        try:
            with _open_log(path) as f:
                for line_no, line in enumerate(f,1):
                    if line_no % PROGRESS_UPDATE_LINES == 0:
                        progress.update(file_idx,path,lines = line_no,match = len(entries))
                    if "Remote get request" in line:
                        m = REMOTE_GET_RE.search(line)
                        if not m:
                            continue
                        ts_str,src_addr,dst_addr = m.groups()
                        trace_id = _extract_trace_id_from_log_line(line)
                        if not trace_id:
                            continue
                        
                        entries.append(RemotePullEntry(
                            timestamp = _parse_timestamp(ts_str),
                            object_key = "",
                            request_size = "",
                            read_src_addr = src_addr.strip(),
                            read_dst_addr = dst_addr.strip(),
                            pod_ip = pod_ip,
                            trace_id = _extract_trace_id_from_log_line(line),
                        ))
                        continue
                    if "Processing pull object[" in line:
                        m = REMOTE_PULL_RE.search(line)
                        if not m:
                            continue
                        ts_str,object_key,src_addr,dst_addr = m.groups()
                        src_addr = src_addr.strip()
                        dst_addr = dst_addr.strip()
                        entries.append(RemotePullEntry(
                            timestamp = _parse_timestamp(ts_str),
                            object_key = object_key.strip(),
                            request_size = "",
                            read_src_addr = src_addr,
                            read_dst_addr = dst_addr,
                            pod_ip = pod_ip,
                            trace_id = _extract_trace_id_from_log_line(line),
                        ))
        except EOFError as e:
            print(f"WARNING: Skipping corrupted file {path} : {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"WARNING: Error reading {path} - {e}",file=sys.stderr)
            continue
        progress.update(file_idx,path,match = len(entries))
    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries
                        
def _parse_worker_link_logs(input_dir:str)->list[LinkEntry]:
    entries = []
    paths = _glob_paths([
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*"),
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*.gz"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*.gz"),
    ])
    progress = Process("Worker link parse",len(paths))
    for file_idx, path in enumerate(paths,1):
        _dir = os.path.basename(os.path.dirname(path))
        pod_ip = _dir.removeprefix("dsworker_").removesuffix("worker_")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        try:
            with _open_log(path) as f:
                for line_no, line in enumerate(f,1):
                    if line_no % PROGRESS_UPDATE_LINES == 0:
                        progress.update(file_idx,path,lines = line_no,match = len(entries))
                    if 'elapsed ms:' not in line:
                        continue
                    if ('WorkerWorkerExchangeUrmaConnectInfo finish' not in line
                            and 'Worker-worker transport connection exchange success' not in line):
                        continue
                    if 'WorkerWorkerExchangeUrmaConnectInfo finish' in line and 'status=code: [OK]' not in line:
                        continue
                    m = URMA_LINK_RE.search(line)
                    if not m:
                        continue
                    ts_str, elapsed_ms = m.groups()
                    trace_id = _extract_trace_id_from_log_line(line)
                    if not trace_id:
                        continue
                    entries.append(LinkEntry(
                        timestamp=_parse_timestamp(ts_str),
                        elapsed_ms=float(elapsed_ms),
                        pod_ip=pod_ip,
                        trace_id=trace_id,
                    ))
        except EOFError as e:
            print(f"WARNING: Skipping corrupted file {path} : {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"WARNING: Error reading {path} - {e}",file=sys.stderr)
            continue
        progress.update(file_idx,path,match = len(entries))
    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries

def _parse_worker_query_meta_logs(input_dir:str)->list[QueryMetaEntry]:
    entries = []
    paths = _glob_paths([
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*"),
        os.path.join(input_dir,"*Worker_*","datasystem_worker.INFO.*.gz"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*"),
        os.path.join(input_dir,"*Worker_*","kvcache.INFO.*.gz"),
    ])
    progress = Process("Worker query meta parse",len(paths))
    for file_idx, path in enumerate(paths,1):
        _dir = os.path.basename(os.path.dirname(path))
        pod_ip = _dir.removeprefix("dsworker_").removesuffix("worker_")
        progress.update(file_idx,path,lines = 0,match = len(entries))
        try:
            with _open_log(path) as f:
                for line_no, line in enumerate(f, 1):
                    if line_no % PROGRESS_UPDATE_LINES == 0:
                        progress.update(file_idx, path, lines=line_no, matched=len(entries))
                    # 修改关键字识别
                    if 'Master query done' not in line:
                        continue
                    m = QUERY_META_RE.search(line)
                    if not m:
                        continue
                    ts_str, elapsed_ms = m.groups()
                    trace_id = _extract_trace_id_from_log_line(line)
                    if not trace_id:
                        continue
                    entries.append(QueryMetaEntry(
                        timestamp=_parse_timestamp(ts_str),
                        elapsed_ms=float(elapsed_ms),
                        pod_ip=pod_ip,
                        trace_id=trace_id,
                    ))
        except EOFError as e:
            print(f"WARNING: Skipping corrupted file {path} : {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"WARNING: Error reading {path} - {e}",file=sys.stderr)
            continue
        progress.update(file_idx,path,match = len(entries))
    entries.sort(key = lambda x: x.timestamp)
    progress.done(match = len(entries))
    return entries  

def _correlate_sdk_worker(
    sdk_entries: list[SdkGetEntry], 
    worker_entries: list[WorkerGetEntry],
    time_window_ms,
    no_time_window=False
    ):
    worker_by_trace: dict[str, list[WorkerGetEntry]] = {}
    for worker in worker_entries:
        worker_by_trace.setdefault(worker.trace_id,[]).append(worker)
     
    window_us = time_window_ms * 1000
    results = {}
    for i,sdk in enumerate(sdk_entries):
        candidates = worker_by_trace.get(sdk.trace_id,[])
        if not candidates:
            continue
        if no_time_window:
            key_matched = [w for w in candidates if w.object_key == sdk.object_key]
            choices = key_matched or candidates
            results[i] = min(
                choices,key = lambda w: abs(w.worker_time_us - sdk.total_time_us).total_seconds()
                )
            continue
        best = None
        best_dt = None

        for w in candidates:
            dt_us = abs(w.worker_time_us - sdk.total_time_us).total_seconds()
            if 0 <= dt_us <= window_us:
                if best_dt is None or dt_us < best_dt:
                    best = w
                    best_dt = dt_us
        if best is not None:
            results[i] = best
            continue

        key_matched = [w for w in candidates if w.object_key and w.object_key == sdk.object_key]
        if len(key_matched) == 0:
            results[i] = key_matched[0]
        elif len(candidates) == 1:
            results[i] = candidates[0]
    return results


def _format_unmatched_reason(
    sdk: SdkGetEntry, 
    candidates: list[WorkerGetEntry],
    time_window_ms:int,
    no_time_window:bool
    )-> str:
    if not _is_success_status(sdk.status_code,sdk.resp_msg):
        return _format_failure_remark("SDK",sdk.status_code,sdk.resp_msg)
    if not candidates:
        return "No Worker entries found for this trace ID"
    if no_time_window:
        return f"No Worker entries found for this trace ID with object key {sdk.object_key}"
    dt_values_ms = [(w.timestamp - sdk.timestamp).total_seconds() * 1000 for w in candidates]
    closest = min(dt_values_ms,key = lambda x: abs(x))
    key_match_count = sum(1 for w in candidates if w.object_key and w.object_key == sdk.object_key)
    key_info = f" object_key_matched_candidates = {key_match_count}/{len(candidates)} "
    if all(dt < 0 for dt in dt_values_ms):
        return (f" all worker candidates are earlier than SDK timestamp;closest_dt={closest:.3f}ms"
                f"{key_info};likely clock skew")
    if all(dt > time_window_ms for dt in dt_values_ms):
        return (f" all worker candidates are later than SDK timestamp by {closest:.3f}ms;"
                f"window={time_window_ms:.3f}ms{key_info}")
    
    return (f"worker candidates exist but none within [0,{time_window_ms}]ms;"
            f"closest_dt={closest:.3f}ms{key_info}")

def _print_unmatched_sdk_samples(
    sdk_entries: list[SdkGetEntry],
    worker_entries: list[WorkerGetEntry],
    sdk_worker_map,
    time_window_ms:int,
    no_time_window:bool,
    limit:int = 10
    ):
    unmatched_total = len(sdk_entries) - len(sdk_worker_map)
    if unmatched_total <= 0:
        return
    worker_by_trace: dict[str, list[WorkerGetEntry]] = {}
    for worker in worker_entries:
        worker_by_trace.setdefault(worker.trace_id,[]).append(worker)
    print(f" Unmatched SDK samples: {unmatched_total}")
    printed = 0
    for i,sdk in enumerate(sdk_entries):
        if i in sdk_worker_map:
            continue
        candidates = worker_by_trace.get(sdk.trace_id,[])
        reason = _format_unmatched_reason(sdk,candidates,time_window_ms,no_time_window)
        print(f" trace_id={sdk.trace_id},sdk_time={sdk.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")},"
        f"sdk_pod = {sdk.pod_ip},op={sdk.operation},object_key={sdk.object_key}"
        f"worker_candidates={len(candidates)} reason={reason}")
        printed += 1
        if printed >= limit:
            break
    
def _match_urma_by_remote_pull(urma_candidates: list[UrmaEntry],remote_pulls: list[RemotePullEntry])-> list[UrmaEntry]:
    if not urma_candidates or not remote_pulls:
        return []
    write_endpoints = set()
    for pull in remote_pulls:
        if not pull.read_src_addr or not pull.read_dst_addr:
            continue
        write_endpoints.add((pull.read_dst_addr,pull.read_src_addr))
        write_endpoints.add((pull.read_src_addr,pull.read_dst_addr))
    
    if not write_endpoints:
        return []
    return [u for u in urma_candidates if (u.src_addr,u.dst_addr) in write_endpoints]

def _dedup_urma_entries(*groups: list[UrmaEntry])-> list[UrmaEntry]:
    results = []
    seen = set()
    for group in groups:
        for u in group:
            key = (u.trace_id,u.src_addr,u.dst_addr)
            if key in seen:
                continue
            seen.add(key)
            results.append(u)
    return results

def _correlate_sdk_urma(
    sdk_entries: list[SdkGetEntry],
    urma_entries: list[UrmaEntry],
    )->dict[int,list[UrmaEntry]]:
    urma_index:dict[tuple[str,str],list[UrmaEntry]] = {}
    for u in urma_entries:
        key = (u.src_addr,u.dst_addr)
        urma_index.setdefault(key,[]).append(u)
    
    for urma_list in urma_index.values():
        urma_list.sort(key = lambda x: x.timestamp)

    results = {}
    for i,sdk in enumerate(sdk_entries):
        key = (sdk.pod_ip,sdk.trace_id)
        if key in urma_index:
            results[i] = urma_index[key]
    return results

def _correlate_worker_urma(
    worker_entries: list[WorkerGetEntry],
    urma_entries: list[UrmaEntry],
    worker_remote_pull_map=None
    ):
    traced_urma_by_pod_trace: dict[tuple[str,str],list[UrmaEntry]] = {}
    traced_urma_by_trace:dict[str,list[UrmaEntry]] = {}

    untraced_urma_by_pod:dict[str,tuple[list[UrmaEntry],list[datetime]]] = {}
    worker_remote_pull_map = worker_remote_pull_map or {}

    for u in urma_entries:
        if u.trace_id:
            traced_urma_by_pod_trace.setdefault((u.pod_ip,u.trace_id),[]).append(u)
            traced_urma_by_trace.setdefault(u.trace_id,[]).append(u)
            continue
        if u.pod_ip not in untraced_urma_by_pod:
            entries = []
            untraced_urma_by_pod[u.pod_ip] = (entries,None)
        untraced_urma_by_pod[u.pod_ip][0].append(u)
    
    for entries in traced_urma_by_pod_trace.values():
        entries.sort(key = lambda x: x.timestamp)
    for entries in traced_urma_by_trace.values():
        entries.sort(key = lambda x: x.timestamp)
    for pod_ip in untraced_urma_by_pod:
        entries = untraced_urma_by_pod[pod_ip][0]
        entries.sort(key = lambda x: x.timestamp)
        untraced_urma_by_pod[pod_ip] = (entries,[e.timestamp for e in entries])

    results = {}
    worker_worker_results = {}

    for i,w in enumerate(worker_entries):
        remote_matched = _match_urma_by_remote_pull(
            untraced_urma_by_trace.get(w.trace_id,[]),
            worker_remote_pull_map.get(i,[])
        )

        if remote_matched:
            worker_worker_results[i] = remote_matched
        
        untraced = []

        cached = untraced_urma_by_pod.get(w.pod_ip,[])
        if cached:
            urma_list,urma_ts = cached
            w_end = w.timestamp + timedelta(milliseconds = w.worker_time_us)
            lo = bisect_left(urma_ts,w.timestamp)
            hi = bisect_right(urma_ts,w_end)
            if lo < hi:
                untraced = urma_list[lo:hi]
        
        matched = _dedup_urma_entries(remote_matched,untraced)
        if matched:
            results[i] = matched
    return results,worker_worker_results

def _correlate_worker_remote_pulls(
    worker_entries: list[WorkerGetEntry],
    remote_pull_entries: list[RemotePullEntry],
    ):

    pulls_by_trace: dict[str,list[RemotePullEntry]] = {}
    for pull in remote_pull_entries:
        pulls_by_trace.setdefault(pull.trace_id,[]).append(pull)
    results = {}
    for i,w in enumerate(worker_entries):
        candidates = pulls_by_trace.get(w.trace_id,[])
        if not candidates:
            continue
        key_matched = [p for p in candidates if not w.object_key or p.object_key == w.object_key]
        choices = key_matched or candidates
        if choices:
            results[i] = choices
    return results

def _correlate_worker_link(
    worker_entries: list[WorkerGetEntry],
    link_entries: list[LinkEntry],
    ):
    links_by_trace: dict[str,list[LinkEntry]] = {}
    links_by_pod_trace: dict[tuple[str,str],list[LinkEntry]] = {}
    for link in link_entries:
        links_by_trace.setdefault(link.trace_id,[]).append(link)
        links_by_pod_trace.setdefault((link.pod_ip,link.trace_id),[]).append(link)
    results = {}
    for i,w in enumerate(worker_entries):
        candidates = links_by_trace.get(w.trace_id,[])
        if not candidates:
            candidates = links_by_pod_trace.get((w.pod_ip,w.trace_id),[])
        if candidates:
            results[i] = max(link.elapsed_ms for link in candidates)
    return results


def _correlate_worker_query_meta(
    worker_entries: list[WorkerGetEntry],
    query_meta_entries: list[QueryMetaEntry],
    ):

    metas_by_pod_trace: dict[tuple[str,str],list[QueryMetaEntry]] = {}
    for meta in query_meta_entries:
        metas_by_pod_trace.setdefault((meta.pod_ip,meta.trace_id),[]).append(meta)
    
    for entry in metas_by_pod_trace.values():
        entry.sort(key = lambda x: x.timestamp)
    results = {}
    for i,w in enumerate(worker_entries):
        candidates = metas_by_pod_trace.get((w.pod_ip,w.trace_id),[])
        if not candidates:
            continue
        start = w.timestamp - timedelta(milliseconds = w.worker_time_us)
        in_range = [entry for entry in candidates if start <= entry.timestamp <= w.timestamp]
        choices = in_range or candidates
        
        best = min(choices,key = lambda x: abs(x.timestamp - w.timestamp).total_seconds())
        results[i] = best.elapsed_ms
    return results


def _join_unique(values)->str:
    seen = set()
    result = []
    for v in values:
        value = str(v).strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return ",".join(result)

def _serialize_urma(urma_list:list[UrmaEntry])->tuple[str,str,str,str]:
    if not urma_list:
        return ("","","","")
    return(
        ";".join(f"u.elapsed_ms={u.elapsed_ms:.3f}" for u in urma_list),
        _join_unique(str(u.inflight_count) for u in urma_list),
        _join_unique(u.src_addr for u in urma_list),
        _join_unique(u.dst_addr for u in urma_list),
    )


def _serialize_urma_elapsed(urma_list:list[UrmaEntry])->str:
    if not urma_list:
        return ""
    return(
        ";".join(f"u.elapsed_ms={u.elapsed_ms:.3f}" for u in urma_list),
    )

def _serialize_remote_pull_as_urma_endpoints(remote_pulls:list[RemotePullEntry])->tuple[str,str]:
    if not remote_pulls:
        return "",""
    write_src = _join_unique(u.read_src_addr for u in remote_pulls)
    write_dst = _join_unique(u.read_dst_addr for u in remote_pulls)
    if write_src and write_dst:
        return write_src,write_dst
    return "",""

def _format_link_ms(link_ms:float)->str:
    return f"{link_ms:.3f}" if link_ms is not None else ""

def _format_optional_ms(elapsed_ms:float)->str:
    return f"{elapsed_ms:.3f}" if elapsed_ms is not None else ""

def _format_failure_remark(source:str,status_code:int,resp_msg:str)->str:
    msg = resp_msg.strip() if resp_msg else ""
    if status_code == STATUS_OK and NOT_FOUND_RE.match(msg):
        return f"{source} not found,{msg}"
    if msg:
        return f"{source} failed with status_code={status_code} resp_msg={msg}"
    return f"{source} failed with status_code={status_code}"

def _merge_remark(current:str,extra:str)->str:
    if not current:
        return extra
    if current == "OK":
        return f"OK;{extra}" if extra != "OK" else current
    if not extra or extra == "OK":
        return current
    return f"{current};{extra}"

def _build_worker_urma_empty_reasons(
    worker_entries: list[WorkerGetEntry],
    urma_entries: list[UrmaEntry],
    worker_urma_map,
    )->dict[int,str]:
    
    urma_count_by_pod: dict[str,int] = defaultdict(int)
    traced_count_by_pod: dict[str,int] = defaultdict(int)
    untraced_count_by_pod: dict[str,int] = defaultdict(int)
    traced_count_by_pod_trace: dict[tuple[str,str],int] = defaultdict(int)

    for u in urma_entries:
        urma_count_by_pod[u.pod_ip] += 1
        if u.trace_id:
            traced_count_by_pod[u.pod_ip] += 1
            traced_count_by_pod_trace[(u.pod_ip,u.trace_id)] += 1
        else:
            untraced_count_by_pod[u.pod_ip] += 1

    reasons = {}
    for i,w in enumerate(worker_entries):
        if i in worker_urma_map:
            continue
        if urma_count_by_pod[w.pod_ip] == 0:
            reasons[i] = "No Urma entries found for this trace ID"
        elif traced_count_by_pod_trace[(w.pod_ip,w.trace_id)] == 0 and traced_count_by_pod[w.pod_ip] > 0:
            if untraced_count_by_pod[w.pod_ip] > 0:
                reasons[i] = "No Urma entries found for this trace ID with object key"
            else:
                reasons[i] = "No Urma entries found for this trace ID"
        else:
            reasons[i] = "No Urma entries found for this trace ID"
    return reasons

def _write_csv(
    sdk_entries,
    sdk_worker_map,
    worker_urma_map,
    sdk_urma_map,
    worker_worker_urma_map,
    worker_remote_pull_map,
    worker_link_map,
    worker_query_meta_map,
    worker_idx_map,
    worker_urma_empty_reasons,
    output_path,
    keep_trace_ids=None,
    filter_threshold_ms=0,
    ):
    headers = [
        'time', 'Operation', 'TraceId', 'TotalTime(us)', 'DataSize', 'pod_ip',
        'Client2WorkerTime(us)', 'WorkerQueryMetaTime(ms)', 'URMA_LINK(ms)', 'URMA_TOTAL(ms)',
        'ClientWorkerURMA(ms)', 'WorkerWorkerURMA(ms)', 'urma_inflight_wr_count',
        'urma_write_source', 'urma_write_dst',
        'Remarks',
    ]

    filtered_count = 0
    total_count = 0

    with open(output_path,"w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        neg_count = 0
        progress = _Progress("Write CSV",len(sdk_entries))
        for i,sdk in enumerate(sdk_entries):
            if i and i % PROGRESS_UPDATE_LINES == 0:
                progress.update(rows = i)
            total_count += 1

            if keep_trace_ids is not None and sdk.trace_id not in keep_trace_ids:
                filtered_count += 1
                continue
            worker = sdk_worker_map.get(i)
            client2worker = ""
            worker_query_meta = ""
            urma_link = ""
            urma_total = ""
            client_worker_urma = ""
            worker_worker_urma = ""
            urma_inflight_count = ""
            urma_src = ""
            urma_dst = ""
            remark = ""

            sdk_success = _is_success_status(sdk.status_code,sdk.resp_msg)

            if worker:
                client2worker = sdk.total_time_us - worker.worker_time_us
                if client2worker < 0:
                    neg_count += 1
                    remark = _merge_remark(remark,"Client2WorkerTime(us) < 0")

                worker_success = _is_success_status(worker.status_code,worker.resp_msg)
                if not sdk_success:
                    remark = _merge_remark(remark,_format_failure_remark("SDK",sdk.status_code,sdk.resp_msg))
                if not worker_success:
                    remark = _merge_remark(remark,_format_failure_remark("Worker",worker.status_code,worker.resp_msg))

                w_idx = worker_idx_map.get(i)

                if w_idx is not None:
                    worker_query_meta = _format_optional_ms(worker_query_meta_map.get(w_idx))
                    
                    link_ms = worker_link_map.get(w_idx)
                    urma_link = _format_link_ms(link_ms)

                    client_worker_urma = _serialize_urma_elapsed(sdk_urma_map.get(w_idx))

                    worker_worker_urma = _serialize_urma_elapsed(worker_worker_urma_map.get(w_idx,[]))

                    urma_list = worker_urma_map.get(w_idx,[])

                    if urma_list:
                        urma_total,urma_inflight,urma_src,urma_dst = _serialize_urma(urma_list)

                    elif sdk_success and worker_success:
                        urma_total = "1"
                        urma_src,urma_dst = _serialize_remote_pull_as_urma_endpoints(worker_remote_pull_map.get(w_idx,[]))

                    elif not remark:
                        remark = _merge_remark(remark,worker_urma_empty_reasons.get(w_idx,""),"URMA fields empty: no matching URMA entry")
            else:
                if not sdk_success:
                    remark = _format_failure_remark("SDK",sdk.status_code,sdk.resp_msg)
                client_worker_urma = _serialize_urma_elapsed(sdk_urma_map.get(w_idx,[]))

            writer.writerow([
                sdk.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                sdk.operation,
                sdk.trace_id,
                sdk.total_time_us,
                sdk.data_size,
                sdk.pod_ip,
                client2worker,
                worker_query_meta,
                urma_link,
                urma_total,
                client_worker_urma,
                worker_worker_urma,
                urma_inflight,
                urma_src,
                urma_dst,
                remark or "OK",
            ])
        progress.done(rows=total_count - filtered_count)

    if keep_trace_ids is not None and filtered_count > 0:
        print(f"Filtered: kept {total_count - filtered_count}/{total_count} rows (removed {filtered_count} rows with P99 <= {filter_threshold_ms:.3f}ms)")
    if neg_count > 0:
        print(f"Warning: {neg_count} entries had negative Client2WorkerTime(us)"
        f"(worker_time > sdk_time,measurement skew)")

    return total_count - filtered_count

def _write_worker_only_csv(
    worker_entries,
    worker_urma_map,
    worker_worker_urma_map,
    worker_remote_pull_map,
    worker_link_map,
    worker_query_meta_map,
    worker_idx_map,
    worker_urma_empty_reasons,
    output_path,
    keep_trace_ids=None,
    filter_threshold_ms=0,
    ):
    headers = [
        'time', 'Operation', 'TraceId', 'TotalTime(us)', 'DataSize', 'pod_ip',
        'Client2WorkerTime(us)', 'WorkerQueryMetaTime(ms)', 'URMA_LINK(ms)', 'URMA_TOTAL(ms)',
        'ClientWorkerURMA(ms)', 'WorkerWorkerURMA(ms)', 'urma_inflight_wr_count',
        'urma_write_source', 'urma_write_dst',
        'Remarks',
    ]

    with open(output_path,"w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        progress = _Progress("Write CSV",len(worker_entries))
        for i,w in enumerate(worker_entries):
            if i and i % PROGRESS_UPDATE_LINES == 0:
                progress.update(rows = i)
            urma_list = worker_urma_map.get(i,[])
            urma_total,urma_inflight,urma_src,urma_dst = _serialize_urma(urma_list)
            if not urma_inflight:
                urma_inflight = "0"
            worker_query_meta = _format_optional_ms(worker_query_meta_map.get(i))
            urma_link = _format_link_ms(worker_link_map.get(i))
            client_worker_urma = ""
            worker_worker_urma = _serialize_urma_elapsed(worker_worker_urma_map.get(i,[]))
            if not _is_success_status(w.status_code,w.resp_msg):
                remark = _format_failure_remark("Worker",w.status_code,w.resp_msg)
            elif urma_list:
                remark = ""
            else:
                urma_total = "1"
                urma_src,urma_dst = _serialize_remote_pull_as_urma_endpoints(worker_remote_pull_map.get(i,[]))
                remark = ""
            writer.writerow([
                w.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "DS_POSIX_GET",
                w.trace_id,
                w.worker_time_us,
                "",
                w.pod_ip,
                "",
                worker_query_meta,
                urma_link,
                urma_total,
                client_worker_urma or "0",
                worker_worker_urma or "0",
                urma_inflight,
                urma_src,
                urma_dst,
                remark,
            ])
        progress.done(rows=len(worker_entries))

def _compute_endpoint_p99_threshold(
    sdk_entries: list[SdkGetEntry],
    sdk_worker_map,
    worker_urma_map,
    sdk_urma_map,
    worker_worker_urma_map,
    worker_remote_pull_map,
    worker_idx_map,
    p99_threshold_ms,
):
    if p99_threshold_ms <= 0:
        return set()
    
    endpoint_latencies: dict[str,list[float]] = defaultdict(list)
    endpoint_to_trace: dict[str,list[str]] = defaultdict(list)

    for i,sdk in enumerate(sdk_entries):
        w_idx = worker_idx_map.get(i)
        if w_idx is None:
            continue
        urma_list = worker_urma_map.get(w_idx,[])
        if urma_list:
            for urma in urma_list:
                if urma.src_addr and urma.dst_addr:
                    endpoint = f"{urma.src_addr}->{urma.dst_addr}"
                    latency_us = urma.elapsed_ms * 1000
                    endpoint_latencies[endpoint].append(latency_us)
                    endpoint_to_trace[endpoint].append(sdk.trace_id)
        else:
            remote_pulls = worker_remote_pull_map.get(w_idx,[])
            if remote_pulls:
                for pull in remote_pulls:
                    if pull.read_src_addr and pull.read_dst_addr:
                        endpoint = f"{pull.read_src_addr}->{pull.read_dst_addr}"
                        latency_us = float(sdk.total_time_us)
                        endpoint_latencies[endpoint].append(latency_us)
                        endpoint_to_trace[endpoint].append(sdk.trace_id)
        client_value = sdk_urma_map.get(w_idx,[])
        if client_value is not None:
            endpoint = f"client->{sdk.pod_ip}"
            latency_us = float(client_value)
            endpoint_latencies[endpoint].append(latency_us)
            endpoint_to_trace[endpoint].append(sdk.trace_id)

    endpoint_p99:dict[str,float] = {}
    endpoint_sample_count:dict[str,int] = {}
    for endpoint,latencies in endpoint_latencies.items():
        endpoint_sample_count[endpoint] = len(latencies)
        if len(latencies) >= 10:
            p99_us = _percentile(latencies,0.99)
            endpoint_p99[endpoint] = p99_us/1000.0
    high_latency_endpoints = []
    total_trace_kept = 0
    for endpoint,p99 in endpoint_p99.items():
        if p99 > p99_threshold_ms:
            trace_count = len(endpoint_to_trace[endpoint])
            
            total_trace_kept += trace_count

            high_latency_endpoints.append((endpoint,p99,trace_count))
    if high_latency_endpoints:
        high_latency_endpoints.sort(key = lambda x: x[1],reverse=True)
        print(f"High latency endpoints (P99 > {p99_threshold_ms:.3f}ms):")
        for endpoint,p99,trace_count in high_latency_endpoints[:10]:
            print(f"{endpoint}: P99={p99:.3f}ms, {trace_count} traces")
        if len(high_latency_endpoints) > 10:
            print(f"... and {len(high_latency_endpoints) - 10} more endpoints")

        print(f"Total traces kept: {total_trace_kept}")

    else:
        print(f"No high latency endpoints (P99 > {p99_threshold_ms:.3f}ms)")
    
    keep_trace_ids = set()
    for endpoint,p99,trace_count in high_latency_endpoints:
        if p99 > p99_threshold_ms:
            keep_trace_ids.update(endpoint_to_trace[endpoint])
    return keep_trace_ids

def parse_cmd(args):
    if not os.path.isdir(args.input_dir):
        print(f"Error: input_dir {args.input_dir} is not a directory",file=sys.stderr)
        sys.exit(1)
    if not args.no_time_window and args.time_window <= 0:
        print(f"Error: time_window {args.time_window} must be > 0",file=sys.stderr)
        sys.exit(1)
    
    start_time = None
    end_time = None
    if args.start:
        try:
            for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%d %H:%M:%S.%f"):
                try:
                    start_time = datetime.strptime(args.start,fmt)
                    break
                except ValueError:
                    continue
            if start_time is None:
                raise ValueError(f"Unrecognized start time format: {args.start}")
            print(f"Start time filter: {start_time}")
        except ValueError:
            print(f"Error: start time {args.start} is not in format %Y-%m-%dT%H:%M:%S.%f or %Y-%m-%dT%H:%M:%S",file=sys.stderr)
            print("Expected format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS",file=sys.stderr)
            sys.exit(1)

    if args.end:
        try:
            for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%d %H:%M:%S.%f"):
                try:
                    end_time = datetime.strptime(args.end,fmt)
                    break
                except ValueError:
                    continue
            if end_time is None:
                raise ValueError(f"Unrecognized end time format: {args.end}")
            print(f"End time filter: {end_time}")
        except ValueError:
            print(f"Error: end time {args.end} is not in format %Y-%m-%dT%H:%M:%S.%f or %Y-%m-%dT%H:%M:%S",file=sys.stderr)
            print("Expected format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS",file=sys.stderr)
            sys.exit(1)
    if start_time and end_time and start_time >= end_time:
        print(f"Error: start time {start_time} must be before end time {end_time}",file=sys.stderr)
        sys.exit(1)
    
    print(f"Parsing SDK logs from {args.input_dir}")
    sdk_entries = _parse_sdk_logs(args.input_dir,start_time,end_time,min_total_time_ms=args.min_total_time)
    print(f"SDK Get {len(sdk_entries)} entries")
    print("Parsing Worker access logs...")

    print("Parsing Worker URMA logs...")
    urma_entries = _parse_worker_urma_logs(args.input_dir)
    print(f"Worker URMA Get {len(urma_entries)} entries")
    print(f"URMA entries :{len(urma_entries)}")

    trace_urma_entries = sum(1 for u in urma_entries if u.trace_id)
    print(f"URMA entries with trace_id: {trace_urma_entries}/{len(urma_entries)}")
    print("Parsing Worker remote pull endpoint logs...")
    remote_pull_entries = _parse_worker_remote_pull_logs(args.input_dir)
    print(f"Worker remote pull Get {len(remote_pull_entries)} entries")
    print(f"Remote pull entries :{len(remote_pull_entries)}")
    print("Parsing Worker link logs...")
    link_entries = _parse_worker_link_logs(args.input_dir)
    print(f"Worker link Get {len(link_entries)} entries")
    print(f"Link entries :{len(link_entries)}")
    print("Parsing Worker query meta logs...")
    query_meta_entries = _parse_worker_query_meta_logs(args.input_dir)
    print(f"Worker query meta Get {len(query_meta_entries)} entries")
    print(f"Query meta entries :{len(query_meta_entries)}")

    print("Correlating Worker <-> URMA...")
    worker_remote_pull_map = _correlate_worker_remote_pull(worker_entries,remote_pull_entries)
    worker_urma_map,worker_worker_urma_map = _correlate_worker_urma(worker_entries,urma_entries,worker_remote_pull_map)

    sdk_urma_map = _correlate_sdk_urma(sdk_entries,urma_entries)
    print(f"SDK URMA Get {len(sdk_urma_map)} entries")
    print("Correlating Worker <-> Link...")
    worker_link_map = _correlate_worker_link(worker_entries,link_entries)
    worker_query_meta_map = _correlate_worker_query_meta(worker_entries,query_meta_entries)
    worker_urma_empty_reasons = _build_worker_urma_empty_reasons(worker_entries,urma_entries,worker_urma_map)
    matched_urma = sum(1 for v in worker_urma_map.values() if v)

    if sdk_entries:
        if args.no_time_window:
            print("Correlating Worker <-> SDK...(trace_id,no_time_window)")
        else:
            print(f"Correlating Worker <-> SDK...(trace_id,time_window={args.time_window}ms)...")
        sdk_worker_map = _correlate_sdk_worker(sdk_entries,worker_entries,args.no_time_window)
        _print_unmatched_sdk_samples(sdk_entries,sdk_worker_map,args.time_window,args.no_time_window)

        worker_to_idx = {id(w):i for i,w in enumerate(worker_entries)}
        worker_idx_map = {}
        for sdk_i,w in sdk_worker_map.items():
            if w:
                worker_idx_map[sdk_i] = worker_to_idx[id(w)]
        keep_trace_ids =None
        if args.p99_threshold and args.p99_threshold > 0:
            keep_trace_ids = _compute_endpoint_p99_threshold(
                sdk_entries,
                sdk_worker_map,
                worker_urma_map,
                sdk_urma_map,
                worker_worker_urma_map,
                worker_remote_pull_map,
                worker_idx_map,
                args.p99_threshold,
            )
            if len(keep_trace_ids) == 0:
                print(f"WARNING: No traces exceed the p99 threshold ,output CSV will empty")

        print(f"Write CSV to {args.output}")
        _write_csv(
            sdk_entries,
            sdk_worker_map,
            worker_urma_map,
            sdk_urma_map,
            worker_worker_urma_map,
            worker_remote_pull_map,
            worker_link_map,
            worker_query_meta_map,
            worker_idx_map,
            worker_urma_empty_reasons,
            args.output,
            keep_trace_ids=keep_trace_ids,
            filter_threshold_ms=args.filter_threshold_ms,
        )
    else:
        print(f"WARNING: No SDK entries ,writing Worker-only CSV...")
        _write_worker_only_csv(
            worker_entries,
            worker_urma_map,
            worker_worker_urma_map,
            worker_remote_pull_map,
            worker_link_map,
            worker_query_meta_map,
            worker_idx_map,
            worker_urma_empty_reasons,
            args.output,
            keep_trace_ids=keep_trace_ids,
            filter_threshold_ms=args.filter_threshold_ms,
        )
    print("Done")


#====================================================================
# PLOT MODULE
#====================================================================

def _percentile(values:list[float],pct:float)->float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * pct / 100.0
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    frac = k - lo
    return values[lo] + frac * (values[hi] - values[lo])

def _parse_semicolon_values(raw:str,converter:type)->list:
    if not raw or not raw.strip():
        return []
    
    results = []
    for item in raw.split(";"):
        item = item.strip()
        if item:
            results.append(converter(item))
    return results

def _parse_semicolon_floats(raw:str)->list[float]:
    if not raw or not raw.strip():
        return []
    results = []
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        match = LEAD_DIGIT_RE.match(item)
        if match:
            results.append(float(match.group()))
    return results

def _parse_semicolon_ints(raw:str)->list[int]:
    return _parse_semicolon_values(raw,int)

class _Bucket:
    __slot__ = 'time', 'Operation', 'TraceId', 'TotalTime(us)', 'DataSize', 'pod_ip',
    'Client2WorkerTime(us)', 'WorkerQueryMetaTime(ms)', 'URMA_LINK(ms)', 'URMA_TOTAL(ms)',
    'ClientWorkerURMA(ms)', 'WorkerWorkerURMA(ms)', 'urma_inflight_wr_count',
    'urma_write_source', 'urma_write_dst',

    def __init__(self,window_start:datetime):
        self.window_start = window_start
        self.count = 0
        self.worker_samples:list[tuple[float,str]] = []
        self.client_samples:list[tuple[float,str]] = []
        self.query_meta_samples:list[tuple[float,str]] = []
        self.urma_samples:list[tuple[float,str]] = []
        self.client_worker_urma_samples:list[tuple[float,str]] = []
        self.worker_worker_urma_samples:list[tuple[float,str]] = []
        self.inflight_count:list[int] = []

def _read_and_bucket(csv_path:str,window_sec:int)->dict[str,list[_Bucket]]:
    node_buckets:dict[str,dict[int,_Bucket]] = defaultdict(dict)
    progress = _Progress("Read CSV")

    with open(csv_path,"r") as f:
        reader = csv.reader(f)
        headers = next(reader,None)
        if headers is None:
            return {}
        header_idx = {name.strip():i for i,name in enumerate(headers)}
        required_headers = set([
            'time', 'TraceId', 'TotalTime(us)', 'pod_ip', 'Client2WorkerTime(us)',
            'URMA_TOTAL(ms)', 'urma_inflight_wr_count',
        ])
        missing_headers = [name for name in required_headers if name not in header_idx]
        if missing_headers:
            print(f"Error: CSV file {csv_path} missing required headers: {missing_headers}")
            sys.exit(1)
        idx_time = header_idx['time']
        idx_trace = header_idx['TraceId']
        idx_total = header_idx['TotalTime(us)']
        idx_pod = header_idx['pod_ip']
        idx_c2w = header_idx['Client2WorkerTime(us)']
        idx_query_meta = header_idx['WorkerQueryMetaTime(ms)']
        idx_urma = header_idx['URMA_TOTAL(ms)']
        idx_client_worker_urma = header_idx['ClientWorkerURMA(ms)']
        idx_worker_worker_urma = header_idx['WorkerWorkerURMA(ms)']
        idx_inflight = header_idx['urma_inflight_wr_count']
        required_indexes = [idx_time,idx_trace,idx_total,idx_pod,idx_c2w,idx_urma,idx_inflight]
        if idx_query_meta is not None:
            required_indexes.append(idx_query_meta)
        if idx_client_worker_urma is not None:
            required_indexes.append(idx_client_worker_urma)
        if idx_worker_worker_urma is not None:
            required_indexes.append(idx_worker_worker_urma)
        required_cols = max(required_indexes) + 1

        row_count =0
        for row in reader:
            if len(row) < required_cols:
                continue
            row_count += 1
            if row_count % PROGRESS_UPDATE_LINES == 0:
                progress.update(rows = row_count)
            ts_str = row[idx_time].strip()
            trace_id = row[idx_trace].strip()
            total_str = row[idx_total].strip()
            pod_ip = row[idx_pod].strip()
            c2w_str = row[idx_c2w].strip()
            query_meta_str = row[idx_query_meta].strip() if idx_query_meta is not None else ""
            urma_str = row[idx_urma].strip()
            client_worker_urma_str = row[idx_client_worker_urma].strip() if idx_client_worker_urma is not None else ""
            worker_worker_urma_str = row[idx_worker_worker_urma].strip() if idx_worker_worker_urma is not None else ""
            inflight_str = row[idx_inflight].strip()

            if not ts_str or not total_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                total_us = int(total_str)
            except (ValueError,TypeError):
                continue

            bucket_key = int(ts.timestamp() // window_sec)

            bucket_start = datetime.fromtimestamp(bucket_key * window_sec)
            bucket_map = node_buckets[pod_ip]

            if bucket_key not in bucket_map:
                bucket_map[bucket_key] = _Bucket(bucket_start)
            bucket = bucket_map[bucket_key]
            bucket.count += 1
            
            is_sdk_row = bool(c2w_str)
            if is_sdk_row:
                try:
                    c2w_us = int(c2w_str)
                    worker_time = total_us - c2w_us
                except (ValueError,TypeError):
                    worker_time = float(total_us)
                bucket.client_samples.append((float(total_us),trace_id))
                
            else:
                worker_time = total_us
            bucket.worker_samples.append((float(worker_time),trace_id))
            query_meta_vals = _parse_semicolon_floats(query_meta_str)
            if query_meta_vals:
                bucket.query_meta_samples.extend((v*1000.0,trace_id) for v in query_meta_vals)
            
            urma_vals = _parse_semicolon_floats(urma_str)
            if urma_vals:
                bucket.urma_samples.extend((v*1000.0,trace_id) for v in urma_vals)
            client_worker_urma_vals = _parse_semicolon_floats(client_worker_urma_str)
            if client_worker_urma_vals:
                bucket.client_worker_urma_samples.extend((v*1000.0,trace_id) for v in client_worker_urma_vals)
            
            worker_worker_urma_vals = _parse_semicolon_floats(worker_worker_urma_str)
            if worker_worker_urma_vals:
                bucket.worker_worker_urma_samples.extend((v*1000.0,trace_id) for v in worker_worker_urma_vals)
            
            inflight_vals = _parse_semicolon_ints(inflight_str)
            if inflight_vals:
                bucket.inflight_count.extend(inflight_vals)

    if row_count == 0:
        progress.done(rows=row_count)
        return {}
    result:dict[str,list[_Bucket]] = {}
    for pod_ip,bucket_map in node_buckets.items():
        result[pod_ip] = sorted(bucket_map.values(),key=lambda x: x.window_start)
    progress.done(rows=row_count)
    return result
    
def _percentile_with_trace(samples:list[tuple[float,str]],pct:float):
    if not samples:
        return None
    sorted_samples = sorted(samples,key=lambda x: x[0])
    values = [v for v,trace_id in sorted_samples]
    pct_value = _percentile(values,pct)
    sample_idx = min(math.ceil((len(sorted_samples) - 1) * pct / 100.0),len(sorted_samples) - 1)
    return pct_value,sorted_samples[sample_idx][1]

def _compute_metrics(buckets:list[_Bucket],min_samples:int)->list[dict]:
    metrics = []
    for b in buckets:
        if b.count < min_samples:
            continue
        worker_p99,worker_trace = _percentile_with_trace(b.worker_samples,0.99)
        client_p99,client_trace = _percentile_with_trace(b.client_samples,0.99)
        query_meta_p99,query_meta_trace = _percentile_with_trace(b.query_meta_samples,0.99)
        urma_p99,urma_trace = _percentile_with_trace(b.urma_samples,0.99)
        client_worker_urma_p99,client_worker_urma_trace = _percentile_with_trace(b.client_worker_urma_samples,0.99)
        worker_worker_urma_p99,worker_worker_urma_trace = _percentile_with_trace(b.worker_worker_urma_samples,0.99)
        
        m = {
            'window_start': b.window_start,
            'worker_p99': worker_p99,
            'worker_p99_trace': worker_trace,
            'client_p99': client_p99,
            'client_p99_trace': client_trace,
            'query_meta_p99': query_meta_p99,
            'query_meta_p99_trace': query_meta_trace,
            'urma_p99': urma_p99,
            'urma_p99_trace': urma_trace,
            'client_worker_urma_p99': client_worker_urma_p99,
            'client_worker_urma_p99_trace': client_worker_urma_trace,
            'worker_worker_urma_p99': worker_worker_urma_p99,
            'worker_worker_urma_p99_trace': worker_worker_urma_trace,
            'inflight_max': max(b.inflight_counts) if b.inflight_counts else None,
        }
        metrics.append(m)
    return metrics

def _write_slow_p99_trace_log(pod_ip:str,metrics:list[dict],output_dir:str)->int:
    os.makedirs(output_dir,exist_ok=True)
    out_path = os.path.join(output_dir,f"{pod_ip}.log")
    rows = []
    metric_fields = [
        ('Total P99', 'client_p99', 'client_p99_trace'),
        ('KVC Worker P99', 'worker_p99', 'worker_p99_trace'),
        ('KVC Master P99', 'query_meta_p99', 'query_meta_p99_trace'),
        ('URMA P99', 'urma_p99', 'urma_p99_trace'),
        ('Client-Worker URMA P99', 'client_worker_urma_p99', 'client_worker_urma_p99_trace'),
        ('Worker-Worker URMA P99', 'worker_worker_urma_p99', 'worker_worker_urma_p99_trace'),
        ]
    for m in metrics:
        for metric_name,value_key,trace_key in metric_fields:
            p99_value = m.get(value_key,None)
            trace_id = m.get(trace_key,None)
            if p99_value is None or p99_value <= SLOW_P99_THRESHOLD_US:
                continue
            rows.append(
                [m["window_start"].strftime("%Y-%m-%dT%H:%M:%S"),
                 metric_name,
                 f"{p99_value:.3f}us",
                 m.get(trace_key,None),
            ])
    
    with open(out_path,"w") as f:
        writer = csv.writer(f)
        writer.writerow(["time","metric","p99","trace_id"])
        writer.writerows(rows)
    return len(rows)

def _plot_node(pod_ip:str,metrics:list[dict],output_dir:str,fmt:str,dpi:int):
    times = [m["window_start"] for m in metrics]
    worker_p99 = [m["worker_p99"] for m in metrics if m["worker_p99"] is not None]
    worker_times = [m["window_start"] for m in metrics if m["worker_p99"] is not None]

    client_p99 = [m["client_p99"] for m in metrics if m["client_p99"] is not None]
    client_times = [m["window_start"] for m in metrics if m["client_p99"] is not None]

    urma_p99 = [m["urma_p99"] for m in metrics if m["urma_p99"] is not None]
    urma_times = [m["window_start"] for m in metrics if m["urma_p99"] is not None]

    client_worker_urma_p99 = [m["client_worker_urma_p99"] for m in metrics if m["client_worker_urma_p99"] is not None]
    client_worker_urma_times = [m["window_start"] for m in metrics if m["client_worker_urma_p99"] is not None]

    worker_worker_urma_p99 = [m["worker_worker_urma_p99"] for m in metrics if m["worker_worker_urma_p99"] is not None]
    worker_worker_urma_times = [m["window_start"] for m in metrics if m["worker_worker_urma_p99"] is not None]

    query_meta_p99 = [m["query_meta_p99"] for m in metrics if m["query_meta_p99"] is not None]
    query_meta_times = [m["window_start"] for m in metrics if m["query_meta_p99"] is not None]

    inflight = [m["inflight_max"] for m in metrics if m["inflight_max"] is not None]
    inflight_times = [m["window_start"] for m in metrics if m["inflight_max"] is not None]

    has_latency = bool(worker_p99 or client_p99 or urma_p99 or client_worker_urma_p99 or worker_worker_urma_p99 or query_meta_p99)
    has_inflight = bool(inflight)

    if not has_latency and not has_inflight:
        print(f"WARNING: No latency or inflight data for {pod_ip}, skip plotting")
        return
    fig,ax1 = plt.subplots(figsize=(14,6))

    if client_p99:
        ax1.plot(client_times,client_p99,"g-s",markersize=3,linewidth=1.2,label="Total P99")
    if worker_p99:
        ax1.plot(worker_times,worker_p99,"b-o",markersize=3,linewidth=1.2,label="KVC Worker P99")
    if query_meta_p99:
        ax1.plot(query_meta_times,query_meta_p99,"c-d",markersize=3,linewidth=1.2,label="KVC Master P99")
    if urma_p99:
        ax1.plot(urma_times,urma_p99,"r-^",markersize=3,linewidth=1.0,alpha=0.45,label="URMA P99")
    if client_worker_urma_p99:
        ax1.plot(client_worker_urma_times,client_worker_urma_p99,"r-^",markersize=3,linewidth=1.3,label="Client-Worker URMA P99")
    if worker_worker_urma_p99:
        ax1.plot(worker_worker_urma_times,worker_worker_urma_p99,color="orange",marker = "v",markersize=3,linewidth=1.3,label="Worker-Worker URMA P99")

    ax1.set_ylabel("P99 Latency(us)",color="black")
    ax1.set_ylim(bottom=0)

    ax1.tick_params(axis="y",labelcolor="black")
    ax1.grid(alpha=0.3)

    line_right = []
    if has_inflight:
        ax2 = ax1.twinx()
        line_inf = ax2.plot(inflight_times, inflight, 'm--x', markersize=3, linewidth=1.0,
                            alpha=0.7, label='inflight_wr_count (max)')[0]
        ax2.set_ylabel("inflight_wr_count(max)",color="m")
        ax2.tick_params(axis="y",labelcolor="m")
        line_right.append(line_inf)

    if times:
        span_sec = (times[-1] - times[0]).total_seconds()
        date_fmt = '%H:%M' if span_sec <= 86400 else '%m-%d %H:%M'
        fig.autofmt_xdate()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))

    ax1.set_title(f'Get Latency P99 - Pod IP {pod_ip}')

    lines_left, labels_left = ax1.get_legend_handles_labels()
    if lines_right:
        lines_all = lines_left + lines_right
        labels_all = labels_left + [l.get_label() for l in lines_right]
    else:
        lines_all = lines_left
        labels_all = labels_left
    ax1.legend(lines_all, labels_all, loc='upper right')

    fig.tight_layout()

    os.makedirs(output_dir,exist_ok=True)
    out_path = os.path.join(output_dir,f"{pod_ip}.{fmt}")
    fig.savefig(out_path,dpi=dpi,format=fmt)
    plt.close(fig)
    print(f"Save plot to {out_path}")

import os


def _read_and_bucket_by_endpoint(
    csv_path: str, windows_sec: int
) -> dict[str, list[_Bucket]]:
    endpoint_to_buckets: dict[str, list[_Bucket]] = defaultdict(dict)
    progress = _Progress("CSV bucket parse (by endpoint)")
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return {}
        header_idx = {name.strip(): idx for idx, name in enumerate(header)}
        required_headers = [
            "time",
            "TraceId",
            "TotalTime(us)",
            "pod_ip",
            "Client2WorkerTime(us)",
            "URMA_TOTAL(ms)",
            "urma_inflight_wr_count",
            "urma_write_source",
            "urma_write_dst",
        ]
        missing_headers = [h for h in required_headers if h not in header_idx]
        if missing_headers:
            print(f"Missing required headers: {missing_headers}", file=sys.stderr)
            sys.exit(1)

        idx_time = header_idx["time"]
        idx_trace = header_idx["TraceId"]
        idx_total = header_idx["TotalTime(us)"]
        idx_pod = header_idx["pod_ip"]
        idx_c2w = header_idx["Client2WorkerTime(us)"]
        idx_query_meta = header_idx["WorkerQueryMetaTime(ms)"]
        idx_urma = header_idx["URMA_TOTAL(ms)"]
        idx_client_worker_urma = header_idx["ClientWorkerURMA(ms)"]
        idx_worker_worker_urma = header_idx["WorkerWorkerURMA(ms)"]
        idx_inflight = header_idx["urma_inflight_wr_count"]
        idx_src = header_idx["urma_write_source"]
        idx_dst = header_idx["urma_write_dst"]
        required_indexes = [
            idx_time,
            idx_trace,
            idx_total,
            idx_pod,
            idx_c2w,
            idx_inflight,
            idx_src,
            idx_dst,
        ]
        if idx_query_meta is not None:
            required_indexes.append(idx_query_meta)
        if idx_client_worker_urma is not None:
            required_indexes.append(idx_client_worker_urma)
        if idx_worker_worker_urma is not None:
            required_indexes.append(idx_worker_worker_urma)
        required_cols = max(required_indexes) + 1
        row_count = 0
        for row in reader:
            if len(row) < required_cols:
                print(
                    f"Skipping row {row_count} with insufficient columns: {row}",
                    file=sys.stderr,
                )
                continue
            row_count += 1
            if row_count % PROGRESS_UPDATE_LINE==0:
                progress.update(rows=row_count)
            ts_str = row[idx_time].strip()
            trace_id = row[idx_trace].strip()
            total_str = row[idx_total].strip()
            pod_ip = row[idx_pod].strip()
            c2w_str = row[idx_c2w].strip()
            query_meta_str = row[idx_query_meta].strip() if idx_query_meta is not None else ""
            urma_str = row[idx_urma].strip() if idx_urma is not None else ""
            if src_str and dst_str:
                src = src_str.split(";")[0].strip()
                dst = dst_str.split(";")[0].strip()
                endpoint = f"{src} -> {dst}"
            else:
                continue
            try:
                ts=datetime.fromisoformat(ts_str)
                total_us = int(total_str)
            except (ValueError, TypeError):
                print(
                    f"Skipping row {row_count} with invalid time or total: {row}",
                    file=sys.stderr,
                )
                continue
            bucket_key= int(ts.timestamp()) // windows_sec
            bucket_start = datetime.fromtimestamp(bucket_key * windows_sec) 
            bucket_map =endpoint_to_buckets[endpoint]
            if bucket_key not in bucket_map:
                bucket_map[bucket_key] = _Bucket(bucket_start)
            bucket = bucket_map[bucket_key]
            bucket.count += 1

            is_sdk_row=bool(c2w_str)
            if is_sdk_row:
                try:
                    c2w_us = int(c2w_str)
                    worker_time = total_us - c2w_us
                except (ValueError, TypeError):
                    worker_time = float(total_us)
                bucket.client_samples.append((float(c2w_us), trace_id))
            else:
                worker_time = total_us
            
            bucket.worker_samples.append((float(worker_time), trace_id))

            query_meta_vals = _parse_semicolon_floats(query_meta_str)
            if query_meta_vals:
                bucket.query_meta_samples.extend((v*1000.0,trace_id) for v in query_meta_vals)
            
            urma_vals = _parse_semicolon_floats(urma_str)
            if urma_vals:
                bucket.urma_samples.extend((v*1000.0,trace_id) for v in urma_vals)
            client_worker_urma_vals = _parse_semicolon_floats(client_worker_urma_str)
            if client_worker_urma_vals:
                bucket.client_worker_urma_samples.extend((v*1000.0,trace_id) for v in client_worker_urma_vals)
            worker_worker_urma_vals = _parse_semicolon_floats(worker_worker_urma_str)
            if worker_worker_urma_vals:
                bucket.worker_worker_urma_samples.extend((v*1000.0,trace_id) for v in worker_worker_urma_vals)
            inflight_vals = _parse_semicolon_ints(inflight_str)
            if inflight_vals:
                bucket.inflight_counts.extend(inflight_vals)
    if row_count==0:
        process.done(rows=row_count)
        return {}
    result:dict[str, list[_Bucket]] = {}
    for endpoint, bucket_map in endpoint_to_buckets.items():
        result[endpoint] = sorted(bucket_map.values(), key=lambda b: b.window_start)
    progress.done(rows=row_count)
    return result

def _plot_endpoint(end_point:str,metrics:list[dict],output_dir:str,fmt:str,dpi:int):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    times = [m["window_start"] for m in metrics]
    worker_p99=[m["worker_p99"] for m in metrics if m["worker_p99"] is not None]
    worker_times = [m["windows_start"] for m in metrics if m["worker_p99"] is not None]
    client_p99 = [m["client_p99"] for m in metrics if m["client_p99"] is not None]
    client_times = [m["windows_start"] for m in metrics if m["client_p99"] is not None]
    urma_p99 = [m["urma_p99"] for m in metrics if m["urma_p99"] is not None]
    urma_times = [m["windows_start"] for m in metrics if m["urma_p99"] is not None]
    client_worker_urma_p99 = [m["client_worker_urma_p99"] for m in metrics if m["client_worker_urma_p99"] is not None]
    client_worker_urma_times = [m["windows_start"] for m in metrics if m["client_worker_urma_p99"] is not None]
    worker_worker_urma_p99 = [m["worker_worker_urma_p99"] for m in metrics if m["worker_worker_urma_p99"] is not None]
    worker_worker_urma_times = [m["window_start"] for m in metrics if m["worker_worker_urma_p99"] is not None]
    query_meta_p99 = [m["query_meta_p99"] for m in metrics if m["query_meta_p99"] is not None]
    query_meta_times = [m["window_start"] for m in metrics if m["query_meta_p99"] is not None]
    inflight = [m["inflight_max"] for m in metrics if m["inflight_max"] is not None]
    inflight_times = [m["window_start"] for m in metrics if m["inflight_max"] is not None]
    has_latency = bool(
        worker_p99 or client_p99 or urma_p99 or client_worker_urma_p99 or worker_worker_urma_p99 or query_meta_p99
    )
    has_inflight = bool(inflight)
    if not has_latency and not has_inflight:
        print(f"No plottable data for endpoint {end_point}")
        return
    fig,ax1 = plt.subplots(figsize=(14,6))
    if client_p99:
        ax1.plot(client_times,client_p99,'g-5',marker_size=3,linewidth=1.2,label="Total P99")
    if worker_p99:
        ax1.plot(worker_times,worker_p99,'b-o',marker_size=3,linewidth=1.2,label="KVC Worker P99")
    if query_meta_p99:
        ax1.plot(query_meta_times,query_meta_p99,'c-d',marker_size=3,linewidth=1.2,label="KVC Master P99")
    if urma_p99:
        ax1.plot(urma_times,urma_p99,'r-^',marker_size=3,linewidth=1.2,label="URMA P99")
    if client_worker_urma_p99:
        ax1.plot(client_worker_urma_times,client_worker_urma_p99,'r-^',marker_size=3,linewidth=1.2,label="Client-Worker URMA P99")
    if worker_worker_urma_p99:
        ax1.plot(worker_worker_urma_times,worker_worker_urma_p99,color="orange",marker="v",marker_size=3,linewidth=1.2,label="Worker-Worker URMA P99")
    
    ax1.set_ylabel('P99 Latency (us)',color='black')
    ax1.set_ylim(bottom=0)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(alpha=0.3)

    lines_right=[]
    if has_inflight:
        ax2 = ax1.twinx()
        line_inf=ax2.plot(inflight_times,inflight,'m--x',marker_size=3,linewidth=1.0,alpha=0.7,label="inflight_wr_count (max)")[0]
        ax2.set_ylabel('inflight_wr_count (max)',color='magenta')
        ax2.set_ylim(bottom=0)
        ax2.tick_params(axis='y', labelcolor='magenta')
        lines_right.append(line_inf)
    
    if times:
        span_spec = (times[-1]-times[0]).total_seconds()
        date_fmt = "%H:%M" if span_spec < 84600 else "%m-%d %H:%M"
        fig.autofmt_xdate()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    
    display_name= end_point if len(endpoint) <=60 else endpont[:57] + '...'
    ax1.set_title(f"Get Latency P99 - Endpoint: {display_name}")
    lines_left, labels_left = ax1.get_legend_handles_labels()
    if lines_right:
        lines_all = lines_left + lines_right
        labels_all = labels_left + [l.get_label() for l in lines_right]
    else:
        lines_all = lines_left
        labels_all = labels_left
    ax1.legend(lines_all, labels_all, loc='upper left')
    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)  
    safe_endpoint = endpoint.replace("->", "to").replace(":", "_").replace(".", "_")
    output_path = os.path.join(output_dir, f"{safe_endpoint}_latency.{fmt}")
    fig.savefig(output_path, format=fmt, dpi=dpi)
    plt.close(fig)
    print(f"Saved plot for endpoint {end_point} to {output_path}")

def plot_cmd(args):
    if args.windows<=0:
        print('Error: --windows must be a positive integer representing seconds',file=sys.stderr)
        sys.exit(1)
    if args.min_samples< 0:
        print('Error: --min_samples must be a non-negative integer',file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.input):
        print(f"Error: Input file {args.input} does not exist",file=sys.stderr)
        sys.exit(1)
    print(f"Reading CSV:{args.input}")
    print(f" Window: {args.windows}s Min samples: {args.min_samples}")
    print(f" Group by: {args.group_by}")

    if args.group_by != "endpoint":
        print(f" Grouping by: urma_write_source -> urma_write_dst (with ports)")
        endpont_buckets = _read_and_bucket_by_endpoint(args.input, args.windows)
        if not endpont_buckets:
            print("WARING: No valid rows with endpoint information found in CSV . Nothing to plot.",file=sys.stderr)
            sys.exit(0)
        
        print(f" Endpoint pairs: {len(endpont_buckets)}")

        for endpoint in sorted(endpont_buckets.keys()):
            buckets = endpont_buckets[endpoint]
            print(f"\nEndpoint: {endpoint} Buckets: {len(buckets)} time buckets")
            metrics = _compute_metrics(buckets, args.min_samples)
            if not metrics:
                print(f" WARING: No buckets with >= {args.min_samples} samples, skpping")
                continue
            print(f" Plottable buckets: {len(metrics)}")
            _plot_endpoint(endpoint, metrics, args.output_dir, args.format, args.dpi)
    else:
        node_buckets = _read_and_bucket(args.input, args.windows)
        if not node_buckets:
            print("WARNING: No valid rows found in CSV. Nothing to plot.",file=sys.stderr)
            sys.exit(0)
        
        print(f" Pod IPs: {len(node_buckets)}")

        for pod_ip in sorted(node_buckets.keys()):
            buckets = node_buckets[pod_ip]
            print(f"\nPod IP: {pod_ip} Buckets: {len(buckets)} time buckets")
            metrics = _compute_metrics(buckets, args.min_samples)
            if not metrics:
                print(f" WARNING: No buckets with >= {args.min_samples} samples, skpping")
                continue
            print(f" Plottable buckets: {len(metrics)}")
            slow_count =_write_slow_p99_trace_logs(pod_ip,metrics,args.output_dir)
            if slow_count:
                print(f" Slow P99 trace log:{os.path.join(args.output_dir,f"{pod_ip}.log")} ({slow_count} rows)")
            _plot_node(pod_ip, metrics, args.output_dir, args.format, args.dpi)
    print("\nDone")

@dataclass
class _LatencyEntry:
    timestamp:datetime
    elapsed_us:float
    handle:str
    pod_id:str

def _resolve_log_files(inputs:list[str])->list[tuple[str,str]]:
    _IP_PREFIXES = ("SDK_","dsworker_","worker_")
    def _extract_ip(dir_name:str)->str:
        for prefix in _IP_PREFIXES:
            if dir_name.startswith(prefix):
                return dir_name[len(prefix):]
        return dir_name

    result=[]
    for path in inputs:
        if os.path.isfile(path):
            parent = os.path.basename(os.path.dirname(path))
            result.append((path,_extract_ip(parent)))
        elif os.path.isdir(path):
            for entry in sorted(os.listdir(path)):
                child = os.path.join(path,entry)
                if os.path.isdir(child):
                    pod_ip = _extract_ip(entry)
                    for fname in sorted(os.listdir(child)):
                        fpath=os.path.join(child,fname)
                        if os.path.isfile(fpath):
                            result.append((fpath,pod_ip))
                elif os.path.isfile(child):
                    parent = os.path.basename(os.path.dirname(child))
                    result.append((child,_extract_ip(parent)))
    return result

def _parse_latency_logs(inputs: list[str],op_filter:str)->list[_LatencyEntry]:
    entries=[]
    for fpath,pod_ip in _resolve_log_files(inputs):
        with open(fpath,"r",errors="replace") as f:
            for line in f:
                p = _parse_access_line(line)
                if not p:
                    continue
                if op_filter and p["handle"] != op_filter:
                    continue
                try:
                    elapsed = int(p["elapsed"])
                except (ValueError,TypeError):
                    continue
                entries.append(_LatencyEntry(
                    timestamp=_parse_timestamp(p["timestamp"]),
                    elapsed_us=float(elapsed),
                    handle=p["handle"],
                    pod_ip=pod_ip                
                    ))
    entries.sort(key=lambda e: e.timestamp)
    return entries

def _bucket_latency(entries:list[_LatencyEntry],window_sec:int)->dict[str,dict[int,list[_LatencyEntry]]]:
    result: dict[str,dict[int,list[_LatencyEntry]]] = defaultdict(lambda:defaultdict(list))
    for e in entries:
        bk = int(e.timestamp.timestamp()) // window_sec
        result[e.pod_ip][bk].append(e.elapsed_us)
    return result

def _compute_latency_stats(values:list[float])->dict:
    return {
        "avg": sum(values)/len(values) if values else None,
        "p90": _percentile(values,90) if values else None,
        "p99": _percentile(values,99) if values else None,
        "max" : max(values) if values else None,
        "min" : min(values) if values else None,
        "count": len(values) if values else 0
    }
    
def _format_us(val:float)->str:
    if val >= 1000:
        return f"{val/1000:.2f} ms"
    return f"{val:.0f} us"

def _plot_latency_chart(label:str,stats_series:list[dict],output_dir:str,fmt:str,dpi:int):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    times = [s["window_start"] for s in stats_series]
    avg_vals = [s["avg"] for s in stats_series if s["avg"] is not None]
    p99_vals = [s["p99"] for s in stats_series if s["p99"] is not None]

    fig,ax = plt.subplots(figsize=(14,6))

    ax.plot(times,avg_vals,'b-o',marker_size=3,linewidth=1.2,label="Avg")
    ax.plot(times,p99_vals,'r--',linewidth=0.8,alpha=0.6,label="P99")

    all_elapsed = []
    for s in stats_series:
        all_elapsed.extend(s["values"])
    overall = _compute_latency_stats(all_elapsed)
    stats_text=(
        f"Overall avg={_format_us(overall['avg'])}  "
        f"p90={_format_us(overall['p90'])}  "
        f"p99={_format_us(overall['p99'])}  "
        f"max={_format_us(overall['max'])}  "
        f"min={_format_us(overall['min'])}  "
        f"count={overall['count']}"
    )

    ax.set_ylabel('Latency (us)')
    ax.grid(alpha=0.3)
    
    ax.legend(loc='upper left')

    if times:
        span_sec = (times[-1]-times[0]).total_seconds()
        date_fmt = "%H:%M" if span_sec < 84600 else "%m-%d %H:%M"
        fig.autofmt_xdate()
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    
    ax.set_title(f"Latency - {label}\n{stats_text}",fontsize=11)

    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    safe_label = label.replace(".","_")
    out_path = os.path.join(output_dir,f"{safe_label}_latency.{fmt}")
    fig.savefig(out_path, format=fmt, dpi=dpi) 
    plt.close(fig)
    print(f"Saved:  {out_path}")

def latency_cmd(args):
    if args.window <=0:
        print("ERROR: --window must be a positive integer",file=sys.stderr)
        sys.exit(1)
    if not args.inputs:
        print("ERROR: --input is required",file=sys.stderr)
        sys.exit(1)
    for p in args.inputs:
        if not os.path.exists(p):
            print(f"ERROR: Input path {p} does not exist",file=sys.stderr)
            sys.exit(1)
    
    op_filter= args.op if args.op else ""
    print(f"Parsing access logs...")
    if op_filter:
        print(f" Filtering: {op_filter}")
    
    entries = _parse_latency_logs(args.inputs,op_filter)    
    if not entries:
        print("WARNING: No valid log entries found. Nothing to plot.",file=sys.stderr)
        sys.exit(0)
    start_ts=_parse_timestamp(args.start) if args.start else None
    end_ts=_parse_timestamp(args.end) if args.end else None
    if start_ts or end_ts:
        before = len(entries)
        if start_ts:
            entries = [e for e in entries if e.timestamp >= start_ts]
        if end_ts:
            entries = [e for e in entries if e.timestamp <= end_ts]
        print(f" Time range: {args.start or '...'} ~ {args.end or '...'}")
        print(f" Filtered by time: {before} -> {len(entries)} entries")
    if not entries:
        print("WARNING: No log entries after time filtering.",file=sys.stderr)
        sys.exit(0)
    handles=set(e.handle for e in entries)
    pods=set(e.pod_ip for e in entries)
    print(f" Total entries: {len(entries)}  Handles: {handles}  Pods: {pods}")
    print(f" Bucketing latency by {args.window}s windows...")
    bucketed = _bucket_latency(entries,args.window)
    if args.merge:
        all_buckets:dict[int,list[float]] = defaultdict(list)
        for pod_buckets in bucketed.values():
            for bk,vals in pod_buckets.items():
                all_buckets[bk].extend(vals)
        stats_series=[]
        for bk in sorted(all_buckets.keys()):
            ws = datetime.fromtimestamp(bj * args.window)
            vals = all_buckets[bk]
            s=_compute_latency_stats(vals)
            s["window_start"]=ws
            s["values"]=vals
            stats_series.append(s)
        if stats_series:
            _plot_latency_chart("All Pods",stats_series,args.output_dir,args.format,args.dpi)
    else:
        for pod_ip, pod_buckets in bucketed.items():
            pod_buckets=[]
            stats_series=[]
            for bk in sorted(pod_buckets):
                ws = datetime.fromtimestamp(bk * args.window)
                vals = pod_buckets[bk]
                s=_compute_latency_stats(vals)
                s["window_start"]=ws
                s["values"]=vals
                stats_series.append(s)
        if stats_series:
            _plot_latency_chart(f"Pod {pod_ip}",stats_series,args.output_dir,args.format,args.dpi)
    
    print(f"\n{'='*80}")
    print(f"{'Pod':<18} {'Avg':>10} {'P90':>10} {'P99':>10} {'Max':>10} {'Min':>10} {'Count':>8}")
    print(f"{'-'*18} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    if args.merge:
        all_vals=[e.elapsed_us for e in entries ]
        s=_compute_latency_stats(all_vals)
        print(f"{'all':<18} {_format_us(s['avg']):>10} {_format_us(s['p90']):>10} {_format_us(s['p99']):>10} {_format_us(s['max']):>10} {_format_us(s['min']):>10} {s['count']:>8}")
    else:
        for pod_id in sorted(bucketed):
            vals = [v for bk_vals in bucketed[pod_id].values() for v in bk_vals]
            s=_compute_latency_stats(vals)
            print(f"{pod_id:<18} {_format_us(s['avg']):>10} {_format_us(s['p90']):>10} {_format_us(s['p99']):>10} {_format_us(s['max']):>10} {_format_us(s['min']):>10} {s['count']:>8}")
    print(f"{'='*80}")
    print("\nDone") 


def _get_template_content(template_name):
    try:
        import pkgutil
        template_bytes = pkgutil.get_data(__name__,template_name)
        if template_bytes:
            return template_bytes.decode("utf-8")
    except Exception as e:
        pass
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir,'templates',template_name)
    if os.path.exists(template_path):
        with open(template_path,'r',encoding="utf-8") as f:
            return f.read()
        
    template_path = os.path.join(os.getcwd(),template_name)
    if os.path.exists(template_path):
        with open(template_path,'r',encoding ="utf-8") as f:
            return f.read()
    return None

def _aggregate_by_windos(traces:list,window_seconds:int)->list:
    if not traces:
        return []
    windows = {}
    for tarce in traces:
        ts =datetime.fromisoformat(trace["timestamp"])
        window_key = int(ts.timestamp()//window_seconds)
        if window_key not in windows:
            windows[window_key]={
                "window_start": datetime.fromtimestamp(window_key * window_seconds),
                "total_times:":[],
                "query_meta_times":[],
                "urma_times":[],
                "samples":[]
            }
        if trace["total_time_us"] is not None:
            windows[window_key]["total_times"].append(trace["total_time_us"])
        if trace["query_meta_us"] is not None:
            windows[window_key]["query_meta_times"].append(trace["query_meta_us"])
        if trace["urma_total_us"] is not None:
            windows[window_key]["urma_times"].append(trace["urma_total_us"])
        windows[window_key]["samples"].append(trace)
    result=[]
    for window_key,data in sorted(windows.items()):
        total_p99= _percentile(data["total_times"],99) if data["total_times"] else None
        query_p99=_percentile(data["query_meta_times"],99) if data["query_meta_times"] else None
        urma_p99=_percentile(data["urma_times"],99) if data["urma_times"] else None

        representative= None
        if total_p99 is not None and data["total_times"]:
            closest_idx = min(range(len(data['total_times'])),key=lambda i: abs(data["total_times"][i]-total_p99))
            representative = data["samples"][closest_idx] if closest_idx < len(data["samples"]) else data["samples"][0]
        result.append({
            "window_start": data["window_start"],
            "window_end": data["window_start"] + timedelta(seconds=window_seconds),
            "total_p99_us": total_p99,
            "query_p99_us": query_p99,
            "urma_p99_us": urma_p99,
            "sample_count": len(data["samples"]),
            "representative_trace": representative
        })
    return result
def _aggregate_by_ip_pair(traces:list)->dict:
    """按 urma_write_source 和 urma_write_dst 进行聚合"""
    result={}
    for trace in traces:
        src = trace.get("urma_write_source","")
        dst = trace.get("urma_write_dst","")
        if not src or not dst:
            continue
        key=f"{src}||{dst}"
        if key not in result:
            result[key]={
                "src": src,
                "dst": dst,
                "total_times_us":[],
                "query_meta_us":[],
                "urma_total_us":[],
            }
        result[key]["traces"].append(trace)
        if trace.get("total_time_us") is not None:
            result[key]["total_times_us"].append(trace["total_time_us"] )
        if trace.get("query_meta_us") is not None:
            result[key]["query_meta_us"].append(trace["query_meta_us"])
        if trace.get("urma_total_us") is not None:
            result[key]["urma_total_us"].append(trace["urma_total_us"])

    for key,data in result.items():
        total_times=data["total_times_us"]
        query_meta_times=data["query_meta_us"]
        urma_times=data["urma_total_us"]
        if total_times:
            data["total_p99"]= _percentile(sorted(total_times),99)
            data["total_avg"]= sum(total_times)/len(total_times)
        else:
            data["total_p99"]=None
            data["total_avg"]=None
        if query_meta_times:
            data["query_p99"] = _percentile(sorted(query_meta_times),99)
        else:
            data["query_p99"]=0
        if urma_times:
            data["urma_p99"] = _percentile(sorted(urma_times),99)
        else:
            data["urma_p99"]=0
        data["sample_count"]= len(data["traces"])
    return result