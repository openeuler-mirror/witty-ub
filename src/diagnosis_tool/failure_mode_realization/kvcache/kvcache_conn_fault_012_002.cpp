#include "kvcache_conn_fault_012_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault012_002> g_kvcacheconnfault("kvcache_conn_fault_012_002");

bool KvcacheConnFault012_002::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("zmq_gateway_recreate_total") != std::string::npos ||
            message.find("zmq_event_disconnect_total") != std::string::npos ||
            message.find("zmq_event_handshake_failure_total") != std::string::npos);
}

std::string KvcacheConnFault012_002::GetName() const
{
    return "ZMQ相关问题（重建/断开/握手）。";
}

std::string KvcacheConnFault012_002::GetRootCauseDesc() const
{
    return "分为两种情况（08手册:L272）：低频出现SDK自重连可忽略；"
           "高频出现转OS查网络；握手失败查TLS/认证配置。";
}

RootCause KvcacheConnFault012_002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_002::GetFixSuggDesc() const
{
    return "低频可忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/"
           "认证配置（08手册:L272）。";
}

std::string KvcacheConnFault012_002::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L272）：匹配zmq_gateway_recreate_total "
           "/ zmq_event_disconnect_total / zmq_event_handshake_failure_total增多。";
}

std::string KvcacheConnFault012_002::GetId() const
{
    return "kvcache_conn_fault_012_002";
}
} // namespace diag
