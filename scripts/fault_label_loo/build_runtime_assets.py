#!/usr/bin/env python3
"""Build full-data deployment assets; their training fit is not a new test score."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import skill_runtime
from skill_runtime import SCRIPTS
import cosine_matching
import eval_loo
import feature_vectors
import loo_support as io
import mined_log_features_v2 as extraction
import mine_label_features_v2 as training
import portable_classifier


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,'wt',compresslevel=9) as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False)


def build(args):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    prepared=io.read(args.reference/'inputs/prepared.json');raw=io.read(args.reference/'inputs/raw_observations.json')
    assert raw['prepared_sha256']==hashlib.sha256((args.reference/'inputs/prepared.json').read_bytes()).hexdigest()
    audit=eval_loo.audit_dataset(prepared,args.reports_root,args.gt_labels)
    contexts=[]
    for i,q in enumerate(prepared['reports']):
        with gzip.open(args.context_root/'context_cache'/f'{i:04d}.json.gz','rt') as stream:context=json.load(stream)
        assert context['schema_version']==extraction.VERSION
        assert {r['file']:r['sha256'] for r in context['provenance']['files']}=={
            r['file']:r['sha256'] for r in q['structured']['log']['provenance']['files']}
        contexts.append(context)
    for name in ('mined_log_features.py','mined_log_features_v2.py','log_message_features.py'):
        assert (SCRIPTS/name).read_bytes()==(args.context_root/'source_snapshot'/name).read_bytes()
    queries=prepared['reports'];base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in queries]
    numeric=[extraction.vector('numeric_units',b,c) for b,c in zip(base,contexts)]
    config={'id':'c1.0_none_natural','C':1.,'selection':'none','class_weight':None}
    fitted=training.fit(numeric,[q['truth'] for q in queries],config)
    model=training.export(fitted,'numeric_units',config)
    model['metadata'].update(model_id='numeric-units-full-20261118-v1',training_reports=len(queries),
        training_source_ids=[q['source_id'] for q in queries],purpose='deployment; fit on all development data',
        evaluation_note='79.96% is the v6 fold-retrained LOO procedure score, not a test of these full-data weights')
    assert training.predict(fitted,numeric)==[portable_classifier.predict(model,v)['label'] for v in numeric]
    sources=[{'source_id':q['source_id'],'identity':q['identity'],
        'log_content_sha256':io.digest(sorted(r['sha256'] for r in c['provenance']['files'])),
        'vector':extraction.vector('all_context_v2',b,c)} for q,b,c in zip(queries,base,contexts)]
    bank={'schema_version':cosine_matching.VERSION,'feature_version':extraction.VERSION,'view':'all_context_v2',
          'sources':sources,'cases':[{k:c[k] for k in ('id','source_id','identity','label')} for c in prepared['cases']]}
    args.out.mkdir(parents=True,exist_ok=True)
    paths={'numeric_classifier':'numeric_classifier.json.gz','cosine_bank':'cosine_bank.json.gz'}
    for key,value in (('numeric_classifier',model),('cosine_bank',bank)):write(args.out/paths[key],value)
    manifest={'schema_version':'default-label-assets-v1','policy':'numeric-units-classifier-cosine-fallback-v1',
        'feature_version':extraction.VERSION,'training_reports':len(queries),'reference_cases':len(bank['cases']),
        'files':{key:{'path':name,'sha256':hashlib.sha256((args.out/name).read_bytes()).hexdigest()} for key,name in paths.items()},
        'gt_sha256':hashlib.sha256(args.gt_labels.read_bytes()).hexdigest(),
        'prepared_sha256':hashlib.sha256((args.reference/'inputs/prepared.json').read_bytes()).hexdigest(),
        'extractor_sha256':{name:hashlib.sha256((SCRIPTS/name).read_bytes()).hexdigest() for name in (
            'mined_log_features.py','mined_log_features_v2.py','log_message_features.py')},
        'deployment_training':True,'independent_test_score':None,
        'evaluation_note':model['metadata']['evaluation_note'],'dataset_audit':audit}
    io.write(args.out/'manifest.json',manifest)
    print('Saved deployment model and cosine reference bank',len(queries),len(bank['cases']),args.out,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','context-root','reports-root','gt-labels','out'):parser.add_argument('--'+name,type=Path,required=True)
    build(parser.parse_args())
