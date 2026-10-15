"""sqlite.py 单例与数据库管理测试。"""

import sqlite3
from pathlib import Path

import pytest

import experience_skill_cli.sqlite as sqlite_mod
from experience_skill_cli.sqlite import AsyncSQLiteSingleton, _check_tokenizer


def test_singleton_identity(db):
    a = AsyncSQLiteSingleton()
    b = AsyncSQLiteSingleton()
    assert a is b
    assert a is db


def test_init_creates_tables(db):
    rows = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r["name"] for r in rows}
    assert "keyword_table" in names
    assert "experience_table" in names
    triggers = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert triggers == {"fts_insert", "fts_update", "fts_delete"}


def test_run_success_and_failure(db):
    assert db.run("INSERT INTO experience_table (id, type, name, status, created_at, updated_at) VALUES ('x', 'skill', 'n', 'existed', 't', 't')")
    assert db.run("INVALID SQL") is False
    rows = db.query("SELECT id FROM experience_table")
    assert rows == [{"id": "x"}]
    # query 异常返回空列表
    assert db.query("INVALID SQL") == []


def test_query_row_factory(db):
    db.run("INSERT INTO experience_table (id, type, name, status, created_at, updated_at) VALUES ('x', 'skill', 'n', 'existed', 't', 't')")
    row = db.query("SELECT id, name FROM experience_table")[0]
    assert isinstance(row, dict)
    assert row["name"] == "n"


def test_clear_database(db, tmp_path):
    db.run("INSERT INTO experience_table (id, type, name, status, created_at, updated_at) VALUES ('x', 'skill', 'n', 'existed', 't', 't')")
    db.clear_database()
    assert not Path(db.db_path).exists()
    assert db._conn is None
    # clear 后需重新 init 建表，再写入
    db.init()
    db.run("INSERT INTO experience_table (id, type, name, status, created_at, updated_at) VALUES ('y', 'skill', 'n', 'existed', 't', 't')")
    assert db.query("SELECT id FROM experience_table") == [{"id": "y"}]


def test_ensure_column_adds_when_missing(tmp_skill_root, monkeypatch):
    # 直接在内存库上验证 _ensure_column 的迁移逻辑
    monkeypatch.setattr(sqlite_mod, "DATA_DIR", tmp_skill_root)
    AsyncSQLiteSingleton._instance = None
    inst = AsyncSQLiteSingleton()
    inst._conn.close()
    inst._conn = sqlite3.connect(":memory:", check_same_thread=False)
    inst._ext_path = "loaded"
    try:
        inst.run("CREATE TABLE t (a TEXT)")
        cols = [r[1] for r in inst._conn.execute("PRAGMA table_info(t)").fetchall()]
        assert "b" not in cols
        inst._ensure_column("t", "b", "TEXT")
        cols = [r[1] for r in inst._conn.execute("PRAGMA table_info(t)").fetchall()]
        assert "b" in cols
        # 已存在时不再添加
        inst._ensure_column("t", "b", "TEXT")
    finally:
        inst._conn.close()
        AsyncSQLiteSingleton._instance = None


def test_check_tokenizer_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sqlite_mod, "LIBSIMPLE_PATH", tmp_path / "nonexistent")
    with pytest.raises(RuntimeError, match="Tokenizer"):
        _check_tokenizer()


def test_check_tokenizer_found(monkeypatch, tmp_path):
    fake = tmp_path / "libsimple.so"
    fake.write_text("")
    monkeypatch.setattr(sqlite_mod, "LIBSIMPLE_PATH", tmp_path / "libsimple")
    assert _check_tokenizer() == str(tmp_path / "libsimple")


def test_init_twice_idempotent(db):
    db.init()
    db.init()
    assert db.query("SELECT COUNT(*) AS c FROM experience_table")[0]["c"] == 0
