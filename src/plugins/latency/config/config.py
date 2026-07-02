# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""配置文件处理模块"""

import json
import os
import threading
from copy import deepcopy
from latency.schemas.config import ConfigModel, DiagnosisRuntimeConfig


class Config:
    """只读加载基础配置，并在进程内维护可热更新的诊断配置。"""

    _config: ConfigModel
    _instance = None
    _initialized = False
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """首次构造时从统一配置文件读取默认配置，之后不再重复读取。"""
        if self.__class__._initialized:
            return
        with self.__class__._lock:
            if self.__class__._initialized:
                return
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
            self._default_diagnosis_config = DiagnosisRuntimeConfig(
                log_filename_pattern=deepcopy(self._config.log_filename_pattern),
                log_analyzer_params=deepcopy(self._config.log_analyzer_params),
            )
            self.__class__._initialized = True

    def get_config(self) -> ConfigModel:
        """获取当前生效配置的快照。"""
        with self.__class__._lock:
            return deepcopy(self._config)

    def get_diagnosis_config(self) -> DiagnosisRuntimeConfig:
        """获取当前生效的可热更新诊断配置。"""
        with self.__class__._lock:
            return DiagnosisRuntimeConfig(
                log_filename_pattern=deepcopy(self._config.log_filename_pattern),
                log_analyzer_params=deepcopy(self._config.log_analyzer_params),
            )

    def get_default_diagnosis_config(self) -> DiagnosisRuntimeConfig:
        """获取启动时从原始文件读取的可信默认配置快照。"""
        with self.__class__._lock:
            return deepcopy(self._default_diagnosis_config)

    def update_diagnosis_config(
        self, diagnosis_config: DiagnosisRuntimeConfig
    ) -> DiagnosisRuntimeConfig:
        """更新进程内配置；不会写回启动时读取的原始配置文件。"""
        with self.__class__._lock:
            self._config.log_filename_pattern = deepcopy(
                diagnosis_config.log_filename_pattern
            )
            self._config.log_analyzer_params = deepcopy(
                diagnosis_config.log_analyzer_params
            )

        # 文件匹配模块在导入时会缓存列表，需要显式刷新。
        from latency.regex.kvcache_log_file import reload_patterns

        reload_patterns()
        return self.get_diagnosis_config()

    def reset_diagnosis_config(self) -> DiagnosisRuntimeConfig:
        """恢复启动时从原始文件读取到的默认诊断配置。"""
        return self.update_diagnosis_config(self.get_default_diagnosis_config())
