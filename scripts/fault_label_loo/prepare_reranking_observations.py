#!/usr/bin/env python3
"""Extract immutable additional telemetry, verifying frozen source hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import skill_runtime
from skill_runtime import SCRIPTS
import raw_observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse to overwrite an observation cache')
    prepared = json.loads(args.prepared.read_text())
    result = {'schema_version': 'raw-observation-cache-v1',
              'prepared_sha256': hashlib.sha256(args.prepared.read_bytes()).hexdigest(),
              'extractor_sha256': hashlib.sha256(Path(raw_observations.__file__).read_bytes()).hexdigest(),
              'reports': {}}
    for i, query in enumerate(prepared['reports'], 1):
        folder = args.data_root / query['group'] / query['name']
        expected = query['structured']['log'].get('provenance', {}).get('files', [])
        if not expected:
            raise ValueError('Cannot verify raw observations without frozen source hashes')
        result['reports'][query['source_id']] = raw_observations.scan(folder, expected)
        if i%25==0 or i==len(prepared['reports']):
            print(f'raw telemetry {i}/{len(prepared["reports"])}', flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(args.out, flush=True)


if __name__ == '__main__':
    main()
