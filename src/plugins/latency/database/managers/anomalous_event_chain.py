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
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, chain.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def add_event_chains(chains: list[AnomalousEventChainModel]) -> list[str]:
        """批量添加异常事件链"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(chains), batch_size):
            batch = chains[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO anomalous_event_chain_table (
                        id, log_id, anomalous_event_id, name, description,
                        anomaly_code, offset, existed_status, created_at
                    ) VALUES (
                        :id, :log_id, :anomalous_event_id, :name, :description,
                        :anomaly_code, :offset, :existed_status, :created_at
                    )
                """
                params = [
                    c.model_dump(exclude_none=False, by_alias=True) for c in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([c.id for c in batch])
            except Exception as e:
                print(f"批量添加异常事件链失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def delete_event_chains_by_log_id(log_id: str) -> bool:
        """根据日志ID删除异常事件链"""
        sql_str = """
            UPDATE anomalous_event_chain_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def list_event_chains(
        req: ListAnomalousEventChainRequest,
    ) -> tuple[int, list[AnomalousEventChainModel]]:
        """分页查询异常事件链"""
        sql_str = """
            SELECT id, log_id, anomalous_event_id, name, description,
                anomaly_code, offset, existed_status, created_at
            FROM anomalous_event_chain_table
            WHERE existed_status = 1
        """
        params = {}

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sql_str += " ORDER BY created_at DESC"
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
