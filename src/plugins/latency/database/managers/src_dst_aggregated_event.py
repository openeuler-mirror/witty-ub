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
