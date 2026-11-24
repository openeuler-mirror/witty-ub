#!/usr/bin/env python3
"""Fit the report-level domain/component classifier on a validated LOO dataset."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

import eval_domain_component_loo as evaluation
import loo_support as io
import portable_classifier
from prepare_domain_component_loo import file_sha
from score_domain_component_loo import read_targets
from threadpoolctl import threadpool_limits

VIEW = 'all_context_v2'


def train(run, reports_root, out, model_id):
    plan = io.read(run / 'plan.json')
    if io.read(run / 'validation.json')['status'] != 'passed':
        raise ValueError('Expected a validated LOO run')
    observations = run / 'observations.json.gz'
    if file_sha(observations) != plan['observations_sha256']:
        raise ValueError('Observations differ from the evaluated dataset')
    for name in ('gt_labels', 'taxonomy'):
        source = plan[name]
        if file_sha(Path(source['path'])) != source['sha256']:
            raise ValueError(f'LOO input changed: {name}')
    for path in (evaluation.v6.training.__file__, *(evaluation.v6.SCRIPTS / name for name in
                   ('mined_log_features.py', 'mined_log_features_v2.py'))):
        path = Path(path).resolve()
        if file_sha(path) != plan['source_sha256'][str(path)]:
            raise ValueError(f'LOO feature or training code changed: {path}')

    reports = evaluation.load_inputs(observations, reports_root=reports_root)['reports']
    targets = read_targets(Path(plan['gt_labels']['path']).read_bytes(),
                           Path(plan['taxonomy']['path']).read_bytes(), reports)
    if targets != io.read(run / 'ground_truth.json'):
        raise ValueError('Resolved labels differ from the evaluated ground truth')
    truths = [sorted({evaluation.target_label(fault) for fault in target['faults']}) for target in targets]
    features = [evaluation.v6.vector(VIEW, row['base'], row['context']) for row in reports]
    config = {'C': plan['views'][VIEW], 'selection': 'none', 'class_weight': None}
    print(f'Fitting {VIEW} on all {len(reports)} reports', flush=True)
    training = evaluation.v6.training
    with threadpool_limits(limits=1):
        fitted = training.fit(features, truths, config)
        model = training.export(fitted, VIEW, config)
        expected = [evaluation.prediction(label)['component'] for label in training.predict(fitted, features)]

    # The report runtime maps the predicted component to its unique taxonomy domain.
    model['classes'] = [evaluation.prediction(label)['component'] for label in model['classes']]
    if len(set(model['classes'])) != len(model['classes']):
        raise ValueError('Runtime classification requires a unique domain per component')
    if expected != [portable_classifier.predict(model, vector)['label'] for vector in features]:
        raise ValueError('Portable predictions differ from the fitted estimator')
    model['metadata'].update(
        model_id=model_id, training_reports=len(reports),
        training_source_ids=[row['source_id'] for row in reports],
        reports_root=str(reports_root.resolve()),
        class_counts=dict(Counter(evaluation.prediction(label)['component']
                                  for labels in truths for label in labels)),
        observations_sha256=plan['observations_sha256'], gt_sha256=plan['gt_labels']['sha256'],
        taxonomy_sha256=plan['taxonomy']['sha256'], independent_test_score=None,
        purpose='Report-level full-data deployment classifier',
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, 'wt', encoding='utf-8', compresslevel=9) as stream:
        json.dump(model, stream, ensure_ascii=False, allow_nan=False)
    print(f'Wrote {out} with {len(model["classes"])} classes and {len(model["feature_names"])} features', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--reports-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model-id', required=True)
    args = parser.parse_args()
    train(args.run, args.reports_root, args.out, args.model_id)
