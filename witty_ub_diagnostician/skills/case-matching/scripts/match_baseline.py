#!/usr/bin/env python3
"""Export observed profiles or apply the frozen numeric/cosine default policy."""
import argparse
import json
from pathlib import Path
import baseline_matching as engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--fault-index', type=int)
    parser.add_argument('--log-dir', type=Path)
    parser.add_argument('--query', type=Path)
    parser.add_argument('--cases', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--structured-query', type=Path)
    parser.add_argument('--raw-query', type=Path, help='已有原始观测旁车的位置；默认自动读取同名 .raw.json')
    parser.add_argument('--exclude-source-id', action='append', default=[], help='排除源报告和同日志的全部来源ID')
    args = parser.parse_args(argv)
    if bool(args.report) == bool(args.query):
        parser.error('--report 与 --query 必须恰选一种')
    read = lambda p: json.loads(p.read_text())
    if args.report:
        if args.cases:
            parser.error('导出与匹配分开执行；匹配使用 --query 和 --cases')
        if args.fault_index is not None and args.fault_index < 0:
            parser.error('fault-index 不能为负')
        payload = read(args.report)
        from fixed_matching import extract_report
        result, structured, raw = extract_report(payload, args.log_dir,
            None if args.fault_index is None else [args.fault_index])
        companion = args.out.with_name(args.out.stem + '.structured.json')
        companion.parent.mkdir(parents=True, exist_ok=True)
        companion.write_text(json.dumps(structured, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        raw_companion = args.out.with_name(args.out.stem + '.raw.json')
        raw_companion.write_text(json.dumps(raw, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        import default_matching
        import mined_log_features_v2
        context=mined_log_features_v2.scan(args.log_dir) if args.log_dir else default_matching.unknown_context()
        context['provenance']['source_identities']=default_matching.identities(payload)
        args.out.with_name(args.out.stem+'.mined.json').write_text(json.dumps(context,ensure_ascii=False,allow_nan=False)+'\n')
    else:
        if not args.cases:
            parser.error('匹配需要 --cases')
        if args.log_dir or args.fault_index is not None:
            parser.error('--log-dir / --fault-index 仅用于导出')
        bundle = read(args.cases)
        cases = bundle['cases'] if isinstance(bundle, dict) else bundle
        cases = [c for c in cases if c['source_id'] not in args.exclude_source_id]
        companion = args.query.with_name(args.query.stem + '.structured.json')
        structured_path = args.structured_query or (companion if companion.is_file() else None)
        structured = read(structured_path) if structured_path else None
        import default_matching
        raw_companion = args.query.with_name(args.query.stem + '.raw.json')
        raw_path = args.raw_query or (raw_companion if raw_companion.is_file() else None)
        try:
            context_path=args.query.with_name(args.query.stem+'.mined.json')
            result = default_matching.match(read(args.query),cases,structured,read(raw_path) if raw_path else None,
                read(context_path) if context_path.exists() else None,excluded_sources=args.exclude_source_id)
        except ValueError as error:
            parser.error(str(error))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
