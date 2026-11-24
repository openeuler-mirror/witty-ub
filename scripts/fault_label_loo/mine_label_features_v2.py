#!/usr/bin/env python3
"""Learn predictive log observations from external GT using the frozen v5 split."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil

import skill_runtime
from skill_runtime import SCRIPTS
import baseline_matching
import classifier_training
import eval_loo
import feature_vectors
import loo_support as io
import mined_log_features_v2 as extraction
import portable_classifier

CONFIGS=[{'id':f'c{c}_{selection}_{weight or "natural"}','C':c,'selection':selection,'class_weight':weight}
         for selection,weight in (('none',None),('chi2_500',None),('chi2_500','balanced')) for c in (.1,1.)]+[{'id':f'c{c}_stable_1000','C':c,'selection':'stable_1000','class_weight':None} for c in (.1,1.)]


def fit(features,truths,config):
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.feature_selection import chi2
    from sklearn.preprocessing import MaxAbsScaler
    from sklearn.linear_model import LogisticRegression
    dictionary=DictVectorizer(sparse=True)
    x=dictionary.fit_transform(features)
    scaling=MaxAbsScaler().fit(x);x=scaling.transform(x)
    indices=[];labels=[];weights=[]
    for i,truth in enumerate(truths):
        for label in truth:indices.append(i);labels.append(label);weights.append(1/len(truth))
    scores,_=chi2(x[indices].multiply(np.asarray(weights)[:,None]),labels)
    scores=np.nan_to_num(scores,nan=0.,posinf=0.)
    if config['selection']=='none':columns=np.arange(x.shape[1])
    elif config['selection']=='stable_1000':
        support=np.asarray((x>0).sum(axis=0)).ravel()
        eligible=np.flatnonzero(support>=3)
        columns=np.sort(eligible[np.argsort(-scores[eligible],kind='stable')[:1000]])
        if not len(columns):columns=np.arange(min(1000,x.shape[1]))
    else:columns=np.sort(np.argsort(-scores,kind='stable')[:500])
    model=LogisticRegression(C=config['C'],class_weight=config['class_weight'],solver='lbfgs',max_iter=1200,tol=1e-4)
    model.fit(x[indices][:,columns],labels,sample_weight=weights)
    return dictionary,scaling,columns,model,scores


def predict(model,features):
    dictionary,scaling,columns,classifier,_=model
    return classifier.predict(scaling.transform(dictionary.transform(features))[:,columns]).tolist()


def export(model,view,config):
    dictionary,scaling,columns,classifier,_=model
    return {'schema_version':portable_classifier.VERSION,'kind':'logistic','view':view,
        'classes':classifier.classes_.tolist(),'feature_names':dictionary.get_feature_names_out()[columns].tolist(),
        'coefficients':(classifier.coef_/scaling.scale_[columns]).tolist(),'intercept':classifier.intercept_.tolist(),
        'metadata':{'feature_version':extraction.VERSION,'view':view,'config':config}}


def metric_fit(features,truths,supervised):
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import MaxAbsScaler
    from sklearn.feature_selection import chi2
    dictionary=DictVectorizer(sparse=True);x=dictionary.fit_transform(features)
    scaling=MaxAbsScaler().fit(x);x=scaling.transform(x)
    if supervised:
        indices=[];labels=[];weights=[]
        for i,truth in enumerate(truths):
            for label in truth:indices.append(i);labels.append(label);weights.append(1/len(truth))
        scores,_=chi2(x[indices].multiply(np.asarray(weights)[:,None]),labels)
        scores=np.nan_to_num(scores,nan=0.,posinf=0.)
        columns=np.sort(np.argsort(-scores,kind='stable')[:500])
        weights=np.sqrt(scores[columns]/(scores[columns].max() or 1.))
    else:columns=np.arange(x.shape[1]);weights=np.ones(len(columns))
    return dictionary,scaling,columns,weights


def metric_predict(metric,fit_features,query_features,cases,source_position):
    import numpy as np
    from sklearn.preprocessing import normalize
    dictionary,scaling,columns,weights=metric
    def transform(features):return normalize(scaling.transform(dictionary.transform(features))[:,columns].multiply(weights),norm='l2')
    reference=transform(fit_features);query=transform(query_features)
    similarities=(query@reference.T).toarray()
    result=[]
    for row in similarities:
        ranked=sorted([{'first_level_label':case['label'],'score_norm':float(row[source_position[case['source_id']]])}
                       for case in cases],key=lambda r:-r['score_norm'])
        result.append(baseline_matching.decide(ranked)['label'])
    return result


def summarize_predictions(queries,indices,predicted,baseline=None):
    records=[{'query_id':queries[i]['source_id'],'truth':queries[i]['truth'],
              'baseline':baseline[j] if baseline else p,'prediction':p} for j,(i,p) in enumerate(zip(indices,predicted))]
    return io.metrics(records,'prediction'),records


def extract_all(prepared,root,data_root):
    reports={}
    reference=root.parent
    for i,q in enumerate(prepared['reports'],1):
        path=root/'context_cache'/f'{i-1:04d}.json.gz'
        if path.exists():
            with gzip.open(path,'rt') as stream:context=json.load(stream)
        else:
            with gzip.open(reference/'context_cache'/f'{i-1:04d}.json.gz','rt') as stream:base=json.load(stream)
            expected=q['structured']['log'].get('provenance',{}).get('files',[])
            context=extraction.upgrade(base,data_root/q['group']/q['name'],expected)
            path.parent.mkdir(parents=True,exist_ok=True)
            with gzip.open(path,'wt') as stream:json.dump(context,stream,ensure_ascii=False)
        reports[q['source_id']]=context
        if i%25==0 or i==len(prepared['reports']):print('unit-aware context extracted',i,'/',len(prepared['reports']),flush=True)
    return reports


def associations(queries,indices,maps):
    labels=io.LABELS;support=Counter();by_label={l:Counter() for l in labels};scenes={}
    totals=Counter(l for i in indices for l in queries[i]['truth'])
    for i in indices:
        present={k for k,v in maps[i].items() if v>0}
        support.update(present)
        for label in queries[i]['truth']:
            by_label[label].update(present)
            for key in present:scenes.setdefault((label,key),set()).add(queries[i]['scene'])
    result={}
    n=len(indices)
    for label in labels:
        items=[]
        for key,hits in by_label[label].items():
            df=support[key]
            if df<3 or hits<2:continue
            p=(hits+.5)/(totals[label]+1);other=(df-hits+.5)/(n-totals[label]+1)
            score=math.log(p/other)*math.sqrt(hits)
            items.append({'feature':key,'label_hits':hits,'feature_reports':df,'label_reports':totals[label],
                          'precision_in_train':hits/df,'lift':(hits/df)/(totals[label]/n),
                          'log_odds_score':score,'supporting_scenes':len(scenes[(label,key)])})
        result[label]=sorted(items,key=lambda row:(-row['log_odds_score'],-row['label_hits'],row['feature']))[:80]
    return result


def run(args):
    import sklearn
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    prepared=io.read(args.reference/'inputs/prepared.json');raw=io.read(args.reference/'inputs/raw_observations.json')
    split=io.read(args.reference/'split.json');root=args.out
    audit=eval_loo.audit_dataset(prepared,args.reports_root,args.gt_labels)
    root.mkdir(parents=True,exist_ok=True)
    plan={'feature_version':extraction.VERSION,'views':extraction.VIEWS,'configs':CONFIGS,
          'split_sha256':hashlib.sha256((args.reference/'split.json').read_bytes()).hexdigest(),
          'gt_sha256':hashlib.sha256(args.gt_labels.read_bytes()).hexdigest(),'dataset_audit':audit,
          'selection':'train-only fixed 3 grouped folds; accuracy then macro-F1; preset config order ties'}
    if (root/'plan.json').exists():assert io.read(root/'plan.json')==json.loads(json.dumps(plan))
    else:
        io.write(root/'plan.json',plan);shutil.copy2(args.reference/'split.json',root/'split.json')
        snapshot=root/'source_snapshot';snapshot.mkdir()
        for path in (Path(__file__),SCRIPTS/'mined_log_features.py',SCRIPTS/'mined_log_features_v2.py',SCRIPTS/'log_message_features.py'):
            shutil.copy2(path,snapshot/path.name)
    contexts=extract_all(prepared,root,args.data_root)
    base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in prepared['reports']]
    maps={view:[extraction.vector(view,base[i],contexts[q['source_id']]) for i,q in enumerate(prepared['reports'])] for view in extraction.VIEWS}
    train,valid=split['train_indices'],split['validation_indices'];queries=prepared['reports']
    io.write(root/'label_associations.json',associations(queries,train,maps['all_context_v2']))
    selections={};fold_results=[]
    for view,features in maps.items():
        candidates=[]
        for config in CONFIGS:
            all_indices=[];all_predictions=[];selected=[]
            for fold in split['inner_folds']:
                a,b=fold['train_indices'],fold['validation_indices']
                model=fit([features[i] for i in a],[queries[i]['truth'] for i in a],config)
                pred=predict(model,[features[i] for i in b]);all_indices+=b;all_predictions+=pred
                selected.append(model[0].get_feature_names_out()[model[2]].tolist())
            metrics,_=summarize_predictions(queries,all_indices,all_predictions)
            candidates.append({'config':config,'metrics':metrics,'fold_feature_names':selected})
            print('CV',view,config['id'],metrics['hits'],'/',metrics['n'],flush=True)
        best=max(candidates,key=lambda row:(row['metrics']['accuracy'],row['metrics']['macro_f1']))
        selections[view]={'classifier':best,'all_configs':candidates}
        metric_candidates=[]
        for supervised in (False,True):
            ii=[];pp=[]
            for fold in split['inner_folds']:
                a,b=fold['train_indices'],fold['validation_indices'];sources={queries[i]['source_id'] for i in a}
                metric=metric_fit([features[i] for i in a],[queries[i]['truth'] for i in a],supervised)
                cases=[c for c in prepared['cases'] if c['source_id'] in sources]
                pred=metric_predict(metric,[features[i] for i in a],[features[i] for i in b],cases,
                                    {queries[i]['source_id']:j for j,i in enumerate(a)})
                ii+=b;pp+=pred
            metrics,_=summarize_predictions(queries,ii,pp)
            metric_candidates.append({'supervised':supervised,'metrics':metrics})
        selections[view]['k4_candidates']=metric_candidates
        selections[view]['k4']=max(metric_candidates,key=lambda row:(row['metrics']['accuracy'],row['metrics']['macro_f1']))
    # Freeze all choices before any held-out prediction is calculated.
    io.write(root/'training_selection.json',selections)
    selected_primary=max(selections,key=lambda v:(selections[v]['classifier']['metrics']['accuracy'],selections[v]['classifier']['metrics']['macro_f1']))
    io.write(root/'primary_selection.json',{'view':selected_primary,'chosen_from':'training CV only'})
    baselines={r['query_id']:r for r in io.read(args.reference/'classifier/validation_predictions.json')}
    baseline=[baselines[queries[i]['source_id']]['all_feature_k4'] for i in valid]
    validation={};sources={queries[i]['source_id'] for i in train};cases=[c for c in prepared['cases'] if c['source_id'] in sources]
    for view,features in maps.items():
        config=selections[view]['classifier']['config']
        model=fit([features[i] for i in train],[queries[i]['truth'] for i in train],config)
        exported=export(model,view,config)
        exported['metadata'].update(training_source_ids=split['train_source_ids'],split_sha256=plan['split_sha256'])
        pred=predict(model,[features[i] for i in valid])
        assert pred==[portable_classifier.predict(exported,features[i])['label'] for i in valid]
        metrics,records=summarize_predictions(queries,valid,pred,baseline)
        io.write(root/f'models/{view}.json',exported);io.write(root/f'predictions/{view}_classifier.json',records)
        metric=metric_fit([features[i] for i in train],[queries[i]['truth'] for i in train],selections[view]['k4']['supervised'])
        p=metric_predict(metric,[features[i] for i in train],[features[i] for i in valid],cases,
                         {queries[i]['source_id']:j for j,i in enumerate(train)})
        k4,records=summarize_predictions(queries,valid,p,baseline);io.write(root/f'predictions/{view}_k4.json',records)
        validation[view]={'classifier':metrics,'k4':k4}
        print('holdout',view,'classifier',metrics['hits'],'K4',k4['hits'],flush=True)
    result={'validation':validation,'primary_selected_on_training':selected_primary,'train':len(train),'validation_n':len(valid),
        'split_sha256':plan['split_sha256'],'gt_sha256':plan['gt_sha256'],'feature_version':extraction.VERSION,
        'note':'Exploratory supervised feature discovery; v5 holdout was seen before; no root-cause claim for statistical patterns.'}
    io.write(root/'summary.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,required=True);parser.add_argument('--reports-root',type=Path,required=True)
    parser.add_argument('--gt-labels',type=Path,required=True)
    run(parser.parse_args())
