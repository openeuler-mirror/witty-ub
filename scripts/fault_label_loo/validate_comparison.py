#!/usr/bin/env python3
"""Replay mixed K4 LOO, train-only model selection and holdout inference."""
import argparse
import hashlib
from pathlib import Path

import skill_runtime
import classifier_matching
import classifier_training as training
import compare_paths as experiment
import fixed_matching
import loo_support as io
import portable_classifier


def validate(root):
    manifest=io.read(root/'manifest.json');split=io.read(root/'split.json')
    prepared,raw=io.read(root/'inputs/prepared.json'),io.read(root/'inputs/raw_observations.json')
    assert io.digest({'prepared':prepared,'raw':raw})==manifest['input_sha256']==split['input_sha256']
    for path,digest in manifest['source_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        folder='runtime' if str(Path(path).parent)==str(experiment.SCRIPTS) else 'experiment'
        assert hashlib.sha256((root/'source_snapshot'/folder/Path(path).name).read_bytes()).hexdigest()==digest
    queries=prepared['reports'];groups=io.source_groups(queries,'source')
    train,valid=split['train_indices'],split['validation_indices']
    assert set(train)|set(valid)==set(range(len(queries))) and not set(train)&set(valid)
    assert not {groups[i] for i in train}&{groups[i] for i in valid}
    assert split['train_source_ids']==[queries[i]['source_id'] for i in train]
    assert split['validation_source_ids']==[queries[i]['source_id'] for i in valid]
    banks=experiment.Banks(prepared,raw,root)
    records=io.read(root/'k4_loo/predictions.json');metrics=io.read(root/'k4_loo/summary.json')
    assert [r['query_id'] for r in records]==[q['source_id'] for q in queries]
    sources={q['source_id'] for q in queries}
    for index,(q,record) in enumerate(zip(queries,records)):
        cases=banks.candidates(index,sources)
        matched=fixed_matching.match(q['profile'],cases,q['structured'],raw['reports'][q['source_id']])
        assert record['decision']==matched['decision']
        assert record['candidate_count']==len(cases)
        excluded=sorted(s for s in sources if banks.groups[s]==banks.groups[q['source_id']])
        assert record['excluded_source_ids']==excluded
        assert record['truth']==q['truth']
        variants=banks.ranked(index,cases)
        for key,rows in variants.items():
            assert record[key]==fixed_matching.decide(q['profile'],q['structured'],raw['reports'][q['source_id']],rows)['label']
        if (index+1)%100==0 or index+1==len(queries):print('K4 replay exact',index+1,flush=True)
    for key in metrics:assert io.metrics(records,key)==metrics[key]
    selection={view:{c['id']:0 for c in experiment.CONFIGS} for view in experiment.VIEWS}
    inner_trace=[]
    for fold in split['inner_folds']:
        a,b=fold['train_indices'],fold['validation_indices']
        assert set(a)|set(b)==set(train) and not set(a)&set(b)
        assert not {groups[i] for i in a}&{groups[i] for i in b}
        assert not (set(a)|set(b))&set(valid)
        bank=banks.build(a,a+b,f'inner_{fold["fold"]}')
        assert set(bank['candidate_source_ids'])=={queries[i]['source_id'] for i in a}
        assert set(bank['queries'])=={queries[i]['source_id'] for i in a+b}
        for view in experiment.VIEWS:
            x,y=banks.features(bank,a,view),banks.features(bank,b,view)
            for config in experiment.CONFIGS:
                fitted=training.fit_model(x,[queries[i]['truth'] for i in a],config)
                predicted=training.model_predictions(fitted,y)
                hits=sum(p in queries[i]['truth'] for i,p in zip(b,predicted))
                selection[view][config['id']]+=hits
                inner_trace.append({'fold':fold['fold'],'view':view,'config':config,'hits':hits,'n':len(b)})
        print('train-only selection reproduced',fold['fold'],flush=True)
    assert selection==io.read(root/'classifier/inner_selection.json')
    bank=banks.build(train,train+valid,'outer_train')
    assert set(bank['candidate_source_ids'])==set(split['train_source_ids'])
    assert not set(bank['candidate_source_ids'])&set(split['validation_source_ids'])
    summary=io.read(root/'classifier/summary.json')
    model_hashes={};replays=0
    models={view:io.read(root/'classifier/models'/(view+'.json')) for view in experiment.VIEWS}
    for view,model in models.items():
        assert model['metadata']['training_source_ids']==split['train_source_ids']
        assert model['metadata']['validation_source_ids']==split['validation_source_ids']
        assert model['metadata']['split_sha256']==hashlib.sha256((root/'split.json').read_bytes()).hexdigest()
        config=max(experiment.CONFIGS,key=lambda c:selection[view][c['id']])
        assert model['metadata']['config']==config
        names={name for x in banks.features(bank,train,view) for name in x}
        assert set(model['feature_names'])<=names
        model_hashes[view]=hashlib.sha256((root/'classifier/models'/(view+'.json')).read_bytes()).hexdigest()
    for partition,indices in (('train',train),('validation',valid)):
        predictions=io.read(root/f'classifier/{partition}_predictions.json')
        assert [r['query_id'] for r in predictions]==[queries[i]['source_id'] for i in indices]
        for index,record in zip(indices,predictions):
            q=queries[index];qid=q['source_id']
            assert record['truth']==q['truth']
            for key,predicted in bank['queries'][qid]['decisions'].items():assert record[key]==predicted
            rows=None
            if partition=='validation':
                cases=banks.candidates(index,set(split['train_source_ids']))
                matched=fixed_matching.match(q['profile'],cases,q['structured'],raw['reports'][qid])
                assert record['all_feature_k4']==matched['decision']['label']
                rows=matched['candidates']
            for view,model in models.items():
                features=bank['queries'][qid]['features'][view]
                if rows is not None:
                    assert features==classifier_matching.features(q['profile'],q['structured'],raw['reports'][qid],rows,view)
                assert record[view]==portable_classifier.predict(model,features)['label']
                replays+=1
        for key in summary['metrics'][partition]:assert io.metrics(predictions,key)==summary['metrics'][partition][key]
    result={'status':'passed','mixed_loo_queries':len(records),'train_queries':len(train),
        'validation_queries':len(valid),'classifier_portable_replays':replays,
        'inner_selection_refits':len(inner_trace),'model_sha256':model_hashes,
        'split_sha256':hashlib.sha256((root/'split.json').read_bytes()).hexdigest(),
        'checks':['source/alias separation','training-only candidate statistics','training-only parameter selection',
                  'training-only feature vocabulary','shared Agent K4/classifier inference','complete metrics replay']}
    io.write(root/'validation/inner_selection_replay.json',inner_trace)
    io.write(root/'validation.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    print(validate(parser.parse_args().root))
