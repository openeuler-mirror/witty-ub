from latency.schemas.log import (
    SrcDstAggregatedEventDataclass,
    SrcDstAggregatedEventModel,
)
from latency.schemas.request import ListSrcDstAggregatedEventRequest
from latency.database.engine import AsyncSQLiteSingleton


def _aggregated_event_to_db_tuple(
    event: SrcDstAggregatedEventDataclass | SrcDstAggregatedEventModel,
) -> tuple:
    return (
        event.id,
        event.src_ip,
        event.dst_ip,
        event.log_id,
        event.log_parse_result_cnt,
        event.anomaly_log_parse_result_cnt,
        event.anomaly_cnt,
        event.ave_total_latency,
        event.min_total_latency,
        event.max_total_latency,
        event.p99_total_latency,
        event.p95_total_latency,
        event.ave_query_meta_latency,
        event.min_query_meta_latency,
        event.max_query_meta_latency,
        event.p99_query_meta_latency,
        event.p95_query_meta_latency,
        event.ave_urma_total_latency,
        event.min_urma_total_latency,
        event.max_urma_total_latency,
        event.p99_urma_total_latency,
        event.p95_urma_total_latency,
        event.ave_urma_link_latency,
        event.min_urma_link_latency,
        event.max_urma_link_latency,
        event.p99_urma_link_latency,
        event.p95_urma_link_latency,
        event.ave_c2w_urma_latency,
        event.min_c2w_urma_latency,
        event.max_c2w_urma_latency,
        event.p99_c2w_urma_latency,
        event.p95_c2w_urma_latency,
        event.ave_w2w_urma_latency,
        event.min_w2w_urma_latency,
        event.max_w2w_urma_latency,
        event.p99_w2w_urma_latency,
        event.p95_w2w_urma_latency,
        event.existed_status,
        event.created_at,
    )


class SrcDstAggregatedEventManager:
    """聚合事件管理器"""

    @staticmethod
    async def add_aggregated_event(event: SrcDstAggregatedEventModel) -> bool:
        """添加聚合事件"""
        sql_str = """
            INSERT INTO src_dst_aggregated_event_table (
                id, src_ip, dst_ip, log_id, log_parse_result_cnt,
                anomaly_log_parse_result_cnt, anomaly_cnt, ave_total_latency,
                min_total_latency, max_total_latency, p99_total_latency, p95_total_latency,
                ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                p99_query_meta_latency, p95_query_meta_latency, ave_urma_total_latency,
                min_urma_total_latency, max_urma_total_latency, p99_urma_total_latency,
                p95_urma_total_latency, ave_urma_link_latency, min_urma_link_latency,
                max_urma_link_latency, p99_urma_link_latency, p95_urma_link_latency,
                ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                p99_c2w_urma_latency, p95_c2w_urma_latency, ave_w2w_urma_latency,
                min_w2w_urma_latency, max_w2w_urma_latency, p99_w2w_urma_latency,
                p95_w2w_urma_latency, existed_status, created_at
            ) VALUES (
                :id, :src_ip, :dst_ip, :log_id, :log_parse_result_cnt,
                :anomaly_log_parse_result_cnt, :anomaly_cnt, :ave_total_latency,
                :min_total_latency, :max_total_latency, :p99_total_latency, :p95_total_latency,
                :ave_query_meta_latency, :min_query_meta_latency, :max_query_meta_latency,
                :p99_query_meta_latency, :p95_query_meta_latency, :ave_urma_total_latency,
                :min_urma_total_latency, :max_urma_total_latency, :p99_urma_total_latency,
                :p95_urma_total_latency, :ave_urma_link_latency, :min_urma_link_latency,
                :max_urma_link_latency, :p99_urma_link_latency, :p95_urma_link_latency,
                :ave_c2w_urma_latency, :min_c2w_urma_latency, :max_c2w_urma_latency,
                :p99_c2w_urma_latency, :p95_c2w_urma_latency, :ave_w2w_urma_latency,
                :min_w2w_urma_latency, :max_w2w_urma_latency, :p99_w2w_urma_latency,
                :p95_w2w_urma_latency, :existed_status, :created_at
            )
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            sql_str, event.model_dump(exclude_none=False, by_alias=True)
        )
        return success

    @staticmethod
    async def add_aggregated_events(
        events: list[SrcDstAggregatedEventDataclass]
        | list[SrcDstAggregatedEventModel],
        batch_size: int = 50000,
    ) -> list[str]:
        """批量添加聚合事件：全局单事务 + SQLite写入优化 + 线程安全修复"""
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not events:
            return []
            
        ids_added = [event.id for event in events]
        total_count = len(events)
        db = AsyncSQLiteSingleton()
        
        async with db._async_lock:
            def sync_batch_insert():
                db.ensure_initialized()
                conn = db._write_conn
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                    conn.execute("PRAGMA cache_size = -65536;")
                    conn.execute("PRAGMA temp_store = MEMORY;")
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    
                    conn.execute("BEGIN TRANSACTION;")
                    
                    sql_str = """
                        INSERT INTO src_dst_aggregated_event_table (
                            id, src_ip, dst_ip, log_id, log_parse_result_cnt,
                            anomaly_log_parse_result_cnt, anomaly_cnt, ave_total_latency,
                            min_total_latency, max_total_latency, p99_total_latency, p95_total_latency,
                            ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                            p99_query_meta_latency, p95_query_meta_latency, ave_urma_total_latency,
                            min_urma_total_latency, max_urma_total_latency, p99_urma_total_latency,
                            p95_urma_total_latency, ave_urma_link_latency, min_urma_link_latency,
                            max_urma_link_latency, p99_urma_link_latency, p95_urma_link_latency,
                            ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                            p99_c2w_urma_latency, p95_c2w_urma_latency, ave_w2w_urma_latency,
                            min_w2w_urma_latency, max_w2w_urma_latency, p99_w2w_urma_latency,
                            p95_w2w_urma_latency, existed_status, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    for i in range(0, total_count, batch_size):
                        end = min(i + batch_size, total_count)
                        batch = (
                            _aggregated_event_to_db_tuple(events[index])
                            for index in range(i, end)
                        )
                        conn.executemany(sql_str, batch)
                    
                    conn.commit()
                    logger.info(f"[Store] 单事务插入成功，共 {total_count:,} 条记录")
                    return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"[Store] 插入失败，事务回滚: {str(e)}")
                    return False
            
            success = await asyncio.to_thread(sync_batch_insert)
            return ids_added if success else []

    @staticmethod
    async def delete_aggregated_events_by_log_id(log_id: str) -> bool:
        """根据日志ID删除聚合事件"""
        sql_str = """
            UPDATE src_dst_aggregated_event_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def update_aggregated_events_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        """根据日志ID更新聚合事件的existed_status"""
        sql_str = """
            UPDATE src_dst_aggregated_event_table
            SET existed_status = :existed_status
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id, "existed_status": existed_status}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def list_aggregated_events(
        req: ListSrcDstAggregatedEventRequest,
    ) -> tuple[int, list[SrcDstAggregatedEventModel]]:
        """分页查询聚合事件"""
        sql_str = """
            SELECT ae.id, ae.src_ip, ae.dst_ip, ae.log_id, ae.log_parse_result_cnt,
                ae.anomaly_log_parse_result_cnt, ae.anomaly_cnt, ae.ave_total_latency,
                ae.min_total_latency, ae.max_total_latency, ae.p99_total_latency, ae.p95_total_latency,
                ae.ave_query_meta_latency, ae.min_query_meta_latency, ae.max_query_meta_latency,
                ae.p99_query_meta_latency, ae.p95_query_meta_latency, ae.ave_urma_total_latency,
                ae.min_urma_total_latency, ae.max_urma_total_latency, ae.p99_urma_total_latency,
                ae.p95_urma_total_latency, ae.ave_urma_link_latency, ae.min_urma_link_latency,
                ae.max_urma_link_latency, ae.p99_urma_link_latency, ae.p95_urma_link_latency,
                ae.ave_c2w_urma_latency, ae.min_c2w_urma_latency, ae.max_c2w_urma_latency,
                ae.p99_c2w_urma_latency, ae.p95_c2w_urma_latency, ae.ave_w2w_urma_latency,
                ae.min_w2w_urma_latency, ae.max_w2w_urma_latency, ae.p99_w2w_urma_latency,
                ae.p95_w2w_urma_latency, ae.existed_status, ae.created_at
            FROM src_dst_aggregated_event_table ae
            LEFT JOIN log_file_table lf ON ae.log_id = lf.id
            WHERE ae.existed_status = 1
        """
        params = {}
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.log_id:
            sql_str += " AND ae.log_id = :log_id"
            params["log_id"] = req.log_id
        if req.src_ip:
            sql_str += " AND ae.src_ip LIKE :src_ip"
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            sql_str += " AND ae.dst_ip LIKE :dst_ip"
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.created_at_start:
            sql_str += " AND ae.created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND ae.created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        stat_type = req.stat_type if req.stat_type in ["p99", "p95", "ave", "min", "max"] else "ave"
        
        sort_field_mapping = {
            "total_latency": f"ae.{stat_type}_total_latency",
            "query_meta_latency": f"ae.{stat_type}_query_meta_latency",
            "urma_total_latency": f"ae.{stat_type}_urma_total_latency",
            "urma_link_latency": f"ae.{stat_type}_urma_link_latency",
            "c2w_urma_latency": f"ae.{stat_type}_c2w_urma_latency",
            "w2w_urma_latency": f"ae.{stat_type}_w2w_urma_latency",
            "src_ip": "ae.src_ip",
            "dst_ip": "ae.dst_ip",
            "anomaly_log_parse_result_cnt": "ae.anomaly_log_parse_result_cnt",
            "created_at": "ae.created_at",
        }
        
        if req.sort_fields and len(req.sort_fields) > 0:
            sort_clauses = []
            for sort_field in req.sort_fields:
                field_name = sort_field.field
                if field_name in sort_field_mapping:
                    order = "DESC" if sort_field.order == "desc" else "ASC"
                    sort_clauses.append(f"{sort_field_mapping[field_name]} {order}")
            # 如果有有效的排序字段，使用它们；否则使用默认排序
            if sort_clauses:
                sql_str += " ORDER BY " + ", ".join(sort_clauses)
            else:
                sql_str += f" ORDER BY {sort_field_mapping['total_latency']} DESC"
        else:
            sql_str += f" ORDER BY {sort_field_mapping['total_latency']} DESC"

        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        events = [SrcDstAggregatedEventModel(**row) for row in rows]
        return total, events

    @staticmethod
    async def get_aggregated_event_by_id(
        event_id: str,
    ) -> SrcDstAggregatedEventModel | None:
        """根据ID获取聚合事件"""
        sql_str = """
            SELECT id, src_ip, dst_ip, log_id, log_parse_result_cnt,
                anomaly_log_parse_result_cnt, anomaly_cnt, ave_total_latency,
                min_total_latency, max_total_latency, p99_total_latency, p95_total_latency,
                ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                p99_query_meta_latency, p95_query_meta_latency, ave_urma_total_latency,
                min_urma_total_latency, max_urma_total_latency, p99_urma_total_latency,
                p95_urma_total_latency, ave_urma_link_latency, min_urma_link_latency,
                max_urma_link_latency, p99_urma_link_latency, p95_urma_link_latency,
                ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                p99_c2w_urma_latency, p95_c2w_urma_latency, ave_w2w_urma_latency,
                min_w2w_urma_latency, max_w2w_urma_latency, p99_w2w_urma_latency,
                p95_w2w_urma_latency, existed_status, created_at
            FROM src_dst_aggregated_event_table
            WHERE id = :event_id
        """
        params = {"event_id": event_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return SrcDstAggregatedEventModel(**rows[0])
        return None

    @staticmethod
    async def list_time_window_events(
        req,
    ) -> tuple[int, list[dict]]:
        """从预计算表查询时间窗口聚合事件"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        import math

        from latency.database.managers.time_window_aggregated_event import (
            TimeWindowAggregatedEventManager,
        )

        def strip_port(ip: str) -> str:
            """去掉 IP 地址中的端口号"""
            if not ip:
                return ""
            return ip.rsplit(":", 1)[0] if ":" in ip else ip

        def calc_percentile(sorted_vals: list[float], pct: float) -> float | None:
            if not sorted_vals:
                return None
            sorted_vals.sort()
            k = (pct / 100) * (len(sorted_vals) - 1)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_vals[int(k)]
            d0 = sorted_vals[int(f)] * (c - k) if int(f) < len(sorted_vals) else 0
            d1 = sorted_vals[int(c)] * (k - f) if int(c) < len(sorted_vals) else 0
            return d0 + d1

        def get_bucket_key(time_bucket: str, interval: str) -> str:
            """根据 interval 截断时间戳，生成分组 key"""
            if interval == "hour":
                return time_bucket[:13] + ":00:00"
            elif interval == "minute":
                return time_bucket[:16] + ":00"
            else:
                return time_bucket

        rows = await TimeWindowAggregatedEventManager.get_time_window_events(
            kb_id=req.kb_id or "",
            start_time=req.start_time or "",
            end_time=req.end_time or "",
            src_ip=req.src_ip or None,
            dst_ip=req.dst_ip or None,
        )

        if not rows:
            return 0, []

        interval_delta = {
            "second": timedelta(seconds=1),
            "minute": timedelta(minutes=1),
            "hour": timedelta(hours=1),
        }.get(req.interval, timedelta(minutes=1))

        time_buckets: dict[str, dict] = defaultdict(lambda: {
            "start_time": "",
            "end_time": "",
            "total_cnt": 0,
            "anomaly_cnt": 0,
            "ip_pairs": [],
            "ave_total_latencies": [],
            "min_total_latencies": [],
            "max_total_latencies": [],
            "p99_total_latencies": [],
            "p95_total_latencies": [],
            "ave_query_meta_latencies": [],
            "p99_query_meta_latencies": [],
            "p95_query_meta_latencies": [],
            "ave_urma_total_latencies": [],
            "p99_urma_total_latencies": [],
            "p95_urma_total_latencies": [],
            "ave_urma_link_latencies": [],
            "p99_urma_link_latencies": [],
            "p95_urma_link_latencies": [],
            "ave_c2w_urma_latencies": [],
            "p99_c2w_urma_latencies": [],
            "p95_c2w_urma_latencies": [],
            "ave_w2w_urma_latencies": [],
            "p99_w2w_urma_latencies": [],
            "p95_w2w_urma_latencies": [],
        })

        ip_pair_keys: dict[tuple[str, str], list[dict]] = defaultdict(list)

        for row in rows:
            bucket_key = get_bucket_key(row["time_bucket"], req.interval)
            tb = bucket_key

            if tb not in time_buckets:
                try:
                    start_dt = datetime.strptime(tb, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    start_dt = datetime.strptime(tb, "%Y-%m-%d %H:%M:00")
                end_dt = start_dt + interval_delta
                time_buckets[tb]["start_time"] = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                time_buckets[tb]["end_time"] = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            bucket = time_buckets[tb]
            cnt = row["log_parse_result_cnt"] or 0
            anomaly_cnt = row["anomaly_cnt"] or 0
            bucket["total_cnt"] += cnt
            bucket["anomaly_cnt"] += anomaly_cnt

            if row["ave_total_latency"] is not None:
                bucket["ave_total_latencies"].append(row["ave_total_latency"])
            if row["min_total_latency"] is not None:
                bucket["min_total_latencies"].append(row["min_total_latency"])
            if row["max_total_latency"] is not None:
                bucket["max_total_latencies"].append(row["max_total_latency"])
            if row["p99_total_latency"] is not None:
                bucket["p99_total_latencies"].append(row["p99_total_latency"])
            if row["p95_total_latency"] is not None:
                bucket["p95_total_latencies"].append(row["p95_total_latency"])

            if row["ave_query_meta_latency"] is not None:
                bucket["ave_query_meta_latencies"].append(row["ave_query_meta_latency"])
            if row["p99_query_meta_latency"] is not None:
                bucket["p99_query_meta_latencies"].append(row["p99_query_meta_latency"])
            if row["p95_query_meta_latency"] is not None:
                bucket["p95_query_meta_latencies"].append(row["p95_query_meta_latency"])

            if row["ave_urma_total_latency"] is not None:
                bucket["ave_urma_total_latencies"].append(row["ave_urma_total_latency"])
            if row["p99_urma_total_latency"] is not None:
                bucket["p99_urma_total_latencies"].append(row["p99_urma_total_latency"])
            if row["p95_urma_total_latency"] is not None:
                bucket["p95_urma_total_latencies"].append(row["p95_urma_total_latency"])

            if row["ave_urma_link_latency"] is not None:
                bucket["ave_urma_link_latencies"].append(row["ave_urma_link_latency"])
            if row["p99_urma_link_latency"] is not None:
                bucket["p99_urma_link_latencies"].append(row["p99_urma_link_latency"])
            if row["p95_urma_link_latency"] is not None:
                bucket["p95_urma_link_latencies"].append(row["p95_urma_link_latency"])

            if row["ave_c2w_urma_latency"] is not None:
                bucket["ave_c2w_urma_latencies"].append(row["ave_c2w_urma_latency"])
            if row["p99_c2w_urma_latency"] is not None:
                bucket["p99_c2w_urma_latencies"].append(row["p99_c2w_urma_latency"])
            if row["p95_c2w_urma_latency"] is not None:
                bucket["p95_c2w_urma_latencies"].append(row["p95_c2w_urma_latency"])

            if row["ave_w2w_urma_latency"] is not None:
                bucket["ave_w2w_urma_latencies"].append(row["ave_w2w_urma_latency"])
            if row["p99_w2w_urma_latency"] is not None:
                bucket["p99_w2w_urma_latencies"].append(row["p99_w2w_urma_latency"])
            if row["p95_w2w_urma_latency"] is not None:
                bucket["p95_w2w_urma_latencies"].append(row["p95_w2w_urma_latency"])

            ip_pair_key = (strip_port(row["src_ip"] or ""), strip_port(row["dst_ip"] or ""))
            ip_pair_keys[ip_pair_key].append({
                "row": row,
                "bucket_key": bucket_key,
                "cnt": cnt,
                "anomaly_cnt": anomaly_cnt,
            })

        for ip_pair_key, entries in ip_pair_keys.items():
            src_ip, dst_ip = ip_pair_key

            ip_pair_group: dict[str, dict] = defaultdict(lambda: {
                "cnt": 0,
                "anomaly_cnt": 0,
                "ave_total_latencies": [],
                "min_total_latencies": [],
                "max_total_latencies": [],
                "p99_total_latencies": [],
                "p95_total_latencies": [],
                "ave_query_meta_latencies": [],
                "min_query_meta_latencies": [],
                "max_query_meta_latencies": [],
                "p99_query_meta_latencies": [],
                "p95_query_meta_latencies": [],
                "ave_urma_total_latencies": [],
                "min_urma_total_latencies": [],
                "max_urma_total_latencies": [],
                "p99_urma_total_latencies": [],
                "p95_urma_total_latencies": [],
                "ave_urma_link_latencies": [],
                "min_urma_link_latencies": [],
                "max_urma_link_latencies": [],
                "p99_urma_link_latencies": [],
                "p95_urma_link_latencies": [],
                "ave_c2w_urma_latencies": [],
                "min_c2w_urma_latencies": [],
                "max_c2w_urma_latencies": [],
                "p99_c2w_urma_latencies": [],
                "p95_c2w_urma_latencies": [],
                "ave_w2w_urma_latencies": [],
                "min_w2w_urma_latencies": [],
                "max_w2w_urma_latencies": [],
                "p99_w2w_urma_latencies": [],
                "p95_w2w_urma_latencies": [],
            })

            for entry in entries:
                bucket_key = entry["bucket_key"]
                row = entry["row"]
                cnt = entry["cnt"]
                anomaly_cnt = entry["anomaly_cnt"]

                g = ip_pair_group[bucket_key]
                g["cnt"] += cnt
                g["anomaly_cnt"] += anomaly_cnt

                if row["ave_total_latency"] is not None:
                    g["ave_total_latencies"].append(row["ave_total_latency"])
                if row["min_total_latency"] is not None:
                    g["min_total_latencies"].append(row["min_total_latency"])
                if row["max_total_latency"] is not None:
                    g["max_total_latencies"].append(row["max_total_latency"])
                if row["p99_total_latency"] is not None:
                    g["p99_total_latencies"].append(row["p99_total_latency"])
                if row["p95_total_latency"] is not None:
                    g["p95_total_latencies"].append(row["p95_total_latency"])

                if row["ave_query_meta_latency"] is not None:
                    g["ave_query_meta_latencies"].append(row["ave_query_meta_latency"])
                if row["min_query_meta_latency"] is not None:
                    g["min_query_meta_latencies"].append(row["min_query_meta_latency"])
                if row["max_query_meta_latency"] is not None:
                    g["max_query_meta_latencies"].append(row["max_query_meta_latency"])
                if row["p99_query_meta_latency"] is not None:
                    g["p99_query_meta_latencies"].append(row["p99_query_meta_latency"])
                if row["p95_query_meta_latency"] is not None:
                    g["p95_query_meta_latencies"].append(row["p95_query_meta_latency"])

                if row["ave_urma_total_latency"] is not None:
                    g["ave_urma_total_latencies"].append(row["ave_urma_total_latency"])
                if row["min_urma_total_latency"] is not None:
                    g["min_urma_total_latencies"].append(row["min_urma_total_latency"])
                if row["max_urma_total_latency"] is not None:
                    g["max_urma_total_latencies"].append(row["max_urma_total_latency"])
                if row["p99_urma_total_latency"] is not None:
                    g["p99_urma_total_latencies"].append(row["p99_urma_total_latency"])
                if row["p95_urma_total_latency"] is not None:
                    g["p95_urma_total_latencies"].append(row["p95_urma_total_latency"])

                if row["ave_urma_link_latency"] is not None:
                    g["ave_urma_link_latencies"].append(row["ave_urma_link_latency"])
                if row["min_urma_link_latency"] is not None:
                    g["min_urma_link_latencies"].append(row["min_urma_link_latency"])
                if row["max_urma_link_latency"] is not None:
                    g["max_urma_link_latencies"].append(row["max_urma_link_latency"])
                if row["p99_urma_link_latency"] is not None:
                    g["p99_urma_link_latencies"].append(row["p99_urma_link_latency"])
                if row["p95_urma_link_latency"] is not None:
                    g["p95_urma_link_latencies"].append(row["p95_urma_link_latency"])

                if row["ave_c2w_urma_latency"] is not None:
                    g["ave_c2w_urma_latencies"].append(row["ave_c2w_urma_latency"])
                if row["min_c2w_urma_latency"] is not None:
                    g["min_c2w_urma_latencies"].append(row["min_c2w_urma_latency"])
                if row["max_c2w_urma_latency"] is not None:
                    g["max_c2w_urma_latencies"].append(row["max_c2w_urma_latency"])
                if row["p99_c2w_urma_latency"] is not None:
                    g["p99_c2w_urma_latencies"].append(row["p99_c2w_urma_latency"])
                if row["p95_c2w_urma_latency"] is not None:
                    g["p95_c2w_urma_latencies"].append(row["p95_c2w_urma_latency"])

                if row["ave_w2w_urma_latency"] is not None:
                    g["ave_w2w_urma_latencies"].append(row["ave_w2w_urma_latency"])
                if row["min_w2w_urma_latency"] is not None:
                    g["min_w2w_urma_latencies"].append(row["min_w2w_urma_latency"])
                if row["max_w2w_urma_latency"] is not None:
                    g["max_w2w_urma_latencies"].append(row["max_w2w_urma_latency"])
                if row["p99_w2w_urma_latency"] is not None:
                    g["p99_w2w_urma_latencies"].append(row["p99_w2w_urma_latency"])
                if row["p95_w2w_urma_latency"] is not None:
                    g["p95_w2w_urma_latencies"].append(row["p95_w2w_urma_latency"])

            for bucket_key, g in ip_pair_group.items():
                aves = g["ave_total_latencies"]
                mins = g["min_total_latencies"]
                maxs = g["max_total_latencies"]
                p99s = g["p99_total_latencies"]
                p95s = g["p95_total_latencies"]

                ip_pair = {
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "log_parse_result_cnt": g["cnt"],
                    "anomaly_log_parse_result_cnt": g["anomaly_cnt"],
                    "anomaly_cnt": g["anomaly_cnt"],
                    "ave_total_latency": sum(aves) / len(aves) if aves else None,
                    "min_total_latency": min(mins) if mins else None,
                    "max_total_latency": max(maxs) if maxs else None,
                    "p99_total_latency": calc_percentile(p99s[:], 99) if p99s else None,
                    "p95_total_latency": calc_percentile(p95s[:], 95) if p95s else None,
                }

                aves_qm = g["ave_query_meta_latencies"]
                mins_qm = g["min_query_meta_latencies"]
                maxs_qm = g["max_query_meta_latencies"]
                p99s_qm = g["p99_query_meta_latencies"]
                p95s_qm = g["p95_query_meta_latencies"]
                ip_pair["ave_query_meta_latency"] = sum(aves_qm) / len(aves_qm) if aves_qm else None
                ip_pair["min_query_meta_latency"] = min(mins_qm) if mins_qm else None
                ip_pair["max_query_meta_latency"] = max(maxs_qm) if maxs_qm else None
                ip_pair["p99_query_meta_latency"] = calc_percentile(p99s_qm[:], 99) if p99s_qm else None
                ip_pair["p95_query_meta_latency"] = calc_percentile(p95s_qm[:], 95) if p95s_qm else None

                aves_ut = g["ave_urma_total_latencies"]
                mins_ut = g["min_urma_total_latencies"]
                maxs_ut = g["max_urma_total_latencies"]
                p99s_ut = g["p99_urma_total_latencies"]
                p95s_ut = g["p95_urma_total_latencies"]
                ip_pair["ave_urma_total_latency"] = sum(aves_ut) / len(aves_ut) if aves_ut else None
                ip_pair["min_urma_total_latency"] = min(mins_ut) if mins_ut else None
                ip_pair["max_urma_total_latency"] = max(maxs_ut) if maxs_ut else None
                ip_pair["p99_urma_total_latency"] = calc_percentile(p99s_ut[:], 99) if p99s_ut else None
                ip_pair["p95_urma_total_latency"] = calc_percentile(p95s_ut[:], 95) if p95s_ut else None

                aves_ul = g["ave_urma_link_latencies"]
                mins_ul = g["min_urma_link_latencies"]
                maxs_ul = g["max_urma_link_latencies"]
                p99s_ul = g["p99_urma_link_latencies"]
                p95s_ul = g["p95_urma_link_latencies"]
                ip_pair["ave_urma_link_latency"] = sum(aves_ul) / len(aves_ul) if aves_ul else None
                ip_pair["min_urma_link_latency"] = min(mins_ul) if mins_ul else None
                ip_pair["max_urma_link_latency"] = max(maxs_ul) if maxs_ul else None
                ip_pair["p99_urma_link_latency"] = calc_percentile(p99s_ul[:], 99) if p99s_ul else None
                ip_pair["p95_urma_link_latency"] = calc_percentile(p95s_ul[:], 95) if p95s_ul else None

                aves_c2w = g["ave_c2w_urma_latencies"]
                mins_c2w = g["min_c2w_urma_latencies"]
                maxs_c2w = g["max_c2w_urma_latencies"]
                p99s_c2w = g["p99_c2w_urma_latencies"]
                p95s_c2w = g["p95_c2w_urma_latencies"]
                ip_pair["ave_c2w_urma_latency"] = sum(aves_c2w) / len(aves_c2w) if aves_c2w else None
                ip_pair["min_c2w_urma_latency"] = min(mins_c2w) if mins_c2w else None
                ip_pair["max_c2w_urma_latency"] = max(maxs_c2w) if maxs_c2w else None
                ip_pair["p99_c2w_urma_latency"] = calc_percentile(p99s_c2w[:], 99) if p99s_c2w else None
                ip_pair["p95_c2w_urma_latency"] = calc_percentile(p95s_c2w[:], 95) if p95s_c2w else None

                aves_w2w = g["ave_w2w_urma_latencies"]
                mins_w2w = g["min_w2w_urma_latencies"]
                maxs_w2w = g["max_w2w_urma_latencies"]
                p99s_w2w = g["p99_w2w_urma_latencies"]
                p95s_w2w = g["p95_w2w_urma_latencies"]
                ip_pair["ave_w2w_urma_latency"] = sum(aves_w2w) / len(aves_w2w) if aves_w2w else None
                ip_pair["min_w2w_urma_latency"] = min(mins_w2w) if mins_w2w else None
                ip_pair["max_w2w_urma_latency"] = max(maxs_w2w) if maxs_w2w else None
                ip_pair["p99_w2w_urma_latency"] = calc_percentile(p99s_w2w[:], 99) if p99s_w2w else None
                ip_pair["p95_w2w_urma_latency"] = calc_percentile(p95s_w2w[:], 95) if p95s_w2w else None

                time_buckets[bucket_key]["ip_pairs"].append(ip_pair)

        for tb in time_buckets:
            bucket = time_buckets[tb]
            bucket["ip_pairs"].sort(key=lambda x: x.get("p99_total_latency", 0) or 0, reverse=True)

        events = []
        for tb in sorted(time_buckets.keys()):
            bucket = time_buckets[tb]

            aves = bucket["ave_total_latencies"]
            mins = bucket["min_total_latencies"]
            maxs = bucket["max_total_latencies"]
            p99s = bucket["p99_total_latencies"]
            p95s = bucket["p95_total_latencies"]

            aves_qm = bucket["ave_query_meta_latencies"]
            p99s_qm = bucket["p99_query_meta_latencies"]
            p95s_qm = bucket["p95_query_meta_latencies"]

            aves_ut = bucket["ave_urma_total_latencies"]
            p99s_ut = bucket["p99_urma_total_latencies"]
            p95s_ut = bucket["p95_urma_total_latencies"]

            aves_ul = bucket["ave_urma_link_latencies"]
            p99s_ul = bucket["p99_urma_link_latencies"]
            p95s_ul = bucket["p95_urma_link_latencies"]

            aves_c2w = bucket["ave_c2w_urma_latencies"]
            p99s_c2w = bucket["p99_c2w_urma_latencies"]
            p95s_c2w = bucket["p95_c2w_urma_latencies"]

            aves_w2w = bucket["ave_w2w_urma_latencies"]
            p99s_w2w = bucket["p99_w2w_urma_latencies"]
            p95s_w2w = bucket["p95_w2w_urma_latencies"]

            events.append({
                "start_time": bucket["start_time"],
                "end_time": bucket["end_time"],
                "total_cnt": bucket["total_cnt"],
                "anomaly_cnt": bucket["anomaly_cnt"],
                "ave_total_latency": sum(aves) / len(aves) if aves else None,
                "min_total_latency": min(mins) if mins else None,
                "max_total_latency": max(maxs) if maxs else None,
                "p99_total_latency": calc_percentile(p99s[:], 99) if p99s else None,
                "p95_total_latency": calc_percentile(p95s[:], 95) if p95s else None,
                "ave_query_meta_latency": sum(aves_qm) / len(aves_qm) if aves_qm else None,
                "p99_query_meta_latency": calc_percentile(p99s_qm[:], 99) if p99s_qm else None,
                "p95_query_meta_latency": calc_percentile(p95s_qm[:], 95) if p95s_qm else None,
                "ave_urma_total_latency": sum(aves_ut) / len(aves_ut) if aves_ut else None,
                "p99_urma_total_latency": calc_percentile(p99s_ut[:], 99) if p99s_ut else None,
                "p95_urma_total_latency": calc_percentile(p95s_ut[:], 95) if p95s_ut else None,
                "ave_urma_link_latency": sum(aves_ul) / len(aves_ul) if aves_ul else None,
                "p99_urma_link_latency": calc_percentile(p99s_ul[:], 99) if p99s_ul else None,
                "p95_urma_link_latency": calc_percentile(p95s_ul[:], 95) if p95s_ul else None,
                "ave_c2w_urma_latency": sum(aves_c2w) / len(aves_c2w) if aves_c2w else None,
                "p99_c2w_urma_latency": calc_percentile(p99s_c2w[:], 99) if p99s_c2w else None,
                "p95_c2w_urma_latency": calc_percentile(p95s_c2w[:], 95) if p95s_c2w else None,
                "ave_w2w_urma_latency": sum(aves_w2w) / len(aves_w2w) if aves_w2w else None,
                "p99_w2w_urma_latency": calc_percentile(p99s_w2w[:], 99) if p99s_w2w else None,
                "p95_w2w_urma_latency": calc_percentile(p95s_w2w[:], 95) if p95s_w2w else None,
                "ip_pairs": bucket["ip_pairs"],
            })

        if req.sort_by == "start_time":
            reverse = req.sort_order == "desc"
            events.sort(key=lambda e: e["start_time"], reverse=reverse)
        elif req.sort_by == "total_latency":
            reverse = True if req.sort_order == "desc" else False
            events.sort(
                key=lambda e: e["ave_total_latency"] or 0,
                reverse=reverse,
            )

        total = len(events)

        offset = (req.page_num - 1) * req.page_cnt
        events = events[offset : offset + req.page_cnt]

        return total, events
