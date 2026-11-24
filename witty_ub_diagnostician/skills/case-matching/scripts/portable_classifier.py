"""Explicit classifier inference, standard library only; never trains."""
import math
import struct
VERSION = 'label-reranker-v1'

def predict(model, features):
    """Evaluate an exported model, with unknown features ignored."""
    if model.get('schema_version') != VERSION:
        raise ValueError('Unsupported label model')
    names = model['feature_names']
    vector = [features.get(name, 0.) for name in names]
    if model['kind'] == 'logistic':
        logits = [b + math.fsum(w*x for w, x in zip(weights, vector))
                  for weights, b in zip(model['coefficients'], model['intercept'])]
        if len(logits) == 1 and len(model['classes']) == 2:
            logits = [0., logits[0]]
        maximum = max(logits)
        exp = [math.exp(x-maximum) for x in logits]
        scores = [x/sum(exp) for x in exp]
    elif model['kind'] == 'extra_trees':
        if 'feature_scale' in model:
            # sklearn's tree prediction validates the scaled matrix as float32.
            # Comparing unscaled float64 inputs against rescaled thresholds can
            # take another branch exactly at a split boundary.
            vector = [struct.unpack('f', struct.pack('f', x/scale))[0]
                      for x, scale in zip(vector, model['feature_scale'])]
        scores = [0.] * len(model['classes'])
        for tree in model['trees']:
            node = 0
            while tree['left'][node] != -1:
                node = tree['left'][node] if vector[tree['feature'][node]] <= tree['threshold'][node] else tree['right'][node]
            values = tree['value'][node]
            total = sum(values)
            for i, value in enumerate(values):
                scores[i] += value / total / len(model['trees'])
    else:
        raise ValueError('Unsupported model kind')
    ranked = sorted(zip(model['classes'], scores), key=lambda item: -item[1])
    return {'label': ranked[0][0], 'scores': dict(ranked), 'method': model['kind'],
            'score_margin': ranked[0][1] - ranked[1][1] if len(ranked)>1 else ranked[0][1]}
