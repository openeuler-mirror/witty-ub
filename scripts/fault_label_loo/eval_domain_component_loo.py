#!/usr/bin/env python3
"""Repeat the seven-view source LOO using report fault domain/component pairs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import json
import multiprocessing
from pathlib import Path
import platform

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MaxAbsScaler, normalize
from threadpoolctl import threadpool_limits

import eval_feature_loo as v6
import baseline_matching
import loo_support as io
import score_domain_component_loo as csv_truth
from prepare_domain_component_loo import fault_targets, file_sha, read_gzip

FIELDS = ('domain', 'component', 'pair')
METHODS = ('classifier', 'k4')
FOLD_STATE = {}


def target_label(fault):
    pair = [fault['domain'], fault['component']]
    if all(isinstance(value, str) and value.strip() for value in pair):
        return json.dumps(pair, ensure_ascii=False)
    return None


def prediction(label):
    if label is None:
        return None
    domain, component = json.loads(label)
    return {'domain': domain, 'component': component}


def load_inputs(path, *, reports_root=None):
    inputs = read_gzip(path)
    reports = inputs['reports']
    root = reports_root if reports_root is not None else Path(inputs['reports_root'])
    actual = sorted(root.glob('*.json'))
    if [p.name for p in actual] != [row['source_id'] for row in reports]:
        raise ValueError('Report inventory changed after observation extraction')
    for report, row in zip(actual, reports):
        data = report.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['report_sha256'] or fault_targets(json.loads(data)) != row['faults']:
            raise ValueError(f'Report changed after observation extraction: {report}')
    return inputs


def make_folds(reports, truths):
    queries = [{**{key: row[key] for key in ('source_id', 'identity')},
                'structured': {'log': {'provenance': {'files': row['log_files']}}}} for row in reports]
    groups = io.source_groups(queries, 'source')
    by_group = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)
    return [{'fold': index, 'query_id': row['source_id'],
             'excluded_source_ids': [reports[j]['source_id'] for j in by_group[groups[index]]],
             'train_indices': [j for j, labels in enumerate(truths) if labels and groups[j] != groups[index]]}
            for index, row in enumerate(reports)]


def storage_matrix(features):
    # The column index is only a storage format. Each fold selects columns
    # present in its training rows before computing statistics or fitting.
    dictionary = DictVectorizer(sparse=True)
    matrix = dictionary.fit_transform(features)
    present = matrix.copy()
    present.data.fill(1)
    return matrix, present, dictionary.get_feature_names_out()


def cosine_vote(train, query, candidates):
    if not query.nnz or not query.data.any():
        return None, []
    values = (normalize(query) @ normalize(train).T).toarray()[0]
    values = np.clip(values, 0., 1.)
    available = np.asarray(abs(train).sum(axis=1)).ravel() > 0
    rows = [{'first_level_label': label, 'score_norm': float(values[index]), 'source_id': source}
            for index, label, source in candidates if available[index]]
    rows.sort(key=lambda row: -row['score_norm'])
    top = rows[:4]
    return baseline_matching.decide(top)['label'], top


def run_fold(index):
    state = FOLD_STATE
    train_indices = state['folds'][index]['train_indices']
    source_ids = [state['sources'][j] for j in train_indices]
    assert set(source_ids).isdisjoint(state['folds'][index]['excluded_source_ids'])
    columns = state['present'][train_indices].getnnz(axis=0) > 0
    matrix = state['matrix']
    train = matrix[train_indices][:, columns]
    scaler = MaxAbsScaler().fit(train)
    train = scaler.transform(train)
    query = scaler.transform(matrix[index][:, columns])
    labels, positions, weights, candidates = [], [], [], []
    for position, j in enumerate(train_indices):
        truth = state['truths'][j]
        labels.extend(truth)
        positions.extend([position] * len(truth))
        weights.extend([1 / len(truth)] * len(truth))
        candidates.extend((position, label, state['sources'][j]) for label in state['fault_labels'][j] if label)
    classes = sorted(set(labels))
    if len(classes) == 1:
        predicted, scores = classes[0], [1.]
    else:
        model = LogisticRegression(C=state['c'], solver='lbfgs', max_iter=1200, tol=1e-4)
        model.fit(train[positions], labels, sample_weight=weights)
        assert list(model.classes_) == classes
        scores = model.predict_proba(query)[0].tolist()
        predicted = model.predict(query)[0]
    voted, neighbors = cosine_vote(train, query, candidates)
    for row in neighbors:
        row['target'] = prediction(row.pop('first_level_label'))
    record = {'fold': index, 'source_id': state['sources'][index], 'classifier': prediction(predicted),
              'classifier_scores': [{**prediction(label), 'score': score} for label, score in zip(classes, scores)],
              'k4': prediction(voted), 'k4_neighbors': neighbors}
    audit = {'fold': index, 'training_reports': len(train_indices), 'candidate_faults': len(candidates),
             'training_sources_sha256': io.digest(source_ids), 'feature_count': train.shape[1],
             'feature_names_sha256': io.digest(state['names'][columns].tolist()),
             'scaling_sha256': io.digest(scaler.scale_.tolist())}
    return record, audit


def value_for(field, item):
    return target_label(item) if field == 'pair' else item.get(field)


def metric(reports, records, method, field):
    support, predicted_counts, true_positive = Counter(), Counter(), Counter()
    confusion = defaultdict(Counter)
    scored = 0
    for report, record in zip(reports, records):
        truth = {value for fault in report['faults'] if (value := value_for(field, fault))}
        if not truth:
            continue
        selected = value_for(field, record[method]) if record[method] else None
        scored += 1
        support.update(truth)
        confusion[' + '.join(sorted(truth))][selected or '<unknown>'] += 1
        if selected:
            predicted_counts[selected] += 1
        if selected in truth:
            true_positive[selected] += 1
    per_label = {}
    for label in sorted(support.keys() | predicted_counts.keys()):
        hits = true_positive[label]
        count = support[label] + predicted_counts[label]
        per_label[label] = {'support': support[label], 'predicted': predicted_counts[label], 'hits': hits,
                            'f1': 2 * hits / count}
    hits = true_positive.total()
    return {'scored_reports': scored, 'hits': hits, 'accuracy': hits / scored if scored else None,
            'predictions': predicted_counts.total(), 'abstentions': scored - predicted_counts.total(),
            'macro_f1': sum(row['f1'] for row in per_label.values()) / len(per_label) if per_label else None,
            'per_label': per_label, 'confusion': dict(confusion)}


def validate_fold_samples(folds, features, truths, fault_labels, records, audits, c):
    sources = [fold['query_id'] for fold in folds]
    indices = {0, len(folds) // 2, len(folds) - 1}
    classes = {label for labels in truths for label in labels}
    indices.update(next(i for i, labels in enumerate(truths) if label in labels) for label in classes)
    for fold, record, audit in zip(folds, records, audits):
        train_ids = [sources[j] for j in fold['train_indices']]
        assert audit['training_sources_sha256'] == io.digest(train_ids)
        assert audit['training_reports'] == len(train_ids) and record['source_id'] == fold['query_id']
        assert set(train_ids).isdisjoint(fold['excluded_source_ids'])
        assert all(neighbor['source_id'] in train_ids for neighbor in record['k4_neighbors'])
    config = {'C': c, 'selection': 'none', 'class_weight': None}
    for index in sorted(indices):
        train = folds[index]['train_indices']
        targets = [truths[j] for j in train]
        cases = [{'id': f'{sources[j]}#{k}', 'source_id': sources[j], 'label': label}
                 for j in train for k, label in enumerate(fault_labels[j]) if label]
        references = {'schema_version': v6.cosine_matching.VERSION, 'cases': cases,
                      'sources': [{'source_id': sources[j], 'vector': features[j]} for j in train]}
        ranked, _ = v6.cosine_matching.rank(features[index], references, labels=classes)
        voted = v6.cosine_matching.decide(ranked)['label']
        assert prediction(voted) == records[index]['k4'], (index, voted, records[index]['k4'])
        if len({label for labels in targets for label in labels}) <= 1:
            continue
        fit = v6.training.fit([features[j] for j in train], targets, config)
        dictionary, scaler, _, _, _ = fit
        assert io.digest(dictionary.get_feature_names_out().tolist()) == audits[index]['feature_names_sha256']
        assert io.digest(scaler.scale_.tolist()) == audits[index]['scaling_sha256']
        predicted = v6.training.predict(fit, [features[index]])[0]
        assert prediction(predicted) == records[index]['classifier'], (index, predicted, records[index]['classifier'])
    return {'folds_checked': len(records), 'classifier_refit_and_k4_replay_folds': sorted(indices)}


def write_csv(out, targets, results, metrics):
    with (out / 'comparison.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['view', 'method', 'target', 'scored_reports', 'hits', 'accuracy', 'macro_f1', 'abstentions']
        writer = csv.DictWriter(stream, fields, extrasaction='ignore')
        writer.writeheader()
        for view, methods in metrics.items():
            for method, measures in methods.items():
                for field, values in measures.items():
                    writer.writerow({'view': view, 'method': method, 'target': field, **values})
    with (out / 'predictions.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['report', 'scene', 'view', 'method', 'gt_faults', 'domain', 'component',
                         'domain_hit', 'component_hit', 'pair_hit'])
        for view, records in results.items():
            for target, record in zip(targets, records):
                expected = [{value_for(field, fault) for fault in target['faults']}
                            for field in FIELDS]
                faults = json.dumps(target['faults'], ensure_ascii=False)
                for method in METHODS:
                    selected = record[method] or {}
                    hits = [bool(selected) and value_for(field, selected) in truth
                            for field, truth in zip(FIELDS, expected)]
                    writer.writerow([target['source_id'], target['scene'], view, method, faults, selected.get('domain'),
                                     selected.get('component'), *hits])


def verify_report_labels(out, reports, targets):
    exact_sets = Counter()
    missing_fields = []
    different_pair_counts = []
    with (out / 'report_verification.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['report', 'scene', 'report_faults', 'gt_faults', 'domain_set_match',
                         'component_set_match', 'pair_set_match', 'pair_counts_match', 'incomplete_faults'])
        for report, target in zip(reports, targets):
            observed, expected = report['faults'], target['faults']
            matches = []
            for field in FIELDS:
                actual = {value for fault in observed
                          if isinstance(value := value_for(field, fault), str) and value.strip()}
                match = actual == {value_for(field, fault) for fault in expected}
                matches.append(match)
                exact_sets[field] += match
            pair_counts_match = Counter(filter(None, map(target_label, observed))) == Counter(map(target_label, expected))
            if not pair_counts_match:
                different_pair_counts.append(report['source_id'])
            incomplete = [fault for fault in observed if not target_label(fault)]
            missing_fields.extend({'report': report['source_id'], **fault} for fault in incomplete)
            writer.writerow([report['source_id'], target['scene'], json.dumps(observed, ensure_ascii=False),
                             json.dumps(expected, ensure_ascii=False), *matches, pair_counts_match, len(incomplete)])
    return {'exact_nonempty_label_sets': dict(exact_sets), 'different_pair_counts': different_pair_counts,
            'incomplete_report_faults': missing_fields}


def run(observations, gt_labels, taxonomy, out, jobs):
    threadpool_limits(1)
    inputs = load_inputs(observations)
    reports = inputs['reports']
    gt_bytes = gt_labels.read_bytes()
    taxonomy_bytes = taxonomy.read_bytes()
    targets = csv_truth.read_targets(gt_bytes, taxonomy_bytes, reports)
    sources = [row['source_id'] for row in reports]
    fault_labels = [[target_label(fault) for fault in row['faults']] for row in targets]
    truths = [sorted({label for label in labels if label}) for labels in fault_labels]
    folds = make_folds(reports, truths)
    if not all(fold['train_indices'] for fold in folds):
        raise ValueError('At least one fold has no labeled training reports')
    plan = {'protocol': 'grouped-source-loo-domain-component-v1',
            'targets': 'CSV 故障组件 and its corresponding domain in the diagnostic taxonomy',
            'gt_labels': {'path': str(gt_labels.resolve()), 'sha256': hashlib.sha256(gt_bytes).hexdigest()},
            'taxonomy': {'path': str(taxonomy.resolve()), 'sha256': hashlib.sha256(taxonomy_bytes).hexdigest()},
            'scoring': 'One predicted pair per report. A hit matches any external CSV target for the field; '
                       'a pair hit matches both fields on the same target.',
            'fold_exclusion': 'Held-out report, source aliases, and identical whole-log content',
            'views': v6.CONFIGS, 'observations_sha256': file_sha(observations),
            'source_sha256': {str(path): file_sha(path) for path in (
                Path(__file__), Path(v6.__file__), Path(v6.training.__file__),
                Path(io.__file__), Path(csv_truth.__file__),
                v6.SCRIPTS / 'mined_log_features.py', v6.SCRIPTS / 'mined_log_features_v2.py',
                v6.SCRIPTS / 'cosine_matching.py', v6.SCRIPTS / 'baseline_matching.py')},
            'software': {'python': platform.python_version(), 'scikit-learn': sklearn.__version__,
                         'numpy': np.__version__, 'scipy': scipy.__version__}}
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / 'plan.json'
    if plan_path.exists() and io.read(plan_path) != plan:
        raise ValueError('Existing evaluation was created from a different plan')
    io.write(plan_path, plan)
    io.write(out / 'folds.json', folds)
    io.write(out / 'ground_truth.json', targets)
    report_verification = verify_report_labels(out, reports, targets)
    metrics, results, validation = {}, {}, {}
    for view, c in v6.CONFIGS.items():
        features = [v6.vector(view, row['base'], row['context']) for row in reports]
        artifact = out / 'views' / f'{view}.json'
        if artifact.exists():
            data = io.read(artifact)
            records, audits = data['predictions'], data['audits']
            validation[view] = data['validation']
        else:
            matrix, present, names = storage_matrix(features)
            FOLD_STATE.update(matrix=matrix, present=present, names=names, folds=folds, sources=sources,
                              truths=truths, fault_labels=fault_labels, c=c)
            records, audits = [], []
            with ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context('fork')) as pool:
                for count, (record, audit) in enumerate(pool.map(run_fold, range(len(folds)), chunksize=2), 1):
                    records.append(record)
                    audits.append(audit)
                    if count % 50 == 0 or count == len(folds):
                        print(f'{view} {count}/{len(folds)}', flush=True)
            FOLD_STATE.clear()
            validation[view] = validate_fold_samples(folds, features, truths, fault_labels, records, audits, c)
            artifact.parent.mkdir(exist_ok=True)
            temporary = artifact.with_suffix('.tmp')
            io.write(temporary, {'predictions': records, 'audits': audits, 'validation': validation[view]})
            temporary.replace(artifact)
        results[view] = records
        metrics[view] = {method: {field: metric(targets, records, method, field) for field in FIELDS}
                         for method in METHODS}
    coverage = {'reports': len(reports), 'gt_scenes': len({target['scene'] for target in targets}),
                'gt_pairs': sum(len(target['faults']) for target in targets),
                'source_groups': len({tuple(fold['excluded_source_ids']) for fold in folds}),
                'labeled_reports': sum(bool(labels) for labels in truths),
                'reused_log_observations': sum(row['reused_log_observations'] for row in reports)}
    write_csv(out, targets, results, metrics)
    io.write(out / 'validation.json', {'status': 'passed', 'views': validation})
    io.write(out / 'summary.json', {'coverage': coverage, 'report_verification': report_verification,
                                   'results': metrics})
    print(f'Completed grouped source LOO with {len(folds)} reports', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--gt-labels', type=Path, required=True)
    parser.add_argument('--taxonomy', type=Path, default=csv_truth.DEFAULT_TAXONOMY)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    run(args.observations, args.gt_labels, args.taxonomy, args.out, args.jobs)
