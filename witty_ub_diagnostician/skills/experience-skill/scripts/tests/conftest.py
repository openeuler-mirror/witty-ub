"""experience-skill CLI 测试公共夹具：将 SKILL_ROOT / 数据库重定向到 tmp_path。"""

from pathlib import Path

import pytest


def _reset_singleton() -> None:
    """关闭并销毁当前 SQLite 单例，避免测试间互相污染。"""
    from experience_skill_cli.sqlite import AsyncSQLiteSingleton

    inst = AsyncSQLiteSingleton._instance
    if inst is not None and getattr(inst, "_conn", None) is not None:
        inst._conn.close()
    AsyncSQLiteSingleton._instance = None


@pytest.fixture()
def tmp_skill_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把所有依赖 SKILL_ROOT 的模块级常量重定向到 tmp_path。"""
    import experience_skill_cli.cli as cli_mod
    import experience_skill_cli.manager.content_searcher as cs_mod
    import experience_skill_cli.service.experience_service as svc_mod
    import experience_skill_cli.sqlite as sqlite_mod
    import experience_skill_cli.web_server as ws_mod

    (tmp_path / "data" / "skill_hub").mkdir(parents=True)
    (tmp_path / "data" / "wiki_hub").mkdir(parents=True)

    monkeypatch.setattr(svc_mod, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(cs_mod, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(ws_mod, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(cli_mod, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sqlite_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cli_mod, "DATA_SKILL_DIR", tmp_path / "data" / "skill_hub")
    monkeypatch.setattr(cli_mod, "DATA_WIKI_DIR", tmp_path / "data" / "wiki_hub")
    _reset_singleton()
    yield tmp_path
    _reset_singleton()


@pytest.fixture()
def db(tmp_skill_root: Path):
    """每个测试一个全新的 SQLite 单例（临时库），结束后销毁单例。"""
    from experience_skill_cli.sqlite import AsyncSQLiteSingleton

    instance = AsyncSQLiteSingleton()
    instance.init()
    yield instance


@pytest.fixture()
def make_experience():
    """构造 Experience 对象的工厂。"""

    def _make(**overrides):
        from experience_skill_cli.schema.exprience import Experience

        defaults = {
            "name": "exp",
            "description": "kvcache alpha beta",
            "keywords": ["alpha"],
            "source": "data/wiki_hub/exp.md",
        }
        defaults.update(overrides)
        return Experience(**defaults)

    return _make
