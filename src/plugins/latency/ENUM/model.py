from enum import StrEnum, IntEnum

# from tkinter.tix import IMAGE


class ModelLabel(StrEnum):
    """模型标签"""

    TXT2TXT = "txt2txt"
    TXT2IMG = "txt2img"
    IMG2TXT = "img2txt"
    VOICETOTXT = "voicetotxt"
    VIDEOTOTXT = "videototxt"
    OCR = "ocr"
    FUNCTION_CALL = "function_call"
    RERANKER = "reranker"
    TXT2EMBEDDING = "txt2embedding"
    IMAGE2EMBEDDING = "image2embedding"
    VOICE2EMBEDDING = "voice2embedding"
    VIDEO2EMBEDDING = "video2embedding"


class ModelProvider(StrEnum):
    """模型提供商"""

    OPENAI = "openai"
    ASCEND = "ascend"
    BAILIAN = "bailian"
    GUIJILIUDONG = "guijiliudong"
    VLLM = "vllm"
    OLLMA = "ollma"
    OTHER = "other"


class ModelParam(IntEnum):
    EMBEDDING_DIM_LIMIT = 1024


class InputType(StrEnum):
    TEXT = "text"
    IMAGE = "image_url"
    VIDEO = "video_url"
