"""测试只有Worker access日志的trace能够被正确处理"""
import sys
sys.path.insert(0, "src/plugins")

from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
from latency.parse.parallel_scanner.process_worker import _serialize_entry
from latency.ENUM.ds_log import TupleField, EntryType
from datetime import datetime


def test_worker_only_trace_extraction():
    """测试_extract_trace_metrics能够处理只有Worker access日志的trace"""
    
    # 构造一个只有Worker access日志的trace
    worker_entry = (
        datetime(2026, 6, 30, 17, 5, 4),  # timestamp
        "DS_POSIX_GET",  # operation
        11714,  # elapsed_us
        "0",  # data_size
        "0741a220-3d66-4bf6-8f0a-e9a708d6ca32",  # object_key
        "084a61aa-c503-4281-b10a-e2aa7e7bc0da",  # trace_id
        "searchctrwirelesskvworker-24-00104",  # pod_ip
        5,  # status_code
        "URMA wait fallback...",  # resp_msg
        EntryType.WORKER_GET.value,  # entry_type
        "model_kvcache_predictor",  # cluster_name
        None,  # src_addr
        None,  # dst_addr
        None,  # inflight_count
        None,  # request_size
        "log-123",  # log_id
    )
    
    entries = {
        "Worker access parse": [worker_entry],
        # 注意：没有"SDK access parse"条目
    }
    
    # 调用_extract_trace_metrics
    metrics = KVCacheLogParseWorker._extract_trace_metrics(
        "084a61aa-c503-4281-b10a-e2aa7e7bc0da",
        entries
    )
    
    # 验证返回值不为None（修复前会返回None）
    assert metrics is not None, "Worker-only trace should not be skipped"
    
    # 验证提取的字段
    assert metrics["tid"] == "084a61aa-c503-4281-b10a-e2aa7e7bc0da"
    assert metrics["op"] == "DS_POSIX_GET"
    assert metrics["op_key"] == "GET"
    assert metrics["total_ms"] == 11.714
    assert metrics["first"][TupleField.OPERATION] == "DS_POSIX_GET"
    assert metrics["first"][TupleField.POD_IP] == "searchctrwirelesskvworker-24-00104"
    
    # 测试_resolve_snapshot对Worker-only的支持
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    snapshot = KVCacheLogParseWorker._resolve_snapshot(entries)
    
    # 验证total_latency从Worker提取
    assert snapshot["total_latency"] == 11.714, f"Expected total_latency=11.714, got {snapshot['total_latency']}"
    
    print("✅ Worker-only trace extraction test passed!")


def test_sdk_worker_mixed_trace():
    """测试同时包含SDK和Worker access日志的trace"""
    
    # 构造SDK entry
    sdk_entry = (
        datetime(2026, 6, 30, 17, 5, 4),  # timestamp
        "DS_KV_CLIENT_GET",  # operation
        15000,  # elapsed_us
        "1024",  # data_size
        "test-key",  # object_key
        "trace-mixed-123",  # trace_id
        "sdk-pod-1",  # pod_ip
        0,  # status_code
        "success",  # resp_msg
        EntryType.SDK_GET.value,  # entry_type
        "cluster-1",  # cluster_name
        None,  # src_addr
        None,  # dst_addr
        None,  # inflight_count
        None,  # request_size
        "log-123",  # log_id
    )
    
    # 构造Worker entry
    worker_entry = (
        datetime(2026, 6, 30, 17, 5, 4),  # timestamp
        "DS_POSIX_GET",  # operation
        8000,  # elapsed_us
        "0",  # data_size
        "test-key",  # object_key
        "trace-mixed-123",  # trace_id
        "worker-pod-1",  # pod_ip
        0,  # status_code
        "",  # resp_msg
        EntryType.WORKER_GET.value,  # entry_type
        "cluster-1",  # cluster_name
        None,  # src_addr
        None,  # dst_addr
        None,  # inflight_count
        None,  # request_size
        "log-123",  # log_id
    )
    
    entries = {
        "SDK access parse": [sdk_entry],
        "Worker access parse": [worker_entry],
    }
    
    # 调用_extract_trace_metrics
    metrics = KVCacheLogParseWorker._extract_trace_metrics(
        "trace-mixed-123",
        entries
    )
    
    # 验证返回值
    assert metrics is not None
    
    # 验证使用SDK entry作为first（优先级）
    assert metrics["op"] == "DS_KV_CLIENT_GET"
    assert metrics["total_ms"] == 15.0
    assert metrics["first"][TupleField.POD_IP] == "sdk-pod-1"
    
    print("✅ SDK-Worker mixed trace test passed!")


def test_no_access_trace_skipped():
    """测试没有access日志的trace会被跳过"""
    
    entries = {
        "Worker urma parse": [],  # 只有URMA等其他类型日志
        # 没有"SDK access parse"或"Worker access parse"
    }
    
    metrics = KVCacheLogParseWorker._extract_trace_metrics(
        "trace-no-access",
        entries
    )
    
    # 验证返回None
    assert metrics is None, "Trace without access logs should be skipped"
    
    print("✅ No access trace skip test passed!")


if __name__ == "__main__":
    test_worker_only_trace_extraction()
    test_sdk_worker_mixed_trace()
    test_no_access_trace_skipped()
    print("\n✅ All tests passed!")