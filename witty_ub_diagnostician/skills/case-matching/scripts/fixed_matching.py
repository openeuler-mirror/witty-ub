#!/usr/bin/env python3
"""Fixed evidence scoring and K4 vote shared by Agent reports and LOO."""

import baseline_matching as baseline
import combination_matching as retrieval
import fixed_observations
POLICY = 'all-feature-vote-v1'


def decide(query, structured, raw, rows):
    baseline.validate_profile(query)
    retrieval_decision = baseline.decide(rows)
    usage = set(query['status_codes']).intersection(baseline.legacy.USER_USAGE_FAULT_CODES)
    if usage:
        supported = [r for r in rows if r['first_level_label']==baseline.legacy.USER_USAGE_FIRST_LEVEL]
        decision = baseline.decide(supported)
        decision.update(label=baseline.legacy.USER_USAGE_FIRST_LEVEL, method='user_usage_rule', policy=POLICY,
                        second_level_label=baseline.legacy.USER_USAGE_SECOND_LEVEL, user_usage_codes=sorted(usage))
        return decision
    if not rows:
        return {'label': None, 'method': 'empty', 'distribution': {}, 'policy': POLICY}
    decision = dict(retrieval_decision)
    decision.update(method='fixed_feature_vote', vote_method=retrieval_decision['method'],
                    policy=POLICY, top_k=4, margin=.05)
    decision['log_observations_available'] = bool(raw and raw.get('provenance', {}).get('source')!='unavailable')
    decision['supporting_case_ids'] = [r['case_id'] for r in rows
        if r['first_level_label']==decision['label']][:4]
    return decision


def rank(query, cases, query_structured=None, query_raw=None):
    baseline.validate_profile(query)
    if set(query['status_codes']).intersection(baseline.legacy.USER_USAGE_FAULT_CODES):
        cases = [c for c in cases if c['label']==baseline.legacy.USER_USAGE_FIRST_LEVEL
                 and c.get('second_level_label') in (None, baseline.legacy.USER_USAGE_SECOND_LEVEL)]
    import all_feature_matching
    return all_feature_matching.rank(query,cases,query_structured,query_raw)


def match(query, cases, query_structured=None, query_raw=None):
    rows = rank(query, cases, query_structured,query_raw)
    decision = decide(query, query_structured, query_raw, rows)
    return {'engine': 'fixed-feature-matching-v1', 'policy': POLICY, 'candidates': rows,
            'decision': decision, 'retrieval_decision': baseline.decide(rows)}


def extract_report(payload, log_dir=None, fault_indices=None):
    """Shared report/LOO observation extraction; never consume answer fields."""
    import enhanced_matching
    query = baseline.extract_report(payload, fault_indices)
    structured = enhanced_matching.extract_report(payload, fault_indices)
    if log_dir is not None:
        query['log_semantic_profile'], _ = baseline.semantic_from_logs(log_dir)
        structured['log'] = enhanced_matching.scan_logs(log_dir)
        raw = fixed_observations.scan(log_dir)
    else:
        raw = fixed_observations.unknown()
    return query, structured, raw


def match_report(payload, cases, log_dir=None, fault_indices=None):
    query, structured, raw = extract_report(payload, log_dir, fault_indices)
    return match(query, cases, structured, raw)
