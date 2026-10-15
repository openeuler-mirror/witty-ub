"""cli.py 子命令测试（通过 monkeypatch sys.argv 调 main()）。"""

import pytest

import experience_skill_cli.cli as cli_mod
from experience_skill_cli.cli import main
from experience_skill_cli.schema.enum import ExperienceType
from experience_skill_cli.service.experience_service import ExperienceService


@pytest.fixture()
def seeded_hub(tmp_skill_root):
    """准备 SKILL / WIKI 各一条经验素材。"""
    skill_dir = tmp_skill_root / "data/skill_hub/my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill_def.md").write_text(
        "---\nname: my-skill\ndescription: kvcache alpha\nkeywords: [k1]\n---\nbody\n",
        encoding="utf-8",
    )
    wiki = tmp_skill_root / "data/wiki_hub/my.md"
    wiki.write_text(
        "---\nname: my-wiki\ndescription: kvcache beta\nkeywords: [k2]\n---\nbody\n",
        encoding="utf-8",
    )
    return tmp_skill_root


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["prog", *argv])
    main()


def test_add_and_sync(monkeypatch, db, seeded_hub, capsys):
    run_cli(monkeypatch, "add-experiences", "--type", "SKILL", "--source", "data/skill_hub/my-skill")
    out, _ = capsys.readouterr()
    assert "成功添加 SKILL 经验" in out

    # 重复添加抛 ValueError（main 不捕获，直接冒泡）
    monkeypatch.setattr(
        "sys.argv", ["prog", "add-experiences", "--type", "SKILL", "--source", "data/skill_hub/my-skill"]
    )
    with pytest.raises(ValueError, match="already exists"):
        main()

    # sync：已存在的 skill 被跳过（0 新增），wiki 新增
    run_cli(monkeypatch, "sync")
    out, _ = capsys.readouterr()
    assert "新增 0 个 Skill" in out
    assert "1 篇 Wiki" in out


def test_sync_error_collection(monkeypatch, db, seeded_hub, capsys):
    # skill 目录存在但 skill_def.md 缺失 → 收集错误并告警
    bad = seeded_hub / "data/skill_hub/bad-skill"
    bad.mkdir()
    run_cli(monkeypatch, "sync")
    out, err = capsys.readouterr()
    assert "新增 1 个 Skill" in out
    assert "1 篇 Wiki" in out
    assert "SKILL data/skill_hub/bad-skill" in err


def test_sync_empty_dirs(monkeypatch, tmp_skill_root, capsys):
    run_cli(monkeypatch, "sync")
    out, _ = capsys.readouterr()
    assert "新增 0 个 Skill" in out


def test_list_experiences(monkeypatch, db, seeded_hub, capsys):
    ExperienceService.add_experiences(ExperienceType.SKILL, "data/skill_hub/my-skill")
    run_cli(monkeypatch, "list-experiences")
    out, _ = capsys.readouterr()
    assert "总计：1 条" in out
    run_cli(monkeypatch, "list-experiences", "--type", "SKILL", "--name", "my-skill", "--is-hot", "false")
    assert "my-skill" in capsys.readouterr()[0]
    run_cli(monkeypatch, "list-experiences", "--type", "WIKI")
    assert "总计：0 条" in capsys.readouterr()[0]


def test_delete_by_ids_and_source(monkeypatch, db, seeded_hub, capsys):
    exp = ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(monkeypatch, "delete-by-ids", "--ids", exp.id)
    out, _ = capsys.readouterr()
    assert f"已删除经验 ID：['{exp.id}']" in out

    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(monkeypatch, "delete-by-source", "--source", "data/wiki_hub/my.md")
    out, _ = capsys.readouterr()
    assert "已删除来源为 data/wiki_hub/my.md 的经验" in out


def test_search_metadata_only(monkeypatch, db, seeded_hub, capsys):
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(
        monkeypatch,
        "search-experiences",
        "--query",
        "kvcache",
        "--type",
        "WIKI",
        "--metadata-only",
    )
    out, _ = capsys.readouterr()
    assert "仅元数据）找到 1 条结果" in out


def test_search_content_only(monkeypatch, db, seeded_hub, capsys):
    from experience_skill_cli.manager.content_searcher import ContentSearcher

    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(
        monkeypatch,
        "search-experiences",
        "--query",
        "kvcache",
        "--type",
        "WIKI",
        "--content-only",
    )
    out, _ = capsys.readouterr()
    assert "仅正文）找到" in out


def test_search_hybrid_default(monkeypatch, db, seeded_hub, capsys):
    from experience_skill_cli.manager.content_searcher import ContentSearcher

    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(
        monkeypatch,
        "search-experiences",
        "--query",
        "kvcache",
        "--type",
        "WIKI",
        "--top-k",
        "3",
        "--fields",
        "k2",
        "--banned-ids",
        "nope",
        "--experience-ids",
        "anyid",
    )
    out, _ = capsys.readouterr()
    assert "找到" in out


def test_delete_all(monkeypatch, db, seeded_hub, capsys):
    ExperienceService.add_experiences(ExperienceType.WIKI, "data/wiki_hub/my.md")
    run_cli(monkeypatch, "delete-all")
    out, _ = capsys.readouterr()
    assert "已删除所有经验数据" in out
    total, _ = ExperienceService.list_experiences(None, None, 1, 10, is_hot=None)
    assert total == 0


def test_web_subcommand(monkeypatch, db, seeded_hub, capsys):
    def fake_start(host, port, *, open_browser):
        print(f"FAKE_WEB {host}:{port} {open_browser}")

    monkeypatch.setattr(cli_mod, "start_web_server", fake_start)
    run_cli(monkeypatch, "web", "--host", "0.0.0.0", "--port", "9999", "--no-browser")
    out, _ = capsys.readouterr()
    assert "FAKE_WEB 0.0.0.0:9999 False" in out


def test_required_subcommand(monkeypatch, db):
    monkeypatch.setattr("sys.argv", ["prog"])
    with pytest.raises(SystemExit):
        main()
