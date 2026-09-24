"""schema 与 console 输出测试。"""

from experience_skill_cli.console import (
    _build_enum_display_map,
    _format_value,
    blank,
    deleted,
    echo,
    error,
    info,
    launch,
    link,
    print_experience,
    print_experience_list,
    print_hybrid_search_results,
    rocket,
    search_result,
    section,
    success,
    warn,
)
from experience_skill_cli.schema.enum import ExperienceStatus, ExperienceType
from experience_skill_cli.schema.exprience import Experience


def test_enum_members():
    assert ExperienceType.SKILL.value == "skill"
    assert ExperienceType.WIKI.value == "wiki"
    assert ExperienceStatus.EXISTED.value == "existed"
    assert ExperienceStatus.DELETED.value == "deleted"


def test_experience_defaults():
    exp = Experience()
    assert exp.id
    assert exp.type == ExperienceType.WIKI
    assert exp.status == ExperienceStatus.EXISTED
    assert exp.keywords == []
    assert exp.is_hot == 0
    assert exp.created_at and exp.updated_at


def test_format_value_enum_and_list_and_none():
    assert _format_value(ExperienceType.SKILL) == "SKILL"
    # 命中 _build_enum_display_map 缓存分支
    assert _format_value(ExperienceStatus.DELETED) == "已删除"
    assert _format_value(["a", "b"]) == "a, b"
    assert _format_value(None) == ""
    assert _format_value(123) == "123"


def test_semantic_outputs(capsys):
    success("ok")
    info("msg")
    warn("warn")
    error("err")
    deleted("del")
    search_result("find")
    launch("browser")
    link("url")
    rocket("server")
    blank()
    section("title")
    echo("raw", end="")
    out, err = capsys.readouterr()
    assert "✅ ok" in out
    assert "📋 msg" in out
    assert "🗑️  del" in out
    assert "🔍 find" in out
    assert "🌐 browser" in out
    assert "🔗 url" in out
    assert "🚀 server" in out
    assert "\n" in out
    assert "===== title =====" in out
    assert out.endswith("raw")
    assert "⚠️  warn" in err
    assert "❌ err" in err


def test_enum_display_map_cached():
    _build_enum_display_map()
    # 已填充时直接返回，不重复构建
    _build_enum_display_map()
    assert _format_value(ExperienceType.WIKI) == "WIKI"


def _make_exp(**kw):
    base = dict(
        name="n",
        description="d",
        keywords=["k1"],
        source="s",
    )
    base.update(kw)
    return Experience(**base)


def test_print_experience(capsys):
    print_experience(_make_exp())
    out, _ = capsys.readouterr()
    assert "经验详情" in out
    assert "名称" in out
    assert "来源" in out

    print_experience(_make_exp(), 2)
    out, _ = capsys.readouterr()
    assert "第 2 条经验" in out


def test_print_experience_list(capsys):
    print_experience_list([], total=0)
    out, _ = capsys.readouterr()
    assert "总计：0 条" in out

    print_experience_list([_make_exp()], total=1)
    out, _ = capsys.readouterr()
    assert "总计：1 条" in out

    print_experience_list([_make_exp(name="a"), _make_exp(name="b")])
    out, _ = capsys.readouterr()
    assert "共 2 条" in out
    assert "第 1 条经验" in out
    assert "第 2 条经验" in out


def test_print_hybrid_search_results_empty(capsys):
    print_hybrid_search_results([])
    out, _ = capsys.readouterr()
    assert "无匹配结果" in out


def test_print_hybrid_search_results(capsys):
    from experience_skill_cli.manager.content_searcher import ContentSnippet
    from experience_skill_cli.service.experience_service import HybridSearchResult

    long_snip = "x" * 150
    results = [
        HybridSearchResult(
            experience=_make_exp(description="d" * 250),
            match_type="both",
            db_score=0.5,
            content_score=0.4,
            final_score=0.45,
            snippets=[
                ContentSnippet(line_num=1, content=long_snip),
                ContentSnippet(line_num=2, content="hit"),
                ContentSnippet(line_num=3, content="h2"),
                ContentSnippet(line_num=4, content="h3"),
            ],
            content_hit_count=4,
        ),
        HybridSearchResult(
            experience=_make_exp(description=""),
            match_type="unknown_type",
            db_score=0.1,
            content_score=0.1,
            final_score=0.1,
        ),
    ]
    print_hybrid_search_results(results)
    out, _ = capsys.readouterr()
    assert "第 1 条结果" in out
    assert "元数据 + 正文" in out
    assert "正文命中" in out
    assert "L1: " + "x" * 97 + "..." in out
    assert "L2: hit" in out
    assert "L3: h2" in out
    assert "h3" not in out.split("第 2 条结果")[0]  # 只展示 3 条片段
    assert "unknown_type" in out  # 未知匹配方式原样输出
    assert "否" in out  # is_hot=0
