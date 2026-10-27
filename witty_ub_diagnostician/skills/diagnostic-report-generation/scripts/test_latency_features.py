"""离线回归：来源映射、分母、跨窗口/跨桶隔离及实际 HTML/侧车输出。"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from latency_features import build_features, main as features_main, validate_features
import render_report


def snapshot(operation="GET", count=4, p50=10.0, p90=30.0,
             start="2026-10-26 12:00:00", end="2026-10-26 12:10:00"):
    key = "urma" if operation == "GET" else "set_client"
    # 测试用合成响应；字段来自 StageStatsItem/GetStageStatsMsg，不请求现场。
    return {
        "request": {"kb_id": "test-kb", "log_id": "test-log", "operation": operation,
                    "start_time": start, "end_time": end, "sample_cap": 1000},
        "response": {"code": 200, "result": {
            "operation": operation, "sample_cnt": count, "truncated": False,
            "note": "异常 + top 慢正常选样",
            "items": [{"key": key, "name": "测试归因桶", "trace_cnt": count,
                       "success_cnt": count // 2, "fail_cnt": count - count // 2,
                       "p50_ms": p50, "p90_ms": p90, "max_ms": p90,
                       "client_p50_ms": 40.0 if count else None,
                       "client_p90_ms": 80.0 if count else None,
                       "metric_name": "主阶段耗时", "action": "调查提示", "note": "证据口径",
                       "top_traces": [{"trace_id": "synthetic-A", "evidence_ms": p90,
                                       "client_ms": 80.0}] if count else []}],
        }},
    }


def features(snap=None, **kwargs):
    result = build_features({"current": snap or snapshot(), **kwargs})
    return next(iter(result["features_by_bucket"].values()))


def trace_snapshot(current, items):
    req = {key: value for key, value in current["request"].items() if key != "sample_cap"}
    req.update(trace_ids=["synthetic-A"], include=["topology", "failure_codes"])
    return {"request": req, "response": {"code": 200, "result": {"total": len(items), "items": items}}}


class LatencyFeaturesTest(unittest.TestCase):
    def test_exact_mapping_and_ratios(self):
        f = features()
        self.assertEqual(f["normal_cnt"], 2)
        self.assertEqual(f["anomalous_cnt"], 2)
        self.assertEqual(f["bucket_share_pct"], 100)
        self.assertEqual(f["anomalous_ratio_pct"], 50)
        self.assertEqual(f["tail_ratio_p90_p50"], 3)
        self.assertEqual(f["distribution"]["client_p90_ms"], 80)
        self.assertEqual(f["source"]["response_path"], "result.items[0]")
        self.assertNotIn("p99_ms", f["distribution"])
        self.assertNotIn("baseline", f)
        self.assertEqual(validate_features(f), [])

    def test_bucket_share_uses_all_classified_samples(self):
        snap = snapshot()
        other = deepcopy(snap["response"]["result"]["items"][0])
        other.update(key="query_meta", trace_cnt=6, success_cnt=3, fail_cnt=3)
        snap["response"]["result"]["items"].append(other)
        snap["response"]["result"]["sample_cnt"] = 10
        result = build_features({"current": snap, "bucket_keys": ["urma"]})
        self.assertEqual(set(result["features_by_bucket"]), {"urma"})
        self.assertEqual(result["features_by_bucket"]["urma"]["bucket_share_pct"], 40)

    def test_zero_population_and_missing_measurements(self):
        f = features(snapshot(count=0, p50=None, p90=None))
        self.assertIsNone(f["bucket_share_pct"])
        self.assertIsNone(f["anomalous_ratio_pct"])
        self.assertIsNone(f["tail_ratio_p90_p50"])
        self.assertIsNone(f["distribution"]["p90_ms"])
        self.assertEqual(f["top_traces"], [])

    def test_zero_is_not_missing(self):
        f = features(snapshot(p50=0, p90=0))
        self.assertEqual(f["distribution"]["p50_ms"], 0)
        self.assertIsNone(f["tail_ratio_p90_p50"])

    def test_baseline_delta_can_be_negative_and_zero_denominator_is_null(self):
        base = snapshot(p50=20, p90=60, start="2026-10-26 11:00:00", end="2026-10-26 11:10:00")
        f = features(baseline=base)
        self.assertEqual(f["baseline"]["delta_p90_ms"], -30)
        self.assertEqual(f["baseline"]["p90_amplification"], 0.5)
        base["response"]["result"]["items"][0].update(p50_ms=0, p90_ms=0)
        self.assertIsNone(features(baseline=base)["baseline"]["p90_amplification"])

    def test_incomparable_or_overlapping_baseline_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "重叠"):
            features(baseline=snapshot())
        base = snapshot(start="2026-10-26 11:00:00", end="2026-10-26 11:10:00")
        base["request"]["log_id"] = "other-log"
        with self.assertRaisesRegex(ValueError, "log_id"):
            features(baseline=base)
        base["request"]["log_id"] = "test-log"
        base["response"]["result"]["items"][0]["metric_name"] = "Client 总时延"
        with self.assertRaisesRegex(ValueError, "metric_name"):
            features(baseline=base)

    def test_windows_sorted_and_overlap_rejected(self):
        first = snapshot(end="2026-10-26 12:04:00")
        second = snapshot(start="2026-10-26 12:05:00")
        f = features(windows=[second, first])
        self.assertEqual(f["windows"][0]["source"]["request"]["end_time"], "2026-10-26 12:04:00")
        with self.assertRaisesRegex(ValueError, "重叠"):
            features(windows=[first, first])
        outside = snapshot(start="2026-10-26 11:00:00")
        with self.assertRaisesRegex(ValueError, "当前窗口内"):
            features(windows=[outside])

    def test_top_trace_join_and_missing_lookup_are_explicit(self):
        current = snapshot()
        rows = [{"trace_id": "synthetic-A", "operation": "GET", "host": "host-A",
                 "pod_ips": ["10.0.0.1"], "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2",
                 "is_anomalous": True, "failure_codes": [{"code": "1008", "cnt": 2}]},
                {"trace_id": "unrelated", "operation": "GET", "host": "host-other"}]
        f = features(current, traces=trace_snapshot(current, rows))
        self.assertEqual(f["top_traces"][0]["host"], "host-A")
        self.assertEqual(f["top_traces"][0]["failure_codes"], [{"code": "1008", "cnt": 2}])
        self.assertEqual(f["trace_coverage"]["returned_cnt"], 1)
        self.assertEqual(len(f["top_traces"]), 1)
        missing = features(current, traces=trace_snapshot(current, []))
        self.assertEqual(missing["trace_coverage"]["missing_trace_ids"], ["synthetic-A"])
        self.assertNotIn("failure_codes", missing["top_traces"][0])

    def test_mismatched_trace_operation_and_query_scope_rejected(self):
        current = snapshot()
        traces = trace_snapshot(current, [{"trace_id": "synthetic-A", "operation": "SET"}])
        with self.assertRaisesRegex(ValueError, "操作类型"):
            features(current, traces=traces)
        traces = trace_snapshot(current, [])
        traces["request"]["log_id"] = "other-log"
        with self.assertRaisesRegex(ValueError, "log_id"):
            features(current, traces=traces)

    def test_set_keeps_independent_bucket_keys(self):
        f = features(snapshot(operation="SET"))
        self.assertEqual(f["bucket_key"], "set_client")
        f["bucket_key"] = "urma"
        self.assertTrue(validate_features(f))

    def test_rejects_fabricated_metrics_invalid_counts_and_nonfinite_values(self):
        mutations = [lambda f: f["distribution"].update(p99_ms=100),
                     lambda f: f.update(anomalous_cnt=5),
                     lambda f: f.update(bucket_share_pct=20),
                     lambda f: f["distribution"].update(p90_ms=float("nan")),
                     lambda f: f["distribution"].update(p50_ms=True),
                     lambda f: f.update(timeout_rate_pct=50),
                     lambda f: f["source"]["request"].update(host="unsupported")]
        for mutate in mutations:
            f = features()
            mutate(f)
            with self.subTest(feature=f):
                self.assertTrue(validate_features(f))

    def test_flat_and_fault_contract_validate_new_features(self):
        data = self.report_data()
        self.assertEqual(render_report.validate(data)[0], [])
        flat = {k: v for k, v in data.items() if k != "faults"}
        flat.update(conclusion={}, latency=data["faults"][0]["latency"])
        self.assertEqual(render_report.validate(flat)[0], [])
        flat["latency"]["stages"][0]["features"]["distribution"]["p99_ms"] = 100
        self.assertTrue(render_report.validate(flat)[0])
        self.assertTrue(render_report.validate(data)[0])

    def test_extraction_cli_and_failed_upstream_response(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "snapshots.json", Path(temp) / "features.json"
            source.write_text(json.dumps({"current": snapshot()}), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(features_main([str(source), str(output)]), 0)
            saved = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(saved)["features_by_bucket"]["urma"], features())
            failed = snapshot()
            failed["response"]["code"] = 500
            source.write_text(json.dumps({"current": failed}), encoding="utf-8")
            with redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
                features_main([str(source), str(output)])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), saved)

    @staticmethod
    def report_data():
        return {"report": {"title": "合成数据回归", "report_id": "test", "generated_at": "2026-10-26 12:10:00"},
                "basic_info": {"kb_id": "test-kb", "kb_name": "test", "total_trace_cnt": 4},
                "statistics": {}, "workflow": {"steps": []},
                "faults": [{"id": "F01", "title": "测试故障", "role": "primary",
                            "status": "suspected", "severity": "P2", "category": "latency",
                            "conclusion": {"first_level_label": None, "second_level_label": None},
                            "latency": {"stages": [{"name": "测试阶段", "status": "warn", "features": features()}]}}]}

    def test_actual_render_sidecar_flat_compatibility_and_escaping(self):
        data = self.report_data()
        current = snapshot(p50=0, p90=0)
        traces = trace_snapshot(current, [{"trace_id": "synthetic-A", "operation": "GET", "host": "<script>unsafe</script>",
                                           "failure_codes": []}])
        base = snapshot(start="2026-10-26 11:00:00", end="2026-10-26 11:10:00")
        f = features(current, traces=traces, baseline=base, windows=[snapshot(p50=0, p90=0)])
        data["faults"][0]["latency"]["stages"][0]["features"] = f
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            with patch.dict("os.environ", {"WITTY_REPORT_DIR": temp}), redirect_stdout(io.StringIO()):
                self.assertEqual(render_report.main([str(source)]), 0)
            output = next((Path(temp) / "test-kb").glob("*.html"))
            html = output.read_text(encoding="utf-8")
            self.assertIn("0ms", html)
            self.assertIn("&lt;script&gt;unsafe&lt;/script&gt;", html)
            self.assertIn("相对对照窗口", html)
            self.assertNotIn("<script>unsafe</script>", html)
            sidecar = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["faults"][0]["latency"]["stages"][0]["features"], f)
            flat = {k: v for k, v in data.items() if k != "faults"}
            flat.update(conclusion={}, latency=data["faults"][0]["latency"])
            source.write_text(json.dumps(flat), encoding="utf-8")
            with patch.dict("os.environ", {"WITTY_REPORT_DIR": temp}), redirect_stdout(io.StringIO()):
                self.assertEqual(render_report.main([str(source)]), 0)
            outputs = list((Path(temp) / "test-kb").glob("*.html"))
            # 每个知识库只保留最新报告；第二次渲染会清理上一份。
            self.assertEqual(len(outputs), 1)
            self.assertTrue(all("阶段特征" in p.read_text(encoding="utf-8") for p in outputs))
            # 历史报告没有 features 时仍应渲染。
            del flat["latency"]["stages"][0]["features"]
            flat["latency"]["stages"][0]["p99"] = "20ms"
            source.write_text(json.dumps(flat), encoding="utf-8")
            with patch.dict("os.environ", {"WITTY_REPORT_DIR": temp}), redirect_stdout(io.StringIO()):
                self.assertEqual(render_report.main([str(source)]), 0)


if __name__ == "__main__":
    unittest.main()
