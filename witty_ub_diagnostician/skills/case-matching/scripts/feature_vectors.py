"""Shared label-blind observation vectors for fixed K4 and classifiers."""
from collections import Counter, defaultdict
import math
import baseline_matching as baseline
import enhanced_matching as enhanced

VERSION = 'all-observations-v1'
LABELS = ('OS故障', 'SDK故障', 'Worker故障', '容器故障', '硬件故障')

def observations(profile, structured):
    """Accept closed observation schemas, never report objects or envelopes."""
    baseline.validate_profile(profile)
    enhanced.validate_profile(structured)
    out = {}
    for field in ('status_codes', 'failure_mode_ids', 'latency_components'):
        for key in profile[field]:
            out[f'query:legacy:{field}:{key}'] = 1.
    if profile['operation']:
        out[f'query:legacy:operation:{profile["operation"]}'] = 1.
    # Existing semantic tokens are measured E/W features, not report prose.
    for key, value in profile['log_semantic_profile'].items():
        if not enhanced.NOISE_RE.fullmatch(key):
            out[f'query:semantic:{key}'] = value
    for op, view in structured['views'].items():
        prefix = f'query:{op}:'
        out[prefix + 'observed'] = 1.
        for field in ('code_counts','code_distribution', 'buckets'):
            for key, value in view.get(field, {}).items():
                out[prefix + field + ':' + key] = math.log1p(value) if field=='code_counts' else value
        for field in ('numeric', 'time'):
            for key, value in view.get(field, {}).items():
                # Drop the descriptive metric name, retaining bucket and metric.
                parts = key.split('|')
                key = '|'.join((parts[0], parts[-1]))
                out[prefix + field + ':' + key] = math.log1p(max(0., value))
        for field in ('code_complete', 'truncated'):
            if view.get(field) is not None:
                out[prefix + field + ':known'] = 1.
                out[prefix + field] = float(view[field])
        if view.get('other_share') is not None:
            out[prefix + 'other_share'] = view['other_share']
        if view.get('sample_count') is not None:
            out[prefix+'sample_count']=math.log1p(view['sample_count'])
    log = structured.get('log') or {}
    for field in ('actors', 'events', 'families', 'interactions', 'transport', 'chains','semantic'):
        out[f'query:log:{field}:observed'] = float(bool(log.get(field)))
        for key, value in log.get(field, {}).items():
            out[f'query:log:{field}:{key}'] = value
    # File count is intentionally excluded: collection layout is not impact.
    for key, fact in structured.get('facts', {}).items():
        if fact.get('verified') is True:
            out[f'query:fact:{key}:known'] = 1.
            out[f'query:fact:{key}'] = float(fact['value'])
    for key,value in structured['tokens'].items():
        out['query:mechanism:'+key]=float(value)
    role_count=log.get('scope',{}).get('observed_role_count')
    if role_count is not None:
        out['query:scope:observed_role_count']=math.log1p(role_count)
    return out


def build_observations(profile,structured,raw=None):
    out=observations(profile,structured)
    if raw is None:
        out['query:raw:available']=0.
        return out
    if set(raw)!={'schema_version','features','provenance'} or raw['schema_version']!='raw-observations-v1':
        raise ValueError('Expected measured raw-observations-v1 without label fields')
    for key,value in raw['features'].items():
        if not key.startswith(('raw:max:','raw:count:','raw:word:','raw:phrase:','raw:structure:','raw:component:')):
            raise ValueError('Unknown raw feature family: '+key)
        if not key.isascii() or type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('Invalid raw observation')
        out[key]=math.log1p(value) if key.startswith('raw:max:') else float(value)
    out['query:raw:available']=float(raw['provenance'].get('source')!='unavailable')
    if any(not math.isfinite(v) for v in out.values()):
        raise ValueError('Non-finite observation')
    return out

def retrieval_features(rows):
    """Summarize independently retrieved historical labels, not query truth."""
    out = {}
    by_label = defaultdict(list)
    for row in rows:
        if row['first_level_label'] in LABELS:
            by_label[row['first_level_label']].append(row)
    best = rows[0]['score_norm'] if rows else 0.
    for label in LABELS:
        prefix = f'retrieval:{label}:'
        candidates = by_label[label]
        # One source can contribute at most once to per-label score summaries.
        unique, seen = [], set()
        for row in candidates:
            source = row.get('source_id', row['case_id'])
            if source not in seen:
                unique.append(row)
                seen.add(source)
        out[prefix + 'present'] = float(bool(candidates))
        if unique:
            scores = [r['score_norm'] for r in unique]
            out[prefix + 'best'] = scores[0]
            out[prefix + 'gap_to_best'] = scores[0] - best
            out[prefix + 'top3_mean'] = sum(scores[:3]) / len(scores[:3])
            out[prefix + 'second_gap'] = scores[0] - scores[min(1, len(scores)-1)]
            row = unique[0]
            out[prefix + 'base_score'] = row.get('base_score', row['score_norm'])
            for field in ('log_semantic_sim',):
                out[prefix + field] = row.get(field, 0.)
            for field, value in row.get('feature_values', {}).items():
                out[prefix + field + ':known'] = float(value is not None)
                out[prefix + field] = value or 0.
        for k in (4, 10, 20):
            top = rows[:k]
            out[prefix + f'top{k}_share'] = sum(r['first_level_label'] == label for r in top) / max(1, len(top))
    out['retrieval:top_gap'] = best - rows[1]['score_norm'] if len(rows) > 1 else 0.
    vote = baseline.decide(rows)
    if vote['label']:
        out['retrieval:k4:' + vote['label']] = 1.
    return out
