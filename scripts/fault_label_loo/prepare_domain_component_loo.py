#!/usr/bin/env python3
"""Freeze fault-domain/component targets and label-blind observations for source LOO."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import json
from pathlib import Path

from skill_runtime import SCRIPTS
import baseline_matching
import default_matching
import enhanced_matching
import feature_vectors
import fixed_matching
import loo_support as io
import mined_log_features_v2 as extraction


def read_gzip(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def write_gzip(path, data):
    temporary = path.with_suffix('.tmp')
    with gzip.open(temporary, 'wt', encoding='utf-8', compresslevel=1) as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False)
    temporary.replace(path)


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fault_targets(report):
    result = []
    for fault in report['faults']:
        conclusion = fault['conclusion']
        domain, component = (conclusion.get(key) for key in ('domain', 'component'))
        result.append({'fault_id': fault['id'], 'domain': domain, 'component': component})
    return result


def log_files(directory):
    files = sorted(path for path in directory.rglob('*') if path.is_file()
                   and path.name.endswith(('.log', '.log.gz')))
    if not files:
        raise ValueError(f'No log files under {directory}')
    rows = []
    for path in files:
        opener = gzip.open if path.name.endswith('.gz') else open
        with opener(path, 'rb') as stream:
            rows.append({'file': path.relative_to(directory).as_posix(),
                         'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()})
    return rows


def file_map(files):
    return {row['file']: row['sha256'] for row in files}


def reference_inputs(reference):
    if reference is None:
        return {}
    snapshot = reference / 'feature_loo/source_snapshot/runtime'
    extractors = ('baseline_matching.py', 'build_log_semantic_profiles.py', 'enhanced_matching.py',
                  'fixed_observations.py', 'raw_observations.py', 'log_message_features.py',
                  'mined_log_features.py', 'mined_log_features_v2.py')
    for name in extractors:
        if file_sha(SCRIPTS / name) != file_sha(snapshot / name):
            raise ValueError(f'Reference extractor changed: {name}')
    path = reference / 'inputs/prepared.json'
    raw = io.read(reference / 'inputs/raw_observations.json')
    if raw['prepared_sha256'] != file_sha(path) or raw['extractor_sha256'] != file_sha(SCRIPTS / 'raw_observations.py'):
        raise ValueError('Reference raw observations do not match their inputs')
    inputs = {}
    for index, row in enumerate(io.read(path)['reports']):
        inputs[row['name']] = (row['profile']['log_semantic_profile'], row['structured']['log'],
                               raw['reports'][row['source_id']],
                               reference / 'context/context_cache' / f'{index:04d}.json.gz')
    return inputs


def observe(path, directory, reference):
    data = path.read_bytes()
    report = json.loads(data)
    files = log_files(directory)
    expected = file_map(files)
    reused = reference is not None and file_map(reference[1]['provenance']['files']) == expected
    if reused:
        semantic, structured_log, raw, context_path = reference
        profile = baseline_matching.extract_report(report)
        profile['log_semantic_profile'] = semantic
        structured = enhanced_matching.extract_report(report)
        structured['log'] = structured_log
        context = read_gzip(context_path)
    else:
        profile, structured, raw = fixed_matching.extract_report(report, directory)
        context = extraction.scan(directory, files)
    for provenance in (structured['log']['provenance'], raw['provenance'], context['provenance']):
        if file_map(provenance['files']) != expected:
            raise ValueError(f'Observation/log mismatch for {path.name}')
    if context['schema_version'] != extraction.VERSION:
        raise ValueError(f'Unexpected context version for {path.name}')
    return {'source_id': path.name, 'identity': default_matching.identities(report),
            'report_sha256': hashlib.sha256(data).hexdigest(), 'log_files': files,
            'faults': fault_targets(report), 'reused_log_observations': reused,
            'base': feature_vectors.build_observations(profile, structured, raw),
            'context': {'families': context['families']}}


def prepare(reports_root, logs_root, out, reference, jobs):
    reports = sorted(reports_root.glob('*.json'))
    if not reports:
        raise ValueError(f'No JSON reports in {reports_root}')
    if out.exists():
        raise ValueError(f'Observation file already exists: {out}')
    cache = reference_inputs(reference)
    results = {}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        submissions = {pool.submit(observe, path, logs_root / path.stem, cache.get(path.stem)): path
                       for path in reports}
        for count, future in enumerate(as_completed(submissions), 1):
            results[submissions[future]] = future.result()
            if count % 25 == 0 or count == len(reports):
                print(f'Observations {count}/{len(reports)}', flush=True)
    rows = [results[path] for path in reports]
    out.parent.mkdir(parents=True, exist_ok=True)
    write_gzip(out, {'reports_root': str(reports_root.resolve()), 'logs_root': str(logs_root.resolve()),
                     'reference': str(reference.resolve()) if reference else None, 'reports': rows})
    print(f'Reused verified log observations for {sum(row["reused_log_observations"] for row in rows)} reports',
          flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('reports-root', 'logs-root', 'out'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    prepare(args.reports_root, args.logs_root, args.out, args.reference, args.jobs)
