#include "kvcache_conn_fault_012.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault012> g_kvcacheconnfault("kvcache_conn_fault_012");

bool KvcacheConnFault012::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 19 || statusCode == 23 || statusCode == 29 || statusCode == 31 || statusCode == 32);
}

std::string KvcacheConnFault012::GetName() const
{
    return "yuanrong-datasystem进程内故障（19/23/29/31/32）。";
}

std::string KvcacheConnFault012::GetRootCauseDesc() const
{
    return "向下级匹配，需要根据证据进一步定界（08手册:L256-278）。";
}

RootCause KvcacheConnFault012::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault012::GetFixSuggDesc() const
{
    return "向下级匹配（08手册:L256-278）。";
}

std::string KvcacheConnFault012::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L133-136, L197）：access log中status_code（第8列）为19/"
           "23/29/31/32。";
}

std::string KvcacheConnFault012::GetId() const
{
    return "kvcache_conn_fault_012";
}
} // namespace diag
