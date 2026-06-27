from typing import Optional
from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel
from latency.database.engine import AsyncSQLiteSingleton


class FailureModeKnowledgeManager:
    @staticmethod
    async def get_status_code_knowledge(
        status_code: str,
    ) -> Optional[StatusCodeKnowledgeModel]:
        sql_str = """
            SELECT status_code, symptom, root_cause
            FROM status_code_knowledge_table
            WHERE status_code = :status_code
        """
        results = await AsyncSQLiteSingleton().execute_query(
            sql_str, {"status_code": status_code}
        )
        if results:
            return StatusCodeKnowledgeModel(**results[0])
        return None

    @staticmethod
    async def add_status_code_knowledge(
        results: list[StatusCodeKnowledgeModel],
    ) -> list[str]:
        if not results:
            return []
        sql_str = """
            INSERT OR REPLACE INTO status_code_knowledge_table
            (status_code, symptom, root_cause)
            VALUES (:status_code, :symptom, :root_cause)
        """
        params = [result.model_dump() for result in results]
        await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return [result.status_code for result in results]

    @staticmethod
    async def get_failure_mode_by_id(failure_mode_id: str) -> Optional[FailureModeModel]:
        sql_str = """
            SELECT id, name, symptom, root_cause, solution, failure_domain, children_failure_mode_ids
            FROM failure_mode_knowledge_table
            WHERE id = :id
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, {"id": failure_mode_id})
        if results:
            return FailureModeModel(**results[0])
        return None
    
    @staticmethod
    async def get_all_failure_modes() -> dict[str, FailureModeModel]:
        sql_str = """
            SELECT id, name, symptom, root_cause, solution, failure_domain, children_failure_mode_ids
            FROM failure_mode_knowledge_table
        """
        results = await AsyncSQLiteSingleton().execute_query(sql_str, {})
        return {result["id"]: FailureModeModel(**result) for result in results}

    @staticmethod
    async def add_failure_mode_knowledge(results: list[FailureModeModel]) -> list[str]:
        ids_added = []
        if not results:
            return ids_added
        
        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            try:
                sql_str = """
                    INSERT OR REPLACE INTO failure_mode_knowledge_table 
                    (id, name, symptom, root_cause, solution, failure_domain, children_failure_mode_ids)
                    VALUES (:id, :name, :symptom, :root_cause, :solution, :failure_domain, :children_failure_mode_ids)
                """
                params = [
                    failure_mode.model_dump(exclude_none=False, by_alias=True)
                    for failure_mode in batch
                ]
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([failure_mode.id for failure_mode in batch])
            except Exception as e:
                print(f"批量添加故障模式知识失败，错误信息: {str(e)}")
        return ids_added
