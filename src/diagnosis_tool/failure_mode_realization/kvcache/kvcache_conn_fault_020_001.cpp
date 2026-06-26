#include "kvcache_conn_fault_020_001.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_001> g_kvcacheconnfault("kvcache_conn_fault_020_001");

bool KvcacheConnFault020_001::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return message.find("[TCP_CONNECT_FAILED]") != std::string::npos;
}

std::string KvcacheConnFault020_001::GetName() const
{
    return "1001/1002 → OS侧TCP连接失败（对端活）。";
}

std::string KvcacheConnFault020_001::GetRootCauseDesc() const
{
    return "端口不通/iptables/路由问题，属于OS层（08手册:L208）。";
}

RootCause KvcacheConnFault020_001::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_001::GetFixSuggDesc() const
{
    return "ss -tnlp确认端口LISTEN；iptables -L -n检查规则；开端口/删规则（08手册:L336）。";
}

std::string KvcacheConnFault020_001::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L208, L336）：匹配[TCP_CONNECT_FAILED]且对端Worker活。";
}

std::string KvcacheConnFault020_001::GetId() const
{
    return "kvcache_conn_fault_020_001";
}
} // namespace diag
