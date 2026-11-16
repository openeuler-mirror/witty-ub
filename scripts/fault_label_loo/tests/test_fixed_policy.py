import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENTS))
import skill_runtime
from skill_runtime import SCRIPTS
import baseline_matching
import fixed_matching
import default_matching
import fixed_observations
import match_baseline
import match_cases


def inputs():
    query = {'schema_version': 'legacy-evidence-v1', 'status_codes': ['1004'],
             'failure_mode_ids': [], 'latency_components': [], 'operation': 'GET', 'log_semantic_profile': {}}
    structured = {'schema_version': 'evidence-v1', 'views': {}, 'codes': ['1004'], 'modes': [],
                  'tokens': {}, 'log': {}, 'facts': {}, 'audit': {}, 'provenance': {}}
    cases = [{'id': 'history', 'source_id': 'history-report', 'label': 'Worker故障',
              'profile': query, 'structured': structured}]
    return query, structured, fixed_observations.unknown(), cases


class FixedPolicyTests(unittest.TestCase):
    def test_api_uses_fixed_vote(self):
        query, structured, raw, cases = inputs()
        result = baseline_matching.match(query, cases, structured, raw)
        self.assertEqual(result['decision']['label'], 'Worker故障')
        self.assertEqual(result['retrieval_decision']['label'], 'Worker故障')
        self.assertEqual(result['decision']['method'], 'all_feature_cosine_k4')

    def test_raw_extraction_is_optional_for_rule_voting(self):
        query, structured, raw, cases = inputs()
        self.assertEqual(fixed_matching.match(query, cases, structured, None)['decision']['label'], 'Worker故障')

    def test_empty_candidates_remain_empty_without_model_or_logs(self):
        query, _, _, _ = inputs()
        result = fixed_matching.match(query, [])
        self.assertIsNone(result['decision']['label'])

    def test_user_usage_rule_is_shared_even_without_historical_cases(self):
        query, _, _, _ = inputs()
        query['status_codes'] = ['3']
        result = fixed_matching.match(query, [])
        self.assertEqual(result['decision']['label'], '用户相关故障')
        self.assertEqual(result['decision']['second_level_label'], '使用问题')
        self.assertEqual(result['candidates'], [])

    def test_cli_uses_same_fixed_vote(self):
        query, structured, raw, cases = inputs()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name, value in [('query.json', query), ('query.structured.json', structured),
                                ('query.raw.json', raw), ('cases.json', {'cases': cases})]:
                (directory/name).write_text(json.dumps(value))
            with contextlib.redirect_stdout(io.StringIO()):
                match_baseline.main(['--query', str(directory/'query.json'), '--cases', str(directory/'cases.json'),
                                     '--out', str(directory/'result.json')])
            result = json.loads((directory/'result.json').read_text())
            self.assertEqual(result['policy'], default_matching.POLICY)
            self.assertEqual(result['decision']['label'], 'Worker故障')

    def test_report_export_produces_full_fixed_raw_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); logs = directory/'logs'; logs.mkdir()
            (logs/'kvcache.INFO.log').write_text('2026-11-17T00:00:00 | E | urma.cpp:12 | 10.0.0.1 | 1:2 | trace | cluster | RPC peer dead\n')
            (directory/'report.json').write_text(json.dumps({'basic_info': {'operation': 'GET'}, 'faults': []}))
            with contextlib.redirect_stdout(io.StringIO()):
                match_baseline.main(['--report', str(directory/'report.json'), '--log-dir', str(logs),
                                     '--out', str(directory/'query.json')])
            raw = json.loads((directory/'query.raw.json').read_text())
            self.assertEqual(raw['provenance']['feature_set'], fixed_observations.FEATURE_SET)
            self.assertIn('raw:phrase:peer_dead', raw['features'])
            self.assertIn('raw:component:worker_process:urma.cpp', raw['features'])
            self.assertIn('raw:structure:worker_process:error_host_fraction', raw['features'])

    def test_http_route_uses_same_fixed_decision_without_report_prose(self):
        query, structured, raw, cases = inputs()
        case = {'id': 'history', 'first_level_label': 'Worker故障', **query, 'structured': structured}
        payload = {'matches': [{'case': case}], 'total': 1}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'query.json').write_text(json.dumps({**query, 'structured': structured, 'raw_observations': raw,
                                                         'query_text': 'OS故障 root cause answer', 'log_keywords': ['untrusted answer']}))
            with patch.object(match_cases, '_search_all', return_value=payload), contextlib.redirect_stdout(io.StringIO()):
                match_cases.main([str(directory/'query.json'), '--json', str(directory/'result.json')])
            result = json.loads((directory/'result.json').read_text())
            self.assertEqual(result['decision']['label'], 'Worker故障')
            self.assertEqual(result['decision'], result['label_vote'])
            self.assertEqual(result['policy'], default_matching.POLICY)

    def test_skill_copy_runs_outside_repo_with_standard_library_only(self):
        query, structured, raw, cases = inputs()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            skill = directory/'case-matching'
            shutil.copytree(SCRIPTS.parent, skill, ignore=shutil.ignore_patterns('__pycache__'))
            for name, value in [('query.json', query), ('query.structured.json', structured),
                                ('query.raw.json', raw), ('cases.json', {'cases': cases})]:
                (directory/name).write_text(json.dumps(value))
            command = [sys.executable, '-S', str(skill/'scripts/match_baseline.py'), '--query', str(directory/'query.json'),
                       '--cases', str(directory/'cases.json'), '--out', str(directory/'result.json')]
            subprocess.run(command, cwd=directory, check=True, capture_output=True)
            result = json.loads((directory/'result.json').read_text())
            self.assertEqual(result['decision']['method'], 'all_feature_cosine_k4')
            self.assertEqual(result['policy'], default_matching.POLICY)


if __name__=='__main__':
    unittest.main()
