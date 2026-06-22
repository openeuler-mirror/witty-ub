#include "kvcache_conn_fault_002_003.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_003> g_kvcacheconnfault("kvcache_conn_fault_002_003");

bool KvcacheConnFault002_003::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("Client object is already sealed") != std::string::npos);
}

std::string KvcacheConnFault002_003::GetName() const
{
    return "respMsg重复Publish故障。";
}

std::string KvcacheConnFault002_003::GetRootCauseDesc() const
{
    return "buffer重复Publish，属于用户业务逻辑问题（08手册:L249）。";
}

RootCause KvcacheConnFault002_003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_003::GetFixSuggDesc() const
{
    return "检查业务逻辑，确认是否对同一对象重复调用Publish（08手册:L249）。";
}

std::string KvcacheConnFault002_003::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L249）：匹配Client object is "
           "already sealed。";
}

std::string KvcacheConnFault002_003::GetId() const
{
    return "kvcache_conn_fault_002_003";
}
} // namespace diag
