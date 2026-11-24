#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按「场景关键词」对 *_app 目录去重：每类只保留一个采样 -> *_app_simp。

规则
----
1) 输入目录：与脚本并列的 ci_yxh_new_app、yxh_new_app（--base-dir 可覆盖）。
2) 分组：任务目录名去掉末尾时间戳（_YYYYMMDD_HH_MM_SS）得到「场景关键词」，
   同一场景关键词的多次运行归为一类。
3) 每类保留一个采样，默认按任务名排序取第一个（--keep first|last|largest 可改）。
4) 输出：保留的整个任务目录原样复制到 <输入名>_app_simp/<原任务名>/...（结构不变）。
5) 文件排除：命中的文件不复制、其余日志照常收集；默认排除 *_ubse.log
   （FILE_EXCLUDE_PATTERNS，可用 --exclude 追加 glob 模式）。
6) 幂等：目标已存在同名文件则跳过；不删除、不覆盖。
7) 输入目录的顶层文件（如 _manifest.json）不处理。

放置与运行
----------
把本脚本放到 ci_yxh_new_app 与 yxh_new_app「并列」的目录下，直接 `python simplify_app_dirs.py`。

示例
----
  python simplify_app_dirs.py                 # 默认按名字取第一个
  python simplify_app_dirs.py --dry-run       # 只统计不落盘
  python simplify_app_dirs.py --keep largest  # 每类保留体积最大的采样
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil

# (输入 *_app 目录, 输出 *_app_simp 目录)，均相对于脚本所在目录
JOBS = [
    ("ci_yxh_new_app", "ci_yxh_new_app_simp"),
    ("yxh_new_app", "yxh_new_app_simp"),
]
# 任务名末尾时间戳，如 _20261019_21_10_38
TS_RE = re.compile(r"_\d{8}_\d{2}_\d{2}_\d{2}$")
# 复制时排除的文件（glob，大小写不敏感）；默认排除 ubse 日志，其余日志照常收集
FILE_EXCLUDE_PATTERNS: list[str] = ["*_ubse.log"]


def _log(msg: str) -> None:
    print(msg, flush=True)


def scene_of(name: str) -> str:
    """任务目录名 -> 场景关键词（去掉末尾时间戳）。"""
    return TS_RE.sub("", name.strip().rstrip("/"))


def is_excluded(filename: str) -> bool:
    """文件名是否命中排除模式（glob，大小写不敏感）。"""
    low = filename.lower()
    return any(fnmatch.fnmatch(low, p.lower()) for p in FILE_EXCLUDE_PATTERNS)


def dir_size(path: str) -> int:
    """目录内所有文件的字节总量（用于 --keep largest）。"""
    total = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def pick(names: list[str], keep: str, src_root: str) -> str:
    """在一类任务名中选出要保留的那个。"""
    names = sorted(names)
    if keep == "last":
        return names[-1]
    if keep == "largest":
        return max(names, key=lambda n: (dir_size(os.path.join(src_root, n)), n))
    return names[0]  # first


def simplify(src_root: str, dst_root: str, keep: str, dry_run: bool) -> tuple[dict, list]:
    """对一个 *_app 去重。返回 (统计, 计划[scene, kept, dropped])。"""
    stat = {"tasks_total": 0, "groups": 0, "kept": 0, "dropped": 0,
            "files_copied": 0, "files_skipped_exists": 0, "files_skipped_excluded": 0}
    plan: list = []
    if not os.path.isdir(src_root):
        _log(f"[跳过] 输入目录不存在: {src_root}")
        return stat, plan

    groups: dict[str, list[str]] = {}
    for entry in sorted(os.listdir(src_root)):
        if entry.startswith("."):
            continue
        if not os.path.isdir(os.path.join(src_root, entry)):
            continue
        stat["tasks_total"] += 1
        groups.setdefault(scene_of(entry), []).append(entry)

    for scene in sorted(groups):
        names = groups[scene]
        chosen = pick(names, keep, src_root)
        dropped = sorted(n for n in names if n != chosen)
        plan.append((scene, chosen, dropped))
        stat["kept"] += 1
        stat["dropped"] += len(dropped)
    stat["groups"] = len(plan)

    for _scene, chosen, _dropped in plan:
        for dp, dns, fns in os.walk(os.path.join(src_root, chosen)):
            dns[:] = [d for d in dns if not d.startswith(".")]
            rel = os.path.relpath(dp, src_root)  # 含任务名，保持路径结构
            for fn in sorted(fns):
                if fn.startswith("."):
                    continue
                if is_excluded(fn):
                    stat["files_skipped_excluded"] += 1
                    continue
                dst_file = os.path.join(dst_root, rel, fn)
                if os.path.exists(dst_file):
                    stat["files_skipped_exists"] += 1
                    continue
                stat["files_copied"] += 1
                if dry_run:
                    continue
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(os.path.join(src_root, rel, fn), dst_file)
    return stat, plan


def main() -> None:
    ap = argparse.ArgumentParser(description="按场景关键词对 *_app 去重 -> *_app_simp")
    ap.add_argument("--base-dir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="输入/输出目录的父目录（默认=脚本所在目录）")
    ap.add_argument("--keep", choices=["first", "last", "largest"], default="first",
                    help="每类保留哪个采样（默认 first：按名字排序取第一个）")
    ap.add_argument("--exclude", action="append", default=[],
                    help="追加不收集的文件名 glob 模式（默认已排除 *_ubse.log），可多次指定")
    ap.add_argument("--dry-run", action="store_true", help="只统计不落盘")
    args = ap.parse_args()

    global FILE_EXCLUDE_PATTERNS
    FILE_EXCLUDE_PATTERNS = FILE_EXCLUDE_PATTERNS + list(args.exclude)
    _log(f"[配置] 文件排除模式={FILE_EXCLUDE_PATTERNS}  每类保留={args.keep}")

    grand = {"kept": 0, "dropped": 0, "files_copied": 0, "files_skipped_excluded": 0}
    for src_name, dst_name in JOBS:
        src_root = os.path.join(args.base_dir, src_name)
        dst_root = os.path.join(args.base_dir, dst_name)
        _log(f"\n===== {src_name} -> {dst_name} =====")
        st, plan = simplify(src_root, dst_root, args.keep, args.dry_run)
        _log(f"  任务 {st['tasks_total']} 个 -> 场景类 {st['groups']} 个，"
             f"保留 {st['kept']}，丢弃 {st['dropped']}")
        _log(f"  文件：复制 {st['files_copied']}，跳过(目标已存在) {st['files_skipped_exists']}，"
             f"排除 {st['files_skipped_excluded']}"
             + ("   [dry-run 未落盘]" if args.dry_run else ""))
        if not args.dry_run and plan:
            os.makedirs(dst_root, exist_ok=True)
            manifest = os.path.join(dst_root, "_simp_manifest.json")
            with open(manifest, "w", encoding="utf-8") as fh:
                json.dump({"src_root": src_root, "keep": args.keep,
                           "file_exclude_patterns": FILE_EXCLUDE_PATTERNS,
                           "groups": [{"scene": s, "kept": c, "dropped": d}
                                      for s, c, d in plan]},
                          fh, ensure_ascii=False, indent=1)
        grand["kept"] += st["kept"]
        grand["dropped"] += st["dropped"]
        grand["files_copied"] += st["files_copied"]
        grand["files_skipped_excluded"] += st["files_skipped_excluded"]
    _log(f"\n[完成] 保留 {grand['kept']} 类（丢弃 {grand['dropped']} 个重复任务），"
         f"复制 {grand['files_copied']} 个文件、排除 {grand['files_skipped_excluded']} 个。"
         + ("（dry-run，未写入磁盘）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
