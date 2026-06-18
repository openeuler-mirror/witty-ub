#include "kvcache_conn_fault_002_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_002> g_kvcacheconnfault("kvcache_conn_fault_002_002");

bool KvcacheConnFault002_002::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("ConnectOptions was not configured") != std::string::npos);
}

std::string KvcacheConnFault002_002::GetName() const
{
    return "respMsg未配置Init故障。";
}

std::string KvcacheConnFault002_002::GetRootCauseDesc() const
{
    return "未配置Init就发起调用，属于用户侧问题（08手册:L248）。";
}

RootCause KvcacheConnFault002_002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_002::GetFixSuggDesc() const
{
    return "检查业务侧Init调用是否正确配置ConnectOptions（08手册:L248）。";
}

std::string KvcacheConnFault002_002::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L248）：匹配ConnectOptions "
           "was not configured。";
}

std::string KvcacheConnFault002_002::GetId() const
{
    return "kvcache_conn_fault_002_002";
}
} // namespace diag
