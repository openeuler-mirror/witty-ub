#include "kvcache_conn_fault_006.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault006> g_kvcacheconnfault("kvcache_conn_fault_006");

bool KvcacheConnFault006::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 5);
}

std::string KvcacheConnFault006::GetName() const
{
    return "错误码5 K_RUNTIME_ERROR。";
}

std::string KvcacheConnFault006::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault006::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault006::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault006::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L131, L191-195）：access log中status_code（第8列）为5；"
           "并通过Worker INFO log按日志串细分。";
}

std::string KvcacheConnFault006::GetId() const
{
    return "kvcache_conn_fault_006";
}
} // namespace diag
