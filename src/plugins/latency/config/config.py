# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""配置文件处理模块"""

import json
import os
from copy import deepcopy
from latency.schemas.config import ConfigModel


class Config:
    """配置文件读取和使用Class"""

    _config: ConfigModel

    def __init__(self) -> None:
        """从统一配置文件读取服务、日志分析及日志文件名配置。"""
        config_file = os.getenv("CONFIG") or "/var/witty-ub/config/diagnosis_config.json"
        if not os.path.exists(config_file):
            # Fallback to the repository config in development environments.
            latency_dir = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.abspath(
                os.path.join(
                    latency_dir,
                    "..",
                    "..",
                    "..",
                    "config",
                    "diagnosis_config.json",
                )
            )
        with open(config_file, "r", encoding="utf-8") as file:
            self._config = ConfigModel.model_validate(json.load(file))

    def get_config(self) -> ConfigModel:
        """获取配置文件内容"""
        return deepcopy(self._config)
