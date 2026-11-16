#!/usr/bin/env python3
"""Evaluate the historical fixed K4 baseline with each source group left out.

No classifier is loaded or fitted. This baseline explicitly retains
fixed_matching.match; the deployed Agent uses default_matching instead. Historical candidate labels are
known; the held-out query's external truth is used only for scoring afterwards.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import skill_runtime
from skill_runtime import SCRIPTS
import baseline_matching
import fixed_matching
import loo_support as evaluation

MODE = 'fixed_feature_vote_source_loo'


def audit_dataset(prepared, reports_root, truth_path):
    truths = evaluation.read(truth_path)
    actual = {f'reports/{group}/{p.name}': p for group in ('train','v7')
              for p in (reports_root/group).glob('*.json')}
    included = {q['source_id']: q for q in prepared['reports']}
    excluded = {q['source_id']: q for q in prepared.get('excluded',[])}
    assert set(actual)==included.keys()|excluded.keys(), 'Dataset coverage changed; regenerate prepared inputs'
    assert not included.keys()&excluded.keys()
    for qid, query in {**included,**excluded}.items():
        assert hashlib.sha256(actual[qid].read_bytes()).hexdigest()==query.get('report_sha256',query.get('sha256'))
        if qid in included:
            truth = set(truths[query['scene']]['一级标签'].split('/'))-baseline_matching.CONTROL
            assert truth==set(query['truth']), qid
        else:
            assert set(query['truth'])<=baseline_matching.CONTROL
    for case in prepared['cases']:
        assert case['source_id'] in included and case['label'] in included[case['source_id']]['truth']
    return {'status':'passed','reports_root':str(reports_root),'truth_source':str(truth_path),
            'truth_sha256':hashlib.sha256(truth_path.read_bytes()).hexdigest(),
            'report_counts':dict(Counter(qid.split('/')[1] for qid in actual)),
            'included_counts':dict(Counter(q['group'] for q in included.values())),
            'excluded_counts':dict(Counter(qid.split('/')[1] for qid in excluded)),
            'excluded_reason':'Coordinator故障 and UB管控面故障; fixed five-label scope'}


def evaluate(prepared, raw, out, input_paths=None, audit=None):
    if out.exists() and any(out.iterdir()):
        raise ValueError('LOO output directory must be empty')
    out.mkdir(parents=True,exist_ok=True)
    manifest = {'evaluation_mode':MODE,'policy':fixed_matching.POLICY,
        'classifier':'none','fitted_parameters':False,
        'input_sha256':evaluation.digest({'prepared':prepared,'raw':raw}),
        'source_sha256':{},'input_files':{},'dataset_audit':audit}
    for source in list(Path(__file__).parent.glob('*.py'))+list(SCRIPTS.glob('*.py')):
        folder='runtime' if source.parent==SCRIPTS else 'experiment'
        target=out/'source_snapshot'/folder/source.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        manifest['source_sha256'][str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
    for name,source in (input_paths or {}).items():
        shutil.copy2(source,out/name)
        manifest['input_files'][name]={'path':str(source.resolve()),
            'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    evaluation.write(out/'manifest.json',manifest)
    queries=prepared['reports']
    groups=evaluation.source_groups(queries,'source')
    group_by_source={q['source_id']:g for q,g in zip(queries,groups)}
    records=[]
    enriched=[{**c,'raw_observations':raw['reports'][c['source_id']]} for c in prepared['cases']] if raw else prepared['cases']
    for index,query in enumerate(queries):
        excluded={qid for qid,g in group_by_source.items() if g==groups[index]}
        candidates=[c for c in enriched if c['source_id'] not in excluded and evaluation.eligible(c,query)]
        raw_query=raw['reports'][query['source_id']] if raw else None
        matched=fixed_matching.match(query['profile'],candidates,query['structured'],raw_query)
        rows,decision=matched['candidates'],matched['decision']
        base=baseline_matching.decide(baseline_matching.rank_base(query['profile'],candidates))
        records.append({'query_id':query['source_id'],'truth':query['truth'],'group':query.get('group'),
            'baseline':base['label'],'fixed':decision['label'],'decision':decision,
            'candidate_count':len(rows),'excluded_source_ids':sorted(excluded),
            'candidate_source_ids':sorted({c['source_id'] for c in candidates}),
            'top20':[{'id':r['case_id'],'label':r['first_level_label'],'score':r['score_norm'],
                      'features':r.get('feature_values',{})} for r in rows[:20]]})
        if (index+1)%25==0 or index+1==len(queries):
            evaluation.write(out/'predictions.partial.json',records)
            print(f'fixed feature-vote source-LOO {index+1}/{len(queries)}',flush=True)
    summary={'evaluation_mode':MODE,'policy':fixed_matching.POLICY,'classifier':'none',
        'queries_evaluated':len(records),'total_queries':len(queries),'partial':False,
        'vote':{'top_k':4,'margin':.05},'channels':{'bm25':.05,'actor':.05,'scope':.05},
        'all_feature_budget':.30,
        'baseline_definition':'compatible base scoring and K4, without BM25/actor/scope increments',
        'metrics':{key:evaluation.metrics(records,key) for key in ('baseline','fixed')},
        'by_group':{group:{key:evaluation.metrics([r for r in records if r['group']==group],key)
                    for key in ('baseline','fixed')} for group in sorted({r['group'] for r in records if r['group']})}}
    evaluation.write(out/'predictions.json',records)
    evaluation.write(out/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--reports-root',type=Path,required=True)
    parser.add_argument('--gt-labels',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    prepared,raw=evaluation.read(args.prepared),evaluation.read(args.raw)
    assert raw['prepared_sha256']==hashlib.sha256(args.prepared.read_bytes()).hexdigest()
    assert set(raw['reports'])=={q['source_id'] for q in prepared['reports']}
    audit=audit_dataset(prepared,args.reports_root,args.gt_labels)
    evaluate(prepared,raw,args.out,{'prepared.json':args.prepared,'raw_observations.json':args.raw},audit)


if __name__=='__main__':
    main()
