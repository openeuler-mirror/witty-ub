#include "kvcache_conn_fault_020_004.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_004> g_kvcacheconnfault("kvcache_conn_fault_020_004");

bool KvcacheConnFault020_004::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[ZMQ_SEND_FAILURE_TOTAL]") != std::string::npos ||
            message.find("[ZMQ_RECEIVE_FAILURE_TOTAL]") != std::string::npos);
}

std::string KvcacheConnFault020_004::GetName() const
{
    return "1001/1002 → OS侧ZMQ发送/接收失败。";
}

std::string KvcacheConnFault020_004::GetRootCauseDesc() const
{
    return "ZMQ系统调用层硬失败，按errno对应OS问题（08手册:L338）。";
}

RootCause KvcacheConnFault020_004::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_004::GetFixSuggDesc() const
{
    return "按zmq_last_error_number对应的OS errno进行排查：检查端口/路由/"
           "防火墙/资源限制（08手册:L338）。";
}

std::string KvcacheConnFault020_004::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L211, L338）：匹配[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]。";
}

std::string KvcacheConnFault020_004::GetId() const
{
    return "kvcache_conn_fault_020_004";
}
} // namespace diag
