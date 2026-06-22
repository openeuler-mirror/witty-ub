#include "kvcache_conn_fault_020_010.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_010> g_kvcacheconnfault("kvcache_conn_fault_020_010");

bool KvcacheConnFault020_010::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[SOCK_CONN_WAIT_TIMEOUT]") != std::string::npos ||
            message.find("[REMOTE_SERVICE_WAIT_TIMEOUT]") != std::string::npos);
}

std::string KvcacheConnFault020_010::GetName() const
{
    return "1001/1002 → 需进一步验证：SOCK/REMOTE握手超时。";
}

std::string KvcacheConnFault020_010::GetRootCauseDesc() const
{
    return "握手延迟超时，需根据对端Worker存活状态区分是OS网络慢还是yuanrong-datasystem问题（08手册:L232）。";
}

RootCause KvcacheConnFault020_010::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_010::GetFixSuggDesc() const
{
    return "根据对端存活状态定界后按对应边界处置（08手册:L232）。";
}

std::string KvcacheConnFault020_010::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L232）：匹配[SOCK_CONN_WAIT_TIMEOUT]或[REMOTE_SERVICE_WAIT_TIMEOUT]。";
}

std::string KvcacheConnFault020_010::GetId() const
{
    return "kvcache_conn_fault_020_010";
}
} // namespace diag
