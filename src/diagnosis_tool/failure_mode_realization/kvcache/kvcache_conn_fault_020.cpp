#include "kvcache_conn_fault_020.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020> g_kvcacheconnfault("kvcache_conn_fault_020");

bool KvcacheConnFault020::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 1001 || statusCode == 1002);
}

std::string KvcacheConnFault020::GetName() const
{
    return "错误码1001 K_RPC_DEADLINE_EXCEEDED / 1002 K_RPC_UNAVAILABLE（桶码）。";
}

std::string KvcacheConnFault020::GetRootCauseDesc() const
{
    return "向下级匹配，必须按日志前缀分流定界（08手册:L202-234）。";
}

RootCause KvcacheConnFault020::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault020::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault020::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L137, L198）：access log中status_code（第8列）为1001或1002，"
           "须按日志前缀分流定界。1002是桶码：crash、OS网络断、"
           "etcd不可用都会给1002（08手册:L140, L202）。";
}

std::string KvcacheConnFault020::GetId() const
{
    return "kvcache_conn_fault_020";
}
} // namespace diag
