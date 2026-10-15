"""ExperienceService 业务层测试。"""

import pytest

from experience_skill_cli.manager.keyword_manager import KeyWordManager
from experience_skill_cli.schema.enum import ExperienceType
from experience_skill_cli.service.experience_service import ExperienceService


def _write_md(path, front_matter: str, body: str = "body text"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n{body}\n", encoding="utf-8")
    return path


# ---------------- 纯函数 ----------------


def test_filter_special_characters():
    assert ExperienceService.filter_special_characters("hello, world! (test)") == "hello world test"
    assert ExperienceService.filter_special_characters("  中文  保持  ") == "中文 保持"
    assert ExperienceService.filter_special_characters("") == ""


def test_md_to_structured_json_valid():
    data = ExperienceService.md_to_structured_json("---\nname: x\ndescription: y\n---\nbody")
    assert data == {"name": "x", "description": "y"}


def test_md_to_structured_json_invalid_yaml():
    assert ExperienceService.md_to_structured_json("---\n: [bad\n---\n") == {}


def test_md_to_structured_json_no_front_matter():
    assert ExperienceService.md_to_structured_json("plain text") == {}


# ---------------- add_experiences ----------------


def test_add_skill_experience(db, tmp_skill_root):
    _write_md(
        tmp_skill_root / "data/skill_hub/my-skill/skill_def.md",
        "name: my-skill\ndescription: 描述 alpha\nkeywords: [k1, k2]\n",
    )
    exp = ExperienceService.add_experiences(ExperienceType.SKILL, "data/skill_hub/my-skill")
    assert exp.name == "my-skill"
    assert exp.description == "描述 alpha"
    assert exp.keywords == ["k1", "k2"]
    assert KeyWordManager.get_keywords_by_experience_id(exp.id) == ["k1", "k2"]


def test_add_skill_missing_file(db):
    with pytest.raises(FileNotFoundError, match="skill_def.md not found"):
        ExperienceService.add_experiences(ExperienceType.SKILL, "data/skill_hub/none")


def test_add_wiki_experience(db, tmp_skill_root):
    _write_md(
        tmp_skill_root / "data/wiki_hub/my.md",
        "name: my-wiki\ndescription: wiki desc\nreferences:\n  - r1\n",
    )
    exp = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    assert exp.type == ExperienceType.WIKI
    assert exp.references


def test_add_wiki_missing_file(db):
    with pytest.raises(FileNotFoundError, match="WIKI file not found"):
        ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/none.md")


def test_add_duplicate_source(db, tmp_skill_root):
    _write_md(tmp_skill_root / "data/wiki_hub/my.md", "name: w")
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    with pytest.raises(ValueError, match="already exists"):
        ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")


# ---------------- 查重 / 列表 / 删除 ----------------


def test_check_duplicate_empty_query(db):
    assert ExperienceService.check_duplicate_before_create(ExperienceType.WIKI, "", []) == []


def test_check_duplicate_finds_similar(db, tmp_skill_root):
    _write_md(
        tmp_skill_root / "data/wiki_hub/my.md",
        "name: myname\ndescription: myname alpha\nkeywords: [alpha]",
    )
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    similar = ExperienceService.check_duplicate_before_create(
        ExperienceType.WIKI, "myname", ["alpha"]
    )
    assert len(similar) == 1
    # 名称完全无关的结果被过滤
    similar = ExperienceService.check_duplicate_before_create(
        ExperienceType.WIKI, "zzzznotexist", []
    )
    assert similar == []


def test_list_experiences(db, tmp_skill_root):
    _write_md(tmp_skill_root / "data/wiki_hub/a.md", "name: a\ndescription: alpha")
    _write_md(tmp_skill_root / "data/wiki_hub/b.md", "name: b\ndescription: beta")
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/b.md")
    total, exps = ExperienceService.list_experiences(ExperienceType.WIKI, None, 1, 10, is_hot=None)
    assert total == 2
    assert exps[0].keywords is not None


def test_delete_by_ids_and_source(db, tmp_skill_root):
    _write_md(tmp_skill_root / "data/wiki_hub/a.md", "name: a\nkeywords: [k]")
    exp = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")
    ExperienceService.delete_experience_by_ids([exp.id])
    assert ExperienceService.list_experiences(ExperienceType.WIKI, None, 1, 10, is_hot=None)[0] == 0
    assert KeyWordManager.get_keywords_by_experience_id(exp.id) == []

    exp2 = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")
    ExperienceService.delete_experience_by_source("data/wiki_hub/a.md")
    assert ExperienceService.list_experiences(ExperienceType.WIKI, None, 1, 10, is_hot=None)[0] == 0


# ---------------- merge / optimize ----------------


def _seed_wiki(tmp_skill_root, name, desc, source, keywords=None):
    kws = "\n  - ".join(keywords or [])
    _write_md(
        tmp_skill_root / source,
        f"name: {name}\ndescription: {desc}\nkeywords:\n  - {kws if kws else 'kw'}",
    )
    return ExperienceService.add_experiences(ExperienceType.WIKI, source)


def test_merge_errors(db, tmp_skill_root):
    base = _seed_wiki(tmp_skill_root, "base", "alpha", "data/wiki_hub/base.md")
    with pytest.raises(ValueError, match="不能为空"):
        ExperienceService.merge_experiences(ExperienceType.WIKI, base.id, [])

    with pytest.raises(ValueError, match="不存在或已删除"):
        ExperienceService.merge_experiences(ExperienceType.WIKI, "missing", ["alsomissing"])

    # base_id 不存在但两个合并目标存在
    m1 = _seed_wiki(tmp_skill_root, "m1", "beta", "data/wiki_hub/m1.md")
    m2 = _seed_wiki(tmp_skill_root, "m2", "gamma", "data/wiki_hub/m2.md")
    with pytest.raises(ValueError, match="base_id=missing 不存在"):
        ExperienceService.merge_experiences(ExperienceType.WIKI, "missing", [m1.id, m2.id])

    with pytest.raises(ValueError, match="类型不匹配"):
        ExperienceService.merge_experiences(ExperienceType.SKILL, base.id, [m1.id])

    # 合并目标存在但类型不匹配
    skill_dir = tmp_skill_root / "data/skill_hub/s1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill_def.md").write_text(
        "---\nname: s1\ndescription: skill desc\n---\nbody\n", encoding="utf-8"
    )
    skill_exp = ExperienceService.add_experiences(ExperienceType.SKILL, "data/skill_hub/s1")
    with pytest.raises(ValueError, match="合并目标"):
        ExperienceService.merge_experiences(ExperienceType.WIKI, base.id, [skill_exp.id])


def test_merge_success(db, tmp_skill_root):
    base = _seed_wiki(tmp_skill_root, "base", "alpha desc", "data/wiki_hub/base.md", ["ka"])
    m1 = _seed_wiki(tmp_skill_root, "m1", "beta desc", "data/wiki_hub/m1.md", ["kb"])
    merged = ExperienceService.merge_experiences(ExperienceType.WIKI, base.id, [m1.id])
    assert "合并自：m1" in merged.name
    assert "beta desc" in merged.description
    # 注：merge 从 DB 重建 Experience 时未回填 keywords，合并结果 keywords 为空（见报告中的问题）
    assert merged.keywords == []
    assert KeyWordManager.get_keywords_by_experience_id(base.id) == []


def test_optimize_experience(db, tmp_skill_root):
    exp = _seed_wiki(tmp_skill_root, "n", "alpha", "data/wiki_hub/x.md")
    with pytest.raises(ValueError, match="不存在或已删除"):
        ExperienceService.optimize_experience("missing", name="x")

    # 只改 name
    got = ExperienceService.optimize_experience(exp.id, name="newname")
    assert got.name == "newname"
    # 全量更新
    got = ExperienceService.optimize_experience(
        exp.id, description="new desc!!", keywords=["kw1", "kw2"]
    )
    assert got.description == "new desc"
    assert KeyWordManager.get_keywords_by_experience_id(exp.id) == ["kw1", "kw2"]


# ---------------- 搜索 ----------------


def test_search_experiences_guards(db):
    assert ExperienceService.search_experiences("", ExperienceType.WIKI) == []
    # 纯 ASCII 单字母被过滤
    assert ExperienceService.search_experiences("a", ExperienceType.WIKI) == []
    # 清洗后为空
    assert ExperienceService.search_experiences("!!!", ExperienceType.WIKI) == []


def test_search_experiences_fts(db, tmp_skill_root):
    _write_md(tmp_skill_root / "data/wiki_hub/a.md", "name: a\ndescription: kvcache alpha")
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")
    # is_hot 过滤（搜索前 a 尚未因命中而变热门）
    assert ExperienceService.search_experiences("kvcache", ExperienceType.WIKI, is_hot=True) == []

    exps = ExperienceService.search_experiences("kvcache", ExperienceType.WIKI)
    expected = ExperienceService.list_experiences(ExperienceType.WIKI, None, 1, 10, is_hot=None)[1][0].id
    assert [e.id for e in exps] == [expected]
    assert exps[0].keywords is not None


def test_search_with_content_hybrid(db, tmp_skill_root, monkeypatch):
    from experience_skill_cli.manager.content_searcher import ContentSearcher

    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))
    # a: 元数据+正文命中；b: 仅正文命中；c: 仅元数据命中
    _write_md(tmp_skill_root / "data/wiki_hub/a.md", "name: a\ndescription: kvcache", "kvcache content line")
    _write_md(tmp_skill_root / "data/wiki_hub/b.md", "name: b\ndescription: plain", "needle in body only")
    _write_md(tmp_skill_root / "data/wiki_hub/c.md", "name: c\ndescription: kvcache meta", "nothing relevant")
    exp_a = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")
    exp_b = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/b.md")
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/c.md")

    assert ExperienceService.search_with_content("", ExperienceType.WIKI) == []

    results = ExperienceService.search_with_content("kvcache", ExperienceType.WIKI, top_k=5)
    match_types = [r.match_type for r in results]
    assert match_types.count("both") == 1
    assert match_types.count("metadata") == 1
    both = next(r for r in results if r.match_type == "both")
    assert both.experience.id == exp_a.id
    assert both.snippets
    meta = next(r for r in results if r.match_type == "metadata")
    assert meta.snippets == []
    assert meta.content_score == 0.0

    results = ExperienceService.search_with_content("needle", ExperienceType.WIKI, top_k=5)
    assert len(results) == 1
    assert results[0].experience.id == exp_b.id
    assert results[0].match_type == "content"

    # banned 排除 content 命中
    results = ExperienceService.search_with_content(
        "needle", ExperienceType.WIKI, top_k=5, banned_experience_ids=[exp_b.id]
    )
    assert results == []
    # experience_ids 限定
    results = ExperienceService.search_with_content(
        "kvcache", ExperienceType.WIKI, top_k=5, experience_ids=[exp_a.id]
    )
    assert len(results) == 1
    # is_hot 过滤（b 非热门）
    results = ExperienceService.search_with_content(
        "needle", ExperienceType.WIKI, top_k=5, is_hot=False
    )
    assert len(results) == 1
    results = ExperienceService.search_with_content(
        "needle", ExperienceType.WIKI, top_k=5, is_hot=True
    )
    assert results == []


def test_search_content_only(db, tmp_skill_root, monkeypatch):
    from experience_skill_cli.manager.content_searcher import ContentSearcher

    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))
    _write_md(tmp_skill_root / "data/wiki_hub/a.md", "name: a\ndescription: meta", "special token line")
    exp = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/a.md")

    assert ExperienceService.search_content_only("", ExperienceType.WIKI) == []

    results = ExperienceService.search_content_only("special", ExperienceType.WIKI, top_k=5)
    assert len(results) == 1
    assert results[0].match_type == "content"
    assert results[0].final_score == results[0].content_score

    assert ExperienceService.search_content_only("special", ExperienceType.WIKI, top_k=5, is_hot=True) == []
    assert (
        ExperienceService.search_content_only("special", ExperienceType.WIKI, top_k=5, experience_ids=["other"])
        == []
    )
    results = ExperienceService.search_content_only(
        "special", ExperienceType.WIKI, top_k=5, experience_ids=[exp.id]
    )
    assert len(results) == 1
