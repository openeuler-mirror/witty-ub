# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Two-level fault label dictionary contract tests.

The dictionary itself is owned by ``witty_ub_diagnostician``; these tests pin
the read/validate/snapshot behaviour the case library depends on.
"""
from __future__ import annotations

import json
import os

import pytest

from latency.services import label_taxonomy


def _options() -> dict:
    return label_taxonomy.label_options()


def _first_and_second() -> tuple[str, str]:
    options = _options()
    first = options["first_level_labels"][0]
    pair = next(
        item for item in options["pairs"] if item["first_level_label"] == first
    )
    return first, pair["second_level_labels"][0]


def test_source_tree_taxonomy_is_loaded_and_versioned_by_content():
    taxonomy = label_taxonomy.load_taxonomy()

    assert taxonomy.path.is_file()
    assert len(taxonomy.version) == 64
    assert taxonomy.first_levels
    assert all(taxonomy.pairs[first] for first in taxonomy.first_levels)
    assert taxonomy.first_levels == tuple(sorted(taxonomy.first_levels))


def test_label_options_cover_all_first_levels():
    options = _options()

    assert len(options["version"]) == 64
    assert [pair["first_level_label"] for pair in options["pairs"]] == list(
        options["first_level_labels"]
    )
    for pair in options["pairs"]:
        assert pair["second_level_labels"] == sorted(pair["second_level_labels"])


def test_valid_pair_returns_pair_status_and_taxonomy_version():
    first, second = _first_and_second()

    validation = label_taxonomy.validate_labels(first, second)

    assert validation.status == "pair"
    assert validation.valid is True
    assert validation.error is None
    assert validation.first_level_label == first
    assert validation.second_level_label == second
    assert validation.taxonomy_version == _options()["version"]


def test_first_only_is_accepted():
    first, _ = _first_and_second()

    validation = label_taxonomy.validate_labels(first, None)

    assert validation.status == "first_only"
    assert validation.valid is True
    assert validation.second_level_label is None


def test_empty_labels_are_unclassified_not_invalid():
    validation = label_taxonomy.validate_labels(None, None)

    assert validation.status == "empty"
    assert validation.valid is True
    assert validation.first_level_label is None
    assert validation.second_level_label is None


@pytest.mark.parametrize(
    "first, second, error",
    [
        (None, "某个二级", "second_without_first"),
        ("不存在的分类", "不存在-子类", "unknown_first_level_label"),
        (123, None, "not_string"),
        ("null", None, "empty_or_null_string"),
    ],
)
def test_malformed_labels_are_invalid_and_keep_raw_values(first, second, error):
    validation = label_taxonomy.validate_labels(first, second)

    assert validation.status == "invalid"
    assert validation.valid is False
    assert validation.error == error


def test_second_level_from_another_first_level_is_rejected():
    options = _options()
    pairs = {
        pair["first_level_label"]: pair["second_level_labels"]
        for pair in options["pairs"]
    }
    firsts = list(pairs)
    first = firsts[0]
    other_second = pairs[firsts[1]][0]

    validation = label_taxonomy.validate_labels(first, other_second)

    assert validation.status == "invalid"
    assert validation.error == "unknown_label_pair"


def test_snapshot_hash_is_deterministic_and_label_sensitive():
    first, second = _first_and_second()
    version = _options()["version"]

    base = label_taxonomy.label_snapshot_hash(first, second, version)

    assert len(base) == 64
    assert base == label_taxonomy.label_snapshot_hash(first, second, version)
    assert base != label_taxonomy.label_snapshot_hash(first, None, version)
    assert base != label_taxonomy.label_snapshot_hash(None, None, version)
    assert base != label_taxonomy.label_snapshot_hash(first, second, "other")


def test_override_file_is_used_and_cache_follows_mtime(tmp_path, monkeypatch):
    path = tmp_path / "log_label.json"
    path.write_text(
        json.dumps(
            [
                {"first_level_label": "自定一级", "second_level_label": "自定一级-甲"},
                {"first_level_label": "自定一级", "second_level_label": "自定一级-乙"},
                {"first_level_label": "另一组", "second_level_label": "另一组-丙"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WITTY_LABEL_TAXONOMY_FILE", str(path))

    taxonomy = label_taxonomy.load_taxonomy()
    assert taxonomy.path == path
    assert set(taxonomy.pairs) == {"自定一级", "另一组"}
    assert taxonomy.pairs["自定一级"] == frozenset({"自定一级-甲", "自定一级-乙"})

    assert (
        label_taxonomy.validate_labels("自定一级", "另一组-丙").error
        == "unknown_label_pair"
    )

    first_version = taxonomy.version
    path.write_text(
        json.dumps(
            [{"first_level_label": "自定一级", "second_level_label": "自定一级-甲"}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    os.utime(path, (taxonomy.path.stat().st_atime, taxonomy.path.stat().st_mtime + 5))

    refreshed = label_taxonomy.load_taxonomy()
    assert refreshed.version != first_version
    assert set(refreshed.pairs) == {"自定一级"}


def test_missing_taxonomy_raises(monkeypatch):
    monkeypatch.setattr(label_taxonomy, "taxonomy_path", lambda: None)

    with pytest.raises(label_taxonomy.TaxonomyError) as exc_info:
        label_taxonomy.load_taxonomy()
    assert str(exc_info.value) == "label_taxonomy_missing"

    with pytest.raises(label_taxonomy.TaxonomyError):
        label_taxonomy.validate_labels(None, None)
    with pytest.raises(label_taxonomy.TaxonomyError):
        label_taxonomy.label_options()


@pytest.mark.parametrize(
    "content",
    [
        "{ not json",
        json.dumps({"first_level_label": "x"}, ensure_ascii=False),
        json.dumps([{"first_level_label": "只有一级"}], ensure_ascii=False),
        json.dumps([{"first_level_label": "x", "second_level_label": None}]),
        json.dumps([]),
    ],
)
def test_broken_taxonomy_payload_raises(tmp_path, monkeypatch, content):
    path = tmp_path / "broken_log_label.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("WITTY_LABEL_TAXONOMY_FILE", str(path))

    with pytest.raises(label_taxonomy.TaxonomyError) as exc_info:
        label_taxonomy.load_taxonomy()
    assert "label_taxonomy" in str(exc_info.value)
