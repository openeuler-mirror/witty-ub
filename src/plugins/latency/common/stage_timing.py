"""结构化分阶段耗时打点：一条任务报告，行内紧凑 JSON，前端直接渲染。

契约（冻结 —— 前端按此解析，改动前先对齐前端）::

    [timing] {"task_type":"kv_cache_log_parse_worker","started_at":"2026-09-15T23:01:00.000",
     "finished_at":"2026-09-15T23:01:02.345","total_s":11.885,"rows":1909790,
     "stages":[{"stage":"scan","label":"扫描","wall_s":2.304,"cpu_s":18.05,"cores":7.83,
                "start_s":0.004,"end_s":2.308,"detail":"11 文件 / 1909790 行",
                "occurrences":[{"start_s":0.004,"end_s":2.308,"wall_s":2.304,
                                "detail":"11 文件 / 1909790 行"}]}]}
    （上面为便于阅读折了行；实际是**单行**紧凑 JSON。）

  - 前缀严格为 ``[timing] ``（含一个空格），其后是**单行**紧凑 JSON（JSON 内无换行）。
  - 顶层键 ``task_type``(str|null，``TaskTypeEnum`` 的值) / ``started_at``(str|null，ISO
    毫秒 —— **worker 真正开工的时刻**，口径见下；老报告没有这个键) / ``finished_at``
    (str，ISO 毫秒 —— **发出这条报告的时刻**) / ``total_s``(float) / ``rows``(int) /
    ``stages``(list，按管线顺序)。
  - stage 键按任务分三组（中文 label 见 ``STAGE_LABELS``，固定映射）：
    - 解析：``scan | trace_frame | aggregate | detail | bucket | store``
    - 故障定界：``diagnose_prepare``(准备) / ``diagnose_tool``(运行定界工具) /
      ``diagnose_persist``(落失败事件)
    - 上下文落库：``trace_store_wait``(等诊断完成) / ``trace_store_collect``
      (生成 trace_id 集合) / ``trace_store_write``(落库)
    ``wall_s`` / ``start_s`` / ``end_s`` 保留 3 位小数；``cpu_s`` / ``cores`` /
    ``start_s`` / ``end_s`` 可以是 null；``detail`` 是写清规模的字符串（可空）。
  - ``start_s`` / ``end_s`` = 该阶段起止**相对本任务 run() 起点**的秒偏移：
    起点 = 构造计时器时给的 ``started_at``（解析/定界/落库三个 worker 都在 run()
    入口取 ``time.perf_counter()``）。同一阶段登记多次（落库任务的三段各走两遍：
    等诊断→落库，然后再等解析→再落库）→ 这里的跨度取 [最早起点, 最晚终点]，覆盖该阶段的
    每一次登记，于是 **跨度 ≥ wall_s 恒成立**；代价是相邻阶段会有真实的重叠。
    渲染时只保证"不回退"：``start_s`` 序列、``end_s`` 序列各自非递减，且
    ``end_s ≥ start_s``（不把后一段的起点硬推到前一段终点之后 —— 那会画出自相矛盾的
    位置，2026-09-15 在落库任务上实测到过）。
  - ``occurrences`` = 该阶段**每一次登记的原始起止**（新增键，2026-09-15）：每条
    ``{"start_s","end_s","wall_s","detail"}``，按登记先后；只登记一次就是长度 1。
    它不受上面那套"不回退"钳制 —— 每次都是真实时刻，前端按此逐次画块，就不会把
    "等定界"和"等解析"两段并成一条横跨中间干活的假块。老报告没有这个键。
  - 没测到的阶段**不出现**（不补 0 占位）；``total_s`` = 已测阶段 ``wall_s`` 之和。
  - 发出通路 = ``BaseWorker.report(task_id, message, 0.0)``（前端从
    ``/log_file/list`` 的 ``task_reports`` 取）。

用法::

    timer = StageTimer(task_type="kv_cache_log_parse_worker", started_at=t_run_start)
    with timer.stage("scan") as scope:
        ...
        scope.detail = "11 文件 / 1909790 行"    # detail 在块内赋值(块退出时登记)
    timer.add("aggregate", wall_s=2.5, detail="端点 12 / 时间窗 8")  # 手工登记
    await timer.emit(task_id, rows=1909790)     # 发那一条报告

口径（先写清，免得读的人猜）::

  - ``wall_s``: ``time.perf_counter`` 差；同一阶段被登记多次（例如 ``store``
    同时覆盖"分桶表插入"和"主落库"）→ 累加。
  - ``cpu_s``: **本进程** CPU 秒 = ``/proc/self/stat`` 的 utime+stime 之差
    （第 14/15 字段，单位 tick）除以 ``os.sysconf("SC_CLK_TCK")``；spawn 出去的
    子进程不计入。平台不支持（Windows 无 /proc、无 os.sysconf）或读取失败 →
    ``null``，绝不抛异常。同一阶段多段登记时累加可读到的段，一段都读不到才
    给 ``null``（不会把"读不到"记成 0）。
  - ``cores``: ``cpu_s / wall_s``（仅 ``wall_s > 0`` 才算）；>1 表示这一段确实
    并行跑了。
  - ``started_at``: 构造 ``StageTimer`` 时取的 ``local_now().isoformat(timespec=
    "milliseconds")``。三个 worker 都紧挨着 ``t_run_start = time.perf_counter()``
    构造它，所以它就是 ``run()`` 起点 —— 阶段偏移 ``start_s`` 的原点。
    它与"任务创建时刻"（``task.created_at``，也约等于最早一条报告 "Task initialized"
    的时间）**不是同一个点**：中间隔着等调度器下一拍（1s 轮询，0~1s）与 worker
    子进程冷启动（实测 ~0.9s，重新 import 一千多个模块）。前端必须用 ``started_at``
    当阶段块锚点，否则那段落差会被显示成泳道尾部一段凭空的"收尾"。
  - ``finished_at``: ``local_now().isoformat(timespec="milliseconds")``，取在 ``emit``
    里、发报告之前 —— 就是"这个任务实际干完的时刻"（三个 worker 都在 ``run()`` 结尾
    emit）。服务层用它当任务跨度的右端：``task.completed_at`` 由调度器**下一拍**
    （1 秒轮询）才写进库，比真实干完晚最多 ~1s，会在泳道右端留下一段说不清的收尾。

打点绝不能弄挂任务：``emit`` 内部整块 try/except，失败只 ``logger.warning``；
调用方拿到的 ``stage_timer`` 可能是 ``None``，用 ``as_stage_timer`` 兜底。
"""

import json
import logging
import os
import time

from latency.common.local_time import local_now

logger = logging.getLogger(__name__)

# 阶段键 → 中文标签（冻结映射，前端按 label 显示）
STAGE_LABELS = {
    # 解析任务（kv_cache_log_parse_worker）
    "scan": "扫描",
    "trace_frame": "归并",
    "aggregate": "聚合",
    "detail": "明细",
    "bucket": "分桶",
    "store": "写库",
    # 故障定界任务（kv_cache_log_event_diagnosis_worker）
    "diagnose_prepare": "准备",
    "diagnose_tool": "运行定界工具",
    "diagnose_persist": "落失败事件",
    # 上下文落库任务（store_trace_context_logs_worker）
    "trace_store_wait": "等待前序任务",
    "trace_store_collect": "生成 trace_id 集合",
    "trace_store_write": "落库",
}

# 输出顺序 = 管线顺序（解析六段 → 定界三段 → 落库三段）；一个计时器只属于一个
# 任务，因此实际只出现该任务的那几段；未测到的阶段不出现
STAGE_ORDER = (
    "scan",
    "trace_frame",
    "aggregate",
    "detail",
    "bucket",
    "store",
    "diagnose_prepare",
    "diagnose_tool",
    "diagnose_persist",
    "trace_store_wait",
    "trace_store_collect",
    "trace_store_write",
)

# 报告前缀（前端按此前缀过滤出那一行）
TIMING_MESSAGE_PREFIX = "[timing] "

WALL_DECIMALS = 3
CPU_DECIMALS = 2
CORES_DECIMALS = 2


def read_cpu_seconds():
    """本进程累计 CPU 秒（utime+stime）；读不到返回 ``None``，不抛。"""
    try:
        with open("/proc/self/stat", "rb") as fh:
            stat = fh.read().decode("ascii", "replace")
        # 第 2 字段 comm 可含空格/括号 → 从最后一个 ')' 之后切，下一个是 state(第 3 字段)
        fields = stat.rsplit(")", 1)[1].split()
        ticks = int(fields[11]) + int(fields[12])  # utime(14) + stime(15)
        return ticks / float(os.sysconf("SC_CLK_TCK"))
    except Exception:  # 非 Linux / 读失败: 如实给 null
        logger.debug("[timing] cpu seconds unavailable", exc_info=True)
        return None


def _clean_detail(detail) -> str:
    """detail 必须单行：换行/多余空白压成单个空格（JSON 内不得有换行）。"""
    if not detail:
        return ""
    return " ".join(str(detail).split())


class _StageRecord:
    """一个阶段的累计记录（同一阶段被登记多次就累加）。"""

    __slots__ = ("key", "wall", "cpu", "cpu_seen", "detail", "start", "end", "occurrences")

    def __init__(self, key):
        self.key = key
        self.wall = 0.0
        self.cpu = 0.0
        self.cpu_seen = False
        self.detail = ""
        # 该阶段的绝对时钟点（最早起点 / 最晚终点）；None = 取不到
        self.start = None
        self.end = None
        # 逐次登记（每次 add 一条）；合并跨度无法表达"同一阶段跑了两遍"
        self.occurrences: list[dict] = []

    def add(self, wall_s, cpu_s, detail, start=None, end=None):
        self.wall += max(0.0, float(wall_s))
        if cpu_s is not None:
            self.cpu += float(cpu_s)
            self.cpu_seen = True
        if detail and not self.detail:
            self.detail = str(detail)
        if start is not None:
            self.start = start if self.start is None else min(self.start, start)
        if end is not None:
            self.end = end if self.end is None else max(self.end, end)
        self.occurrences.append(
            {
                "start": start,
                "end": end,
                "wall": max(0.0, float(wall_s)),
                "detail": str(detail) if detail else "",
            }
        )


class _StageScope:
    """``with timer.stage(key) as scope:`` 的句柄；块内可改 ``scope.detail``。"""

    __slots__ = ("_timer", "_key", "_t0", "_c0", "detail")

    def __init__(self, timer, key, detail=""):
        self._timer = timer
        self._key = key
        self._t0 = None
        self._c0 = None
        self.detail = detail or ""

    def __enter__(self):
        # 取时刻 / 读 CPU 分开兜底：读不到 CPU 只丢 cpu_s，wall_s 照记；
        # 两者都不抛给调用方（打点绝不弄挂任务）。
        try:
            self._t0 = self._timer._clock()
            self._timer._note_origin(self._t0)
        except Exception:
            self._t0 = None
            logger.warning("[timing] stage %s clock failed", self._key, exc_info=True)
        try:
            self._c0 = self._timer._cpu()
        except Exception:
            self._c0 = None
            logger.warning("[timing] stage %s cpu read failed", self._key, exc_info=True)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._t0 is None:  # 起点没取到 → 这个阶段不登记
            return False
        try:
            t_end = self._timer._clock()
            wall = t_end - self._t0
        except Exception:
            logger.warning("[timing] stage %s clock failed", self._key, exc_info=True)
            return False
        cpu = None
        if self._c0 is not None:
            try:
                cpu_end = self._timer._cpu()
                if cpu_end is not None:
                    cpu = cpu_end - self._c0
            except Exception:
                logger.warning("[timing] stage %s cpu read failed", self._key, exc_info=True)
        try:
            self._timer.add(
                self._key,
                wall_s=wall,
                cpu_s=cpu,
                detail=self.detail,
                start=self._t0,
                end=t_end,
            )
        except Exception:  # 打点失败绝不影响任务
            logger.warning("[timing] stage %s timing failed", self._key, exc_info=True)
        return False  # 异常照常向上抛


class _NullScope:
    """空计时块：``detail`` 可随意赋值，不产生任何记录。"""

    __slots__ = ("detail",)

    def __init__(self, detail=""):
        self.detail = detail or ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StageTimer:
    """分阶段墙钟 + 进程 CPU 计时器，产出一行 ``[timing] {...}`` 报告。

    Args:
        reporter: ``async (task_id, message, progress) -> Any``；默认（``None``）
            在 ``emit`` 时用 ``BaseWorker.report``，测试注入假 reporter 即可。
        clock: ``() -> float`` 秒；默认 ``time.perf_counter``（测试注入假钟）。
        cpu_reader: ``() -> float | None`` 进程 CPU 秒；默认读 ``/proc/self/stat``。
        started_at: 进程内起点（与 ``clock`` 同时基）——只在没给 ``wall_started_at`` 时用。
        wall_run_started_at: **真正开工时刻**（``datetime``）。默认（``None``）在构造时
            现场取一次 ``local_now()``：调用方都建在 ``run()`` 起点，误差微秒级。
            它写进报告的 ``started_at``，前端据此把阶段块锚到真实位置。
        wall_started_at: **任务创建时刻**（``datetime``）。给了它，``end_to_end_s`` 就是
            "任务创建 → 现在"，含预处理/排队/配置读取/收尾；这才是用户要的端到端。
            同时给出 ``outside_s`` = 端到端 − 各阶段之和。
    """

    def __init__(self, reporter=None, clock=None, cpu_reader=None, started_at=None,
                 wall_started_at=None, task_type=None, wall_run_started_at=None):
        self.stages: dict[str, _StageRecord] = {}
        self._reporter = reporter
        self._clock = clock or time.perf_counter
        self._cpu = cpu_reader or read_cpu_seconds
        self._started_at = started_at
        self._wall_started_at = wall_started_at
        # 开工时刻（墙钟）：构造点 = run() 起点（见 Args），现场取一次。
        # 与 finished_at 同源（local_now），两者之差 = 这个任务真正干了多久。
        self._wall_run_started_at = wall_run_started_at or local_now()
        # TaskTypeEnum 的值（StrEnum / str 都按值收）；给不了就是 null
        self._task_type = getattr(task_type, "value", task_type) or None
        # 阶段偏移的原点 = run() 起点（started_at）。没给就在首次登记时用当前
        # 时刻兜底 —— 兜底只借已有的那次读钟，不额外读，脚本化时钟的行为不变。
        self._origin = started_at

    def _note_origin(self, t):
        """记下时间轴原点（只在还没有原点时生效）。"""
        if self._origin is None and t is not None:
            self._origin = t

    def _offset(self, t):
        """绝对时钟点 → 相对 run() 起点的秒偏移（3 位小数）；取不到给 None。"""
        if t is None or self._origin is None:
            return None
        return round(max(0.0, float(t) - float(self._origin)), WALL_DECIMALS)

    # ── 登记 ────────────────────────────────────────────────────────────
    def stage(self, key, detail=""):
        """``with`` 块自动记 wall+cpu；未知 key 退化为空块（不污染契约）。"""
        if key not in STAGE_LABELS:
            logger.warning("[timing] unknown stage key %r, timing skipped", key)
            return _NullScope(detail)
        return _StageScope(self, key, detail)

    def add(self, key, wall_s=0.0, cpu_s=None, detail="", start=None, end=None):
        """手工登记一个已有计时点的阶段（worker 里已有时序点用这个）。

        ``start`` / ``end`` 是**绝对时钟点**（与 ``clock`` 同一时基）；不给时按
        "刚结束"记一个终点、起点由 ``wall_s`` 反推，只用于给出时间轴位置。
        """
        if key not in STAGE_LABELS:
            logger.warning("[timing] unknown stage key %r, add() skipped", key)
            return
        if start is None and end is None:
            try:
                end = self._clock()
            except Exception:
                end = None
                logger.warning("[timing] add(%s) clock failed", key, exc_info=True)
            if end is not None:
                self._note_origin(end)
                try:
                    start = end - max(0.0, float(wall_s))
                except Exception:
                    start = None
        rec = self.stages.get(key)
        if rec is None:
            rec = _StageRecord(key)
            self.stages[key] = rec
        rec.add(wall_s, cpu_s, detail, start=start, end=end)

    # ── 输出 ────────────────────────────────────────────────────────────
    def _ordered(self):
        return [self.stages[key] for key in STAGE_ORDER if key in self.stages]

    def to_message(self, rows=0, finished_at=None) -> str:
        """渲染那一条报告；未测到的阶段不出现，total_s = 各阶段 wall_s 之和。

        ``finished_at`` = 这条报告发出的时刻；``emit`` 传入，直接调本方法时现场取。
        """
        finished_at = finished_at or local_now()
        stages = []
        total = 0.0
        prev_start = 0.0  # 不回退：start_s 序列非递减
        prev_end = 0.0    # 不回退：end_s 序列非递减
        for rec in self._ordered():
            wall = round(rec.wall, WALL_DECIMALS)
            total += wall
            cpu = round(rec.cpu, CPU_DECIMALS) if rec.cpu_seen else None
            cores = None
            if cpu is not None and wall > 0:
                cores = round(cpu / wall, CORES_DECIMALS)
            start_s = self._offset(rec.start)
            end_s = self._offset(rec.end)
            if start_s is not None:
                start_s = max(start_s, prev_start)
                prev_start = start_s
            if end_s is not None:
                end_s = max(end_s, start_s if start_s is not None else prev_start, prev_end)
                prev_end = end_s
            stages.append(
                {
                    "stage": rec.key,
                    "label": STAGE_LABELS[rec.key],
                    "wall_s": wall,
                    "cpu_s": cpu,
                    "cores": cores,
                    "start_s": start_s,
                    "end_s": end_s,
                    "detail": _clean_detail(rec.detail),
                    # 逐次登记各一条：前端按此分段渲染（同色多块），
                    # 不做"不回退"钳制 —— 每一次都是真实时刻。
                    "occurrences": [
                        {
                            "start_s": self._offset(occ["start"]),
                            "end_s": self._offset(occ["end"]),
                            "wall_s": round(occ["wall"], WALL_DECIMALS),
                            "detail": _clean_detail(occ["detail"]),
                        }
                        for occ in rec.occurrences
                    ],
                }
            )
        payload = {
            "task_type": self._task_type,
            "started_at": (
                self._wall_run_started_at.isoformat(timespec="milliseconds")
                if self._wall_run_started_at is not None
                else None
            ),
            "finished_at": finished_at.isoformat(timespec="milliseconds"),
            "total_s": round(total, WALL_DECIMALS),
            "rows": int(rows),
            "stages": stages,
        }
        end_to_end = None
        if self._wall_started_at is not None:
            # 以任务创建时刻为起点：含预处理（解压/拷贝）、排队派发、配置读取与收尾。
            end_to_end = (local_now() - self._wall_started_at).total_seconds()
        elif self._started_at is not None:
            end_to_end = self._clock() - self._started_at
        if end_to_end is not None:
            end_to_end = round(max(0.0, end_to_end), WALL_DECIMALS)
            payload["end_to_end_s"] = end_to_end
            payload["outside_s"] = round(max(0.0, end_to_end - total), WALL_DECIMALS)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return TIMING_MESSAGE_PREFIX + body

    async def emit(self, task_id, rows=0) -> str:
        """发那一条报告（``BaseWorker.report(task_id, msg, 0.0)``）；失败只记日志。"""
        try:
            # 发报告的时刻 = 任务实际干完的时刻（这里就是 run() 结尾）。
            message = self.to_message(rows=rows, finished_at=local_now())
            reporter = self._reporter
            if reporter is None:
                from latency.task.worker.base import BaseWorker

                reporter = BaseWorker.report
            await reporter(task_id, message, 0.0)
            return message
        except Exception:
            logger.warning("[timing] emit failed", exc_info=True)
            return ""


class NullStageTimer:
    """No-op 计时器：``stage_timer`` 为 ``None`` 时用它，调用方无需分支。"""

    def stage(self, key, detail=""):
        return _NullScope(detail)

    def add(self, key, wall_s=0.0, cpu_s=None, detail="", start=None, end=None):
        return None

    def to_message(self, rows=0) -> str:
        return ""

    async def emit(self, task_id, rows=0) -> str:
        return ""


def as_stage_timer(timer):
    """``None`` → ``NullStageTimer()``；其余原样返回（转调方免分支）。"""
    return timer if timer is not None else NullStageTimer()
