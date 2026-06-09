from latency.schemas.log import LogFileModel
from latency.schemas.request import ListLogFilesRequest
from latency.database.engine import AsyncSQLiteSingleton


class LogFileManager:
    @staticmethod
    async def add_log_file(log_file: LogFileModel) -> bool:
        """添加日志文件"""
        sql_str = """
            INSERT INTO log_file_table (id, kb_id, name, parse_status, file_path, file_size, anomaly_cnt, trace_failure_event_cnt, existed_status, created_at)
            VALUES (:id, :kb_id, :name, :parse_status, :file_path, :file_size, :anomaly_cnt, :trace_failure_event_cnt, :existed_status, :created_at)
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, log_file.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def add_log_files(log_files: list[LogFileModel]) -> list[str]:
        """批量添加日志文件"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(log_files), batch_size):
            batch = log_files[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO log_file_table (id, kb_id, name, parse_status, file_path, file_size, anomaly_cnt, trace_failure_event_cnt, existed_status, created_at)
                    VALUES (:id, :kb_id, :name, :parse_status, :file_path, :file_size, :anomaly_cnt, :trace_failure_event_cnt, :existed_status, :created_at)
                """
                params = [
                    log_file.model_dump(exclude_none=False, by_alias=True)
                    for log_file in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([log_file.id for log_file in batch])
            except Exception as e:
                print(f"批量添加日志文件失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def delete_log_file_by_log_file_id(log_file_id: str) -> bool:
        """根据日志文件ID删除日志文件"""
        sql_str = """
            DELETE FROM log_file_table
            WHERE id = :log_file_id
        """
        params = {"log_file_id": log_file_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def update_log_file(log_file_id: str, log_file_info_dict: dict) -> bool:
        """根据日志文件ID更新日志文件信息"""
        set_clauses = []
        for key in log_file_info_dict.keys():
            set_clauses.append(f"{key} = :{key}")
        set_clause_str = ", ".join(set_clauses)
        sql_str = f"""
            UPDATE log_file_table
            SET {set_clause_str}
            WHERE id = :log_file_id
        """
        params = {"log_file_id": log_file_id, **log_file_info_dict}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def list_log_files(
        kb_id: str, req: ListLogFilesRequest
    ) -> tuple[int, list[LogFileModel]]:
        """根据知识ID分页查询日志文件列表"""
        sql_str = """
            SELECT id, kb_id, name, parse_status, file_path, file_size, anomaly_cnt, trace_failure_event_cnt, existed_status, created_at
            FROM log_file_table
            WHERE kb_id = :kb_id AND existed_status = 1
        """
        params = {"kb_id": kb_id}
        if req.name:
            sql_str += " AND name LIKE :name"
            params["name"] = f"%{req.name}%"
        if req.parse_status:
            sql_str += " AND parse_status = :parse_status"
            params["parse_status"] = req.parse_status.value
        if req.created_at_start:
            sql_str += " AND created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end
        total_rows = await AsyncSQLiteSingleton().execute_query(
            f"SELECT COUNT(*) as cnt FROM ({sql_str})", params
        )
        total_count = total_rows[0]["cnt"] if total_rows else 0
        if req.created_sorted_desc:
            sql_str += " ORDER BY created_at DESC"
        else:
            sql_str += " ORDER BY created_at ASC"
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        log_files = []
        for row in rows:
            if row.get("trace_failure_event_cnt") is None:
                row["trace_failure_event_cnt"] = 0
            log_files.append(LogFileModel(**row))
        return total_count, log_files

    @staticmethod
    async def get_log_file_by_log_file_id(log_file_id: str) -> LogFileModel | None:
        """根据日志文件ID获取日志文件信息"""
        sql_str = """
            SELECT id, kb_id, name, parse_status, file_path, file_size, anomaly_cnt, trace_failure_event_cnt, existed_status, created_at
            FROM log_file_table
            WHERE id = :log_file_id
        """
        params = {"log_file_id": log_file_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            data = rows[0]
            if data.get("trace_failure_event_cnt") is None:
                data["trace_failure_event_cnt"] = 0
            return LogFileModel(**data)
        return None
