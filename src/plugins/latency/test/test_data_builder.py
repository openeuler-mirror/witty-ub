#!/usr/bin/env python3
"""
测试数据构建脚本
从CSV文件抽样traceid，从日志数据集检索相关日志，构建测试数据集

使用方法:
python test_data_builder.py <csv文件路径> <日志数据集路径> <抽样比例> <输出目录>

示例:
python test_data_builder.py data.csv /data 0.1 /test_data
"""

import os
import sys
import csv
import gzip
import random
import argparse
import re
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Set, Dict, List, Tuple
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
def extract_trace_id(line: str) -> str:
    """从行中提取trace_id"""
    match = UUID_RE.search(line)
    return match.group(0) if match else ""

def open_log(path: str):
    """打开日志文件（支持 .gz 压缩）"""
    if path.endswith(".gz"):
        try:
            return gzip.open(path, "rt", encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  ⚠️  解压失败: {e}")
            return None
    return open(path, "r", encoding="utf-8", errors="replace")


def read_traceids_from_csv(csv_path: str, delimiter: str = ',', required_cols: list = None) -> Set[str]:
    """
    从CSV文件读取traceid
    筛选条件：traceid列非空，且指定的required_cols全部非空
    
    参数:
        csv_path: CSV文件路径
        delimiter: CSV分隔符，默认逗号','
        required_cols: 需要检查非空的列索引列表，默认[3,7,9]
    """
    if required_cols is None:
        required_cols = [3, 7, 9]  # 默认D=3, H=7, J=9
    
    traceids = set()
    total_rows = 0
    skipped_no_traceid = 0
    skipped_empty_required = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            # 自动检测分隔符
            sample = f.read(1024)
            f.seek(0)
            
            if delimiter == 'auto':
                if ';' in sample and ',' not in sample:
                    delimiter = ';'
                elif '\t' in sample:
                    delimiter = '\t'
                else:
                    delimiter = ','
                print(f"🔍 自动检测到分隔符: '{delimiter}'")
            
            reader = csv.reader(f, delimiter=delimiter)
            
            try:
                headers = next(reader)  # 读取表头
            except StopIteration:
                print(f"❌ 错误: CSV文件为空")
                return traceids
            
            print(f"📋 表头内容: {headers}")
            
            # 找到traceid列的索引
            col_c = None  # traceid列
            for i, header in enumerate(headers):
                header_lower = header.lower().strip()
                if 'traceid' in header_lower or header_lower == 'c':
                    col_c = i
                    break
            
            if col_c is None:
                print(f"❌ 错误: 未找到traceid列（C列）")
                print(f"   可用列名: {[h.strip() for h in headers]}")
                return traceids
            
            # 获取需要检查的列名
            required_col_names = []
            for idx in required_cols:
                if idx < len(headers):
                    required_col_names.append(f"{idx}({headers[idx]})")
                else:
                    required_col_names.append(f"{idx}(超出范围)")
            
            print(f"📊 列索引: traceid={col_c}({headers[col_c]}), 需要检查的列={required_col_names}")
            
            # 读取数据行
            for row in reader:
                total_rows += 1
                
                if len(row) <= col_c:
                    skipped_no_traceid += 1
                    continue
                
                traceid = row[col_c].strip()
                if not traceid:
                    skipped_no_traceid += 1
                    continue
                
                # 检查指定的列是否全部非空
                all_non_empty = True
                for col_idx in required_cols:
                    if col_idx >= len(row) or not row[col_idx].strip():
                        all_non_empty = False
                        break
                
                if all_non_empty:
                    traceids.add(traceid)
                else:
                    skipped_empty_required += 1
    
    except Exception as e:
        print(f"❌ 读取CSV文件失败: {e}")
    
    print(f"\n📈 CSV读取统计:")
    print(f"   总行数: {total_rows}")
    print(f"   跳过(无traceid): {skipped_no_traceid}")
    print(f"   跳过(指定列有空值): {skipped_empty_required}")
    print(f"   有效traceid: {len(traceids)}")
    
    return traceids


def sample_traceids(traceids: Set[str], ratio: float) -> Set[str]:
    """
    从traceid集合中随机抽样
    ratio: 抽样比例（0-1）
    """
    if ratio <= 0:
        return set()
    if ratio >= 1:
        return traceids
    
    traceid_list = list(traceids)
    sample_size = max(1, int(len(traceid_list) * ratio))
    
    sampled = random.sample(traceid_list, sample_size)
    return set(sampled)


def find_log_files(log_dataset_path: str) -> List[str]:
    """
    查找日志数据集中的所有日志文件
    """
    path = Path(log_dataset_path)
    log_files = []
    
    if path.is_file():
        log_files.append(str(path))
    elif path.is_dir():
        # 递归查找所有.log和.log.gz文件
        for ext in ['*.log', '*.log.gz']:
            log_files.extend([str(f) for f in path.rglob(ext)])
    
    log_files.sort()
    return log_files



def extract_matching_lines(file_path: str, target_traceids: Set[str]) -> List[str]:
    """
    从文件中提取包含目标 traceid 的所有行
    优化版本：使用预编译的正则表达式块，流式读取（适合大文件）
    
    参数:
        file_path: 日志文件路径
        target_traceids: traceid 集合
    """
    matching_lines = []

    if not target_traceids:
        return matching_lines
    
    fh = open_log(file_path)
    if fh is None:
        return matching_lines
    
    try:
        with fh:
            # 流式读取，逐行处理
            for line in fh:
                traceid = extract_trace_id(line)
                if traceid in target_traceids:
                    matching_lines.append(line)
                    continue    
                
    except Exception as e:
        print(f"  ⚠️  读取文件失败 {file_path}: {e}")
    
    return matching_lines


def build_test_dataset(
    log_dataset_path: str,
    target_traceids: Set[str],
    output_path: str,
    num_threads: int = 4
) -> Dict[str, int]:
    """
    构建测试数据集
    保持原目录结构，将匹配的日志写入输出目录
    """
    log_files = find_log_files(log_dataset_path)
    output_path_obj = Path(output_path)
    
    stats = {
        'total_files': len(log_files),
        'processed_files': 0,
        'matched_files': 0,
        'total_lines': 0,
        'extracted_lines': 0
    }
    
    print(f"📁 找到 {len(log_files)} 个日志文件")
    print(f"🔍 搜索 {len(target_traceids)} 个 traceid")
    print(f"🚀 使用 {num_threads} 个进程并行处理")
    print("=" * 80)
    
    # 显示正在处理的文件（实时进度）
    processed = 0
    total = len(log_files)
    
    # 使用多进程（绕过GIL限制，真正并行）
    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        # 提交所有任务（传递traceid集合，每个进程自己编译正则表达式）
        future_to_file = {
            executor.submit(process_single_file, file_path, target_traceids, log_dataset_path, str(output_path_obj)): file_path
            for file_path in log_files
        }
        
        # 收集结果
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file_stats = future.result()
                stats['processed_files'] += 1
                stats['total_lines'] += file_stats['total_lines']
                stats['extracted_lines'] += file_stats['extracted_lines']
                
                processed += 1
                progress = (processed / total) * 100
                
                if file_stats['matched']:
                    stats['matched_files'] += 1
                    print(f"[{processed}/{total}] {progress:.1f}%  ✅ {file_stats['extracted_lines']} 行 | {file_path}")
                else:
                    print(f"[{processed}/{total}] {progress:.1f}%  ⭕ 0 行 | {file_path}")
                    
            except Exception as e:
                print(f"[{processed}/{total}] {progress:.1f}%  ❌ 处理失败 {file_path}: {e}")
    
    return stats


def process_single_file(
    file_path: str,
    target_traceids: Set[str],
    log_dataset_path: str,
    output_path: str
) -> Dict:
    """
    处理单个文件：提取匹配的行，写入输出目录
    
    参数:
        file_path: 日志文件路径
        target_traceids: traceid 集合（每个进程独立编译正则表达式）
        log_dataset_path: 日志数据集根目录
        output_path: 输出目录路径（字符串形式，便于多进程传递）
    """
    # 进程内部编译正则表达式（每个进程独立编译，绕过GIL）
    
    # 计算相对路径
    file_path_obj = Path(file_path)
    log_dataset_path_obj = Path(log_dataset_path)
    
    try:
        rel_path = file_path_obj.relative_to(log_dataset_path_obj)
    except ValueError:
        # 如果无法计算相对路径，使用文件名
        rel_path = file_path_obj.name
    
    # 构建输出文件路径
    output_file_path = Path(output_path) / rel_path
    
    # 创建输出目录
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 提取匹配的行
    matching_lines = extract_matching_lines(file_path, target_traceids)
    
    # 统计总行数
    total_lines = 0
    fh = open_log(file_path)
    if fh:
        try:
            with fh:
                total_lines = sum(1 for _ in fh)
        except Exception:
            pass
    
    # 写入输出文件
    if matching_lines:
        # 如果原文件是.gz压缩文件，输出也应该是.gz
        if file_path.endswith('.gz'):
            with gzip.open(output_file_path, 'wt', encoding='utf-8') as f:
                f.writelines(matching_lines)
        else:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.writelines(matching_lines)
    
    return {
        'matched': len(matching_lines) > 0,
        'total_lines': total_lines,
        'extracted_lines': len(matching_lines)
    }


def print_summary(stats: Dict, sampled_traceids: Set[str]):
    """打印汇总信息"""
    print("\n" + "=" * 80)
    print("📊 测试数据构建完成")
    print("=" * 80)
    print(f"抽样 traceid 数量: {len(sampled_traceids)}")
    print(f"总文件数: {stats['total_files']}")
    print(f"已处理文件数: {stats['processed_files']}")
    print(f"匹配文件数: {stats['matched_files']}")
    print(f"总行数: {stats['total_lines']}")
    print(f"提取行数: {stats['extracted_lines']}")
    
    if stats['total_lines'] > 0:
        ratio = (stats['extracted_lines'] / stats['total_lines']) * 100
        print(f"数据压缩比: {ratio:.2f}%")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="测试数据构建脚本")
    parser.add_argument("csv_path", help="CSV文件路径")
    parser.add_argument("log_dataset_path", help="日志数据集路径")
    parser.add_argument("sample_ratio", type=float, help="抽样比例（0-1）")
    parser.add_argument("output_path", help="输出测试数据目录路径")
    parser.add_argument("--threads", type=int, default=8, help="线程数（默认8）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（用于可重复抽样）")
    parser.add_argument("--delimiter", type=str, default='auto', 
                        help="CSV分隔符，支持逗号','、分号';'、制表符'tab'或'auto'自动检测（默认auto）")
    parser.add_argument("--required-cols", type=str, default="3,7,9", 
                        help="需要检查非空的列索引，用逗号分隔，默认'3,7,9'")
    
    args = parser.parse_args()
    
    # 验证参数
    if not os.path.exists(args.csv_path):
        print(f"❌ 错误: CSV文件不存在: {args.csv_path}")
        sys.exit(1)
    
    if not os.path.exists(args.log_dataset_path):
        print(f"❌ 错误: 日志数据集不存在: {args.log_dataset_path}")
        sys.exit(1)
    
    if args.sample_ratio <= 0 or args.sample_ratio > 1:
        print(f"❌ 错误: 抽样比例必须在0-1之间")
        sys.exit(1)
    
    # 解析需要检查的列索引
    try:
        required_cols = [int(x.strip()) for x in args.required_cols.split(',')]
    except ValueError:
        print(f"❌ 错误: --required-cols 参数格式不正确，应为逗号分隔的数字列表")
        sys.exit(1)
    
    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        print(f"🎲 使用随机种子: {args.seed}")
    
    print("=" * 80)
    print("🚀 开始构建测试数据")
    print("=" * 80)
    
    # 步骤1: 从CSV文件读取traceid
    print(f"\n📖 步骤1: 从CSV文件读取traceid")
    print(f"   文件: {args.csv_path}")
    
    # 处理分隔符参数
    delimiter = args.delimiter
    if delimiter.lower() == 'tab':
        delimiter = '\t'
    
    all_traceids = read_traceids_from_csv(args.csv_path, delimiter=delimiter, required_cols=required_cols)
    print(f"   ✅ 找到 {len(all_traceids)} 个有效traceid")
    
    if not all_traceids:
        print("❌ 错误: 未找到任何有效的traceid")
        sys.exit(1)
    
    # 步骤2: 随机抽样traceid
    print(f"\n🎲 步骤2: 随机抽样traceid")
    print(f"   抽样比例: {args.sample_ratio * 100:.1f}%")
    sampled_traceids = sample_traceids(all_traceids, args.sample_ratio)
    print(f"   ✅ 抽样得到 {len(sampled_traceids)} 个traceid")
    
    # 步骤3: 构建测试数据集
    print(f"\n🔍 步骤3: 从日志数据集检索相关日志")
    print(f"   日志数据集: {args.log_dataset_path}")
    print(f"   输出目录: {args.output_path}")
    
    stats = build_test_dataset(
        args.log_dataset_path,
        sampled_traceids,
        args.output_path,
        args.threads
    )
    
    # 打印汇总
    print_summary(stats, sampled_traceids)
    
    print(f"\n✅ 测试数据已构建完成，输出到: {args.output_path}")


if __name__ == "__main__":
    main()