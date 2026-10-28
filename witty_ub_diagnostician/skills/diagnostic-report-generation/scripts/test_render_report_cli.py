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


if __name__ == "__main__":
    unittest.main()
