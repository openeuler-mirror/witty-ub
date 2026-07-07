from latency.schemas.log import AnomalousEventChainModel
from latency.schemas.request import ListAnomalousEventChainRequest
from latency.database.engine import AsyncSQLiteSingleton


class AnomalousEventChainManager:
    """异常事件链管理器"""

    @staticmethod
    async def add_event_chain(chain: AnomalousEventChainModel) -> bool:
        """添加异常事件链"""
        sql_str = """
            INSERT INTO anomalous_event_chain_table (
                id, log_id, anomalous_event_id, name, description,
                anomaly_code, offset, existed_status, created_at
            ) VALUES (
                :id, :log_id, :anomalous_event_id, :name, :description,
                :anomaly_code, :offset, :existed_status, :created_at
            )
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            sql_str, chain.model_dump(exclude_none=False, by_alias=True)
        )
        return success

    @staticmethod
    async def add_event_chains(
        chains: list[AnomalousEventChainModel],
        batch_size: int = 50000,
    ) -> list[str]:
        """批量添加异常事件链：全局单事务 + SQLite写入优化 + 线程安全修复"""
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not chains:
            return []
            
        ids_added = [c.id for c in chains]
        params = [c.model_dump(exclude_none=False, by_alias=True) for c in chains]
        total_count = len(params)
        db = AsyncSQLiteSingleton()
        
        async with db._async_lock:
            def sync_batch_insert():
                db.ensure_initialized()
                conn = db._conn
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                    conn.execute("PRAGMA cache_size = -7500;")
                    conn.execute("PRAGMA temp_store = MEMORY;")
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    
                    conn.execute("BEGIN TRANSACTION;")
                    
                    sql_str = """
                        INSERT INTO anomalous_event_chain_table (
                            id, log_id, anomalous_event_id, name, description,
                            anomaly_code, offset, existed_status, created_at
                        ) VALUES (
                            :id, :log_id, :anomalous_event_id, :name, :description,
                            :anomaly_code, :offset, :existed_status, :created_at
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
    async def delete_event_chains_by_log_id(log_id: str) -> bool:
        """根据日志ID删除异常事件链"""
        sql_str = """
            UPDATE anomalous_event_chain_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def update_event_chains_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        """根据日志ID更新异常事件链的存在状态"""
        sql_str = """
            UPDATE anomalous_event_chain_table
            SET existed_status = :existed_status
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id, "existed_status": existed_status}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def list_event_chains(
        req: ListAnomalousEventChainRequest,
    ) -> tuple[int, list[AnomalousEventChainModel]]:
        """分页查询异常事件链"""
        sql_str = """
            SELECT aec.id, aec.log_id, aec.anomalous_event_id, aec.name, aec.description,
                aec.anomaly_code, aec.offset, aec.existed_status, aec.created_at
            FROM anomalous_event_chain_table aec
            LEFT JOIN log_file_table lf ON aec.log_id = lf.id
            WHERE aec.existed_status = 1
        """
        params = {}
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.log_id:
            sql_str += " AND aec.log_id = :log_id"
            params["log_id"] = req.log_id

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sql_str += " ORDER BY aec.created_at DESC"
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        chains = [AnomalousEventChainModel(**row) for row in rows]
        return total, chains

    @staticmethod
    async def list_event_chains_by_log_id(
        log_id: str,
    ) -> list[AnomalousEventChainModel]:
        """根据日志ID查询异常事件链"""
        sql_str = """
            SELECT id, log_id, anomalous_event_id, name, description,
                anomaly_code, offset, existed_status, created_at
            FROM anomalous_event_chain_table
            WHERE log_id = :log_id AND existed_status = 1
            ORDER BY offset ASC, created_at DESC
        """
        params = {"log_id": log_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [AnomalousEventChainModel(**row) for row in rows]

    @staticmethod
    async def get_event_chain_by_id(chain_id: str) -> AnomalousEventChainModel | None:
        """根据ID获取异常事件链"""
        sql_str = """
            SELECT id, log_id, anomalous_event_id, name, description,
                anomaly_code, offset, existed_status, created_at
            FROM anomalous_event_chain_table
            WHERE id = :chain_id
        """
        params = {"chain_id": chain_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return AnomalousEventChainModel(**rows[0])
        return None
