#!/usr/bin/env python3
"""Replay the packaged default policy with historical LOO weights, never full-fit weights."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path

import skill_runtime
import default_matching as runtime
import loo_support as io

STATE={}


def read_gzip(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def one(index):
    q=STATE['prepared']['reports'][index];qid=q['source_id']
    model=read_gzip(STATE['reference']/f'models/numeric_units/{index:04d}.json.gz')
    assert qid not in model['metadata']['training_source_ids']
    result=runtime.match(q['profile'],None,q['structured'],STATE['raw']['reports'][qid],STATE['contexts'][index],
        model=model,references=STATE['bank'],query_identities=q['identity'],excluded_sources=[qid])
    assert result['retrieval_decision']['label']==STATE['cosine'][index]['k4'],qid
    if not result['fallback_used']:assert result['decision']['label']==STATE['numeric'][index]['classifier'],qid
    return {'query_id':qid,'truth':q['truth'],'baseline':STATE['numeric'][index]['classifier'],
        'hybrid':result['decision']['label'],'cosine':result['retrieval_decision']['label'],
        'fallback_used':result['fallback_used'],'fallback_reason':result['decision'].get('fallback_reason'),
        'excluded_source_ids':result['excluded_source_ids']}


def verify(args):
    STATE.update(reference=args.reference,prepared=io.read(args.reference/'inputs/prepared.json'),
        raw=io.read(args.reference/'inputs/raw_observations.json'),bank=runtime.asset('cosine_bank'),
        numeric=io.read(args.reference/'predictions/numeric_units.json'),
        cosine=io.read(args.reference/'predictions/all_context_v2.json'))
    STATE['contexts']=[read_gzip(args.context_root/f'context_cache/{i:04d}.json.gz') for i in range(len(STATE['prepared']['reports']))]
    records=[]
    with ProcessPoolExecutor(max_workers=args.jobs,mp_context=multiprocessing.get_context('fork')) as pool:
        for count,row in enumerate(pool.map(one,range(len(STATE['contexts']))),1):
            records.append(row)
            if count%100==0 or count==len(STATE['contexts']):print('runtime policy parity',count,'/',len(STATE['contexts']),flush=True)
    io.write(args.out/'fold_replay.json',records)
    summary={'status':'passed','source_queries':len(records),'cosine_predictions_exact':len(records),
        'numeric_predictions_exact_when_applicable':sum(not r['fallback_used'] for r in records),
        'hybrid_metrics':io.metrics(records,'hybrid'),'fallback_reports':[r for r in records if r['fallback_used']],
        'full_data_deployment_weights_evaluated':False,'note':'Reuses stored fold-excluded models; verifies runtime parity and the explicit fallback composition, not new independent data.',
        'asset_manifest_sha256':hashlib.sha256((runtime.ASSETS/'manifest.json').read_bytes()).hexdigest()}
    io.write(args.out/'summary.json',summary);print('runtime policy parity passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','context-root','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=8);verify(parser.parse_args())
