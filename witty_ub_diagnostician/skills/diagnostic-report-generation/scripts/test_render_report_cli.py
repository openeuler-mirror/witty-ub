"""CLI regression tests for validation-only and rendering separation."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import render_report


def report_data() -> dict:
    return {
        "report": {
            "title": "校验模式回归",
            "report_id": "validation-test",
            "generated_at": "2026-10-27 18:00:00",
        },
        "basic_info": {
            "kb_id": "validation-kb",
            "kb_name": "校验资产库",
            "total_trace_cnt": 1,
        },
        "statistics": {},
        "workflow": {"steps": []},
        "faults": [
            {
                "id": "F01",
                "title": "合成故障",
                "role": "primary",
                "status": "suspected",
                "severity": "P3",
                "category": "latency",
                "conclusion": {
                    "first_level_label": None,
                    "second_level_label": None,
                    "one_line_conclusion": "用于验证 JSON 契约",
                },
            }
        ],
    }


class RenderReportCliTest(unittest.TestCase):
    def test_time_hotspot_accepts_normalized_heights_in_both_modes(self):
        for mode in ("fault", "latency"):
            with self.subTest(mode=mode):
                data = report_data()
                data["statistics"] = {
                    "heatmap_metric": mode,
                    "time_heatmap": [
                        {"time": "11:01", "pct": 0, "level": 0},
                        {"time": "11:04", "pct": 18.5, "level": 1},
                        {"time": "11:06", "pct": 100, "level": 3, "spike": True},
                    ],
                }
                if mode == "latency":
                    for slot in data["statistics"]["time_heatmap"]:
                        slot["lat_ms"] = slot["pct"] * 20

                errors, _ = render_report.validate(data)
                self.assertEqual(errors, [])
                html = render_report.render_report_html(
                    data, render_report.DEFAULT_TEMPLATE, Path("hotspot-test.json")
                )
                self.assertIn('style="height: 100%;"', html)
                if mode == "latency":
                    self.assertIn('2000<span style="font-size:9px;">ms</span>', html)

    def test_time_hotspot_rejects_out_of_range_and_nonfinite_heights(self):
        for pct in (-1, 100.01, 3010.3, float("nan"), float("inf"),
                    float("-inf"), "NaN", "Infinity", None, "bad"):
            with self.subTest(pct=pct):
                data = report_data()
                data["statistics"]["time_heatmap"] = [{"time": "11:06", "pct": pct}]
                errors, _ = render_report.validate(data)
                self.assertTrue(any(
                    "statistics.time_heatmap[0].pct" in error and "0~100" in error
                    for error in errors
                ), errors)

    def test_invalid_hotspot_height_blocks_validation_and_render_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.json"
            data = report_data()
            data["statistics"]["time_heatmap"] = [{"time": "11:06", "pct": 3010.3}]
            source.write_text(json.dumps(data), encoding="utf-8")
            for options in (["--validate-only"], [str(root / "out.html")]):
                with self.subTest(options=options), \
                        patch("sys.stderr", new_callable=io.StringIO) as stderr, \
                        patch.object(render_report, "render_report_html") as render:
                    result = render_report.main([str(source), *options])
                self.assertEqual(result, 2)
                self.assertIn("statistics.time_heatmap[0].pct", stderr.getvalue())
                render.assert_not_called()
                self.assertEqual(list(root.iterdir()), [source])

    @staticmethod
    def _overview_metric(label: str, mode: str, observed: float = 12.34) -> dict:
        return {
            "label": label,
            "value": "12.340 ms",
            "sub": "1小时桶 / GET / log-1",
            "tone": "warn",
            "source": {
                "endpoint": "/log_parse_result/metrics/latency",
                "request": {
                    "kb_id": "validation-kb",
                    "log_id": "log-1",
                    "operation": "GET",
                    "start_time": "2026-11-08 14:00:00",
                    "end_time": "2026-11-08 15:00:00",
                    "bucket_seconds": 3600,
                    "sample_mode": mode,
                },
                "response_path": "result.metrics[0].total_latency",
                "returned_points": 1,
                "observed_total_latency_ms": observed,
            },
        }

    def test_avg_and_p9999_cards_require_matching_single_bucket_sources(self):
        data = report_data()
        data["faults"][0]["latency"] = {
            "metrics": [
                self._overview_metric("平均时延", "avg"),
                self._overview_metric("P99.99 时延", "p9999"),
            ]
        }

        errors, _ = render_report.validate(data)
        self.assertEqual(errors, [])

        data["faults"][0]["latency"]["metrics"][1]["source"]["request"]["end_time"] = (
            "2026-11-08 16:00:00"
        )
        errors, _ = render_report.validate(data)
        self.assertTrue(any("除 sample_mode 外必须完全一致" in error for error in errors))

    def test_avg_card_without_source_is_rejected(self):
        data = report_data()
        data["faults"][0]["latency"] = {
            "metrics": [{"label": "平均时延", "value": "12.34ms"}]
        }

        errors, _ = render_report.validate(data)
        self.assertTrue(any("metrics/latency 同源请求" in error for error in errors))

    def test_avg_card_value_must_match_frontend_formatter(self):
        data = report_data()
        metric = self._overview_metric("平均时延", "avg")
        metric["value"] = "12.34ms"
        data["faults"][0]["latency"] = {"metrics": [metric]}

        errors, _ = render_report.validate(data)
        self.assertTrue(any("必须按前端格式显示" in error for error in errors))

        render_report.normalize_compat(data)
        errors, _ = render_report.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(metric["value"], "12.340 ms")

    def test_latency_card_uses_frontend_small_value_units(self):
        data = report_data()
        metric = self._overview_metric("P99.99 时延", "p9999", 0.0004)
        data["faults"][0]["latency"] = {"metrics": [metric]}

        render_report.normalize_compat(data)

        self.assertEqual(metric["value"], "0.400 us")
        errors, _ = render_report.validate(data)
        self.assertEqual(errors, [])

    def test_latency_card_uses_javascript_tie_rounding(self):
        data = report_data()
        metric = self._overview_metric("平均时延", "avg", 1.0625)
        data["faults"][0]["latency"] = {"metrics": [metric]}

        render_report.normalize_compat(data)

        self.assertEqual(metric["value"], "1.063 ms")

    def test_confidence_values_are_normalized_to_zero_one_numbers(self):
        data = report_data()
        data["faults"][0]["confidence"] = "high"
        data["faults"][0]["conclusion"]["confidence"] = "高90%"
        data["incident_summary"] = {"confidence": 90}
        data["fault_relations"] = [{"confidence": "高"}]

        render_report.normalize_compat(data)

        self.assertEqual(data["faults"][0]["confidence"], 0.9)
        self.assertEqual(data["faults"][0]["conclusion"]["confidence"], 0.9)
        self.assertEqual(data["incident_summary"]["confidence"], 0.9)
        self.assertEqual(data["fault_relations"][0]["confidence"], 0.9)
        errors, _ = render_report.validate(data)
        self.assertFalse([error for error in errors if "confidence" in error])

    def test_unknown_confidence_text_is_rejected(self):
        data = report_data()
        data["faults"][0]["conclusion"]["confidence"] = "大概90%"

        render_report.normalize_compat(data)
        errors, _ = render_report.validate(data)

        self.assertTrue(any("confidence" in error and "0~1" in error for error in errors))

    def test_rendered_confidence_is_always_a_percentage(self):
        data = report_data()
        data["faults"][0]["confidence"] = 0.9
        data["faults"][0]["conclusion"]["confidence"] = 0.9
        render_report.normalize_compat(data)

        html = render_report.render_report_html(
            data,
            render_report.DEFAULT_TEMPLATE,
            Path("confidence-test.json"),
        )

        self.assertIn('置信度</div><div class="hero-metric-value">90%</div>', html)
        self.assertIn('<span class="chip chip-conf">置信 90%</span>', html)
        self.assertNotIn("置信 high", html)
        self.assertNotIn("高90%", html)

    def test_missing_classification_uses_field_specific_placeholders(self):
        data = report_data()
        data["faults"][0]["conclusion"].update(
            domain=None, component=None, type=None,
        )
        render_report.normalize_compat(data)

        errors, _ = render_report.validate(data)
        self.assertEqual(errors, [])

        html = render_report.render_report_html(
            data,
            render_report.DEFAULT_TEMPLATE,
            Path("missing-fault-location-test.json"),
        )

        for value_class, count in (("hero-metric-value", 1), ("card-value", 2)):
            for label, placeholder in (("故障域", "未知故障"), ("故障组件", "-")):
                with self.subTest(value_class=value_class, label=label):
                    self.assertEqual(
                        html.count(f'{label}</div><div class="{value_class}">{placeholder}</div>'),
                        count,
                    )

    def test_multi_fault_sidecar_and_cards_use_primary_classification(self):
        data = report_data()
        primary = data["faults"][0]
        primary["conclusion"].update(
            domain="软件", component="Worker故障",
            type="Worker故障-进程申请不到CPU/内存/IO等资源",
            affected_scope_pct=0, affected_scope_desc="主故障范围",
        )
        primary["confidence"] = 0.94
        secondary = {
            **primary, "id": "F02", "role": "secondary", "confidence": 0.61,
            "conclusion": {
                "first_level_label": "硬件故障", "second_level_label": "网卡故障-丢包",
                "affected_scope_pct": 18, "affected_scope_desc": "次生故障范围",
            },
        }
        data["faults"].insert(0, secondary)
        impact = "impact_scope_" * 30
        data["incident_summary"] = {
            "primary_fault_id": "F01", "one_line_conclusion": "两个故障",
            "fault_count": 2, "confidence": 0.82, "overall_impact": impact,
        }
        data["fault_relations"] = [{"from": "F01", "to": "F02", "type": "causes", "evidence": "同窗传播"}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "draft.json"
            output = root / "report.html"
            source.write_text(json.dumps(data), encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(render_report.main([str(source), str(output)]), 0)
            html = output.read_text(encoding="utf-8")
            sidecar = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))

        summary = sidecar["incident_summary"]
        self.assertEqual((summary["domain"], summary["component"], summary["type"]),
                         ("软件", "Worker故障", "Worker故障-进程申请不到CPU/内存/IO等资源"))
        self.assertEqual(summary["overall_impact"], impact)
        self.assertEqual(summary["confidence"], 0.82)
        self.assertEqual(sidecar["faults"][0]["conclusion"]["type"], "网卡故障-丢包")
        for fault in sidecar["faults"]:
            self.assertNotIn("first_level_label", fault["conclusion"])
            self.assertNotIn("second_level_label", fault["conclusion"])
        self.assertEqual(html.count(impact), 2)
        self.assertIn('置信度</div><div class="hero-metric-value">82%</div>', html)
        self.assertIn('置信度</div><div class="card-value">82%</div>', html)
        self.assertIn('置信度</div><div class="card-value">94%</div>', html)
        self.assertIn('置信度</div><div class="card-value">61%</div>', html)
        self.assertNotIn('>故障类型</div>', html)
        self.assertNotIn('Worker故障-进程申请不到CPU/内存/IO等资源', html)
        self.assertIn('<span class="chip chip-conf">置信 94%</span>', html)
        self.assertIn('<span class="chip chip-conf">置信 61%</span>', html)
        self.assertIn('<div class="card-value">0%</div>', html)
        self.assertNotIn('>故障标签<', html)

    def test_classification_must_follow_one_taxonomy_branch(self):
        data = report_data()
        data["faults"][0]["conclusion"].update(
            domain="软件", component="URMA故障", type="网卡故障-丢包",
        )
        errors, _ = render_report.validate(data)
        self.assertTrue(any("conclusion.type" in error for error in errors))

    def test_validate_only_does_not_load_template_or_write_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.json"
            source.write_text(json.dumps(report_data()), encoding="utf-8")
            missing_template = root / "missing-template.html"
            stdout = io.StringIO()

            with patch.dict("os.environ", {"WITTY_REPORT_DIR": str(root / "reports")}), \
                    redirect_stdout(stdout):
                result = render_report.main([
                    str(source),
                    "--validate-only",
                    "--template",
                    str(missing_template),
                ])

            self.assertEqual(result, 0)
            self.assertIn("JSON 校验通过（未生成 HTML）", stdout.getvalue())
            self.assertEqual(list(root.rglob("*.html")), [])
            self.assertEqual(list((root / "reports").rglob("*.json")), [])

    def test_validate_only_and_render_use_the_same_rejection_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.json"
            invalid = report_data()
            invalid["faults"][0]["severity"] = "critical"
            source.write_text(json.dumps(invalid), encoding="utf-8")

            with patch("sys.stderr", new_callable=io.StringIO) as validation_error:
                validation_result = render_report.main([str(source), "--validate-only"])
            with patch("sys.stderr", new_callable=io.StringIO) as render_error:
                render_result = render_report.main([str(source), str(root / "out.html")])

            self.assertEqual(validation_result, 2)
            self.assertEqual(render_result, 2)
            self.assertIn("severity", validation_error.getvalue())
            self.assertEqual(validation_error.getvalue(), render_error.getvalue())
            self.assertFalse((root / "out.html").exists())

    def test_validate_only_rejects_output_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.json"
            source.write_text(json.dumps(report_data()), encoding="utf-8")

            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                result = render_report.main([
                    str(source), str(root / "out.html"), "--validate-only"
                ])

            self.assertEqual(result, 2)
            self.assertIn("不接受输出 HTML 路径", stderr.getvalue())
            self.assertFalse((root / "out.html").exists())


class TimeHotspotChartTest(unittest.TestCase):
    def test_regular_and_zero_only_series_keep_the_linear_scale(self):
        for values in ([], [0, 0], [0, 100], [10, 20, 50, 100], [90, 100]):
            with self.subTest(values=values):
                stats = {"time_heatmap": [{"pct": v} for v in values]}
                chart = render_report._time_hotspot_chart(stats)
                self.assertIsNone(chart["axis"])
                self.assertEqual([s["height"] for s in chart["slots"]], list(values))
                self.assertFalse(any(s["broken"] for s in chart["slots"]))

    def test_broken_scale_skips_only_an_empty_interval_and_preserves_evidence(self):
        stats = {"time_heatmap": [{"pct": v} for v in [0, 2, 3, 80, 100]]}
        original = json.dumps(stats)
        chart = render_report._time_hotspot_chart(stats)

        self.assertEqual(chart["axis"]["ticks"],
                         [(0, "0%"), (40, "3.6%"), (52, "64%"), (100, "100%")])
        self.assertEqual([s["broken"] for s in chart["slots"]],
                         [False, False, False, True, True])
        heights = [s["height"] for s in chart["slots"]]
        self.assertEqual(heights, sorted(heights))
        self.assertEqual((heights[0], heights[-1]), (0, 100))
        self.assertTrue(all(0 <= h <= 40 or 52 <= h <= 100 for h in heights))
        self.assertAlmostEqual(heights[1] / heights[2], 2 / 3)
        self.assertAlmostEqual((heights[3] - 52) / (heights[4] - 52), 16 / 36)
        self.assertEqual(json.dumps(stats), original)

    def test_small_gap_and_gradual_growth_do_not_trigger_a_break(self):
        for values in ([0.001, 0.01, 1, 2, 5, 10, 20, 50, 100], [1, 4, 16, 64, 100]):
            with self.subTest(values=values):
                chart = render_report._time_hotspot_chart(
                    {"time_heatmap": [{"pct": v} for v in values]}
                )
                self.assertIsNone(chart["axis"])

    def test_latency_axis_uses_actual_milliseconds_and_shows_zero_as_ms(self):
        data = report_data()
        data["statistics"] = {
            "heatmap_metric": "latency",
            "time_heatmap": [
                {"time": f"11:{i:02d}", "pct": value / 10,
                 "lat_ms": value, "level": 3, "spike": i == 4}
                for i, value in enumerate([0, 1, 2, 900, 1000])
            ],
        }
        self.assertEqual(render_report.validate(data)[0], [])
        html = render_report.render_report_html(
            data, render_report.DEFAULT_TEMPLATE, Path("broken-latency.json")
        )
        self.assertIn('class="tchart has-break"', html)
        self.assertEqual(html.count('<svg class="tbreak"'), 3)  # axis + two tall bars
        self.assertIn("省略 2.4 ms～720 ms 区间", html)
        self.assertIn('>1000 ms</span>', html)
        self.assertIn('0<span style="font-size:9px;">ms</span>', html)
        self.assertIn('1000<span style="font-size:9px;">ms</span>', html)

    def test_missing_or_nonfinite_latency_cannot_create_a_broken_axis(self):
        for value in (None, "bad", -1, float("inf"), float("nan")):
            with self.subTest(value=value):
                chart = render_report._time_hotspot_chart({
                    "heatmap_metric": "latency",
                    "time_heatmap": [{"pct": 1, "lat_ms": value},
                                     {"pct": 100, "lat_ms": 1000}],
                })
                self.assertIsNone(chart["axis"])


class CleanupTest(unittest.TestCase):
    """旧报告清理：已确认与已绑案的报告必须留存。"""

    OLD = "report_kb1_20261001_090000"

    def _workspace(self, root: Path):
        reports = root / "reports"
        kb = reports / "kb1"
        kb.mkdir(parents=True)
        (kb / f"{self.OLD}.html").write_text("<html>old</html>", encoding="utf-8")
        (kb / f"{self.OLD}.json").write_text("{}", encoding="utf-8")
        data = report_data()
        data["basic_info"]["kb_id"] = "kb1"
        source = root / "input.json"
        source.write_text(json.dumps(data), encoding="utf-8")
        return reports, kb, source

    def _render(self, reports: Path, source: Path, states) -> tuple[int, str, str]:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"WITTY_REPORT_DIR": str(reports)}), \
                patch.object(render_report, "report_states", states), \
                redirect_stdout(stdout), \
                patch("sys.stderr", new_callable=io.StringIO) as stderr:
            code = render_report.main([str(source)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_unconfirmed_old_report_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            reports, kb, source = self._workspace(Path(temp))
            states = {self.OLD: {"review_status": "unconfirmed", "case_count": 0}}

            code, stdout, _ = self._render(reports, source, lambda slug: states)

            self.assertEqual(code, 0)
            self.assertIn("清理旧报告 1 份", stdout)
            self.assertFalse((kb / f"{self.OLD}.html").exists())
            self.assertFalse((kb / f"{self.OLD}.json").exists())
            self.assertEqual(len(list(kb.glob("*.html"))), 1)

    def test_confirmed_old_report_is_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            reports, kb, source = self._workspace(Path(temp))
            states = {self.OLD: {"review_status": "confirmed", "case_count": 0}}

            code, stdout, _ = self._render(reports, source, lambda slug: states)

            self.assertEqual(code, 0)
            self.assertIn("保留旧报告 1 份", stdout)
            self.assertIn("已确认", stdout)
            self.assertTrue((kb / f"{self.OLD}.html").exists())
            self.assertTrue((kb / f"{self.OLD}.json").exists())
            self.assertEqual(len(list(kb.glob("*.html"))), 2)

    def test_old_report_with_bound_case_is_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            reports, kb, source = self._workspace(Path(temp))
            states = {self.OLD: {"review_status": "unconfirmed", "case_count": 1}}

            code, stdout, _ = self._render(reports, source, lambda slug: states)

            self.assertEqual(code, 0)
            self.assertIn("已绑定确认案例", stdout)
            self.assertTrue((kb / f"{self.OLD}.html").exists())
            self.assertTrue((kb / f"{self.OLD}.json").exists())

    def test_cleanup_is_skipped_when_state_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            reports, kb, source = self._workspace(Path(temp))

            def unavailable(_slug):
                raise render_report.CleanupStateUnavailable("WITTY_API_BASE 未设置")

            code, stdout, stderr = self._render(reports, source, unavailable)

            self.assertEqual(code, 0)
            self.assertIn("保留旧报告 1 份", stdout)
            self.assertIn("未清理旧报告", stderr)
            self.assertTrue((kb / f"{self.OLD}.html").exists())
            self.assertTrue((kb / f"{self.OLD}.json").exists())


if __name__ == "__main__":
    unittest.main()
