from latency.schemas.log import LogParseResultModel
from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.database.engine import AsyncSQLiteSingleton
from typing import Optional

class LogParseResultManager:
    """日志解析结果管理器"""

    @staticmethod
    async def add_log_parse_result(result: LogParseResultModel) -> bool:
        """添加日志解析结果"""
        sql_str = """
            INSERT INTO log_parse_result_table (
                id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                timestamp, src_ip, dst_ip, pod_ip, cluster_name, host,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, operation, data_size,
                offset, is_anomalous, content, anomaly_reason, anomaly_score,
                remark, existed_status, created_at,
                sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
            ) VALUES (
                :id, :log_id, :aggregated_event_id, :anomalous_event_id, :trace_id,
                :timestamp, :src_ip, :dst_ip, :pod_ip, :cluster_name, :host,
                :total_latency, :c2w_latency, :worker_query_meta_latency,
                :urma_total_latency, :urma_link_latency, :urma_inflight_count,
                :c2w_urma_latency, :w2w_urma_latency, :operation, :data_size,
                :offset, :is_anomalous, :content, :anomaly_reason, :anomaly_score,
                :remark, :existed_status, :created_at,
                :sdk_process, :sdk_rpc, :local_worker_cost, :local_worker_lock,
                :remote_worker_cost, :remote_worker_rpc, :master_process, :master_rpc_total
            )
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, result.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def add_log_parse_results(
        results: list[LogParseResultModel],
        batch_size: int = 50000,
    ) -> list[str]:
        """批量添加日志解析结果：全局单事务 + SQLite写入优化 + 线程安全修复"""
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not results:
            return []
            
        ids_added = [r.id for r in results]
        params = [r.model_dump(exclude_none=False, by_alias=True) for r in results]
        total_count = len(params)
        db = AsyncSQLiteSingleton()
        
        # 全局协程锁，保证同一时间只有一组操作操作sqlite连接
        async with db._async_lock:
            def sync_batch_insert():
                """同步函数：全部sqlite操作放到同一个子线程，线程安全"""
                conn = db._conn
                try:
                    # 写入性能调优（事务内生效，不影响其他连接）
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                    conn.execute("PRAGMA cache_size = -7500;")  # 7.5MB缓存
                    conn.execute("PRAGMA temp_store = MEMORY;")
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    
                    # 开启统一事务
                    conn.execute("BEGIN TRANSACTION;")
                    
                    sql_str = """
                        INSERT INTO log_parse_result_table (
                            id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                            timestamp, src_ip, dst_ip, pod_ip, cluster_name, host,
                            total_latency, c2w_latency, worker_query_meta_latency,
                            urma_total_latency, urma_link_latency, urma_inflight_count,
                            c2w_urma_latency, w2w_urma_latency, operation, data_size,
                            offset, is_anomalous, content, anomaly_reason, anomaly_score,
                            remark, existed_status, created_at,
                            sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                            remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
                        ) VALUES (
                            :id, :log_id, :aggregated_event_id, :anomalous_event_id, :trace_id,
                            :timestamp, :src_ip, :dst_ip, :pod_ip, :cluster_name, :host,
                            :total_latency, :c2w_latency, :worker_query_meta_latency,
                            :urma_total_latency, :urma_link_latency, :urma_inflight_count,
                            :c2w_urma_latency, :w2w_urma_latency, :operation, :data_size,
                            :offset, :is_anomalous, :content, :anomaly_reason, :anomaly_score,
                            :remark, :existed_status, :created_at,
                            :sdk_process, :sdk_rpc, :local_worker_cost, :local_worker_lock,
                            :remote_worker_cost, :remote_worker_rpc, :master_process, :master_rpc_total
                        )
                    """
                    # 分批次插入
                    for i in range(0, total_count, batch_size):
                        batch = params[i:i + batch_size]
                        conn.executemany(sql_str, batch)
                    
                    # 一次性提交
                    conn.commit()
                    logger.info(f"[Store] 单事务插入成功，共 {total_count:,} 条记录")
                    return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"[Store] 插入失败，事务回滚: {str(e)}")
                    return False
            
            # 所有sqlite操作全部在同一个线程执行，避免多线程争抢conn
            success = await asyncio.to_thread(sync_batch_insert)
            return ids_added if success else []

    @staticmethod
    async def delete_log_parse_results_by_log_id(log_id: str) -> bool:
        """根据日志ID删除解析结果"""
        sql_str = """
            UPDATE log_parse_result_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def update_log_parse_results_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        """根据日志ID更新解析结果的existed_status"""
        sql_str = """
            UPDATE log_parse_result_table
            SET existed_status = :existed_status
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id, "existed_status": existed_status}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def list_log_parse_results(
        req: ListLogParseResultRequest,
    ) -> tuple[int, list[LogParseResultModel]]:
        """分页查询日志解析结果"""
        sql_str = """
            SELECT lpr.id, lpr.log_id, lpr.aggregated_event_id, lpr.anomalous_event_id, lpr.trace_id,
                lpr.timestamp, lpr.src_ip, lpr.dst_ip, lpr.pod_ip, lpr.cluster_name, lpr.host,
                lpr.total_latency, lpr.c2w_latency, lpr.worker_query_meta_latency,
                lpr.urma_total_latency, lpr.urma_link_latency, lpr.urma_inflight_count,
                lpr.c2w_urma_latency, lpr.w2w_urma_latency, lpr.operation, lpr.data_size,
                lpr.offset, lpr.is_anomalous, lpr.content, lpr.anomaly_reason, lpr.anomaly_score,
                lpr.remark, lpr.existed_status, lpr.created_at,
                lpr.sdk_process, lpr.sdk_rpc, lpr.local_worker_cost, lpr.local_worker_lock,
                lpr.remote_worker_cost, lpr.remote_worker_rpc, lpr.master_process, lpr.master_rpc_total
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.existed_status = 1
        """
        params = {}
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.log_id:
            sql_str += " AND lpr.log_id = :log_id"
            params["log_id"] = req.log_id
        if req.aggregated_event_id:
            sql_str += " AND lpr.aggregated_event_id = :aggregated_event_id"
            params["aggregated_event_id"] = req.aggregated_event_id
        if req.src_ip:
            sql_str += " AND lpr.src_ip LIKE :src_ip"
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            sql_str += " AND lpr.dst_ip LIKE :dst_ip"
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.host:
            sql_str += " AND lpr.host LIKE :host"
            params["host"] = f"%{req.host}%"
        if req.cluster_name:
            sql_str += " AND lpr.cluster_name LIKE :cluster_name"
            params["cluster_name"] = f"%{req.cluster_name}%"
        if req.is_anomalous is not None:
            sql_str += " AND lpr.is_anomalous = :is_anomalous"
            params["is_anomalous"] = req.is_anomalous
        if req.created_at_start:
            sql_str += " AND lpr.created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND lpr.created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end
        if req.start_time:
            sql_str += " AND lpr.timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND lpr.timestamp <= :end_time"
            params["end_time"] = req.end_time

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sort_field_mapping = {
            "total_latency": "lpr.total_latency",
            "timestamp": "lpr.timestamp",
            "trace_id": "lpr.trace_id",
            "pod_ip": "lpr.pod_ip",
            "cluster_name": "lpr.cluster_name",
            "host": "lpr.host",
            "query_meta_latency": "lpr.worker_query_meta_latency",
            "urma_total_latency": "lpr.urma_total_latency",
            "urma_link_latency": "lpr.urma_link_latency",
            "worker_query_meta_latency": "lpr.worker_query_meta_latency",
            "c2w_urma_latency": "lpr.c2w_urma_latency",
            "w2w_urma_latency": "lpr.w2w_urma_latency",
            "created_at": "lpr.created_at",
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
                sql_str += " ORDER BY lpr.total_latency DESC"
        else:
            sql_str += " ORDER BY lpr.total_latency DESC"
        
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        results = [LogParseResultModel(**row) for row in rows]
        return total, results

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> LogParseResultModel | None:
        """根据ID获取日志解析结果"""
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                timestamp, src_ip, dst_ip, pod_ip, cluster_name, host,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, operation, data_size,
                offset, is_anomalous, content, anomaly_reason, anomaly_score,
                remark, existed_status, created_at,
                sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
            FROM log_parse_result_table
            WHERE id = :result_id
        """
        params = {"result_id": result_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return LogParseResultModel(**rows[0])
        return None

    @staticmethod
    async def list_traces_by_host(
        req: ListTracesByHostRequest,
    ) -> tuple[int, list[dict]]:
        """根据主机获取trace列表"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"list_traces_by_host called with is_anomalous={req.is_anomalous}")
        
        sql_str = """
            SELECT 
                lpr.id,
                lpr.trace_id,
                lpr.pod_ip,
                lpr.cluster_name,
                lpr.host,
                lpr.timestamp as time,
                lpr.operation,
                lpr.total_latency,
                lpr.urma_total_latency,
                lpr.c2w_latency,
                lpr.worker_query_meta_latency,
                lpr.w2w_urma_latency,
                lpr.is_anomalous,
                lpr.anomaly_reason,
                lpr.c2w_latency as req_delay_ms,
                (lpr.total_latency - lpr.c2w_latency) as rsp_delay_ms,
                lpr.total_latency as sdk_ms,
                lpr.pod_ip as pod_id
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.existed_status = 1 AND lpr.pod_ip = :host
        """
        params = {"host": req.host}
        
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.start_time:
            sql_str += " AND lpr.timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND lpr.timestamp <= :end_time"
            params["end_time"] = req.end_time
        if req.operation:
            sql_str += " AND lpr.operation LIKE :operation"
            params["operation"] = f"%{req.operation}%"
        if req.is_anomalous is not None:
            logger.info(f"Adding is_anomalous filter: {req.is_anomalous}")
            sql_str += " AND lpr.is_anomalous = :is_anomalous"
            params["is_anomalous"] = 1 if req.is_anomalous else 0
        
        logger.info(f"Final SQL params: {params}")
        
        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0
        
        valid_sort_fields = ["timestamp", "total_latency", "c2w_latency"]
        sort_by = req.sort_by if req.sort_by in valid_sort_fields else "timestamp"
        sort_order = "DESC" if req.sort_order.lower() == "desc" else "ASC"
        sql_str += f" ORDER BY {sort_by} {sort_order}"
        
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset
        
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        logger.info(f"Returned {len(rows)} rows")
        return total, rows

    @staticmethod
    async def get_latency_metrics(
        req: GetLatencyMetricsRequest,
    ) -> tuple[int, list[dict]]:
        """获取延迟指标时间曲线数据（SQL 分桶 + JSON 存原始值）"""
        # === 构建 WHERE 条件 ===
        where_clauses = ["lpr.existed_status = 1"]
        params = {}

        if req.kb_id:
            where_clauses.append("lf.kb_id = :kb_id")
            params["kb_id"] = req.kb_id
        if req.host:
            where_clauses.append("lpr.pod_ip = :host")
            params["host"] = req.host
        if req.src_ip:
            where_clauses.append("lpr.src_ip LIKE :src_ip")
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            where_clauses.append("lpr.dst_ip LIKE :dst_ip")
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.start_time:
            where_clauses.append("lpr.timestamp >= :start_time")
            params["start_time"] = req.start_time
        if req.end_time:
            where_clauses.append("lpr.timestamp <= :end_time")
            params["end_time"] = req.end_time
        if req.operation:
            where_clauses.append("lpr.operation LIKE :operation")
            params["operation"] = f"%{req.operation}%"

        where_sql = " AND ".join(where_clauses)

        # === 1. COUNT 查询 ===
        count_sql = f"""
            SELECT COUNT(*) as cnt 
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE {where_sql}
        """
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        if total == 0:
            return 0, []

        # === 2. 判断是否需要分桶 ===
        max_points = req.max_points
        if total <= max_points or max_points == -1:
            sql_str = f"""
                SELECT 
                    lpr.timestamp as time,
                    lpr.total_latency,
                    lpr.urma_total_latency,
                    lpr.worker_query_meta_latency,
                    lpr.sdk_process,
                    lpr.sdk_rpc,
                    lpr.local_worker_cost,
                    lpr.local_worker_lock,
                    lpr.remote_worker_cost,
                    lpr.remote_worker_rpc,
                    lpr.master_process,
                    lpr.master_rpc_total
                FROM log_parse_result_table lpr
                LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
                WHERE {where_sql}
                ORDER BY lpr.timestamp ASC
            """
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            return total, rows

        # === 3. 查询时间范围，计算分桶步长（毫秒级精度） ===
        # strftime('%f') 返回 SS.SSS，取小数部分需：CAST(strftime('%f', ts) * 1000 AS INTEGER) % 1000
        range_sql = f"""
            SELECT 
                MIN(CAST(strftime('%s', lpr.timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', lpr.timestamp) * 1000 AS INTEGER) % 1000) as min_ms,
                MAX(CAST(strftime('%s', lpr.timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', lpr.timestamp) * 1000 AS INTEGER) % 1000) as max_ms
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE {where_sql}
        """
        range_rows = await AsyncSQLiteSingleton().execute_query(range_sql, params)
        if not range_rows or range_rows[0]["min_ms"] is None:
            return total, []

        min_ms = float(range_rows[0]["min_ms"])
        max_ms = float(range_rows[0]["max_ms"])
        time_span_ms = max_ms - min_ms

        if time_span_ms <= 0:
            sql_str = f"""
                SELECT 
                    MIN(lpr.timestamp) as time,
                    JSON_GROUP_ARRAY(lpr.total_latency) as total_latency_values,
                    JSON_GROUP_ARRAY(lpr.urma_total_latency) as urma_total_latency_values,
                    JSON_GROUP_ARRAY(lpr.worker_query_meta_latency) as worker_query_meta_latency_values,
                    JSON_GROUP_ARRAY(lpr.sdk_process) as sdk_process_values,
                    JSON_GROUP_ARRAY(lpr.sdk_rpc) as sdk_rpc_values,
                    JSON_GROUP_ARRAY(lpr.local_worker_cost) as local_worker_cost_values,
                    JSON_GROUP_ARRAY(lpr.local_worker_lock) as local_worker_lock_values,
                    JSON_GROUP_ARRAY(lpr.remote_worker_cost) as remote_worker_cost_values,
                    JSON_GROUP_ARRAY(lpr.remote_worker_rpc) as remote_worker_rpc_values,
                    JSON_GROUP_ARRAY(lpr.master_process) as master_process_values,
                    JSON_GROUP_ARRAY(lpr.master_rpc_total) as master_rpc_total_values
                FROM log_parse_result_table lpr
                LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
                WHERE {where_sql}
            """
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            return total, rows

        bucket_step_ms = time_span_ms / max_points  # 动态步长（毫秒）

        # === 4. 分桶聚合查询（毫秒级精度分桶） ===
        agg_sql = f"""
            SELECT 
                MIN(lpr.timestamp) as time,
                JSON_GROUP_ARRAY(lpr.total_latency) as total_latency_values,
                JSON_GROUP_ARRAY(lpr.urma_total_latency) as urma_total_latency_values,
                JSON_GROUP_ARRAY(lpr.worker_query_meta_latency) as worker_query_meta_latency_values,
                JSON_GROUP_ARRAY(lpr.sdk_process) as sdk_process_values,
                JSON_GROUP_ARRAY(lpr.sdk_rpc) as sdk_rpc_values,
                JSON_GROUP_ARRAY(lpr.local_worker_cost) as local_worker_cost_values,
                JSON_GROUP_ARRAY(lpr.local_worker_lock) as local_worker_lock_values,
                JSON_GROUP_ARRAY(lpr.remote_worker_cost) as remote_worker_cost_values,
                JSON_GROUP_ARRAY(lpr.remote_worker_rpc) as remote_worker_rpc_values,
                JSON_GROUP_ARRAY(lpr.master_process) as master_process_values,
                JSON_GROUP_ARRAY(lpr.master_rpc_total) as master_rpc_total_values
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE {where_sql}
            GROUP BY CAST(
                (CAST(strftime('%s', lpr.timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', lpr.timestamp) * 1000 AS INTEGER) % 1000)
                / :bucket_step_ms
            AS INTEGER)
            ORDER BY time ASC
        """
        params["bucket_step_ms"] = bucket_step_ms
        rows = await AsyncSQLiteSingleton().execute_query(agg_sql, params)
        return total, rows

    @staticmethod
    async def get_cluster_list(kb_id: str | None = None) -> list[str]:
        """获取所有非空的集群名称列表"""
        sql_str = """
            SELECT DISTINCT lpr.cluster_name 
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.cluster_name IS NOT NULL AND lpr.cluster_name != ''
        """
        params = {}
        if kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = kb_id
        sql_str += " ORDER BY lpr.cluster_name"
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [row["cluster_name"] for row in rows] if rows else []

    @staticmethod
    async def get_host_list(kb_id: str | None = None) -> list[str]:
        """获取所有非空的主机名称列表"""
        sql_str = """
            SELECT DISTINCT lpr.host 
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.host IS NOT NULL AND lpr.host != ''
        """
        params = {}
        if kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = kb_id
        sql_str += " ORDER BY lpr.host"
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [row["host"] for row in rows] if rows else []
