# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
from openai import AsyncOpenAI
import urllib3
import logging
import base64
from latency.config.config import Config
from latency.schemas.config import ModelConfig
from latency.ENUM.model import ModelProvider, InputType

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class LLM:
    def __init__(
        self,
        model_config: ModelConfig,
    ):
        self.model_name = model_config.model_name
        self.model_labels = model_config.model_labels
        self.temperature = model_config.temperature
        self.input_max_tokens = model_config.input_max_tokens
        self.output_max_tokens = model_config.output_max_tokens
        self.api_key = model_config.api_key
        self.end_point = model_config.end_point
        self.temperature = model_config.temperature
        self.request_timeout = model_config.request_timeout
        self.batch_size = model_config.batch_size
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.end_point,
        )

    def encode_file(self, file_path: str) -> str:
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")

    async def create_stream(self, message):
        try:
            return await self._client.chat.completions.create(
                model=self.model_name,
                messages=message,  # type: ignore[]
                temperature=self.temperature,
                stream=True,
                timeout=self.request_timeout,
                max_completion_tokens=self.input_max_tokens,
                max_tokens=self.output_max_tokens,
            )
        except Exception as e:
            warning = f"[LLM] create_stream 出现异常: {e}"
            logger.warning(warning)
            return None

    async def data_producer(self, q: asyncio.Queue, message: list[dict[str, str]]):
        stream = await self.create_stream(message)
        if stream is None:
            await q.put(None)
            logger.error("[LLM] 无法创建流式响应，生产者任务退出")
            raise Exception("无法创建流式响应")
        try:
            async for chunk in stream:
                if len(chunk.choices) == 0:
                    continue
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                else:
                    continue
                await q.put(content)
        except Exception as e:
            await q.put(None)
            err = f"[LLM] 流式输出生产者任务异常: {e}"
            logger.error(err)
            raise e
        await q.put(None)

    async def stream(self, message: list[dict[str, str]]):
        q = asyncio.Queue(maxsize=10)

        # 启动生产者任务
        asyncio.create_task(self.data_producer(q, message))
        while True:
            data = await q.get()
            if data is None:
                break
            yield data

    async def text_to_text(
        self,
        message: list[dict[str, str]] = [],
        system_prompt: str = "",
        user_prompt: str = "",
    ) -> str:
        message.extend(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        response = ""
        try:
            async for chunk in self.stream(message):
                response += chunk
        except Exception as e:
            logger.error(f"text_to_text 任务失败: {e}")
            return None
        return response.strip()

    async def check_source_is_online(self, source: str) -> bool:
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(source, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"检查资源在线状态失败: {e}")
            return False

    async def image_to_text(
        self,
        source: str = "",
        prompt: str = "",
    ) -> str:
        if await self.check_source_is_online(source):
            message = [
                {
                    "role": "user",
                    "content": [
                        {"type": InputType.IMAGE.value, "image_url": {"url": source}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        else:
            base64_image = self.encode_file(source)
            message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": InputType.IMAGE.value,
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        response = ""
        try:
            async for chunk in self.stream(message):
                response += chunk
        except Exception as e:
            logger.error(f"image_to_text 任务失败: {e}")
            return None
        return response.strip()

    async def video_to_text(
        self,
        source: str = "",
        prompt: str = "",
    ) -> str:
        if await self.check_source_is_online(source):
            message = [
                {
                    "role": "user",
                    "content": [
                        {"type": InputType.VIDEO.value, "video_url": {"url": source}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        else:
            base64_video = self.encode_file(source)
            message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": InputType.VIDEO.value,
                            "video_url": {
                                "url": f"data:video/mp4;base64,{base64_video}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        response = ""
        try:
            async for chunk in self.stream(message):
                response += chunk
        except Exception as e:
            logger.error(f"video_to_text 任务失败: {e}")
            return None
        return response.strip()
