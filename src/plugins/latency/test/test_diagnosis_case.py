from latency.database.managers.diagnosis_case import DiagnosisCasePGManager as DiagnosisCaseManager
from latency.schemas.diagnosis_case import DiagnosisCaseModel
from latency.schemas.request import SearchDiagnosisCasesRequest


def test_diagnosis_case_extracts_match_signals():
    case = DiagnosisCaseModel(
        kb_id="kb-1",
        fault_type="latency",
        symptom_summary="src to dst P99 latency spikes",
        root_cause="URMA link setup is slow",
        recommendation="Check URMA link path",
        confidence=0.8,
        status_codes=["1004"],
        failure_mode_ids=["FM-URMA-LINK"],
        source_log_ids=["log-1"],
        fingerprint_json={
            "src_ips": ["10.0.0.1"],
            "dst_ips": ["10.0.0.2"],
            "hosts": ["host-a"],
            "pods": ["pod-a"],
            "clusters": ["cluster-a"],
            "latency_components": ["urma_link_latency"],
            "log_keywords": ["connect timeout"],
        },
    )

    signals = DiagnosisCaseManager._signals_for_case(case)
    signal_pairs = {(signal.signal_type, signal.signal_value) for signal in signals}

    assert ("status_code", "1004") in signal_pairs
    assert ("failure_mode_id", "fm-urma-link") in signal_pairs
    assert ("src_ip", "10.0.0.1") in signal_pairs
    assert ("dst_ip", "10.0.0.2") in signal_pairs
    assert ("host", "host-a") in signal_pairs
    assert ("pod", "pod-a") in signal_pairs
    assert ("cluster", "cluster-a") in signal_pairs
    assert ("latency_component", "urma_link_latency") in signal_pairs
    assert ("log_keyword", "connect timeout") in signal_pairs


def test_search_request_extracts_match_signals():
    req = SearchDiagnosisCasesRequest(
        status_codes=["1004"],
        failure_mode_ids=["FM-URMA-LINK"],
        src_ips=["10.0.0.1"],
        latency_components=["urma_link_latency"],
        log_keywords=["Connect Timeout"],
    )

    query_signals = DiagnosisCaseManager._signals_for_search(req)

    assert query_signals[("status_code", "1004")] == 3.0
    assert query_signals[("failure_mode_id", "fm-urma-link")] == 3.0
    assert query_signals[("src_ip", "10.0.0.1")] == 1.5
    assert query_signals[("latency_component", "urma_link_latency")] == 1.5
    assert query_signals[("log_keyword", "connect timeout")] == 1.0
