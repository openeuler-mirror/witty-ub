"""Versioned numeric classifier with all-feature cosine K4 fallback; no training."""
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path

import baseline_matching
import cosine_matching
import feature_vectors
import fixed_matching
import mined_log_features_v2 as extraction
import portable_classifier
import model_registry

POLICY='numeric-units-classifier-cosine-fallback-v1'
ASSETS=Path(__file__).resolve().parents[1]/'assets/default_label_policy'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


@lru_cache(maxsize=8)
def load_file(path,expected_sha=None):
    path=Path(path)
    if expected_sha and hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError('Runtime asset checksum mismatch: '+path.name)
    with (gzip.open if path.suffix=='.gz' else open)(path,'rt',encoding='utf-8') as stream:return json.load(stream)


def asset(kind,assets_dir=None):
    directory=Path(assets_dir) if assets_dir is not None else model_registry.active_directory() or ASSETS
    manifest=load_file(str(directory/'manifest.json'))
    if manifest.get('feature_version',extraction.VERSION)!=extraction.VERSION:
        raise ValueError('Runtime asset feature version mismatch')
    for name,expected in manifest.get('extractor_sha256',{}).items():
        if hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Runtime extractor differs from trained assets: '+name)
    item=manifest['files'][kind]
    return load_file(str(directory/item['path']),item['sha256'])


def unknown_context(reason='logs_unavailable'):
    return {'schema_version':extraction.VERSION,'families':{key:{} for key in (
        'all_context','templates','sequences','numeric_units','conditioned','contrasts','temporal')},
        'provenance':{'source':'unavailable','reason':reason,'files':[],'rows':0}}


def identities(payload):
    basic=payload.get('basic_info') or {};values=[]
    if basic.get('kb_id'):values.append('kb_id:'+str(basic['kb_id']))
    for key in ('kb_name','log_file'):
        if basic.get(key):values.append('name:'+str(basic[key]))
    return sorted(set(values))


def observe(payload,log_dir=None):
    profile,structured,raw=fixed_matching.extract_report(payload,log_dir)
    context=extraction.scan(log_dir) if log_dir is not None else unknown_context()
    return profile,structured,raw,context


def validate_model(model):
    if model.get('schema_version')!=portable_classifier.VERSION or model.get('kind')!='logistic':
        raise ValueError('Expected portable Logistic model')
    if model.get('view')!='numeric_units' or model.get('metadata',{}).get('feature_version')!=extraction.VERSION:
        raise ValueError('Numeric classifier feature version mismatch')
    names=model['feature_names'];classes=model['classes'];weights=model['coefficients'];intercept=model['intercept']
    rows=1 if len(classes)==2 else len(classes)
    if len(weights)!=rows or len(intercept)!=rows or any(len(w)!=len(names) for w in weights):
        raise ValueError('Invalid numeric classifier dimensions')
    if len(classes)<2 or len(set(classes))!=len(classes) or not set(classes)<=set(feature_vectors.LABELS):
        raise ValueError('Numeric classifier label scope mismatch')
    if any(not math.isfinite(v) for w in weights for v in w) or any(not math.isfinite(v) for v in intercept):
        raise ValueError('Invalid numeric classifier coefficients')


def predict_numeric(model,numeric):
    """Shared portable numeric inference for Agent and fold-local evaluation."""
    validate_model(model)
    decision=portable_classifier.predict(model,numeric)
    model_id=model['metadata'].get('model_id') or 'external-'+digest({
        'weights':model['coefficients'],'intercept':model['intercept']})[:12]
    decision.update(method='numeric_units_classifier',model_id=model_id,model_scope='report',
        known_numeric_features=len(set(model['feature_names'])&{k for k,v in numeric.items() if v}))
    return decision


def mami_fuse(rows,mami_hit=False,mami_weight=0.):
    """mami 硬件通道后处理：对本轮 mami 命中的查询，给一级标签为「硬件故障」的
    候选按 mami_weight 做加性加分并重排（不改模型、不进训练）。"""
    if not (mami_hit and mami_weight):return rows
    for row in rows:
        if row.get('first_level_label')=='硬件故障':
            row['score_norm']=min(1.,row.get('score_norm',0.)+mami_weight)
            row['score_raw']=row['score_norm']
    return sorted(rows,key=lambda r:-r['score_norm'])


def match(profile,cases=None,structured=None,raw=None,context=None,*,model=None,references=None,
          query_identities=(),excluded_sources=(),allow_classifier=True,fallback_reason=None,assets_dir=None,
          mami_hit=False,mami_weight=0.):
    baseline_matching.validate_profile(profile)
    # Pin both assets once per prediction; an atomic activation cannot mix bundles.
    if assets_dir is None:assets_dir=model_registry.active_directory() or ASSETS
    if model is None and allow_classifier:
        try:
            disabled=load_file(str(Path(assets_dir)/'manifest.json')).get('classifier_disabled_reason')
            if disabled:allow_classifier=False;fallback_reason='insufficient_training_data: '+disabled
        except (OSError,ValueError,KeyError):pass
    context=context or unknown_context()
    if context.get('schema_version')!=extraction.VERSION:context=unknown_context('feature_version_mismatch')
    query_identities=sorted(set(query_identities)|set(context.get('provenance',{}).get('source_identities',[])))
    usage=set(profile['status_codes'])&baseline_matching.legacy.USER_USAGE_FAULT_CODES
    if usage:
        decision=fixed_matching.decide(profile,structured,raw,[]);decision['policy']=POLICY
        return {'policy':POLICY,'decision':decision,'retrieval_decision':decision,'candidates':[],
                'feature_usage':{'business_rule':'user_usage_rule'},'fallback_used':False,'disagreement':False}
    reference_error=None
    if references is None:
        try:references=asset('cosine_bank',assets_dir)
        except (OSError,ValueError,KeyError) as error:
            references={'schema_version':cosine_matching.VERSION,'sources':[],'cases':[]}
            reference_error=str(error)
    excluded=set(excluded_sources)
    hashes=sorted(f['sha256'] for f in context.get('provenance',{}).get('files',[]))
    fingerprint=digest(hashes) if hashes else None
    for source in references['sources']:
        if fingerprint and source.get('log_content_sha256')==fingerprint:excluded.add(source['source_id'])
        if set(query_identities)&set(source.get('identity',[])):excluded.add(source['source_id'])
    base=cosine_matching.observed_vector(profile,structured,raw)
    all_features=extraction.vector('all_context_v2',base,context)
    try:rows,coverage=cosine_matching.rank(all_features,references,cases,excluded,query_identities)
    except ValueError as error:
        rows=[];coverage={'reference_sources':0,'known_query_features':0,'reason':'invalid_reference_bank'}
        reference_error=str(error)
    rows=mami_fuse(rows,mami_hit,mami_weight)
    retrieval=cosine_matching.decide(rows);numeric=extraction.vector('numeric_units',base,context)
    reason=fallback_reason if not allow_classifier else None;decision=None
    if allow_classifier:
        if not any(numeric.values()):reason='numeric_observations_unavailable'
        else:
            try:
                if model is None:model=asset('numeric_classifier',assets_dir)
                elif isinstance(model,(str,Path)):model=load_file(str(model))
                validate_model(model)
                known=set(model['feature_names'])&{k for k,v in numeric.items() if v}
                if not known:reason='numeric_features_unknown_to_model'
                else:
                    decision=predict_numeric(model,numeric)
            except (OSError,ValueError,KeyError,TypeError) as error:
                reason='numeric_model_unavailable: '+str(error)
    if decision is None:
        decision=dict(retrieval);decision['fallback_reason']=reason or 'classifier_not_applicable'
    if mami_hit and mami_weight:
        decision=dict(retrieval);decision.update(method='mami_fused_cosine_k4',mami_applied=True,
                                                  mami_weight=mami_weight,fallback_reason='mami_fusion')
    decision.update(policy=POLICY,fallback_used=decision['method']!='numeric_units_classifier')
    disagreement=bool(decision['method']=='numeric_units_classifier' and retrieval['label'] and
                      decision['label']!=retrieval['label'])
    return {'policy':POLICY,'engine':POLICY,'decision':decision,'retrieval_decision':retrieval,'candidates':rows,
        'fallback_used':decision['fallback_used'],'disagreement':disagreement,'excluded_source_ids':sorted(excluded),
        'feature_usage':{'classifier_view':'numeric_units','fallback_view':'all_context_v2',
            'numeric_feature_count':len(numeric),'cosine':coverage,'reference_error':reference_error,
            'context_source':context.get('provenance',{}).get('source')}}


def match_report(payload,cases=None,log_dir=None,**kwargs):
    profile,structured,raw,context=observe(payload,log_dir)
    return match(profile,cases,structured,raw,context,query_identities=identities(payload),**kwargs)
