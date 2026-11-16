from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import skill_runtime
import mined_log_features as features
import mined_log_features_v2 as units


class MinedFeatureTests(unittest.TestCase):
    def test_info_context_and_measured_ratios_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'ds_client_1.INFO.log').write_text('2026-11-17T00:00:00 | I | urma.cpp:12 | 10.0.0.1 | 1:2 | trace | cluster | URMA_WRITE_PHASE totalUs=100 waitUs=90 status=code: [OK]\n')
            result=features.scan(p)
        self.assertTrue(result['families']['all_context'])
        self.assertFalse(result['families']['ew_context'])
        self.assertTrue(any('waitus_over_total' in k for k in result['families']['numeric']))
        self.assertTrue(any('status:' in k and 'OK' in k for k in result['families']['numeric']))

    def test_identity_date_location_and_injection_do_not_become_features(self):
        results=[]
        with tempfile.TemporaryDirectory() as tmp:
            for i,(date,host,pid,cluster) in enumerate((('2026-01-01','10.0.0.1','123','alphaCluster'),('2026-11-17','192.168.1.2','789','betaCluster'))):
                p=Path(tmp)/str(i);p.mkdir()
                (p/'kvcache.INFO.log').write_text(f'{date}T00:00:00 | E | urma.cpp:{i+12} | {host} | {pid}:2 | trace | {cluster} | RPC peer dead cluster={cluster} address={host} key=T_obj_{pid}\n'+
                    f'{date}T00:00:01 | I | test.cpp:1 | {host} | {pid}:2 | trace | {cluster} | scenario=SDK_fault root_cause=client_exit\n')
                x=features.scan(p);results.append(x['families'])
                self.assertEqual(x['provenance']['excluded_test_annotations'],1)
        self.assertEqual(results[0],results[1])

    def test_labels_are_not_accepted_by_extractor(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TypeError):features.scan(Path(tmp),truth=['OS故障'])

    def test_decimal_units_are_preserved_and_converted(self):
        parsed=units.parameters(b'totalCost: 11.519ms waitUs=11016 dataSize=8388608 traceId=1234')
        self.assertAlmostEqual(parsed['totalcost|us'],11519.)
        self.assertEqual(parsed['waitus|us'],11016.)
        self.assertFalse(any('trace' in key for key in parsed))

    def test_status_conditioned_distributions_and_error_relative_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'ds_client_1.INFO.log').write_text('2026-11-17T00:00:00.100 | I | urma.cpp:12 | hostA | 1:2 | trace | cluster | URMA totalUs=100 waitUs=10 status=code: [OK]\n'+
                '2026-11-17T00:00:01.300 | E | urma.cpp:13 | hostA | 1:2 | trace | cluster | URMA totalUs=1000 waitUs=900 status=code: [FAILED]\n')
            result=units.scan(p)
        self.assertTrue(result['families']['contrasts'])
        self.assertTrue(any('|relative_window:4' in key for key in result['families']['temporal']))
