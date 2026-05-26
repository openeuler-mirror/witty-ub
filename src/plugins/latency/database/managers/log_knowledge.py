from datetime import datetime
from latency.schemas.request import ListLogKnowledgeRequest
from latency.schemas.log import LogKnowledgeModel
from latency.database.engine import AsyncSQLiteSingleton


class LogKnowledgeManager:
    """日志知识库管理器"""

    @staticmethod
    async def add_log_kb(log_kb_model: LogKnowledgeModel) -> str:
        """添加日志知识库，返回知识库ID"""
        sql_str = """
            INSERT INTO log_knowledge_table (id, image_bytes, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at)
            VALUES (:id, :image_bytes, :name, :description, :task_cnt, :log_file_cnt, :anomaly_cnt, :existed_status, :created_at, :updated_at)
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, log_kb_model.model_dump(exclude_none=True)
        )
        return log_kb_model.id if result else ""

    @staticmethod
    async def add_log_kbs(log_kbs: list[LogKnowledgeModel]) -> list[str]:
        """批量添加日志知识库"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(log_kbs), batch_size):
            batch = log_kbs[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO log_knowledge_table (
                        id, image_bytes, name, description, task_cnt, log_file_cnt,
                        anomaly_cnt, existed_status, created_at, updated_at
                    ) VALUES (
                        :id, :image_bytes, :name, :description, :task_cnt, :log_file_cnt,
                        :anomaly_cnt, :existed_status, :created_at, :updated_at
                    )
                """
                params = [
                    log_kb.model_dump(exclude_none=False, by_alias=True)
                    for log_kb in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([log_kb.id for log_kb in batch])
            except Exception as e:
                print(f"批量添加日志知识库失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def delete_log_kb_by_kb_id(kb_id: str) -> bool:
        """根据知识库ID删除日志知识库"""
        sql_str = """
            DELETE FROM log_knowledge_table
            WHERE id = :kb_id
        """
        params = {"kb_id": kb_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def update_log_kb(log_kb_id: str, log_kb_info_dict: dict) -> bool:
        """根据知识库ID更新日志知识库信息"""
        set_clause = ", ".join([f"{key} = :{key}" for key in log_kb_info_dict.keys()])
        sql_str = f"""
            UPDATE log_knowledge_table
            SET {set_clause}, updated_at = :updated_at
            WHERE id = :kb_id
        """
        params = {
            **log_kb_info_dict,
            "kb_id": log_kb_id,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        }
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def count_log_kbs(req: ListLogKnowledgeRequest) -> int:
        sql_str = """
            SELECT COUNT(*) as cnt FROM log_knowledge_table WHERE existed_status = 1
        """
        params = {}
        if req.name:
            sql_str += " AND name LIKE :name"
            params["name"] = f"%{req.name}%"
        if req.description:
            sql_str += " AND description LIKE :description"
            params["description"] = f"%{req.description}%"
        if req.created_at_start:
            sql_str += " AND created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return rows[0]["cnt"] if rows else 0

    @staticmethod
    async def list_log_kbs(req: ListLogKnowledgeRequest) -> list[LogKnowledgeModel]:
        """根据查询条件分页查询日志知识库列表"""
        sql_str = """
            SELECT id, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at
            FROM log_knowledge_table
            WHERE 1=1
        """
        params = {}
        if req.name:
            sql_str += " AND name LIKE :name"
            params["name"] = f"%{req.name}%"
        if req.description:
            sql_str += " AND description LIKE :description"
            params["description"] = f"%{req.description}%"
        if req.created_at_start:
            sql_str += " AND created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end
        sort_order = "ASC" if req.created_sorted_desc else "DESC"
        sql_str += f" ORDER BY created_at {sort_order}"
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        log_kbs = [LogKnowledgeModel.model_validate(row) for row in rows]
        return log_kbs

    @staticmethod
    async def get_log_kb_by_kb_id(kb_id: str) -> LogKnowledgeModel | None:
        """根据知识库ID查询日志知识库信息"""
        sql_str = """
            SELECT id, image_bytes, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at
            FROM log_knowledge_table
            WHERE id = :kb_id
        """
        params = {"kb_id": kb_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            return LogKnowledgeModel.model_validate(rows[0])
        return None
