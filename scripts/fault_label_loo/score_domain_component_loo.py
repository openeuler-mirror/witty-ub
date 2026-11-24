#!/usr/bin/env python3
"""Score a completed domain/component LOO against external scene-level CSV labels."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import re

import loo_support as io
from prepare_domain_component_loo import file_sha, read_gzip
from skill_runtime import SCRIPTS

DEFAULT_TAXONOMY = SCRIPTS.parents[1] / 'diagnostic-report-generation/references/log_label.json'
TIMESTAMP_SUFFIX = re.compile(r'_20\d{6}_\d{2}_\d{2}_\d{2}$')
REPLICA_SUFFIX = re.compile(r'_\d{3}$')


def report_scene(source_id, labels):
    name = Path(source_id).stem.removeprefix('lingqu_kvcache_dfx_')
    undated = TIMESTAMP_SUFFIX.sub('', name)
    candidates = {name, undated, REPLICA_SUFFIX.sub('', undated)} & labels.keys()
    if len(candidates) != 1:
        raise ValueError(f'Expected one CSV scene for {source_id}, found {sorted(candidates)}')
    return next(iter(candidates))


def read_targets(label_bytes, taxonomy_bytes, reports):
    domains = defaultdict(set)
    for item in json.loads(taxonomy_bytes):
        domains[item['component']].add(item['domain'])
    reader = csv.DictReader(StringIO(label_bytes.decode('utf-8-sig')))
    if not {'日志描述', '故障组件'} <= set(reader.fieldnames or []):
        raise ValueError('CSV must contain 日志描述 and 故障组件')
    labels = {}
    for row in reader:
        scene = row['日志描述'].strip()
        if not scene or scene in labels:
            raise ValueError(f'Empty or duplicate CSV scene: {scene!r}')
        faults = []
        for component in row['故障组件'].split('/'):
            component = component.strip()
            if len(domains[component]) != 1:
                raise ValueError(f'Expected one taxonomy domain for {component!r} in {scene}')
            faults.append({'domain': next(iter(domains[component])), 'component': component})
        labels[scene] = faults
    targets = []
    for report in reports:
        scene = report_scene(report['source_id'], labels)
        targets.append({'source_id': report['source_id'], 'scene': scene, 'faults': labels[scene]})
    return targets


def score(run, gt_labels, taxonomy, out):
    import eval_domain_component_loo as evaluation

    plan = io.read(run / 'plan.json')
    observations = run / 'observations.json.gz'
    if file_sha(observations) != plan['observations_sha256']:
        raise ValueError('LOO observations differ from the frozen input')
    reports = read_gzip(observations)['reports']
    source_ids = [r['source_id'] for r in reports]
    label_bytes, taxonomy_bytes = gt_labels.read_bytes(), taxonomy.read_bytes()
    targets = read_targets(label_bytes, taxonomy_bytes, reports)
    different_sets, different_counts = [], []
    for target, report in zip(targets, reports):
        observed = Counter(filter(None, map(evaluation.target_label, report['faults'])))
        expected = Counter(map(evaluation.target_label, target['faults']))
        if observed.keys() != expected.keys():
            different_sets.append(target['source_id'])
        if observed != expected:
            different_counts.append(target['source_id'])

    validation = io.read(run / 'validation.json')
    if validation['status'] != 'passed' or validation['views'].keys() != plan['views'].keys():
        raise ValueError('The LOO run must be complete and validated before scoring')
    results, metrics = {}, {}
    for view in plan['views']:
        records = io.read(run / 'views' / f'{view}.json')['predictions']
        if [record['source_id'] for record in records] != source_ids:
            raise ValueError(f'Prediction coverage differs from the CSV labels: {view}')
        results[view] = records
        metrics[view] = {method: {field: evaluation.metric(targets, records, method, field)
                                  for field in evaluation.FIELDS} for method in evaluation.METHODS}

    out.mkdir(parents=True, exist_ok=True)
    summary = {'truth_source': str(gt_labels.resolve()), 'truth_sha256': hashlib.sha256(label_bytes).hexdigest(),
               'taxonomy_source': str(taxonomy.resolve()), 'taxonomy_sha256': hashlib.sha256(taxonomy_bytes).hexdigest(),
               'loo_run': str(run.resolve()), 'reports': len(reports),
               'matched_scenes': len({row['scene'] for row in targets}),
               'csv_faults': sum(len(row['faults']) for row in targets),
               'report_pairs_checked': {'different_sets': different_sets, 'different_counts': different_counts},
               'scoring': plan['scoring'], 'results': metrics}
    io.write(out / 'ground_truth.json', targets)
    evaluation.write_csv(out, targets, results, metrics)
    io.write(out / 'summary.json', summary)
    print(f'Scored {len(reports)} reports against {summary["matched_scenes"]} CSV scenes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('run', 'gt-labels', 'out'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--taxonomy', type=Path, default=DEFAULT_TAXONOMY)
    args = parser.parse_args()
    score(args.run, args.gt_labels, args.taxonomy, args.out)
