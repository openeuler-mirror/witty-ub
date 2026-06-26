#include "kvcache_conn_fault_020_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_002> g_kvcacheconnfault("kvcache_conn_fault_020_002");

bool KvcacheConnFault020_002::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[TCP_CONNECT_RESET]") != std::string::npos ||
            message.find("[TCP_NETWORK_UNREACHABLE]") != std::string::npos);
}

std::string KvcacheConnFault020_002::GetName() const
{
    return "1001/1002 → OS侧TCP连接重置/网络不可达。";
}

std::string KvcacheConnFault020_002::GetRootCauseDesc() const
{
    return "网络闪断或路由不可达，属于OS层（08手册:L209）。";
}

RootCause KvcacheConnFault020_002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_002::GetFixSuggDesc() const
{
    return "dmesg查看系统日志；netstat -s | grep reset查看重置统计（08手册:L337）。";
}

std::string KvcacheConnFault020_002::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L209, L337）：匹配[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]。";
}

std::string KvcacheConnFault020_002::GetId() const
{
    return "kvcache_conn_fault_020_002";
}
} // namespace diag
