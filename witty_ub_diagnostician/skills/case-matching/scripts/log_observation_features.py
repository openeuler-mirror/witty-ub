#!/usr/bin/env python3
"""Runtime log words, process impact and component features for Agent diagnosis."""
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import hashlib
import math
from pathlib import Path
import re

import log_message_features as messages
from enhanced_matching import _actor


def add_messages(obs, directory):
    """Extend one raw observation from measured files; no report/GT input."""
    directory = Path(directory)
    counts, seen, references = Counter(), set(), []
    for source in obs['provenance']['files']:
        path = directory/source['file']
        digest = hashlib.sha256()
        with (gzip.open if path.name.endswith('.gz') else open)(path, 'rb') as stream:
            for line, raw in enumerate(stream, 1):
                digest.update(raw)
                # Fast header test; the parsed level below remains authoritative.
                header = raw[:70]
                if b'E' not in header and b'W' not in header:
                    continue
                parts = raw.split(b'|', 7)
                if len(parts)!=8 or parts[1].strip() not in (b'E', b'W'):
                    continue
                identity = hashlib.sha256(raw.rstrip(b'\r\n')).hexdigest()
                if identity in seen:
                    continue
                seen.add(identity)
                features = messages.message_features(parts[7])
                counts.update(features)
                if features and len(references)<100:
                    references.append({'file': source['file'], 'line': line, 'row_sha256': identity,
                                       'feature_names': sorted(features)})
        if digest.hexdigest()!=source['sha256']:
            raise ValueError('Raw log hash changed: '+str(path))
    # Saturate within-document repetition; no corpus vocabulary/IDF is fit here.
    norm = math.sqrt(sum(math.log1p(v)**2 for v in counts.values())) or 1.
    obs['features'].update({'raw:'+k: math.log1p(v)/norm for k, v in counts.items()})
    obs['provenance']['message_references'] = references
    obs['provenance']['ew_event_count'] = len(seen)
    return obs


def add_structure(observation, directory):
    """Extend one raw observation from measured files; no report/GT input."""
    directory = Path(directory)
    roles = {}
    components = Counter()
    seen = set()
    references = []
    for source in observation['provenance']['files']:
        path = directory/source['file']
        role = _actor(path)
        stats = roles.setdefault(role, {'rows': 0, 'ew': 0, 'processes': set(), 'error_processes': set(),
            'hosts': set(), 'error_hosts': set(), 'by_host': defaultdict(set), 'error_windows': Counter(), 'first': None, 'last': None})
        digest = hashlib.sha256()
        with (gzip.open if path.name.endswith('.gz') else open)(path, 'rb') as stream:
            for line, raw in enumerate(stream, 1):
                digest.update(raw)
                parts = raw.split(b'|', 7)
                if len(parts)!=8 or parts[1].strip() not in (b'I', b'W', b'E'):
                    continue
                timestamp = parts[0].strip()
                if not re.match(rb'^\d{4}-\d\d-\d\dT', timestamp):
                    continue
                stats['rows'] += 1
                stats['first'] = min(stats['first'] or timestamp, timestamp)
                stats['last'] = max(stats['last'] or timestamp, timestamp)
                pid = parts[4].strip().split(b':', 1)[0]
                host = parts[3].strip()
                process = (host, pid)
                if pid.isdigit():
                    stats['processes'].add(process); stats['by_host'][host].add(pid)
                if host:
                    stats['hosts'].add(host)
                if parts[1].strip() not in (b'E', b'W'):
                    continue
                identity = hashlib.sha256(raw.rstrip(b'\r\n')).hexdigest()
                if identity in seen:
                    continue
                seen.add(identity)
                stats['ew'] += 1
                stats['error_windows'][timestamp[:16]] += 1
                if pid.isdigit(): stats['error_processes'].add(process)
                if host: stats['error_hosts'].add(host)
                location = parts[2].strip().split(b':', 1)[0]
                if re.fullmatch(rb'[a-zA-Z][a-zA-Z0-9_]{0,80}\.(?:cpp|cc|c|h)', location):
                    key = role+':'+location.decode()
                    components[key] += 1
                    if components[key]==1 and len(references)<100:
                        references.append({'component': key, 'file': source['file'], 'line': line, 'row_sha256': identity})
        if digest.hexdigest()!=source['sha256']:
            raise ValueError('Raw log hash changed: '+str(path))
    features = observation['features']
    for role, stats in roles.items():
        if not stats['rows']:
            continue
        prefix = 'raw:structure:'+role+':'
        features[prefix+'observed'] = 1.
        features[prefix+'error_row_fraction'] = stats['ew']/stats['rows']
        if stats['processes']:
            features[prefix+'observed_process_count'] = math.log1p(len(stats['processes']))
            features[prefix+'error_process_fraction'] = len(stats['error_processes'])/len(stats['processes'])
            features[prefix+'max_processes_per_host'] = math.log1p(max(map(len, stats['by_host'].values())))
        if stats['hosts']:
            features[prefix+'error_host_fraction'] = len(stats['error_hosts'])/len(stats['hosts'])
        if stats['ew']:
            features[prefix+'error_peak_minute_share'] = max(stats['error_windows'].values())/stats['ew']
            features[prefix+'error_minute_count'] = math.log1p(len(stats['error_windows']))
        try:
            span = (datetime.fromisoformat(stats['last'].decode())-datetime.fromisoformat(stats['first'].decode())).total_seconds()
            features[prefix+'observed_span_seconds'] = math.log1p(max(0., span))
        except ValueError:
            pass
    total = sum(components.values()) or 1
    features.update({'raw:component:'+k: count/total for k, count in components.items()})
    observation['provenance']['component_references'] = references
    return observation
