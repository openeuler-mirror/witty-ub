from latency.schemas.log import AnomalousEventModel
from latency.database.engine import AsyncSQLiteSingleton


class AnomalousEventManager:
    """异常事件管理器"""

    @staticmethod
    async def add_anomalous_event(event: AnomalousEventModel) -> bool:
        """添加异常事件"""
        sql_str = """
            INSERT INTO anomalous_event_table (
                id, log_id, aggregated_event_id, start_log_parse_offset,
                end_log_parse_offset, anomaly_reason, existed_status, created_at
            ) VALUES (
                :id, :log_id, :aggregated_event_id, :start_log_parse_offset,
                :end_log_parse_offset, :anomaly_reason, :existed_status, :created_at
            )
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, event.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def add_anomalous_events(events: list[AnomalousEventModel]) -> list[str]:
        """批量添加异常事件"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO anomalous_event_table (
                        id, log_id, aggregated_event_id, start_log_parse_offset,
                        end_log_parse_offset, anomaly_reason, existed_status, created_at
                    ) VALUES (
                        :id, :log_id, :aggregated_event_id, :start_log_parse_offset,
                        :end_log_parse_offset, :anomaly_reason, :existed_status, :created_at
                    )
                """
                params = [
                    e.model_dump(exclude_none=False, by_alias=True) for e in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([e.id for e in batch])
            except Exception as e:
                print(f"批量添加异常事件失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def delete_anomalous_events_by_log_id(log_id: str) -> bool:
        """根据日志ID删除异常事件"""
        sql_str = """
            UPDATE anomalous_event_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def update_anomalous_events_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        """根据日志ID更新异常事件的存在状态"""
        sql_str = """
            UPDATE anomalous_event_table
            SET existed_status = :existed_status
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id, "existed_status": existed_status}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def list_anomalous_events_by_log_id(log_id: str) -> list[AnomalousEventModel]:
        """根据日志ID查询异常事件列表"""
        sql_str = """
            SELECT id, log_id, aggregated_event_id, start_log_parse_offset,
                end_log_parse_offset, anomaly_reason, existed_status, created_at
            FROM anomalous_event_table
            WHERE log_id = :log_id AND existed_status = 1
            ORDER BY created_at DESC
        """
        params = {"log_id": log_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [AnomalousEventModel(**row) for row in rows]

    @staticmethod
    async def get_anomalous_event_by_id(event_id: str) -> AnomalousEventModel | None:
        """根据ID获取异常事件"""
        sql_str = """
            SELECT id, log_id, aggregated_event_id, start_log_parse_offset,
                end_log_parse_offset, anomaly_reason, existed_status, created_at
            FROM anomalous_event_table
            WHERE id = :event_id
        """
        params = {"event_id": event_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return AnomalousEventModel(**rows[0])
        return None
