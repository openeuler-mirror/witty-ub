from pathlib import Path

from latency.services.diagnostic_report import DiagnosticReportService


def test_document_retains_all_fault_category_pairs_before_case_generation():
    faults = [
        {"id": "F01", "status": "suspected", "conclusion": {
            "first_level_label": "OS故障", "second_level_label": "OS故障-重启",
        }},
        {"id": "F02", "status": "confirmed", "conclusion": {
            "first_level_label": "Worker故障", "second_level_label": "Worker故障-进程退出",
        }},
        {"id": "F03", "status": "suspected", "conclusion": {
            "first_level_label": None, "second_level_label": None,
        }},
        {"id": "F04", "status": "excluded", "conclusion": {
            "first_level_label": "SDK故障", "second_level_label": None,
        }},
    ]
    item = DiagnosticReportService._build_item(
        None, Path("/nonexistent/report_test.html"),
        {"report": {"title": "多类文档"}, "faults": faults},
    )
    assert len(item.classifications) == 3
    assert [(entry.first_level_label, entry.second_level_label) for entry in item.classifications] == [
        ("OS故障", "OS故障-重启"),
        ("Worker故障", "Worker故障-进程退出"),
        (None, None),
    ]
    assert item.case_count == 0


def test_repeated_fault_labels_are_not_silently_lost():
    data = {"faults": [
        {"id": name, "conclusion": {"first_level_label": "OS故障", "second_level_label": None}}
        for name in ("F01", "F02")
    ]}
    item = DiagnosticReportService._build_item(None, Path("/nonexistent/report_test.html"), data)
    assert len(item.classifications) == 2
    assert all(entry.status == "first_only" for entry in item.classifications)
