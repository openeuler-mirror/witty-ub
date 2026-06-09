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
        batch_size: int = 1024,
    ) -> list[str]:
        """批量添加日志解析结果"""
        ids_added = []
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            try:
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
                params = [
                    r.model_dump(exclude_none=False, by_alias=True) for r in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([r.id for r in batch])
            except Exception as e:
                print(f"批量添加日志解析结果失败，错误信息: {str(e)}")
        return ids_added

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
            WHERE existed_status = 1
        """
        params = {}
        if req.log_id:
            sql_str += " AND log_id = :log_id"
            params["log_id"] = req.log_id
        if req.src_ip:
            sql_str += " AND src_ip LIKE :src_ip"
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            sql_str += " AND dst_ip LIKE :dst_ip"
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.host:
            sql_str += " AND host LIKE :host"
            params["host"] = f"%{req.host}%"
        if req.cluster_name:
            sql_str += " AND cluster_name LIKE :cluster_name"
            params["cluster_name"] = f"%{req.cluster_name}%"
        if req.is_anomalous is not None:
            sql_str += " AND is_anomalous = :is_anomalous"
            params["is_anomalous"] = req.is_anomalous
        if req.created_at_start:
            sql_str += " AND created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sort_order = "DESC" if req.created_sorted_desc else "ASC"
        sql_str += f" ORDER BY created_at {sort_order}"
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
                id,
                trace_id,
                pod_ip,
                cluster_name,
                host,
                timestamp as time,
                operation,
                total_latency,
                urma_total_latency,
                c2w_latency,
                worker_query_meta_latency,
                w2w_urma_latency,
                is_anomalous,
                anomaly_reason,
                c2w_latency as req_delay_ms,
                (total_latency - c2w_latency) as rsp_delay_ms,
                total_latency as sdk_ms,
                pod_ip as pod_id
            FROM log_parse_result_table
            WHERE existed_status = 1 AND pod_ip = :host
        """
        params = {"host": req.host}
        
        if req.start_time:
            sql_str += " AND timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND timestamp <= :end_time"
            params["end_time"] = req.end_time
        if req.operation:
            sql_str += " AND operation LIKE :operation"
            params["operation"] = f"%{req.operation}%"
        if req.is_anomalous is not None:
            logger.info(f"Adding is_anomalous filter: {req.is_anomalous}")
            sql_str += " AND is_anomalous = :is_anomalous"
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
        where_clauses = ["existed_status = 1"]
        params = {}

        if req.host:
            where_clauses.append("pod_ip = :host")
            params["host"] = req.host
        if req.src_ip:
            where_clauses.append("src_ip LIKE :src_ip")
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            where_clauses.append("dst_ip LIKE :dst_ip")
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.start_time:
            where_clauses.append("timestamp >= :start_time")
            params["start_time"] = req.start_time
        if req.end_time:
            where_clauses.append("timestamp <= :end_time")
            params["end_time"] = req.end_time
        if req.operation:
            where_clauses.append("operation LIKE :operation")
            params["operation"] = f"%{req.operation}%"

        where_sql = " AND ".join(where_clauses)

        # === 1. COUNT 查询 ===
        count_sql = f"SELECT COUNT(*) as cnt FROM log_parse_result_table WHERE {where_sql}"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        if total == 0:
            return 0, []

        # === 2. 判断是否需要分桶 ===
        max_points = req.max_points
        if total <= max_points or max_points == -1:
            # 数据量小或不需要采样，直接返回原始数据
            sql_str = f"""
                SELECT 
                    timestamp as time,
                    total_latency,
                    urma_total_latency,
                    worker_query_meta_latency
                FROM log_parse_result_table
                WHERE {where_sql}
                ORDER BY timestamp ASC
            """
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            return total, rows

        # === 3. 查询时间范围，计算分桶步长（毫秒级精度） ===
        # strftime('%f') 返回 SS.SSS，取小数部分需：CAST(strftime('%f', ts) * 1000 AS INTEGER) % 1000
        range_sql = f"""
            SELECT 
                MIN(CAST(strftime('%s', timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', timestamp) * 1000 AS INTEGER) % 1000) as min_ms,
                MAX(CAST(strftime('%s', timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', timestamp) * 1000 AS INTEGER) % 1000) as max_ms
            FROM log_parse_result_table
            WHERE {where_sql}
        """
        range_rows = await AsyncSQLiteSingleton().execute_query(range_sql, params)
        if not range_rows or range_rows[0]["min_ms"] is None:
            return total, []

        min_ms = float(range_rows[0]["min_ms"])
        max_ms = float(range_rows[0]["max_ms"])
        time_span_ms = max_ms - min_ms

        if time_span_ms <= 0:
            # 时间跨度为 0，返回单条聚合
            sql_str = f"""
                SELECT 
                    MIN(timestamp) as time,
                    JSON_GROUP_ARRAY(total_latency) as total_latency_values,
                    JSON_GROUP_ARRAY(urma_total_latency) as urma_total_latency_values,
                    JSON_GROUP_ARRAY(worker_query_meta_latency) as worker_query_meta_latency_values
                FROM log_parse_result_table
                WHERE {where_sql}
            """
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            return total, rows

        bucket_step_ms = time_span_ms / max_points  # 动态步长（毫秒）

        # === 4. 分桶聚合查询（毫秒级精度分桶） ===
        agg_sql = f"""
            SELECT 
                MIN(timestamp) as time,
                JSON_GROUP_ARRAY(total_latency) as total_latency_values,
                JSON_GROUP_ARRAY(urma_total_latency) as urma_total_latency_values,
                JSON_GROUP_ARRAY(worker_query_meta_latency) as worker_query_meta_latency_values
            FROM log_parse_result_table
            WHERE {where_sql}
            GROUP BY CAST(
                (CAST(strftime('%s', timestamp) AS INTEGER) * 1000 + CAST(strftime('%f', timestamp) * 1000 AS INTEGER) % 1000)
                / :bucket_step_ms
            AS INTEGER)
            ORDER BY time ASC
        """
        params["bucket_step_ms"] = bucket_step_ms
        rows = await AsyncSQLiteSingleton().execute_query(agg_sql, params)
        return total, rows

    @staticmethod
    async def get_cluster_list() -> list[str]:
        """获取所有非空的集群名称列表"""
        sql_str = """
            SELECT DISTINCT cluster_name 
            FROM log_parse_result_table 
            WHERE cluster_name IS NOT NULL AND cluster_name != ''
            ORDER BY cluster_name
        """
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, {})
        return [row["cluster_name"] for row in rows] if rows else []

    @staticmethod
    async def get_host_list() -> list[str]:
        """获取所有非空的主机名称列表"""
        sql_str = """
            SELECT DISTINCT host 
            FROM log_parse_result_table 
            WHERE host IS NOT NULL AND host != ''
            ORDER BY host
        """
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, {})
        return [row["host"] for row in rows] if rows else []
