"""Bounded entry batches on disk; hash partitions keep complete traces together."""
from collections import Counter, defaultdict
from pathlib import Path
from io import BytesIO
import logging
import os
import struct
import time

from .columnar import ALL_COLUMNS, entries_to_columns

BATCH_ROWS = 16_384
PARTITIONS = 16
_FRAME_LENGTH = struct.Struct("<Q")
logger = logging.getLogger(__name__)


class SpillError(Exception):
    """Storage failures must fail the scan, never be treated as malformed log lines."""


def scan_schema():
    import polars as pl

    strings = {
        'tid', 'src', 'dst', 'op', 'operation', 'op_key', 'log_id',
        'timestamp', 'pod_ip', 'cluster_name', 'host',
        'data_size', '_label',
    }
    schema = {c: pl.String if c in strings else pl.Float64 for c in ALL_COLUMNS}
    schema.update({c: pl.Float64 for c in (
        '_elapsed_us', '_rpc_e2e_us', '_rpc_server_exec_us', '_rpc_network_us',
    )})
    schema.update({c: pl.Int64 for c in ('status_code', 'bucket_epoch', '_src_rank')})
    schema.update({c: pl.UInt64 for c in ('_scan_group', '_scan_label')})
    return schema


class EntrySpool:
    def __init__(self, directory, group_id, batch_rows=BATCH_ROWS):
        self.directory = Path(directory)
        self.group_id = group_id
        self.batch_rows = batch_rows
        self.labels = {}
        self.counts = Counter()
        self.pending = defaultdict(list)
        self.size = 0
        self.paths = defaultdict(list)
        self.sequence = 0
        self._writers = {}
        self.flush_seconds = 0.0
        self.bytes_written = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        writers, self._writers = self._writers, {}
        try:
            for writer in writers.values():
                writer.close()
        finally:
            for writer in writers.values():
                if not writer.closed:
                    writer.close()

    def register(self, labels):
        for label in labels:
            self.labels.setdefault(label, len(self.labels))

    def append(self, label, entry):
        self.register([label])
        self.pending[label].append(entry)
        self.size += 1
        if self.size >= self.batch_rows:
            self.flush()

    def flush(self):
        if not self.size:
            return
        import polars as pl

        started = time.perf_counter()
        try:
            columns = entries_to_columns(self.pending)
            # RESP_MSG is already projected into numeric RPC columns; don't persist it.
            columns.pop('_resp_msg', None)
            ranks = []
            for label, entries in self.pending.items():
                ranks.extend([self.labels[label]] * len(entries))
            columns['_scan_group'] = [self.group_id] * self.size
            columns['_scan_label'] = ranks
            self.counts.update(columns['_label'])
            frame = pl.DataFrame(columns, schema=scan_schema(), strict=False)
            frame = frame.with_columns((pl.col('tid').hash(seed=0) % PARTITIONS).alias('_partition'))
            for (partition,), part in frame.partition_by('_partition', as_dict=True).items():
                partition = int(partition)
                writer = self._writers.get(partition)
                if writer is None:
                    path = self.directory / f'{self.group_id}-{partition}.ipcseq'
                    writer = path.open('wb')
                    self._writers[partition] = writer
                    self.paths[partition].append(str(path))
                # Length-prefixed IPC batches, appended to one file per partition.
                # Each payload stays bounded by the existing entry batch size.
                payload = part.drop('_partition').write_ipc(None, compression='lz4').getvalue()
                writer.write(_FRAME_LENGTH.pack(len(payload)))
                writer.write(payload)
                self.bytes_written += _FRAME_LENGTH.size + len(payload)
            self.sequence += 1
            self.pending.clear()
            self.size = 0
        except Exception as exc:
            raise SpillError('Failed to write scan batch') from exc
        finally:
            self.flush_seconds += time.perf_counter() - started

    def finish(self):
        try:
            self.flush()
        finally:
            self.close()
        logger.info(
            '[perf][spill.write] group=%d batches=%d files=%d bytes=%d project_partition_write_s=%.3f',
            self.group_id, self.sequence, len(self.paths), self.bytes_written, self.flush_seconds,
        )
        return {'spill_paths': dict(self.paths), 'entry_counts': dict(self.counts)}


def _read_partition_batches(path):
    import polars as pl

    with open(path, 'rb') as source:
        remaining = os.fstat(source.fileno()).st_size
        while True:
            header = source.read(_FRAME_LENGTH.size)
            if not header:
                return
            if len(header) != _FRAME_LENGTH.size:
                raise SpillError(f'Truncated spool header: {path}')
            remaining -= _FRAME_LENGTH.size
            size = _FRAME_LENGTH.unpack(header)[0]
            if not size or size > remaining:
                raise SpillError(f'Truncated spool batch: {path}')
            payload = source.read(size)
            remaining -= size
            if not size or len(payload) != size:
                raise SpillError(f'Truncated spool batch: {path}')
            yield pl.read_ipc(BytesIO(payload), memory_map=False)


def build_spilled_traces(results):
    import polars as pl
    from .trace_frame import build_trace_frame

    counts = Counter()
    partitions = defaultdict(list)
    for result in results:
        counts.update(result['entry_counts'])
        for partition, paths in result['spill_paths'].items():
            partitions[partition].extend(paths)
    traces = []
    read_s = sort_s = aggregate_s = 0.0
    for paths in partitions.values():
        started = time.perf_counter()
        frame = pl.concat(
            [batch for path in paths for batch in _read_partition_batches(path)], rechunk=False
        )
        read_s += time.perf_counter() - started
        # Append streams already preserve entry order within each group/label.
        # Reorder whole blocks instead of sorting every log row by three columns.
        started = time.perf_counter()
        blocks = frame.partition_by(['_scan_group', '_scan_label'], as_dict=True)
        frame = pl.concat([blocks[key] for key in sorted(blocks)], rechunk=False)
        del blocks
        sort_s += time.perf_counter() - started
        started = time.perf_counter()
        traces.append(build_trace_frame(frame))
        aggregate_s += time.perf_counter() - started
        del frame
    logger.info('[perf][spill.merge] partitions=%d read_s=%.3f order_s=%.3f aggregate_s=%.3f',
                len(partitions), read_s, sort_s, aggregate_s)
    if not traces:
        traces.append(build_trace_frame(pl.DataFrame(schema=scan_schema())))
    return {'trace_frame': pl.concat(traces, rechunk=False), 'entry_counts': dict(counts)}
