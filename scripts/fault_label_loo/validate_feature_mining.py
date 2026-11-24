#!/usr/bin/env python3
"""Refit selected train-only mappings and replay all held-out mining outcomes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import skill_runtime
import feature_vectors
import loo_support as io
import mined_log_features as extraction
import mine_label_features as mining
import portable_classifier


def validate(reference,root,revision=1):
    if revision==2:
        import mined_log_features_v2 as extraction
        import mine_label_features_v2 as mining
    else:
        import mined_log_features as extraction
        import mine_label_features as mining
    import sklearn
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    prepared=io.read(reference/'inputs/prepared.json');raw=io.read(reference/'inputs/raw_observations.json')
    split=io.read(root/'split.json');plan=io.read(root/'plan.json');selection=io.read(root/'training_selection.json')
    summary=io.read(root/'summary.json');queries=prepared['reports'];train=split['train_indices'];valid=split['validation_indices']
    assert (root/'split.json').read_bytes()==(reference/'split.json').read_bytes()
    assert hashlib.sha256(Path(plan['dataset_audit']['truth_source']).read_bytes()).hexdigest()==plan['gt_sha256']
    groups=io.source_groups(queries,'source')
    assert not {groups[i] for i in train}&{groups[i] for i in valid}
    contexts={};cache_hashes={}
    for i,q in enumerate(queries):
        path=root/'context_cache'/f'{i:04d}.json.gz';cache_hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt') as stream:contexts[q['source_id']]=json.load(stream)
    base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in queries]
    baselines={r['query_id']:r for r in io.read(reference/'classifier/validation_predictions.json')}
    before=[baselines[queries[i]['source_id']]['all_feature_k4'] for i in valid]
    truths=[queries[i]['truth'] for i in train]
    sources=set(split['train_source_ids']);cases=[c for c in prepared['cases'] if c['source_id'] in sources]
    max_difference=0.;replays=0
    for view in extraction.VIEWS:
        values=[extraction.vector(view,base[i],contexts[q['source_id']]) for i,q in enumerate(queries)]
        config=selection[view]['classifier']['config']
        model=mining.fit([values[i] for i in train],truths,config)
        expected=io.read(root/f'models/{view}.json');exported=mining.export(model,view,config)
        for key in ('feature_names','classes'):assert exported[key]==expected[key]
        difference=max((abs(a-b) for aa,bb in zip(exported['coefficients'],expected['coefficients']) for a,b in zip(aa,bb)),default=0.)
        intercept_difference=max(abs(a-b) for a,b in zip(exported['intercept'],expected['intercept']))
        assert intercept_difference<1e-8
        max_difference=max(max_difference,difference);assert difference<1e-8
        assert expected['metadata']['training_source_ids']==split['train_source_ids']
        pred=mining.predict(model,[values[i] for i in valid])
        records=io.read(root/f'predictions/{view}_classifier.json')
        assert pred==[r['prediction'] for r in records]
        assert pred==[portable_classifier.predict(expected,values[i])['label'] for i in valid]
        assert [r['query_id'] for r in records]==split['validation_source_ids']
        assert io.metrics(records,'prediction')==summary['validation'][view]['classifier']
        metric=mining.metric_fit([values[i] for i in train],truths,selection[view]['k4']['supervised'])
        pred=mining.metric_predict(metric,[values[i] for i in train],[values[i] for i in valid],cases,
                                   {queries[i]['source_id']:j for j,i in enumerate(train)})
        records=io.read(root/f'predictions/{view}_k4.json');assert pred==[r['prediction'] for r in records]
        assert [r['query_id'] for r in records]==split['validation_source_ids']
        assert io.metrics(records,'prediction')==summary['validation'][view]['k4']
        replays+=2*len(valid);print('refit/replay exact',view,flush=True)
    primary=summary['primary_selected_on_training'];cv_indices=[];cv_pred=[]
    values=[extraction.vector(primary,base[i],contexts[q['source_id']]) for i,q in enumerate(queries)]
    for fold in split['inner_folds']:
        a,b=fold['train_indices'],fold['validation_indices']
        assert set(a)|set(b)==set(train) and not (set(a)|set(b))&set(valid)
        assert not {groups[i] for i in a}&{groups[i] for i in b}
        model=mining.fit([values[i] for i in a],[queries[i]['truth'] for i in a],selection[primary]['classifier']['config'])
        cv_indices+=b;cv_pred+=mining.predict(model,[values[i] for i in b])
    metrics,_=mining.summarize_predictions(queries,cv_indices,cv_pred)
    assert metrics==selection[primary]['classifier']['metrics']
    result={'status':'passed','train':len(train),'validation':len(valid),'heldout_replays':replays,
        'refitted_classifiers':len(extraction.VIEWS),'refitted_K4_metrics':len(extraction.VIEWS),
        'primary_cv_refits':len(split['inner_folds']),'max_coefficient_difference':max_difference,
        'split_sha256':plan['split_sha256'],'gt_sha256':plan['gt_sha256'],'cache_sha256':cache_hashes}
    io.write(root/'refit_validation.json',result);print('all mining checks passed',flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--revision',type=int,choices=(1,2),default=1)
    args=parser.parse_args();validate(args.reference,args.root,args.revision)
