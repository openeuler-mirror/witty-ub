import os
import json
import logging
from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel
from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgePGManager
from latency.schemas.response import (
    GetFailureModeMsg,
    GetStatusCodeKnowledgeMsg,
)

logger = logging.getLogger(__name__)

KVCACHE_ERROR_CODE_FILE = "kvcache_error_code_info.json"
KVCACHE_FAILURE_MODE_FILE = "kvcache_failure_mode.json"
URMA_FAILURE_MODE_FILE = "urma_failure_mode.json"
KVCACHE_TREE_MODULE = "kvcache"
URMA_TREE_MODULE = "urma"
UNKNOWN_KVCACHE_FAILURE_MODE_ID = "kvcache_failure_unknown"


class FailureModeKnowledge:
    @staticmethod
    async def init_failure_mode_knowledge() -> list[FailureModeModel]:
        witty_dir = os.getenv("WITTY_DIR")
        if not witty_dir:
            witty_dir = "/var/witty-ub"
        
        data_path = os.path.join(witty_dir, "data")
        logger.info(f"故障模式数据路径: {data_path}")
        
        failure_modes = []

        status_code_json_path = os.path.join(
            data_path, "kvcache", KVCACHE_ERROR_CODE_FILE
        )
        try:
            with open(status_code_json_path, "r", encoding="utf-8") as f:
                status_code_data = json.load(f)

            if not isinstance(status_code_data, dict):
                raise ValueError("故障码知识文件顶层必须是对象")
            status_code_knowledge = []
            for status_code, info in status_code_data.items():
                status_code_knowledge.append(
                    StatusCodeKnowledgeModel(
                        status_code=str(status_code),
                        symptom=info.get("故障现象", ""),
                        root_cause=info.get("故障原因", ""),
                    )
                )
            await FailureModeKnowledgePGManager.add_status_code_knowledge(
                status_code_knowledge
            )
            logger.info("成功初始化故障码知识库: 共 %d 条", len(status_code_knowledge))
        except FileNotFoundError:
            logger.error("故障码知识文件不存在: %s", status_code_json_path)
        except Exception as e:
            logger.error("读取故障码知识失败: %s", str(e))
        
        kvcache_json_path = os.path.join(
            data_path, "kvcache", KVCACHE_FAILURE_MODE_FILE
        )
        try:
            with open(kvcache_json_path, "r", encoding="utf-8") as f:
                kvcache_data = json.load(f)
            
            for row in kvcache_data:
                failure_mode = FailureModeModel(
                    id=row.get("故障编号", ""),
                    name=row.get("故障名称", ""),
                    symptom=row.get("故障现象", ""),
                    root_cause=row.get("故障原因", ""),
                    solution=row.get("解决办法", ""),
                    failure_domain=row.get("故障域", ""),
                    children_failure_mode_ids="",
                    error_code=row.get("错误码"),
                )
                failure_modes.append(failure_mode)
            logger.info(f"成功读取 kvcache 故障模式: {len(kvcache_data)} 条")
        except FileNotFoundError:
            logger.error(f"kvcache 故障模式文件不存在: {kvcache_json_path}")
        except Exception as e:
            logger.error(f"读取 kvcache 故障模式失败: {str(e)}")

        if not any(
            mode.id == UNKNOWN_KVCACHE_FAILURE_MODE_ID for mode in failure_modes
        ):
            failure_modes.append(
                FailureModeModel(
                    id=UNKNOWN_KVCACHE_FAILURE_MODE_ID,
                    name="未知故障",
                    symptom="状态码非0且未匹配其他已知故障模式",
                    root_cause="识别到未知状态码，当前知识库中没有对应故障模式",
                    solution="请联系管理员更新故障模式知识库",
                    failure_domain="KVCache",
                    children_failure_mode_ids="",
                )
            )
        
        urma_json_path = os.path.join(data_path, "urma", URMA_FAILURE_MODE_FILE)
        urma_count = 0
        try:
            with open(urma_json_path, "r", encoding="utf-8") as f:
                urma_data = json.load(f)
            
            for row in urma_data:
                failure_mode = FailureModeModel(
                    id=row.get("故障编号", ""),
                    name=row.get("故障名称", ""),
                    symptom=row.get("故障现象", ""),
                    root_cause=row.get("故障原因", ""),
                    solution=row.get("解决办法", ""),
                    failure_domain=row.get("故障域", ""),
                    children_failure_mode_ids="",
                    error_code=row.get("错误码"),
                )
                failure_modes.append(failure_mode)
                urma_count += 1
            logger.info(f"成功读取 urma 故障模式: {urma_count} 条")
        except FileNotFoundError:
            logger.error(f"urma 故障模式文件不存在: {urma_json_path}")
        except Exception as e:
            logger.error(f"读取 urma 故障模式失败: {str(e)}")
        
        tree_json_path = os.path.join(data_path, "failure_mode_tree.json")
        try:
            with open(tree_json_path, "r", encoding="utf-8") as f:
                tree_data = json.load(f)
            
            children_map = {}
            for category in [KVCACHE_TREE_MODULE, URMA_TREE_MODULE]:
                if category in tree_data:
                    for mode_id, children_ids in tree_data[category].items():
                        if children_ids:
                            children_map[mode_id] = ",".join(children_ids)
            
            for failure_mode in failure_modes:
                if failure_mode.id in children_map:
                    failure_mode.children_failure_mode_ids = children_map[failure_mode.id]
            
            logger.info(f"成功读取故障模式树关系: {len(children_map)} 条")
        except FileNotFoundError:
            logger.error(f"故障模式树文件不存在: {tree_json_path}")
        except Exception as e:
            logger.error(f"读取故障模式树关系失败: {str(e)}")
        
        if failure_modes:
            await FailureModeKnowledgePGManager.add_failure_mode_knowledge(failure_modes)
            logger.info(f"成功初始化故障模式知识库: 共 {len(failure_modes)} 条")
        return failure_modes

    @staticmethod
    async def get_failure_mode_knowledege_by_id(failure_mode_id: str) -> GetFailureModeMsg:
        failure_mode_model = await FailureModeKnowledgePGManager.get_failure_mode_by_id(failure_mode_id)
        return GetFailureModeMsg(failure_mode=failure_mode_model)

    @staticmethod
    async def get_status_code_knowledge(status_code: str) -> GetStatusCodeKnowledgeMsg:
        status_code_info = await FailureModeKnowledgePGManager.get_status_code_knowledge(
            status_code
        )
        return GetStatusCodeKnowledgeMsg(status_code_info=status_code_info)
