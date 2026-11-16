"""Standard-library helpers for source exclusion and evaluation metrics."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

LABELS = ('OS故障', 'SDK故障', 'Worker故障', '容器故障', '硬件故障')

def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_groups(queries, protocol):
    """Union aliases before fold assignment; scenes are grouping metadata only."""
    parents = list(range(len(queries)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    owners = {}
    for i, q in enumerate(queries):
        keys = ['source:'+q['source_id']] + ['identity:'+s for s in q['identity']]
        files = q['structured'].get('log', {}).get('provenance', {}).get('files', [])
        if files:
            keys.append('whole_log_content:'+digest(sorted(f['sha256'] for f in files)))
        if protocol == 'scene':
            keys.append('scene:'+q['scene'])
        for key in keys:
            if key in owners:
                parents[find(i)] = find(owners[key])
            owners[key] = i
    return [str(find(i)) for i in range(len(queries))]


def eligible(case, query):
    return case['source_id'] != query['source_id'] and not set(case['identity']).intersection(query['identity'])


def metrics(records, key):
    labels = LABELS
    hits = sum(r[key] in r['truth'] for r in records)
    per = {}
    confusion = defaultdict(Counter)
    for r in records:
        confusion[' / '.join(sorted(r['truth']))][r[key] or '<unknown>'] += 1
    for label in labels:
        tp = sum(r[key] == label and label in r['truth'] for r in records)
        predicted = sum(r[key] == label for r in records)
        support = sum(label in r['truth'] for r in records)
        precision = tp / predicted if predicted else 0.
        recall = tp / support if support else 0.
        per[label] = {'support': support, 'tp': tp, 'predicted': predicted,
                      'precision': precision, 'recall': recall,
                      'f1': 2*precision*recall/(precision+recall) if precision+recall else 0.}
    before = [r['baseline'] in r['truth'] for r in records]
    after = [r[key] in r['truth'] for r in records]
    return {'n': len(records), 'hits': hits, 'accuracy': hits/len(records), 'per_label': per,
            'macro_f1': sum(p['f1'] for p in per.values())/len(per),
            'confusion': {k: dict(v) for k, v in confusion.items()},
            'rescued': sum(b and not a for a, b in zip(before, after)),
            'harmed': sum(a and not b for a, b in zip(before, after))}
