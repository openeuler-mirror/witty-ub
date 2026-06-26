#include "kvcache_conn_fault_007.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault007> g_kvcacheconnfault("kvcache_conn_fault_007");

bool KvcacheConnFault007::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 6);
}

std::string KvcacheConnFault007::GetName() const
{
    return "错误码6 K_OUT_OF_MEMORY (OS)。";
}

std::string KvcacheConnFault007::GetRootCauseDesc() const
{
    return "内存不足（OOM），属于OS层问题（08手册:L132）。";
}

RootCause KvcacheConnFault007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault007::GetFixSuggDesc() const
{
    return "dmesg | grep -i 'Out of memory'；free -h；扩内存或调整cgroup限制（08手册:L330）。";
}

std::string KvcacheConnFault007::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L132, L196）：access log中status_code（第8列）为6；"
           "或dmesg中Out of memory。";
}

std::string KvcacheConnFault007::GetId() const
{
    return "kvcache_conn_fault_007";
}
} // namespace diag
