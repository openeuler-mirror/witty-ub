# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""磁盘类型检测工具（T3 / Block F1）。

通过 os.stat(path).st_dev → /sys/dev/block/{major}:{minor} → 块设备名 →
/sys/block/{dev}/queue/rotational 判断路径所在磁盘为 hdd/ssd/nvme。

- NVMe 由设备名前缀判定（nvme0n1，不依赖 rotational）。
- 容器/overlay 下 st_dev 解析失败，或 loop/ram 虚拟设备（rotational 语义
  不可信）→ 返回 "unknown"。io_concurrency_for 对 unknown 保守取 3，
  防止 HDD 的 IO 并发上限在解析失败时消失。
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

DiskType = str  # "hdd" | "ssd" | "nvme" | "unknown"

# loop/ram/zram 为虚拟设备，rotational 不可信 → 一律 unknown
_VIRTUAL_DEVICE_PREFIXES = ("loop", "ram", "zram")

# nvme 整盘形如 nvme0n1（末尾数字为 namespace 号，非分区号），分区为 nvme0n1p1
_NVME_PARTITION_RE = re.compile(r"^(nvme\d+n\d+)p\d+$")
_MMCBLK_PARTITION_RE = re.compile(r"^(mmcblk\d+)p\d+$")

_HDD_CONCURRENCY = 3


def _strip_partition(devname: str) -> str:
    """剥离分区号：nvme0n1p1→nvme0n1、mmcblk0p1→mmcblk0、sdd1→sdd。

    整盘设备名（nvme0n1、sdd、sdaa）原样返回；nvme namespace 号不是分区号。
    """
    if devname.startswith("nvme"):
        return _NVME_PARTITION_RE.sub(r"\1", devname)
    if devname.startswith("mmcblk"):
        return _MMCBLK_PARTITION_RE.sub(r"\1", devname)
    return devname.rstrip("0123456789")


def _block_device_name(st_dev: int) -> str | None:
    """st_dev → /sys/dev/block/{major}:{minor} → 块设备名。

    解析失败（容器/overlay 无对应节点）返回 None。
    """
    major = (st_dev >> 8) & 0xFFF
    minor = (st_dev & 0xFF) | ((st_dev >> 12) & 0xFFF00)
    sys_path = f"/sys/dev/block/{major}:{minor}"
    if not os.path.exists(sys_path):
        return None
    return os.path.basename(os.path.realpath(sys_path))


def _read_rotational(devname: str) -> int | None:
    """读取 /sys/block/{dev}/queue/rotational（0=SSD，1=HDD）。缺失/不可读返回 None。"""
    rot_path = f"/sys/block/{devname}/queue/rotational"
    try:
        with open(rot_path, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=None)
def detect_disk_type(path: str) -> str:
    """返回路径所在磁盘类型："hdd" | "ssd" | "nvme" | "unknown"。

    链路：os.stat(path).st_dev → major/minor → /sys/dev/block/{major}:{minor}
    → realpath 块设备名 → 剥离分区号 → 虚拟设备过滤 → nvme 前缀判 NVMe →
    rotational 判 HDD/SSD。同目录结果缓存（检测一次）。
    """
    try:
        st = os.stat(path)
    except OSError:
        return "unknown"
    devname = _block_device_name(st.st_dev)
    if devname is None:
        return "unknown"
    devname = _strip_partition(devname)
    if devname.startswith(_VIRTUAL_DEVICE_PREFIXES):
        return "unknown"
    if devname.startswith("nvme"):
        return "nvme"
    rotational = _read_rotational(devname)
    if rotational is None:
        return "unknown"
    return "hdd" if rotational else "ssd"


def io_concurrency_for(log_dir: str) -> int:
    """按磁盘类型返回 IO 并发数：HDD=3；SSD/NVMe=os.cpu_count()；unknown=3（保守）。"""
    if detect_disk_type(log_dir) in ("hdd", "unknown"):
        return _HDD_CONCURRENCY
    return os.cpu_count() or _HDD_CONCURRENCY
