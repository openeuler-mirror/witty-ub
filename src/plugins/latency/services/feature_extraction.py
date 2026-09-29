# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Feature extraction from parsed KVCache log data.

Extracts latency and connectivity fault features for a given log_id,
returning a structured dict for downstream diagnosis.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import func, select, text

from latency.database.engine import PGManager
from latency.database.models import LogFailureEvent, LogParseResult, TraceFailureEvent


class FeatureExtractionManager:
    """Extract fault features from parsed KVCache log data for a given log_id."""

    # Latency sub-fields used for timeout segment analysis
    _LATENCY_FIELDS = [
        "total_latency",
        "c2w_latency",
        "worker_query_meta_latency",
        "urma_total_latency",
        "urma_link_latency",
        "c2w_urma_latency",
        "w2w_urma_latency",
        "sdk_process",
        "sdk_rpc",
        "local_worker_cost",
        "local_worker_lock",
        "remote_worker_cost",
        "remote_worker_rpc",
        "master_process",
        "master_rpc_total",
        "create_latency",
        "publish_latency",
        "worker_total_latency",
    ]

    @staticmethod
    async def extract_features(log_id: str) -> dict:
        """Extract fault features for a given log_id.

        Returns a dict with keys:
            fault_category: "latency" | "connectivity" | "mixed" | "unknown"
            latency: {...} | None
            connectivity: {...} | None
            summary: {anomalous_event_count, failure_event_count, total_parse_result_count}
        """
        print(f"[FeatureExtraction] extract_features log_id={log_id}")

        # ── Step 1: Count total records ──
        count_stmt = select(func.count()).select_from(LogParseResult).where(
            LogParseResult.log_id == log_id,
            LogParseResult.existed_status.is_(True),
        )
        print(f"[FeatureExtraction] Step 1: count total records, SQL: {count_stmt}")
        async with PGManager.session() as session:
            total_count = (await session.execute(count_stmt)).scalar() or 0
        print(f"[FeatureExtraction] total_count={total_count}")

        # ── Step 2: Extract latency features ──
        latency_features = None
        anomalous_count = 0

        # 2a: Query anomalous records with latency fields
        latency_cols = [getattr(LogParseResult, f) for f in FeatureExtractionManager._LATENCY_FIELDS]
        anomalous_stmt = select(*latency_cols, LogParseResult.operation).where(
            LogParseResult.log_id == log_id,
            LogParseResult.existed_status.is_(True),
            LogParseResult.is_anomalous.is_(True),
        ).limit(5000)
        print(f"[FeatureExtraction] Step 2a: query anomalous latency records, SQL: {anomalous_stmt}")
        async with PGManager.session() as session:
            anomalous_rows = (await session.execute(anomalous_stmt)).all()
        anomalous_count = len(anomalous_rows)
        print(f"[FeatureExtraction] anomalous_count={anomalous_count}")

        if anomalous_count > 0:
            # Compute avg for each latency field
            field_avgs: dict[str, float] = {}
            for i, field_name in enumerate(FeatureExtractionManager._LATENCY_FIELDS):
                values = [row[i] for row in anomalous_rows if row[i] is not None]
                if values:
                    field_avgs[field_name] = sum(values) / len(values)

            total_latency_avg = field_avgs.get("total_latency", 0)

            # timeout_segments: fields where avg > 10% of total_latency avg
            threshold = 0.1 * total_latency_avg if total_latency_avg > 0 else 0
            timeout_segments = sorted(
                [(name, avg) for name, avg in field_avgs.items() if avg > threshold],
                key=lambda x: x[1],
                reverse=True,
            )

            # segment_ranking: top 5 [field_name, avg_value]
            segment_ranking = [[name, avg] for name, avg in sorted(
                field_avgs.items(), key=lambda x: x[1], reverse=True
            )[:5]]

            # 2b: P99/P50 ratio from sorted total_latency values
            p99_p50_ratio = None
            tl_stmt = select(LogParseResult.total_latency).where(
                LogParseResult.log_id == log_id,
                LogParseResult.existed_status.is_(True),
                LogParseResult.total_latency.is_not(None),
            ).order_by(LogParseResult.total_latency)
            print(f"[FeatureExtraction] Step 2b: query total_latency for P99/P50, SQL: {tl_stmt}")
            async with PGManager.session() as session:
                tl_rows = (await session.execute(tl_stmt)).scalars().all()
            tl_list = sorted([v for v in tl_rows if v is not None])
            if len(tl_list) >= 2:
                p99_val = tl_list[int(0.99 * (len(tl_list) - 1))]
                p50_val = tl_list[int(0.50 * (len(tl_list) - 1))]
                if p50_val and p50_val > 0:
                    p99_p50_ratio = p99_val / p50_val

            # 2c: Unique pod count from anomalous records (raw SQL with unnest)
            pod_stmt = text("""
                SELECT count(DISTINCT pod_ip)
                FROM log_parse_result, unnest(pod_ips) AS pod_ip
                WHERE log_id = :log_id AND is_anomalous = true AND existed_status = true
            """)
            print(f"[FeatureExtraction] Step 2c: count unique anomalous pods, SQL: {pod_stmt}")
            async with PGManager.session() as session:
                unique_pod_count = (await session.execute(pod_stmt, {"log_id": log_id})).scalar() or 0
            print(f"[FeatureExtraction] unique_pod_count={unique_pod_count}")

            if unique_pod_count <= 1:
                pod_concentration = "single_pod"
            elif unique_pod_count <= 3:
                pod_concentration = "few_pods"
            else:
                pod_concentration = "multi_pod"

            # 2d: Operation distribution from anomalous records (needed before per-op P99/P50)
            operations = [row[-1] for row in anomalous_rows if row[-1] is not None]
            affected_operation_dist = dict(Counter(operations))

            # 2e: Per-operation P99/P50 ratio
            op_p99_p50 = {}
            if operations:
                op_tl_stmt = select(
                    LogParseResult.operation, LogParseResult.total_latency
                ).where(
                    LogParseResult.log_id == log_id,
                    LogParseResult.existed_status.is_(True),
                    LogParseResult.is_anomalous.is_(True),
                    LogParseResult.total_latency.is_not(None),
                )
                print(f"[FeatureExtraction] Step 2e: query per-op latency for P99/P50, SQL: {op_tl_stmt}")
                async with PGManager.session() as session:
                    op_tl_rows = (await session.execute(op_tl_stmt)).all()
                op_latency_map: dict[str, list[float]] = defaultdict(list)
                for op, tl in op_tl_rows:
                    if op and tl is not None:
                        op_latency_map[op].append(tl)
                for op, vals in op_latency_map.items():
                    vals_sorted = sorted(vals)
                    if len(vals_sorted) >= 2:
                        p99 = vals_sorted[int(0.99 * (len(vals_sorted) - 1))]
                        p50 = vals_sorted[int(0.50 * (len(vals_sorted) - 1))]
                        if p50 and p50 > 0:
                            op_p99_p50[op] = round(p99 / p50, 3)

            latency_features = {
                "timeout_segments": timeout_segments,
                "segment_ranking": segment_ranking,
                "p99_p50_ratio": p99_p50_ratio,
                "op_p99_p50_ratio": op_p99_p50,
                "pod_concentration": pod_concentration,
                "affected_pods_count": unique_pod_count,
                "affected_operation_dist": affected_operation_dist,
                "anomalous_ratio": anomalous_count / total_count if total_count > 0 else 0.0,
            }

        # ── Step 3: Extract connectivity features ──
        # Only records with non-empty failure_mode or non-zero/non-empty status_code
        # are real connectivity failures. Records with empty failure_mode and
        # empty/zero/"0" status_code are trace context logs of latency-anomalous
        # traces — their spatial info should feed into latency features instead.
        connectivity_features = None
        real_conn_failure_count = 0  # only true connectivity failures

        def _is_real_conn_failure(fm: str | None, sc_str: str | None) -> bool:
            """True if this record represents a real connectivity failure."""
            if fm and fm.strip():
                return True
            if sc_str and str(sc_str).strip() and str(sc_str).strip() != "0":
                return True
            return False

        # 3a: Query trace_failure_events
        trace_stmt = select(
            TraceFailureEvent.failure_mode,
            TraceFailureEvent.status_code,
            TraceFailureEvent.pod_names,
            TraceFailureEvent.host_names,
            TraceFailureEvent.cluster_names,
            TraceFailureEvent.operation,
            TraceFailureEvent.src_ip,
            TraceFailureEvent.dst_ip,
        ).where(
            TraceFailureEvent.log_id == log_id,
        )
        print(f"[FeatureExtraction] Step 3a: query trace_failure_events, SQL: {trace_stmt}")
        async with PGManager.session() as session:
            trace_rows = (await session.execute(trace_stmt)).all()

        # 3b: Query log_failure_events (fields for feature extraction)
        lfe_stmt = select(
            LogFailureEvent.failure_mode,
            LogFailureEvent.status_code,
            LogFailureEvent.pod_name,
            LogFailureEvent.host_name,
            LogFailureEvent.cluster_name,
        ).where(
            LogFailureEvent.log_id == log_id,
        ).limit(5000)
        print(f"[FeatureExtraction] Step 3b: query log_failure_events, SQL: {lfe_stmt}")
        async with PGManager.session() as session:
            lfe_rows = (await session.execute(lfe_stmt)).all()
        lfe_count = len(lfe_rows)
        print(f"[FeatureExtraction] log_failure_event_count={lfe_count}")

        # 3c: Separate real connectivity failures from trace context logs
        # TFE: row = (failure_mode, status_code[], pod_names[], host_names[], cluster_names[], operation, src_ip, dst_ip)
        # LFE: row = (failure_mode, status_code, pod_name, host_name, cluster_name)
        latency_trace_pods: set[str] = set()
        latency_trace_hosts: set[str] = set()
        latency_trace_clusters: set[str] = set()

        # Collect spatial info from TFE
        real_tfe_indices: list[int] = []
        for i, row in enumerate(trace_rows):
            fm = row[0]
            # TFE status_code is VARCHAR[] — check if any non-zero code exists
            codes = row[1]
            has_nonzero_code = any(
                c and str(c).strip() and str(c).strip() != "0"
                for c in (codes or [])
            )
            if (fm and fm.strip()) or has_nonzero_code:
                real_tfe_indices.append(i)
                real_conn_failure_count += 1
            else:
                # Trace context log — spatial info goes to latency
                for pn in (row[2] or []):
                    if pn and pn.strip():
                        latency_trace_pods.add(pn.strip())
                for hn in (row[3] or []):
                    if hn and hn.strip():
                        latency_trace_hosts.add(hn.strip())
                for cn in (row[4] or []):
                    if cn and cn.strip():
                        latency_trace_clusters.add(cn.strip())

        # Collect spatial info from LFE
        real_lfe_indices: list[int] = []
        for i, row in enumerate(lfe_rows):
            if _is_real_conn_failure(row[0], row[1]):
                real_lfe_indices.append(i)
                real_conn_failure_count += 1
            else:
                # Trace context log — spatial info goes to latency
                if row[2] and row[2].strip():
                    latency_trace_pods.add(row[2].strip())
                if row[3] and row[3].strip():
                    latency_trace_hosts.add(row[3].strip())
                if row[4] and row[4].strip():
                    latency_trace_clusters.add(row[4].strip())

        print(f"[FeatureExtraction] real_conn_failure_count={real_conn_failure_count}, latency_trace_pods={len(latency_trace_pods)}, latency_trace_hosts={len(latency_trace_hosts)}")

        # 3d: Supplement latency spatial features with trace context log spatial info
        if latency_features and (latency_trace_pods or latency_trace_hosts or latency_trace_clusters):
            # Merge into existing latency pod info
            existing_pods = latency_features.get("affected_pods_count", 0)
            # Use the larger of existing anomalous pod count and trace context pod count
            combined_pods = existing_pods  # anomalous pods from log_parse_result
            trace_pod_count = len(latency_trace_pods)
            latency_features["trace_context_pods_count"] = trace_pod_count
            latency_features["trace_context_hosts_count"] = len(latency_trace_hosts)
            latency_features["trace_context_clusters_count"] = len(latency_trace_clusters)

        # 3e: Build connectivity features ONLY from real connectivity failures
        if real_conn_failure_count > 0:
            # failure_mode_dist
            failure_mode_counter = Counter()
            for i in real_tfe_indices:
                fm = trace_rows[i][0]
                if fm:
                    for part in fm.split(","):
                        part = part.strip()
                        if part:
                            failure_mode_counter[part] += 1
            for i in real_lfe_indices:
                fm = lfe_rows[i][0]
                if fm:
                    for part in fm.split(","):
                        part = part.strip()
                        if part:
                            failure_mode_counter[part] += 1

            # status_code_dist (exclude "0" which means success)
            status_code_counter = Counter()
            for i in real_tfe_indices:
                codes = trace_rows[i][1]
                if codes:
                    for code in codes:
                        c = str(code).strip() if code else ""
                        if c and c != "0":
                            status_code_counter[c] += 1
            for i in real_lfe_indices:
                code = lfe_rows[i][1]
                c = str(code).strip() if code else ""
                if c and c != "0":
                    status_code_counter[c] += 1

            # spatial_pod (only from real failures)
            all_pods: set[str] = set()
            for i in real_tfe_indices:
                for pn in (trace_rows[i][2] or []):
                    if pn and pn.strip():
                        all_pods.add(pn.strip())
            for i in real_lfe_indices:
                if lfe_rows[i][2] and lfe_rows[i][2].strip():
                    all_pods.add(lfe_rows[i][2].strip())
            unique_pod_count_conn = len(all_pods)
            if unique_pod_count_conn <= 1:
                pod_scope = "single_pod"
            elif unique_pod_count_conn <= 3:
                pod_scope = "few_pods"
            else:
                pod_scope = "multi_pod"
            spatial_pod = {"unique_count": unique_pod_count_conn, "scope": pod_scope}

            # spatial_host (only from real failures)
            all_hosts: set[str] = set()
            for i in real_tfe_indices:
                for hn in (trace_rows[i][3] or []):
                    if hn and hn.strip():
                        all_hosts.add(hn.strip())
            for i in real_lfe_indices:
                if lfe_rows[i][3] and lfe_rows[i][3].strip():
                    all_hosts.add(lfe_rows[i][3].strip())
            unique_host_count = len(all_hosts)
            if unique_host_count <= 1:
                host_scope = "single_host"
            elif unique_host_count <= 3:
                host_scope = "few_hosts"
            else:
                host_scope = "multi_host"
            spatial_host = {"unique_count": unique_host_count, "scope": host_scope}

            # spatial_cluster (only from real failures)
            all_clusters: set[str] = set()
            for i in real_tfe_indices:
                for cn in (trace_rows[i][4] or []):
                    if cn and cn.strip():
                        all_clusters.add(cn.strip())
            for i in real_lfe_indices:
                if lfe_rows[i][4] and lfe_rows[i][4].strip():
                    all_clusters.add(lfe_rows[i][4].strip())
            unique_cluster_count = len(all_clusters)
            if unique_cluster_count <= 1:
                cluster_scope = "single_cluster"
            elif unique_cluster_count <= 3:
                cluster_scope = "few_clusters"
            else:
                cluster_scope = "multi_cluster"
            spatial_cluster = {"unique_count": unique_cluster_count, "scope": cluster_scope}

            # affected_operation_dist (only from real failures)
            conn_operations = [trace_rows[i][5] for i in real_tfe_indices if trace_rows[i][5] is not None]
            conn_operation_dist = dict(Counter(conn_operations))

            # src_dst_pair_count (only from real failures)
            src_dst_pairs: set[tuple[str, str]] = set()
            for i in real_tfe_indices:
                src_ip = trace_rows[i][6]
                dst_ip = trace_rows[i][7]
                src_ip_str = str(src_ip) if src_ip is not None else ""
                dst_ip_str = str(dst_ip) if dst_ip is not None else ""
                src_dst_pairs.add((src_ip_str, dst_ip_str))

            connectivity_features = {
                "failure_mode_dist": dict(failure_mode_counter),
                "status_code_dist": dict(status_code_counter),
                "spatial_pod": spatial_pod,
                "spatial_host": spatial_host,
                "spatial_cluster": spatial_cluster,
                "affected_operation_dist": conn_operation_dist,
                "src_dst_pair_count": len(src_dst_pairs),
            }

        # ── Step 4: Determine fault category ──
        if anomalous_count > 0 and real_conn_failure_count == 0:
            fault_category = "latency"
        elif anomalous_count == 0 and real_conn_failure_count > 0:
            fault_category = "connectivity"
        elif anomalous_count > 0 and real_conn_failure_count > 0:
            fault_category = "mixed"
        else:
            fault_category = "unknown"

        print(f"[FeatureExtraction] fault_category={fault_category}, anomalous={anomalous_count}, real_conn_failure={real_conn_failure_count}")

        return {
            "fault_category": fault_category,
            "latency": latency_features,
            "connectivity": connectivity_features,
            "summary": {
                "anomalous_event_count": anomalous_count,
                "failure_event_count": real_conn_failure_count,
                "total_parse_result_count": total_count,
            },
        }
