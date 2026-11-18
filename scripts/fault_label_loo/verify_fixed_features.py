#!/usr/bin/env python3
"""Re-extract every fixed feature and compare with the frozen experiment."""
import argparse
import hashlib
import json
from pathlib import Path

import skill_runtime
from skill_runtime import SCRIPTS
import fixed_observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse to overwrite feature verification')
    prepared_path = args.reference_run/'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    reference = json.loads((args.reference_run/'raw_observations.json').read_text())
    result = {'schema_version': 'raw-observation-cache-v1',
              'prepared_sha256': hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
              'extractor_sha256': hashlib.sha256((SCRIPTS/'raw_observations.py').read_bytes()).hexdigest(),
              'message_extractor_sha256': hashlib.sha256((SCRIPTS/'log_message_features.py').read_bytes()).hexdigest(),
              'structure_extractor_name': 'log_observation_features.py',
              'structure_extractor_sha256': hashlib.sha256((SCRIPTS/'log_observation_features.py').read_bytes()).hexdigest(),
              'reports': {}}
    features = 0
    for i, query in enumerate(prepared['reports'], 1):
        qid = query['source_id']
        expected = reference['reports'][qid]
        profile = fixed_observations.scan(args.data_root/query['group']/query['name'], expected['provenance']['files'])
        if profile['features']!=expected['features']:
            keys = profile['features'].keys() | expected['features'].keys()
            changed = [k for k in keys if profile['features'].get(k)!=expected['features'].get(k)]
            raise AssertionError((qid, changed[:20]))
        result['reports'][qid] = profile
        features += len(profile['features'])
        if i%25==0 or i==len(prepared['reports']):
            print(f'fixed features exact {i}/{len(prepared["reports"])}', flush=True)
    args.out.mkdir(parents=True)
    (args.out/'raw_observations.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    (args.out/'validation.json').write_text(json.dumps({'status': 'passed', 'queries': len(prepared['reports']),
        'feature_values_exact': features, 'feature_set': fixed_observations.FEATURE_SET}, indent=2)+'\n')


if __name__=='__main__':
    main()
