#!/usr/bin/env python3
"""Frozen-config source LOO for mined features; fit every fold without its query."""
import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from collections import Counter
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import shutil

import skill_runtime
from skill_runtime import SCRIPTS
import eval_loo
import feature_vectors
import loo_support as io
import mined_log_features_v2 as extraction
import mine_label_features_v2 as training
import portable_classifier
import default_matching
import cosine_matching

# Fixed from the previous development study, before this LOO is run.
# These are comparisons, not an outer-LOO model/hyperparameter search.
CONFIGS={'v5':1.,'v1_numeric':.1,'numeric_units':1.,'templates':.1,
         'sequences':.1,'numeric_context':.1,'all_context_v2':.1}
STATE={}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_gzip(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def write_gzip(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,'wt',compresslevel=1) as stream:json.dump(data,stream,ensure_ascii=False,allow_nan=False)


def vector(view,base,context):
    if view in ('templates','sequences'):return extraction.v1.vector(view,base,context)
    return extraction.vector(view,base,context)


def check_logs(item):
    query,data_root=item;directory=data_root/query['group']/query['name']
    expected=query['structured']['log']['provenance']['files']
    actual={str(p.relative_to(directory)) for p in directory.rglob('*')
            if p.is_file() and p.name.endswith(('.log','.log.gz'))}
    assert actual=={row['file'] for row in expected},query['source_id']
    checked=[]
    for row in expected:
        path=directory/row['file'];digest=hashlib.sha256()
        with (gzip.open if path.name.endswith('.gz') else open)(path,'rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        assert digest.hexdigest()==row['sha256'],str(path)
        checked.append({'file':row['file'],'sha256':digest.hexdigest()})
    return {'source_id':query['source_id'],'files':checked}


def load(args):
    prepared=io.read(args.reference/'inputs/prepared.json');raw=io.read(args.reference/'inputs/raw_observations.json')
    assert raw['prepared_sha256']==sha(args.reference/'inputs/prepared.json')
    audit=eval_loo.audit_dataset(prepared,args.reports_root,args.gt_labels)
    queries=prepared['reports'];groups=io.source_groups(queries,'source')
    contexts=[];cache_hashes={}
    for i,q in enumerate(queries):
        path=args.context_root/'context_cache'/f'{i:04d}.json.gz';context=read_gzip(path)
        assert context['schema_version']==extraction.VERSION
        expected={f['file']:f['sha256'] for f in q['structured']['log']['provenance']['files']}
        assert {f['file']:f['sha256'] for f in context['provenance']['files']}==expected
        contexts.append(context);cache_hashes[path.name]=sha(path)
    base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in queries]
    folds=[{'fold':i,'query_id':q['source_id'],'train_indices':[j for j in range(len(queries)) if groups[j]!=groups[i]],
            'excluded_source_ids':[r['source_id'] for j,r in enumerate(queries) if groups[j]==groups[i]]}
           for i,q in enumerate(queries)]
    for fold in folds:
        assert fold['fold'] not in fold['train_indices']
        assert not {groups[j] for j in fold['train_indices']}&{groups[fold['fold']]}
    return prepared,contexts,base,folds,audit,cache_hashes


def init_state(prepared,contexts,base,folds,out):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    STATE.clear();STATE.update(queries=prepared['reports'],cases=prepared['cases'],contexts=contexts,
                               base=base,folds=folds,out=out)


def one_fold(index):
    view=STATE['view'];features=STATE['features'];queries=STATE['queries'];fold=STATE['folds'][index]
    indices=fold['train_indices'];q=queries[index]
    truths=[queries[j]['truth'] for j in indices];values=[features[j] for j in indices]
    config={'id':f'c{CONFIGS[view]}_none_natural','C':CONFIGS[view],'selection':'none','class_weight':None}
    model=training.fit(values,truths,config)
    predicted=training.predict(model,[features[index]])[0]
    exported=training.export(model,view,config)
    if view in ('templates','sequences'):exported['metadata']['feature_version']=extraction.v1.VERSION
    train_ids=[queries[j]['source_id'] for j in indices]
    assert q['source_id'] not in train_ids
    exported['metadata'].update(training_source_ids=train_ids,excluded_source_ids=fold['excluded_source_ids'],fold=index,
                                protocol='source-leave-one-out-fixed-config-v1')
    portable=(default_matching.predict_numeric(exported,features[index]) if view=='numeric_units' else
              portable_classifier.predict(exported,features[index]))
    assert portable['label']==predicted
    source_set=set(train_ids)
    cases=[c for c in STATE['cases'] if c['source_id'] in source_set and io.eligible(c,q)]
    references={'schema_version':cosine_matching.VERSION,
        'sources':[{'source_id':queries[j]['source_id'],'vector':features[j]} for j in indices],'cases':cases}
    ranked,_=cosine_matching.rank(features[index],references,cases)
    k4=cosine_matching.decide(ranked)['label']
    path=STATE['out']/f'models/{view}/{index:04d}.json.gz';write_gzip(path,exported)
    audit={'fold':index,'query_id':q['source_id'],'training_reports':len(indices),
           'train_source_ids_sha256':io.digest(train_ids),'feature_count':len(exported['feature_names']),
           'feature_names_sha256':io.digest(exported['feature_names']),
           'scaling_sha256':io.digest(model[1].scale_.tolist()),'model_sha256':sha(path),
           'excluded_source_ids':fold['excluded_source_ids'],'model_path':str(path.relative_to(STATE['out']))}
    record={'fold':index,'query_id':q['source_id'],'group':q['group'],'truth':q['truth'],
            'classifier':predicted,'k4':k4,'scores':portable['scores'],'score_margin':portable['score_margin'],
            'baseline':predicted,'training_reports':len(indices),'candidate_count':len(cases)}
    return record,audit


def run(args):
    import sklearn,numpy,scipy,platform
    prepared,contexts,base,folds,audit,cache_hashes=load(args)
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    source_files=sorted(set(Path(__file__).parent.glob('*.py'))|set(SCRIPTS.glob('*.py')))
    # Verify that the reused feature caches were made by the same extractors.
    for name in ('mined_log_features.py','mined_log_features_v2.py','log_message_features.py'):
        assert (SCRIPTS/name).read_bytes()==(args.context_root/'source_snapshot'/name).read_bytes(),name
    plan={'protocol':'source-leave-one-out-fixed-config-v1','views':CONFIGS,
          'classifier':'logistic; C frozen per representation from previous development; no selection on this LOO',
          'k4':'fold-local vocabulary and MaxAbsScaler; unsupervised cosine; top4 margin0.05; report vectors per candidate source',
          'fold_local':['vocabulary','scaling','classifier weights','candidate sources'],
          'query_features':'label-blind; raw log message columns; no report answer or GT',
          'queries':len(folds),'source_groups':len(set(io.source_groups(prepared['reports'],'source'))),
          'dataset_audit':audit,'gt_sha256':sha(args.gt_labels),
          'input_sha256':{str(p):sha(p) for p in (args.reference/'inputs/prepared.json',args.reference/'inputs/raw_observations.json')},
          'context_root':str(args.context_root),'context_sha256':cache_hashes,
          'source_sha256':{str(p):sha(p) for p in source_files},
          'software':{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__},
          'independent_new_data_test':False,
          'limitation':'Features and configurations were developed using this dataset. No held-out query participates in its fold fit, but this is not fresh independent evaluation.'}
    if (out/'plan.json').exists():assert io.read(out/'plan.json')==json.loads(json.dumps(plan))
    else:
        io.write(out/'plan.json',plan);io.write(out/'folds.json',folds)
        io.write(out/'coverage.json',{'audit':audit,'included':[q['source_id'] for q in prepared['reports']],
            'excluded':prepared['excluded']})
        for p in source_files:
            target=out/'source_snapshot'/('runtime' if p.parent==SCRIPTS else 'experiment')/p.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        for name in ('prepared.json','raw_observations.json'):
            target=out/'inputs'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(args.reference/'inputs'/name,target)
    if not (out/'raw_log_validation.json').exists():
        with ThreadPoolExecutor(max_workers=min(args.jobs,4)) as pool:
            rows=list(pool.map(check_logs,((q,args.data_root) for q in prepared['reports'])))
        io.write(out/'raw_log_validation.json',{'status':'passed','reports':len(rows),'files':sum(len(r['files']) for r in rows),'rows':rows})
    print('input coverage, raw logs, feature caches and frozen source checked',flush=True)
    init_state(prepared,contexts,base,folds,out)
    results={}
    for view in CONFIGS:
        prediction_path=out/f'predictions/{view}.json'
        if prediction_path.exists():
            records=io.read(prediction_path)
            assert [r['query_id'] for r in records]==[q['source_id'] for q in prepared['reports']]
        else:
            STATE['view']=view
            STATE['features']=[vector(view,b,c) for b,c in zip(base,contexts)]
            records=[];audits=[]
            with ProcessPoolExecutor(max_workers=args.jobs,mp_context=multiprocessing.get_context('fork')) as pool:
                for count,(record,fold_audit) in enumerate(pool.map(one_fold,range(len(folds)),chunksize=1),1):
                    records.append(record);audits.append(fold_audit)
                    if count%25==0 or count==len(folds):
                        print(view,'source-LOO',count,'/',len(folds),flush=True)
                        io.write(out/f'progress/{view}.json',{'completed':count,'total':len(folds)})
            io.write(prediction_path,records);io.write(out/f'fold_audits/{view}.json',audits)
        results[view]={key:io.metrics(records,key) for key in ('classifier','k4')}
        print('completed',view,'classifier',results[view]['classifier']['hits'],'K4',results[view]['k4']['hits'],flush=True)
        io.write(out/'summary.partial.json',{'partial':True,'results':results})
    io.write(out/'summary.json',{'partial':False,'protocol':plan['protocol'],'n':len(folds),'results':results,
         'dataset_audit':audit,'independent_new_data_test':False,'configurations':CONFIGS,'all_models_fold_local':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','context-root','reports-root','data-root','gt-labels','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=8)
    run(parser.parse_args())
