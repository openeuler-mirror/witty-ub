#include "kvcache_conn_fault_028.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028> g_kvcacheconnfault("kvcache_conn_fault_028");

bool KvcacheConnFault028::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 1004 || statusCode == 1006 || statusCode == 1008 || statusCode == 1009 || statusCode == 1010);
}

std::string KvcacheConnFault028::GetName() const
{
    return "URMA故障（1004-1010）。";
}

std::string KvcacheConnFault028::GetRootCauseDesc() const
{
    return "向下级匹配（08手册:L281-308）。";
}

RootCause KvcacheConnFault028::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028::GetFixSuggDesc() const
{
    return "向下级匹配（08手册:L281-308）。";
}

std::string KvcacheConnFault028::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L137-138, L199）：access log中status_code（第8列）为1004/"
           "1006/1008/1009/1010；或通过Worker INFO log [URMA_前缀识别。";
}

std::string KvcacheConnFault028::GetId() const
{
    return "kvcache_conn_fault_028";
}
} // namespace diag
