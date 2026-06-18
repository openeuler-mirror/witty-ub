#include "kvcache_conn_fault_002_008.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_008> g_kvcacheconnfault("kvcache_conn_fault_002_008");

bool KvcacheConnFault002_008::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 8);
}

std::string KvcacheConnFault002_008::GetName() const
{
    return "错误码8 K_NOT_READY。";
}

std::string KvcacheConnFault002_008::GetRootCauseDesc() const
{
    return "K_NOT_READY(8)表示Client未就绪，通常Init未完成或顺序错误，"
           "属于用户侧问题（08手册:L130）。";
}

RootCause KvcacheConnFault002_008::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_008::GetFixSuggDesc() const
{
    return "检查业务侧Init调用和ConnectOptions配置顺序，确保在Put/"
           "Get前已完成Init（08手册:L248）。";
}

std::string KvcacheConnFault002_008::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L130, L189）：access log中status_code（第8列）为8。";
}

std::string KvcacheConnFault002_008::GetId() const
{
    return "kvcache_conn_fault_002_008";
}
} // namespace diag
