"""generate_kvcache_conn_logs.py 测试。"""

import json
import os
import subprocess

import pytest

import generate_kvcache_conn_logs as gen


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """把 PROJECT_ROOT / DATA_DIR / FAULT_LOG_DIR 重定向到 tmp_path。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(gen, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(gen, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(
        gen, "FAULT_LOG_DIR", str(data_dir / "kvcache_conn_fault_log")
    )
    realization_dir = tmp_path / "src/diagnosis_tool/failure_mode_realization"
    realization_dir.mkdir(parents=True)
    return tmp_path


def _add_cpp(realization_dir, fault_id, cmd=None):
    cmd = cmd or 'R"(etcdctl endpoint status -w table)"'
    p = realization_dir / f"{fault_id}.cpp"
    p.write_text(
        f"// stub\nvoid f() {{\n  auto cmd = {cmd};\n  (void)cmd;\n}}\n",
        encoding="utf-8",
    )
    return p


# ---------------- extract_commands_from_cpp ----------------


def test_extract_commands_from_cpp(tmp_env):
    realization = tmp_env / "src/diagnosis_tool/failure_mode_realization"
    _add_cpp(realization, "kvcache_conn_fault_001", 'R"(etcdctl endpoint status)"')
    p = realization / "kvcache_conn_fault_002.cpp"
    # 同一命令出现两次 → 去重；两条不同命令均被提取
    p.write_text(
        'auto a = R"(grep etcd $LOG/a.log)";\n'
        'auto b = R"(grep etcd $LOG/a.log)";\n'
        'auto c = R"(ss -tnlp | grep 31402)";\n',
        encoding="utf-8",
    )
    # 非 kvcache_conn_fault_ 前缀文件被忽略
    (realization / "other.cpp").write_text('auto d = R"(cat x)";', encoding="utf-8")

    cmd_map = gen.extract_commands_from_cpp()
    assert cmd_map["kvcache_conn_fault_001"] == ["etcdctl endpoint status"]
    assert cmd_map["kvcache_conn_fault_002"] == ["grep etcd $LOG/a.log", "ss -tnlp | grep 31402"]
    assert "other" not in cmd_map


def test_extract_base_commands():
    assert gen.extract_base_commands("grep x | awk -F'|' '{print $1}' | mystery z") == ["grep", "awk"]
    assert gen.extract_base_commands("   ") == []
    assert gen.extract_base_commands("cat /proc/meminfo") == ["cat"]
    assert gen.extract_base_commands("unknownbin -x") == []


# ---------------- check_commands ----------------


def test_check_commands_with_installed_cmds(tmp_env):
    # cat/grep 已安装：cat 对不存在文件返回 1 → 不计错误
    cmd_map = {"kvcache_conn_fault_001": ["cat /tmp/nonexistent_log_dir/x.log | grep y"]}
    ignore_cmds, error_cmds = gen.check_commands(cmd_map)
    assert error_cmds == []
    assert ignore_cmds == []


def test_check_commands_missing_binary(tmp_env, monkeypatch):
    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    ignore_cmds, error_cmds = gen.check_commands(
        {"f": ["etcdctl endpoint status"]}
    )
    assert ignore_cmds == [("etcdctl", "f", "etcdctl endpoint status")]
    assert error_cmds == []


def test_check_commands_error_paths(tmp_env, monkeypatch):
    calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls["n"] += 1
        if cmd[0] == "which":
            # which 返回 0 → 视为已安装
            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()
        # bash -c 执行返回码 2 → 记录错误
        class R2:
            returncode = 2
            stdout = ""
            stderr = "boom"

        return R2()

    monkeypatch.setattr(subprocess, "run", fake_run)
    ignore_cmds, error_cmds = gen.check_commands({"f": ["ssh root@localhost 'x'"]})
    assert ignore_cmds == []
    assert len(error_cmds) == 1
    assert error_cmds[0][0] == "ssh"
    assert error_cmds[0][3] == "boom"


def test_check_commands_exceptions_and_timeout(tmp_env, monkeypatch):
    # which 阶段抛异常 → ignore
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: (_ for _ in ()).throw(OSError("gone"))
    )
    ignore_cmds, error_cmds = gen.check_commands({"f": ["free -m"]})
    assert ignore_cmds[0][0] == "free"

    # which 成功但执行超时 → error
    state = {"phase": 0}

    def fake_run(cmd, **kw):
        if cmd[0] == "which":
            state["phase"] = 1

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()
        raise subprocess.TimeoutExpired("bash", 5)

    monkeypatch.setattr(subprocess, "run", fake_run)
    _, error_cmds = gen.check_commands({"f": ["free -m"]})
    assert error_cmds[0][3] == "timeout after 5s"

    # 执行阶段抛通用异常 → error
    def fake_run2(cmd, **kw):
        if cmd[0] == "which":

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()
        raise RuntimeError("kaput")

    monkeypatch.setattr(subprocess, "run", fake_run2)
    _, error_cmds = gen.check_commands({"f": ["free -m"]})
    assert error_cmds[0][3] == "kaput"


def test_check_commands_dedup(tmp_env):
    # 同一 base_cmd 只检查一次
    cmd_map = {
        "f1": ["cat /tmp/nonexistent_log_dir/a", "cat /tmp/nonexistent_log_dir/b"],
        "f2": ["cat /tmp/nonexistent_log_dir/c"],
    }
    gen.check_commands(cmd_map)  # 不崩溃即可


# ---------------- md 生成 ----------------


def test_generate_ignore_and_error_md(tmp_env):
    gen.generate_ignore_cmd_md([("etcdctl", "f1", "etcdctl endpoint status")], {})
    path = tmp_env / "data" / "ignore-cmd.md"
    content = path.read_text(encoding="utf-8")
    assert "未安装命令清单" in content
    assert "| etcdctl | f1 | `etcdctl endpoint status` |" in content

    gen.generate_error_cmd_md([("ssh", "f2", "ssh x", "boom")], {})
    path = tmp_env / "data" / "error-cmd.md"
    content = path.read_text(encoding="utf-8")
    assert "执行失败命令清单" in content
    assert "| ssh | f2 | `ssh x` | boom |" in content


# ---------------- generate_fault_logs ----------------


def test_generate_fault_logs(tmp_env):
    realization = tmp_env / "src/diagnosis_tool/failure_mode_realization"
    # 003: access + INFO 模板；026: access 模板 + system_cmd；099: 无模板（目录应被删除）
    for fid in ["kvcache_conn_fault_003", "kvcache_conn_fault_026", "kvcache_conn_fault_099"]:
        _add_cpp(realization, fid)

    gen.generate_fault_logs()

    fault_dir = tmp_env / "data" / "kvcache_conn_fault_log"
    d3 = fault_dir / "kvcache_conn_fault_003"
    assert (d3 / "kvcache_conn_fault_003_ds_client_access.log").exists()
    assert (d3 / "kvcache_conn_fault_003_ds_client.INFO.log").exists()
    content = (d3 / "kvcache_conn_fault_003_ds_client_access.log").read_text(encoding="utf-8")
    assert "DS_KV_CLIENT_GET | 49469" in content  # normal 行
    assert "The objectKey is empty" in content  # fault 行

    d26 = fault_dir / "kvcache_conn_fault_026"
    assert (d26 / "kvcache_conn_fault_026_ds_client_access.log").exists()
    sys_log = d26 / "kvcache_conn_fault_026_system_cmd.log"
    assert sys_log.exists()
    assert "# ifconfig_ub0" in sys_log.read_text(encoding="utf-8")

    assert not (fault_dir / "kvcache_conn_fault_099").exists()
    # 不在模板中的 cpp（如 004 INFO）应有 INFO 文件
    _add_cpp(realization, "kvcache_conn_fault_004")
    gen.generate_fault_logs()
    assert (
        fault_dir / "kvcache_conn_fault_004" / "kvcache_conn_fault_004_ds_client.INFO.log"
    ).exists()
    # 资源日志
    _add_cpp(realization, "kvcache_conn_fault_013")
    _add_cpp(realization, "kvcache_conn_fault_032")
    gen.generate_fault_logs()
    assert (
        fault_dir / "kvcache_conn_fault_013" / "kvcache_conn_fault_013_resource.log"
    ).exists()
    assert (
        fault_dir / "kvcache_conn_fault_032" / "kvcache_conn_fault_032_resource.log"
    ).exists()
    # worker INFO
    _add_cpp(realization, "kvcache_conn_fault_009")
    gen.generate_fault_logs()
    assert (
        fault_dir
        / "kvcache_conn_fault_009"
        / "kvcache_conn_fault_009_datasystem_worker.INFO.log"
    ).exists()


# ---------------- aggregate_logs ----------------


def test_aggregate_logs_missing_dir(tmp_env, capsys):
    gen.aggregate_logs()
    assert "skipping aggregation" in capsys.readouterr().out


def test_aggregate_logs(tmp_env):
    fault_dir = tmp_env / "data" / "kvcache_conn_fault_log"
    d1 = fault_dir / "kvcache_conn_fault_001"
    d1.mkdir(parents=True)
    (d1 / "kvcache_conn_fault_001_ds_client_access.log").write_text("access content\n", encoding="utf-8")
    (d1 / "kvcache_conn_fault_001_ds_client.INFO.log").write_text("info content\n", encoding="utf-8")
    (d1 / "unknown.log").write_text("skip me\n", encoding="utf-8")
    (d1 / "subdir").mkdir()
    # 没有任何 datasystem_worker 文件 → 聚合输出应为空

    gen.aggregate_logs()

    data_dir = tmp_env / "data"
    acc = (data_dir / "ds_client_access.log").read_text(encoding="utf-8")
    assert "# === kvcache_conn_fault_001 ===" in acc
    assert "access content" in acc
    inf = (data_dir / "ds_client.INFO.log").read_text(encoding="utf-8")
    assert "info content" in inf
    assert not (data_dir / "datasystem_worker.INFO.log").exists()
    assert not (data_dir / "resource.log").exists()


# ---------------- main ----------------


def test_main(tmp_env, capsys):
    realization = tmp_env / "src/diagnosis_tool/failure_mode_realization"
    _add_cpp(realization, "kvcache_conn_fault_003")

    gen.main()
    out = capsys.readouterr().out
    assert "Step 1" in out
    assert "Step 2" in out
    assert "Step 3" in out
    assert "Step 4" in out
    data_dir = tmp_env / "data"
    assert (data_dir / "ignore-cmd.md").exists()
    assert (data_dir / "error-cmd.md").exists()
    assert (
        data_dir / "kvcache_conn_fault_log" / "kvcache_conn_fault_003"
    ).is_dir()
    assert "Done!" in out
    assert os.path.isdir(data_dir)
