"""manager 层：KeyWordManager 与 ExperienceManager 测试。"""

from datetime import datetime

from experience_skill_cli.common.exprience import HOT_EXPRINCE_CNT_LIMIT
from experience_skill_cli.manager.experience_manager import ExperienceManager
from experience_skill_cli.manager.keyword_manager import KeyWordManager
from experience_skill_cli.schema.enum import ExperienceType
from experience_skill_cli.schema.exprience import Experience


def _insert(db, exp_id, name, desc, keywords=None, exp_type=ExperienceType.SKILL, is_hot=0, source=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    assert db.run(
        """
        INSERT INTO experience_table
            (id, type, name, description, "references", status, is_hot, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, '', 'existed', ?, ?, ?, ?)
        """,
        (exp_id, exp_type.value, name, desc, is_hot, source or f"src/{exp_id}", now, now),
    )
    for kw in keywords or []:
        KeyWordManager.add_keywords(exp_id, [kw])
    return exp_id


# ---------------- KeyWordManager ----------------


def test_keyword_crud(db):
    KeyWordManager.add_keywords("e1", ["k1", "k2"])
    KeyWordManager.add_keywords("e2", ["k2"])
    assert KeyWordManager.get_keywords_by_experience_id("e1") == ["k1", "k2"]

    _insert(db, "e1", "n1", "d", exp_type=ExperienceType.WIKI)
    _insert(db, "e2", "n2", "d", exp_type=ExperienceType.SKILL)

    assert KeyWordManager.get_experience_ids_by_keywords(["k1"]) == ["e1"]
    assert set(KeyWordManager.get_experience_ids_by_keywords(["k2"])) == {"e1", "e2"}
    assert KeyWordManager.get_experience_ids_by_keywords([]) == []

    assert set(KeyWordManager.get_all_keywords()) == {"k1", "k2"}
    assert KeyWordManager.get_all_keywords(ExperienceType.WIKI) == ["k1", "k2"]
    assert KeyWordManager.get_all_keywords(ExperienceType.SKILL) == ["k2"]

    KeyWordManager.delete_keywords_by_experience_id("e1")
    assert KeyWordManager.get_keywords_by_experience_id("e1") == []
    assert KeyWordManager.get_experience_ids_by_keywords(["k1"]) == []


# ---------------- ExperienceManager ----------------


def test_add_and_row_to_experience(db):
    exp = Experience(name="n", description="kvcache alpha", keywords=["alpha"], source="s")
    ExperienceManager.add_experiences([exp])
    got = ExperienceManager.query_experience_by_source("s")
    assert len(got) == 1
    assert got[0].name == "n"
    assert got[0].type == ExperienceType.WIKI
    assert got[0].description == "kvcache alpha"


def test_delete_and_query_by_ids(db):
    _insert(db, "e1", "n1", "d")
    _insert(db, "e2", "n2", "d")
    assert len(ExperienceManager.query_experience_by_ids(["e1", "e2"])) == 2
    assert ExperienceManager.query_experience_by_ids([]) == []

    ExperienceManager.delete_experiences_by_ids(["e1"])
    assert ExperienceManager.query_experience_by_ids(["e1"]) == []
    assert ExperienceManager.query_experience_ids_by_source("src/e1") == []


def test_update_experience(db):
    _insert(db, "e1", "n1", "d1")
    exp = ExperienceManager.query_experience_by_ids(["e1"])[0]
    exp.name = "n2"
    exp.description = "d2"
    ExperienceManager.update_experience(exp)
    got = ExperienceManager.query_experience_by_ids(["e1"])[0]
    assert got.name == "n2"
    assert got.description == "d2"


def test_update_hot_experience_touch_when_hot(db):
    _insert(db, "e1", "n1", "d", is_hot=1)
    ExperienceManager.update_hot_experience("e1")
    assert ExperienceManager.query_experience_by_ids(["e1"])[0].is_hot == 1
    # 不存在的经验：无任何变化
    ExperienceManager.update_hot_experience("missing")


def test_update_hot_experience_sets_hot_and_evicts_oldest(db):
    ids = []
    for i in range(HOT_EXPRINCE_CNT_LIMIT + 1):
        eid = f"e{i}"
        _insert(db, eid, f"n{i}", "d", is_hot=1)
        ids.append(eid)

    # 已满：e0 updated_at 最旧，插入新热门后 e0 被取消
    _insert(db, "new", "nn", "d", is_hot=0)
    ExperienceManager.update_hot_experience("new")
    assert ExperienceManager.query_experience_by_ids(["e0"])[0].is_hot == 0
    assert ExperienceManager.query_experience_by_ids(["new"])[0].is_hot == 1


def test_list_experiences_filters_and_pagination(db):
    _insert(db, "a", "alpha one", "contains needle here", keywords=["kw"], exp_type=ExperienceType.WIKI, is_hot=1)
    _insert(db, "b", "beta two", "plain desc", exp_type=ExperienceType.SKILL)
    _insert(db, "c", "gamma needle", "desc needle", exp_type=ExperienceType.WIKI)

    total, exps = ExperienceManager.list_experiences(None, None, None, None, 1, 10)
    assert total == 3
    assert len(exps) == 3

    total, exps = ExperienceManager.list_experiences(ExperienceType.WIKI, None, None, None, 1, 10)
    assert total == 2

    total, _ = ExperienceManager.list_experiences(None, None, "alpha", None, 1, 10)
    assert total == 1

    total, _ = ExperienceManager.list_experiences(None, ["needle"], None, None, 1, 10)
    assert total == 2

    total, _ = ExperienceManager.list_experiences(None, None, None, True, 1, 10)
    assert total == 1

    total, _ = ExperienceManager.list_experiences(None, None, None, False, 1, 10)
    assert total == 2

    total, exps = ExperienceManager.list_experiences(None, None, None, None, 1, 2)
    assert total == 3
    assert len(exps) == 2
    total, exps = ExperienceManager.list_experiences(None, None, None, None, 2, 2)
    assert len(exps) == 1

    # 空关键词 / 空 ID 列表短路
    assert ExperienceManager.list_experiences(None, [], None, None, 1, 10) == (0, [])
    assert ExperienceManager.list_experiences(None, None, None, None, 1, 10, experience_ids=[]) == (0, [])

    total, _ = ExperienceManager.list_experiences(None, None, None, None, 1, 10, experience_ids=["a"])
    assert total == 1


def test_fts5_search(db):
    _insert(db, "a", "n1", "kvcache alpha beta", exp_type=ExperienceType.SKILL)
    _insert(db, "b", "n2", "network gamma delta", exp_type=ExperienceType.SKILL)
    _insert(db, "c", "n3", "kvcache only here", exp_type=ExperienceType.WIKI)

    # 短路分支
    assert ExperienceManager.query_experience_by_fts5_use_description(["k"], ExperienceType.SKILL, top_k=0) == []
    assert ExperienceManager.query_experience_by_fts5_use_description(["k"], ExperienceType.SKILL, fields=[]) == []
    assert (
        ExperienceManager.query_experience_by_fts5_use_description(["k"], ExperienceType.SKILL, experience_ids=[])
        == []
    )

    # 紧凑 AND 查询
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["kvcache", "alpha"], ExperienceType.SKILL, top_k=5
    )
    assert [e.id for e in exps] == ["a"]

    # 松散 OR 补全
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["alpha", "gamma"], ExperienceType.SKILL, top_k=5
    )
    assert {e.id for e in exps} == {"a", "b"}

    # banned ids 排除
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["kvcache"], ExperienceType.SKILL, top_k=5, banned_experience_ids=["a"]
    )
    assert [e.id for e in exps] == []

    # experience_ids 限定
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["kvcache"], ExperienceType.SKILL, top_k=5, experience_ids=["b"]
    )
    assert exps == []

    # fields 关键词过滤：b 有 keyword 'kb'
    KeyWordManager.add_keywords("b", ["kb"])
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["gamma"], ExperienceType.SKILL, top_k=5, fields=["kb"]
    )
    assert [e.id for e in exps] == ["b"]

    # is_hot 过滤
    _insert(db, "d", "n4", "kvcache hot one", exp_type=ExperienceType.SKILL, is_hot=1)
    exps = ExperienceManager.query_experience_by_fts5_use_description(
        ["kvcache"], ExperienceType.SKILL, top_k=5, is_hot=True
    )
    assert [e.id for e in exps] == ["d"]
