#!/usr/bin/env python3
"""Complete fixed raw feature set shared by report export and offline tools."""
import hashlib
from pathlib import Path

import raw_observations
from log_observation_features import add_messages, add_structure

FEATURE_SET = 'fixed-observations-v1'


def scan(directory, expected_files=None):
    result = raw_observations.scan(directory, expected_files)
    add_messages(result, directory)
    add_structure(result, directory)
    result['provenance']['feature_set'] = FEATURE_SET
    result['provenance']['extractors'] = {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ('raw_observations.py', 'log_message_features.py',
                     'log_observation_features.py')}
    return result


def unknown():
    """Explicit absence of log observations, never synthetic healthy events."""
    return {'schema_version': raw_observations.VERSION, 'features': {},
            'provenance': {'feature_set': FEATURE_SET, 'source': 'unavailable',
                           'files': [], 'coverage': 'unknown', 'missing_is_healthy': False}}
