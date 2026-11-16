#!/usr/bin/env python3
"""Shared evidence-only extraction, comparison and decisions. Standard library only.

No report conclusions, prose, scenario names, topology, labels or GT are accepted
as features. Candidate labels live in separate case envelopes used by decisions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

VERSION = 'evidence-v1'
CONTROL = {'Coordinator故障', 'UB管控面故障'}
WEIGHTS = {'codes': 3., 'families': 1., 'modes': 3., 'stages': 2., 'numeric': 1.,
           'operation': .5, 'semantic': 1., 'actor': .5, 'lifecycle': .5,
           'transport': .5, 'interaction': 1., 'time': .25, 'scope': .1,
           'mechanism': .5, 'bm25': .5}
CHANNELS = tuple(WEIGHTS)
EVENTS = {
    'urma_completion_timeout': r'URMA_WAIT_TIMEOUT|Urma wait for completion timed out|timedout waiting.*urma',
    'urma_post_failure': r'URMA_POST.*FAIL|post (?:send|write).*fail',
    'rpc_peer_unavailable': r'RPC peer dead|Metadata owner unavailable|K_RPC_UNAVAILABLE',
    'rpc_timeout': r'deadline exceeded|RPC.*(?:timed out|timeout)',
    'connection_failure': r'connection refused|failed to connect|connect.*timed out',
    'fallback_rejected': r'(?:fallback|fall back|TCP fallback).*?(?:reject|refus|exceed|limit)',
    'fallback_success': r'(?:fallback|fall back).*?(?:succeed|success)',
    'fallback_attempted': r'fallback to (?:TCP|tcp)|fall back to (?:TCP|tcp)|TCP fallback',
    'process_exit': r'process (?:exited|terminated)|received (?:SIGTERM|SIGKILL)|terminating process',
    'process_restart': r'(?:worker|client|process) (?:is )?restarting|restart (?:the )?(?:worker|client) process',
    'register_again': r're-register|register again|reconnect client:\s*1',
    'heartbeat_lost': r'heartbeat.*(?:lost|timeout|expired)',
    'disk_full': r'No space left on device|ENOSPC|disk (?:is )?full|inode.*exhaust',
    'io_error': r'Input/output error|I/O error|blk_update_request.*error',
    'oom_kill': r'Out of memory: Kill process|oom-kill:|Memory cgroup out of memory',
}
EVENT_RE = {k: re.compile(v, re.I) for k, v in EVENTS.items()}
LIFECYCLE = {'process_exit', 'process_restart', 'register_again', 'heartbeat_lost', 'disk_full', 'io_error', 'oom_kill'}
CODE_RE = re.compile(r'code:\s*\[([^\]]+)\]')
CONST_RE = re.compile(r'\b[A-Z][A-Z0-9_]{3,}\b')
ERR_RE = re.compile(r'\bE\d{3,4}\b')
STOP = {'URMA', 'RPC', 'SHM', 'UB', 'TCP', 'SLOW', 'LOG', 'ID'}
NOISE_RE = re.compile(r'^(?:[CT]:)?[0-9a-fA-F]{16,}$')
RAW_CODE = re.compile(r'\b(?:status_code|error_code|status code)\s*[=:]\s*(-?\d+)\b', re.I)
INFO_TRIGGER = re.compile(rb'process (?:exited|terminated)|SIGTERM|SIGKILL|restarting|restart .*process|re-register|register again|reconnect client:\s*1|heartbeat.*(?:lost|timeout|expired)|No space left|ENOSPC|disk.*full|inode.*exhaust|I/O error|Input/output error|oom-kill|Out of memory|Memory cgroup',re.I)
ALLOWED_FACTS = {'pod_recreated', 'client_process_exit', 'worker_process_exit', 'disk_full', 'oom_kill'}


def number(value):
    return float(value) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(counter):
    values = {str(k): float(v) for k, v in counter.items() if number(v) is not None and v > 0}
    total = sum(values.values())
    return {k: v / total for k, v in sorted(values.items())} if total else {}


def cosine(a, b):
    if not a or not b:
        return None
    norm = math.sqrt(math.fsum(v*v for v in a.values()) * math.fsum(v*v for v in b.values()))
    return math.fsum(v * b.get(k, 0.) for k, v in a.items()) / norm if norm else None


def weighted_overlap(a, b):
    if not a or not b:
        return None
    keys = sorted(a.keys() | b.keys())
    denominator = math.fsum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return math.fsum(min(a.get(k, 0), b.get(k, 0)) for k in keys) / denominator if denominator else None


def set_score(a, b):
    a, b = set(a), set(b)
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else None


def views_operation(header):
    head = re.split(r'[（(]', str(header or '').upper(), 1)[0]
    return sorted(set(re.findall(r'\b(?:GET|SET)\b', head)))


def _time(value):
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (ValueError, TypeError):
        return None


def _time_summary(points):
    if not points:
        return {}
    points = sorted(points)
    total = sum(v for _, v in points)
    if total <= 0:
        return {}
    times = [t for t, v in points if v > 0]
    return {'span_seconds': max(times)-min(times) if times else 0.,
            'peak_share': max(v for _, v in points)/total,
            'occupied_fraction': len(times)/len(points), 'positive_windows': len(times)}


def extract_report(payload, fault_indices=None):
    """Return a closed-schema numeric/identifier-token profile. Never read prose.

    No basic_info.log_semantic_profile is trusted here: semantic profiles must
    come from scan_logs, or be supplied as an explicitly versioned sidecar.
    """
    faults = payload.get('faults') or []
    selected = faults if fault_indices is None else [faults[i] for i in fault_indices]
    views = {}
    modes = set()
    sources = []
    evidence_codes = set()
    audit = Counter()
    def view(op):
        return views.setdefault(op, {'code_counts': {}, 'code_distribution': {}, 'code_complete': None,
                                     'other_share': None, 'buckets': {}, 'numeric': {}, 'time': {},
                                     'sample_count': None, 'truncated': None})
    for fault in selected:
        for anchor in fault.get('evidence_traces') or []:
            if not isinstance(anchor, dict):
                continue
            code = anchor.get('status_code')
            if code is not None and re.fullmatch(r'-?\d+', str(code).strip()):
                evidence_codes.add(str(code).strip())
            mode = anchor.get('failure_mode_id')
            if isinstance(mode, str) and re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}', mode):
                modes.add(mode)
        for bd in (fault.get('error') or {}).get('breakdowns') or []:
            if not isinstance(bd, dict) or bd.get('operation') not in ('GET', 'SET'):
                continue
            op = bd['operation']; dist = bd.get('code_distribution') or {}
            total = number(dist.get('total_count')); complete = (bd.get('coverage') or {}).get('complete') is True
            if total is None or total <= 0:
                continue
            v = view(op)
            # Multiple independent scopes are not silently summed. Matching sees
            # one distribution per source scope; duplicate snapshots deduplicate.
            source_key = digest({'scope': bd.get('scope'), 'dist': dist})
            if source_key in sources:
                continue
            sources.append(source_key)
            counts = {}
            for item in dist.get('items') or []:
                code, count = str(item.get('code', '')).strip(), number(item.get('count'))
                if re.fullmatch(r'-?\d+', code) and count is not None and count > 0:
                    counts[code] = count; evidence_codes.add(code)
            # Keep separate source-key-prefixed distributions only as provenance;
            # use the first valid scope for one view rather than double counting.
            if not v['code_counts']:
                v['code_counts'] = counts
                v['code_complete'] = complete
                if complete:
                    v['code_distribution'] = {k: c/total for k, c in counts.items()}
                    other = number(dist.get('other_count'))
                    v['other_share'] = other/total if other is not None else None
            else:
                audit['additional_error_scope_not_merged'] += 1
            timeline = bd.get('timeline') or {}; points = []
            if complete and not v['time']:
                for w in timeline.get('windows') or []:
                    t = _time(w.get('start_time'))
                    values = list((w.get('counts') or {}).values())
                    if t is not None and w.get('complete') is True and all(number(n) is not None for n in values):
                        points.append((t, sum(values) + (number(w.get('other_count')) or 0)))
                v['time'] = _time_summary(points)
        for stage in (fault.get('latency') or {}).get('stages') or []:
            fs = stage.get('features')
            fs = [fs] if isinstance(fs, dict) else fs if isinstance(fs, list) else []
            for f in fs:
                op, key = f.get('operation'), f.get('bucket_key')
                if op not in ('GET', 'SET') or not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z_0-9]*', key):
                    continue
                n, sample = number(f.get('trace_cnt')), number(f.get('sample_cnt'))
                if n is None or sample is None or sample <= 0 or n > sample:
                    continue
                v = view(op); v['sample_count'] = sample; v['truncated'] = f.get('truncated') is True
                v['buckets'][key] = n/sample
                metric = f.get('metric_name')
                if metric not in ('主阶段耗时', 'URMA timeout elapsedMs', 'Client 总时延（数据面未观测）'):
                    # Unknown display wording must not encode an answer even
                    # through a hash; only upstream metric enums are comparable.
                    audit['unknown_metric_omitted'] += 1
                    metric = None
                if metric:
                    for k in ('p50_ms', 'p90_ms', 'max_ms', 'client_p50_ms', 'client_p90_ms'):
                        value = number((f.get('distribution') or {}).get(k))
                        if value is not None:
                            v['numeric'][f'{key}|{metric}|{k}'] = value
                    request=(f.get('source') or {}).get('request') or {}
                    current_start,current_end=_time(request.get('start_time')),_time(request.get('end_time'))
                    base=f.get('baseline') or {};base_request=(base.get('source') or {}).get('request') or {}
                    base_start,base_end=_time(base_request.get('start_time')),_time(base_request.get('end_time'))
                    same_scope=all(request.get(k)==base_request.get(k) for k in ('kb_id','log_id','operation'))
                    if base and same_scope and base.get('operation')==op and base.get('bucket_key')==key and base.get('metric_name')==f.get('metric_name') and all(x is not None for x in (current_start,current_end,base_start,base_end)) and (base_end<=current_start or current_end<=base_start):
                        a=number((f.get('distribution') or {}).get('p90_ms'));b=number((base.get('distribution') or {}).get('p90_ms'))
                        if a is not None and b is not None and b>0:
                            v['numeric'][f'{key}|{metric}|baseline_p90_amplification']=a/b
                    windows=[]
                    for point in f.get('windows') or []:
                        pr=(point.get('source') or {}).get('request') or {}
                        start,end=_time(pr.get('start_time')),_time(pr.get('end_time'))
                        p90=number((point.get('distribution') or {}).get('p90_ms'))
                        if (point.get('operation')==op and point.get('bucket_key')==key and point.get('metric_name')==f.get('metric_name')
                            and all(request.get(k)==pr.get(k) for k in ('kb_id','log_id','operation'))
                            and all(x is not None for x in (current_start,current_end,start,end))
                            and current_start<=start<end<=current_end and p90 is not None):windows.append((start,end,p90))
                    windows.sort()
                    if len(windows)>=2 and all(a[1]<=b[0] for a,b in zip(windows,windows[1:])):
                        mean=math.fsum(w[2] for w in windows)/len(windows)
                        if mean>0:v['time'][f'{key}:p90_window_cv']=math.sqrt(math.fsum((w[2]-mean)**2 for w in windows)/len(windows))/mean
    if not views:
        for op in views_operation((payload.get('basic_info') or {}).get('operation')):
            view(op)
    tokens = Counter({f'mode:{m}': 1 for m in modes})
    for op, v in views.items():
        tokens[f'operation:{op}'] += 1
        for code in v['code_counts']: tokens[f'{op}:code:{code}'] += 1
        for key in v['buckets']: tokens[f'{op}:bucket:{key}'] += 1
    result = {'schema_version': VERSION, 'views': views, 'codes': sorted(evidence_codes),
              'modes': sorted(modes), 'tokens': dict(tokens), 'log': {}, 'facts': {},
              'audit': dict(audit), 'provenance': {'source': 'report_observed_fields', 'free_text': False}}
    validate_profile(result)
    return result


def _actor(path):
    name = path.name.lower()
    if 'ds_client' in name: return 'client_sdk'
    if 'coordinator' in name: return 'coordinator'
    if name.startswith('kvcache'): return 'worker_process'
    if 'ubm' in name: return 'ubm'
    return 'unknown'


def scan_logs(directory):
    """Extract role/event/family/phase relations from E/W and explicit I events.

    Parent directory names and scenario names are never interpreted. No raw text
    is persisted; references and row hashes remain in provenance only.
    """
    directory = Path(directory)
    if not directory.is_dir(): raise ValueError(f'日志目录不存在：{directory}')
    actors, events, families, interactions, transport, semantics = (Counter() for _ in range(6))
    stats = Counter(); references = []; manifest = []; seen = set(); trace_events = defaultdict(list)
    for path in sorted(p for p in directory.rglob('*') if p.is_file() and p.name.endswith(('.log', '.log.gz'))):
        role = _actor(path); h = hashlib.sha256(); stats['files'] += 1
        opener = gzip.open if path.name.endswith('.gz') else open
        with opener(path, 'rb') as stream:
            for line_number, raw in enumerate(stream, 1):
                h.update(raw); stats['lines'] += 1
                parts = raw.split(b'|', 7)
                if len(parts) != 8 or not re.match(rb'^\d{4}-\d\d-\d\d[T ]', parts[0]): continue
                level = parts[1].strip()
                if level not in (b'I', b'E', b'W'): continue
                if level == b'I' and not INFO_TRIGGER.search(parts[7]): continue
                message = parts[7].decode('utf-8', 'replace').strip()
                hits = [event for event, regex in EVENT_RE.items() if (level != b'I' or event in LIFECYCLE) and regex.search(message)]
                if level == b'I' and not any(event in LIFECYCLE for event in hits): continue
                key = hashlib.sha256(raw.rstrip(b'\r\n')).digest()
                if key in seen: stats['duplicates'] += 1; continue
                seen.add(key); stats['observed_events'] += 1; actors[role] += 1
                if level in (b'E', b'W'):
                    stats['ew_events'] += 1
                    for code in CODE_RE.findall(message):
                        if re.fullmatch(r'[A-Za-z0-9_ .:/()=-]{1,120}', code.strip()): semantics['C:'+code.strip()] += 1.
                    for token in CONST_RE.findall(message):
                        if token not in STOP and not NOISE_RE.fullmatch('T:'+token): semantics['T:'+token] += 3.
                    for code in ERR_RE.findall(message): semantics['T:'+code] += 3.
                phases = []
                for phase, regex in {'completion': r'completion|URMA_WAIT|WaitFor', 'connect': r'connect|handshake',
                                     'metadata': r'query.*meta|metadata owner', 'transfer': r'URMA_WRITE|transfer|dataSize'}.items():
                    if re.search(regex, message, re.I): phases.append(phase)
                for name in ('URMA', 'TCP'):
                    if re.search(r'\b'+name+r'\b|'+name+'_', message, re.I): transport[name] += 1
                for field,pattern in [('payload',r'\bdataSize[=:]\s*(\d+)'),('payload_limit',r'\b(?:payloadLimit|fallbackLimit|maxPayloadSize)[=:]\s*(\d+)')]:
                    match=re.search(pattern,message)
                    if match:
                        size=int(match.group(1));bucket=0 if size==0 else int(math.ceil(math.log2(max(1,size/(1024*1024)))))
                        transport[f'{field}_mib_log2_{bucket}']+=1
                for event in hits:
                    events[f'{role}:{event}'] += 1
                    if event not in LIFECYCLE:
                        families[event] += 1
                    for phase in phases or ['unknown']:
                        interactions[f'{role}|{phase}|{event}'] += 1
                    if len(references) < 80:
                        references.append({'event': event, 'role': role, 'file': str(path.relative_to(directory)),
                                           'line': line_number, 'row_sha256': key.hex()})
                    trace = parts[5].strip().decode('ascii', 'ignore')
                    t = _time(parts[0].strip().decode('ascii', 'ignore'))
                    if re.fullmatch(r'[0-9a-fA-F-]{32,36}', trace) and t is not None and len(trace_events[trace]) < 24:
                        trace_events[trace].append((t, role, event))
        manifest.append({'file': str(path.relative_to(directory)), 'sha256': h.hexdigest()})
    if not stats['files']: raise ValueError(f'没有日志文件：{directory}')
    chains = Counter()
    for sequence in trace_events.values():
        sequence.sort()
        for a, b in zip(sequence, sequence[1:]):
            delta = b[0]-a[0]
            if a[2] != b[2] and delta <= 60:
                bucket = 'same_second' if delta < 1 else 'within_10s' if delta <= 10 else 'within_1m'
                chains[f'{a[1]}:{a[2]}>{b[1]}:{b[2]}:{bucket}'] += 1
    return {'actors': normalize(actors), 'events': normalize(events), 'families': normalize(families),
            'interactions': normalize(interactions), 'transport': normalize(transport),
            'semantic': dict(semantics), 'chains': normalize(chains),
            'scope': {'observed_file_count': stats['files'], 'observed_role_count': len(actors)} if actors else {},
            'provenance': {'source': 'raw_log_messages', 'stats': dict(stats), 'references': references,
                           'files': manifest, 'coverage': 'observed_files_only_not_process_health'}}


def add_observations(profile, observations):
    """Optional measured facts, never inferred from a missing message."""
    profile = json.loads(canonical(profile))
    for key, fact in observations.items():
        if key not in ALLOWED_FACTS or not isinstance(fact, dict) or type(fact.get('value')) is not bool:
            raise ValueError(f'不支持的观测事实：{key}')
        if not isinstance(fact.get('evidence_ref'), str) or not fact['evidence_ref'].strip():
            raise ValueError(f'观测事实缺少来源：{key}')
        if fact.get('verified') is not True:
            raise ValueError(f'观测事实未经核对：{key}')
        profile['facts'][key] = {k: fact[k] for k in ('value', 'evidence_ref', 'verified')}
    return profile


def validate_profile(p):
    allowed = {'schema_version', 'views', 'codes', 'modes', 'tokens', 'log', 'facts', 'audit', 'provenance'}
    if set(p) - allowed or p.get('schema_version') != VERSION:
        raise ValueError('不支持的特征契约或多余字段（标签/文本不得进入profile）')
    if not {'views','codes','modes','tokens','log','facts'} <= p.keys():
        raise ValueError('profile缺少必需字段')
    if not all(re.fullmatch(r'-?\d+', str(c)) for c in p.get('codes', [])):
        raise ValueError('错误码必须是原始数值码')
    # Closed schema recursively: embedding/model scores belong to pair sidecars,
    # never to unconstrained strings in an observed-evidence profile.
    for op, v in p.get('views', {}).items():
        if op not in ('GET', 'SET'): raise ValueError('operation必须为GET/SET')
        expected = {'code_counts','code_distribution','code_complete','other_share','buckets','numeric','time','sample_count','truncated'}
        if set(v)-expected: raise ValueError('operation view存在未知字段')
        for field in ('code_counts','code_distribution','buckets','numeric','time'):
            if any(number(x) is None for x in v.get(field, {}).values()): raise ValueError(f'非法数值：{field}')
        if any(not re.fullmatch(r'-?\d+',k) for k in v.get('code_counts',{})) or any(not re.fullmatch(r'-?\d+',k) for k in v.get('code_distribution',{})):
            raise ValueError('view错误码不是原始数值码')
        if any(not re.fullmatch(r'[a-z][a-z_0-9]*',k) for k in v.get('buckets',{})):
            raise ValueError('bucket必须是上游key')
    if set(p.get('log',{}))-{'actors','events','families','interactions','transport','semantic','chains','scope','provenance'}:
        raise ValueError('log存在未知字段')
    if any(not re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}', m) for m in p.get('modes', [])):
        raise ValueError('failure mode必须是上游ID')
    expected_tokens=Counter({f'mode:{m}':1 for m in p['modes']})
    for op,v in p['views'].items():
        expected_tokens[f'operation:{op}']+=1
        for code in v.get('code_counts',{}):expected_tokens[f'{op}:code:{code}']+=1
        for key in v.get('buckets',{}):expected_tokens[f'{op}:bucket:{key}']+=1
    if dict(expected_tokens)!=p['tokens']:
        raise ValueError('tokens必须由观测字段确定性构造，不能写入标签或自由文本')
    for field in ('actors','events','families','interactions','transport','semantic','chains','scope'):
        for key,value in p.get('log',{}).get(field,{}).items():
            if not isinstance(key,str) or re.search(r'[^\x20-\x7e]',key) or number(value) is None:
                raise ValueError('日志特征只能为观测ASCII token和非负有限数值')
    if any(key not in ALLOWED_FACTS or type(fact.get('value')) is not bool or fact.get('verified') is not True
           or not fact.get('evidence_ref') for key,fact in p.get('facts',{}).items()):
        raise ValueError('facts必须是带来源的已核对观测')
    return p


def mechanism_tokens(p):
    tokens = Counter(p.get('tokens', {}))
    log = p.get('log') or {}
    for channel in ('events','families','interactions','transport','chains'):
        for k, v in log.get(channel, {}).items(): tokens[f'{channel}:{k}'] += v
    return tokens


def pool_statistics(cases):
    semantic_df, token_df = Counter(), Counter(); lengths = []
    for case in cases:
        p = case['profile']; semantic_df.update((p.get('log') or {}).get('semantic', {}).keys())
        t = mechanism_tokens(p); token_df.update(t.keys()); lengths.append(sum(t.values()))
    n = len(cases)
    return {'semantic_idf': {k: math.log((n+1)/(df+1))+1 for k, df in semantic_df.items()},
            'token_idf': {k: math.log(1+(n-df+.5)/(df+.5)) for k, df in token_df.items()},
            'average_length': sum(lengths)/n if n else 1., 'n': n}


def _numeric_similarity(a, b):
    keys = sorted(a.keys() & b.keys())
    return math.fsum(math.exp(-abs(math.log1p(a[k])-math.log1p(b[k]))) for k in keys)/len(keys) if keys else None


def _semantic(p, stats):
    return {k: v*stats['semantic_idf'].get(k, 1.) for k, v in (p.get('log') or {}).get('semantic', {}).items()
            if not NOISE_RE.fullmatch(k)}


def compare(q, c, stats, mode_parents=None):
    """Label-blind pair features; returns None for unobserved channels."""
    common = q['views'].keys() & c['views'].keys(); values = defaultdict(list)
    for op in sorted(common):
        a, b = q['views'][op], c['views'][op]
        if a.get('code_complete') is True and b.get('code_complete') is True:
            # Unknown 'other' identities cannot score as matching code symbols.
            hit = math.fsum(min(a['code_distribution'].get(k,0), b['code_distribution'].get(k,0))
                      for k in sorted(a['code_distribution'].keys() | b['code_distribution'].keys()))
            if a['code_distribution'] and b['code_distribution']: values['codes'].append(hit)
        else:
            s = set_score(a.get('code_counts',{}), b.get('code_counts',{}))
            if s is not None: values['codes'].append(s)
        for channel, a_field, b_field, fn in [('stages','buckets','buckets',weighted_overlap),
                                            ('numeric','numeric','numeric',_numeric_similarity),
                                            ('time','time','time',_numeric_similarity)]:
            s = fn(a.get(a_field,{}), b.get(b_field,{}))
            if s is not None: values[channel].append(s)
    out = {k: sum(v)/len(v) for k, v in values.items() if v}
    out['operation'] = set_score(q['views'], c['views'])
    if 'codes' not in out: out['codes'] = set_score(q['codes'], c['codes'])
    exact = set_score(q['modes'], c['modes'])
    if mode_parents and exact is not None:
        parent = set_score([mode_parents[m] for m in q['modes'] if m in mode_parents],
                           [mode_parents[m] for m in c['modes'] if m in mode_parents])
        exact = max(exact, .7*parent) if parent is not None else exact
    out['modes'] = exact
    a, b = q.get('log') or {}, c.get('log') or {}
    for channel, field, fn in [('families','families',weighted_overlap),('actor','actors',weighted_overlap),
                               ('lifecycle','events',weighted_overlap),('transport','transport',weighted_overlap),
                               ('interaction','interactions',weighted_overlap),('scope','scope',_numeric_similarity)]:
        if channel == 'lifecycle':
            aa = {k:v for k,v in a.get(field,{}).items() if k.split(':')[-1] in LIFECYCLE}
            bb = {k:v for k,v in b.get(field,{}).items() if k.split(':')[-1] in LIFECYCLE}
        else: aa, bb = a.get(field,{}), b.get(field,{})
        out[channel] = fn(aa, bb)
    out['semantic'] = cosine(_semantic(q, stats), _semantic(c, stats))
    qa, cb = mechanism_tokens(q), mechanism_tokens(c)
    out['mechanism'] = cosine(qa, cb)
    if qa and cb:
        dl, avg = sum(cb.values()), max(stats['average_length'],1e-9)
        raw = math.fsum(stats['token_idf'].get(k,0)*cb.get(k,0)*2.2/(cb.get(k,0)+1.2*(.25+.75*dl/avg)) for k in qa if cb.get(k))
        out['bm25'] = 1-math.exp(-raw/max(1,len(qa)))
    else: out['bm25'] = None
    contradictions = [k for k in q.get('facts',{}).keys() & c.get('facts',{}).keys()
                      if q['facts'][k]['value'] != c['facts'][k]['value']]
    return {k: out.get(k) for k in CHANNELS}, contradictions
