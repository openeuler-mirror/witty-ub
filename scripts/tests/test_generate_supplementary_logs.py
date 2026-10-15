"""generate_supplementary_logs.py 测试。"""

import os

import pytest

import generate_supplementary_logs as gen


VALID_LINE = (
    "2026-05-06T13:25:28.429016 | I | access_recorder.cpp:220 | pod-10.0.0.1 | 11:291 | "
    "trace-0001 | cluster-1 | 0 | DS_KV_CLIENT_GET | 2410 | 8388608 | {k:v} | "
)


def test_parse_sdk_line_valid():
    entry = gen.parse_sdk_line(VALID_LINE)
    assert entry is not None
    assert entry["timestamp"] == "2026-05-06T13:25:28.429016"
    assert entry["pod_ip"] == "pod-10.0.0.1"
    assert entry["trace_id"] == "trace-0001"
    assert entry["operation"] == "DS_KV_CLIENT_GET"
    assert entry["latency_us"] == 2410
    assert entry["metadata"] == "{k:v}"
    assert entry["error_msg"] == ""


def test_parse_sdk_line_invalid():
    assert gen.parse_sdk_line("only a few | parts\n") is None
    assert gen.parse_sdk_line("a | b | c | d | e | f | g | h | i | notint | j\n") is None
    assert gen.parse_sdk_line("") is None


def test_generate_worker_access():
    entry = gen.parse_sdk_line(VALID_LINE)
    line = gen.generate_worker_access(entry)
    assert "DS_POSIX_GET" in line
    parts = line.split(" | ")
    assert int(parts[9]) >= 50  # latency 被压缩但有下限

    # SET 操作映射为 PUBLISH；未知操作回退 GET
    set_line = VALID_LINE.replace("DS_KV_CLIENT_GET", "DS_KV_CLIENT_SET")
    assert "DS_POSIX_PUBLISH" in gen.generate_worker_access(gen.parse_sdk_line(set_line))
    other_line = VALID_LINE.replace("DS_KV_CLIENT_GET", "DS_KV_CLIENT_DELETE")
    assert "DS_POSIX_GET" in gen.generate_worker_access(gen.parse_sdk_line(other_line))

    # 极小 latency 的钳制
    tiny = gen.parse_sdk_line(VALID_LINE.replace("2410", "1"))
    assert int(gen.generate_worker_access(tiny).split(" | ")[9]) >= 50


def test_generate_faulty_worker_access_tiers():
    entry = gen.parse_sdk_line(VALID_LINE)

    def latency_for(fault):
        return int(gen.generate_faulty_worker_access(entry, fault).split(" | ")[9])

    assert 5000 <= latency_for("RPC_RECV_TIMEOUT") <= 15000
    assert 5000 <= latency_for("SOCK_WAIT_TIMEOUT") <= 15000
    assert 5000 <= latency_for("LINK_RESET") <= 15000
    assert 3000 <= latency_for("TCP_CONNECT_RESET") <= 10000
    assert 3000 <= latency_for("ETCD_UNAVAILABLE") <= 10000
    assert 1500 <= latency_for("MMAP_FAILED") <= 5000
    # 结尾少一列（无 error_msg）
    assert gen.generate_faulty_worker_access(entry, "ETCD_TIMEOUT").endswith(" | ")


def test_generate_info_line():
    entry = gen.parse_sdk_line(VALID_LINE)
    line = gen.generate_info_line(entry, "some fault msg")
    assert "some fault msg" in line
    assert "worker_impl.cpp:100" in line
    # 微秒被增加
    ts = line.split(" | ")[0]
    assert int(ts.split(".")[1]) > 429016

    # 无小数的时间戳分支 + 自定义 source_file
    no_frac = VALID_LINE.replace("2026-05-06T13:25:28.429016", "2026-05-06T13:25:28")
    line = gen.generate_info_line(gen.parse_sdk_line(no_frac), "msg", "custom.cpp:1")
    assert line.startswith("2026-05-06T13:25:28 | ")
    assert "custom.cpp:1" in line


def _make_input(path, n_traces=60, lines_per_trace=2):
    with open(path, "w") as f:
        for i in range(n_traces):
            for j in range(lines_per_trace):
                f.write(
                    f"2026-05-06T13:25:28.{i:06d} | I | access_recorder.cpp:220 | pod-10.0.0.1 | "
                    f"11:29{j} | trace-{i:04d} | cluster-1 | 0 | DS_KV_CLIENT_GET | 2410 | "
                    f"1024 | {{k:v}} | \n"
                )
    return path


def test_main_full_run(tmp_path, monkeypatch, capsys):
    input_file = _make_input(tmp_path / "ds_client_access_3941.log")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "gen",
            str(input_file),
            "--worker-ratio",
            "0.9",
            "--fault-ratio",
            "0.2",
            "--output-dir",
            str(out_dir),
            "--seed",
            "7",
        ],
    )
    gen.main()
    out = capsys.readouterr().out
    assert "Reading:" in out
    assert "Generated files in" in out

    access = out_dir / "access.log"
    worker_info = out_dir / "datasystem_worker.INFO.log"
    client_info = out_dir / "ds_client_10411.INFO.log"
    expected = out_dir / "expected_result.txt"
    for p in (access, worker_info, client_info, expected):
        assert p.exists(), p

    access_lines = access.read_text().strip().splitlines()
    # worker-ratio 0.9 → n_worker = max(50, int(60*0.9)) = 54，每 trace 2 条 entry
    assert len(access_lines) == 54 * 2
    exp_text = expected.read_text()
    assert "input: ds_client_access_3941.log" in exp_text
    assert "expected_anomalous_events: >=" in exp_text

    # 断言 worker/fault trace 计数与输出一致
    assert f"worker_traces: 54" in exp_text
    n_fault = max(10, int(54 * 0.2))
    assert f"fault_traces: {n_fault}" in exp_text
    assert len(worker_info.read_text().strip().splitlines()) == n_fault


def test_main_default_output_dir(tmp_path, monkeypatch):
    input_file = _make_input(tmp_path / "ds_client_access_1.log", n_traces=55)
    monkeypatch.setattr("sys.argv", ["gen", str(input_file), "--seed", "3"])
    gen.main()
    assert (tmp_path / "access.log").exists()
    assert (tmp_path / "datasystem_worker.INFO.log").exists()
    assert (tmp_path / "ds_client_10411.INFO.log").exists()
    assert (tmp_path / "expected_result.txt").exists()
    assert os.path.isabs(str(input_file))
