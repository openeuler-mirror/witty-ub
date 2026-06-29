import logging
import os
import uuid

from latency.common.ds_log_io import open_log
from latency.database.managers.log_failure_event import LogFailureEventManager
from latency.parse import LogParser
from latency.schemas.log_failure_event import LogFailureEventModel


logger = logging.getLogger(__name__)

TRACE_CONTEXT_BATCH_SIZE = 1024


def split_pid_tid(pid_tid: str) -> tuple[str, str]:
    if ":" not in pid_tid:
        return pid_tid.strip(), ""
    pid, tid = pid_tid.split(":", 1)
    return pid.strip(), tid.strip()


def build_trace_context_event(
    log_id: str,
    log_dir: str,
    path: str,
    line_no: int,
    line: str,
    trace_ids: set[str],
) -> LogFailureEventModel | None:
    raw_text = line.strip()
    if not raw_text:
        return None

    parts = LogParser.split_by_delimiter(raw_text)
    if len(parts) < LogParser.RunCol.MSG + 1 or not parts[0].startswith("20"):
        return None

    trace_id = parts[LogParser.RunCol.TRACE_ID].strip()
    if trace_id not in trace_ids:
        return None

    is_access_log = len(parts) >= LogParser.AccessCol.RESP_MSG + 1
    pid, tid = split_pid_tid(parts[LogParser.RunCol.PID_TID])
    log_file = os.path.relpath(path, log_dir) if log_dir else os.path.basename(path)
    host_name = os.path.basename(os.path.dirname(path)) or "Unknown"
    status_code = parts[LogParser.AccessCol.STATUS_CODE].strip() if is_access_log else ""

    if is_access_log:
        operation = parts[LogParser.AccessCol.HANDLE].strip()
        elapsed = parts[LogParser.AccessCol.ELAPSED].strip()
        size = parts[LogParser.AccessCol.SIZE].strip()
        resp_msg = "|".join(parts[LogParser.AccessCol.RESP_MSG :]).strip()
        message = (
            f"{operation} elapsed={elapsed} size={size} "
            f"status_code={status_code} resp={resp_msg}"
        ).strip()
    else:
        message = "|".join(parts[LogParser.RunCol.MSG :]).strip()

    return LogFailureEventModel(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, raw_text)),
        log_id=log_id,
        log_file=log_file,
        raw_text=raw_text,
        host_name=host_name,
        timestamp=parts[LogParser.RunCol.TIMESTAMP].strip(),
        level=parts[LogParser.RunCol.LEVEL].strip() or "INFO",
        filename=parts[LogParser.RunCol.FILENAME].strip(),
        pod_name=parts[LogParser.RunCol.POD_NAME].strip(),
        pid=pid,
        tid=tid,
        trace_id=trace_id,
        cluster_name=parts[LogParser.RunCol.CLUSTER_NAME].strip(),
        message=message,
        status_code=status_code,
        failure_mode=[],
    )


async def collect_trace_context_logs(
    log_id: str,
    log_dir: str,
    trace_ids: set[str],
    clear_existing: bool = False,
) -> int:
    trace_ids = {trace_id.strip() for trace_id in trace_ids if trace_id and trace_id.strip()}
    if clear_existing:
        await LogFailureEventManager.delete_unclassified_log_events_by_log_id(log_id)

    if not trace_ids or not log_dir or not os.path.isdir(log_dir):
        return 0

    total = 0
    batch: list[LogFailureEventModel] = []
    logger.info(
        "Collecting raw trace context logs from %s for %s trace(s)",
        log_dir,
        len(trace_ids),
    )

    for root, _, files in os.walk(log_dir):
        for file_name in files:
            path = os.path.join(root, file_name)
            if not os.path.isfile(path):
                continue

            try:
                with open_log(path) as f:
                    for line_no, line in enumerate(f, 1):
                        event = build_trace_context_event(
                            log_id=log_id,
                            log_dir=log_dir,
                            path=path,
                            line_no=line_no,
                            line=line,
                            trace_ids=trace_ids,
                        )
                        if not event:
                            continue

                        batch.append(event)
                        if len(batch) >= TRACE_CONTEXT_BATCH_SIZE:
                            await LogFailureEventManager.add_log_failure_event_if_not_exist(batch)
                            total += len(batch)
                            batch.clear()
            except EOFError as e:
                logger.warning(
                    "Skipping corrupted file while collecting trace context %s: %s",
                    path,
                    e,
                )
            except Exception as e:
                logger.warning("Error collecting trace context from %s: %s", path, e)

    if batch:
        await LogFailureEventManager.add_log_failure_event(batch)
        total += len(batch)

    logger.info("Stored %s raw trace context log rows", total)
    return total
