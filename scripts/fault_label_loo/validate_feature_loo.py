#!/usr/bin/env python3
"""Audit every fold/model, replay cosine K4, and independently refit preset folds."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import time
from types import SimpleNamespace

import eval_feature_loo as run
import baseline_matching
import loo_support as io
import portable_classifier

STATE={}


def one(index):
    import numpy as np
    from sklearn.preprocessing import normalize
    from sklearn.preprocessing._data import _handle_zeros_in_scale
    fold=STATE['folds'][index];queries=STATE['queries'];q=queries[index];indices=fold['train_indices']
    view=STATE['view'];record=STATE['records'][index];audit=STATE['audits'][index]
    model_path=STATE['out']/audit['model_path'];assert run.sha(model_path)==audit['model_sha256']
    model=run.read_gzip(model_path);names=model['feature_names'];metadata=model['metadata']
    expected_sources=[queries[j]['source_id'] for j in indices]
    assert metadata['training_source_ids']==expected_sources
    assert metadata['excluded_source_ids']==fold['excluded_source_ids']
    assert metadata['fold']==index and q['source_id'] not in expected_sources
    assert metadata['config']['C']==run.CONFIGS[view] and metadata['config']['selection']=='none'
    assert audit['train_source_ids_sha256']==io.digest(expected_sources)
    assert record['training_reports']==audit['training_reports']==len(indices)
    excluded=set(fold['excluded_source_ids']);excluded_features=Counter()
    for j,r in enumerate(queries):
        if r['source_id'] in excluded:excluded_features.update(STATE['features'][j].keys())
    expected_names=[k for k in STATE['names'] if STATE['df'][k]>excluded_features[k]]
    assert names==expected_names
    assert audit['feature_names_sha256']==io.digest(names)
    # Audit-only maxima over all inputs, then remove the complete held-out group.
    # These statistics are never supplied to training.
    group=STATE['groups'][index]
    maxima=[next((value for value,g in STATE['maxima'][k] if g!=group),0.) for k in names]
    scale=_handle_zeros_in_scale(np.asarray(maxima,dtype=float),copy=True)
    assert io.digest(scale.tolist())==audit['scaling_sha256']
    prediction=portable_classifier.predict(model,STATE['features'][index])
    assert prediction['label']==record['classifier']
    assert prediction['scores']==record['scores']
    assert record['truth']==q['truth'] and record['query_id']==q['source_id'] and record['fold']==index
    columns=np.asarray([STATE['column'][k] for k in names]);matrix=STATE['matrix'][:,columns]
    reference=normalize(matrix[indices].multiply(1/scale),norm='l2')
    query=normalize(matrix[index].multiply(1/scale),norm='l2')
    similarities=(query@reference.T).toarray()[0]
    position={queries[j]['source_id']:k for k,j in enumerate(indices)}
    cases=[c for c in STATE['cases'] if c['source_id'] in position and io.eligible(c,q)]
    ranked=sorted([{'first_level_label':c['label'],'score_norm':float(similarities[position[c['source_id']]])}
                   for c in cases],key=lambda r:-r['score_norm'])
    assert baseline_matching.decide(ranked)['label']==record['k4']
    assert len(cases)==record['candidate_count']
    difference=None
    if index in STATE['refit_indices']:
        config=metadata['config']
        fitted=run.training.fit([STATE['features'][j] for j in indices],[queries[j]['truth'] for j in indices],config)
        exported=run.training.export(fitted,view,config)
        assert exported['feature_names']==names and exported['classes']==model['classes']
        difference=max([abs(a-b) for aa,bb in zip(exported['coefficients'],model['coefficients']) for a,b in zip(aa,bb)]+
                       [abs(a-b) for a,b in zip(exported['intercept'],model['intercept'])])
        assert difference<1e-8
        assert run.training.predict(fitted,[STATE['features'][index]])[0]==record['classifier']
    return difference


def await_summary(out,view,wait):
    while True:
        path=out/('summary.json' if (out/'summary.json').exists() else 'summary.partial.json')
        try:
            summary=io.read(path)
            if view in summary['results']:return summary
        except (FileNotFoundError,ValueError):pass
        if not wait:raise ValueError('LOO representation is not complete: '+view)
        print('waiting for complete LOO representation',view,flush=True);time.sleep(10)


def validate(out,jobs,wait=False):
    from sklearn.feature_extraction import DictVectorizer
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    plan=io.read(out/'plan.json')
    assert plan['views']==run.CONFIGS
    for path,digest in plan['source_sha256'].items():
        path=Path(path);folder='runtime' if path.parent==run.SCRIPTS else 'experiment'
        assert run.sha(out/'source_snapshot'/folder/path.name)==digest
        assert run.sha(path)==digest
    for path,digest in plan['input_sha256'].items():
        assert run.sha(path)==digest and run.sha(out/'inputs'/Path(path).name)==digest
    args=SimpleNamespace(reference=out,context_root=Path(plan['context_root']),
        reports_root=Path(plan['dataset_audit']['reports_root']),gt_labels=Path(plan['dataset_audit']['truth_source']))
    prepared,contexts,base,folds,audit,cache_hashes=run.load(args)
    assert cache_hashes==plan['context_sha256'] and audit==plan['dataset_audit']
    assert run.sha(args.gt_labels)==plan['gt_sha256']
    assert folds==io.read(out/'folds.json')
    assert io.read(out/'raw_log_validation.json')['status']=='passed'
    queries=prepared['reports'];groups=io.source_groups(queries,'source')
    refit={0,len(queries)//2,len(queries)-1}
    for label in io.LABELS:refit.add(next(i for i,q in enumerate(queries) if label in q['truth']))
    STATE.clear();STATE.update(out=out,queries=queries,cases=prepared['cases'],folds=folds,groups=groups,refit_indices=refit)
    results={}
    for view in run.CONFIGS:
        summary=await_summary(out,view,wait)
        features=[run.vector(view,b,c) for b,c in zip(base,contexts)]
        dictionary=DictVectorizer(sparse=True);matrix=dictionary.fit_transform(features)
        names=dictionary.get_feature_names_out().tolist();df=Counter(k for row in features for k in row)
        maxima={}
        for group,values in zip(groups,features):
            for key,value in values.items():
                top=dict((g,v) for v,g in maxima.get(key,()))
                top[group]=max(top.get(group,0.),abs(value))
                maxima[key]=sorted(((v,g) for g,v in top.items()),reverse=True)[:2]
        records=io.read(out/f'predictions/{view}.json');audits=io.read(out/f'fold_audits/{view}.json')
        assert [r['query_id'] for r in records]==[q['source_id'] for q in queries]
        assert len(audits)==len(records)==len(folds)==plan['queries']
        for key in ('classifier','k4'):assert io.metrics(records,key)==summary['results'][view][key]
        STATE.update(view=view,features=features,matrix=matrix,names=names,column=dictionary.vocabulary_,
                     df=df,maxima=maxima,records=records,audits=audits)
        differences=[]
        with ProcessPoolExecutor(max_workers=jobs,mp_context=multiprocessing.get_context('fork')) as pool:
            for count,difference in enumerate(pool.map(one,range(len(folds)),chunksize=1),1):
                if difference is not None:differences.append(difference)
                if count%100==0 or count==len(folds):print('validated',view,count,'/',len(folds),flush=True)
        results[view]={'folds':len(folds),'portable_replays':len(folds),'independent_cosine_k4_replays':len(folds),
            'all_training_vocabularies_and_scalers_verified':True,'independent_refits':len(differences),
            'max_parameter_difference':max(differences)}
        io.write(out/'validation.partial.json',{'status':'partial','views':results})
    while wait and not (out/'summary.json').exists():time.sleep(1)
    assert not io.read(out/'summary.json')['partial']
    result={'status':'passed','n':len(queries),'views':results,'refit_indices':sorted(refit),
        'independent_new_data_test':False,'note':'All stored fold vocabularies/scales and exclusions checked; all predictions replayed; preset folds independently refit.'}
    io.write(out/'validation.json',result)
    print('all feature LOO checks passed',flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--jobs',type=int,default=8)
    parser.add_argument('--wait',action='store_true',help='Validate each completed representation while the evaluator continues')
    args=parser.parse_args();validate(args.out,args.jobs,args.wait)
