import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import skill_runtime
from skill_runtime import SCRIPTS
sys.path.insert(0,str(SCRIPTS.parents[1]/'diagnostic-report-generation/scripts'))
import fixed_matching
import default_matching
import generate_report
import render_report
from test_fixed_policy import inputs
from test_render_report_cli import report_data


MODE = 'kvcache_access_022'
WORKER_EXIT = 'Worker故障-进程退出'
WORKER_HANG = 'Worker故障-进程挂死'


def worker_cases():
    query, _, _, _ = inputs()
    return [{'id': case_id, 'source_id': case_id, 'status': 'confirmed',
             'label': 'Worker故障', 'second_level_label': WORKER_EXIT,
             'profile': {**query, 'failure_mode_ids': [MODE]}}
            for case_id in ('worker-a', 'worker-b')]


def worker_report():
    data = report_data()
    data['basic_info']['operation'] = 'GET'
    data['faults'][0]['evidence_traces'] = [{
        'trace_id': 'observed-trace', 'kind': 'error', 'why': '现场故障模式与错误码',
        'status_code': '1004', 'failure_mode_id': MODE,
    }]
    return data


class ReportConsistencyTests(unittest.TestCase):
    def test_second_level_is_filled_with_traceable_case_consensus(self):
        data = worker_report()
        data['faults'][0]['conclusion'].update(first_level_label='硬件故障',
                                               second_level_label='网卡故障-时延高')
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, worker_cases(), work_dir=Path(tmp))
        fault = result['faults'][0]
        self.assertEqual(fault['label_matching']['decision']['label'], 'Worker故障')
        self.assertEqual(fault['conclusion']['type'], WORKER_EXIT)
        self.assertEqual(fault['conclusion']['domain'], '软件')
        self.assertEqual(fault['conclusion']['component'], 'Worker故障')
        self.assertNotIn('first_level_label', fault['conclusion'])
        self.assertNotIn('second_level_label', fault['conclusion'])
        self.assertEqual(fault['label_matching']['fault_type_decision'], {
            'method': 'case_feature_consensus', 'label': WORKER_EXIT,
            'failure_mode_id': MODE, 'supporting_case_ids': ['worker-a', 'worker-b'],
        })
        errors, _ = render_report.validate(result)
        self.assertEqual(errors, [])
        fault['conclusion']['type'] = WORKER_HANG
        errors, _ = render_report.validate(result)
        self.assertTrue(any('fault_type_decision.label' in error for error in errors))

    def test_valid_draft_keeps_its_subtype_and_records_case_suggestion(self):
        data = worker_report()
        data['faults'][0]['conclusion'].update(domain='软件', component='Worker故障',
                                               type=WORKER_HANG)
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, worker_cases(), work_dir=Path(tmp))
        fault = result['faults'][0]
        self.assertEqual(fault['conclusion']['type'], WORKER_HANG)
        selection = fault['label_matching']['fault_type_decision']
        self.assertEqual(selection['method'], 'draft')
        self.assertEqual(selection['case_suggestion']['label'], WORKER_EXIT)

    def test_draft_type_from_another_component_does_not_override_prediction(self):
        data = worker_report()
        conclusion = data['faults'][0]['conclusion']
        conclusion.update(
            domain='软件', component='SDK故障',
            type='SDK故障-进程异常退出',
        )
        del data['faults'][0]['evidence_traces'][0]['failure_mode_id']
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, worker_cases(), work_dir=Path(tmp))

        fault = result['faults'][0]
        self.assertEqual(fault['label_matching']['decision']['label'], 'Worker故障')
        self.assertEqual(fault['conclusion']['domain'], '软件')
        self.assertEqual(fault['conclusion']['component'], 'Worker故障')
        self.assertIsNone(fault['conclusion']['type'])
        self.assertEqual(fault['label_matching']['fault_type_decision']['method'], 'unresolved')

        fault['conclusion']['type'] = WORKER_EXIT
        errors, _ = render_report.validate(result)
        self.assertTrue(any('fault_type_decision.label' in error for error in errors))

    def test_draft_does_not_fill_classification_when_policy_abstains(self):
        data = worker_report()
        data['faults'][0]['conclusion'].update(
            domain='软件', component='Worker故障', type=WORKER_EXIT,
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, [], work_dir=Path(tmp))

        fault = result['faults'][0]
        self.assertIsNone(fault['label_matching']['decision']['label'])
        self.assertEqual(fault['label_matching']['fault_type_decision']['method'], 'unresolved')
        for field in ('domain', 'component', 'type'):
            self.assertIsNone(fault['conclusion'][field])

    def test_second_level_abstains_without_independent_agreeing_mode_evidence(self):
        for variation, reason in (
            ('shared_source', 'insufficient_case_support'),
            ('shared_identity', 'insufficient_case_support'),
            ('contradictory_label', 'conflicting_case_labels'),
            ('unconfirmed', 'insufficient_case_support'),
            ('report_wide_mode_only', 'no_fault_failure_mode'),
        ):
            with self.subTest(variation=variation), tempfile.TemporaryDirectory() as tmp:
                data = worker_report()
                cases = worker_cases()
                if variation == 'shared_source':
                    cases[1]['source_id'] = cases[0]['source_id']
                elif variation == 'shared_identity':
                    for case in cases:
                        case['identity'] = ['kb_id:history']
                elif variation == 'contradictory_label':
                    cases.append({**cases[0], 'id': 'worker-c', 'source_id': 'worker-c',
                                  'second_level_label': WORKER_HANG})
                elif variation == 'unconfirmed':
                    cases[1]['status'] = 'draft'
                else:
                    trace = data['faults'][0]['evidence_traces'][0]
                    data['statistics']['evidence_traces'] = [dict(trace)]
                    del trace['failure_mode_id']
                result = generate_report.label_report(data, cases, work_dir=Path(tmp))
                fault = result['faults'][0]
                self.assertEqual(fault['label_matching']['decision']['label'], 'Worker故障')
                self.assertIsNone(fault['conclusion']['type'])
                self.assertEqual(fault['label_matching']['fault_type_decision']['reason'], reason)

    def test_fault_type_preserves_misoperation_rule_priority(self):
        data = worker_report()
        data['faults'][0]['conclusion'].update(
            domain='软件', component='Worker故障', type=WORKER_EXIT,
        )
        data['faults'][0]['evidence_traces'][0]['status_code'] = '3'
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, worker_cases(), work_dir=Path(tmp))
        fault = result['faults'][0]
        self.assertEqual(fault['conclusion']['domain'], '用户')
        self.assertEqual(fault['conclusion']['component'], '业务故障')
        self.assertEqual(fault['conclusion']['type'], '误操作故障-KVCache使用问题')
        self.assertEqual(fault['label_matching']['fault_type_decision'], {
            'method': 'misoperation_rule', 'label': '误操作故障-KVCache使用问题', 'misoperation_codes': ['3'],
        })

    def test_usage_rule_recalls_only_the_corresponding_catalog_type(self):
        data = worker_report()
        data['faults'][0]['evidence_traces'][0]['status_code'] = '3'
        query, _, _, _ = inputs()
        case = {'label': '业务故障', 'status': 'confirmed',
                'profile': {**query, 'status_codes': ['3']}}
        cases = [
            {**case, 'id': 'usage-case', 'second_level_label': '误操作故障-KVCache使用问题'},
            {**case, 'id': 'legacy-usage-case', 'label': '用户相关故障', 'second_level_label': '使用问题'},
            {**case, 'id': 'other-case', 'second_level_label': '杰夫系统故障'},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, cases, work_dir=Path(tmp))

        matches = result['faults'][0]['knowledge_matches']
        self.assertCountEqual([entry['id'] for entry in matches], ['usage-case', 'legacy-usage-case'])
        self.assertEqual({entry['type'] for entry in matches}, {'误操作故障-KVCache使用问题'})
        self.assertEqual(render_report.validate(result)[0], [])

    def test_second_level_uses_each_faults_own_mode(self):
        data = worker_report()
        secondary = copy.deepcopy(data['faults'][0])
        secondary.update(id='F02', role='secondary')
        del secondary['evidence_traces'][0]['failure_mode_id']
        data['faults'].append(secondary)
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, worker_cases(), work_dir=Path(tmp))
        self.assertEqual([fault['conclusion']['type'] for fault in result['faults']],
                         [WORKER_EXIT, None])

    def test_report_generates_knowledge_cases_per_fault(self):
        query, _, _, _ = inputs()
        data = report_data()
        data["basic_info"]["operation"] = "GET"
        primary = data["faults"][0]
        secondary = copy.deepcopy(primary)
        secondary.update(id="F02", role="secondary")
        data["faults"].append(secondary)
        cases = []
        for fault, case_id, label, code in (
            (primary, "worker-case", "Worker故障", "1004"),
            (secondary, "hardware-case", "硬件故障", "1001"),
        ):
            fault["evidence_traces"] = [{"status_code": code}]
            cases.append({"id": case_id, "label": label, "status": "confirmed",
                          "profile": {**query, "status_codes": [code]}})
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, cases, work_dir=Path(tmp))
        for fault, case in zip(result["faults"], cases):
            self.assertEqual(fault["label_matching"]["decision"]["label"], case["label"])
            self.assertEqual([entry["id"] for entry in fault["knowledge_matches"]], [case["id"]])

    def test_report_omits_history_when_only_operation_matches(self):
        query, _, _, _ = inputs()
        data = report_data()
        data["basic_info"]["operation"] = "GET"
        data["faults"][0]["knowledge_matches"] = [{"id": "UB-CASE-000042", "symptom": "旧案例"}]
        cases = [{"id": "case", "label": "Worker故障", "status": "confirmed", "profile": query}]
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(data, cases, work_dir=Path(tmp))
        self.assertEqual(result["faults"][0]["label_matching"]["decision"]["label"], "Worker故障")
        self.assertEqual(result["faults"][0]["knowledge_matches"], [])

    def test_report_labels_equal_shared_matching_and_ignore_answer_text(self):
        _, _, _, cases = inputs()
        payload = report_data()
        payload['basic_info'].update(operation='GET', kb_id=None)
        expected = default_matching.match_report(payload,cases)['decision']['label']
        payload['faults'][0]['conclusion'].update(first_level_label='OS故障', second_level_label=None,
                                               one_line_conclusion='SDK故障 root cause answer')
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(payload, cases, work_dir=Path(tmp))
        self.assertNotIn('first_level_label', result['faults'][0]['conclusion'])
        self.assertEqual(result['faults'][0]['label_matching']['decision']['label'], expected)
        self.assertEqual(payload['faults'][0]['conclusion']['first_level_label'], 'OS故障')

    def test_report_validation_rejects_manual_change_after_matching(self):
        _, _, _, cases = inputs()
        payload = report_data()
        with tempfile.TemporaryDirectory() as tmp:
            labelled = generate_report.label_report(payload, cases, work_dir=Path(tmp))
        errors, _ = render_report.validate(labelled)
        self.assertEqual(errors, [])
        fault = labelled['faults'][0]
        fault['label_matching']['decision']['label'] = 'OS故障'
        fault['conclusion'].update(domain='硬件', component='硬件故障', type=None)
        errors, _ = render_report.validate(labelled)
        self.assertTrue(any('标签选择策略' in error for error in errors))

    def test_agent_report_command_renders_the_rule_label(self):
        cases = worker_cases()
        payload = worker_report()
        payload['basic_info']['kb_id'] = None
        payload['faults'][0]['evidence_traces'][0]['status_code'] = '3'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'draft.json').write_text(json.dumps(payload))
            (root/'cases.json').write_text(json.dumps({'cases': cases}))
            with contextlib.redirect_stdout(io.StringIO()), patch.object(render_report, 'cleanup_old_reports',
                    return_value=render_report.CleanupOutcome([], {}, None)):
                code = generate_report.main([str(root/'draft.json'), str(root/'report.html'),
                                             '--cases', str(root/'cases.json')])
            self.assertEqual(code, 0)
            self.assertTrue((root/'report.html').is_file())
            source = json.loads((root/'report.json').read_text())
            fault = source['faults'][0]
            self.assertNotIn('first_level_label', fault['conclusion'])
            self.assertEqual(fault['conclusion']['domain'], '用户')
            self.assertEqual(fault['conclusion']['component'], '业务故障')
            self.assertEqual(fault['conclusion']['type'], '误操作故障-KVCache使用问题')
            self.assertEqual(fault['label_matching']['policy'], default_matching.POLICY)
