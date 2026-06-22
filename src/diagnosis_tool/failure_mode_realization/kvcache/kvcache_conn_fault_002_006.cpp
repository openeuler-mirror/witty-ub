#include "kvcache_conn_fault_002_006.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_006> g_kvcacheconnfault("kvcache_conn_fault_002_006");

bool KvcacheConnFault002_006::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 2);
}

std::string KvcacheConnFault002_006::GetName() const
{
    return "错误码2 K_INVALID。";
}

std::string KvcacheConnFault002_006::GetRootCauseDesc() const
{
    return "K_INVALID表示业务参数非法，属于用户侧问题（08手册:L130）。";
}

RootCause KvcacheConnFault002_006::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_006::GetFixSuggDesc() const
{
    return "业务方校验调用参数（08手册:L130, L247）。";
}

std::string KvcacheConnFault002_006::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L130, L189）：access log中status_code（第8列）为2。";
}

std::string KvcacheConnFault002_006::GetId() const
{
    return "kvcache_conn_fault_002_006";
}
} // namespace diag
