#!/usr/bin/env python3
"""
TraceID 快速搜索脚本（优化版）
直接读取日志文件，不使用完整解析器，适合大日志文件

支持 .gz 压缩文件

使用方法:
python test_traceid_search_fast.py <日志目录或文件> <traceid>

示例:
python test_traceid_search_fast.py /path/to/logs 550e8400-e29b-41d4-a716-446655440000
python test_traceid_search_fast.py /path/to/logs/access.log 550e8400-e29b-41d4-a716-446655440000
python test_traceid_search_fast.py /path/to/logs/access.log.gz 550e8400-e29b-41d4-a716-446655440000
"""

import os
import sys
import re
import gzip
import argparse
from pathlib import Path

# UUID 格式的 traceid 正则表达式
UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

# 从项目配置中提取的日志文件模式
LOG_FILE_PATTERNS = [
    # SDK Access
    "SDK_*/ds_client_access_*.log",
    "SDK_*/ds_client_access_*.log.gz",
    "SDK_*/ds_client.log",
    "SDK_*/ds_client.log.gz",
    "SDK_*/ds_client_access.log",
    "SDK_*/ds_client_access.*.log.gz",
    # Worker Access
    "*Worker_*/access.log",
    "*Worker_*/access.log.gz",
    # URMA / Remote Pull / Link / Query Meta
    "*Worker_*/datasystem_worker.INFO.*",
    "*Worker_*/datasystem_worker.INFO.*.gz",
    "*Worker_*/kvcache.INFO.*",
    "*Worker_*/kvcache.INFO.*.gz",
]


def open_log(path: str):
    """打开日志文件（支持 .gz 压缩）"""
    if path.endswith(".gz"):
        try:
            return gzip.open(path, "rt", encoding="utf-8")
        except OSError as e:
            print(f"  ⚠️  解压失败: {e}")
            return None
    return open(path, "r", encoding="utf-8", errors="replace")


def find_log_files(search_path: str) -> list[str]:
    """查找日志文件"""
    path = Path(search_path)
    files = []
    
    if path.is_file():
        # 如果是文件，直接返回
        files.append(str(path))
    elif path.is_dir():
        # 如果是目录，查找所有匹配的日志文件
        for pattern in LOG_FILE_PATTERNS:
            try:
                found = list(path.rglob(pattern))
                files.extend([str(f) for f in found if f.is_file()])
            except Exception:
                pass
        
        # 去重
        files = list(set(files))
    
    # 按文件名排序
    files.sort()
    return files


def search_traceid_in_file(file_path: str, target_traceid: str, show_lines: bool = True, context_lines: int = 0) -> int:
    """在单个文件中搜索 traceid"""
    matches = []
    target_lower = target_traceid.lower()
    
    fh = open_log(file_path)
    if fh is None:
        return 0
    
    try:
        with fh:
            lines = fh.readlines()
            total_lines = len(lines)
            
            for i, line in enumerate(lines):
                if target_lower in line.lower():
                    matches.append((i + 1, line))
    
    except Exception as e:
        print(f"  ⚠️  读取文件失败: {e}")
        return 0
    
    if matches:
        print(f"  ✅ 找到 {len(matches)} 处匹配")
        if show_lines:
            for line_num, line in matches[:5]:  # 最多显示5条
                print(f"    行 {line_num}: {line[:150]}...")
            if len(matches) > 5:
                print(f"    ... 还有 {len(matches) - 5} 条匹配")
    
    return len(matches)


def extract_all_traceids(file_path: str, limit: int = 10) -> list[str]:
    """从文件中提取所有 traceid"""
    traceids = []
    
    fh = open_log(file_path)
    if fh is None:
        return []
    
    try:
        with fh:
            for line in fh:
                found = UUID_PATTERN.findall(line)
                for tid in found:
                    if tid not in traceids:
                        traceids.append(tid)
                        if len(traceids) >= limit:
                            return traceids
    except Exception as e:
        print(f"  ⚠️  读取文件失败: {e}")
    
    return traceids


def main():
    parser = argparse.ArgumentParser(description="TraceID 快速搜索脚本（优化版）")
    parser.add_argument("path", help="日志目录或文件路径")
    parser.add_argument("traceid", nargs="?", help="要搜索的 traceid（可选）")
    parser.add_argument("--extract", action="store_true", help="提取日志中的所有 traceid")
    parser.add_argument("--limit", type=int, default=10, help="提取 traceid 的数量限制")
    parser.add_argument("--quiet", action="store_true", help="静默模式，只显示结果统计")
    
    args = parser.parse_args()
    
    # 检查路径是否存在
    if not os.path.exists(args.path):
        print(f"错误: {args.path} 不存在")
        sys.exit(1)
    
    # 查找日志文件
    log_files = find_log_files(args.path)
    
    if not log_files:
        print("未找到日志文件")
        sys.exit(1)
    
    print(f"找到 {len(log_files)} 个日志文件")
    if not args.quiet:
        for f in log_files:
            print(f"  - {f}")
    print("=" * 80)
    
    if args.extract:
        # 提取模式
        print("提取 traceid...")
        all_traceids = []
        file_results = []  # 记录每个文件的结果
        
        for file_path in log_files:
            if not args.quiet:
                print(f"\n[{os.path.basename(file_path)}]")
            
            traceids = extract_all_traceids(file_path, args.limit - len(all_traceids))
            all_traceids.extend(traceids)
            file_results.append((file_path, len(traceids)))
            
            if not args.quiet:
                if traceids:
                    print(f"  提取到 {len(traceids)} 个 traceid")
                    for tid in traceids:
                        print(f"    {tid}")
                else:
                    print(f"  未找到 traceid")
            
            if len(all_traceids) >= args.limit:
                break
        
        # 打印汇总结果
        unique_traceids = list(set(all_traceids))
        files_with_traceids = sum(1 for _, count in file_results if count > 0)
        files_without_traceids = len(file_results) - files_with_traceids
        
        print("\n" + "=" * 80)
        print("📊 提取汇总结果")
        print("=" * 80)
        print(f"总文件数: {len(file_results)}")
        print(f"包含 traceid 的文件数: {files_with_traceids}")
        print(f"不包含 traceid 的文件数: {files_without_traceids}")
        print(f"提取的 traceid 总数: {len(all_traceids)}")
        print(f"唯一 traceid 数量: {len(unique_traceids)}")
        print("-" * 80)
        print("文件提取详情:")
        for file_path, count in file_results:
            status = f"✅ {count} 个 traceid" if count > 0 else "❌ 未找到"
            print(f"  {status} | {file_path}")
        if unique_traceids:
            print("-" * 80)
            print("所有唯一 traceid:")
            for tid in unique_traceids:
                print(f"    {tid}")
        print("=" * 80)
        
    elif args.traceid:
        # 搜索模式
        print(f"搜索 traceid: {args.traceid}")
        total_matches = 0
        matched_files = 0
        unmatched_files = 0
        file_results = []  # 记录每个文件的结果
        
        for file_path in log_files:
            if not args.quiet:
                print(f"\n[{os.path.basename(file_path)}]")
            
            matches = search_traceid_in_file(file_path, args.traceid, show_lines=not args.quiet)
            
            if matches > 0:
                matched_files += 1
                total_matches += matches
                file_results.append((file_path, matches))
            else:
                unmatched_files += 1
                file_results.append((file_path, 0))
        
        # 打印汇总结果
        print("\n" + "=" * 80)
        print("📊 搜索汇总结果")
        print("=" * 80)
        print(f"总文件数: {len(log_files)}")
        print(f"匹配文件数: {matched_files}")
        print(f"未匹配文件数: {unmatched_files}")
        print(f"总匹配次数: {total_matches}")
        print("-" * 80)
        print("文件匹配详情:")
        for file_path, count in file_results:
            if count > 0:
                print(f"  ✅ {count} 处匹配 | {file_path}")
        print("=" * 80)
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
