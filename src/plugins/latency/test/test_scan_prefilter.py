import io

from latency.parse.parallel_scanner.process_worker import _prefilter_lines, _parse_lines
from test_scan_merge import _mk_parsers, _SDK_LINE, _MIXED_LINE, _WORKER_LINE, _SRC_DST_LINE, _URMA_LINE


def test_bounded_prefilter_keeps_all_matching_and_fallback_lines(tmp_path):
    lines = ['2026 unrelated noise\n'] * 600 + [
        _SDK_LINE + '\n', _MIXED_LINE + '\n', _WORKER_LINE + '\n',
        _SRC_DST_LINE + '\n', _URMA_LINE + '\n',
    ]
    class Source(io.StringIO):
        def readlines(self, hint=-1):
            assert 0 < hint <= 1024 * 1024
            return super().readlines(hint)
    filtered = list(_prefilter_lines(list(_mk_parsers()), Source(''.join(lines))))
    assert filtered == lines[-5:]
    original = _parse_lines(list(_mk_parsers()), str(tmp_path / 'log'), lines)
    actual = _parse_lines(list(_mk_parsers()), str(tmp_path / 'log'), filtered)
    def signatures(parsed):
        return {label: [(e.trace_id, e.entry_type, e.elapsed_us) for e in entries] for label, entries in parsed.items()}
    assert signatures(actual) == signatures(original)


def test_dense_files_use_direct_iteration_after_first_chunk(monkeypatch):
    from latency.parse.parallel_scanner import process_worker
    monkeypatch.setattr(process_worker, '_PREFILTER_BYTES', len(_SDK_LINE) * 300)
    class Source(io.StringIO):
        calls = 0
        def readlines(self, hint=-1):
            self.calls += 1
            return super().readlines(hint)
    lines = [_SDK_LINE + '\n'] * 1500
    source = Source(''.join(lines))
    assert list(_prefilter_lines([_mk_parsers()[0]], source)) == lines
    assert source.calls == 1
