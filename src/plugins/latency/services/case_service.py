# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case library service: create, list, delete cases with automatic feature extraction."""
from __future__ import annotations

import os
import json
import re
import uuid
from datetime import datetime

from latency.services.feature_extraction import FeatureExtractionManager

WITTY_DIR = os.getenv("WITTY_DIR", "/var/witty-ub")
CASE_DIR = os.path.join(WITTY_DIR, "case")
CATEGORIES_FILE = os.path.join(CASE_DIR, "_categories.json")

# 根因类型提取正则：去掉 lingqu_kvcache_ 前缀和 _NNN_YYYYMMDD_HH_MM_SS 后缀
RC_PATTERN = re.compile(r"^lingqu_kvcache_(.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$")


class CaseServiceManager:
    """Case library business logic: create / list / delete cases."""

    @staticmethod
    def extract_root_cause_type(name: str) -> str:
        """从日志文件名提取根因类型"""
        m = RC_PATTERN.match(name)
        return m.group(1) if m else name

    @staticmethod
    def ensure_case_dir():
        os.makedirs(CASE_DIR, exist_ok=True)

    @staticmethod
    async def create_case(
        kb_id: str = "",
        root_cause_type: str = "",
        description: str = "",
        task_ids: list | None = None,
        task_names: list | None = None,
        log_file_id: str = "",
        log_file_name: str = "",
        attachment_path: str | None = None,
        case_category: str = "",
    ) -> dict:
        """Create a case with automatic feature extraction and persist to JSON.

        Returns the case_record dict.
        """
        CaseServiceManager.ensure_case_dir()

        if not root_cause_type:
            raise ValueError("root_cause_type 为必填项")

        case_id = str(uuid.uuid4())

        # 自动提取特征
        features = None
        fault_category = None
        if log_file_id:
            try:
                features = await FeatureExtractionManager.extract_features(log_file_id)
                fault_category = features.get("fault_category") if features else None
            except Exception as e:
                print(f"[WARN] 特征提取失败 log_file_id={log_file_id}: {e}")
                features = None
                fault_category = None

        # 如果 root_cause_type 是 __auto__，从文件名提取
        if root_cause_type == "__auto__" and log_file_name:
            root_cause_type = CaseServiceManager.extract_root_cause_type(log_file_name)

        case_record = {
            "id": case_id,
            "kb_id": kb_id,
            "root_cause_type": root_cause_type,
            "description": description,
            "task_ids": task_ids or [],
            "task_names": task_names or [],
            "log_file_id": log_file_id,
            "log_file_name": log_file_name,
            "attachment_path": attachment_path,
            "fault_category": fault_category,
            "case_category": case_category,
            "features": features,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 写入 JSON
        json_path = os.path.join(CASE_DIR, f"{case_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(case_record, f, ensure_ascii=False, indent=2)

        return case_record

    @staticmethod
    def list_cases() -> list[dict]:
        """List all cases from CASE_DIR."""
        CaseServiceManager.ensure_case_dir()
        cases = []
        for filename in os.listdir(CASE_DIR):
            if filename.endswith(".json") and not filename.startswith("_"):
                json_path = os.path.join(CASE_DIR, filename)
                with open(json_path, "r", encoding="utf-8") as f:
                    cases.append(json.load(f))
        return cases

    @staticmethod
    def delete_case(case_id: str) -> bool:
        """Delete a case by case_id. Returns True if deleted."""
        CaseServiceManager.ensure_case_dir()
        json_path = os.path.join(CASE_DIR, f"{case_id}.json")
        if not os.path.exists(json_path):
            return False

        with open(json_path, "r", encoding="utf-8") as f:
            case_record = json.load(f)

        attachment_path = case_record.get("attachment_path")
        if attachment_path:
            att_file = os.path.join(CASE_DIR, attachment_path)
            if os.path.exists(att_file):
                os.remove(att_file)

        os.remove(json_path)
        return True

    @staticmethod
    def update_case(case_id: str, case_category: str | None = None, root_cause_type: str | None = None) -> dict | None:
        """Update a case's case_category and/or root_cause_type. Returns updated case or None.
        Also syncs _categories.json: creates missing categories and types."""
        CaseServiceManager.ensure_case_dir()
        json_path = os.path.join(CASE_DIR, f"{case_id}.json")
        if not os.path.exists(json_path):
            return None

        with open(json_path, "r", encoding="utf-8") as f:
            case_record = json.load(f)

        old_category = case_record.get("case_category", "")
        old_type = case_record.get("root_cause_type", "")
        changed = False
        if case_category is not None and case_category != old_category:
            case_record["case_category"] = case_category
            changed = True
        if root_cause_type is not None and root_cause_type != old_type:
            case_record["root_cause_type"] = root_cause_type
            changed = True

        if changed:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(case_record, f, ensure_ascii=False, indent=2)

        # Always sync _categories.json (even if unchanged, type might be missing from meta)
        new_category = case_category if case_category is not None else old_category
        new_type = root_cause_type if root_cause_type is not None else old_type
        CaseServiceManager._sync_categories_meta(new_category, new_type, old_category, old_type)

        return case_record

    @staticmethod
    def _sync_categories_meta(new_category: str, new_type: str, old_category: str, old_type: str) -> None:
        """Ensure _categories.json contains the new category and type. Create if missing.
        Also clean up: if old_type no longer has any cases, remove it from meta."""
        if not new_category and not new_type:
            return

        meta = CaseServiceManager._load_categories_meta()
        categories = meta["categories"]
        types = meta["types"]
        dirty = False

        # Ensure new category exists
        cat_id = None
        if new_category:
            for cat in categories:
                if cat["name"] == new_category:
                    cat_id = cat["id"]
                    break
            if not cat_id:
                cat_id = str(uuid.uuid4())
                categories.append({
                    "id": cat_id,
                    "name": new_category,
                    "description": "",
                    "sort_order": len(categories),
                })
                dirty = True

        # Ensure new type exists under the category
        if new_type and cat_id:
            type_exists = any(t["name"] == new_type and t["category_id"] == cat_id for t in types)
            if not type_exists:
                # Find next sort_order for this category
                cat_types = [t for t in types if t.get("category_id") == cat_id]
                next_order = max((t.get("sort_order", 0) for t in cat_types), default=0) + 1
                types.append({
                    "id": str(uuid.uuid4()),
                    "category_id": cat_id,
                    "name": new_type,
                    "description": "",
                    "sort_order": next_order,
                })
                dirty = True

        # Clean up: if old type no longer has any cases, remove it from meta
        type_counts = CaseServiceManager._type_case_counts()
        if old_type and old_type != new_type:
            if type_counts.get(old_type, 0) == 0:
                types[:] = [t for t in types if t["name"] != old_type]
                dirty = True

        # Clean up: if old category no longer has any cases, remove it from meta
        if old_category and old_category != new_category:
            old_cat_types = [t for t in types if any(
                c.get("case_category") == old_category for c in CaseServiceManager.list_cases()
                for _ in [None] if c.get("root_cause_type") == t["name"]
            )]
            # Simpler: check if any case still uses old_category
            has_cases = any(
                c.get("case_category") == old_category
                for c in CaseServiceManager.list_cases()
            )
            if not has_cases:
                # Remove category and its types
                old_cat_id = next((cat["id"] for cat in categories if cat["name"] == old_category), None)
                if old_cat_id:
                    categories[:] = [cat for cat in categories if cat["id"] != old_cat_id]
                    types[:] = [t for t in types if t.get("category_id") != old_cat_id]
                    dirty = True

        if dirty:
            CaseServiceManager._save_categories_meta(meta)

    @staticmethod
    def delete_cases_by_type(root_cause_type: str) -> int:
        """Delete all cases with the given root_cause_type. Returns deleted count."""
        CaseServiceManager.ensure_case_dir()
        deleted_count = 0
        for filename in os.listdir(CASE_DIR):
            if not filename.endswith(".json") or filename.startswith("_"):
                continue
            json_path = os.path.join(CASE_DIR, filename)
            with open(json_path, "r", encoding="utf-8") as f:
                case_record = json.load(f)

            if case_record.get("root_cause_type") == root_cause_type:
                attachment_path = case_record.get("attachment_path")
                if attachment_path:
                    att_file = os.path.join(CASE_DIR, attachment_path)
                    if os.path.exists(att_file):
                        os.remove(att_file)
                os.remove(json_path)
                deleted_count += 1
        return deleted_count

    @staticmethod
    def find_existing_case_by_log_name(log_file_name: str) -> str | None:
        """Check if a case already exists for the given log_file_name. Returns case_id or None."""
        if not os.path.isdir(CASE_DIR):
            return None
        for filename in os.listdir(CASE_DIR):
            if not filename.endswith(".json") or filename.startswith("_"):
                continue
            fpath = os.path.join(CASE_DIR, filename)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("log_file_name") == log_file_name:
                    return data.get("id")
            except (json.JSONDecodeError, OSError):
                continue
        return None

    # ------------------------------------------------------------------
    # 故障大类 / 故障类型 元数据管理
    # ------------------------------------------------------------------

    @staticmethod
    def _load_categories_meta() -> dict:
        """加载 _categories.json，不存在时返回空结构。"""
        CaseServiceManager.ensure_case_dir()
        if not os.path.exists(CATEGORIES_FILE):
            return {"categories": [], "types": []}
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("categories", [])
            data.setdefault("types", [])
            return data
        except (json.JSONDecodeError, OSError):
            return {"categories": [], "types": []}

    @staticmethod
    def _save_categories_meta(data: dict) -> None:
        CaseServiceManager.ensure_case_dir()
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _type_case_counts() -> dict[str, int]:
        """统计每种 root_cause_type 的案例数量。"""
        counts: dict[str, int] = {}
        for c in CaseServiceManager.list_cases():
            t = c.get("root_cause_type", "")
            if t:
                counts[t] = counts.get(t, 0) + 1
        return counts

    @staticmethod
    def list_categories_with_types() -> list[dict]:
        """返回所有分类及其故障类型（含案例数量），未纳入元数据的类型归入'未分类'。"""
        meta = CaseServiceManager._load_categories_meta()
        type_counts = CaseServiceManager._type_case_counts()

        categories = sorted(
            meta["categories"],
            key=lambda x: (x.get("sort_order", 0), x.get("name", "")),
        )
        all_types = meta["types"]

        result = []
        for cat in categories:
            cat_types = sorted(
                [t for t in all_types if t.get("category_id") == cat["id"]],
                key=lambda x: (x.get("sort_order", 0), x.get("name", "")),
            )
            type_list = []
            cat_total = 0
            for t in cat_types:
                count = type_counts.get(t["name"], 0)
                cat_total += count
                type_list.append({
                    "id": t["id"],
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "case_count": count,
                })
            result.append({
                "id": cat["id"],
                "name": cat["name"],
                "description": cat.get("description", ""),
                "types": type_list,
                "case_count": cat_total,
            })

        # 未分类：存在于案例中但未纳入元数据的 root_cause_type
        known_names = {t["name"] for t in all_types}
        uncategorized = []
        uncategorized_total = 0
        for tname, count in sorted(type_counts.items()):
            if tname not in known_names:
                uncategorized.append({"name": tname, "case_count": count})
                uncategorized_total += count
        if uncategorized:
            result.append({
                "id": "__uncategorized__",
                "name": "未分类",
                "description": "",
                "types": uncategorized,
                "case_count": uncategorized_total,
            })

        return result

    @staticmethod
    def create_category(name: str, description: str = "") -> dict:
        meta = CaseServiceManager._load_categories_meta()
        cat_id = str(uuid.uuid4())
        sort_order = len(meta["categories"])
        cat = {"id": cat_id, "name": name, "description": description, "sort_order": sort_order}
        meta["categories"].append(cat)
        CaseServiceManager._save_categories_meta(meta)
        return cat

    @staticmethod
    def update_category(cat_id: str, name: str | None = None, description: str | None = None) -> dict | None:
        meta = CaseServiceManager._load_categories_meta()
        for cat in meta["categories"]:
            if cat["id"] == cat_id:
                if name is not None:
                    cat["name"] = name
                if description is not None:
                    cat["description"] = description
                CaseServiceManager._save_categories_meta(meta)
                return cat
        return None

    @staticmethod
    def delete_category(cat_id: str, recursive: bool = False) -> bool:
        meta = CaseServiceManager._load_categories_meta()
        # 找到该大类下的所有类型
        child_types = [t for t in meta["types"] if t.get("category_id") == cat_id]
        if child_types and not recursive:
            type_names = ", ".join(t["name"] for t in child_types)
            raise ValueError(f"该分类下还有故障类型（{type_names}），无法删除。请先删除子类型或使用递归删除。")

        if recursive:
            # 递归删除：先删除所有子类型对应的案例，再删除类型
            for t in child_types:
                CaseServiceManager.delete_cases_by_type(t["name"])
            meta["types"] = [t for t in meta["types"] if t.get("category_id") != cat_id]

        meta["categories"] = [c for c in meta["categories"] if c["id"] != cat_id]
        CaseServiceManager._save_categories_meta(meta)
        return True

    @staticmethod
    def create_type(category_id: str, name: str, description: str = "") -> dict:
        meta = CaseServiceManager._load_categories_meta()
        if not any(c["id"] == category_id for c in meta["categories"]):
            raise ValueError("指定的故障大类不存在")
        if any(t["name"] == name for t in meta["types"]):
            raise ValueError("该故障类型名称已存在")
        type_id = str(uuid.uuid4())
        existing_in_cat = [t for t in meta["types"] if t.get("category_id") == category_id]
        sort_order = len(existing_in_cat)
        t = {"id": type_id, "category_id": category_id, "name": name, "description": description, "sort_order": sort_order}
        meta["types"].append(t)
        CaseServiceManager._save_categories_meta(meta)
        return t

    @staticmethod
    def update_type(type_id: str, name: str | None = None, description: str | None = None) -> dict | None:
        meta = CaseServiceManager._load_categories_meta()
        for t in meta["types"]:
            if t["id"] == type_id:
                old_name = t.get("name")
                if name is not None:
                    t["name"] = name
                if description is not None:
                    t["description"] = description
                CaseServiceManager._save_categories_meta(meta)
                if name is not None and old_name != name:
                    CaseServiceManager._rename_type_in_cases(old_name, name)
                return t
        return None

    @staticmethod
    def _rename_type_in_cases(old_name: str, new_name: str) -> None:
        """当故障类型重命名时，同步更新已有案例的 root_cause_type。"""
        CaseServiceManager.ensure_case_dir()
        for filename in os.listdir(CASE_DIR):
            if not filename.endswith(".json") or filename.startswith("_"):
                continue
            json_path = os.path.join(CASE_DIR, filename)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    case_record = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if case_record.get("root_cause_type") == old_name:
                case_record["root_cause_type"] = new_name
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(case_record, f, ensure_ascii=False, indent=2)

    @staticmethod
    def delete_type(type_id: str, recursive: bool = False) -> bool:
        meta = CaseServiceManager._load_categories_meta()
        target = None
        for t in meta["types"]:
            if t["id"] == type_id:
                target = t
                break
        if not target:
            return False
        has_cases = any(
            c.get("root_cause_type") == target["name"]
            for c in CaseServiceManager.list_cases()
        )
        if has_cases and not recursive:
            raise ValueError("该故障类型下还有案例，无法删除。请先删除案例或使用递归删除。")

        if recursive and has_cases:
            CaseServiceManager.delete_cases_by_type(target["name"])

        meta["types"] = [t for t in meta["types"] if t["id"] != type_id]
        CaseServiceManager._save_categories_meta(meta)
        return True
