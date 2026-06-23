from latency.schemas.log import AnomalousEventModel
from latency.schemas.request import ListAnomalousEventRequest
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

    @staticmethod
    async def list_anomalous_events(
        req: ListAnomalousEventRequest,
    ) -> tuple[int, list[AnomalousEventModel]]:
        """分页查询异常事件"""
        sql_str = """
            SELECT ae.id, ae.log_id, ae.aggregated_event_id, ae.start_log_parse_offset,
                ae.end_log_parse_offset, ae.anomaly_reason, ae.existed_status, ae.created_at
            FROM anomalous_event_table ae
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
        if req.aggregated_event_id:
            sql_str += " AND ae.aggregated_event_id = :aggregated_event_id"
            params["aggregated_event_id"] = req.aggregated_event_id

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sort_field_mapping = {
            "created_at": "ae.created_at",
            "anomaly_reason": "ae.anomaly_reason",
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
                sql_str += " ORDER BY ae.created_at DESC"
        else:
            sql_str += " ORDER BY ae.created_at DESC"

        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        events = [AnomalousEventModel(**row) for row in rows]
        return total, events
