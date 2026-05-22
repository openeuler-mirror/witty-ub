from latency.ENUM.task import TaskStatusEnum
from latency.schemas.task import TaskReportModel
from latency.database.engine import AsyncSQLiteSingleton


class TaskReportManager:
    """任务报告管理类"""

    @staticmethod
    async def create_task(task_report: TaskReportModel) -> bool:
        """创建新任务"""
        sql_str = """
            INSERT INTO task_report_table (task_id, progress, message)
            VALUES (:task_id, :progress, :message)
        """
        result = await AsyncSQLiteSingleton().execute_modify(
            sql_str, task_report.model_dump(exclude_none=False, by_alias=True)
        )
        return result
