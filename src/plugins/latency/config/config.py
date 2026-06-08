# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""配置文件处理模块"""

import os
from copy import deepcopy
import toml
from latency.schemas.config import ConfigModel


class Config:
    """配置文件读取和使用Class"""

    _config: ConfigModel

    def __init__(self) -> None:
        """读取配置文件；当PROD环境变量设置时，配置文件将在读取后删除"""
        config_file = os.getenv("CONFIG")
        if config_file is None:
            # 使用绝对路径，基于当前文件的位置
            latency_dir = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.join(latency_dir, "static", "config.toml")
        self._config = ConfigModel.model_validate(toml.load(config_file))

    def get_config(self) -> ConfigModel:
        """获取配置文件内容"""
        return deepcopy(self._config)
