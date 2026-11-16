"""Explicit alternative to K4, using a supplied trained model and shared features."""
import json
from pathlib import Path
import feature_vectors
import fixed_matching
import portable_classifier


def features(profile,structured,raw,rows,view):
    values=feature_vectors.build_observations(profile,structured,raw)
    if view=='base_observations':
        return {k:v for k,v in values.items() if k.startswith(('query:legacy:','query:semantic:'))}
    if view=='all_observations':return values
    if view=='all_observations_and_retrieval':
        values.update(feature_vectors.retrieval_features(rows))
        for label in feature_vectors.LABELS:
            candidates=[r for r in rows if r['first_level_label']==label]
            if candidates:
                for key,value in candidates[0].get('all_feature_values',{}).items():
                    values[f'retrieval:{label}:all:{key}:known']=float(value is not None)
                    values[f'retrieval:{label}:all:{key}']=value or 0.
        return values
    raise ValueError('Unknown classifier feature view')


def match(profile,cases,structured,raw,model):
    if isinstance(model,(str,Path)):model=json.loads(Path(model).read_text())
    if model.get('metadata',{}).get('feature_version')!=feature_vectors.VERSION:
        raise ValueError('Classifier feature version does not match current extractor')
    result=fixed_matching.match(profile,cases,structured,raw)
    if result['decision']['method'] in ('empty','user_usage_rule'):return result
    values=features(profile,structured,raw,result['candidates'],model['view'])
    decision=portable_classifier.predict(model,values)
    decision.update(method='explicit_classifier',model_id=model['metadata']['model_id'],
                    policy='all-feature-classifier-v1')
    result.update(decision=decision,policy='all-feature-classifier-v1')
    return result
