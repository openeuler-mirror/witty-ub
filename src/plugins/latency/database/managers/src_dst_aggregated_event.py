from latency.schemas.log import SrcDstAggregatedEventModel
from latency.schemas.request import ListSrcDstAggregatedEventRequest
from latency.database.engine import AsyncSQLiteSingleton


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
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, event.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def add_aggregated_events(
        events: list[SrcDstAggregatedEventModel],
        batch_size: int = 50000,
    ) -> list[str]:
        """批量添加聚合事件：全局单事务 + SQLite写入优化 + 线程安全修复"""
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not events:
            return []
            
        ids_added = [event.id for event in events]
        params = [event.model_dump(exclude_none=False, by_alias=True) for event in events]
        total_count = len(params)
        db = AsyncSQLiteSingleton()
        
        async with db._async_lock:
            def sync_batch_insert():
                conn = db._conn
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                    conn.execute("PRAGMA cache_size = -7500;")
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
                    for i in range(0, total_count, batch_size):
                        batch = params[i:i + batch_size]
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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        """按时间窗口聚合 log_parse_result_table，返回时间窗口列表，每个包含 IP 对子聚合"""
        from collections import defaultdict
        from datetime import datetime, timedelta

        def strip_port(ip: str) -> str:
            """去掉 IP 地址中的端口号"""
            if not ip:
                return ""
            return ip.rsplit(":", 1)[0] if ":" in ip else ip

        # 1. 确定时间格式化 SQL
        if req.interval == "second":
            time_format_sql = "%Y-%m-%d %H:%M:%S"
        elif req.interval == "hour":
            time_format_sql = "%Y-%m-%d %H:00:00"
        else:
            time_format_sql = "%Y-%m-%d %H:%M:00"

        # 2. 构建基础 SQL
        sql_parts = [
            f"strftime('{time_format_sql}', timestamp) AS time_bucket",
            "src_ip",
            "dst_ip",
            "COUNT(*) AS cnt",
            "SUM(CASE WHEN is_anomalous THEN 1 ELSE 0 END) AS anomaly_cnt",
            "AVG(total_latency) AS ave_total_latency",
            "MIN(total_latency) AS min_total_latency",
            "MAX(total_latency) AS max_total_latency",
            "AVG(worker_query_meta_latency) AS ave_query_meta_latency",
            "MIN(worker_query_meta_latency) AS min_query_meta_latency",
            "MAX(worker_query_meta_latency) AS max_query_meta_latency",
            "AVG(urma_total_latency) AS ave_urma_total_latency",
            "MIN(urma_total_latency) AS min_urma_total_latency",
            "MAX(urma_total_latency) AS max_urma_total_latency",
            "AVG(urma_link_latency) AS ave_urma_link_latency",
            "MIN(urma_link_latency) AS min_urma_link_latency",
            "MAX(urma_link_latency) AS max_urma_link_latency",
            "AVG(c2w_urma_latency) AS ave_c2w_urma_latency",
            "MIN(c2w_urma_latency) AS min_c2w_urma_latency",
            "MAX(c2w_urma_latency) AS max_c2w_urma_latency",
            "AVG(w2w_urma_latency) AS ave_w2w_urma_latency",
            "MIN(w2w_urma_latency) AS min_w2w_urma_latency",
            "MAX(w2w_urma_latency) AS max_w2w_urma_latency",
        ]

        sql_str = f"""
            SELECT {', '.join(sql_parts)}
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.existed_status = 1
              AND lpr.src_ip IS NOT NULL AND lpr.src_ip != ''
              AND lpr.dst_ip IS NOT NULL AND lpr.dst_ip != ''
        """
        params: dict[str, str] = {}

        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.start_time:
            sql_str += " AND lpr.timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND lpr.timestamp <= :end_time"
            params["end_time"] = req.end_time
        if req.src_ip:
            sql_str += " AND lpr.src_ip = :src_ip"
            params["src_ip"] = req.src_ip
        if req.dst_ip:
            sql_str += " AND lpr.dst_ip = :dst_ip"
            params["dst_ip"] = req.dst_ip

        sql_str += " GROUP BY time_bucket, src_ip, dst_ip"
        sql_str += " ORDER BY time_bucket ASC, src_ip ASC, dst_ip ASC"

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)

        if not rows:
            return 0, []

        # 3. 计算 P99/P95（需要从原始数据计算，这里用估计值 SQLite 没有 PERCENTILE）
        # 先用 AVG/MIN/MAX 填充，P99/P95 在 Python 层单独计算
        # 获取所有分组的唯一统计值列表用于 P99/P95
        import math

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

        # 4. 按时间窗口分组
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
            "total_latency_values": [],
            "query_meta_values": [],
            "urma_total_values": [],
            "urma_link_values": [],
            "c2w_urma_values": [],
            "w2w_urma_values": [],
            "ip_pairs": [],
        })

        for row in rows:
            tb = row["time_bucket"]
            if tb not in time_buckets:
                try:
                    start_dt = datetime.strptime(tb, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    start_dt = datetime.strptime(tb, "%Y-%m-%d %H:%M:00")
                end_dt = start_dt + interval_delta
                time_buckets[tb]["start_time"] = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                time_buckets[tb]["end_time"] = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            bucket = time_buckets[tb]
            cnt = row["cnt"] or 0
            anomaly_cnt = row["anomaly_cnt"] or 0
            bucket["total_cnt"] += cnt
            bucket["anomaly_cnt"] += anomaly_cnt

            # 收集值用于 P99/P95 计算
            if row["ave_total_latency"] is not None:
                for _ in range(cnt):
                    bucket["total_latency_values"].append(row["ave_total_latency"])
            if row["ave_query_meta_latency"] is not None:
                for _ in range(cnt):
                    bucket["query_meta_values"].append(row["ave_query_meta_latency"])
            if row["ave_urma_total_latency"] is not None:
                for _ in range(cnt):
                    bucket["urma_total_values"].append(row["ave_urma_total_latency"])
            if row["ave_urma_link_latency"] is not None:
                for _ in range(cnt):
                    bucket["urma_link_values"].append(row["ave_urma_link_latency"])
            if row["ave_c2w_urma_latency"] is not None:
                for _ in range(cnt):
                    bucket["c2w_urma_values"].append(row["ave_c2w_urma_latency"])
            if row["ave_w2w_urma_latency"] is not None:
                for _ in range(cnt):
                    bucket["w2w_urma_values"].append(row["ave_w2w_urma_latency"])

            ip_pair = {
                "src_ip": strip_port(row["src_ip"] or ""),
                "dst_ip": strip_port(row["dst_ip"] or ""),
                "log_parse_result_cnt": cnt,
                "anomaly_log_parse_result_cnt": anomaly_cnt,
                "anomaly_cnt": anomaly_cnt,
                "ave_total_latency": row["ave_total_latency"],
                "min_total_latency": row["min_total_latency"],
                "max_total_latency": row["max_total_latency"],
                "p99_total_latency": None,
                "p95_total_latency": None,
                "ave_query_meta_latency": row["ave_query_meta_latency"],
                "min_query_meta_latency": row["min_query_meta_latency"],
                "max_query_meta_latency": row["max_query_meta_latency"],
                "p99_query_meta_latency": None,
                "p95_query_meta_latency": None,
                "ave_urma_total_latency": row["ave_urma_total_latency"],
                "min_urma_total_latency": row["min_urma_total_latency"],
                "max_urma_total_latency": row["max_urma_total_latency"],
                "p99_urma_total_latency": None,
                "p95_urma_total_latency": None,
                "ave_urma_link_latency": row["ave_urma_link_latency"],
                "min_urma_link_latency": row["min_urma_link_latency"],
                "max_urma_link_latency": row["max_urma_link_latency"],
                "p99_urma_link_latency": None,
                "p95_urma_link_latency": None,
                "ave_c2w_urma_latency": row["ave_c2w_urma_latency"],
                "min_c2w_urma_latency": row["min_c2w_urma_latency"],
                "max_c2w_urma_latency": row["max_c2w_urma_latency"],
                "p99_c2w_urma_latency": None,
                "p95_c2w_urma_latency": None,
                "ave_w2w_urma_latency": row["ave_w2w_urma_latency"],
                "min_w2w_urma_latency": row["min_w2w_urma_latency"],
                "max_w2w_urma_latency": row["max_w2w_urma_latency"],
                "p99_w2w_urma_latency": None,
                "p95_w2w_urma_latency": None,
            }
            bucket["ip_pairs"].append(ip_pair)

        # 5. 从 log_parse_result_table 查询每个 IP 对的原始时延值，计算真实 P99/P95
        # 收集所有唯一的 (src_ip, dst_ip) 对
        ip_pair_keys = set()
        for bucket in time_buckets.values():
            for ip_pair in bucket["ip_pairs"]:
                ip_pair_keys.add((ip_pair["src_ip"], ip_pair["dst_ip"]))

        if ip_pair_keys and req.kb_id:
            # 构建查询条件，使用 LIKE 匹配去掉端口后的 IP
            conditions = []
            p99_params = {"kb_id": req.kb_id}
            for i, (src_ip, dst_ip) in enumerate(ip_pair_keys):
                conditions.append(
                    f"(lpr.src_ip = :src_ip_{i} OR lpr.src_ip LIKE :src_ip_{i} || ':%') AND "
                    f"(lpr.dst_ip = :dst_ip_{i} OR lpr.dst_ip LIKE :dst_ip_{i} || ':%')"
                )
                p99_params[f"src_ip_{i}"] = src_ip
                p99_params[f"dst_ip_{i}"] = dst_ip

            p99_sql = f"""
                SELECT lpr.src_ip, lpr.dst_ip,
                    lpr.total_latency, lpr.worker_query_meta_latency,
                    lpr.urma_total_latency, lpr.urma_link_latency,
                    lpr.c2w_urma_latency, lpr.w2w_urma_latency
                FROM log_parse_result_table lpr
                LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
                WHERE lpr.existed_status = 1
                  AND lf.kb_id = :kb_id
                  AND lpr.src_ip IS NOT NULL AND lpr.src_ip != ''
                  AND lpr.dst_ip IS NOT NULL AND lpr.dst_ip != ''
                  AND ({' OR '.join([f'({c})' for c in conditions])})
            """
            if req.start_time:
                p99_sql += " AND lpr.timestamp >= :start_time"
                p99_params["start_time"] = req.start_time
            if req.end_time:
                p99_sql += " AND lpr.timestamp <= :end_time"
                p99_params["end_time"] = req.end_time

            p99_rows = await AsyncSQLiteSingleton().execute_query(p99_sql, p99_params)

            # 按 (src_ip, dst_ip) 分组收集值
            ip_pair_vals: dict[tuple[str, str], dict[str, list[float]]] = {}
            for row in p99_rows:
                key = (strip_port(row["src_ip"] or ""), strip_port(row["dst_ip"] or ""))
                if key not in ip_pair_vals:
                    ip_pair_vals[key] = {
                        "total": [], "query_meta": [], "urma_total": [],
                        "urma_link": [], "c2w_urma": [], "w2w_urma": [],
                    }
                vals = ip_pair_vals[key]
                if row["total_latency"] is not None:
                    vals["total"].append(row["total_latency"])
                if row["worker_query_meta_latency"] is not None:
                    vals["query_meta"].append(row["worker_query_meta_latency"])
                if row["urma_total_latency"] is not None:
                    vals["urma_total"].append(row["urma_total_latency"])
                if row["urma_link_latency"] is not None:
                    vals["urma_link"].append(row["urma_link_latency"])
                if row["c2w_urma_latency"] is not None:
                    vals["c2w_urma"].append(row["c2w_urma_latency"])
                if row["w2w_urma_latency"] is not None:
                    vals["w2w_urma"].append(row["w2w_urma_latency"])

            # 更新 IP 对的 P99/P95 值
            for bucket in time_buckets.values():
                for ip_pair in bucket["ip_pairs"]:
                    key = (ip_pair["src_ip"], ip_pair["dst_ip"])
                    vals = ip_pair_vals.get(key)
                    if vals:
                        ip_pair["p99_total_latency"] = calc_percentile(vals["total"], 99)
                        ip_pair["p95_total_latency"] = calc_percentile(vals["total"], 95)
                        ip_pair["p99_query_meta_latency"] = calc_percentile(vals["query_meta"], 99)
                        ip_pair["p95_query_meta_latency"] = calc_percentile(vals["query_meta"], 95)
                        ip_pair["p99_urma_total_latency"] = calc_percentile(vals["urma_total"], 99)
                        ip_pair["p95_urma_total_latency"] = calc_percentile(vals["urma_total"], 95)
                        ip_pair["p99_urma_link_latency"] = calc_percentile(vals["urma_link"], 99)
                        ip_pair["p95_urma_link_latency"] = calc_percentile(vals["urma_link"], 95)
                        ip_pair["p99_c2w_urma_latency"] = calc_percentile(vals["c2w_urma"], 99)
                        ip_pair["p95_c2w_urma_latency"] = calc_percentile(vals["c2w_urma"], 95)
                        ip_pair["p99_w2w_urma_latency"] = calc_percentile(vals["w2w_urma"], 99)
                        ip_pair["p95_w2w_urma_latency"] = calc_percentile(vals["w2w_urma"], 95)

        # 6. 构建最终结果
        events = []
        for tb in sorted(time_buckets.keys()):
            bucket = time_buckets[tb]
            vals = bucket["total_latency_values"]
            query_vals = bucket["query_meta_values"]
            urma_total_vals = bucket["urma_total_values"]
            urma_link_vals = bucket["urma_link_values"]
            c2w_urma_vals = bucket["c2w_urma_values"]
            w2w_urma_vals = bucket["w2w_urma_values"]
            bucket["total_latency_values"] = []
            bucket["query_meta_values"] = []
            bucket["urma_total_values"] = []
            bucket["urma_link_values"] = []
            bucket["c2w_urma_values"] = []
            bucket["w2w_urma_values"] = []

            avg_total = sum(vals) / len(vals) if vals else None
            events.append({
                "start_time": bucket["start_time"],
                "end_time": bucket["end_time"],
                "total_cnt": bucket["total_cnt"],
                "anomaly_cnt": bucket["anomaly_cnt"],
                "ave_total_latency": avg_total,
                "min_total_latency": min(vals) if vals else None,
                "max_total_latency": max(vals) if vals else None,
                "p99_total_latency": calc_percentile(vals[:], 99),
                "p95_total_latency": calc_percentile(vals[:], 95),
                "ave_query_meta_latency": (
                    sum(query_vals) / len(query_vals)
                    if query_vals else None
                ),
                "p99_query_meta_latency": calc_percentile(query_vals[:], 99),
                "p95_query_meta_latency": calc_percentile(query_vals[:], 95),
                "ave_urma_total_latency": (
                    sum(urma_total_vals) / len(urma_total_vals)
                    if urma_total_vals else None
                ),
                "p99_urma_total_latency": calc_percentile(urma_total_vals[:], 99),
                "p95_urma_total_latency": calc_percentile(urma_total_vals[:], 95),
                "ave_urma_link_latency": (
                    sum(urma_link_vals) / len(urma_link_vals)
                    if urma_link_vals else None
                ),
                "p99_urma_link_latency": calc_percentile(urma_link_vals[:], 99),
                "p95_urma_link_latency": calc_percentile(urma_link_vals[:], 95),
                "ave_c2w_urma_latency": (
                    sum(c2w_urma_vals) / len(c2w_urma_vals)
                    if c2w_urma_vals else None
                ),
                "p99_c2w_urma_latency": calc_percentile(c2w_urma_vals[:], 99),
                "p95_c2w_urma_latency": calc_percentile(c2w_urma_vals[:], 95),
                "ave_w2w_urma_latency": (
                    sum(w2w_urma_vals) / len(w2w_urma_vals)
                    if w2w_urma_vals else None
                ),
                "p99_w2w_urma_latency": calc_percentile(w2w_urma_vals[:], 99),
                "p95_w2w_urma_latency": calc_percentile(w2w_urma_vals[:], 95),
                "ip_pairs": bucket["ip_pairs"],
            })

        # 6. 排序
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

        # 7. 分页
        offset = (req.page_num - 1) * req.page_cnt
        events = events[offset : offset + req.page_cnt]

        return total, events
