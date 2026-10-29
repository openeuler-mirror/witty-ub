"""CLI regression tests for validation-only and rendering separation."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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
