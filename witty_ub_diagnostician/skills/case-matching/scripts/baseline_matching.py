#!/usr/bin/env python3
"""Report-text-free adapter around the existing soft scorer and K4 decision.

Identifiers intentionally preserve historical composite values and header
operation parsing. Changes to those semantics are separate experiments.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import importlib.util
import math
from pathlib import Path
import re
import threading

HERE = Path(__file__).resolve().parent
VERSION = 'legacy-evidence-v1'
CONTROL = {'Coordinator故障', 'UB管控面故障'}
CODE = re.compile(r'-?\d+(?:\s*[,/]\s*-?\d+)*')
MODE_PART = r'[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}'
MODE = re.compile(MODE_PART + r'(?:\s*[,/]\s*' + MODE_PART + r')*')
BUCKET = re.compile(r'[a-z][a-z0-9_]*')
_LOCK = threading.RLock()


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


# Private instance: online CLI globals and repeated/off-thread LOO calls cannot
# accidentally change each other's semantic/prior settings.
legacy = _module('baseline_legacy_scorer', HERE / 'match_cases.py')
legacy._LOG_SEMANTIC_CACHE = {}


def walk(value, key):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child, key)


def _identifiers(values, pattern):
    return list(dict.fromkeys(str(v) for v in values if pattern.fullmatch(str(v))))


def extract_report(payload, fault_indices=None):
    """Extract only observed identifiers; never concatenate report prose.

    Report-wide statistics remain report context for a fault candidate, matching
    the historical LOO contract. This is not a claim of per-fault attribution.
    """
    faults = payload.get('faults') or []
    selected = faults if fault_indices is None else [faults[i] for i in fault_indices]
    observed = {'statistics': payload.get('statistics') or {},
                'faults': [{k: f.get(k) for k in ('evidence_traces', 'error', 'latency')}
                           for f in selected]}
    codes, modes, buckets = [], [], []
    for anchors in walk(observed, 'evidence_traces'):
        for anchor in anchors or []:
            if not isinstance(anchor, dict):
                continue
            if anchor.get('status_code') is not None:
                codes.append(anchor['status_code'])
            if anchor.get('failure_mode_id'):
                modes.append(anchor['failure_mode_id'])
    for distribution in walk(observed, 'code_distribution'):
        if isinstance(distribution, dict):
            codes.extend(item['code'] for item in distribution.get('items') or []
                         if isinstance(item, dict) and item.get('code') is not None)
    for stages in walk(observed, 'stages'):
        for stage in stages if isinstance(stages, list) else [stages]:
            if not isinstance(stage, dict):
                continue
            features = stage.get('features') or {}
            features = features if isinstance(features, list) else [features]
            bucket = stage.get('bucket_key')
            for f in features:
                if isinstance(f, dict) and f.get('bucket_key'):
                    bucket = f['bucket_key']
                    break
            if bucket:
                buckets.append(str(bucket).strip())
    operations = set(re.findall(r'\b(GET|SET)\b', str((payload.get('basic_info') or {}).get('operation') or '').upper()))
    result = {
        'schema_version': VERSION,
        'status_codes': _identifiers(codes, CODE),
        'failure_mode_ids': _identifiers(modes, MODE),
        'latency_components': _identifiers(buckets, BUCKET),
        'operation': 'MIXED' if len(operations) > 1 else next(iter(operations), None),
        'log_semantic_profile': {},
    }
    return validate_profile(result)


def validate_profile(profile):
    expected = {'schema_version', 'status_codes', 'failure_mode_ids', 'latency_components',
                'operation', 'log_semantic_profile'}
    if set(profile) != expected or profile['schema_version'] != VERSION:
        raise ValueError('需要封闭的 legacy-evidence-v1 profile；标签/文字/身份不得加入特征')
    for key, pattern in [('status_codes', CODE), ('failure_mode_ids', MODE), ('latency_components', BUCKET)]:
        values = profile[key]
        if (not isinstance(values, list) or any(not isinstance(v, str) or not pattern.fullmatch(v) for v in values)
                or len(set(values)) != len(values)):
            raise ValueError(f'非法或重复标识符：{key}')
    if profile['operation'] not in (None, 'GET', 'SET', 'MIXED'):
        raise ValueError('非法 operation')
    semantic = profile['log_semantic_profile']
    if not isinstance(semantic, dict) or any(
        not isinstance(k, str) or not k.isascii() or not k.startswith(('T:', 'C:'))
        or type(v) not in (int, float) or not math.isfinite(v) or v < 0 for k, v in semantic.items()
    ):
        raise ValueError('非法日志语义轮廓；须来自原始日志或显式版本缓存')
    return profile


def semantic_from_logs(directory):
    """Same E/W message extraction as the frozen baseline; no backend access."""
    extractor = _module('baseline_semantic_extractor', HERE / 'build_log_semantic_profiles.py')
    directory = Path(directory)
    files = sorted(p for p in directory.rglob('*') if p.is_file() and p.name.endswith(('.log', '.log.gz')))
    if not files:
        raise ValueError(f'没有原始日志：{directory}')
    seen, manifest = set(), []

    def messages():
        for path in files:
            digest = hashlib.sha256()
            with (gzip.open if path.name.endswith('.gz') else open)(path, 'rb') as stream:
                for raw in stream:
                    digest.update(raw)
                    parts = raw.split(b'|', 7)
                    if len(parts) != 8 or parts[1].strip() not in (b'E', b'W') or not re.match(rb'^\d{4}-\d\d-\d\d[T ]', parts[0]):
                        continue
                    event = raw.rstrip(b'\r\n')
                    identity = hashlib.sha256(event).digest()
                    if identity in seen:
                        continue
                    seen.add(identity)
                    yield (parts[7].strip() or event).decode('utf-8', errors='replace')
            manifest.append({'path': str(path.resolve()), 'size': path.stat().st_size,
                             'decoded_file_sha256': digest.hexdigest()})
    return extractor.extract_profile(messages()), manifest


def _soft(profile):
    return {**{key: [{'value': legacy._normalize(v), 'share': 1.} for v in profile[key]]
               for key in ('status_codes', 'failure_mode_ids', 'latency_components')},
            'log_keywords': [], 'operation': profile['operation'], 'time_shape': None,
            'affected_scope': None, 'topology_shape': None,
            'log_semantic_profile': profile['log_semantic_profile']}


def rank_base(query, cases, *, semantic_enabled=True, prior_enabled=True):
    """Closed-schema candidate scoring kernel; no fitting or experiment workflow."""
    validate_profile(query)
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('重复候选 ID')
    cases = [c for c in cases if c['label'] not in CONTROL]
    matches = []
    for case in cases:
        validate_profile(case['profile'])
        cp = case['profile']
        matches.append({'case': {'id': case['id'], 'case_no': case['id'],
            'first_level_label': case['label'], 'status': 'confirmed',
            **{k: cp[k] for k in ('status_codes', 'failure_mode_ids', 'latency_components', 'operation', 'log_semantic_profile')},
            'log_keywords': [], 'confidence': None, 'hit_count': 0, 'updated_at': ''}})
    with _LOCK:
        settings = ('LOG_SEMANTIC_ENABLED', 'LOG_SEMANTIC_IDF', 'LOG_SEMANTIC_PRIOR_ENABLED', 'DOMAIN_PRIOR_WEIGHT')
        previous = {k: getattr(legacy, k) for k in settings}
        try:
            legacy.LOG_SEMANTIC_ENABLED = semantic_enabled
            legacy.LOG_SEMANTIC_IDF = True
            legacy.LOG_SEMANTIC_PRIOR_ENABLED = False
            if not prior_enabled:
                legacy.DOMAIN_PRIOR_WEIGHT = 0.
            rows = legacy._rerank(matches, _soft(query), '')
        finally:
            for k, v in previous.items():
                setattr(legacy, k, v)
    by_id = {c['id']: c for c in cases}
    for row in rows:
        row['source_id'] = by_id[row['case_id']]['source_id']
        row['baseline_score'] = row['score_norm']
        row['experiment_delta'] = 0.
        if row['text_sim']:
            raise AssertionError('基线不应使用文本相似度')
    return rows


def rank(query, cases, query_structured=None):
    """Fixed Agent candidate ranking; final labels are returned by match()."""
    from combination_matching import rank_default
    return rank_default(query, cases, query_structured)


def match(query, cases, query_structured=None, query_raw=None):
    """Ordinary matching via the packaged numeric/cosine default policy.

    rank()/decide() remain candidate scoring primitives; this entry returns the
    selected label and candidate ranking together without embedding query context
    in candidate rows.
    """
    from default_matching import match as default
    return default(query, cases, query_structured, query_raw)


def decide(rows, method='vote', margin=.05):
    if method == 'top1':
        return {'label': rows[0]['first_level_label'] if rows else None, 'method': 'top1'}
    if method == 'vote':
        return legacy._label_vote(rows, top_k=4, margin=margin)
    raise ValueError(f'未知决策：{method}')
