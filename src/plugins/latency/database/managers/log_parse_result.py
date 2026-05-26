from latency.schemas.log import LogParseResultModel
from latency.database.engine import AsyncSQLiteSingleton


class LogParseResultManager:

    @staticmethod
    async def add_log_parse_result(result: LogParseResultModel) -> str:
        sql_str = """
            INSERT INTO log_parse_result_table (
                id, log_id, aggregated_event_id, anomalous_event_id,
                trace_id, timestamp, src_ip, dst_ip, pod_ip,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                operation, data_size, offset,
                is_anomalous, content, anomaly_reason, anomaly_score, remark,
                existed_status, created_at
            )
            VALUES (
                :id, :log_id, :aggregated_event_id, :anomalous_event_id,
                :trace_id, :timestamp, :src_ip, :dst_ip, :pod_ip,
                :total_latency, :c2w_latency, :worker_query_meta_latency,
                :urma_total_latency, :urma_link_latency, :urma_inflight_count,
                :c2w_urma_latency, :w2w_urma_latency, :urma_write_source, :urma_write_dst,
                :operation, :data_size, :offset,
                :is_anomalous, :content, :anomaly_reason, :anomaly_score, :remark,
                :existed_status, :created_at
            )
        """
        data = result.model_dump(exclude_none=False)
        success = await AsyncSQLiteSingleton().execute_modify(sql_str, data)
        return result.id if success else ""

    @staticmethod
    async def batch_add_log_parse_results(results: list[LogParseResultModel]) -> bool:
        if not results:
            return False
        sql_str = """
            INSERT INTO log_parse_result_table (
                id, log_id, aggregated_event_id, anomalous_event_id,
                trace_id, timestamp, src_ip, dst_ip, pod_ip,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                operation, data_size, offset,
                is_anomalous, content, anomaly_reason, anomaly_score, remark,
                existed_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = []
        for r in results:
            data = r.model_dump(exclude_none=False)
            rows.append((
                data.get("id"), data.get("log_id"), data.get("aggregated_event_id"),
                data.get("anomalous_event_id"), data.get("trace_id"), data.get("timestamp"),
                data.get("src_ip"), data.get("dst_ip"), data.get("pod_ip"),
                data.get("total_latency"), data.get("c2w_latency"),
                data.get("worker_query_meta_latency"), data.get("urma_total_latency"),
                data.get("urma_link_latency"), data.get("urma_inflight_count"),
                data.get("c2w_urma_latency"), data.get("w2w_urma_latency"),
                data.get("urma_write_source"), data.get("urma_write_dst"),
                data.get("operation"), data.get("data_size"), data.get("offset"),
                data.get("is_anomalous"), data.get("content"),
                data.get("anomaly_reason"), data.get("anomaly_score"), data.get("remark"),
                data.get("existed_status"), data.get("created_at"),
            ))
        return await AsyncSQLiteSingleton().execute_modify(sql_str, rows)

    @staticmethod
    async def delete_log_parse_result_by_id(result_id: str) -> bool:
        sql_str = """
            DELETE FROM log_parse_result_table
            WHERE id = :result_id
        """
        params = {"result_id": result_id}
        return await AsyncSQLiteSingleton().execute_modify(sql_str, params)

    @staticmethod
    async def delete_log_parse_results_by_ids(result_ids: list[str]) -> bool:
        if not result_ids:
            return False
        placeholders = ", ".join(["?"] * len(result_ids))
        sql_str = f"""
            DELETE FROM log_parse_result_table
            WHERE id IN ({placeholders})
        """
        return await AsyncSQLiteSingleton().execute_modify(sql_str, tuple(result_ids))

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> LogParseResultModel | None:
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id,
                   trace_id, timestamp, src_ip, dst_ip, pod_ip,
                   total_latency, c2w_latency, worker_query_meta_latency,
                   urma_total_latency, urma_link_latency, urma_inflight_count,
                   c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                   operation, data_size, offset,
                   is_anomalous, content, anomaly_reason, anomaly_score, remark,
                   existed_status, created_at
            FROM log_parse_result_table
            WHERE id = :result_id
        """
        params = {"result_id": result_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return LogParseResultModel(**rows[0])
        return None

    @staticmethod
    async def list_log_parse_results_by_aggregated_event_id(
        aggregated_event_id: str,
    ) -> list[LogParseResultModel]:
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id,
                   trace_id, timestamp, src_ip, dst_ip, pod_ip,
                   total_latency, c2w_latency, worker_query_meta_latency,
                   urma_total_latency, urma_link_latency, urma_inflight_count,
                   c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                   operation, data_size, offset,
                   is_anomalous, content, anomaly_reason, anomaly_score, remark,
                   existed_status, created_at
            FROM log_parse_result_table
            WHERE aggregated_event_id = :aggregated_event_id
            ORDER BY created_at DESC
        """
        params = {"aggregated_event_id": aggregated_event_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [LogParseResultModel(**row) for row in rows]

    @staticmethod
    async def list_log_parse_results_by_anomalous_event_id(
        anomalous_event_id: str,
    ) -> list[LogParseResultModel]:
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id,
                   trace_id, timestamp, src_ip, dst_ip, pod_ip,
                   total_latency, c2w_latency, worker_query_meta_latency,
                   urma_total_latency, urma_link_latency, urma_inflight_count,
                   c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                   operation, data_size, offset,
                   is_anomalous, content, anomaly_reason, anomaly_score, remark,
                   existed_status, created_at
            FROM log_parse_result_table
            WHERE anomalous_event_id = :anomalous_event_id
            ORDER BY created_at DESC
        """
        params = {"anomalous_event_id": anomalous_event_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [LogParseResultModel(**row) for row in rows]

    @staticmethod
    async def list_anomalous_log_parse_results() -> list[LogParseResultModel]:
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id,
                   trace_id, timestamp, src_ip, dst_ip, pod_ip,
                   total_latency, c2w_latency, worker_query_meta_latency,
                   urma_total_latency, urma_link_latency, urma_inflight_count,
                   c2w_urma_latency, w2w_urma_latency, urma_write_source, urma_write_dst,
                   operation, data_size, offset,
                   is_anomalous, content, anomaly_reason, anomaly_score, remark,
                   existed_status, created_at
            FROM log_parse_result_table
            WHERE is_anomalous = 1
            ORDER BY created_at DESC
        """
        rows = await AsyncSQLiteSingleton().execute_query(sql_str)
        return [LogParseResultModel(**row) for row in rows]
