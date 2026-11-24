#!/usr/bin/env python3
"""Bounded train-only comparison of linear, kernel and tree feature mappings."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import shutil

import skill_runtime
import eval_loo
import feature_vectors
import loo_support as io
import mined_log_features_v2 as extraction

VIEWS=('v5','numeric_units','numeric_context','all_context_v2')
CONFIGS=[{'id':f'svc_{kernel}_c{c}','kind':'svc','kernel':kernel,'C':c}
         for kernel,c in (('rbf',1.),('rbf',10.),('linear',.1),('linear',1.))]+[
    {'id':f'extratrees_leaf{leaf}','kind':'trees','leaf':leaf} for leaf in (2,5)]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit(features,truths,config):
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.feature_selection import chi2
    from sklearn.preprocessing import MaxAbsScaler
    from sklearn.svm import SVC
    from sklearn.ensemble import ExtraTreesClassifier
    dictionary=DictVectorizer(sparse=True);x=dictionary.fit_transform(features)
    scaling=MaxAbsScaler().fit(x);x=scaling.transform(x)
    indices=[];labels=[];weights=[]
    for i,truth in enumerate(truths):
        for label in truth:indices.append(i);labels.append(label);weights.append(1/len(truth))
    scores,_=chi2(x[indices].multiply(np.asarray(weights)[:,None]),labels)
    scores=np.nan_to_num(scores,nan=0.,posinf=0.)
    eligible=np.flatnonzero(np.asarray((x>0).sum(axis=0)).ravel()>=3)
    columns=np.sort(eligible[np.argsort(-scores[eligible],kind='stable')[:1000]])
    if not len(columns):raise ValueError('No training features with support >= 3')
    if config['kind']=='svc':
        classifier=SVC(kernel=config['kernel'],C=config['C'],gamma='scale',class_weight=None,random_state=1717)
    else:
        classifier=ExtraTreesClassifier(n_estimators=300,min_samples_leaf=config['leaf'],max_features='sqrt',
            class_weight=None,random_state=1717,n_jobs=1)
    classifier.fit(x[indices][:,columns],labels,sample_weight=weights)
    return dictionary,scaling,columns,classifier


def predict(model,features):
    dictionary,scaling,columns,classifier=model
    return classifier.predict(scaling.transform(dictionary.transform(features))[:,columns]).tolist()


def summarize(queries,indices,predicted):
    records=[{'query_id':queries[i]['source_id'],'truth':queries[i]['truth'],'baseline':p,'prediction':p}
             for i,p in zip(indices,predicted)]
    return io.metrics(records,'prediction'),records


def run(args):
    import sklearn
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    root=args.out;root.mkdir(parents=True,exist_ok=True)
    reference=args.reference;split=io.read(reference/'split.json')
    prepared=io.read(reference/'inputs/prepared.json');raw=io.read(reference/'inputs/raw_observations.json')
    audit=eval_loo.audit_dataset(prepared,args.reports_root,args.gt_labels)
    queries=prepared['reports'];train=split['train_indices'];valid=split['validation_indices']
    groups=io.source_groups(queries,'source')
    assert not {groups[i] for i in train}&{groups[i] for i in valid}
    assert [queries[i]['source_id'] for i in train]==split['train_source_ids']
    assert [queries[i]['source_id'] for i in valid]==split['validation_source_ids']
    cache_paths=[args.context_root/'context_cache'/f'{i:04d}.json.gz' for i in range(len(queries))]
    plan={'views':VIEWS,'configs':CONFIGS,'preprocessing':'fold-local DictVectorizer, MaxAbsScaler, df>=3 then chi2 top1000',
        'selection':'pooled train 3-fold accuracy then macro-F1, preset order tie break; primary chosen before validation',
        'split_sha256':sha(reference/'split.json'),'gt_sha256':sha(args.gt_labels),'dataset_audit':audit,
        'software':{'sklearn':sklearn.__version__},'feature_version':extraction.VERSION,
        'source_sha256':{str(p):sha(p) for p in (Path(__file__),Path(extraction.__file__),Path(extraction.v1.__file__),
            Path(feature_vectors.__file__),Path(extraction.v1.log_message_features.__file__))},
        'cache_sha256':{p.name:sha(p) for p in cache_paths},
        'inputs_sha256':{p.name:sha(p) for p in (reference/'inputs/prepared.json',reference/'inputs/raw_observations.json')}}
    if (root/'plan.json').exists():assert io.read(root/'plan.json')==json.loads(json.dumps(plan))
    else:
        io.write(root/'plan.json',plan);shutil.copy2(reference/'split.json',root/'split.json')
        snapshot=root/'source_snapshot';snapshot.mkdir()
        for path in plan['source_sha256']:shutil.copy2(path,snapshot/Path(path).name)
    contexts=[]
    for path,q in zip(cache_paths,queries):
        with gzip.open(path,'rt') as stream:context=json.load(stream)
        assert context['schema_version']==extraction.VERSION
        assert {f['file']:f['sha256'] for f in context['provenance']['files']}=={
            f['file']:f['sha256'] for f in q['structured']['log']['provenance']['files']}
        contexts.append(context)
    base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in queries]
    selections={}
    for view in VIEWS:
        values=[extraction.vector(view,base[i],contexts[i]) for i in range(len(queries))]
        candidates=[]
        for config in CONFIGS:
            indices=[];predicted=[];vocabularies=[]
            for fold in split['inner_folds']:
                a,b=fold['train_indices'],fold['validation_indices']
                assert set(a)|set(b)==set(train) and not set(a)&set(b)
                assert not {groups[i] for i in a}&{groups[i] for i in b}
                model=fit([values[i] for i in a],[queries[i]['truth'] for i in a],config)
                names=model[0].get_feature_names_out()[model[2]].tolist()
                assert set(names)<={key for i in a for key in values[i]}
                vocabularies.append(names)
                indices+=b;predicted+=predict(model,[values[i] for i in b])
            assert sorted(indices)==sorted(train)
            metrics,records=summarize(queries,indices,predicted)
            candidates.append({'config':config,'metrics':metrics,'fold_features':vocabularies})
            io.write(root/f'cv_predictions/{view}_{config["id"]}.json',records)
            print('CV',view,config['id'],metrics['hits'],flush=True)
        selections[view]={'candidates':candidates,'selected':max(candidates,key=lambda c:(c['metrics']['accuracy'],c['metrics']['macro_f1']))}
    primary=max(VIEWS,key=lambda view:(selections[view]['selected']['metrics']['accuracy'],selections[view]['selected']['metrics']['macro_f1']))
    io.write(root/'training_selection.json',selections)
    io.write(root/'primary_selection.json',{'view':primary,'chosen_from':'training CV only'})
    validation={};checks={}
    for view in VIEWS:
        values=[extraction.vector(view,base[i],contexts[i]) for i in range(len(queries))]
        config=selections[view]['selected']['config']
        model=fit([values[i] for i in train],[queries[i]['truth'] for i in train],config)
        prediction=predict(model,[values[i] for i in valid]);metrics,records=summarize(queries,valid,prediction)
        validation[view]=metrics
        artifact={'view':view,'config':config,'feature_version':extraction.VERSION,'model':model,
                  'training_source_ids':split['train_source_ids'],'split_sha256':plan['split_sha256']}
        model_path=root/f'models/{view}.pickle';model_path.parent.mkdir(exist_ok=True)
        model_path.write_bytes(pickle.dumps(artifact))
        restored=pickle.loads(model_path.read_bytes())
        assert restored['training_source_ids']==split['train_source_ids']
        assert predict(restored['model'],[values[i] for i in valid])==prediction
        # Repeat fit, rather than relying solely on serialized prediction replay.
        refit=fit([values[i] for i in train],[queries[i]['truth'] for i in train],config)
        assert predict(refit,[values[i] for i in valid])==prediction
        checks[view]={'heldout_replays':len(valid),'independent_refit':'exact predictions','vocabulary_train_only':True,
                      'model_sha256':sha(model_path),'selected_feature_count':len(model[2])}
        io.write(root/f'predictions/{view}.json',records)
        print('validation',view,metrics['hits'],metrics['accuracy'],flush=True)
    summary={'train':len(train),'validation_n':len(valid),'primary_selected_on_training':primary,'validation':validation,
             'split_sha256':plan['split_sha256'],'gt_sha256':plan['gt_sha256'],
             'note':'Development comparison on a reused holdout; no claim of fresh external generalization or causality.'}
    io.write(root/'summary.json',summary);io.write(root/'validation.json',{'status':'passed','views':checks})
    rows=['|表示|训练3折命中|训练所选映射|验证命中|验证准确率|验证宏F1|','|---|---:|---|---:|---:|---:|']
    for view in VIEWS:
        selected=selections[view]['selected'];m=validation[view]
        rows.append(f'|{view}|{selected["metrics"]["hits"]}/{len(train)}|{selected["config"]["id"]}|{m["hits"]}/{len(valid)}|{m["accuracy"]:.2%}|{m["macro_f1"]:.4f}|')
    text='''# 特征映射对照

复用 v5 的 379 训练、95 验证和训练内部 3 折，未重新划分。候选表示与配置在 plan.json 中固定。
表示包括旧 v5、统一单位数值、行为统计合并、全部上下文。
映射包括线性 SVC、RBF SVC、ExtraTrees；所有方案使用相同的训练内词表、MaxAbsScaler、支持至少 3 份训练报告的 chi2 前 1000 维。
每个多标签报告重复为多个类别行，每报告权重之和为 1；命中任一真实标签计准确。
词表、缩放、支持筛选、chi2 和分类器全部在对应训练折拟合。
按训练内部命中率、宏 F1 选择各表示的配置及本轮主方案，写入 training_selection.json/primary_selection.json 后才计算验证预测。

'''+f'训练选择的主表示为 **{primary}**。\n\n'+'\n'.join(rows)+'''

这些成绩是已使用过的验证集上的开发对照，不是独立新测试。本轮不根据验证成绩改主方案，也不全量重训。
本轮与 Logistic 表格的区别同时包括映射类型、稳定特征筛选，不能把变化都归为非线性的独立收益。
ExtraTrees 的分裂权重以及 SVC 的边界由训练学习；它们不能直接解释成日志对物理根因的因果证明。
模型仅用 379 个来源拟合，pickle 为实验产物，默认 Agent 未接入这些模型。
源文件、输入、GT、划分与缓存哈希在 plan.json，模型哈希及重放/独立重拟合核验在 validation.json。
'''
    (root/'readme.md').write_text(text,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--context-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--reports-root',type=Path,required=True)
    parser.add_argument('--gt-labels',type=Path,required=True)
    run(parser.parse_args())
