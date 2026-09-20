"""Read-only KVCache parse/aggregate/detail/bucket CPU and peak RSS benchmark.

Point PYTHONPATH at the revision under test. Use --compact for the production
compact representation; the default also supports revisions without batching.
Run alternating fresh processes with identical CONFIG and POLARS_MAX_THREADS.
--copy includes real copy_dataframe conversions with a non-retaining sink.
--digest verifies results only after time and peak RSS have been recorded.
Database/network I/O and asyncpg wire encoding are not benchmarked.
"""
import argparse
import asyncio
import hashlib
import json
import resource
import time


def _digest_frame(digest, frame):
    excluded = {"id", "log_id", "created_at", "aggregated_event_id", "_wide_row"}
    columns = [name for name in frame.columns if name not in excluded and not name.startswith("__")]
    for part in frame.select(columns).iter_slices(10_000):
        digest.update(part.write_json().encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--progress", action="store_true", help="exercise threaded progress callbacks")
    parser.add_argument("--copy", action="store_true", help="include real detail COPY conversion with a non-retaining sink")
    parser.add_argument("--digest", action="store_true", help="verify stable output fields after measuring CPU/RSS")
    args = parser.parse_args()
    asyncio.run(benchmark(args))


async def benchmark(args):
    import polars as pl
    from latency.bucket.statistics import compute_bucket_stats_from_frame
    from latency.parse.parallel_scanner.trace_frame import _yuanrong_from_grouped
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker as Worker
    from latency.database.managers.log_parse_result_bulk import copy_dataframe, LOG_PARSE_RESULT_SPEC

    class Sink:
        def __init__(self):
            self.rows = 0
            self.calls = 0

        async def copy_records_to_table(self, _table, *, records, columns):
            count = sum(1 for _ in records)
            self.rows += count
            self.calls += 1
            return f"COPY {count}"

    sink = Sink()

    async def progress(_fraction):
        pass

    started = time.perf_counter()
    result = await Worker.parse_log(
        log_dir=args.target, scan_progress_cb=progress if args.progress else None,
        **({"compact": True} if args.compact else {}),
    )
    parse_seconds = time.perf_counter() - started
    details = result if hasattr(result, "light") else None
    frame = details.light if details is not None else result
    retained = frame.estimated_size() + (details.wide.estimated_size() if details else 0)

    started = time.perf_counter()
    src_dst_events, aggregate_ids, time_window_events, anomalies = Worker._aggregate_polars(
        frame, threshold_ms=5., log_file_id="benchmark", materialize_anomaly_ids=False
    )
    top = set(frame.top_k(k=1000, by="total_latency")["tid"].to_list())
    anomaly_count = int(frame.select(
        ((pl.col("total_ms") >= 5.) & ~pl.col("tid").is_in(top)).sum()
    ).item() or 0)
    pipeline_seconds = parse_seconds + time.perf_counter() - started
    detail_options = {"trace_details": details} if details is not None else {}
    detail_rows = 0
    batched = hasattr(Worker, "_iter_detail_frames")
    if not batched:
        # The old run() builds and retains all detail rows before bucket work.
        started = time.perf_counter()
        anomaly_ids = set(anomalies.to_list())
        subset = _yuanrong_from_grouped(frame.filter(pl.col("tid").is_in(top | anomaly_ids)))
        payload = Worker._build_detail_payload(
            subset, top, anomaly_ids - top, anomaly_ids, aggregate_ids, "benchmark"
        )
        detail_rows = payload.height
        pipeline_seconds += time.perf_counter() - started

    started = time.perf_counter()
    buckets = compute_bucket_stats_from_frame(frame, **detail_options)
    pipeline_seconds += time.perf_counter() - started
    copy_seconds = 0.0
    if batched:
        # Production prepares the generator first, then computes buckets, then
        # consumes bounded detail frames while COPY owns the same connection.
        iterator = iter(Worker._iter_detail_frames(
            frame, top, 5., aggregate_ids, "benchmark", anomaly_count, **detail_options
        ))
        while True:
            started = time.perf_counter()
            batch = next(iterator, None)
            pipeline_seconds += time.perf_counter() - started
            if batch is None:
                break
            detail_rows += batch.height
            if args.copy:
                started = time.perf_counter()
                result = await copy_dataframe(batch, LOG_PARSE_RESULT_SPEC, pg_conn=sink)
                elapsed = time.perf_counter() - started
                copy_seconds += elapsed
                pipeline_seconds += elapsed
                assert result.rows == batch.height
            del batch
    elif args.copy:
        started = time.perf_counter()
        result = await copy_dataframe(payload, LOG_PARSE_RESULT_SPEC, pg_conn=sink)
        copy_seconds = time.perf_counter() - started
        pipeline_seconds += copy_seconds
        assert result.rows == payload.height
    if args.copy:
        assert sink.rows == detail_rows
    metrics = {
        "parse_seconds": parse_seconds,
        "pipeline_seconds": pipeline_seconds,
        "peak_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "retained_mib": retained / 1024**2,
        "traces": frame.height,
        "details": detail_rows,
        "anomalies": len(anomalies),
        "bucket_rows": {g: f.height for g, f in buckets.items()},
        "aggregate_rows": {"src_dst": len(src_dst_events), "time_window": len(time_window_events)},
        "with_copy": args.copy,
        "with_progress": args.progress,
        "copy_seconds": copy_seconds,
        "copy_rows": sink.rows,
        "copy_batches": sink.calls,
    }
    # Verification starts only after the peak snapshot. Regenerating bounded
    # details avoids retaining them or contaminating measured time/allocations.
    if args.digest:
        digest = hashlib.sha256()
        if batched:
            for batch in Worker._iter_detail_frames(
                frame, top, 5., aggregate_ids, "benchmark", anomaly_count, **detail_options
            ):
                _digest_frame(digest, batch)
        else:
            _digest_frame(digest, payload)
        metrics["detail_sha256"] = digest.hexdigest()
        # Compare actual emitted metrics; __ intermediate representation differs.
        digest = hashlib.sha256()
        for part in frame.iter_slices(10_000):
            if details is not None:
                part = details.enrich(part)
            _digest_frame(digest, _yuanrong_from_grouped(part))
        metrics["trace_sha256"] = digest.hexdigest()
        digest = hashlib.sha256()
        for granularity, bucket in buckets.items():
            digest.update(str(granularity).encode())
            digest.update(bucket.write_json().encode())
        metrics["bucket_sha256"] = digest.hexdigest()
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
