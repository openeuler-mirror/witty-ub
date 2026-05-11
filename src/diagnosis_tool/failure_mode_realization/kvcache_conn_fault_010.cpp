#include "kvcache_conn_fault_010.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault010> g_KvcacheConnFault010("kvcache_conn_fault_010");

KvcacheConnFault010::KvcacheConnFault010() noexcept
{
}

bool KvcacheConnFault010::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L215-L229
    // 来源: 08-fault-triage-consolidated.md L196-L198
    // Case 1: ZMQ相关指标上升
    // 来源: references/kvcache_conn_fault_mode.md L215-L229
    std::string metricsOut0 = kvcache_conn_utils::RunCommand(
        R"(grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = kvcache_conn_utils::HasMetricsIncreased(metricsOut0, "zmq_gateway_recreate_total") || kvcache_conn_utils::HasMetricsIncreased(metricsOut0, "zmq_event_disconnect_total") || kvcache_conn_utils::HasMetricsIncreased(metricsOut0, "zmq_event_handshake_failure_total");
    // Case 2: 对端Worker仍活
    // 来源: references/kvcache_conn_fault_mode.md L215-L229
    bool case1_matched = kvcache_conn_utils::ProcessExists("datasystem_worker");
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault010::GetName() const
{
    return "ZMQ相关问题（重建/断开/握手）";
}

std::string KvcacheConnFault010::GetRootCauseDesc() const
{
    return "ZMQ连接重建/断开/握手失败。低频忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置";
}

RootCause KvcacheConnFault010::AnalyzeRootCause()
{
    return RootCause(true, "ZMQ连接重建/断开/握手失败。低频忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置");
}

std::string KvcacheConnFault010::GetFixSuggDesc() const
{
    return "低频忽略；高频查OS网络；握手失败查TLS/认证配置";
}

std::string KvcacheConnFault010::GetValidationMethodDesc() const
{
    return "INFO log含zmq_gateway_recreate_total或zmq_event_disconnect_total或zmq_event_handshake_failure_total上升，且对端Worker仍活";
}

std::string KvcacheConnFault010::GetId() const
{
    return "kvcache_conn_fault_010";
}

} // namespace diag