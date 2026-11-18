#!/usr/bin/env python3
"""Extend measured telemetry with sanitized E/W words and adjacent phrases."""
import argparse
import hashlib
import json
from pathlib import Path

import skill_runtime
from skill_runtime import SCRIPTS
import log_message_features as messages
from log_observation_features import add_messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--telemetry', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse to overwrite observations')
    result = json.loads(args.telemetry.read_text())
    prepared = json.loads(args.prepared.read_text())
    if result['prepared_sha256']!=hashlib.sha256(args.prepared.read_bytes()).hexdigest():
        raise ValueError('Prepared input mismatch')
    result['message_extractor_sha256'] = hashlib.sha256(Path(messages.__file__).read_bytes()).hexdigest()
    for i, query in enumerate(prepared['reports'], 1):
        obs = result['reports'][query['source_id']]
        add_messages(obs, args.data_root/query['group']/query['name'])
        if i%25==0 or i==len(prepared['reports']):
            print(f'sanitized E/W messages {i}/{len(prepared["reports"])}', flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(args.out, flush=True)


if __name__ == '__main__':
    main()
