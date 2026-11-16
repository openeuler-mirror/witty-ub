#!/usr/bin/env python3
"""Explicit candidate inference for supervised contextual-log features."""
import argparse
import json
from pathlib import Path

import feature_vectors
import fixed_matching
import mined_log_features
import mined_log_features_v2
import portable_classifier


def classify(report,log_dir,model):
    version=model.get('metadata',{}).get('feature_version')
    module=mined_log_features_v2 if version==mined_log_features_v2.VERSION else mined_log_features
    if version!=module.VERSION:
        raise ValueError('Expected a contextual-log candidate model')
    context=module.scan(log_dir)
    if model['view'] in ('v5','v5_contextual','v5_numeric_context','v1_contextual','all_context_v2'):
        profile,structured,raw=fixed_matching.extract_report(report,log_dir)
        base=feature_vectors.build_observations(profile,structured,raw)
    else:base={}
    features=module.vector(model['view'],base,context)
    decision=portable_classifier.predict(model,features)
    return {'policy':'experimental-contextual-classifier-v1','decision':decision,
            'feature_version':module.VERSION,'view':model['view'],
            'source':'log_message_columns','rows':context['provenance']['rows']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--log-dir',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=classify(json.loads(args.report.read_text()),args.log_dir,json.loads(args.model.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(args.out)


if __name__=='__main__':main()
