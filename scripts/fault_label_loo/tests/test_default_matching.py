import contextlib
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import skill_runtime
from skill_runtime import SCRIPTS
sys.path.insert(0,str(SCRIPTS.parents[1]/'diagnostic-report-generation/scripts'))
import default_matching as engine
import cosine_matching
import generate_report
import match_cases
import mined_log_features_v2 as extraction
import render_report
from test_fixed_policy import inputs
from test_render_report_cli import report_data

SIGNAL='client_sdk|access_recorder.cpp|general|totalus|us|mean'
KEY='mined2:numeric_units:'+SIGNAL


def fixtures():
    profile,structured,raw,_=inputs()
    context=engine.unknown_context();context['provenance']['source']='log_message_columns'
    context['families']['numeric_units']={SIGNAL:1.}
    classes=list(engine.feature_vectors.LABELS)
    model={'schema_version':'label-reranker-v1','kind':'logistic','view':'numeric_units',
        'feature_names':[KEY],'classes':classes,'coefficients':[[2.] if x=='硬件故障' else [0.] for x in classes],
        'intercept':[0.]*5,'metadata':{'feature_version':extraction.VERSION,'model_id':'test-numeric'}}
    bank={'schema_version':cosine_matching.VERSION,'feature_version':extraction.VERSION,'sources':[
        {'source_id':'history','identity':[],'vector':{KEY:1.,'query:legacy:operation:GET':1.}}],
        'cases':[{'id':'h1','source_id':'history','label':'Worker故障'}]}
    return profile,structured,raw,context,model,bank


class DefaultPolicyTests(unittest.TestCase):
    def test_external_fault_vectors_from_same_source_do_not_overwrite_each_other(self):
        bank={'schema_version':cosine_matching.VERSION,'sources':[],'cases':[]}
        cases=[{'id':'a','source_id':'shared','label':'Worker故障','all_context_vector':{'x':1.}},
               {'id':'b','source_id':'shared','label':'硬件故障','all_context_vector':{'y':1.}}]
        rows,coverage=cosine_matching.rank({'x':1.},bank,cases)
        self.assertEqual([r['score_norm'] for r in rows],[1.,0.])
        self.assertEqual(coverage['reference_sources'],1)

    def test_cosine_support_cases_are_confined_to_the_actual_decision_window(self):
        rows=[{'case_id':str(i),'first_level_label':label,'score_norm':score} for i,(label,score) in enumerate(
            [('Worker故障',.6),('硬件故障',.59),('Worker故障',.58),('硬件故障',.57),('Worker故障',.56)])]
        decision=cosine_matching.decide(rows)
        self.assertEqual(decision['supporting_case_ids'],['0','2'])
        rows[0]['score_norm']=.9
        decision=cosine_matching.decide(rows)
        self.assertEqual(decision['supporting_case_ids'],['0'])

    def test_primary_and_cosine_reference_are_both_computed(self):
        q,s,r,c,model,bank=fixtures()
        result=engine.match(q,None,s,r,c,model=model,references=bank)
        self.assertEqual(result['decision']['label'],'硬件故障')
        self.assertEqual(result['retrieval_decision']['label'],'Worker故障')
        self.assertEqual(result['decision']['method'],'numeric_units_classifier')
        self.assertFalse(result['fallback_used'])
        self.assertTrue(result['disagreement'])

    def test_missing_numeric_unknown_numeric_and_broken_model_use_cosine(self):
        q,s,r,c,model,bank=fixtures()
        for context,override,reason in ((engine.unknown_context(),model,'numeric_observations_unavailable'),
             ({**c,'families':{**c['families'],'numeric_units':{'never_seen':1.}}},model,'numeric_features_unknown_to_model'),
             (c,{},'numeric_model_unavailable')):
            with self.subTest(reason=reason):
                result=engine.match(q,None,s,r,context,model=override,references=bank)
                self.assertEqual(result['decision']['label'],'Worker故障')
                self.assertEqual(result['decision']['method'],'all_feature_cosine_k4')
                self.assertIn(reason,result['decision']['fallback_reason'])

    def test_query_source_is_excluded_and_empty_reference_does_not_disable_primary(self):
        q,s,r,c,model,bank=fixtures()
        bank['sources'][0]['identity']=['kb_id:self']
        result=engine.match(q,None,s,r,c,model=model,references=bank,query_identities=['kb_id:self'])
        self.assertEqual(result['decision']['label'],'硬件故障')
        self.assertEqual(result['candidates'],[])
        self.assertIn('history',result['excluded_source_ids'])

    def test_multifault_keeps_report_prediction_and_uses_fault_cosine_fallback(self):
        q,s,r,c,model,bank=fixtures();data=report_data()
        second=copy.deepcopy(data['faults'][0]);second.update(id='F02',role='secondary');data['faults'].append(second)
        def assets(kind,*args):return model if kind=='numeric_classifier' else bank
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,'observe',return_value=(q,s,r,c)),patch.object(engine,'asset',side_effect=assets):
            result=generate_report.label_report(data,work_dir=Path(tmp))
        self.assertEqual(result['label_matching']['decision']['label'],'硬件故障')
        for fault in result['faults']:
            self.assertEqual(fault['conclusion']['first_level_label'],'Worker故障')
            self.assertEqual(fault['label_matching']['decision']['method'],'all_feature_cosine_k4')
            self.assertIn('multiple_faults',fault['label_matching']['decision']['fallback_reason'])

    def test_normal_html_command_uses_default_without_model_flag(self):
        q,s,r,c,model,bank=fixtures();data=report_data()
        def assets(kind,*args):return model if kind=='numeric_classifier' else bank
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,'observe',return_value=(q,s,r,c)),patch.object(engine,'asset',side_effect=assets):
            root=Path(tmp);(root/'draft.json').write_text(json.dumps(data))
            with contextlib.redirect_stdout(io.StringIO()),patch.object(render_report,'cleanup_old_reports',return_value=render_report.CleanupOutcome([],{},None)):
                code=generate_report.main([str(root/'draft.json'),str(root/'report.html')])
            self.assertEqual(code,0)
            result=json.loads((root/'report.json').read_text());html=(root/'report.html').read_text()
            self.assertEqual(result['faults'][0]['conclusion']['first_level_label'],'硬件故障')
            self.assertEqual(result['label_matching']['retrieval_decision']['label'],'Worker故障')
            self.assertIn('新增数值特征分类器',html)
            self.assertIn('历史案例参照：Worker故障',html)
            self.assertIn('预测与案例投票不一致',html)
            self.assertTrue(result['label_matching']['disagreement'])

    def test_http_matching_uses_numeric_sidecar_and_same_fallback(self):
        q,s,r,c,model,bank=fixtures()
        response={'matches':[{'case':{'id':'history','first_level_label':'Worker故障',**q,'structured':s}}],'total':1}
        def assets(kind,*args):return model if kind=='numeric_classifier' else bank
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,'asset',side_effect=assets),patch.object(match_cases,'_search_all',return_value=response):
            root=Path(tmp)
            for name,value in (('query.json',q),('query.structured.json',s),('query.raw.json',r),('query.mined.json',c)):
                (root/name).write_text(json.dumps(value))
            with contextlib.redirect_stdout(io.StringIO()):
                code=match_cases.main([str(root/'query.json'),'--json',str(root/'result.json')])
            self.assertEqual(code,0);result=json.loads((root/'result.json').read_text())
            self.assertEqual(result['decision']['method'],'numeric_units_classifier')
            self.assertEqual(result['decision']['label'],'硬件故障')
            self.assertEqual(result['retrieval_decision']['label'],'Worker故障')

    def test_portable_normal_command_uses_only_skills_and_standard_library(self):
        _,_,_,_,model,bank=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);skills=root/'skills'
            for name in ('case-matching','diagnostic-report-generation'):
                shutil.copytree(SCRIPTS.parents[1]/name,skills/name,ignore=shutil.ignore_patterns('__pycache__'))
            assets=skills/'case-matching/assets/default_label_policy';manifest={'files':{}}
            for kind,value in (('numeric_classifier',model),('cosine_bank',bank)):
                path=assets/(kind+'.json.gz')
                with gzip.open(path,'wt') as stream:json.dump(value,stream)
                manifest['files'][kind]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            (assets/'manifest.json').write_text(json.dumps(manifest))
            (root/'draft.json').write_text(json.dumps(report_data()));logs=root/'logs';logs.mkdir()
            (logs/'ds_client_1.INFO.log').write_text('2026-11-18T00:00:00 | I | access_recorder.cpp:12 | hostA | 1:2 | trace | cluster | totalUs=1000\n')
            command=[sys.executable,'-S',str(skills/'diagnostic-report-generation/scripts/generate_report.py'),
                str(root/'draft.json'),str(root/'labelled.json'),'--labels-only','--log-dir',str(logs)]
            subprocess.run(command,cwd=root,check=True,capture_output=True)
            result=json.loads((root/'labelled.json').read_text())
            self.assertEqual(result['label_matching']['decision']['method'],'numeric_units_classifier')
            self.assertEqual(result['faults'][0]['conclusion']['first_level_label'],'硬件故障')
            self.assertEqual(result['label_matching']['retrieval_decision']['label'],'Worker故障')


if __name__=='__main__':unittest.main()
