from latency.ENUM.task import TaskStatusEnum
from latency.schemas.task import TaskReportModel
from latency.database.engine import AsyncSQLiteSingleton


class TaskReportManager:
    """任务报告管理类"""

    @staticmethod
    async def add_task_report(task_report: TaskReportModel) -> bool:
        """创建新任务"""
        sql_str = """
            INSERT INTO task_report_table (task_id, progress, message, existed_status, created_at)
            VALUES (:task_id, :progress, :message, :existed_status, :created_at)
        """
        success, _ = await AsyncSQLiteSingleton().execute_modify(
            sql_str, task_report.model_dump(exclude_none=False, by_alias=True)
        )
        return success

    @staticmethod
    async def add_task_reports(task_reports: list[TaskReportModel]) -> list[str]:
        """批量添加任务报告"""
        ids_added = []
        batch_size = 1024
        for i in range(0, len(task_reports), batch_size):
            batch = task_reports[i : i + batch_size]
            try:
                sql_str = """
                    INSERT INTO task_report_table (
                        task_id, progress, message, existed_status, created_at
                    ) VALUES (
                        :task_id, :progress, :message, :existed_status, :created_at
                    )
                """
                params = [
                    tr.model_dump(exclude_none=False, by_alias=True) for tr in batch
                ]
                success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([tr.task_id for tr in batch])
            except Exception as e:
                print(f"批量添加任务报告失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def update_task_reports_existed_status_by_task_id(
        task_id: str, existed_status: int
    ) -> bool:
        """根据任务ID更新任务报告的存在状态"""
        sql_str = """
            UPDATE task_report_table
            SET existed_status = :existed_status
            WHERE task_id = :task_id
        """
        params = {"task_id": task_id, "existed_status": existed_status}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def list_task_reports_by_task_ids(
        task_ids: list[str],
    ) -> list[TaskReportModel]:
        """根据任务ID列表获取任务报告列表"""
        if not task_ids:
            return []
        placeholders = ", ".join(["?"] * len(task_ids))
        sql_str = f"""
            SELECT task_id, progress, message, created_at
            FROM task_report_table
            WHERE task_id IN ({placeholders})
            ORDER BY created_at DESC
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, tuple(task_ids))
        return [TaskReportModel(**result) for result in results]
