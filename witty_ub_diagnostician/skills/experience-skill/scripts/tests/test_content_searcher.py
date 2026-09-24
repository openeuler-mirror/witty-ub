"""ContentSearcher 正文搜索测试（rg 后端通过 mock 覆盖，Python 后端真实执行）。"""

import subprocess
from pathlib import Path

from experience_skill_cli.manager.content_searcher import ContentSearcher
from experience_skill_cli.schema.enum import ExperienceType


def test_rg_available_detection():
    # 真实检测一次（rg 存在与否均可）
    assert isinstance(ContentSearcher._rg_available(), bool)


def test_rg_available_failure_paths(monkeypatch):
    def raise_fnf(*a, **kw):
        raise FileNotFoundError

    def raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired("rg", 5)

    monkeypatch.setattr("subprocess.run", raise_fnf)
    assert ContentSearcher._rg_available() is False
    monkeypatch.setattr("subprocess.run", raise_timeout)
    assert ContentSearcher._rg_available() is False


def test_strip_front_matter():
    text = "---\nname: x\n---\nbody line"
    assert ContentSearcher._strip_front_matter(text) == "body line"
    assert ContentSearcher._strip_front_matter("no front matter") == "no front matter"
    # 正文中出现的 --- 不受影响
    assert "mid ---" in ContentSearcher._strip_front_matter("---\na\n---\nmid ---")


def test_resolve_md_file(tmp_skill_root):
    skill_dir = tmp_skill_root / "data/skill_hub/my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill_def.md").write_text("x", encoding="utf-8")
    wiki = tmp_skill_root / "data/wiki_hub/my.md"
    wiki.write_text("x", encoding="utf-8")

    p = ContentSearcher.resolve_md_file("data/skill_hub/my-skill", ExperienceType.SKILL)
    assert p == skill_dir / "skill_def.md"
    assert ContentSearcher.resolve_md_file("data/skill_hub/missing", ExperienceType.SKILL) is None
    p = ContentSearcher.resolve_md_file("data/wiki_hub/my.md", ExperienceType.WIKI)
    assert p == wiki


def test_get_all_sources(db):
    from experience_skill_cli.manager.keyword_manager import KeyWordManager  # noqa: F401

    now = "2026-01-01 00:00:00"
    db.run(
        "INSERT INTO experience_table (id, type, name, status, is_hot, source, created_at, updated_at) "
        "VALUES ('a', 'skill', 'n', 'existed', 0, 's1', ?, ?)",
        (now, now),
    )
    db.run(
        "INSERT INTO experience_table (id, type, name, status, is_hot, source, created_at, updated_at) "
        "VALUES ('b', 'wiki', 'n', 'existed', 0, 'w1', ?, ?)",
        (now, now),
    )
    assert ContentSearcher.get_all_sources(ExperienceType.SKILL) == ["s1"]
    assert ContentSearcher.get_all_sources(ExperienceType.WIKI) == ["w1"]


def test_search_with_python_backend(tmp_skill_root):
    wiki_dir = tmp_skill_root / "data/wiki_hub"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "a.md").write_text(
        "---\nname: a\n---\nalpha beta line\nplain line\nalpha again\n",
        encoding="utf-8",
    )
    (wiki_dir / "b.md").write_text("beta only here\n", encoding="utf-8")
    (wiki_dir / "c.md").write_text("nothing relevant\n", encoding="utf-8")

    monkey_targets = [wiki_dir / "a.md", wiki_dir / "b.md", wiki_dir / "c.md"]
    raw = ContentSearcher._search_with_python("alpha", monkey_targets)
    assert str(wiki_dir / "a.md") in raw
    assert len(raw[str(wiki_dir / "a.md")]) == 2

    # 不可读文件被跳过
    raw = ContentSearcher._search_with_python("alpha", [tmp_skill_root / "missing.md"])
    assert raw == {}


def test_search_with_rg_backend(tmp_skill_root, monkeypatch):
    wiki_dir = tmp_skill_root / "data/wiki_hub"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    target = wiki_dir / "a.md"

    class FakeResult:
        returncode = 0
        stdout = (
            '{"type":"match","data":{"path":{"text":"'
            + str(target)
            + '"},"lines":{"text":"alpha line"},"line_number":1,'
            '"submatches":[{"start":0,"end":5}]}}\n'
            "not-json\n"
            '\n{"type":"other"}\n'
        )
        stderr = ""

    monkeypatch.setattr(
        ContentSearcher, "_rg_available", staticmethod(lambda: False)
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())

    raw = ContentSearcher._search_with_rg("alpha", [target])
    expected_data = {
        "path": {"text": str(target)},
        "lines": {"text": "alpha line"},
        "line_number": 1,
        "submatches": [{"start": 0, "end": 5}],
    }
    assert raw == {str(target): [expected_data]}

    # 超时与异常路径
    def raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired("rg", 30)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    assert ContentSearcher._search_with_rg("alpha", [target]) == {}

    def raise_exc(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", raise_exc)
    assert ContentSearcher._search_with_rg("alpha", [target]) == {}


def test_search_end_to_end_python_backend(tmp_skill_root, monkeypatch):
    wiki_dir = tmp_skill_root / "data/wiki_hub"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "a.md").write_text("alpha beta\nbeta\n", encoding="utf-8")
    (wiki_dir / "b.md").write_text("beta\n", encoding="utf-8")
    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))

    # 空查询 / 空来源
    assert ContentSearcher.search("", ["data/wiki_hub/a.md"], ExperienceType.WIKI) == []
    assert ContentSearcher.search("alpha", [], ExperienceType.WIKI) == []
    # 来源不存在
    assert ContentSearcher.search("alpha", ["data/wiki_hub/none.md"], ExperienceType.WIKI) == []

    results = ContentSearcher.search(
        "alpha beta", ["data/wiki_hub/a.md", "data/wiki_hub/b.md"], ExperienceType.WIKI
    )
    assert len(results) == 2
    assert results[0].source.endswith("a.md")
    assert results[0].score == 1.0
    assert results[0].hit_count == 3
    assert results[1].score < 1.0
    assert all(s.line_num >= 1 for r in results for s in r.snippets)


def test_search_snippet_limit(tmp_skill_root, monkeypatch):
    wiki_dir = tmp_skill_root / "data/wiki_hub"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "many.md").write_text("alpha\n" * 10, encoding="utf-8")
    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))

    results = ContentSearcher.search("alpha", ["data/wiki_hub/many.md"], ExperienceType.WIKI)
    assert results[0].hit_count == 10
    assert len(results[0].snippets) == ContentSearcher._MAX_SNIPPETS


def test_search_all(db, tmp_skill_root, monkeypatch):
    wiki_dir = tmp_skill_root / "data/wiki_hub"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "a.md").write_text("uniqueword\n", encoding="utf-8")
    now = "2026-01-01 00:00:00"
    db.run(
        "INSERT INTO experience_table (id, type, name, status, is_hot, source, created_at, updated_at) "
        "VALUES ('a', 'wiki', 'n', 'existed', 0, 'data/wiki_hub/a.md', ?, ?)",
        (now, now),
    )
    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))

    results = ContentSearcher.search_all("uniqueword", ExperienceType.WIKI)
    assert len(results) == 1
    assert results[0].source == "data/wiki_hub/a.md"
