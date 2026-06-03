#!/usr/bin/env python3
"""
TraceID 搜索测试脚本
用于验证日志文件中是否包含特定的 traceid

使用方法:
python test_traceid_search.py <日志目录> <traceid>

示例:
python test_traceid_search.py /path/to/logs 550e8400-e29b-41d4-a716-446655440000
"""

import os
import sys
import argparse

# 设置 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from latency.parse.worker_access_log_parser import WorkerAccessLogParser
from latency.parse.urma_log_parser import UrmaLogParser
from latency.parse.remote_pull_log_parser import RemotePullLogParser
from latency.parse.sdk_access_log_parser import SdkAccessLogParser


def search_traceid_in_logs(log_dir: str, target_traceid: str):
    """在日志目录中搜索指定的 traceid"""
    print(f"搜索 traceid: {target_traceid}")
    print(f"日志目录: {log_dir}")
    print("=" * 80)
    
    # 初始化解析器
    parsers = [
        ("Worker Access", WorkerAccessLogParser()),
        ("URMA", UrmaLogParser()),
        ("Remote Pull", RemotePullLogParser()),
        ("SDK Access", SdkAccessLogParser()),
    ]
    
    found_entries = []
    
    for parser_name, parser in parsers:
        print(f"\n[{parser_name}] 开始解析...")
        
        try:
            # 解析日志
            entries = parser.parse(log_dir)
            print(f"  解析到 {len(entries)} 条日志")
            
            # 搜索 traceid
            matches = [e for e in entries if e.trace_id == target_traceid]
            
            if matches:
                print(f"  ✅ 找到 {len(matches)} 条匹配的日志:")
                for i, entry in enumerate(matches[:3], 1):  # 最多显示3条
                    print(f"    [{i}] 时间: {entry.timestamp}, 类型: {entry.entry_type}")
                    print(f"        对象: {entry.object_key}")
                    print(f"        Pod IP: {entry.pod_ip}")
                    found_entries.extend(matches)
            else:
                print(f"  ❌ 未找到匹配的日志")
                
        except Exception as e:
            print(f"  ⚠️  解析失败: {e}")
    
    print("\n" + "=" * 80)
    
    if found_entries:
        print(f"搜索完成！共找到 {len(found_entries)} 条包含 traceid '{target_traceid}' 的日志")
        return True
    else:
        print(f"搜索完成！未找到包含 traceid '{target_traceid}' 的日志")
        return False


def extract_traceids_from_logs(log_dir: str, limit: int = 10):
    """从日志中提取前 N 个 traceid"""
    print(f"从日志目录提取 traceid: {log_dir}")
    print("=" * 80)
    
    parsers = [
        ("Worker Access", WorkerAccessLogParser()),
        ("URMA", UrmaLogParser()),
        ("Remote Pull", RemotePullLogParser()),
        ("SDK Access", SdkAccessLogParser()),
    ]
    
    all_traceids = []
    
    for parser_name, parser in parsers:
        print(f"\n[{parser_name}] 解析中...")
        
        try:
            entries = parser.parse(log_dir)
            traceids = [e.trace_id for e in entries if e.trace_id][:limit]
            all_traceids.extend([(parser_name, t) for t in traceids])
            
            print(f"  提取到 {len(traceids)} 个 traceid:")
            for tid in traceids:
                print(f"    {tid}")
                
        except Exception as e:
            print(f"  ⚠️  解析失败: {e}")
    
    return all_traceids


def main():
    parser = argparse.ArgumentParser(description="TraceID 搜索测试脚本")
    parser.add_argument("log_dir", help="日志目录路径")
    parser.add_argument("traceid", nargs="?", help="要搜索的 traceid（可选）")
    parser.add_argument("--extract", action="store_true", help="提取日志中的 traceid")
    parser.add_argument("--limit", type=int, default=10, help="提取 traceid 的数量限制")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.log_dir):
        print(f"错误: {args.log_dir} 不是有效的目录")
        sys.exit(1)
    
    if args.extract:
        # 提取模式
        extract_traceids_from_logs(args.log_dir, args.limit)
    elif args.traceid:
        # 搜索模式
        search_traceid_in_logs(args.log_dir, args.traceid)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
