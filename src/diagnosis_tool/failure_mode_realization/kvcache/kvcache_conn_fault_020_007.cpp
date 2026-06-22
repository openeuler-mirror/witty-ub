#include "kvcache_conn_fault_020_007.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_007> g_kvcacheconnfault("kvcache_conn_fault_020_007");

bool KvcacheConnFault020_007::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return message.find("[RPC_RECV_TIMEOUT]") != std::string::npos;
}

std::string KvcacheConnFault020_007::GetName() const
{
    return "1001/1002 → yuanrong-datasystem进程内：RPC接收超时（对端处理慢）。";
}

std::string KvcacheConnFault020_007::GetRootCauseDesc() const
{
    return "对端处理慢导致超时，属于yuanrong-datasystem进程内问题（08手册:L224）。";
}

RootCause KvcacheConnFault020_007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_007::GetFixSuggDesc() const
{
    return "查Worker CPU使用率、锁争用情况；扩oc_rpc_thread_num线程数（08手册:L271）。";
}

std::string KvcacheConnFault020_007::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L224）：匹配[RPC_RECV_TIMEOUT]且ZMQ "
           "fault=0。";
}

std::string KvcacheConnFault020_007::GetId() const
{
    return "kvcache_conn_fault_020_007";
}
} // namespace diag
