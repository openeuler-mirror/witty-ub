#!/usr/bin/env python3
"""Identity-free word/phrase observations from E/W message columns only."""
from collections import Counter
import re

IDENTITY_FIELD = re.compile(
    r'\b(?:trace_?id|request_?id|instance_?id|client_?id|worker_?id|session_?id|'
    r'cluster(?:_?name|_?id)?|tenant_?id|object_?key|object_?id|obj_?key|key|keys|'
    r'address|local_address|remote_address|pod|hostname|host|socket_?fd)\s*[:=]\s*'
    r'(?:\[[^\]]*\]|"[^"]*"|\'[^\']*\'|[^\s,;\]\)]+)', re.I)
UUID = re.compile(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', re.I)
IP = re.compile(r'\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b')
HEX = re.compile(r'\b(?:0x)?[0-9a-f]{12,}\b', re.I)
PATH = re.compile(r'(?:[A-Za-z]:)?[/\\][^\s,;\]\)]+')
MIXED_ID = re.compile(r'\b[A-Za-z0-9_]*\d[A-Za-z0-9_]*\b')
HYPHENATED_ID = re.compile(r'\b(?:[A-Za-z0-9_]+-){2,}[A-Za-z0-9_]+\b')
WORDS = re.compile(r'\b[A-Za-z][A-Za-z_]{1,48}\b')
STOP = {'the', 'a', 'an', 'to', 'of', 'for', 'at', 'in', 'is', 'on', 'and', 'or',
        'with', 'from', 'by', 'as', 'it', 'this', 'that', 'id', 'traceid', 'trace',
        'cluster', 'hostname', 'address', 'key', 'keys', 'uuid', 'true', 'false'}


def tokens(message):
    text = message.decode('utf-8', 'replace') if isinstance(message, bytes) else str(message)
    text = IDENTITY_FIELD.sub(' ', text)
    for regex in (UUID, IP, HEX, PATH, HYPHENATED_ID, MIXED_ID):
        text = regex.sub(' ', text)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return [w.lower() for w in WORDS.findall(text) if w.lower() not in STOP]


def message_features(message):
    words = tokens(message)
    features = Counter('word:'+w for w in words)
    features.update('phrase:'+a+'_'+b for a, b in zip(words, words[1:]))
    return features
