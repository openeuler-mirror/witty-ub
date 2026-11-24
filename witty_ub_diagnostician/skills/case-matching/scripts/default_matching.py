"""Versioned report classifier with all-feature cosine K4 fallback."""
from collections import defaultdict
from functools import lru_cache
import gzip
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import re

import baseline_matching
import cosine_matching
import feature_vectors
import fixed_matching
import mined_log_features_v2 as extraction
import portable_classifier
import model_registry

POLICY='numeric-units-classifier-cosine-fallback-v1'
ASSETS=Path(__file__).resolve().parents[1]/'assets/default_label_policy'
CLASSIFIER_METHODS = {'numeric_units': 'numeric_units_classifier', 'all_context_v2': 'all_context_classifier'}
COMPONENT_LABELS = (*feature_vectors.LABELS, 'URMA故障', 'UDMA故障')


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
    report_id=(payload.get('report') or {}).get('report_id')
    if report_id:values.append('report_id:'+str(report_id))
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
    view = model.get('view')
    if view not in CLASSIFIER_METHODS or model.get('metadata',{}).get('feature_version')!=extraction.VERSION:
        raise ValueError('Classifier feature version mismatch')
    names=model['feature_names'];classes=model['classes'];weights=model['coefficients'];intercept=model['intercept']
    rows=1 if len(classes)==2 else len(classes)
    if len(weights)!=rows or len(intercept)!=rows or any(len(w)!=len(names) for w in weights):
        raise ValueError('Invalid numeric classifier dimensions')
    allowed_labels = feature_vectors.LABELS if view == 'numeric_units' else COMPONENT_LABELS
    if len(classes)<2 or len(set(classes))!=len(classes) or not set(classes)<=set(allowed_labels):
        raise ValueError('Classifier label scope mismatch')
    if any(not math.isfinite(v) for w in weights for v in w) or any(not math.isfinite(v) for v in intercept):
        raise ValueError('Invalid numeric classifier coefficients')


def verify_packaged_assets():
    """Check the packaged hashes and schemas without consulting the active registry."""
    model = asset('numeric_classifier', ASSETS)
    validate_model(model)
    if asset('cosine_bank', ASSETS)['schema_version'] != cosine_matching.VERSION:
        raise ValueError('Unsupported cosine reference bank')
    return model['metadata'].get('model_id')


def _predict_classifier(model, features, known_features):
    decision=portable_classifier.predict(model,features)
    model_id=model['metadata'].get('model_id') or 'external-'+digest({
        'weights':model['coefficients'],'intercept':model['intercept']})[:12]
    view = model['view']
    decision.update(method=CLASSIFIER_METHODS[view], model_id=model_id, model_scope='report')
    feature_count_field = 'known_numeric_features' if view == 'numeric_units' else 'known_classifier_features'
    decision[feature_count_field] = len(known_features)
    return decision


def predict_numeric(model,numeric):
    """Portable numeric inference for historical fold-local evaluation."""
    validate_model(model)
    if model['view'] != 'numeric_units':
        raise ValueError('Expected numeric_units classifier')
    known = {key for key in model['feature_names'] if numeric.get(key)}
    return _predict_classifier(model, numeric, known)


def mami_fuse(rows,mami_hit=False,mami_weight=0.):
    """mami 硬件通道后处理：对本轮 mami 命中的查询，给一级标签为「硬件故障」的
    候选按 mami_weight 做加性加分并重排（不改模型、不进训练）。"""
    if not (mami_hit and mami_weight):return rows
    for row in rows:
        if row.get('first_level_label')=='硬件故障':
            row['score_norm']=min(1.,row.get('score_norm',0.)+mami_weight)
            row['score_raw']=row['score_norm']
    return sorted(rows,key=lambda r:-r['score_norm'])


def rank_knowledge(query, references, cases, decision, excluded_sources=(), query_identities=()):
    """Rank confirmed cases within the fault's final label using the same cosine view."""
    label = decision['label']
    if not label or not cases:
        return []
    second = decision.get('second_level_label') if decision['method'] == 'misoperation_rule' else None
    eligible = [case for case in cases if case.get('status') == 'confirmed'
                and case.get('label') == label
                and (not second or case.get('second_level_label') == second)]
    if not eligible:
        return []
    if references.get('schema_version') != cosine_matching.VERSION:
        references = {'schema_version': cosine_matching.VERSION, 'sources': [], 'cases': []}
    rows, _ = cosine_matching.rank(query, references, eligible, excluded_sources, query_identities,
                                   labels=(label,), require_shared_evidence=True)
    return [row for row in rows if row['score_norm'] > 0]


def suggest_second_level(fault_modes, matched, cases, allowed_labels, query_identities=()):
    """Look for agreement from distinct sources with the same observed failure mode."""
    if not allowed_labels:
        return {'label': None, 'reason': 'no_allowed_second_level_labels'}
    modes = {mode for mode in fault_modes if re.fullmatch(baseline_matching.MODE_PART, mode)}
    if not modes:
        return {'label': None, 'reason': 'no_fault_failure_mode'}

    first = matched['decision']['label']
    eligible = {case['id']: case for case in cases or [] if case.get('status') == 'confirmed'
                and case.get('label') == first and case.get('second_level_label') in allowed_labels}
    query_identities = set(query_identities)
    labels = set()
    support_by_mode = defaultdict(list)
    for row in matched.get('knowledge_candidates', matched['candidates']):
        case = eligible.get(row['case_id'])
        if not case or row['score_norm'] <= 0:
            continue
        identities = set(case.get('identity') or [])
        if query_identities & identities:
            continue
        identities.add('case_source:' + (case.get('source_id') or case['id']))
        case_modes = set((case.get('profile') or {}).get('failure_mode_ids') or [])
        case_modes.update((case.get('structured') or {}).get('modes') or [])
        for mode in modes & case_modes:
            support_by_mode[mode].append((case['id'], identities))
            labels.add(case['second_level_label'])

    if len(labels) > 1:
        return {'label': None, 'reason': 'conflicting_case_labels'}

    for mode, support in sorted(support_by_mode.items()):
        for (first_id, first_source), (case_id, source) in combinations(support, 2):
            if first_source.isdisjoint(source):
                return {'label': next(iter(labels)), 'failure_mode_id': mode,
                        'supporting_case_ids': [first_id, case_id]}
    return {'label': None, 'reason': 'insufficient_case_support'}


def match(profile,cases=None,structured=None,raw=None,context=None,*,model=None,references=None,
          query_identities=(),excluded_sources=(),allow_classifier=True,fallback_reason=None,assets_dir=None,
          mami_hit=False,mami_weight=0.,knowledge_cases=None):
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
    misoperation_codes=set(profile['status_codes'])&baseline_matching.legacy.MISOPERATION_FAULT_CODES
    if knowledge_cases is None:
        knowledge_cases = cases
    if misoperation_codes and not knowledge_cases:
        decision=fixed_matching.decide(profile,structured,raw,[]);decision['policy']=POLICY
        return {'policy':POLICY,'decision':decision,'retrieval_decision':decision,'candidates':[],
                'knowledge_candidates':[], 'feature_usage':{'business_rule':'misoperation_rule'},
                'fallback_used':False,'disagreement':False}
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
    if misoperation_codes:
        decision=fixed_matching.decide(profile,structured,raw,[]);decision['policy']=POLICY
        return {'policy':POLICY,'decision':decision,'retrieval_decision':decision,'candidates':[],
                'knowledge_candidates':rank_knowledge(all_features,references,knowledge_cases,decision,
                                                     excluded,query_identities),
                'feature_usage':{'business_rule':'misoperation_rule'},'fallback_used':False,'disagreement':False}
    try:rows,coverage=cosine_matching.rank(all_features,references,cases,excluded,query_identities)
    except ValueError as error:
        rows=[];coverage={'reference_sources':0,'known_query_features':0,'reason':'invalid_reference_bank'}
        reference_error=str(error)
    rows=mami_fuse(rows,mami_hit,mami_weight)
    retrieval=cosine_matching.decide(rows);numeric=extraction.vector('numeric_units',base,context)
    reason=fallback_reason if not allow_classifier else None;decision=None
    classifier_view = 'numeric_units'
    if allow_classifier:
        reason_prefix = 'numeric'
        try:
            if model is None:model=asset('numeric_classifier',assets_dir)
            elif isinstance(model,(str,Path)):model=load_file(str(model))
            if model.get('view') == 'all_context_v2':
                classifier_view = 'all_context_v2'
                reason_prefix = 'all_context'
            validate_model(model)
            features = all_features if classifier_view == 'all_context_v2' else numeric
            known = {key for key in model['feature_names'] if features.get(key)}
            if not any(features.values()):
                reason = f'{reason_prefix}_observations_unavailable'
            elif not known:
                reason = f'{reason_prefix}_features_unknown_to_model'
            else:
                decision = _predict_classifier(model, features, known)
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:
            reason=f'{reason_prefix}_model_unavailable: {error}'
    if decision is None:
        decision=dict(retrieval);decision['fallback_reason']=reason or 'classifier_not_applicable'
    if mami_hit and mami_weight:
        decision=dict(retrieval);decision.update(method='mami_fused_cosine_k4',mami_applied=True,
                                                  mami_weight=mami_weight,fallback_reason='mami_fusion')
    used_classifier = decision['method'] in CLASSIFIER_METHODS.values()
    decision.update(policy=POLICY,fallback_used=not used_classifier)
    disagreement=bool(used_classifier and retrieval['label'] and
                      decision['label']!=retrieval['label'])
    return {'policy':POLICY,'engine':POLICY,'decision':decision,'retrieval_decision':retrieval,'candidates':rows,
        'knowledge_candidates':rank_knowledge(all_features,references,knowledge_cases,decision,
                                             excluded,query_identities),
        'fallback_used':decision['fallback_used'],'disagreement':disagreement,'excluded_source_ids':sorted(excluded),
        'feature_usage':{'classifier_view':classifier_view,'fallback_view':'all_context_v2',
            'numeric_feature_count':len(numeric),'cosine':coverage,'reference_error':reference_error,
            'context_source':context.get('provenance',{}).get('source')}}


def match_report(payload,cases=None,log_dir=None,**kwargs):
    profile,structured,raw,context=observe(payload,log_dir)
    return match(profile,cases,structured,raw,context,query_identities=identities(payload),**kwargs)
