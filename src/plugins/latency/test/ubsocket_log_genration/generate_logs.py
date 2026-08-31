#!/usr/bin/env python3
"""Generate ubsocket fault log dataset according to prompt.md requirements."""

import argparse
import json
import math
import os
import random
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Paths
DATA_DIR = "/Users/zhaoyujin/Desktop/witty-ub/data"
BASE_DIR = "/Users/zhaoyujin/Desktop/witty-ub/src/plugins/latency/test/ubsocket_log_genration"

# Failure mode data files
UBSOCKET_FM = os.path.join(DATA_DIR, "ubsocket", "ubsocket_failure_mode.json")
UMQ_FM = os.path.join(DATA_DIR, "umq", "umq_failure_mode.json")
URMA_FM = os.path.join(DATA_DIR, "urma", "urma_failure_mode_for_brpc.json")
TREE_FILE = os.path.join(DATA_DIR, "failure_mode_tree.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_fm_dict(fm_list):
    """Build dict keyed by 故障编号."""
    return {item["故障编号"]: item for item in fm_list}


def extract_message(现象):
    """Extract actual log message from 故障现象 field.

    Handles patterns like:
      '依次匹配`text1`、`text2`' -> 'text1text2'
      'plain text' -> 'plain text'
      '向下级匹配' -> None
    """
    if not 现象 or 现象 == "向下级匹配":
        return None
    # Extract text between backticks
    parts = re.findall(r'`([^`]*)`', 现象)
    if parts:
        return "".join(parts)
    return 现象


def find_public_apis(tree, component, upper_components):
    """Find public API failure modes for a component.

    A public API is a failure mode that:
    - Has no parent within the same component, OR
    - Its parent is in an upper-level component
    """
    # Build a set of all failure mode IDs that are children of nodes in this component
    children_in_component = set()
    comp_tree = tree.get(component, {})
    for parent_id, child_list in comp_tree.items():
        for child_id in child_list:
            # Check if child_id belongs to this component
            prefix = component if component != "urma4brpc" else "urma4brpc"
            if child_id.startswith(prefix + "_"):
                children_in_component.add(child_id)

    # Public APIs are keys in the component's tree that are NOT children of any
    # other node in the same component
    public_apis = set()
    for fm_id in comp_tree:
        if fm_id not in children_in_component:
            public_apis.add(fm_id)

    return public_apis


def find_root_public_api(fm_id, tree, component, upper_components):
    """Find the root public API for a given failure mode by traversing up."""
    comp_tree = tree.get(component, {})
    prefix = component if component != "urma4brpc" else "urma4brpc"

    current = fm_id
    visited = set()
    while current not in visited:
        visited.add(current)
        # Find parent of current in this component
        parent = None
        for p, children in comp_tree.items():
            if current in children:
                # Check if parent is in same component
                if p.startswith(prefix + "_"):
                    parent = p
                    break
                else:
                    # Parent is in upper component - current is a public API
                    return current

        if parent is None:
            # No parent found - current is a root (public API)
            return current
        current = parent

    return current


def generate_placeholder_values(fm_id, fm_info):
    """Generate realistic placeholder values for error message templates."""
    values = {}
    values["fd"] = random.randint(10, 200)
    errno_choices = {
        9: "Bad file descriptor",
        11: "Resource temporarily unavailable",
        12: "Cannot allocate memory",
        22: "Invalid argument",
        28: "No space left on device",
        38: "Function not implemented",
        104: "Connection reset by peer",
        110: "Connection timed out",
        113: "No route to host",
        131: "Connection reset by peer",
    }
    values["errno"] = random.choice(list(errno_choices.keys()))
    values["errmsg"] = errno_choices[values["errno"]]
    values["ret"] = random.randint(-20, -1)
    values["ip"] = f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"
    values["port"] = random.randint(1000, 65535)
    values["len"] = random.choice([1024, 4096, 8192, 16384, 65536])
    values["cap"] = random.choice([128, 256, 512, 1024])
    values["sent"] = random.randint(0, 4096)
    values["received"] = random.randint(0, 4096)
    values["wire_size"] = random.randint(16, 256)
    values["send_ret"] = random.randint(-1, 100)
    values["body_len"] = random.randint(64, 1024)
    values["obj_size"] = random.randint(64, 512)
    values["excess"] = random.randint(1, 100)
    values["discard_len"] = random.randint(1, 100)
    values["read_len"] = random.randint(0, 64)
    return values


def fill_template(message, values):
    """Fill in placeholder values in a message template.

    Handles two types of templates:
    1. {placeholder} style (e.g., "fd: {fd}") - replaced directly
    2. field: at end or before comma (e.g., "fd:" in "failed, fd:") - value inserted
    """
    result = message

    # Step 1: Replace {placeholder} patterns
    result = re.sub(r'\{(\w+)\}', lambda m: str(values.get(m.group(1), m.group(0))), result)

    # Step 2: Fill field: patterns (field name followed by colon, then comma or end)
    # These come from extracted error messages like "fd:" "errno:" etc.
    field_patterns = [
        (r'(Peer IP:)(,|$)', 'ip', '10.0.0.1'),
        (r'(fd:)(,|$)', 'fd', 42),
        (r'(ret:)(,|$)', 'ret', -1),
        (r'(errno:)(,|$)', 'errno', 11),
        (r'(errmsg:)(,|$)', 'errmsg', 'Resource temporarily unavailable'),
        (r'(sent:)(,|$)', 'sent', 0),
        (r'(received:)(,|$)', 'received', 0),
        (r'(malloc len:)(,|$)', 'len', 4096),
        (r'(old capacity:)(,|$)', 'cap', 256),
        (r'(wire_size=)(,|$)', 'wire_size', 128),
        (r'(send_ret=)(,|$)', 'send_ret', -1),
        (r'(errno=)(,|$)', 'errno', 11),
        (r'(body_len=)(,|$)', 'body_len', 256),
        (r'(obj_size=)(,|$)', 'obj_size', 128),
        (r'(excess=)(,|$)', 'excess', 32),
        (r'(discard_len=)(,|$)', 'discard_len', 32),
        (r'(read_len=)(,|$)', 'read_len', 0),
        (r'(epoll fd=)(,|$)', 'fd', 42),
        (r'(bytes:)(,|$)', 'len', 4096),
        (r'(qid:)(,|$)', 'fd', 42),
    ]

    for pattern, key, default in field_patterns:
        val = values.get(key, default)
        result = re.sub(pattern, lambda m, v=val: m.group(1) + ' ' + str(v) + m.group(2), result)

    return result


def format_timestamp(dt):
    """Format datetime as YYYYMMDD HH:MM:SS.ffffff (6 digit microseconds)."""
    return dt.strftime("%Y%m%d %H:%M:%S.") + f"{dt.microsecond:06d}"


def format_log_line(dt, pod_name, pod_ip, component, filename, func_name, line_num,
                    thread_id, trace_id, message):
    """Format a single log line."""
    time_str = format_timestamp(dt)
    tid = thread_id if thread_id else "-"
    trace = trace_id if trace_id else "-"
    return (f"[{time_str}][{pod_name}][{pod_ip}][{component}]"
            f"[{filename}:{func_name}:{line_num}][{tid}][{trace}] {message}")


def format_urma_log_line(dt, pod_name, pod_ip, umq_filename, umq_func, umq_line,
                         thread_id, trace_id, urma_filename, urma_func, urma_line, urma_message):
    """Format a log line for URMA errors embedded in UMQ component."""
    time_str = format_timestamp(dt)
    tid = thread_id if thread_id else "-"
    trace = trace_id if trace_id else "-"
    # UMQ component, umq calling location as the outer filename:func:line
    # Message contains the full URMA log
    urma_trace = trace_id if trace_id else "-"
    message = (f"[URMA][thread_id={thread_id}][{urma_trace}]"
               f"[{urma_filename}:{urma_func}:{urma_line}] {urma_message}")
    return (f"[{time_str}][{pod_name}][{pod_ip}][UMQ]"
            f"[{umq_filename}:{umq_func}:{umq_line}][{tid}][{trace}] {message}")


def main(output_name="log_1", target_lines=100):
    output_base = os.path.join(BASE_DIR, output_name)
    logs_dir = os.path.join(output_base, "logs")
    gt_dir = os.path.join(output_base, "ground_truth")

    random.seed(target_lines)

    # Load data
    print("Loading failure mode data...")
    ubsocket_fms = build_fm_dict(load_json(UBSOCKET_FM))
    umq_fms = build_fm_dict(load_json(UMQ_FM))
    urma_fms = build_fm_dict(load_json(URMA_FM))
    tree = load_json(TREE_FILE)

    # Find public APIs
    ubsocket_public = find_public_apis(tree, "ubsocket", ["kvcache_conn"])
    umq_public = find_public_apis(tree, "umq", ["ubsocket"])
    urma_public = find_public_apis(tree, "urma4brpc", ["umq"])

    print(f"Public APIs - ubsocket: {len(ubsocket_public)}, umq: {len(umq_public)}, urma4brpc: {len(urma_public)}")

    # Define pods
    pods = [
        ("pod-worker-01", "10.0.1.10"),
        ("pod-worker-02", "10.0.1.20"),
        ("pod-worker-03", "10.0.1.30"),
    ]

    # Define unique 6-7 digit thread IDs per pod (globally unique, no cross-pod duplication)
    # Round-robin assignment so each pod's threads have timestamps spread across
    # the entire time window (avoids later pods being trimmed away).
    threads_per_pod = max(3, math.ceil(target_lines * 1.5 / 30))
    thread_pod_assignment = []  # (thread_id, pod_name, pod_ip)
    tid_counter = 100000
    for i in range(threads_per_pod):
        for pod_name, pod_ip in pods:
            thread_pod_assignment.append((str(tid_counter), pod_name, pod_ip))
            tid_counter += 1
    thread_ids = [t[0] for t in thread_pod_assignment]

    # Define trace ID counter
    trace_counter = [0]

    def next_trace_id():
        trace_counter[0] += 1
        return f"trace_{trace_counter[0]:06d}"

    # Time range: start between 2026-08-01 and now, span 25 minutes
    start_date = datetime(2026, 8, 10, 14, 30, 0)
    span_minutes = 25
    end_time = start_date + timedelta(minutes=span_minutes)

    # Define failure chains for each type
    # Type 1: ubsocket internal only
    # Type 2: ubsocket -> umq
    # Type 3: ubsocket -> umq -> urma4brpc

    ubsocket_tree = tree.get("ubsocket", {})
    umq_tree = tree.get("umq", {})
    urma_tree = tree.get("urma4brpc", {})

    def collect_messages(chain_fm_ids):
        """Collect real log messages for each fm_id in the chain.

        Only fm_ids with actual 故障现象 (not 向下级匹配) get a message.
        Returns dict: fm_id -> message (only for those with real messages).
        """
        msgs = {}
        for fid in chain_fm_ids:
            if fid.startswith("ubsocket_"):
                fm_info = ubsocket_fms.get(fid, {})
            elif fid.startswith("umq_"):
                fm_info = umq_fms.get(fid, {})
            elif fid.startswith("urma4brpc_"):
                fm_info = urma_fms.get(fid, {})
            else:
                continue
            msg = extract_message(fm_info.get("故障现象", ""))
            if msg is not None:
                msgs[fid] = msg
        return msgs

    # Predefined failure chains
    failure_chains = []

    # Type 1: ubsocket internal
    # ubsocket_001 (Connect) -> ubsocket_037 (Failed to establish UB connection, fd:)
    chain1 = ["ubsocket_001", "ubsocket_037"]
    failure_chains.append({
        "type": 1,
        "chain": chain1,
        "component": "ubsocket",
        "messages": collect_messages(chain1)
    })

    # ubsocket_002 (Accept) -> ubsocket_030 (accept() failed, Peer IP:, fd:, ...)
    chain2 = ["ubsocket_002", "ubsocket_030"]
    failure_chains.append({
        "type": 1,
        "chain": chain2,
        "component": "ubsocket",
        "messages": collect_messages(chain2)
    })

    # ubsocket_003 (ReadV) -> ubsocket_005 (Failed to pop heap, reason: heap is null)
    chain3 = ["ubsocket_003", "ubsocket_005"]
    failure_chains.append({
        "type": 1,
        "chain": chain3,
        "component": "ubsocket",
        "messages": collect_messages(chain3)
    })

    # ubsocket_003 (ReadV) -> ubsocket_008 -> ubsocket_009 (2 log lines!)
    chain4 = ["ubsocket_003", "ubsocket_008", "ubsocket_009"]
    failure_chains.append({
        "type": 1,
        "chain": chain4,
        "component": "ubsocket",
        "messages": collect_messages(chain4)
    })

    # ubsocket_004 (WriteV) -> ubsocket_017 (WriteV invalid argument, fd:, ret:, errno:, errmsg:)
    chain5 = ["ubsocket_004", "ubsocket_017"]
    failure_chains.append({
        "type": 1,
        "chain": chain5,
        "component": "ubsocket",
        "messages": collect_messages(chain5)
    })

    # ubsocket_004 (WriteV) -> ubsocket_018 (WriteV socket is closed, fd:, ret:, errno:, errmsg:)
    chain6 = ["ubsocket_004", "ubsocket_018"]
    failure_chains.append({
        "type": 1,
        "chain": chain6,
        "component": "ubsocket",
        "messages": collect_messages(chain6)
    })

    # Type 2: ubsocket -> umq
    # ubsocket_003 (ReadV) -> umq_021 -> umq_226 (umqh or option invalid)
    chain7 = ["ubsocket_003", "umq_021", "umq_226"]
    failure_chains.append({
        "type": 2,
        "chain": chain7,
        "component": "ubsocket->umq",
        "messages": collect_messages(chain7)
    })

    # ubsocket_003 (ReadV) -> ubsocket_015 (ReadV failed to locate brpc block for data, fd:) -> umq_015 -> umq_138
    chain8 = ["ubsocket_003", "ubsocket_015", "umq_015", "umq_138"]
    failure_chains.append({
        "type": 2,
        "chain": chain8,
        "component": "ubsocket->umq",
        "messages": collect_messages(chain8)
    })

    # Type 3: ubsocket -> umq -> urma4brpc
    # ubsocket_004 (WriteV) -> umq_020 -> urma4brpc_108 -> urma4brpc_784 (Invalid parameter.)
    chain9 = ["ubsocket_004", "umq_020", "urma4brpc_108", "urma4brpc_784"]
    failure_chains.append({
        "type": 3,
        "chain": chain9,
        "component": "ubsocket->umq->urma4brpc",
        "messages": collect_messages(chain9)
    })

    # ubsocket_003 (ReadV) -> umq_020 -> urma4brpc_108 -> urma4brpc_784
    chain10 = ["ubsocket_003", "umq_020", "urma4brpc_108", "urma4brpc_784"]
    failure_chains.append({
        "type": 3,
        "chain": chain10,
        "component": "ubsocket->umq->urma4brpc",
        "messages": collect_messages(chain10)
    })

    # Generate log entries
    # Each entry: (timestamp, pod_name, pod_ip, thread_id, log_line, is_fault, failure_chain, public_api_func)
    all_log_entries = []
    # Track per-thread failure chains for ground truth
    thread_failure_chains = defaultdict(list)  # thread_id -> list of (chain, count)
    # Track per-pod per-API fault counts for aggregate_event
    pod_api_counts = defaultdict(lambda: defaultdict(int))  # pod_ip -> {api_func: count}
    pod_total_faults = defaultdict(int)

    # Assign chains to threads
    # Some threads get failure chains, some get normal (successful) requests

    # Normal log messages for successful requests
    normal_messages = [
        ("ubsocket_socket.h", "Connect", 125, "UBSOCKET", "Connect to peer successfully, fd: {fd}"),
        ("ubsocket_socket.h", "Accept", 89, "UBSOCKET", "Accept connection from peer, fd: {fd}"),
        ("ubsocket_socket.h", "ReadV", 215, "UBSOCKET", "ReadV completed, fd: {fd}, bytes: {len}"),
        ("ubsocket_data_tx.cpp", "WriteV", 145, "UBSOCKET", "WriteV completed, fd: {fd}, bytes: {len}"),
        ("umq_api.h", "umq_create", 78, "UMQ", "UMQ queue created successfully, qid: {fd}"),
        ("umq_api.h", "umq_bind", 112, "UMQ", "UMQ queue bound successfully"),
        ("umq_api.h", "umq_enqueue", 234, "UMQ", "Enqueue completed, qid: {fd}, bytes: {len}"),
    ]

    total_lines = 0

    # Generate log entries for each thread
    # Each thread gets its own time starting at a small offset so timestamps
    # interleave across threads/pods after sorting.
    span_seconds = span_minutes * 60
    total_threads = len(thread_pod_assignment)
    offset_step = span_seconds / max(total_threads, 1)
    call_interval_max = max(5, min(90, span_seconds // 30))
    for thread_idx, (thread_id, pod_name, pod_ip) in enumerate(thread_pod_assignment):
        thread_time = start_date + timedelta(seconds=thread_idx * offset_step)

        # Each thread makes multiple API calls
        num_calls = random.randint(8, 12)
        for call_idx in range(num_calls):

            # Advance time between calls
            thread_time += timedelta(seconds=random.randint(5, call_interval_max))
            if thread_time > end_time:
                thread_time = end_time - timedelta(seconds=random.randint(1, 60))

            trace_id = next_trace_id()

            # Decide if this call is a failure or success
            # ~60% success, ~40% failure
            is_failure = random.random() < 0.4

            if is_failure:
                # Pick a failure chain (prefer type variety)
                available_chains = [c for c in failure_chains]
                # Weight: more type 1, some type 2, few type 3
                weights = []
                for c in available_chains:
                    if c["type"] == 1:
                        weights.append(4)
                    elif c["type"] == 2:
                        weights.append(2)
                    else:
                        weights.append(1)
                chain_info = random.choices(available_chains, weights=weights)[0]
                chain = chain_info["chain"]

                # Generate log lines for this failure chain
                # The chain goes from upstream (public API) to downstream (leaf)
                # We generate one log line per failure mode in the chain
                for fm_idx, fm_id in enumerate(chain):

                    # Advance time slightly within a chain (1-10 milliseconds)
                    thread_time += timedelta(milliseconds=random.randint(1, 10))

                    # Get failure mode info - only generate log if it has a real message
                    msg = chain_info["messages"].get(fm_id)
                    if msg is None:
                        # This failure mode has "向下级匹配" - skip log line
                        continue

                    if fm_id.startswith("ubsocket_"):
                        fm_info = ubsocket_fms.get(fm_id, {})
                        component = "UBSOCKET"
                        filename = fm_info.get("文件名", "unknown.h")
                        func_name = fm_info.get("函数名", "unknown")
                        line_num = random.randint(50, 500)

                        values = generate_placeholder_values(fm_id, fm_info)
                        msg = fill_template(msg, values)

                        log_line = format_log_line(
                            thread_time, pod_name, pod_ip, component,
                            filename, func_name, line_num,
                            thread_id, trace_id, msg
                        )

                    elif fm_id.startswith("umq_"):
                        fm_info = umq_fms.get(fm_id, {})
                        component = "UMQ"
                        filename = fm_info.get("文件名", "unknown.h")
                        func_name = fm_info.get("函数名", "unknown")
                        line_num = random.randint(50, 500)

                        values = generate_placeholder_values(fm_id, fm_info)
                        msg = fill_template(msg, values)

                        log_line = format_log_line(
                            thread_time, pod_name, pod_ip, component,
                            filename, func_name, line_num,
                            thread_id, trace_id, msg
                        )

                    elif fm_id.startswith("urma4brpc_"):
                        fm_info = urma_fms.get(fm_id, {})
                        # URMA logs use UMQ component with embedded URMA log
                        umq_info = umq_fms.get("umq_020", {})  # The calling umq function
                        umq_filename = umq_info.get("文件名", "umq_api.c")
                        umq_func = umq_info.get("函数名", "umq_wait_interrupt")
                        umq_line = random.randint(100, 400)

                        urma_filename = fm_info.get("文件名", "unknown.c")
                        urma_func = fm_info.get("函数名", "unknown")
                        urma_line = random.randint(50, 800)

                        values = generate_placeholder_values(fm_id, fm_info)
                        msg = fill_template(msg, values)

                        log_line = format_urma_log_line(
                            thread_time, pod_name, pod_ip,
                            umq_filename, umq_func, umq_line,
                            thread_id, trace_id,
                            urma_filename, urma_func, urma_line, msg
                        )

                    else:
                        continue

                    all_log_entries.append({
                        "timestamp": thread_time,
                        "pod_name": pod_name,
                        "pod_ip": pod_ip,
                        "thread_id": thread_id,
                        "trace_id": trace_id,
                        "log_line": log_line,
                        "is_fault": True,
                        "failure_chain": chain,
                        "fm_id": fm_id,
                        "fm_info": fm_info if fm_id.startswith("ubsocket_") else
                                   (umq_fms.get(fm_id, {}) if fm_id.startswith("umq_") else
                                    urma_fms.get(fm_id, {}))
                    })

                    total_lines += 1

                # Record failure chain for ground truth
                chain_str = json.dumps(chain)
                found = False
                for entry in thread_failure_chains[thread_id]:
                    if entry["failure_mode_chain"] == chain_str:
                        entry["count"] += 1
                        found = True
                        break
                if not found:
                    thread_failure_chains[thread_id].append({
                        "failure_mode_chain": chain_str,
                        "count": 1
                    })

                # Record for aggregate event
                # Find the public API for this chain
                # The first element is the ubsocket public API
                root_fm_id = chain[0]
                root_info = ubsocket_fms.get(root_fm_id, {})
                root_func = root_info.get("函数名", "unknown")
                pod_api_counts[pod_ip][root_func] += 1
                pod_total_faults[pod_ip] += 1

                # Also record umq/urma public APIs if they exist in the chain
                for chain_fm_id in chain[1:]:
                    if chain_fm_id.startswith("umq_"):
                        # Check if this is a public API (parent is in ubsocket)
                        umq_parent_in_ubsocket = False
                        for ub_id, children in ubsocket_tree.items():
                            if chain_fm_id in children:
                                umq_parent_in_ubsocket = True
                                break
                        if umq_parent_in_ubsocket or chain_fm_id in umq_public:
                            umq_info = umq_fms.get(chain_fm_id, {})
                            umq_func = umq_info.get("函数名", "unknown")
                            pod_api_counts[pod_ip][umq_func] += 1
                            pod_total_faults[pod_ip] += 1
                    elif chain_fm_id.startswith("urma4brpc_"):
                        # Check if this is a public API (parent is in umq)
                        urma_parent_in_umq = False
                        for umq_id, children in umq_tree.items():
                            if chain_fm_id in children:
                                urma_parent_in_umq = True
                                break
                        if urma_parent_in_umq or chain_fm_id in urma_public:
                            urma_info = urma_fms.get(chain_fm_id, {})
                            urma_func = urma_info.get("函数名", "unknown")
                            pod_api_counts[pod_ip][urma_func] += 1
                            pod_total_faults[pod_ip] += 1

            else:
                # Generate a successful request log
                msg_template = random.choice(normal_messages)
                filename, func_name, line_num, component, msg = msg_template
                values = generate_placeholder_values("normal", {})
                msg = fill_template(msg, values)

                log_line = format_log_line(
                    thread_time, pod_name, pod_ip, component,
                    filename, func_name, line_num,
                    thread_id, trace_id, msg
                )

                all_log_entries.append({
                    "timestamp": thread_time,
                    "pod_name": pod_name,
                    "pod_ip": pod_ip,
                    "thread_id": thread_id,
                    "trace_id": trace_id,
                    "log_line": log_line,
                    "is_fault": False,
                    "failure_chain": None,
                    "fm_id": None,
                    "fm_info": None
                })
                total_lines += 1

    # Sort all entries by timestamp (interleave threads)
    all_log_entries.sort(key=lambda x: x["timestamp"])

    # Trim to target
    all_log_entries = all_log_entries[:target_lines]

    # Recount after trimming
    # Rebuild ground truth from actual entries
    thread_failure_chains = defaultdict(list)
    pod_api_counts = defaultdict(lambda: defaultdict(int))
    pod_total_faults = defaultdict(int)

    for entry in all_log_entries:
        if not entry["is_fault"]:
            continue

        chain = entry["failure_chain"]
        thread_id = entry["thread_id"]
        pod_ip = entry["pod_ip"]
        fm_id = entry["fm_id"]

        # Determine the component of this fault log entry and find the root
        # public API within that component by traversing up the tree.
        # This correctly attributes:
        #   - ubsocket internal nodes to the ubsocket public API root (e.g. ubsocket_003/ReadV)
        #   - umq nodes to the umq public API root (e.g. umq_015/umq_data_to_head)
        #   - urma4brpc nodes to the urma4brpc public API root (e.g. urma4brpc_108/urma_ack_jfc)
        if fm_id.startswith("ubsocket_"):
            component = "ubsocket"
        elif fm_id.startswith("umq_"):
            component = "umq"
        elif fm_id.startswith("urma4brpc_"):
            component = "urma4brpc"
        else:
            continue

        root_api = find_root_public_api(fm_id, tree, component, [])

        if root_api.startswith("ubsocket_"):
            root_info = ubsocket_fms.get(root_api, {})
        elif root_api.startswith("umq_"):
            root_info = umq_fms.get(root_api, {})
        elif root_api.startswith("urma4brpc_"):
            root_info = urma_fms.get(root_api, {})
        else:
            continue

        root_func = root_info.get("函数名", "unknown")
        pod_api_counts[pod_ip][root_func] += 1
        pod_total_faults[pod_ip] += 1

    # Rebuild thread failure chains from actual entries
    # Group fault entries by thread_id and failure_chain
    thread_chain_map = defaultdict(lambda: defaultdict(int))  # thread_id -> {chain_str: count}

    # Need to count chains per thread, but each chain generates multiple log entries
    # We should count each chain occurrence once
    seen_chains_per_thread = set()
    for entry in all_log_entries:
        if not entry["is_fault"]:
            continue
        thread_id = entry["thread_id"]
        chain = entry["failure_chain"]
        chain_str = json.dumps(chain)
        # Use thread_id + trace_id + chain_str as unique key for one chain occurrence
        unique_key = (thread_id, entry["trace_id"], chain_str)
        if unique_key not in seen_chains_per_thread:
            seen_chains_per_thread.add(unique_key)
            thread_chain_map[thread_id][chain_str] += 1

    for thread_id, chain_counts in thread_chain_map.items():
        for chain_str, count in chain_counts.items():
            thread_failure_chains[thread_id].append({
                "failure_mode_chain": chain_str,
                "count": count
            })

    # Create output directories
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(gt_dir, exist_ok=True)

    # Write log files grouped by pod IP
    logs_by_pod = defaultdict(list)
    for entry in all_log_entries:
        logs_by_pod[entry["pod_ip"]].append(entry["log_line"])

    for pod_ip, lines in logs_by_pod.items():
        log_file = os.path.join(logs_dir, pod_ip + ".log")
        with open(log_file, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        print(f"Wrote {len(lines)} log lines to {log_file}")

    # Write aggregate_event.json
    aggregate_event = {}
    for pod_ip in logs_by_pod:
        aggregate_event[pod_ip] = {
            "total": pod_total_faults.get(pod_ip, 0),
        }
        for api_func, count in pod_api_counts.get(pod_ip, {}).items():
            if count > 0:
                aggregate_event[pod_ip][api_func] = count

    aggregate_path = os.path.join(gt_dir, "aggregate_event.json")
    with open(aggregate_path, "w", encoding="utf-8") as f:
        json.dump(aggregate_event, f, indent=4, ensure_ascii=False)
    print(f"Wrote aggregate_event.json to {aggregate_path}")

    # Write anomaly_threads.json
    anomaly_threads = {}
    for thread_id in sorted(thread_failure_chains.keys()):
        if thread_failure_chains[thread_id]:
            anomaly_threads[thread_id] = thread_failure_chains[thread_id]

    anomaly_path = os.path.join(gt_dir, "anomaly_threads.json")
    with open(anomaly_path, "w", encoding="utf-8") as f:
        json.dump(anomaly_threads, f, indent=4, ensure_ascii=False)
    print(f"Wrote anomaly_threads.json to {anomaly_path}")

    # Print summary
    print(f"\n=== Generation Summary ===")
    print(f"Total log lines: {len(all_log_entries)}")
    print(f"Fault lines: {sum(1 for e in all_log_entries if e['is_fault'])}")
    print(f"Normal lines: {sum(1 for e in all_log_entries if not e['is_fault'])}")
    print(f"Pod IPs: {list(logs_by_pod.keys())}")
    print(f"Time range: {format_timestamp(all_log_entries[0]['timestamp'])} to {format_timestamp(all_log_entries[-1]['timestamp'])}")
    print(f"Time span: {(all_log_entries[-1]['timestamp'] - all_log_entries[0]['timestamp']).total_seconds() / 60:.1f} minutes")
    print(f"Threads with failures: {list(anomaly_threads.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ubsocket fault log dataset")
    parser.add_argument("--log-dir", default="log_1", help="Output directory name (e.g. log_2)")
    parser.add_argument("--target-lines", type=int, default=100, help="Target number of log lines")
    args = parser.parse_args()
    main(output_name=args.log_dir, target_lines=args.target_lines)
