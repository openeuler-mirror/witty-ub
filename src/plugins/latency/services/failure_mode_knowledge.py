import os
import json
import logging
from latency.schemas.failure_mode import FailureModeModel
from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgeManager
from latency.schemas.response import (
    GetFailureModeMsg,
)

logger = logging.getLogger(__name__)


class FailureModeKnowledge:
    @staticmethod
    async def init_failure_mode_knowledge() -> list[FailureModeModel]:
        witty_dir = os.getenv("WITTY_DIR")
        if not witty_dir:
            witty_dir = "/var/witty-ub"
        
        data_path = os.path.join(witty_dir, "data")
        logger.info(f"故障模式数据路径: {data_path}")
        
        failure_modes = []
        
        kvcache_json_path = os.path.join(data_path, "kvcache", "kvcache_conn_fault_mode.json")
        if os.path.exists(kvcache_json_path):
            try:
                with open(kvcache_json_path, "r", encoding="utf-8") as f:
                    kvcache_data = json.load(f)
                
                for row in kvcache_data:
                    failure_mode = FailureModeModel(
                        id=row.get("故障编码", ""),
                        name=row.get("故障名称", ""),
                        symptom=row.get("故障现象", ""),
                        root_cause=row.get("故障原因", ""),
                        solution=row.get("解决办法", ""),
                        failure_domain=row.get("故障域", ""),
                        children_failure_mode_ids=""
                    )
                    failure_modes.append(failure_mode)
                logger.info(f"成功读取 kvcache 故障模式: {len(kvcache_data)} 条")
            except Exception as e:
                logger.error(f"读取 kvcache 故障模式失败: {str(e)}")
        
        urma_json_path = os.path.join(data_path, "urma", "urma_failure_mode_tree.json")
        urma_count = 0
        if os.path.exists(urma_json_path):
            try:
                with open(urma_json_path, "r", encoding="utf-8") as f:
                    urma_data = json.load(f)
                
                for row in urma_data:
                    failure_mode = FailureModeModel(
                        id=row.get("故障编码", ""),
                        name=row.get("故障名称", ""),
                        symptom=row.get("故障表现（验证方法）", ""),
                        root_cause=row.get("故障原因", ""),
                        solution=row.get("解决办法", ""),
                        failure_domain=row.get("故障域", ""),
                        children_failure_mode_ids=""
                    )
                    failure_modes.append(failure_mode)
                    urma_count += 1
                logger.info(f"成功读取 urma 故障模式: {urma_count} 条")
            except Exception as e:
                logger.error(f"读取 urma 故障模式失败: {str(e)}")
        
        tree_json_path = os.path.join(data_path, "failure_mode_tree.json")
        if os.path.exists(tree_json_path):
            try:
                with open(tree_json_path, "r", encoding="utf-8") as f:
                    tree_data = json.load(f)
                
                children_map = {}
                for category in ["kvcache_conn", "urma"]:
                    if category in tree_data:
                        for mode_id, children_ids in tree_data[category].items():
                            if children_ids:
                                children_map[mode_id] = ",".join(children_ids)
                
                for failure_mode in failure_modes:
                    if failure_mode.id in children_map:
                        failure_mode.children_failure_mode_ids = children_map[failure_mode.id]
                
                logger.info(f"成功读取故障模式树关系: {len(children_map)} 条")
            except Exception as e:
                logger.error(f"读取故障模式树关系失败: {str(e)}")
        
        if failure_modes:
            await FailureModeKnowledgeManager.add_failure_mode_knowledge(failure_modes)
            logger.info(f"成功初始化故障模式知识库: 共 {len(failure_modes)} 条")
        return failure_modes

    @staticmethod
    async def get_failure_mode_knowledege_by_id(failure_mode_id: str) -> GetFailureModeMsg:
        failure_mode_model = await FailureModeKnowledgeManager.get_failure_mode_by_id(failure_mode_id)
        return GetFailureModeMsg(failure_mode=failure_mode_model)
