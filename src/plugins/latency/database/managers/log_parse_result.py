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
                timestamp, src_ip, dst_ip, pod_ip, total_latency, c2w_latency,
                worker_query_meta_latency, urma_total_latency, urma_link_latency,
                urma_inflight_count, c2w_urma_latency, w2w_urma_latency,
                operation, data_size, offset, is_anomalous, content,
                anomaly_reason, anomaly_score, remark, existed_status, created_at
            ) VALUES (
                :id, :log_id, :aggregated_event_id, :anomalous_event_id, :trace_id,
                :timestamp, :src_ip, :dst_ip, :pod_ip, :total_latency, :c2w_latency,
                :worker_query_meta_latency, :urma_total_latency, :urma_link_latency,
                :urma_inflight_count, :c2w_urma_latency, :w2w_urma_latency,
                :operation, :data_size, :offset, :is_anomalous, :content,
                :anomaly_reason, :anomaly_score, :remark, :existed_status, :created_at
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
                        timestamp, src_ip, dst_ip, pod_ip, total_latency, c2w_latency,
                        worker_query_meta_latency, urma_total_latency, urma_link_latency,
                        urma_inflight_count, c2w_urma_latency, w2w_urma_latency,
                        operation, data_size, offset, is_anomalous, content,
                        anomaly_reason, anomaly_score, remark, existed_status, created_at
                    ) VALUES (
                        :id, :log_id, :aggregated_event_id, :anomalous_event_id, :trace_id,
                        :timestamp, :src_ip, :dst_ip, :pod_ip, :total_latency, :c2w_latency,
                        :worker_query_meta_latency, :urma_total_latency, :urma_link_latency,
                        :urma_inflight_count, :c2w_urma_latency, :w2w_urma_latency,
                        :operation, :data_size, :offset, :is_anomalous, :content,
                        :anomaly_reason, :anomaly_score, :remark, :existed_status, :created_at
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
                timestamp, src_ip, dst_ip, pod_ip, total_latency, c2w_latency,
                worker_query_meta_latency, urma_total_latency, urma_link_latency,
                urma_inflight_count, c2w_urma_latency, w2w_urma_latency,
                operation, data_size, offset, is_anomalous, content,
                anomaly_reason, anomaly_score, remark, existed_status, created_at
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
                timestamp, src_ip, dst_ip, pod_ip, total_latency, c2w_latency,
                worker_query_meta_latency, urma_total_latency, urma_link_latency,
                urma_inflight_count, c2w_urma_latency, w2w_urma_latency,
                operation, data_size, offset, is_anomalous, content,
                anomaly_reason, anomaly_score, remark, existed_status, created_at
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
        sql_str = """
            SELECT 
                trace_id,
                pod_ip as pod_id,
                timestamp as time,
                total_latency as sdk_ms,
                c2w_latency as req_delay_ms,
                (total_latency - c2w_latency) as rsp_delay_ms
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
        return total, rows

    @staticmethod
    async def get_latency_metrics(
        req: GetLatencyMetricsRequest,
    ) -> tuple[int, list[dict]]:
        """获取延迟指标时间曲线数据"""
        sql_str = """
            SELECT 
                timestamp as time,
                total_latency,
                urma_total_latency,
                worker_query_meta_latency
            FROM log_parse_result_table
            WHERE existed_status = 1
        """
        params = {}
        
        if req.host:
            sql_str += " AND pod_ip = :host"
            params["host"] = req.host
        if req.src_ip:
            sql_str += " AND src_ip LIKE :src_ip"
            params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip:
            sql_str += " AND dst_ip LIKE :dst_ip"
            params["dst_ip"] = f"%{req.dst_ip}%"
        if req.start_time:
            sql_str += " AND timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND timestamp <= :end_time"
            params["end_time"] = req.end_time
        if req.operation:
            sql_str += " AND operation LIKE :operation"
            params["operation"] = f"%{req.operation}%"
        
        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0
        
        valid_sort_fields = ["timestamp", "total_latency", "urma_total_latency", "worker_query_meta_latency"]
        sort_by = req.sort_by if req.sort_by in valid_sort_fields else "timestamp"
        sort_order = "DESC" if req.sort_order.lower() == "desc" else "ASC"
        sql_str += f" ORDER BY {sort_by} {sort_order}"
        
        sql_str += " LIMIT :limit"
        params["limit"] = req.max_points
        
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return total, rows
