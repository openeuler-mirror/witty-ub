import contextlib
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


class ReportConsistencyTests(unittest.TestCase):
    def test_report_labels_equal_shared_matching_and_ignore_answer_text(self):
        _, _, _, cases = inputs()
        payload = report_data()
        payload['basic_info'].update(operation='GET', kb_id=None)
        expected = default_matching.match_report(payload,cases)['decision']['label']
        payload['faults'][0]['conclusion'].update(first_level_label='OS故障', second_level_label=None,
                                               one_line_conclusion='SDK故障 root cause answer')
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_report.label_report(payload, cases, work_dir=Path(tmp))
        self.assertEqual(result['faults'][0]['conclusion']['first_level_label'], expected)
        self.assertEqual(result['faults'][0]['label_matching']['decision']['label'], expected)
        self.assertEqual(payload['faults'][0]['conclusion']['first_level_label'], 'OS故障')

    def test_report_validation_rejects_manual_change_after_matching(self):
        _, _, _, cases = inputs()
        payload = report_data()
        with tempfile.TemporaryDirectory() as tmp:
            labelled = generate_report.label_report(payload, cases, work_dir=Path(tmp))
        errors, _ = render_report.validate(labelled)
        self.assertEqual(errors, [])
        actual = labelled['faults'][0]['conclusion']['first_level_label']
        labelled['faults'][0]['conclusion']['first_level_label'] = 'OS故障' if actual!='OS故障' else 'SDK故障'
        errors, _ = render_report.validate(labelled)
        self.assertTrue(any('标签选择策略' in error for error in errors))

    def test_agent_report_command_renders_the_rule_label(self):
        _, _, _, cases = inputs()
        payload = report_data(); payload['basic_info']['kb_id'] = None
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
            self.assertEqual(fault['conclusion']['first_level_label'], fault['label_matching']['decision']['label'])
            self.assertEqual(fault['label_matching']['policy'], default_matching.POLICY)
