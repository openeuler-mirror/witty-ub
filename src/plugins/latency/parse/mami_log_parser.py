# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Mami 硬件日志解析器（解析期事实提取，不做任何判断/加权）。

Mami 日志由硬件管理守护进程（``mami_dev_ctrl.bin``）与内核 RAS 一起写出，
时间戳是 journald 的 ``Mon DD HH:MM:SS`` 形式（**不带年份**），与同一 case 的
KVCache 日志处于同一本地时区 —— 年份由 KVCache 故障窗口锚定推断
（见 ``_infer_year``）。

只识别对"硬件故障"有判别力的模板（``MAMI_TEMPLATES``）：

  - ``ras_interrupt``  ：``[mami RAS]``        Ras 中断处理
  - ``link_change``    ：``port_msgq.c``       UB 端口 link 状态翻转
  - ``port_mng_error`` ：``port_mng.c`` ERROR  UB 端口管理错误

其余模块（``tpl`` / ``drm`` / ``UBLINKCOM`` …）在同一窗口内高频刷屏、跨故障域
无区分度，不落库（结论来自案例关键字区分度统计）。

本模块只产出事实（事件 + ``hardware`` 标志）；是否命中故障窗口由调用方用
``filter_by_window`` 完成。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

from latency.common.ds_log_io import glob_paths, open_log

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# journald 单行：userspace 与 kernel 两种前缀都收敛到同一后缀。
#   Oct 21 01:51:04 master mami_dev_ctrl.bin[12351]: <..> [mami ubport] [INFO] [port_msgq.c f 472] msg
#   Oct 21 08:21:11 worker2 kernel: [408094.02] <kworker/..> [mami RAS] [INFO] [ras_intr_handle 387] msg
_LINE_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<hms>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+.*?"
    r"\[mami\s+(?P<module>[^\]]+)\]\s+"
    r"\[(?P<level>[A-Z]+)\]\s+"
    r"\[(?P<loc>[^\]]+)\]\s*"
    r"(?P<msg>.*)$"
)

_DEVID_RE = re.compile(r"devid=(\d+)")
_STATUS_RE = re.compile(r"status=(\d+)")


@dataclass(frozen=True, slots=True)
class MamiEvent:
    """一条窗口内的 mami 故障事实。"""

    timestamp: datetime
    host_name: str
    level: str
    category: str
    signal: str
    message: str
    source_file: str
    hardware: bool


def _match_ras(module: str, level: str, loc: str, msg: str) -> str | None:
    """内核 RAS 中断处理行。"""
    if module.strip().upper() != "RAS" or "Ras interrupt" not in msg:
        return None
    devid = _DEVID_RE.search(msg)
    return f"Ras interrupt(devid={devid.group(1)})" if devid else "Ras interrupt"


def _match_link_change(module: str, level: str, loc: str, msg: str) -> str | None:
    """UB 端口 link 状态翻转（``status=0`` down / ``status=1`` up）。"""
    if "port_msgq.c" not in loc or "Send link change event" not in msg:
        return None
    status = _STATUS_RE.search(msg)
    return f"link change status={status.group(1)}" if status else "link change"


def _match_port_mng(module: str, level: str, loc: str, msg: str) -> str | None:
    """``port_mng.c`` 的 ERROR（Unsupported chip_type / Get trace … Failed）。"""
    if "port_mng.c" not in loc or level != "ERROR":
        return None
    head = msg.split("(", 1)[0].strip().rstrip(".")
    return head or "port_mng error"


#: (category, hardware 标志, 匹配函数)。匹配函数返回 signal 或 None。
MAMI_TEMPLATES = (
    ("ras_interrupt", True, _match_ras),
    ("link_change", True, _match_link_change),
    ("port_mng_error", True, _match_port_mng),
)

#: 硬件故障类 category 集合（供"只看硬件故障"过滤使用）。
MAMI_HARDWARE_CATEGORIES = tuple(
    category for category, hardware, _ in MAMI_TEMPLATES if hardware
)


def _infer_year(anchor: datetime, month: int) -> int:
    """journald 无年份：选与锚点（case 故障窗口）最近的年份。

    月份差 > 6 视为跨年（如 12 月的日志被 1 月的 case 读到时取上一年）。
    """
    if month - anchor.month > 6:
        return anchor.year - 1
    if anchor.month - month > 6:
        return anchor.year + 1
    return anchor.year


def parse_mami_line(
    line: str, anchor: datetime, source_file: str = ""
) -> MamiEvent | None:
    """解析单行 mami 日志；非 mami 行或未命中模板返回 None。"""
    match = _LINE_RE.match(line.rstrip("\r\n"))
    if not match:
        return None
    month = _MONTHS.get(match.group("mon"))
    if month is None:
        return None
    try:
        hour, minute, second = (int(part) for part in match.group("hms").split(":"))
        timestamp = datetime(
            _infer_year(anchor, month), month, int(match.group("day")),
            hour, minute, second,
        )
    except ValueError:
        return None

    module = match.group("module")
    level = match.group("level")
    loc = match.group("loc")
    msg = match.group("msg").strip()
    for category, hardware, matcher in MAMI_TEMPLATES:
        signal = matcher(module, level, loc, msg)
        if signal:
            return MamiEvent(
                timestamp=timestamp,
                host_name=match.group("host"),
                level=level,
                category=category,
                signal=signal,
                message=msg,
                source_file=source_file,
                hardware=hardware,
            )
    return None


def scan_mami_events(
    log_dir: str, patterns: list[str], anchor: datetime
) -> tuple[int, list[MamiEvent]]:
    """递归扫描 ``log_dir`` 下匹配 ``patterns`` 的 mami 文件。

    Returns:
        (命中文件数, 事件列表)；文件读取异常按"跳过该文件"处理，不中断扫描。
    """
    if not log_dir or not patterns:
        return 0, []
    files = glob_paths([os.path.join(log_dir, "**", p) for p in patterns])
    events: list[MamiEvent] = []
    for path in files:
        try:
            with open_log(path) as handle:
                for line in handle:
                    if "[mami " not in line:
                        continue
                    event = parse_mami_line(line, anchor, path)
                    if event is not None:
                        events.append(event)
        except OSError:
            continue
    return len(files), events


def filter_by_window(
    events: list[MamiEvent],
    start: datetime | None,
    end: datetime | None,
) -> list[MamiEvent]:
    """只保留落在 ``[start, end]`` 内的事件；窗口缺失时返回空列表。"""
    if start is None or end is None:
        return []
    return [event for event in events if start <= event.timestamp <= end]
