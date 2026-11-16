"""Offline fitting; portable inference is implemented inside the skill."""
import skill_runtime
import portable_classifier
SEED=1717

def fit_model(features, truths, config):
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import MaxAbsScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    vectorizer = DictVectorizer(sparse=False)
    matrix = vectorizer.fit_transform(features)
    scaler = MaxAbsScaler().fit(matrix)
    matrix = scaler.transform(matrix)
    indices, labels, weights = [], [], []
    for i, truth in enumerate(truths):
        for label in truth:
            indices.append(i); labels.append(label); weights.append(1./len(truth))
    if len(set(labels))<2:
        raise ValueError('Training fold contains fewer than two classes')
    if config['kind'] == 'logistic':
        classifier = LogisticRegression(C=config['C'], solver='lbfgs', max_iter=1500, tol=1e-5,
                                        class_weight=config.get('class_weight'))
    else:
        forest = RandomForestClassifier if config.get('forest') else ExtraTreesClassifier
        classifier = forest(n_estimators=96, max_depth=config['depth'],
                                         min_samples_leaf=3, random_state=SEED, n_jobs=1)
    classifier.fit(matrix[indices], labels, sample_weight=weights)
    return vectorizer, scaler, classifier

def model_predictions(model, features):
    vectorizer, scaler, classifier = model
    return classifier.predict(scaler.transform(vectorizer.transform(features))).tolist()

def export_model(model, config, view):
    vectorizer, scaler, classifier = model
    result = {'schema_version': portable_classifier.VERSION, 'kind': config['kind'], 'view': view,
              'classes': classifier.classes_.tolist(), 'feature_names': vectorizer.get_feature_names_out().tolist()}
    if config['kind'] == 'logistic':
        result['coefficients'] = (classifier.coef_/scaler.scale_).tolist()
        result['intercept'] = classifier.intercept_.tolist()
    else:
        result['trees'] = []
        result['feature_scale'] = scaler.scale_.tolist()
        result['input_dtype'] = 'float32'
        for estimator in classifier.estimators_:
            tree = estimator.tree_
            result['trees'].append({'left': tree.children_left.tolist(), 'right': tree.children_right.tolist(),
                'feature': tree.feature.tolist(), 'threshold': tree.threshold.tolist(), 'value': tree.value[:, 0, :].tolist()})
    return result
