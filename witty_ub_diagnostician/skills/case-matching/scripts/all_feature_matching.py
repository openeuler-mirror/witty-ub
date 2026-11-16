"""Fixed pair similarities over every safe observation family; no fitting."""
from collections import Counter
import math
import feature_vectors
import combination_matching

VERSION='all-feature-similarity-v1'
BLOCKS=('distributions','numeric','time','facts','mechanism','events','families','transport',
        'interaction','chains','scope','telemetry','words','phrases','structure','components')
TOTAL_WEIGHT=.30
BLOCK_WEIGHT=TOTAL_WEIGHT/len(BLOCKS)
NUMERIC={'numeric','time','facts','scope','telemetry','structure'}


def block_name(key):
    if key.startswith('raw:'):
        return {'max':'telemetry','count':'telemetry','word':'words','phrase':'phrases',
                'structure':'structure','component':'components'}[key.split(':')[1]]
    if key.startswith('query:fact:'):return 'facts'
    if key.startswith('query:mechanism:'):return 'mechanism'
    if key.startswith('query:scope:'):return 'scope'
    if key.startswith('query:log:'):
        return {'events':'events','families':'families','transport':'transport',
                'interactions':'interaction','chains':'chains','semantic':'mechanism'}.get(key.split(':')[2])
    if key.startswith(('query:GET:','query:SET:')):
        field=key.split(':')[2]
        if field in ('numeric','time'):return field
        return 'distributions'
    return None  # legacy identifiers/operation/semantic and actors already scored by base + actor.


def blocks(vector):
    out={b:{} for b in BLOCKS}
    for key,value in vector.items():
        name=block_name(key)
        if name is not None and not key.endswith((':known',':observed')):
            out[name][key]=value
    return out


def similarity(a,b,numeric=False,idf=None):
    if not a or not b:return None
    common=a.keys()&b.keys()
    if numeric:
        if not common:return None
        score=math.fsum(math.exp(-abs(a[k]-b[k])) for k in sorted(common))/len(common)
        return score*math.sqrt(len(common)/len(a.keys()|b.keys()))
    idf=idf or {}
    dot=math.fsum(a[k]*b[k]*idf.get(k,1.)**2 for k in sorted(common))
    norm_a=math.fsum(v*v*idf.get(k,1.)**2 for k,v in a.items())
    norm_b=math.fsum(v*v*idf.get(k,1.)**2 for k,v in b.items())
    return min(1.,dot/math.sqrt(norm_a*norm_b)) if norm_a and norm_b else None


def apply(rows,query_vector,case_vectors,source_ids):
    query=blocks(query_vector)
    indexed={r['case_id']:blocks(case_vectors[r['case_id']]) for r in rows}
    # Corpus document counts use known historical sources only, never query/validation rows.
    idfs={}
    for name in ('words','phrases'):
        documents={}
        for cid,profile in indexed.items():
            documents.setdefault(source_ids[cid],set()).update(profile[name])
        df=Counter(k for doc in documents.values() for k in doc)
        n=len(documents)
        idfs[name]={k:1+math.log((n+1)/(count+1)) for k,count in df.items()}
    result=[]
    for row in rows:
        values={name:similarity(query[name],indexed[row['case_id']][name],name in NUMERIC,idfs.get(name))
                for name in BLOCKS}
        delta=BLOCK_WEIGHT*math.fsum(values[name] or 0. for name in BLOCKS)
        result.append({**row,'three_channel_score':row['score_norm'],'score_norm':row['score_norm']+delta,
                       'all_feature_values':values,'all_feature_delta':delta,
                       'all_feature_coverage':sum(v is not None for v in values.values())/len(BLOCKS)})
    return sorted(result,key=lambda r:-r['score_norm'])


def rank(query,cases,structured,raw=None,vectors=None):
    rows=combination_matching.rank_default(query,cases,structured)
    if structured is None:return rows
    query_vector=feature_vectors.build_observations(query,structured,raw)
    by_id={c['id']:c for c in cases}
    vectors=vectors or {}
    profiles={}
    for row in rows:
        case=by_id[row['case_id']]
        if row['case_id'] in vectors:
            profiles[row['case_id']]=vectors[row['case_id']]
        elif case.get('structured') is not None:
            profiles[row['case_id']]=feature_vectors.build_observations(case['profile'],case['structured'],case.get('raw_observations'))
        else:profiles[row['case_id']]={}
    return apply(rows,query_vector,profiles,{c['id']:c['source_id'] for c in cases})
