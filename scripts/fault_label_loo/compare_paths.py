#!/usr/bin/env python3
"""Mixed-data K4 LOO and persisted grouped random holdout classifier comparison."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import skill_runtime
from skill_runtime import SCRIPTS
import all_feature_matching as pairwise
import baseline_matching as baseline
import combination_matching as three_channel
import classifier_matching
import classifier_training as training
import eval_loo
import feature_vectors as vectors
import fixed_matching
import loo_support as io
import portable_classifier

SEED=1717
VIEWS=('base_observations','all_observations','all_observations_and_retrieval')
CONFIGS=[{'id':f'logistic_c{c}','kind':'logistic','C':c,'class_weight':None} for c in (.1,1.,10.)]+[
    {'id':f'extra_trees_d{depth}','kind':'extra_trees','depth':depth} for depth in (6,12)]


def split_dataset(prepared,root,input_hash):
    from sklearn.model_selection import StratifiedGroupKFold
    queries=prepared['reports']
    groups=io.source_groups(queries,'source')
    counts=Counter(label for q in queries for label in q['truth'])
    primary=[min(q['truth'],key=lambda label:(counts[label],label)) for q in queries]
    path=root/'split.json'
    if path.exists():
        split=io.read(path)
        assert split['input_sha256']==input_hash and split['seed']==SEED
        return split
    outer=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=SEED)
    train,valid=next(outer.split(list(range(len(queries))),primary,groups))
    train,valid=train.tolist(),valid.tolist()
    inner=[]
    splitter=StratifiedGroupKFold(n_splits=3,shuffle=True,random_state=SEED+1)
    for number,(a,b) in enumerate(splitter.split(train,[primary[i] for i in train],[groups[i] for i in train])):
        inner.append({'fold':number,'train_indices':[train[i] for i in a],'validation_indices':[train[i] for i in b]})
    split={'schema':'persisted-grouped-holdout-v1','input_sha256':input_hash,'seed':SEED,
        'method':'first fold of shuffled 5-way stratified source groups; fixed before fitting',
        'stratum':'rarest external truth label per report, alphabetical ties',
        'train_indices':train,'validation_indices':valid,'inner_folds':inner,
        'train_source_ids':[queries[i]['source_id'] for i in train],
        'validation_source_ids':[queries[i]['source_id'] for i in valid],
        'assignments':[{'query_id':q['source_id'],'group':groups[i],'stratum':primary[i],
                        'partition':'train' if i in train else 'validation'} for i,q in enumerate(queries)]}
    assert not {groups[i] for i in train}&{groups[i] for i in valid}
    split['counts']={'train':len(train),'validation':len(valid)}
    split['label_counts']={partition:dict(Counter(label for i in indices for label in queries[i]['truth']))
                           for partition,indices in (('train',train),('validation',valid))}
    io.write(path,split)
    return split


class Banks:
    def __init__(self,prepared,raw,root):
        self.queries=prepared['reports'];self.root=root
        self.raw=raw
        self.cases=[{**c,'raw_observations':raw['reports'][c['source_id']]} for c in prepared['cases']]
        groups=io.source_groups(self.queries,'source')
        self.groups={q['source_id']:g for q,g in zip(self.queries,groups)}
        self.case_vectors={c['id']:vectors.build_observations(c['profile'],c['structured'],c['raw_observations']) for c in self.cases}
        self.query_vectors={q['source_id']:vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in self.queries}

    def candidates(self,index,sources):
        q=self.queries[index]
        return [c for c in self.cases if c['source_id'] in sources and io.eligible(c,q)
                and self.groups[c['source_id']]!=self.groups[q['source_id']]]

    def ranked(self,index,cases):
        q=self.queries[index]
        base=baseline.rank_base(q['profile'],cases)
        old=three_channel.apply_default(base,q['structured'],{c['id']:c['structured'] for c in cases})
        all_rows=pairwise.apply(old,self.query_vectors[q['source_id']],self.case_vectors,
                                {c['id']:c['source_id'] for c in cases})
        return {'base_k4':base,'three_channel_k4':old,'all_feature_k4':all_rows}

    def build(self,train_indices,query_indices,name):
        sources={self.queries[i]['source_id'] for i in train_indices}
        path=self.root/'banks'/(name+'.json.gz')
        if path.exists():
            with gzip.open(path,'rt') as stream:bank=json.load(stream)
            assert bank['candidate_source_ids']==sorted(sources)
            return bank
        bank={'candidate_source_ids':sorted(sources),'queries':{}}
        for count,index in enumerate(query_indices,1):
            q=self.queries[index];qid=q['source_id']
            cases=self.candidates(index,sources)
            ranked=self.ranked(index,cases)
            rows=ranked['all_feature_k4']
            bank['queries'][qid]={'features':{view:classifier_matching.features(q['profile'],q['structured'],
                self.raw['reports'][qid],rows,view) for view in VIEWS},
                'decisions':{key:fixed_matching.decide(q['profile'],q['structured'],self.raw['reports'][qid],r)['label']
                             for key,r in ranked.items()},'candidate_count':len(cases),
                'top20':[r['case_id'] for r in rows[:20]]}
            if count%100==0:print(name,'feature bank',count,'/',len(query_indices),flush=True)
        path.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(path,'wt') as stream:json.dump(bank,stream,ensure_ascii=False,allow_nan=False)
        return bank

    def features(self,bank,indices,view):
        return [bank['queries'][self.queries[i]['source_id']]['features'][view] for i in indices]


def k4_loo(banks,out):
    path=out/'k4_loo/predictions.json'
    if path.exists():return io.read(path)
    sources={q['source_id'] for q in banks.queries};records=[]
    for index,q in enumerate(banks.queries):
        cases=banks.candidates(index,sources)
        ranked=banks.ranked(index,cases)
        decisions={key:fixed_matching.decide(q['profile'],q['structured'],banks.raw['reports'][q['source_id']],rows)
                   for key,rows in ranked.items()}
        records.append({'query_id':q['source_id'],'truth':q['truth'],'baseline':decisions['three_channel_k4']['label'],
            **{key:d['label'] for key,d in decisions.items()},'decision':decisions['all_feature_k4'],
            'excluded_source_ids':sorted(s for s in sources if banks.groups[s]==banks.groups[q['source_id']]),
            'candidate_count':len(cases)})
        if (index+1)%50==0 or index+1==len(banks.queries):
            io.write(out/'k4_loo/predictions.partial.json',records)
            print('mixed K4 LOO',index+1,'/',len(banks.queries),flush=True)
    io.write(path,records)
    io.write(out/'k4_loo/summary.json',{key:io.metrics(records,key) for key in ranked})
    return records


def fit_classifiers(banks,split,out):
    queries=banks.queries;selection={view:{c['id']:0 for c in CONFIGS} for view in VIEWS}
    for fold in split['inner_folds']:
        a,b=fold['train_indices'],fold['validation_indices']
        bank=banks.build(a,a+b,f'inner_{fold["fold"]}')
        for view in VIEWS:
            fit,test=banks.features(bank,a,view),banks.features(bank,b,view)
            for config in CONFIGS:
                fitted=training.fit_model(fit,[queries[i]['truth'] for i in a],config)
                predicted=training.model_predictions(fitted,test)
                selection[view][config['id']]+=sum(p in queries[i]['truth'] for i,p in zip(b,predicted))
        print('inner training fold complete',fold['fold'],flush=True)
    io.write(out/'classifier/inner_selection.json',selection)
    train,valid=split['train_indices'],split['validation_indices']
    bank=banks.build(train,train+valid,'outer_train')
    records={i:{'query_id':queries[i]['source_id'],'truth':queries[i]['truth'],
        'baseline':bank['queries'][queries[i]['source_id']]['decisions']['three_channel_k4'],
        **bank['queries'][queries[i]['source_id']]['decisions']} for i in train+valid}
    models={}
    for view in VIEWS:
        config=max(CONFIGS,key=lambda c:selection[view][c['id']])
        fitted=training.fit_model(banks.features(bank,train,view),[queries[i]['truth'] for i in train],config)
        exported=training.export_model(fitted,config,view)
        exported['metadata']={'model_id':'train-only-'+io.digest(exported)[:12],
            'feature_version':vectors.VERSION,'config':config,'seed':SEED,
            'training_source_ids':split['train_source_ids'],
            'validation_source_ids':split['validation_source_ids'],
            'split_sha256':hashlib.sha256((out/'split.json').read_bytes()).hexdigest()}
        io.write(out/'classifier/models'/(view+'.json'),exported)
        all_features=banks.features(bank,train+valid,view)
        prediction=training.model_predictions(fitted,all_features)
        assert prediction==[portable_classifier.predict(exported,x)['label'] for x in all_features]
        for i,predicted in zip(train+valid,prediction):records[i][view]=predicted
        models[view]={'selected_config':config,'inner_correct':selection[view][config['id']],
                      'portable_parity_checks':len(prediction)}
        print('trained/exported',view,config['id'],flush=True)
    result={}
    for partition,indices in (('train',train),('validation',valid)):
        rows=[records[i] for i in indices]
        io.write(out/f'classifier/{partition}_predictions.json',rows)
        result[partition]={key:io.metrics(rows,key) for key in ('base_k4','three_channel_k4','all_feature_k4',*VIEWS)}
    io.write(out/'classifier/summary.json',{'models':models,'metrics':result})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','raw','reports-root','gt-labels','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',choices=('prepare','k4','classifier','all'),default='all')
    args=parser.parse_args()
    import sklearn
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    prepared,raw=io.read(args.prepared),io.read(args.raw)
    assert raw['prepared_sha256']==hashlib.sha256(args.prepared.read_bytes()).hexdigest()
    audit=eval_loo.audit_dataset(prepared,args.reports_root,args.gt_labels)
    root=args.out;root.mkdir(parents=True,exist_ok=True)
    manifest={'input_sha256':io.digest({'prepared':prepared,'raw':raw}),'feature_version':vectors.VERSION,
        'seed':SEED,'feature_block_budget':.30,'block_weights':{b:.30/len(pairwise.BLOCKS) for b in pairwise.BLOCKS},
        'classifier_views':VIEWS,'classifier_configs':CONFIGS,'dataset_audit':audit,'source_sha256':{}}
    if (root/'manifest.json').exists():
        old=io.read(root/'manifest.json');assert old['input_sha256']==manifest['input_sha256']
        for path,digest in old['source_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    else:
        for source in list(SCRIPTS.glob('*.py'))+list(Path(__file__).parent.glob('*.py')):
            manifest['source_sha256'][str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
            target=root/'source_snapshot'/('runtime' if source.parent==SCRIPTS else 'experiment')/source.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        io.write(root/'manifest.json',manifest)
        (root/'inputs').mkdir()
        shutil.copy2(args.prepared,root/'inputs/prepared.json');shutil.copy2(args.raw,root/'inputs/raw_observations.json')
    split=split_dataset(prepared,root,manifest['input_sha256'])
    banks=Banks(prepared,raw,root)
    coverage={name:sum(bool(pairwise.blocks(v)[name]) for v in banks.query_vectors.values()) for name in pairwise.BLOCKS}
    io.write(root/'feature_coverage.json',{'blocks':coverage,'queries':len(banks.queries),
        'feature_keys':sorted({k for v in banks.query_vectors.values() for k in v}),
        'missingness':'unknown pairs add zero; observed zero preserved; file layout and identities excluded'})
    if args.stage in ('k4','all'):k4_loo(banks,root)
    if args.stage in ('classifier','all'):fit_classifiers(banks,split,root)
    print('stage complete',args.stage,flush=True)


if __name__=='__main__':main()
