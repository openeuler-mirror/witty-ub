#!/usr/bin/env python3
"""
TraceID 快速搜索脚本（优化版）
直接读取日志文件，不使用完整解析器，适合大日志文件

使用方法:
python test_traceid_search_fast.py <日志目录或文件> <traceid>

示例:
python test_traceid_search_fast.py /path/to/logs 550e8400-e29b-41d4-a716-446655440000
python test_traceid_search_fast.py /path/to/logs/access.log 550e8400-e29b-41d4-a716-446655440000
"""

import os
import sys
import re
import argparse
from pathlib import Path

# UUID 格式的 traceid 正则表达式
UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

# 常见的日志文件模式
LOG_FILE_PATTERNS = [
    '*.log',
    '*.INFO',
    '*.INFO.*',
    'access.log',
    '*.access.log',
    'datasystem_worker*',
    'kvcache*',
    '*Worker_*/*',
]


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
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
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
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
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
        
        for file_path in log_files:
            if not args.quiet:
                print(f"\n[{os.path.basename(file_path)}]")
            
            traceids = extract_all_traceids(file_path, args.limit - len(all_traceids))
            all_traceids.extend(traceids)
            
            if not args.quiet:
                if traceids:
                    print(f"  提取到 {len(traceids)} 个 traceid")
                    for tid in traceids:
                        print(f"    {tid}")
                else:
                    print(f"  未找到 traceid")
            
            if len(all_traceids) >= args.limit:
                break
        
        print("\n" + "=" * 80)
        print(f"共提取到 {len(all_traceids)} 个唯一 traceid")
        
    elif args.traceid:
        # 搜索模式
        print(f"搜索 traceid: {args.traceid}")
        total_matches = 0
        matched_files = 0
        
        for file_path in log_files:
            if not args.quiet:
                print(f"\n[{os.path.basename(file_path)}]")
            
            matches = search_traceid_in_file(file_path, args.traceid, show_lines=not args.quiet)
            
            if matches > 0:
                matched_files += 1
                total_matches += matches
        
        print("\n" + "=" * 80)
        print(f"搜索完成！在 {matched_files} 个文件中找到 {total_matches} 处匹配")
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
