#!/usr/bin/env python3
"""Finite, label-blind telemetry extraction from raw log message columns.

Only basename component conventions select a role. Parent/scenario names, raw
identities, absolute dates, source-code locations and report prose are excluded.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import math
from pathlib import Path
import re

from enhanced_matching import _actor

VERSION = 'raw-observations-v1'
PATTERNS = {
    'disk_full': rb'No space left on device|\bENOSPC\b|disk (?:is )?full|inode.*exhaust',
    'io_error': rb'Input/output error|I/O error|blk_update_request.*error',
    'oom': rb'oom-kill|Out of memory|Memory cgroup out of memory',
    'process_exit': rb'process (?:exited|terminated)|received (?:SIGTERM|SIGKILL)|terminating process',
    'process_restart': rb'(?:worker|client|process) (?:is )?restarting|restart (?:the )?(?:worker|client) process',
    'heartbeat_loss': rb'heartbeat.*(?:lost|timeout|expired)',
    'client_reconnect': rb'reconnect client:\s*1|re-register|register again',
    'connection_refused': rb'connection refused|failed to connect',
    'urma_timeout': rb'URMA_WAIT_TIMEOUT|Urma wait for completion timed out',
    'urma_post_failure': rb'URMA_POST.*FAIL|post (?:send|write).*fail',
    'rpc_peer_dead': rb'RPC peer dead|Metadata owner unavailable|K_RPC_UNAVAILABLE',
    'rpc_timeout': rb'deadline exceeded|RPC.*(?:timed out|timeout)',
    'fallback_rejected': rb'(?:fallback|fall back).*?(?:reject|refus|exceed|limit)',
    'fallback_success': rb'(?:fallback|fall back).*?(?:succeed|success)',
}
EVENTS = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
TRIGGERS = (b'ub_port_health', b'cluster_lifecycle', b'worker_startup', b'cluster_membership_observed',
            b'no space', b'enospc', b'disk ', b'inode', b'i/o error', b'input/output',
            b'blk_update', b'oom-', b'out of memory', b'process ', b'sigterm', b'sigkill',
            b'restarting', b'restart ', b'heartbeat', b'reconnect client', b're-register',
            b'register again', b'connection refused', b'failed to connect',
            b'urma_wait', b'urma wait', b'urma_post', b'post send', b'post write',
            b'rpc peer', b'metadata owner', b'k_rpc_unavailable', b'deadline exceeded',
            b'rpc', b'fallback', b'fall back')
INFO_TRIGGERS = (b'UB_PORT_HEALTH', b'CLUSTER_LIFECYCLE', b'WORKER_STARTUP', b'CLUSTER_MEMBERSHIP_OBSERVED',
                 b'ENOSPC', b'No space', b'Out of memory', b'oom-kill', b'I/O error',
                 b'Input/output error', b'SIGTERM', b'SIGKILL', b'exited', b'terminated',
                 b'restarting', b'restart ', b're-register', b'register again', b'reconnect client: 1')
TRIGGER = re.compile(b'|'.join(b'(?:'+v+b')' for v in PATTERNS.values()) +
                     rb'|UB_PORT_HEALTH|CLUSTER_LIFECYCLE|WORKER_STARTUP|CLUSTER_MEMBERSHIP_OBSERVED', re.I)
NUMBER = re.compile(rb'\b([a-z_]+)=(-?\d+(?:\.\d+)?)\b')
TIMESTAMP = re.compile(rb'^\d{4}-\d\d-\d\d[T ]')


def message_features(message, role):
    """Return only fixed event/numeric names; no arbitrary log words."""
    result = {f'{role}:event:{key}': 1. for key, pattern in EVENTS.items() if pattern.search(message)}
    numbers = {k.decode(): float(v) for k, v in NUMBER.findall(message)}
    if b'UB_PORT_HEALTH' in message:
        result[f'{role}:ports:observed'] = 1.
        for field in ('valid', 'pending', 'bad', 'total', 'query_status_code'):
            if field in numbers:
                result[f'{role}:ports:{field}'] = max(0., numbers[field])
        if numbers.get('total', 0)>0 and 'bad' in numbers:
            result[f'{role}:ports:bad_share'] = numbers['bad']/numbers['total']
    if b'CLUSTER_LIFECYCLE' in message or b'WORKER_STARTUP' in message:
        result[f'{role}:lifecycle:observed'] = 1.
        for field in ('restart', 'is_restart', 'control_backend_available', 'enable_reconciliation'):
            match = re.search(rb'\b'+field.encode()+rb'=(true|false|[01])\b', message, re.I)
            if match:
                result[f'{role}:lifecycle:{field}'] = float(match[1].lower() in (b'true', b'1'))
        # A restart=true/1 is positive evidence; initial startup is separate.
        if re.search(rb'\b(?:restart|is_restart)=(?:1|true)\b', message):
            result[f'{role}:lifecycle:restart_positive'] = 1.
        if re.search(rb'\b(?:restart|is_restart)=(?:0|false)\b', message):
            result[f'{role}:lifecycle:initial_start'] = 1.
        for state in ('constructed', 'exiting', 'failed', 'recovering', 'ready'):
            if re.search(rb'\bstate='+state.encode()+rb'\b', message):
                result[f'{role}:lifecycle:state:{state}'] = 1.
    if b'CLUSTER_MEMBERSHIP_OBSERVED' in message:
        result[f'{role}:membership:observed'] = 1.
        for field in ('member_count', 'starting', 'restarting', 'recovering', 'ready', 'exiting', 'failed'):
            if field in numbers:
                result[f'{role}:membership:{field}'] = numbers[field]
        total = numbers.get('member_count', 0)
        if total>0:
            for state in ('starting', 'restarting', 'recovering', 'ready', 'exiting', 'failed'):
                if state in numbers:
                    result[f'{role}:membership:{state}_share'] = numbers[state]/total
    return result


def scan(directory, expected_files=None):
    directory = Path(directory)
    files = sorted(p for p in directory.rglob('*') if p.is_file() and p.name.endswith(('.log', '.log.gz')))
    expected = {item['file']: item['sha256'] for item in expected_files or []}
    if expected and {str(p.relative_to(directory)) for p in files} != set(expected):
        raise ValueError('Raw log file set differs from frozen evidence')
    maximum, counts, references = {}, Counter(), []
    seen = set()
    manifest = []
    for path in files:
        role = _actor(path)
        digest = hashlib.sha256()
        with (gzip.open if path.name.endswith('.gz') else open)(path, 'rb') as stream:
            for line, raw in enumerate(stream, 1):
                digest.update(raw)
                parts = raw.split(b'|', 7)
                if len(parts)!=8 or not TIMESTAMP.match(parts[0]) or parts[1].strip() not in (b'I', b'W', b'E'):
                    continue
                message = parts[7]
                if parts[1].strip() == b'I':
                    if not any(token in message for token in INFO_TRIGGERS):
                        continue
                elif not any(token in message.lower() for token in TRIGGERS):
                    continue
                values = message_features(message, role)
                if not values:
                    continue
                identity = hashlib.sha256(raw.rstrip(b'\r\n')).hexdigest()
                if identity in seen:
                    continue
                seen.add(identity)
                for key, value in values.items():
                    if value > maximum.get(key, -1):
                        maximum[key] = value
                        if len(references)<200:
                            references.append({'feature': key, 'value': value, 'file': str(path.relative_to(directory)),
                                               'line': line, 'row_sha256': identity})
                    if ':event:' in key or ':lifecycle:' in key:
                        counts[key] += 1
        relative = str(path.relative_to(directory))
        if expected and digest.hexdigest()!=expected[relative]:
            raise ValueError(f'Raw log hash differs from frozen evidence: {relative}')
        manifest.append({'file': relative, 'sha256': digest.hexdigest()})
    features = {'raw:max:'+key: value for key, value in maximum.items()}
    features.update({'raw:count:'+key: math.log1p(value) for key, value in counts.items()})
    return {'schema_version': VERSION, 'features': features,
            'provenance': {'source': 'raw_log_message_column', 'files': manifest, 'references': references,
                           'coverage': 'observed_files_only', 'missing_is_healthy': False}}
