# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""配置模块与日志文件匹配模式补充测试。

覆盖 latency/config/config.py 的初始化异常分支、双检锁竞争分支、
快照读取与热更新/恢复流程，以及 latency/regex/kvcache_log_file.py
的配置加载失败回退与原地刷新逻辑。
"""

import os
import threading

import pytest

import latency.config.config as config_module
from latency.config.config import Config
from latency.regex import kvcache_log_file as rx
from latency.schemas.config import DiagnosisRuntimeConfig


class TestConfigInit:
    def test_missing_config_file_raises(self, monkeypatch, tmp_path):
        """CONFIG 指向的文件与仓库回退路径均不存在时，初始化应抛 FileNotFoundError。"""
        saved_instance = Config._instance
        saved_initialized = Config._initialized
        Config._instance = None
        Config._initialized = False
        # CONFIG 指向不存在的文件，并让所有 diagnosis_config.toml 路径判定为不存在
        monkeypatch.setenv("CONFIG", str(tmp_path / "diagnosis_config.toml"))
        real_exists = os.path.exists
        monkeypatch.setattr(
            os.path,
            "exists",
            lambda p: (
                False if str(p).endswith("diagnosis_config.toml") else real_exists(p)
            ),
        )
        try:
            with pytest.raises(FileNotFoundError, match="配置文件不存在"):
                Config()
        finally:
            Config._instance = saved_instance
            Config._initialized = saved_initialized

    def test_init_double_checked_lock_second_check(self, monkeypatch):
        """双检锁第二次校验：另一线程在抢锁期间完成初始化时，应直接返回不再读文件。"""

        class _RaceSimLock:
            """第二次加锁（即 __init__ 内）前置 _initialized=True，模拟并发竞争窗口。"""

            def __init__(self, inner):
                self._inner = inner
                self._enters = 0

            def __enter__(self):
                self._enters += 1
                if self._enters == 2:
                    Config._initialized = True
                return self._inner.__enter__()

            def __exit__(self, *exc):
                return self._inner.__exit__(*exc)

        saved_instance = Config._instance
        saved_initialized = Config._initialized
        Config._instance = None
        Config._initialized = False
        monkeypatch.setattr(Config, "_lock", _RaceSimLock(threading.RLock()))
        try:
            instance = Config()
            assert instance is Config._instance
            # __init__ 在第二次校验处提前返回，未读取配置文件
            assert not hasattr(instance, "_config")
            assert Config._initialized is True
        finally:
            Config._instance = saved_instance
            Config._initialized = saved_initialized


class TestConfigSnapshotGetters:
    def test_get_config_returns_isolated_snapshot(self):
        """get_config 返回深拷贝快照，外部修改不影响单例。"""
        cfg = Config()
        snap1 = cfg.get_config()
        snap2 = cfg.get_config()
        assert snap1 == snap2
        assert snap1 is not snap2
        snap1.log_filename_pattern.ds_client_access_log_file.append(
            "zzz_snapshot_*.log"
        )
        assert (
            "zzz_snapshot_*.log"
            not in cfg.get_config().log_filename_pattern.ds_client_access_log_file
        )

    def test_get_diagnosis_config_snapshot(self):
        """get_diagnosis_config 每次基于当前配置构造新对象，互不影响。"""
        cfg = Config()
        first = cfg.get_diagnosis_config()
        second = cfg.get_diagnosis_config()
        assert isinstance(first, DiagnosisRuntimeConfig)
        assert first == second
        assert first is not second
        first.log_filename_pattern.ds_client_access_log_file.append(
            "zzz_diag_*.log"
        )
        first.log_analyzer_params.total_p99_threshold_ms = 999.0
        assert (
            "zzz_diag_*.log"
            not in cfg.get_diagnosis_config().log_filename_pattern.ds_client_access_log_file
        )
        assert (
            cfg.get_diagnosis_config().log_analyzer_params.total_p99_threshold_ms
            != 999.0
        )

    def test_get_default_diagnosis_config_snapshot(self):
        """get_default_diagnosis_config 返回启动默认配置的深拷贝快照。"""
        cfg = Config()
        default = cfg.get_default_diagnosis_config()
        assert isinstance(default, DiagnosisRuntimeConfig)
        # 未发生热更新时与当前配置一致
        assert default == cfg.get_diagnosis_config()
        again = cfg.get_default_diagnosis_config()
        assert default is not again
        default.log_filename_pattern.ds_client_access_log_file.append(
            "zzz_default_*.log"
        )
        assert (
            "zzz_default_*.log"
            not in cfg.get_default_diagnosis_config().log_filename_pattern.ds_client_access_log_file
        )


class TestDiagnosisConfigHotUpdate:
    def test_update_and_reset_diagnosis_config(self):
        """热更新诊断配置后立即生效并原地刷新正则模块，reset 可恢复启动默认。"""
        cfg = Config()
        before = cfg.get_config()
        original = cfg.get_diagnosis_config()
        sdk_list_before = rx.SDK_ACCESS_LOG_PATTERNS
        try:
            modified = original.model_copy(deep=True)
            modified.log_filename_pattern.ds_client_access_log_file = [
                "zzz_hotupdate_*.log"
            ]
            modified.log_analyzer_params.total_p99_threshold_ms = 321.0

            result = cfg.update_diagnosis_config(modified)
            assert result.log_filename_pattern.ds_client_access_log_file == [
                "zzz_hotupdate_*.log"
            ]
            assert result.log_analyzer_params.total_p99_threshold_ms == 321.0
            current = cfg.get_diagnosis_config()
            assert current.log_filename_pattern.ds_client_access_log_file == [
                "zzz_hotupdate_*.log"
            ]
            # reload_patterns 原地刷新：列表对象身份不变，内容已更新
            assert rx.SDK_ACCESS_LOG_PATTERNS is sdk_list_before
            assert "zzz_hotupdate_*.log" in rx.SDK_ACCESS_LOG_PATTERNS
            assert (
                rx.CLIENT_INFO_LOG_PATTERNS
                == Config().get_config().log_filename_pattern.ds_client_info_log_file
            )
        finally:
            restored = cfg.reset_diagnosis_config()
        assert restored == original
        assert cfg.get_diagnosis_config() == original
        assert cfg.get_config() == before
        assert "zzz_hotupdate_*.log" not in rx.SDK_ACCESS_LOG_PATTERNS


class TestKvCacheLogFilePatterns:
    def test_load_patterns_fallback_on_config_error(self, monkeypatch):
        """配置加载失败时回退到内置默认匹配模式，并能原地刷新生效。"""

        class _BrokenConfig:
            def __init__(self):
                raise RuntimeError("模拟配置加载失败")

        monkeypatch.setattr(config_module, "Config", _BrokenConfig)
        loaded = rx._load_patterns()
        assert loaded[0] == rx._DEFAULT_SDK_ACCESS_LOG_PATTERNS
        assert loaded[1] == rx._DEFAULT_WORKER_ACCESS_LOG_PATTERNS
        assert loaded[2] == rx._DEFAULT_WORKER_INFO_LOG_PATTERNS
        assert loaded[3] == [
            "SDK_*/ds_client*.INFO.log",
            "SDK_*/*_runtime.log",
            "SDK_*/*_split_runtime.log",
        ]
        try:
            # 异常路径同样应能完成原地刷新并回填默认值
            rx.reload_patterns()
            assert rx.SDK_ACCESS_LOG_PATTERNS == rx._DEFAULT_SDK_ACCESS_LOG_PATTERNS
            assert rx.WORKER_ACCESS_LOG_PATTERNS == (
                rx._DEFAULT_WORKER_ACCESS_LOG_PATTERNS
            )
            assert rx.WORKER_INFO_LOG_PATTERNS == rx._DEFAULT_WORKER_INFO_LOG_PATTERNS
            assert rx.URMA_LOG_PATTERNS is rx.WORKER_INFO_LOG_PATTERNS
            assert rx.CLIENT_INFO_LOG_PATTERNS == loaded[3]
        finally:
            monkeypatch.undo()
            rx.reload_patterns()

    def test_reload_patterns_in_place(self):
        """正常 reload 使用原地更新，已导入列表的引用可以看到新值。"""
        sdk_before = rx.SDK_ACCESS_LOG_PATTERNS
        worker_access_before = rx.WORKER_ACCESS_LOG_PATTERNS
        worker_info_before = rx.WORKER_INFO_LOG_PATTERNS
        rx.reload_patterns()
        assert rx.SDK_ACCESS_LOG_PATTERNS is sdk_before
        assert rx.WORKER_ACCESS_LOG_PATTERNS is worker_access_before
        assert rx.WORKER_INFO_LOG_PATTERNS is worker_info_before
        # 内容与当前配置一致
        filename_config = Config().get_config().log_filename_pattern
        assert rx.SDK_ACCESS_LOG_PATTERNS == (
            filename_config.ds_client_access_log_file
            + filename_config.ds_client_info_log_file
        )
        assert rx.WORKER_ACCESS_LOG_PATTERNS == (
            filename_config.ds_worker_access_log_file
        )
        assert rx.WORKER_INFO_LOG_PATTERNS == filename_config.ds_worker_info_log_file
        assert rx.CLIENT_INFO_LOG_PATTERNS == filename_config.ds_client_info_log_file
