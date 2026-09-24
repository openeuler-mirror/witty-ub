# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Pytest 根 conftest：保证 latency 包可导入（父目录 src/plugins 注入 sys.path）。"""
import os
import sys

_PLUGINS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGINS_DIR not in sys.path:
    sys.path.insert(0, _PLUGINS_DIR)

# 存量 test/ 用平铺导入（如 from test_scan_merge import ...），补回该目录到 sys.path
_TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)
