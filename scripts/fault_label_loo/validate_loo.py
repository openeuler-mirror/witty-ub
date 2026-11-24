#!/usr/bin/env python3
"""Verify complete rule-based LOO coverage, exclusions and shared decisions."""
import argparse
import hashlib
from pathlib import Path

import skill_runtime
from skill_runtime import SCRIPTS
import baseline_matching
import fixed_matching
import eval_loo
import loo_support as evaluation


def validate(run):
    prepared=evaluation.read(run/'prepared.json')
    raw=evaluation.read(run/'raw_observations.json')
    manifest=evaluation.read(run/'manifest.json')
    records=evaluation.read(run/'predictions.json')
    summary=evaluation.read(run/'summary.json')
    assert manifest['evaluation_mode']==summary['evaluation_mode']==eval_loo.MODE
    assert manifest['classifier']==summary['classifier']=='none'
    assert manifest['fitted_parameters'] is False and not summary['partial']
    queries=prepared['reports']
    assert len(records)==len(queries)==summary['queries_evaluated']==summary['total_queries']
    assert [r['query_id'] for r in records]==[q['source_id'] for q in queries]
    assert evaluation.digest({'prepared':prepared,'raw':raw})==manifest['input_sha256']
    for name,source in manifest['input_files'].items():
        assert hashlib.sha256((run/name).read_bytes()).hexdigest()==source['sha256']
    for path,digest in manifest['source_sha256'].items():
        source=Path(path)
        folder='runtime' if source.parent==SCRIPTS else 'experiment'
        assert hashlib.sha256((run/'source_snapshot'/folder/source.name).read_bytes()).hexdigest()==digest
        assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    groups=evaluation.source_groups(queries,'source')
    for index,(query,record) in enumerate(zip(queries,records)):
        excluded=sorted(q['source_id'] for q,g in zip(queries,groups) if g==groups[index])
        assert record['excluded_source_ids']==excluded
        candidates=[{**c,'raw_observations':raw['reports'][c['source_id']]} for c in prepared['cases']
                    if c['source_id'] not in excluded and evaluation.eligible(c,query)]
        assert record['candidate_source_ids']==sorted({c['source_id'] for c in candidates})
        assert record['truth']==query['truth'] and record['group']==query.get('group')
        matched=fixed_matching.match(query['profile'],candidates,query['structured'],
                                     raw['reports'][query['source_id']])
        assert record['decision']==matched['decision']
        assert record['fixed']==matched['decision']['label']
        assert record['candidate_count']==len(matched['candidates'])
        assert record['baseline']==baseline_matching.decide(
            baseline_matching.rank_base(query['profile'],candidates))['label']
        if (index+1)%100==0 or index+1==len(queries):
            print(f'validated fixed-vote query {index+1}/{len(queries)}',flush=True)
    for key in ('baseline','fixed'):
        assert evaluation.metrics(records,key)==summary['metrics'][key]
    for group,metrics in summary['by_group'].items():
        for key in ('baseline','fixed'):
            assert evaluation.metrics([r for r in records if r['group']==group],key)==metrics[key]
    result={'status':'passed','queries':len(records),'replayed_decisions':len(records),
            'classifier':'none','fitted_parameters':False,'evaluation_mode':eval_loo.MODE}
    evaluation.write(run/'validation.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    print(validate(parser.parse_args().run))


if __name__=='__main__':
    main()
