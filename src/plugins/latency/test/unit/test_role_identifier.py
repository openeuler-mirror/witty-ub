# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""parse.role 容器角色识别单元测试。"""
import polars as pl

from latency.parse.role import LogRole, identify_log_role, role_expr


class TestIdentifyLogRole:
    def test_client_by_pod_name(self):
        assert identify_log_role(pod_name="ds-client-abc") == LogRole.CLIENT.value

    def test_client_by_cluster_name(self):
        assert (
            identify_log_role(pod_name="ds-worker-1", cluster_name="ds-client")
            == LogRole.CLIENT.value
        )

    def test_client_by_operation_message(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1",
                message="0 | DS_KV_CLIENT_GET | 2000 | 4096 | ...",
            )
            == LogRole.CLIENT.value
        )

    def test_meta_worker_by_query_meta(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1",
                message="QueryMeta done, target num 4, success num 3, cost: 6.6ms",
            )
            == LogRole.META_WORKER.value
        )

    def test_meta_worker_by_create_meta(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1",
                message="Processing CreateMetaReq, id=1 src=10.0.0.1:9000, dst=10.0.0.2:9000",
            )
            == LogRole.META_WORKER.value
        )

    def test_meta_worker_by_filename(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1", filename="oc_metadata_manager.cpp",
                message="metadata lookup done",
            )
            == LogRole.META_WORKER.value
        )

    def test_data_worker_by_urma(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-2",
                message="[URMA_ELAPSED_TOTAL] cost 12.5ms src address : 1.2.3.4, "
                "target address : 5.6.7.8",
            )
            == LogRole.DATA_WORKER.value
        )

    def test_data_worker_by_remote_get(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-2",
                message="Remote get request: src=1.1.1.1, dst=2.2.2.2]",
            )
            == LogRole.DATA_WORKER.value
        )

    def test_data_worker_by_pull_object(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-2",
                message="Processing pull object[key1] src=3.3.3.3, dst=4.4.4.4]",
            )
            == LogRole.DATA_WORKER.value
        )

    def test_data_worker_by_log_file(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-2", log_file="worker_urma.log",
                message="urma link established",
            )
            == LogRole.DATA_WORKER.value
        )

    def test_entry_worker_by_posix(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1",
                message="0 | DS_POSIX_GET | 2000 | 4096 | ...",
            )
            == LogRole.ENTRY_WORKER.value
        )

    def test_meta_priority_over_data(self):
        # 元数据查询信号优先于 URMA 数据面信号
        assert (
            identify_log_role(
                pod_name="ds-worker-1",
                message="QueryMeta done cost: 15.5ms, urma transfer ...",
            )
            == LogRole.META_WORKER.value
        )

    def test_unknown(self):
        assert (
            identify_log_role(
                pod_name="ds-worker-1", message="Worker start success"
            )
            == LogRole.UNKNOWN.value
        )

    def test_empty_inputs(self):
        assert identify_log_role() == LogRole.UNKNOWN.value


class TestRoleExpr:
    def _classify(self, **kwargs) -> list[str]:
        row = {
            "log_file": kwargs.get("log_file", "access.log"),
            "pod_name": kwargs.get("pod_name", ""),
            "cluster_name": kwargs.get("cluster_name", ""),
            "filename": kwargs.get("filename", ""),
            "message": kwargs.get("message", ""),
        }
        frame = pl.DataFrame([row])
        return frame.select(role_expr().alias("role"))["role"].to_list()

    def test_matches_python_client(self):
        assert self._classify(pod_name="ds-client-abc") == [LogRole.CLIENT.value]

    def test_matches_python_meta(self):
        assert self._classify(
            message="QueryMeta done, target num 4, success num 3, cost: 6.6ms"
        ) == [LogRole.META_WORKER.value]

    def test_matches_python_data(self):
        assert self._classify(
            message="[URMA_ELAPSED_TOTAL] cost 12.5ms src address : 1.2.3.4, "
            "target address : 5.6.7.8"
        ) == [LogRole.DATA_WORKER.value]

    def test_matches_python_entry(self):
        assert self._classify(
            message="0 | DS_POSIX_GET | 2000 | 4096 | ..."
        ) == [LogRole.ENTRY_WORKER.value]

    def test_unknown(self):
        assert self._classify(message="Worker start success") == [LogRole.UNKNOWN.value]

    def test_consistent_with_python_across_rows(self):
        samples = [
            dict(pod_name="ds-client-abc", message="DS_KV_CLIENT_GET ok"),
            dict(message="QueryMeta done, target num 4"),
            dict(message="[URMA_ELAPSED_TOTAL] cost 12.5ms"),
            dict(message="0 | DS_POSIX_GET | 2000 | 4096"),
            dict(message="Worker start success"),
        ]
        frame = pl.DataFrame(
            [
                {
                    "log_file": "access.log",
                    "pod_name": s.get("pod_name", ""),
                    "cluster_name": "",
                    "filename": "",
                    "message": s.get("message", ""),
                }
                for s in samples
            ]
        )
        got = frame.select(role_expr().alias("role"))["role"].to_list()
        expected = [
            identify_log_role(
                pod_name=s.get("pod_name", ""),
                message=s.get("message", ""),
                log_file="access.log",
            )
            for s in samples
        ]
        assert got == expected
