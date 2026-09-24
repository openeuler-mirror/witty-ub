"""para_cnt.py 测试。"""

import gzip
import json
import sys
from pathlib import Path

import polars as pl
import pytest

import para_cnt


def _log_line(ts, pod, op, code="0"):
    return (
        f"{ts} | I | urma_manager.cpp:347 | {pod} | 5678:872 | trace-id | cluster-2 | "
        f"{code} | {op} | 2410 | 8388608 | message\n"
    )


@pytest.fixture()
def log_dir(tmp_path: Path):
    d = tmp_path / "logs"
    d.mkdir()
    return d


def test_find_log_files(log_dir):
    (log_dir / "a").mkdir()
    (log_dir / "a" / "ds_client_access_1.log").write_text("", encoding="utf-8")
    (log_dir / "a" / "b").mkdir()
    (log_dir / "a" / "b" / "ds_client_access_2.log.gz").write_bytes(b"")
    (log_dir / "a" / "b" / "ds_client_access_3.log").write_text("", encoding="utf-8")
    (log_dir / "other.log").write_text("", encoding="utf-8")
    (log_dir / "readme.txt").write_text("", encoding="utf-8")

    files = para_cnt.find_log_files(str(log_dir))
    # 递归查找 .log 与 .log.gz，排除无关文件
    assert sorted(f.name for f in files) == [
        "ds_client_access_1.log",
        "ds_client_access_2.log.gz",
        "ds_client_access_3.log",
    ]
    # 返回值按完整路径排序（a/b/... 排在 a/ds_... 之前）
    assert files == sorted(files)

    assert para_cnt.find_log_files(str(log_dir / "missing")) == []


def test_process_file(log_dir):
    f = log_dir / "ds_client_access_x.log"
    f.write_text(
        _log_line("2026-04-12T09:00:00.123456", "pod-a", "DS_KV_CLIENT_GET")
        + _log_line("2026-04-12T09:00:00.654321", "pod-a", "DS_KV_CLIENT_GET")
        + _log_line("2026-04-12T09:00:00.123456", "pod-b", "DS_KV_CLIENT_SET")
        # 非法/无关行
        + "not-a-log-line\n"
        + _log_line("bad-ts", "pod-a", "DS_KV_CLIENT_GET")
        + _log_line("2026-04-12T09:00:01.000000", "pod-a", "DS_KV_CLIENT_DELETE")
        + _log_line("2026-04-12T09:00:02.000000", "", "DS_KV_CLIENT_GET"),
        encoding="utf-8",
    )
    df = para_cnt._process_file(f)
    assert df.height == 3
    rows = {(r["ts_ms"], r["pod"]): (r["read"], r["write"]) for r in df.iter_rows(named=True)}
    assert set(rows) == {
        (1775984400123, "pod-a"),
        (1775984400654, "pod-a"),
        (1775984400123, "pod-b"),
    }
    assert rows[(1775984400123, "pod-a")] == (1, 0)
    assert rows[(1775984400123, "pod-b")] == (0, 1)


def test_process_file_gz(log_dir):
    """polars scan_csv 会自动解压 .gz，内容照常解析。"""
    p = log_dir / "ds_client_access_g.log.gz"
    with gzip.open(p, "wb") as gz:
        gz.write(_log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_GET").encode())
    df = para_cnt._process_file(p)
    assert df.height == 1
    row = df.to_dicts()[0]
    assert row["ts_ms"] == 1775984400000
    assert row["pod"] == "pod-a"
    assert row["read"] == 1
    assert row["write"] == 0


def test_parse_and_aggregate(log_dir, capsys):
    f1 = log_dir / "ds_client_access_1.log"
    f1.write_text(
        _log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_GET"),
        encoding="utf-8",
    )
    f2 = log_dir / "ds_client_access_2.log"
    f2.write_text(
        _log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_SET")
        + _log_line("2026-04-12T09:00:01.000000", "pod-b", "DS_KV_CLIENT_GET"),
        encoding="utf-8",
    )
    # 二进制垃圾行不报错（utf8-lossy + 行过滤直接丢弃）；缺失文件触发警告分支
    (log_dir / "corrupt.log").write_bytes(b"\x00\x01binary garbage\x02")

    df = para_cnt.parse_and_aggregate([f1, f2, log_dir / "corrupt.log", log_dir / "missing.log"])
    out = capsys.readouterr()
    assert "已处理: ds_client_access_1.log" in out.out
    assert "跳过文件" in out.err
    assert "missing.log" in out.err

    assert df.height == 2
    row_a = df.filter(pl.col("pod") == "pod-a").to_dicts()[0]
    assert row_a["read"] == 1
    assert row_a["write"] == 1


def test_parse_and_aggregate_all_invalid(log_dir, capsys):
    (log_dir / "empty.log").write_text("", encoding="utf-8")
    df = para_cnt.parse_and_aggregate([log_dir / "empty.log"])
    assert df.is_empty()
    assert df.columns == ["ts_ms", "pod", "read", "write"]
    assert "警告" in capsys.readouterr().err


def test_build_output_data_empty():
    empty = pl.DataFrame(schema={"ts_ms": pl.Int64, "pod": pl.Utf8, "read": pl.Int32, "write": pl.Int32})
    data = para_cnt.build_output_data(empty)
    assert data == {"minTs": 0, "maxTs": 0, "pods": [], "records": []}


def test_build_output_data():
    df = pl.DataFrame(
        {
            "ts_ms": [100, 100, 200],
            "pod": ["pod-b", "pod-a", "pod-a"],
            "read": [1, 2, 3],
            "write": [0, 1, 0],
        },
        schema={"ts_ms": pl.Int64, "pod": pl.Utf8, "read": pl.Int32, "write": pl.Int32},
    ).sort(["ts_ms", "pod"])
    data = para_cnt.build_output_data(df)
    assert data["pods"] == ["pod-a", "pod-b"]
    assert data["minTs"] == 100
    assert data["maxTs"] == 200
    assert data["records"][0] == [100, 0, 2, 1]  # (100, pod-a)
    assert data["records"][1] == [100, 1, 1, 0]  # (100, pod-b)


def test_generate_html():
    html = para_cnt.generate_html({"pods": ["a<b"], "records": []})
    assert "RAW_DATA" in html
    assert "__DATA_PLACEHOLDER__" not in html
    # < 被转义
    assert "\\u003c" in html


def test_main_happy_path(log_dir, tmp_path, monkeypatch, capsys):
    (log_dir / "sub").mkdir()
    (log_dir / "sub" / "ds_client_access_1.log").write_text(
        _log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_GET")
        + _log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_SET"),
        encoding="utf-8",
    )
    out_html = tmp_path / "report.html"
    monkeypatch.setattr(
        sys, "argv", ["para_cnt.py", str(log_dir), "--output", str(out_html)]
    )
    para_cnt.main()
    out = capsys.readouterr().out
    assert "找到 1 个日志文件" in out
    assert "聚合完成: 1 个 (毫秒, pod) 组合, 共 2 条请求" in out
    content = out_html.read_text(encoding="utf-8")
    assert "__DATA_PLACEHOLDER__" not in content
    raw = content.split("const RAW_DATA = ")[1].split(";\n(function")[0]
    assert json.loads(raw)["records"] == [[1775984400000, 0, 1, 1]]


def test_main_no_files(log_dir, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["para_cnt.py", str(log_dir), "-o", str(tmp_path / "x.html")])
    with pytest.raises(SystemExit) as exc:
        para_cnt.main()
    assert exc.value.code == 1
    assert "未找到" in capsys.readouterr().err


def test_main_no_valid_records(log_dir, tmp_path, monkeypatch, capsys):
    (log_dir / "ds_client_access_empty.log").write_text(
        _log_line("2026-04-12T09:00:00.000000", "pod-a", "DS_KV_CLIENT_DELETE"),
        encoding="utf-8",
    )
    out_html = tmp_path / "report.html"
    monkeypatch.setattr(sys, "argv", ["para_cnt.py", str(log_dir), "--output", str(out_html)])
    para_cnt.main()
    captured = capsys.readouterr()
    assert "未解析到有效的 GET/SET" in captured.err
    assert out_html.exists()
