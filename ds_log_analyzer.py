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
