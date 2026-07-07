from latency.task.log_preprocessor import split_unmatched_log_files


def test_split_unmatched_log_files(tmp_path):
    matched = tmp_path / "access.log"
    unmatched = tmp_path / "abcd.log"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line_12 = " | ".join(str(i) for i in range(13)) + "\n"
    access_line_13 = " | ".join(str(i) for i in range(14)) + "\n"
    matched.write_text(runtime_line, encoding="utf-8")
    unmatched.write_text(
        runtime_line + access_line_12 + "unknown\n" + access_line_13,
        encoding="utf-8",
    )

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 2)}
    assert (tmp_path / "abcd.log_split_runtime.log").read_text(encoding="utf-8") == runtime_line
    assert (tmp_path / "abcd.log_split_access.log").read_text(
        encoding="utf-8"
    ) == access_line_12 + access_line_13
    assert not (tmp_path / "access.log_split_runtime.log").exists()
    assert unmatched.exists()


def test_split_unmatched_rotated_log_file(tmp_path):
    unmatched = tmp_path / "abcd.log_yyy"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line = " | ".join(str(i) for i in range(13)) + "\n"
    unmatched.write_text(runtime_line + access_line, encoding="utf-8")

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 1)}
    assert (
        tmp_path / "abcd.log_yyy_split_runtime.log"
    ).read_text(encoding="utf-8") == runtime_line
    assert (
        tmp_path / "abcd.log_yyy_split_access.log"
    ).read_text(encoding="utf-8") == access_line
    assert unmatched.exists()


def test_split_unmatched_plain_text_file(tmp_path):
    unmatched = tmp_path / "mixed-output"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line = " | ".join(str(i) for i in range(13)) + "\n"
    unmatched.write_text(runtime_line + access_line, encoding="utf-8")

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 1)}
    assert (
        tmp_path / "mixed-output_split_runtime.log"
    ).read_text(encoding="utf-8") == runtime_line
    assert (
        tmp_path / "mixed-output_split_access.log"
    ).read_text(encoding="utf-8") == access_line
