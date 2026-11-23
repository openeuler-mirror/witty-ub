# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case-matching label view of the report generation taxonomy.

The dictionary file is owned by ``witty_ub_diagnostician``; this module only
reads it, validates label pairs and computes a stable snapshot hash/version.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

TAXONOMY_RELATIVE_PATH = (
    Path("witty_ub_diagnostician")
    / "skills"
    / "diagnostic-report-generation"
    / "references"
    / "log_label.json"
)
TAXONOMY_DEPLOY_RELATIVE_PATH = (
    Path("witty_ub_diagnostician")
    / ".opencode"
    / "skills"
    / "diagnostic-report-generation"
    / "references"
    / "log_label.json"
)

_TAXONOMY_CACHE: dict[str, tuple[float, "Taxonomy"]] = {}


def _model_label(domain, component, fault_type):
    family = fault_type.partition("-")[0]
    if fault_type == "使用问题":
        return component
    if domain == "硬件故障":
        if family in {"L1交换机故障", "L2交换机故障"}:
            return "UB交换机故障"
        if family not in {"以太交换机故障", "光纤故障"}:
            return domain
    return family


class TaxonomyError(Exception):
    """Raised when the label dictionary cannot be read or parsed."""


@dataclass(frozen=True)
class Taxonomy:
    path: Path
    version: str
    pairs: dict[str, frozenset[str]]
    first_levels: tuple[str, ...]

    def options(self) -> list[dict[str, object]]:
        return [
            {
                "first_level_label": first,
                "second_level_labels": sorted(self.pairs[first]),
            }
            for first in self.first_levels
        ]


@dataclass(frozen=True)
class LabelValidation:
    """Normalised label pair plus its validation status.

    ``status`` is one of ``empty`` / ``first_only`` / ``pair`` / ``invalid``.
    Invalid labels keep the raw values so the UI can show what came from the
    report instead of silently treating them as unclassified.
    """

    first_level_label: str | None
    second_level_label: str | None
    status: str
    error: str | None = None
    taxonomy_version: str | None = None

    @property
    def valid(self) -> bool:
        return self.status != "invalid"


def taxonomy_path() -> Path | None:
    """Locate the dictionary in source, container/host and RPM layouts."""
    override = (os.environ.get("WITTY_LABEL_TAXONOMY_FILE") or "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    source_root = Path(__file__).resolve().parents[4]
    candidates.append(source_root / TAXONOMY_RELATIVE_PATH)
    witty_dir = Path(os.environ.get("WITTY_DIR") or "/var/witty-ub")
    candidates.append(witty_dir / TAXONOMY_DEPLOY_RELATIVE_PATH)
    opencode_dir = (os.environ.get("OPENCODE_CONFIG_DIR") or "").strip()
    if opencode_dir:
        candidates.append(
            Path(opencode_dir)
            / "skills"
            / "diagnostic-report-generation"
            / "references"
            / "log_label.json"
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_taxonomy() -> Taxonomy:
    path = taxonomy_path()
    if path is None:
        raise TaxonomyError("label_taxonomy_missing")
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        raise TaxonomyError("label_taxonomy_unreadable") from exc
    cached = _TAXONOMY_CACHE.get(str(path))
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TaxonomyError("label_taxonomy_invalid") from exc
    pairs: dict[str, set[str]] = {}
    if isinstance(payload, dict):
        for domain, components in payload.items():
            if not isinstance(components, dict):
                raise TaxonomyError("label_taxonomy_invalid")
            for component, types in components.items():
                if not isinstance(types, list) or not all(_known_label(value) for value in types):
                    raise TaxonomyError("label_taxonomy_invalid")
                for fault_type in types:
                    family = _model_label(domain, component, fault_type)
                    pairs.setdefault(family, set()).add(fault_type)
    elif isinstance(payload, list):
        # Keep support for two-level dictionaries supplied by existing installations.
        for item in payload:
            if not isinstance(item, dict):
                raise TaxonomyError("label_taxonomy_invalid")
            first = _known_label(item.get("component", item.get("first_level_label")))
            second = _known_label(item.get("type", item.get("second_level_label")))
            if first is None or second is None:
                raise TaxonomyError("label_taxonomy_invalid")
            pairs.setdefault(first, set()).add(second)
    if not pairs:
        raise TaxonomyError("label_taxonomy_invalid")

    taxonomy = Taxonomy(
        path=path,
        version=hashlib.sha256(path.read_bytes()).hexdigest(),
        pairs={first: frozenset(values) for first, values in pairs.items()},
        first_levels=tuple(sorted(pairs)),
    )
    _TAXONOMY_CACHE[str(path)] = (mtime, taxonomy)
    return taxonomy


def fault_case_labels(fault: dict) -> tuple[object, object]:
    """Read historical case labels or derive case-matching classes from report fields."""
    conclusion = fault.get("conclusion")
    if not isinstance(conclusion, dict):
        return None, None
    if "domain" in conclusion:
        return conclusion.get("component"), conclusion.get("type")
    if "fault_type" not in conclusion:
        return conclusion.get("first_level_label"), conclusion.get("second_level_label")
    domain = conclusion.get("fault_domain")
    if not isinstance(domain, str) or not domain:
        return None, None
    component = conclusion.get("fault_component")
    fault_type = conclusion["fault_type"]
    if isinstance(fault_type, str) and isinstance(component, str):
        return _model_label(domain, component, fault_type), fault_type
    matching = fault.get("label_matching")
    decision = matching.get("decision") if isinstance(matching, dict) else None
    if isinstance(decision, dict) and isinstance(decision.get("label"), str):
        return decision["label"], None
    if domain == "硬件故障":
        return domain, None
    if component in ("URMA故障", "UDMA故障", "UB管控面故障", "亚健康故障", "误操作故障", "用户相关故障"):
        return component, None
    return None, None


def _known_label(value: object) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        if value and value.lower() != "null":
            return value
    return None


def _validate_raw_label(value: object) -> tuple[str | None, str | None]:
    """Return ``(label, error)``; ``None`` means the field is absent/null."""
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "not_string"
    stripped = value.strip()
    if not stripped or stripped.lower() == "null":
        return None, "empty_or_null_string"
    return stripped, None


def validate_labels(first: object, second: object) -> LabelValidation:
    """Validate a report fault label pair against the current dictionary."""
    taxonomy = load_taxonomy()
    first_value, first_error = _validate_raw_label(first)
    second_value, second_error = _validate_raw_label(second)
    if first_error or second_error:
        return LabelValidation(
            first_value,
            second_value,
            "invalid",
            first_error or second_error,
            taxonomy.version,
        )
    if first_value is None and second_value is None:
        return LabelValidation(None, None, "empty", None, taxonomy.version)
    if first_value is None:
        return LabelValidation(
            None, second_value, "invalid", "second_without_first", taxonomy.version
        )
    if first_value not in taxonomy.pairs:
        return LabelValidation(
            first_value,
            second_value,
            "invalid",
            "unknown_first_level_label",
            taxonomy.version,
        )
    if second_value is None:
        return LabelValidation(
            first_value, None, "first_only", None, taxonomy.version
        )
    if second_value not in taxonomy.pairs[first_value]:
        return LabelValidation(
            first_value,
            second_value,
            "invalid",
            "unknown_label_pair",
            taxonomy.version,
        )
    return LabelValidation(
        first_value, second_value, "pair", None, taxonomy.version
    )


def label_snapshot_hash(
    first: str | None, second: str | None, taxonomy_version: str
) -> str:
    payload = json.dumps(
        {
            "first_level_label": first,
            "second_level_label": second,
            "taxonomy_version": taxonomy_version,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def label_options() -> dict[str, object]:
    taxonomy = load_taxonomy()
    return {
        "version": taxonomy.version,
        "first_level_labels": list(taxonomy.first_levels),
        "pairs": taxonomy.options(),
    }
