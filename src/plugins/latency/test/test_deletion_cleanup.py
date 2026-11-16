from types import SimpleNamespace

from latency.task.deletion import cleanup_log_artifacts


def test_cleanup_log_artifacts_removes_owned_upload_and_temp_dirs(
    monkeypatch, tmp_path
):
    witty_dir = tmp_path / "witty"
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    uploaded = upload_root / "log-id.zip"
    uploaded.write_bytes(b"zip")
    preprocess = witty_dir / "log_preprocessed_log-id"
    preprocess.mkdir(parents=True)
    (preprocess / "partial.log").write_text("partial", encoding="utf-8")
    diagnosis = witty_dir / "log_log-id"
    diagnosis.mkdir()
    (diagnosis / "failure.log").write_text("failure", encoding="utf-8")
    monkeypatch.setenv("WITTY_DIR", str(witty_dir))

    cleanup_log_artifacts(
        SimpleNamespace(id="log-id", file_path=str(uploaded)),
        witty_dir=str(witty_dir),
        upload_root=str(upload_root),
    )

    assert not uploaded.exists()
    assert not preprocess.exists()
    assert not diagnosis.exists()


def test_cleanup_log_artifacts_preserves_user_local_source(monkeypatch, tmp_path):
    witty_dir = tmp_path / "witty"
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    local_source = tmp_path / "user-logs"
    local_source.mkdir()
    (local_source / "access.log").write_text("log", encoding="utf-8")
    monkeypatch.setenv("WITTY_DIR", str(witty_dir))

    cleanup_log_artifacts(
        SimpleNamespace(id="local-id", file_path=str(local_source)),
        witty_dir=str(witty_dir),
        upload_root=str(upload_root),
    )

    assert local_source.exists()
