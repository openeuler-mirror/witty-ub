#include "kvcache_conn_fault_006_001.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault006_001> g_kvcacheconnfault("kvcache_conn_fault_006_001");

bool KvcacheConnFault006_001::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("Get mmap entry failed") != std::string::npos);
}

std::string KvcacheConnFault006_001::GetName() const
{
    return "code=5 + Get mmap entry failed (OS)。";
}

std::string KvcacheConnFault006_001::GetRootCauseDesc() const
{
    return "K_RUNTIME_ERROR(5)配合Get mmap entry failed，属于OS层mlock内存限制问题（08手册:L334）。";
}

RootCause KvcacheConnFault006_001::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_001::GetFixSuggDesc() const
{
    return "ulimit -l unlimited；或查看/proc/<pid>/limits确认mlock上限（08手册:L334）。";
}

std::string KvcacheConnFault006_001::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L192, L334）：匹配Get mmap "
           "entry failed。";
}

std::string KvcacheConnFault006_001::GetId() const
{
    return "kvcache_conn_fault_006_001";
}
} // namespace diag
