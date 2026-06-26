#include "kvcache_conn_fault_010.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault010> g_kvcacheconnfault("kvcache_conn_fault_010");

bool KvcacheConnFault010::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 18);
}

std::string KvcacheConnFault010::GetName() const
{
    return "错误码18 K_FILE_LIMIT_REACHED (OS)。";
}

std::string KvcacheConnFault010::GetRootCauseDesc() const
{
    return "文件描述符耗尽，属于OS层问题（08手册:L132）。";
}

RootCause KvcacheConnFault010::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault010::GetFixSuggDesc() const
{
    return "ls /proc/<pid>/fd | wc -l 对比 ulimit -n；调大ulimit -n（08手册:L333）。";
}

std::string KvcacheConnFault010::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L132, L196）：access log中status_code（第8列）为18。";
}

std::string KvcacheConnFault010::GetId() const
{
    return "kvcache_conn_fault_010";
}
} // namespace diag
