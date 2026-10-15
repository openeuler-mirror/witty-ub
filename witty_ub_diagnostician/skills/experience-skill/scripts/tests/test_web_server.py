"""web_server.py FastAPI 接口测试。"""

import pytest

from experience_skill_cli.web_server import (
    _exp_to_dict,
    _hybrid_result_to_dict,
    _strip_yaml_header,
    app,
    start_web_server,
)


@pytest.fixture()
def client(db, tmp_skill_root):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def _add_wiki(tmp_skill_root, name, desc, body, source, keywords=None):
    from experience_skill_cli.service.experience_service import ExperienceService
    from experience_skill_cli.schema.enum import ExperienceType

    path = tmp_skill_root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    kws = ""
    if keywords:
        kws = "keywords:\n  - " + "\n  - ".join(keywords) + "\n"
    path.write_text(f"---\nname: {name}\ndescription: {desc}\n{kws}---\n{body}\n", encoding="utf-8")
    return ExperienceService.add_experiences(ExperienceType.WIKI, source)


# ---------------- 纯函数 ----------------


def test_strip_yaml_header():
    assert _strip_yaml_header("---\nname: x\n---\n\nbody") == "body"
    assert _strip_yaml_header("no header") == "no header"


def test_exp_to_dict():
    from experience_skill_cli.schema.exprience import Experience

    exp = Experience(name="n", keywords=["k"])
    d = _exp_to_dict(exp)
    assert d["name"] == "n"
    assert d["type"] == "wiki"
    assert d["keywords"] == ["k"]
    assert d["status"] == "existed"


def test_hybrid_result_to_dict(tmp_skill_root):
    from experience_skill_cli.service.experience_service import HybridSearchResult
    from experience_skill_cli.schema.exprience import Experience

    sr = HybridSearchResult(
        experience=Experience(name="n"),
        match_type="both",
        db_score=1.0,
        content_score=1.0,
        final_score=1.0,
    )
    d = _hybrid_result_to_dict(sr)
    assert d["match_type"] == "both"
    assert d["name"] == "n"


# ---------------- HTTP 接口 ----------------


def test_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "html" in resp.text.lower()


def test_index_missing_template(client, monkeypatch):
    from pathlib import Path

    import experience_skill_cli.web_server as ws

    monkeypatch.setattr(ws, "TEMPLATES_DIR", Path("/nonexistent"))
    resp = client.get("/")
    assert resp.status_code == 404


def test_list_keywords(client, tmp_skill_root):
    _add_wiki(tmp_skill_root, "a", "desc", "body", "data/wiki_hub/a.md", keywords=["kw1", "kw2"])
    resp = client.get("/api/keywords")
    assert resp.json()["keywords"] == ["kw1", "kw2"]
    resp = client.get("/api/keywords", params={"exp_type": "WIKI"})
    assert resp.json()["keywords"] == ["kw1", "kw2"]
    resp = client.get("/api/keywords", params={"exp_type": "SKILL"})
    assert resp.json()["keywords"] == []


def test_list_experiences(client, tmp_skill_root):
    _add_wiki(tmp_skill_root, "a", "alpha desc", "body", "data/wiki_hub/a.md", keywords=["kw1"])
    resp = client.get("/api/experiences")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "a"
    assert data["items"][0]["keywords"] == ["kw1"]

    resp = client.get("/api/experiences", params={"exp_type": "SKILL"})
    assert resp.json()["total"] == 0
    resp = client.get("/api/experiences", params={"name": "a"})
    assert resp.json()["total"] == 1
    resp = client.get("/api/experiences", params={"kw": "kw1"})
    assert resp.json()["total"] == 1
    resp = client.get("/api/experiences", params={"is_hot": True})
    assert resp.json()["total"] == 0


def test_hot_experiences(client, tmp_skill_root):
    exp = _add_wiki(tmp_skill_root, "a", "alpha", "body", "data/wiki_hub/a.md")
    from experience_skill_cli.service.experience_service import ExperienceService

    ExperienceService.search_experiences("alpha", exp.type, top_k=1)
    resp = client.get("/api/experiences/hot")
    data = resp.json()
    assert data["total"] == 1


def test_search_metadata_mode(client, tmp_skill_root):
    _add_wiki(tmp_skill_root, "a", "kvcache desc", "body", "data/wiki_hub/a.md")
    resp = client.get("/api/experiences/search", params={"query": "kvcache", "search_mode": "metadata"})
    data = resp.json()
    assert data["mode"] == "metadata"
    assert len(data["items"]) == 1

    # 跨类型搜索：不传 exp_type
    resp = client.get("/api/experiences/search", params={"query": "kvcache", "search_mode": "metadata"})
    assert resp.json()["mode"] == "metadata"


def test_search_hybrid_and_content_mode(client, tmp_skill_root, monkeypatch):
    from experience_skill_cli.manager.content_searcher import ContentSearcher

    monkeypatch.setattr(ContentSearcher, "_rg_available", staticmethod(lambda: False))
    _add_wiki(tmp_skill_root, "a", "kvcache desc", "kvcache body line", "data/wiki_hub/a.md")
    resp = client.get("/api/experiences/search", params={"query": "kvcache", "search_mode": "hybrid"})
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["items"][0]["match_type"] == "both"

    resp = client.get("/api/experiences/search", params={"query": "kvcache", "search_mode": "content"})
    data = resp.json()
    assert data["mode"] == "content"
    assert len(data["items"]) == 1

    # 默认 mode = hybrid
    resp = client.get("/api/experiences/search", params={"query": "kvcache"})
    assert resp.json()["mode"] == "hybrid"

    # 指定类型
    resp = client.get(
        "/api/experiences/search",
        params={"query": "kvcache", "search_mode": "hybrid", "exp_type": "SKILL"},
    )
    assert resp.json()["items"] == []


def test_get_experience_detail(client, tmp_skill_root):
    exp = _add_wiki(tmp_skill_root, "a", "alpha", "body content here", "data/wiki_hub/a.md", keywords=["k"])
    resp = client.get(f"/api/experiences/{exp.id}")
    data = resp.json()
    assert data["name"] == "a"
    assert data["keywords"] == ["k"]
    assert data["content"].startswith("body content here")
    assert "name: a" not in data["content"]

    resp = client.get("/api/experiences/missing-id")
    assert resp.status_code == 404


def test_get_experience_source_missing(client, tmp_skill_root):
    # 文件被删除后读取失败 → content 空字符串
    exp = _add_wiki(tmp_skill_root, "a", "alpha", "body", "data/wiki_hub/gone.md")
    (tmp_skill_root / "data/wiki_hub/gone.md").unlink()
    resp = client.get(f"/api/experiences/{exp.id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == ""


def test_start_web_server(tmp_skill_root, db, monkeypatch, capsys):
    import contextlib
    import time as time_mod

    import experience_skill_cli.web_server as ws

    monkeypatch.setattr(ws.uvicorn, "run", lambda *a, **kw: None)
    monkeypatch.setattr(time_mod, "sleep", lambda *a, **kw: None)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # 1) 服务就绪 + 不开浏览器
    monkeypatch.setattr(ws.urllib.request, "urlopen", lambda *a, **kw: contextlib.nullcontext())
    start_web_server("127.0.0.1", 8123, open_browser=False)
    out, _ = capsys.readouterr()
    assert "请访问" in out

    # 2) 服务就绪 + 自动打开浏览器
    monkeypatch.setenv("DISPLAY", ":0")
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda url: True)
    start_web_server("127.0.0.1", 8123, open_browser=True)
    out, _ = capsys.readouterr()
    assert "浏览器已打开" in out

    # 3) 浏览器打开抛异常
    monkeypatch.setattr(webbrowser, "open", lambda url: (_ for _ in ()).throw(RuntimeError))
    start_web_server("127.0.0.1", 8123, open_browser=True)
    _, err = capsys.readouterr()
    assert "无法自动打开浏览器" in err

    # 4) 服务启动超时分支
    monkeypatch.setattr(
        ws.urllib.request, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(OSError("no"))
    )
    start_web_server("127.0.0.1", 8123, open_browser=True)
    _, err = capsys.readouterr()
    assert "服务启动超时" in err
