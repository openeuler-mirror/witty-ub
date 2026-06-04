from latency.schemas.request import CreateLogKnowledgeRequest
from latency.schemas.log import LogKnowledgeModel


class Convertor:
    """数据转换器"""

    @staticmethod
    async def create_log_kb_req_to_log_kb_model(
        req: CreateLogKnowledgeRequest,
    ) -> LogKnowledgeModel:
        """将CreateLogKnowledgeRequest转换为LogKnowledgeModel"""
        log_kb_model = LogKnowledgeModel(
            image_bytes=req.image_bytes or b'',
            name=req.name,
            description=req.description,
        )
        return log_kb_model
