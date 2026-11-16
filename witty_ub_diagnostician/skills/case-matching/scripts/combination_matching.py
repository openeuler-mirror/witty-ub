#!/usr/bin/env python3
"""Fixed Agent candidate scoring with bounded observation increments.

The original scorer computes each base, including its filtered-pool prior and
semantic IDF. Only independently observed channel increments are added here.
"""
import math
import baseline_matching as baseline

VERSION = 'legacy-evidence-combinations-v1'
FEATURES = ('mechanism', 'bm25', 'actor', 'scope', 'interaction')
WEIGHT = .05
DEFAULT_BASE = 'baseline'
DEFAULT_FEATURES = ('bm25', 'actor', 'scope')


def mix(base_scores, base_order, channels, features):
    """Pure score mixing: no query truth, labels, prose or identities accepted."""
    if len(set(features)) != len(features) or any(f not in FEATURES for f in features):
        raise ValueError('组合通道必须已声明且不重复')
    n = len(base_scores)
    if sorted(base_order) != list(range(n)):
        raise ValueError('底座排序不是候选的完整排列')
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in base_scores):
        raise ValueError('底座分数必须有限')
    for f in features:
        if len(channels[f]) != n or any(v is not None and (type(v) not in (float, int)
                or not math.isfinite(v) or not -1e-12 <= v <= 1 + 1e-12) for v in channels[f]):
            raise ValueError(f'非法观测相似度：{f}')
    scores = [base_scores[i] + math.fsum(WEIGHT * (channels[f][i] or 0.) for f in FEATURES if f in features)
              for i in range(n)]
    return sorted(base_order, key=lambda i: -scores[i]), scores


def apply_default(rows, query_structured=None, case_structured=None):
    """Apply the fixed default to an already computed, text-free base ranking.

    Missing observations remain unknown and add zero. Historical cases without
    sidecars do not become fabricated empty documents in BM25 statistics.
    The mapping retains the caller's original candidate order for statistics.
    """
    profiles = case_structured or {}
    identifiers = {r['case_id'] for r in rows}
    if len(identifiers) != len(rows):
        raise ValueError('重复候选ID')
    known = {cid: profile for cid, profile in profiles.items() if cid in identifiers and profile is not None}
    if query_structured is not None or known:
        import enhanced_matching as enhanced
        if query_structured is not None:
            enhanced.validate_profile(query_structured)
        for profile in known.values():
            enhanced.validate_profile(profile)
    stats = enhanced.pool_statistics([{'profile': p} for p in known.values()]) if query_structured is not None else None
    channels = {f: [] for f in DEFAULT_FEATURES}
    for row in rows:
        profile = known.get(row['case_id'])
        values = enhanced.compare(query_structured, profile, stats)[0] if query_structured is not None and profile is not None else {}
        for f in DEFAULT_FEATURES:
            channels[f].append(values.get(f))
    base_scores = [r['score_norm'] for r in rows]
    order, scores = mix(base_scores, list(range(len(rows))), channels, DEFAULT_FEATURES)
    result = []
    for i in order:
        row = dict(rows[i])
        row['base_score'] = base_scores[i]
        row['score_norm'] = scores[i]
        row['feature_values'] = {f: channels[f][i] for f in DEFAULT_FEATURES}
        row['feature_deltas'] = {f: WEIGHT * (channels[f][i] or 0.) for f in DEFAULT_FEATURES}
        row['experiment_delta'] = math.fsum(row['feature_deltas'].values())
        result.append(row)
    return result


def rank_default(query, cases, query_structured=None):
    rows = baseline.rank_base(query, cases)
    profiles = {c['id']: c.get('structured') for c in cases}
    return apply_default(rows, query_structured, profiles)
