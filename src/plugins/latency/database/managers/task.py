from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.task import TaskModel
from latency.database.engine import AsyncSQLiteSingleton


class TaskManager:
    """任务管理类"""

    @staticmethod
    async def add_task(task: TaskModel) -> bool:
        """创建新任务"""
        sql_str = """
            INSERT INTO task_table (id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds)
            VALUES (:id, :kb_id, :op_id, :retry_times, :task_name, :task_type, :status, :existed_status, :created_at, :completed_at, :duration_seconds)
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            sql_str, task.model_dump(exclude_none=False, by_alias=True)
        )
        return success

    @staticmethod
    async def add_tasks(tasks: list[TaskModel]) -> list[str]:
        """批量添加任务"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO task_table (id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds)
                    VALUES (:id, :kb_id, :op_id, :retry_times, :task_name, :task_type, :status, :existed_status, :created_at, :completed_at, :duration_seconds)
                """
                params = [
                    task.model_dump(exclude_none=False, by_alias=True) for task in batch
                ]
                success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([task.id for task in batch])
            except Exception as e:
                print(f"批量添加任务失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def delete_task_by_task_id(task_id: str) -> bool:
        """根据任务ID删除任务"""
        sql_str = """
            DELETE FROM task_table
            WHERE id = :task_id
        """
        params = {"task_id": task_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def delete_tasks_by_task_ids(task_ids: list[str]) -> bool:
        """根据任务ID列表删除多个任务"""
        if not task_ids:
            return False
        placeholders = ", ".join(["?"] * len(task_ids))
        sql_str = f"""
            DELETE FROM task_table
            WHERE id IN ({placeholders})
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, tuple(task_ids))
        return success

    @staticmethod
    async def delete_tasks_by_status(status: str) -> bool:
        """根据任务状态删除任务"""
        sql_str = """
            DELETE FROM task_table
            WHERE status = :status
        """
        params = {"status": status}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def update_task(task_id: str, task_info_dict: dict) -> bool:
        """根据任务ID更新任务信息"""
        set_clauses = []
        params = {"task_id": task_id}
        for key, value in task_info_dict.items():
            set_clauses.append(f"{key} = :{key}")
            params[key] = value
        set_clause_str = ", ".join(set_clauses)

        sql_str = f"""
            UPDATE task_table
            SET {set_clause_str}
            WHERE id = :task_id
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def update_running_tasks_to_pending_tasks():
        """将所有正在运行的任务状态更新为待执行（用于服务重启后恢复任务状态）"""
        sql_str = """
            UPDATE task_table
            SET status = :pending_status
            WHERE status = :running_status
        """
        params = {
            "pending_status": TaskStatusEnum.PENDING.value,
            "running_status": TaskStatusEnum.RUNNING.value,
        }
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def list_tasks_by_task_ids(task_ids: list[str]) -> list[TaskModel]:
        """根据任务ID列表获取多个任务信息"""
        if not task_ids:
            return []
        placeholders = ", ".join(["?"] * len(task_ids))
        sql_str = f"""
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE id IN ({placeholders})
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, tuple(task_ids))
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def list_all_tasks() -> list[TaskModel]:
        """获取所有任务"""
        sql_str = """
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            ORDER BY created_at DESC
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def get_task_by_task_id(task_id: str) -> TaskModel | None:
        """根据任务ID获取任务信息"""
        sql_str = """
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE id = :task_id
        """
        params = {"task_id": task_id}
        results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if results:
            return TaskModel(**results[0])
        return None

    @staticmethod
    async def list_tasks_by_kb_id(
        kb_id: str, status: list[TaskStatusEnum] | None = None
    ) -> list[TaskModel]:
        """根据知识库ID获取任务列表"""
        sql_str = """
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE kb_id = :kb_id
        """
        params = {"kb_id": kb_id}
        if status:
            placeholders = ", ".join([f":status_{i}" for i in range(len(status))])
            sql_str += f" AND status IN ({placeholders})"
            for i, s in enumerate(status):
                params[f"status_{i}"] = s.value
        results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def list_tasks_by_status(status: list[TaskStatusEnum]) -> list[TaskModel]:
        """根据任务状态获取任务列表"""
        if not status:
            return []
        placeholders = ", ".join(["?"] * len(status))
        sql_str = f"""
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE status IN ({placeholders})
        """
        tmp_tuple = tuple(s.value for s in status)
        results = await AsyncSQLiteSingleton().execute_query(sql_str, tmp_tuple)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def get_oldest_tasks_by_status(
        status: TaskStatusEnum, limit: int = 10
    ) -> list[TaskModel]:
        """根据任务状态获取最旧的任务列表（按创建时间升序排序）"""
        sql_str = """
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE status = :status
            ORDER BY created_at ASC
            LIMIT :limit
        """
        params = {"status": status.value, "limit": limit}
        results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def list_current_tasks_by_op_ids(
        op_ids: list[str],
        task_type: TaskTypeEnum | None = None,
    ) -> list[TaskModel]:
        """根据操作ID列表获取每个操作ID对应的最新的任务信息"""
        if not op_ids:
            return []
        placeholders = ", ".join(["?"] * len(op_ids))
        params = list(op_ids)
        task_type_filter = ""
        if task_type:
            task_type_filter = " AND task_type = ?"
            params.append(task_type.value)
        sql_str = f"""
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY op_id ORDER BY created_at DESC) as rn
                FROM task_table
                WHERE op_id IN ({placeholders}){task_type_filter}
            ) sub
            WHERE rn = 1
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, tuple(params))
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def get_current_task_by_op_id(
        op_id: str,
        task_type: TaskTypeEnum | None = None,
    ) -> TaskModel | None:
        """根据操作ID获取最新的任务信息（适用于一个操作可能对应多个任务的场景，获取最新的任务）"""
        sql_str = """
            SELECT id, kb_id, op_id, retry_times, task_name, task_type, status, existed_status, created_at, completed_at, duration_seconds
            FROM task_table
            WHERE op_id = :op_id
        """
        params = {"op_id": op_id}
        if task_type:
            sql_str += " AND task_type = :task_type"
            params["task_type"] = task_type.value
        sql_str += """
            ORDER BY created_at DESC
            LIMIT 1
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if results:
            return TaskModel(**results[0])
        return None

    @staticmethod
    async def delete_tasks_by_op_id(op_id: str) -> bool:
        """根据操作ID删除所有相关任务"""
        sql_str = """
            DELETE FROM task_table
            WHERE op_id = :op_id
        """
        params = {"op_id": op_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success
