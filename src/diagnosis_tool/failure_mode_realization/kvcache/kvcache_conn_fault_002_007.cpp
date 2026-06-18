#include "kvcache_conn_fault_002_007.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_007> g_kvcacheconnfault("kvcache_conn_fault_002_007");

bool KvcacheConnFault002_007::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 3);
}

std::string KvcacheConnFault002_007::GetName() const
{
    return "错误码3 K_NOT_FOUND。";
}

std::string KvcacheConnFault002_007::GetRootCauseDesc() const
{
    return "K_NOT_FOUND(3)表示对象不存在，属于用户侧问题（08手册:L130）。";
}

RootCause KvcacheConnFault002_007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_007::GetFixSuggDesc() const
{
    return "业务方自查key正确性和Put/Get顺序（08手册:L251）。";
}

std::string KvcacheConnFault002_007::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L130, L189）：access log中status_code（第8列）为3。";
}

std::string KvcacheConnFault002_007::GetId() const
{
    return "kvcache_conn_fault_002_007";
}
} // namespace diag
