"""离线回归：时间分布计数口径、分页缺失、操作隔离及 HTML/侧车兼容。"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from error_features import build_error, main, validate_error
import render_report


def series(operation="GET", partial=False):
    events = [
        {"start_time": "2026-10-26 12:00:00", "end_time": "2026-10-26 12:01:00",
         "status_code_cnt": {"all": 5, "1004": 3, "1009": 2}},
        {"start_time": "2026-10-26 12:02:00", "end_time": "2026-10-26 12:03:00",
         "status_code_cnt": {"all": 4, "1009": 4}},
        {"start_time": "2026-10-26 12:03:00", "end_time": "2026-10-26 12:04:00",
         "status_code_cnt": {"all": 2, "-1": 2}},
    ]
    pages = []
    for index in range(1 if partial else 2):
        pages.append({"request": {"kb_id": "synthetic-kb", "operation": operation,
            "host": "host-A", "start_time": "2026-10-26 12:00:00", "end_time": "2026-10-26 12:04:00",
            "interval": "minute", "page_num": index + 1, "page_cnt": 2,
            "sort_by": "timestamp", "sort_desc": False},
            "response": {"code": 200, "result": {"total": 3, "err_codes": ["all", "1004", "1009", "-1"],
                                                     "events": events[index * 2:index * 2 + 2]}}})
    return {"pages": pages}


def error_block(**kwargs):
    return build_error({"series": [series(**kwargs)]})


def report_data(error):
    return {"report": {"title": "合成通断分布回归", "report_id": "test", "generated_at": "2026-10-26 12:05:00"},
            "basic_info": {"kb_id": "synthetic-kb", "kb_name": "合成数据", "total_trace_cnt": 10},
            "statistics": {}, "workflow": {},
            "faults": [{"id": "F01", "title": "通断故障", "role": "primary", "status": "confirmed", "severity": "P2",
                        "category": "error", "conclusion": {"first_level_label": None, "second_level_label": None}, "error": error}]}


class ErrorFeaturesTest(unittest.TestCase):
    def test_distribution_and_zero_windows_from_complete_pages(self):
        error = error_block()
        self.assertEqual(validate_error(error), [])
        bd = error["breakdowns"][0]
        self.assertEqual(bd["code_distribution"]["total_count"], 11)
        self.assertEqual([i["code"] for i in bd["code_distribution"]["items"]], ["1009", "1004", "-1"])
        self.assertEqual(bd["code_distribution"]["items"][0]["share_pct"], round(6 / 11 * 100, 6))
        self.assertEqual(bd["timeline"]["windows"][1]["counts"], {"1009": 0, "1004": 0, "-1": 0})
        self.assertTrue(all(w["complete"] for w in bd["timeline"]["windows"]))
        self.assertEqual(bd["source"]["pages"][1]["request"]["page_num"], 2)

    def test_partial_pages_preserve_unknown_and_omit_proportions(self):
        bd = error_block(partial=True)["breakdowns"][0]
        self.assertFalse(bd["coverage"]["complete"])
        self.assertEqual(bd["code_distribution"]["total_count"], 9)
        self.assertTrue(all(i["share_pct"] is None for i in bd["code_distribution"]["items"]))
        self.assertEqual(bd["timeline"]["windows"][1]["counts"]["1009"], None)
        self.assertTrue(bd["timeline"]["windows"][0]["complete"])
        self.assertFalse(bd["timeline"]["windows"][3]["complete"])

    def test_adjacent_bucket_merge_top_n_and_others_conserve_counts(self):
        for partial in (False, True):
            error = build_error({"series": [series(partial=partial)]}, top_n=1, max_windows=2)
            bd = error["breakdowns"][0]
            self.assertEqual(len(bd["timeline"]["windows"]), 2)
            self.assertEqual(bd["timeline"]["interval_seconds"], 120)
            self.assertEqual(bd["code_distribution"]["other_count"], 3 if partial else 5)
            self.assertEqual(validate_error(error), [])
            if partial:
                self.assertFalse(any(w["complete"] for w in bd["timeline"]["windows"]))
                self.assertEqual(bd["timeline"]["windows"][0]["counts"]["1009"], 2)

    def test_fault_code_filter_and_get_set_are_independent(self):
        get = series()
        get["codes"] = ["1004"]
        error = build_error({"series": [get, series("SET")]})
        self.assertEqual([bd["operation"] for bd in error["breakdowns"]], ["GET", "SET"])
        self.assertEqual(error["breakdowns"][0]["code_distribution"]["total_count"], 3)
        self.assertEqual(error["breakdowns"][1]["code_distribution"]["total_count"], 11)
        self.assertEqual(error["breakdowns"][0]["code_filter"], ["1004"])
        with self.assertRaisesRegex(ValueError, "各一套"):
            build_error({"series": [get, series()]})

    def test_empty_success_is_zero_but_does_not_prove_health(self):
        s = series()
        s["pages"] = s["pages"][:1]
        s["pages"][0]["response"]["result"] = {"total": 0, "err_codes": ["all"], "events": []}
        bd = build_error({"series": [s]})["breakdowns"][0]
        self.assertTrue(bd["coverage"]["complete"])
        self.assertEqual(bd["code_distribution"]["items"], [])
        self.assertTrue(all(w["other_count"] == 0 for w in bd["timeline"]["windows"]))

    def test_boundary_clipping_and_no_timezone_conversion(self):
        s = series()
        for page in s["pages"]:
            page["request"]["start_time"] = "2026-10-26 12:00:30"
            page["request"]["end_time"] = "2026-10-26 12:03:30"
        windows = build_error({"series": [s]})["breakdowns"][0]["timeline"]["windows"]
        self.assertEqual(windows[0]["start_time"], "2026-10-26 12:00:30")
        self.assertEqual(windows[-1]["end_time"], "2026-10-26 12:03:30")

    def test_long_range_merge_keeps_all_counts_with_bounded_windows(self):
        s = series()
        for page in s["pages"]:
            page["request"]["end_time"] = "2026-11-26 12:00:00"
        error = build_error({"series": [s]})
        bd = error["breakdowns"][0]
        self.assertLessEqual(len(bd["timeline"]["windows"]), 48)
        self.assertEqual(bd["code_distribution"]["total_count"], 11)
        self.assertEqual(bd["timeline"]["windows"][-1]["end_time"], "2026-11-26 12:00:00")
        self.assertEqual(validate_error(error), [])

    def test_render_empty_zero_and_simplified_fault(self):
        s = series()
        s["pages"] = s["pages"][:1]
        s["pages"][0]["response"]["result"] = {"total": 0, "err_codes": ["all"], "events": []}
        data = report_data(build_error({"series": [s]}))
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "data.json", Path(temp) / "report.html"
            for simplified in (False, True):
                data["faults"][0]["simplified"] = simplified
                source.write_text(json.dumps(data), encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(render_report.main([str(source), str(output)]), 0)
                html = output.read_text(encoding="utf-8")
                if simplified:
                    self.assertNotIn('<h4 class="fa-sub">通断故障分布</h4>', html)
                else:
                    self.assertIn("不能单独证明系统健康", html)
                    self.assertIn('>0</td>', html)

    def test_bad_upstream_or_incompatible_pages_rejected(self):
        mutations = [
            lambda s: s["pages"][0]["response"].update(code=500),
            lambda s: s["pages"][1]["request"].update(operation="SET"),
            lambda s: s["pages"][1]["request"].update(host="host-B"),
            lambda s: s["pages"][1]["request"].update(page_num=1),
            lambda s: s["pages"][1]["request"].update(sort_desc=True),
            lambda s: s["pages"][0]["request"].update(log_id="unsupported"),
            lambda s: s["pages"][1]["response"]["result"].update(total=4),
            lambda s: s["pages"][0]["response"]["result"]["events"][0]["status_code_cnt"].update(all=3),
            lambda s: s["pages"][0]["response"]["result"]["events"][0]["status_code_cnt"].update(all=True),
        ]
        for mutate in mutations:
            s = series()
            mutate(s)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                build_error({"series": [s]})
        s = series()
        s["pages"][1]["response"]["result"]["events"][0] = deepcopy(s["pages"][0]["response"]["result"]["events"][0])
        with self.assertRaisesRegex(ValueError, "重复时间桶"):
            build_error({"series": [s]})

    def test_invalid_report_counts_proportions_and_unknowns_rejected(self):
        mutations = [
            lambda b: b["code_distribution"]["items"][0].update(count=100),
            lambda b: b["code_distribution"]["items"][0].update(share_pct=float("nan")),
            lambda b: b["code_distribution"]["items"][0].update(share_pct=True),
            lambda b: b["timeline"]["windows"][0]["counts"].update({"1009": -1}),
            lambda b: b["timeline"]["windows"][0]["counts"].update({"1009": None}),
            lambda b: b["source"]["pages"][0]["request"].update(operation="SET"),
            lambda b: b.update(unit="failed_request"),
            lambda b: b.update(stages=[]),
        ]
        for mutate in mutations:
            error = error_block()
            mutate(error["breakdowns"][0])
            with self.subTest(mutate=mutate):
                self.assertTrue(validate_error(error))
                self.assertTrue(render_report.validate(report_data(error))[0])
        self.assertTrue(validate_error("bad"))
        self.assertEqual(validate_error(None), [])
        self.assertEqual(validate_error({}), [])

    def test_cli_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "snapshot.json", Path(temp) / "error.json"
            source.write_text(json.dumps({"series": [series()]}), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(source), str(output)]), 0)
            saved = output.read_text(encoding="utf-8")
            source.write_text('{"series": []}', encoding="utf-8")
            with patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(main([str(source), str(output)]), 2)
            self.assertEqual(output.read_text(encoding="utf-8"), saved)

    def test_render_multi_flat_legacy_mixed_sidecar_and_escaping(self):
        error = error_block(partial=True)
        error["conclusion"] = "<script>unsafe</script>"
        data = report_data(error)
        flat = {k: v for k, v in data.items() if k != "faults"}
        flat.update(conclusion={}, error=deepcopy(error))
        multi = deepcopy(data)
        multi["faults"].append({**deepcopy(data["faults"][0]), "id": "F02", "role": "independent", "error": error_block()})
        multi["incident_summary"] = {"one_line_conclusion": "两个合成故障", "fault_count": 2}
        multi["fault_relations"] = [{"from": "F01", "to": "F02", "type": "independent", "evidence": "合成数据"}]
        mixed = deepcopy(data)
        mixed["faults"][0].update(category="mixed", latency={"stages": [{"name": "URMA", "status": "warn", "p99": "—"}]})
        with tempfile.TemporaryDirectory() as temp:
            for index, payload in enumerate((data, flat, multi, mixed)):
                source, output = Path(temp) / "data.json", Path(temp) / f"report{index}.html"
                source.write_text(json.dumps(payload), encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(render_report.main([str(source), str(output)]), 0)
                html = output.read_text(encoding="utf-8")
                self.assertIn("通断故障分布", html)
                self.assertIn("错误码随时间分布", html)
                self.assertIn("分页不完整", html)
                self.assertIn("error-unknown", html)
                self.assertIn("&lt;script&gt;unsafe&lt;/script&gt;", html)
                self.assertNotIn("<script>unsafe</script>", html)
                sidecar = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
                self.assertEqual(sidecar.get("error", sidecar.get("faults", [{}])[0].get("error")), error)
                if payload is mixed:
                    self.assertIn("时延阶段定位", html)
            for payload in (report_data(None), {**flat, "error": None}):
                source.write_text(json.dumps(payload), encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(render_report.main([str(source), str(output)]), 0)
                self.assertNotIn('<h4 class="fa-sub">通断故障分布</h4>', output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
