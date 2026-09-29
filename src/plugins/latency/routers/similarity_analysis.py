"""相似案例分析路由：根据 log_file_id 提取特征并在案例库中检索最相似的故障类型。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from latency.services.feature_extraction import FeatureExtractionManager
from latency.services.similarity import find_similar_fault_types

router = APIRouter(prefix="/similarity_analysis", tags=["Similarity Analysis"])


class SimilarityRequest(BaseModel):
    """相似案例检索请求体。"""
    log_file_id: str
    top_k: int = 5


@router.post("")
async def analyze_similar_cases(req: SimilarityRequest):
    """根据 log_file_id 提取特征，在案例库中检索 Top-K 最相似的故障类型。

    请求体:
        log_file_id: 日志文件 ID（用于特征提取）
        top_k: 返回的相似案例数量，默认 3

    返回:
        {
            "code": 200,
            "result": {
                "top_matches": [...],
                "library_size": int,
                "unique_types_count": int
            }
        }
    """
    if not req.log_file_id:
        return {"code": 400, "message": "log_file_id 为必填项", "result": None}

    # Step 1: 提取特征
    try:
        features = await FeatureExtractionManager.extract_features(req.log_file_id)
    except Exception as e:
        return {"code": 500, "message": f"特征提取失败: {e}", "result": None}

    if not features:
        return {"code": 500, "message": "特征提取返回空结果", "result": None}

    fault_category = features.get("fault_category", "unknown")

    # Step 2: 在案例库中检索（自动排除同源案例 + 过滤100%自匹配）
    try:
        result = await find_similar_fault_types(
            features, fault_category, req.top_k,
            exclude_log_file_id=req.log_file_id,
        )
    except Exception as e:
        return {"code": 500, "message": f"相似度计算失败: {e}", "result": None}

    return {"code": 200, "message": "分析成功", "result": result}
