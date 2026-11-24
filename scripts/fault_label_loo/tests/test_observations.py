import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
EXPERIMENTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EXPERIMENTS))
import skill_runtime
import raw_observations as raw
import log_message_features as messages

class ObservationBoundaryTests(unittest.TestCase):
    def test_telemetry_ignores_identity(self):
            a = raw.message_features(b'UB_PORT_HEALTH cluster=A valid=1 bad=2 total=4 address=10.0.0.1', 'worker_process')
            b = raw.message_features(b'UB_PORT_HEALTH cluster=B valid=1 bad=2 total=4 address=192.168.1.2', 'worker_process')
            self.assertEqual(a, b)
            self.assertEqual(a['worker_process:ports:bad_share'], .5)
            self.assertNotIn('OS故障', json.dumps(a))

    def test_zero_restart_does_not_become_positive(self):
            result = raw.message_features(b'WORKER_STARTUP is_restart=0 restart=0', 'worker_process')
            self.assertNotIn('worker_process:event:process_restart', result)

    def test_message_words_do_not_match_identities(self):
            a = b'RPC peer dead key=T_site_worker_123 cluster=alpha-kv-ds traceId: 12345678-abcd-abcd-abcd-123456789abc address=10.0.0.1:1234'
            b = b'RPC peer dead key=T_other_client_456 cluster=beta-kv-ds traceId: 87654321-bcde-bcde-bcde-abcdefabcdef address=192.168.1.2:5678'
            self.assertEqual(messages.message_features(a), messages.message_features(b))
            self.assertIn('phrase:peer_dead', messages.message_features(a))



class StructureObservationTests(unittest.TestCase):
    def test_process_host_identity_and_absolute_date_do_not_enter_features(self):
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            for variant, host, pid, date, location in [('A', '10.0.0.1', '123', '2026-01-01', '12'),
                                                      ('B', '192.168.1.2', '456', '2026-11-17', '99')]:
                directory = Path(tmp)/variant
                logs = directory/'data/train'/variant
                logs.mkdir(parents=True)
                content = (f'{date}T00:00:00 | I | urma.cpp:{location} | {host} | {pid}:1 | trace | cluster | ready\n'
                           f'{date}T00:00:10 | E | urma.cpp:{location} | {host} | {pid}:2 | trace | cluster | timeout\n')
                (logs/'kvcache.INFO.log').write_text(content)
                prepared = {'reports': [{'source_id': 'query', 'group': 'train', 'name': variant}]}
                (directory/'prepared.json').write_text(json.dumps(prepared))
                observations = {'prepared_sha256': hashlib.sha256((directory/'prepared.json').read_bytes()).hexdigest(),
                    'reports': {'query': {'features': {}, 'provenance': {'files': [
                        {'file': 'kvcache.INFO.log', 'sha256': hashlib.sha256(content.encode()).hexdigest()}]}}}}
                (directory/'messages.json').write_text(json.dumps(observations))
                subprocess.run([sys.executable, str(EXPERIMENTS/'prepare_log_structure_features.py'),
                                '--prepared', str(directory/'prepared.json'), '--messages', str(directory/'messages.json'),
                                '--data-root', str(directory/'data'), '--out', str(directory/'result.json')],
                               check=True, capture_output=True)
                result = json.loads((directory/'result.json').read_text())
                results.append(result['reports']['query']['features'])
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['raw:structure:worker_process:error_process_fraction'], 1.)
