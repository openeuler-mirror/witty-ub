#include "kvcache_conn_fault_020_006.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_006> g_kvcacheconnfault("kvcache_conn_fault_020_006");

bool KvcacheConnFault020_006::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return message.find("[TCP_CONNECT_FAILED]") != std::string::npos;
}

std::string KvcacheConnFault020_006::GetName() const
{
    return "1001/1002 → yuanrong-datasystem进程内：对端Worker不在。";
}

std::string KvcacheConnFault020_006::GetRootCauseDesc() const
{
    return "Worker crash/未拉起/机器故障，属于yuanrong-datasystem进程内问题（08手册:L223）。";
}

RootCause KvcacheConnFault020_006::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_006::GetFixSuggDesc() const
{
    return "检查Worker进程状态（pgrep -af datasystem_worker）；若无进程则由编排拉起；"
           "若反复crash则查Worker crash dump（08手册:L223）。";
}

std::string KvcacheConnFault020_006::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L223）：匹配[TCP_CONNECT_FAILED]且对端Worker不在。";
}

std::string KvcacheConnFault020_006::GetId() const
{
    return "kvcache_conn_fault_020_006";
}
} // namespace diag
