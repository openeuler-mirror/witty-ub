from dataclasses import dataclass, field
from datetime import datetime

from latency.database.engine import AsyncSQLiteSingleton


@dataclass(slots=True)
class TimeWindowAggregatedEventDataclass:
    id: str = ""
    kb_id: str = ""
    log_id: str = ""
    time_bucket: str = ""
    src_ip: str = ""
    dst_ip: str = ""
    log_parse_result_cnt: int = 0
    anomaly_cnt: int = 0
    ave_total_latency: float | None = None
    min_total_latency: float | None = None
    max_total_latency: float | None = None
    p99_total_latency: float | None = None
    p95_total_latency: float | None = None
    p9999_total_latency: float | None = None
    ave_query_meta_latency: float | None = None
    min_query_meta_latency: float | None = None
    max_query_meta_latency: float | None = None
    p99_query_meta_latency: float | None = None
    p95_query_meta_latency: float | None = None
    p9999_query_meta_latency: float | None = None
    ave_urma_total_latency: float | None = None
    min_urma_total_latency: float | None = None
    max_urma_total_latency: float | None = None
    p99_urma_total_latency: float | None = None
    p95_urma_total_latency: float | None = None
    p9999_urma_total_latency: float | None = None
    ave_urma_link_latency: float | None = None
    min_urma_link_latency: float | None = None
    max_urma_link_latency: float | None = None
    p99_urma_link_latency: float | None = None
    p95_urma_link_latency: float | None = None
    p9999_urma_link_latency: float | None = None
    ave_c2w_urma_latency: float | None = None
    min_c2w_urma_latency: float | None = None
    max_c2w_urma_latency: float | None = None
    p99_c2w_urma_latency: float | None = None
    p95_c2w_urma_latency: float | None = None
    p9999_c2w_urma_latency: float | None = None
    ave_w2w_urma_latency: float | None = None
    min_w2w_urma_latency: float | None = None
    max_w2w_urma_latency: float | None = None
    p99_w2w_urma_latency: float | None = None
    p95_w2w_urma_latency: float | None = None
    p9999_w2w_urma_latency: float | None = None
    ave_sdk_process: float | None = None
    min_sdk_process: float | None = None
    max_sdk_process: float | None = None
    p99_sdk_process: float | None = None
    p95_sdk_process: float | None = None
    p9999_sdk_process: float | None = None
    ave_sdk_rpc: float | None = None
    min_sdk_rpc: float | None = None
    max_sdk_rpc: float | None = None
    p99_sdk_rpc: float | None = None
    p95_sdk_rpc: float | None = None
    p9999_sdk_rpc: float | None = None
    ave_local_worker_cost: float | None = None
    min_local_worker_cost: float | None = None
    max_local_worker_cost: float | None = None
    p99_local_worker_cost: float | None = None
    p95_local_worker_cost: float | None = None
    p9999_local_worker_cost: float | None = None
    ave_local_worker_lock: float | None = None
    min_local_worker_lock: float | None = None
    max_local_worker_lock: float | None = None
    p99_local_worker_lock: float | None = None
    p95_local_worker_lock: float | None = None
    p9999_local_worker_lock: float | None = None
    ave_remote_worker_cost: float | None = None
    min_remote_worker_cost: float | None = None
    max_remote_worker_cost: float | None = None
    p99_remote_worker_cost: float | None = None
    p95_remote_worker_cost: float | None = None
    p9999_remote_worker_cost: float | None = None
    ave_remote_worker_rpc: float | None = None
    min_remote_worker_rpc: float | None = None
    max_remote_worker_rpc: float | None = None
    p99_remote_worker_rpc: float | None = None
    p95_remote_worker_rpc: float | None = None
    p9999_remote_worker_rpc: float | None = None
    ave_master_process: float | None = None
    min_master_process: float | None = None
    max_master_process: float | None = None
    p99_master_process: float | None = None
    p95_master_process: float | None = None
    p9999_master_process: float | None = None
    ave_master_rpc_total: float | None = None
    min_master_rpc_total: float | None = None
    max_master_rpc_total: float | None = None
    p99_master_rpc_total: float | None = None
    p95_master_rpc_total: float | None = None
    p9999_master_rpc_total: float | None = None
    existed_status: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]
    )


def _time_window_event_to_db_tuple(event: TimeWindowAggregatedEventDataclass) -> tuple:
    return (
        event.id,
        event.kb_id,
        event.log_id,
        event.time_bucket,
        event.src_ip,
        event.dst_ip,
        event.log_parse_result_cnt,
        event.anomaly_cnt,
        event.ave_total_latency,
        event.min_total_latency,
        event.max_total_latency,
        event.p99_total_latency,
        event.p95_total_latency,
        event.p9999_total_latency,
        event.ave_query_meta_latency,
        event.min_query_meta_latency,
        event.max_query_meta_latency,
        event.p99_query_meta_latency,
        event.p95_query_meta_latency,
        event.p9999_query_meta_latency,
        event.ave_urma_total_latency,
        event.min_urma_total_latency,
        event.max_urma_total_latency,
        event.p99_urma_total_latency,
        event.p95_urma_total_latency,
        event.p9999_urma_total_latency,
        event.ave_urma_link_latency,
        event.min_urma_link_latency,
        event.max_urma_link_latency,
        event.p99_urma_link_latency,
        event.p95_urma_link_latency,
        event.p9999_urma_link_latency,
        event.ave_c2w_urma_latency,
        event.min_c2w_urma_latency,
        event.max_c2w_urma_latency,
        event.p99_c2w_urma_latency,
        event.p95_c2w_urma_latency,
        event.p9999_c2w_urma_latency,
        event.ave_w2w_urma_latency,
        event.min_w2w_urma_latency,
        event.max_w2w_urma_latency,
        event.p99_w2w_urma_latency,
        event.p95_w2w_urma_latency,
        event.p9999_w2w_urma_latency,
        event.ave_sdk_process,
        event.min_sdk_process,
        event.max_sdk_process,
        event.p99_sdk_process,
        event.p95_sdk_process,
        event.p9999_sdk_process,
        event.ave_sdk_rpc,
        event.min_sdk_rpc,
        event.max_sdk_rpc,
        event.p99_sdk_rpc,
        event.p95_sdk_rpc,
        event.p9999_sdk_rpc,
        event.ave_local_worker_cost,
        event.min_local_worker_cost,
        event.max_local_worker_cost,
        event.p99_local_worker_cost,
        event.p95_local_worker_cost,
        event.p9999_local_worker_cost,
        event.ave_local_worker_lock,
        event.min_local_worker_lock,
        event.max_local_worker_lock,
        event.p99_local_worker_lock,
        event.p95_local_worker_lock,
        event.p9999_local_worker_lock,
        event.ave_remote_worker_cost,
        event.min_remote_worker_cost,
        event.max_remote_worker_cost,
        event.p99_remote_worker_cost,
        event.p95_remote_worker_cost,
        event.p9999_remote_worker_cost,
        event.ave_remote_worker_rpc,
        event.min_remote_worker_rpc,
        event.max_remote_worker_rpc,
        event.p99_remote_worker_rpc,
        event.p95_remote_worker_rpc,
        event.p9999_remote_worker_rpc,
        event.ave_master_process,
        event.min_master_process,
        event.max_master_process,
        event.p99_master_process,
        event.p95_master_process,
        event.p9999_master_process,
        event.ave_master_rpc_total,
        event.min_master_rpc_total,
        event.max_master_rpc_total,
        event.p99_master_rpc_total,
        event.p95_master_rpc_total,
        event.p9999_master_rpc_total,
        event.existed_status,
        event.created_at,
    )


class TimeWindowAggregatedEventManager:
    """时间窗口聚合事件管理器"""

    @staticmethod
    async def add_events(
        events: list[TimeWindowAggregatedEventDataclass],
        batch_size: int = 50000,
    ) -> list[str]:
        """批量添加时间窗口聚合事件"""
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
                        INSERT INTO time_window_aggregated_table (
                            id, kb_id, log_id, time_bucket, src_ip, dst_ip,
                            log_parse_result_cnt, anomaly_cnt,
                            ave_total_latency, min_total_latency, max_total_latency,
                            p99_total_latency, p95_total_latency, p9999_total_latency,
                            ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                            p99_query_meta_latency, p95_query_meta_latency, p9999_query_meta_latency,
                            ave_urma_total_latency, min_urma_total_latency, max_urma_total_latency,
                            p99_urma_total_latency, p95_urma_total_latency, p9999_urma_total_latency,
                            ave_urma_link_latency, min_urma_link_latency, max_urma_link_latency,
                            p99_urma_link_latency, p95_urma_link_latency, p9999_urma_link_latency,
                            ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                            p99_c2w_urma_latency, p95_c2w_urma_latency, p9999_c2w_urma_latency,
                            ave_w2w_urma_latency, min_w2w_urma_latency, max_w2w_urma_latency,
                            p99_w2w_urma_latency, p95_w2w_urma_latency, p9999_w2w_urma_latency,
                            ave_sdk_process, min_sdk_process, max_sdk_process,
                            p99_sdk_process, p95_sdk_process, p9999_sdk_process,
                            ave_sdk_rpc, min_sdk_rpc, max_sdk_rpc,
                            p99_sdk_rpc, p95_sdk_rpc, p9999_sdk_rpc,
                            ave_local_worker_cost, min_local_worker_cost, max_local_worker_cost,
                            p99_local_worker_cost, p95_local_worker_cost, p9999_local_worker_cost,
                            ave_local_worker_lock, min_local_worker_lock, max_local_worker_lock,
                            p99_local_worker_lock, p95_local_worker_lock, p9999_local_worker_lock,
                            ave_remote_worker_cost, min_remote_worker_cost, max_remote_worker_cost,
                            p99_remote_worker_cost, p95_remote_worker_cost, p9999_remote_worker_cost,
                            ave_remote_worker_rpc, min_remote_worker_rpc, max_remote_worker_rpc,
                            p99_remote_worker_rpc, p95_remote_worker_rpc, p9999_remote_worker_rpc,
                            ave_master_process, min_master_process, max_master_process,
                            p99_master_process, p95_master_process, p9999_master_process,
                            ave_master_rpc_total, min_master_rpc_total, max_master_rpc_total,
                            p99_master_rpc_total, p95_master_rpc_total, p9999_master_rpc_total,
                            existed_status, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    for i in range(0, total_count, batch_size):
                        end = min(i + batch_size, total_count)
                        batch = (
                            _time_window_event_to_db_tuple(events[index])
                            for index in range(i, end)
                        )
                        conn.executemany(sql_str, batch)

                    conn.commit()
                    logger.info(f"[Store] 时间窗口聚合事件插入成功，共 {total_count:,} 条记录")
                    return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"[Store] 时间窗口聚合事件插入失败，事务回滚: {str(e)}")
                    return False

            success = await asyncio.to_thread(sync_batch_insert)
            return ids_added if success else []

    @staticmethod
    async def get_time_window_events(
        kb_id: str = "",
        start_time: str = "",
        end_time: str = "",
        src_ip: str | None = None,
        dst_ip: str | None = None,
    ) -> list[dict]:
        """获取时间窗口聚合事件"""
        db = AsyncSQLiteSingleton()

        conditions = ["existed_status = 1"]
        params = {}

        if kb_id:
            conditions.append("kb_id = :kb_id")
            params["kb_id"] = kb_id

        if start_time:
            conditions.append("time_bucket >= :start_time")
            params["start_time"] = start_time

        if end_time:
            conditions.append("time_bucket <= :end_time")
            params["end_time"] = end_time

        if src_ip is not None:
            if src_ip == "":
                conditions.append("(src_ip IS NULL OR src_ip = '')")
            else:
                conditions.append("(src_ip = :src_ip OR src_ip LIKE :src_ip_like)")
                params["src_ip"] = src_ip
                params["src_ip_like"] = f"{src_ip}%"

        if dst_ip is not None:
            if dst_ip == "":
                conditions.append("(dst_ip IS NULL OR dst_ip = '')")
            else:
                conditions.append("(dst_ip = :dst_ip OR dst_ip LIKE :dst_ip_like)")
                params["dst_ip"] = dst_ip
                params["dst_ip_like"] = f"{dst_ip}%"

        sql_str = f"""
            SELECT id, kb_id, log_id, time_bucket, src_ip, dst_ip,
                   log_parse_result_cnt, anomaly_cnt,
                   ave_total_latency, min_total_latency, max_total_latency,
                   p99_total_latency, p95_total_latency,
                   ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                   p99_query_meta_latency, p95_query_meta_latency,
                   ave_urma_total_latency, min_urma_total_latency, max_urma_total_latency,
                   p99_urma_total_latency, p95_urma_total_latency,
                   ave_urma_link_latency, min_urma_link_latency, max_urma_link_latency,
                   p99_urma_link_latency, p95_urma_link_latency,
                   ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                   p99_c2w_urma_latency, p95_c2w_urma_latency,
                   ave_w2w_urma_latency, min_w2w_urma_latency, max_w2w_urma_latency,
                   p99_w2w_urma_latency, p95_w2w_urma_latency
            FROM time_window_aggregated_table
            WHERE {' AND '.join(conditions)}
            ORDER BY time_bucket ASC, src_ip ASC, dst_ip ASC
            LIMIT 50000
        """

        rows = await db.execute_query(sql_str, params)
        return rows if rows else []

    @staticmethod
    async def delete_by_log_id(log_id: str) -> bool:
        """根据日志ID删除时间窗口聚合事件"""
        sql_str = """
            UPDATE time_window_aggregated_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def delete_by_kb_id(kb_id: str) -> bool:
        """根据知识库ID删除时间窗口聚合事件"""
        sql_str = """
            UPDATE time_window_aggregated_table
            SET existed_status = 0
            WHERE kb_id = :kb_id
        """
        params = {"kb_id": kb_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success
