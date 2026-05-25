from re import L

from latency.ENUM.task import TaskStatusEnum
from latency.schemas.task import TaskModel
from latency.database.engine import AsyncSQLiteSingleton


class TaskManager:
    """任务管理类"""

    @staticmethod
    async def create_task(task: TaskModel) -> bool:
        """创建新任务"""
        sql_str = """
            INSERT INTO task_table (id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at)
            VALUES (:id, :kb_id, :op_id, :task_name, :task_type, :status, :task_related_params, :created_at)
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, task.model_dump(exclude_none=False, by_alias=True)
        )
        return result

    @staticmethod
    async def delete_task_by_task_id(task_id: str) -> bool:
        """根据任务ID删除任务"""
        sql_str = """
            DELETE FROM task_table
            WHERE id = :task_id
        """
        params = {"task_id": task_id}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, tuple(task_ids))
        return result

    @staticmethod
    async def delete_tasks_by_status(status: str) -> bool:
        """根据任务状态删除任务"""
        sql_str = """
            DELETE FROM task_table
            WHERE status = :status
        """
        params = {"status": status}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

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
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def list_tasks_by_task_ids(task_ids: list[str]) -> list[TaskModel]:
        """根据任务ID列表获取多个任务信息"""
        if not task_ids:
            return []
        placeholders = ", ".join(["?"] * len(task_ids))
        sql_str = f"""
            SELECT id,kb_id, op_id, task_name, task_type, status, task_related_params, created_at
            FROM task_table
            WHERE id IN ({placeholders})
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, tuple(task_ids))
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def list_all_tasks() -> list[TaskModel]:
        """获取所有任务"""
        sql_str = """
            SELECT id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at
            FROM task_table
            ORDER BY created_at DESC
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def get_task_by_task_id(task_id: str) -> TaskModel | None:
        """根据任务ID获取任务信息"""
        sql_str = """
            SELECT id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at
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
        kb_id: str, status: List[TaskStatusEnum] | None = None
    ) -> list[TaskModel]:
        """根据知识库ID获取任务列表"""
        sql_str = """
            SELECT id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at
            FROM task_table
            WHERE kb_id = :kb_id
        """
        params = {"kb_id": kb_id}
        if status:
            placeholders = ", ".join(["?"] * len(status))
            sql_str += f" AND status IN ({placeholders})"
            tmp_tuple = tuple(s.value for s in status)
            params.update({f"status_{i}": s.value for i, s in enumerate(status)})
            results = await AsyncSQLiteSingleton().execute_query(
                sql_str, tuple(params.values()) + tmp_tuple
            )
        else:
            results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [TaskModel(**result) for result in results]

    @staticmethod
    async def list_tasks_by_status(status: list[TaskStatusEnum]) -> list[TaskModel]:
        """根据任务状态获取任务列表"""
        if not status:
            return []
        placeholders = ", ".join(["?"] * len(status))
        sql_str = f"""
            SELECT id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at
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
            SELECT id, kb_id, op_id, task_name, task_type, status, task_related_params, created_at
            FROM task_table
            WHERE status = :status
            ORDER BY created_at ASC
            LIMIT :limit
        """
        params = {"status": status.value, "limit": limit}
        results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [TaskModel(**result) for result in results]
