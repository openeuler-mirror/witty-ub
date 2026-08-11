# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""磁盘类型检测工具单测（T3 / Block F1 验收）。

覆盖：
  1. 4 分支：HDD（rotational=1）/ SSD（rotational=0）/ NVMe（nvme 前缀）/ unknown。
  2. io_concurrency_for 映射：HDD=3 / SSD=cpu_count / NVMe=cpu_count / unknown=3（保守）。
  3. 同目录缓存：同一路径二次检测不重复解析 sysfs。
  4. 分区剥离：nvme0n1p1→nvme0n1、sdd1→sdd、整盘设备名原样。
  5. loop/ram 虚拟设备过滤 → unknown（rotational 语义不可信）。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_disk.py -v -p no:cacheprovider
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from latency.common import disk

REAL_DIR = str(Path(__file__).parent.parent)  # src/plugins/latency


@pytest.fixture(autouse=True)
def _clear_disk_cache():
    """每个用例前清空 detect_disk_type 的 lru_cache，避免 patch 被缓存污染。"""
    disk.detect_disk_type.cache_clear()
    yield
    disk.detect_disk_type.cache_clear()


def _patch_sysfs(monkeypatch, *, block_name=None, rotational=None):
    """mock sysfs 读取：_block_device_name（/sys/dev/block 解析）与 _read_rotational。"""
    monkeypatch.setattr(disk, "_block_device_name", lambda st_dev: block_name)
    monkeypatch.setattr(disk, "_read_rotational", lambda devname: rotational)


class TestDetectDiskType:
    def test_hdd_when_rotational_1(self, monkeypatch):
        _patch_sysfs(monkeypatch, block_name="sdd1", rotational=1)
        assert disk.detect_disk_type(REAL_DIR) == "hdd"

    def test_ssd_when_rotational_0(self, monkeypatch):
        _patch_sysfs(monkeypatch, block_name="sda", rotational=0)
        assert disk.detect_disk_type(REAL_DIR) == "ssd"

    def test_nvme_when_prefix_nvme(self, monkeypatch):
        # 不提供 rotational：若实现先查 rotational 而非 nvme 前缀，将返回 unknown。
        _patch_sysfs(monkeypatch, block_name="nvme0n1p1")
        assert disk.detect_disk_type(REAL_DIR) == "nvme"

    def test_unknown_when_no_sysfs_node(self, monkeypatch):
        # 容器/overlay 下 st_dev 解析失败：/sys/dev/block 无对应节点。
        _patch_sysfs(monkeypatch, block_name=None)
        assert disk.detect_disk_type(REAL_DIR) == "unknown"

    def test_unknown_when_loop_device(self, monkeypatch):
        # loop 设备 rotational 语义不可信，必须先于 rotational 判过滤。
        _patch_sysfs(monkeypatch, block_name="loop0", rotational=1)
        assert disk.detect_disk_type(REAL_DIR) == "unknown"

    def test_unknown_when_ram_device(self, monkeypatch):
        _patch_sysfs(monkeypatch, block_name="ram0", rotational=1)
        assert disk.detect_disk_type(REAL_DIR) == "unknown"

    def test_unknown_when_rotational_missing(self, monkeypatch):
        _patch_sysfs(monkeypatch, block_name="sdb", rotational=None)
        assert disk.detect_disk_type(REAL_DIR) == "unknown"

    def test_unknown_when_path_missing(self):
        assert disk.detect_disk_type("/nonexistent/definitely/missing") == "unknown"

    def test_real_path_returns_valid_type(self):
        # 真实路径断言：恒返回合法枚举，不抛异常。
        assert disk.detect_disk_type(REAL_DIR) in {"hdd", "ssd", "nvme", "unknown"}


class TestIoConcurrencyFor:
    @pytest.mark.parametrize(
        ("disk_type", "expected"),
        [
            ("hdd", 3),
            ("unknown", 3),  # 保守：未知盘按 HDD 限流，避免 IO cap 消失
            ("ssd", os.cpu_count()),
            ("nvme", os.cpu_count()),
        ],
    )
    def test_map(self, monkeypatch, disk_type, expected):
        monkeypatch.setattr(disk, "detect_disk_type", lambda path: disk_type)
        assert disk.io_concurrency_for(REAL_DIR) == expected


class TestCache:
    def test_same_directory_cached(self, monkeypatch):
        calls: list = []
        real_block = disk._block_device_name

        def counting_block(st_dev):
            calls.append(st_dev)
            return real_block(st_dev)

        monkeypatch.setattr(disk, "_block_device_name", counting_block)
        first = disk.detect_disk_type(REAL_DIR)
        second = disk.detect_disk_type(REAL_DIR)
        assert first == second
        assert len(calls) == 1  # 同目录仅检测一次


class TestStripPartition:
    @pytest.mark.parametrize(
        ("devname", "expected"),
        [
            ("nvme0n1p1", "nvme0n1"),
            ("nvme0n1", "nvme0n1"),  # 整盘（namespace 号非分区号）不变
            ("nvme1n2p3", "nvme1n2"),
            ("sdd1", "sdd"),
            ("sdd", "sdd"),
            ("sdaa1", "sdaa"),
            ("mmcblk0p1", "mmcblk0"),
        ],
    )
    def test_strips_partition(self, devname, expected):
        assert disk._strip_partition(devname) == expected
