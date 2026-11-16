"""All-feature cosine K4, using observed reference vectors; standard library only."""
import math
import baseline_matching

VERSION='all-context-cosine-bank-v1'


def _source(case):return case.get('source_id') or case['id']


def observed_vector(profile,structured=None,raw=None):
    import feature_vectors
    if structured is None:
        structured={'schema_version':'evidence-v1','views':{},'codes':profile['status_codes'],
            'modes':profile['failure_mode_ids'],'tokens':{},'log':{},'facts':{},'audit':{},'provenance':{}}
    return feature_vectors.build_observations(profile,structured,raw)


def rank(query,references,cases=None,excluded_sources=(),query_identities=()):
    if references.get('schema_version')!=VERSION:raise ValueError('Unsupported cosine reference bank')
    excluded=set(excluded_sources);identities=set(query_identities)
    sources={r['source_id']:r for r in references['sources']}
    selected=[];vectors={};source_ids=set()
    for case in references['cases'] if cases is None else cases:
        source=_source(case);known=sources.get(source)
        if source in excluded or identities.intersection(case.get('identity',[])):continue
        if known and identities.intersection(known.get('identity',[])):continue
        if case.get('label') not in ('OS故障','SDK故障','Worker故障','容器故障','硬件故障'):continue
        vector=known['vector'] if known else case.get('all_context_vector')
        if vector is None:
            if not case.get('profile'):continue
            vector=observed_vector(case['profile'],case.get('structured'),case.get('raw_observations'))
        if not vector or not any(vector.values()):continue
        vectors[case['id']]=vector;source_ids.add(source);selected.append(case)
    maxima={}
    for vector in vectors.values():
        for key,value in vector.items():maxima[key]=max(maxima.get(key,0.),abs(value))
    scale={k:v if v>=2.220446049250313e-15 else 1. for k,v in maxima.items()}
    scaled={k:v/scale[k] for k,v in query.items() if k in scale and v}
    norm=math.sqrt(math.fsum(v*v for v in scaled.values()))
    if not norm:return [],{'reference_sources':len(source_ids),'known_query_features':0,'reason':'no_comparable_observations'}
    scores={}
    for case_id,vector in vectors.items():
        length=math.sqrt(math.fsum((v/scale[k])**2 for k,v in vector.items()))
        dot=math.fsum(scaled[k]*vector[k]/scale[k] for k in sorted(scaled.keys()&vector.keys()))
        scores[case_id]=min(1.,max(0.,dot/norm/length)) if length else 0.
    rows=[{'case_id':c['id'],'source_id':_source(c),
           'first_level_label':c['label'],'second_level_label':c.get('second_level_label'),
           'score_norm':scores[c['id']],'score_raw':scores[c['id']],
           'feature_coverage':len(query.keys()&vectors[c['id']].keys())/(len(query) or 1),
           'level_summary':'cosine','levels':{},'operation':(c.get('profile') or {}).get('operation'),
           'score_method':'all_feature_cosine',
           'feature_values':{},'text_sim':0.} for c in selected]
    return sorted(rows,key=lambda r:-r['score_norm']),{'reference_sources':len(source_ids),'known_query_features':len(scaled),'reason':None}


def decide(rows):
    result=dict(baseline_matching.decide(rows))
    vote_method=result['method']
    result.update(method='all_feature_cosine_k4' if rows else 'empty',top_k=4,margin=.05)
    result['vote_method']=vote_method
    window=rows[:1] if vote_method in ('top1_margin','fallback_top1') else rows[:4]
    result['supporting_case_ids']=[r['case_id'] for r in window if r['first_level_label']==result['label']]
    return result
