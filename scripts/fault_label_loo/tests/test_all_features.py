import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import skill_runtime
from skill_runtime import SCRIPTS
sys.path.insert(0,str(SCRIPTS.parents[1]/'diagnostic-report-generation/scripts'))
import all_feature_matching as matching
import classifier_matching
import classifier_training
import compare_paths
import feature_vectors
import fixed_matching
import generate_report
import portable_classifier
from test_fixed_policy import inputs
from test_render_report_cli import report_data
from test_loo import dataset


class AllFeatureTests(unittest.TestCase):
    def test_every_raw_family_reaches_pair_scores(self):
        q,s,raw,cases=inputs()
        raw['features']={'raw:max:worker_process:event:disk_full':1.,
            'raw:count:worker_process:event:disk_full':1.,'raw:word:peer':.5,
            'raw:phrase:peer_dead':.5,'raw:structure:worker_process:error_host_fraction':0.,
            'raw:component:worker_process:urma.cpp':1.}
        raw['provenance']['source']='raw_log_message_column'
        case={**cases[0],'raw_observations':copy.deepcopy(raw)}
        before=fixed_matching.match(q,[case],s,raw)['candidates'][0]
        for block in ('telemetry','words','phrases','structure','components'):
            self.assertAlmostEqual(before['all_feature_values'][block],1.)
        case['raw_observations']=None
        after=fixed_matching.match(q,[case],s,raw)['candidates'][0]
        self.assertGreater(before['score_norm'],after['score_norm'])
        self.assertIsNone(after['all_feature_values']['structure'])
        with self.assertRaises(ValueError):
            feature_vectors.build_observations(q,s,{**raw,'truth':['OS故障']})

    def test_source_split_is_persistent_and_alias_safe(self):
        try:import sklearn
        except ImportError:self.skipTest('training extras not installed')
        p,raw=dataset()
        originals=copy.deepcopy(p['reports'])
        p['reports']=[]
        for repeat in range(8):
            for index,q in enumerate(originals):
                p['reports'].append({**q,'source_id':q['source_id']+f'-{repeat}',
                    'identity':[value+f'-{repeat}' for value in q['identity']]})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=compare_paths.split_dataset(p,root,'inputs')
            before=(root/'split.json').read_bytes()
            second=compare_paths.split_dataset(p,root,'inputs')
            self.assertEqual(first,second)
            self.assertEqual(before,(root/'split.json').read_bytes())
            groups=compare_paths.io.source_groups(p['reports'],'source')
            self.assertFalse({groups[i] for i in first['train_indices']}&{groups[i] for i in first['validation_indices']})

    def test_cached_bank_matches_public_agent_path(self):
        p,raw=dataset()
        with tempfile.TemporaryDirectory() as tmp:
            banks=compare_paths.Banks(p,raw,Path(tmp))
            sources={q['source_id'] for q in p['reports']}
            cases=banks.candidates(0,sources)
            q=p['reports'][0]
            direct=fixed_matching.match(q['profile'],cases,q['structured'],raw['reports'][q['source_id']])
            self.assertEqual(direct['candidates'],banks.ranked(0,cases)['all_feature_k4'])

    def test_training_vocabulary_excludes_unseen_validation_word(self):
        try:import sklearn
        except ImportError:self.skipTest('training extras not installed')
        config={'id':'logistic','kind':'logistic','C':1.,'class_weight':None}
        fit=[{'raw:word:known':float(i)} for i in range(6)]
        truths=[['Worker故障'] if i<3 else ['硬件故障'] for i in range(6)]
        model=classifier_training.fit_model(fit,truths,config)
        self.assertNotIn('raw:word:validation_only',model[0].get_feature_names_out())
        exported=classifier_training.export_model(model,config,'all_observations')
        test=[{'raw:word:known':2.,'raw:word:validation_only':100.}]
        self.assertEqual(classifier_training.model_predictions(model,test),[portable_classifier.predict(exported,test[0])['label']])

    def test_classifier_is_explicit_in_report_flow(self):
        _,_,_,cases=inputs()
        payload=report_data();payload['basic_info']['kb_id']=None
        model={'schema_version':'label-reranker-v1','kind':'logistic','view':'all_observations',
            'feature_names':[],'classes':['OS故障','Worker故障'],'coefficients':[[],[]],'intercept':[10.,0.],
            'metadata':{'feature_version':feature_vectors.VERSION,'model_id':'explicit-test'}}
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            default=generate_report.label_report(payload,cases,work_dir=Path(tmp)/'k4')
            explicit=generate_report.label_report(payload,cases,work_dir=Path(tmp)/'model',classifier_model=model)
        self.assertIsNone(default['faults'][0]['conclusion']['domain'])
        self.assertTrue(default['faults'][0]['label_matching']['fallback_used'])
        self.assertEqual(explicit['faults'][0]['conclusion']['component'],'OS故障')
        self.assertEqual(explicit['faults'][0]['label_matching']['policy'],'all-feature-classifier-v1')
