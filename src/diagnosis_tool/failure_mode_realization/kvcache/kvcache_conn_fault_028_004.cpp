#include "kvcache_conn_fault_028_004.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_004> g_kvcacheconnfault("kvcache_conn_fault_028_004");

bool KvcacheConnFault028_004::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[URMA_RECREATE_JFS_FAILED]") != std::string::npos);
}

std::string KvcacheConnFault028_004::GetName() const
{
    return "URMA_RECREATE_JFS_FAILED连续（JFS重建失败）。";
}

std::string KvcacheConnFault028_004::GetRootCauseDesc() const
{
    return "JFS重建连续失败，可能为UMDK/驱动异常，属于URMA责任（08手册:L300）。";
}

RootCause KvcacheConnFault028_004::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_004::GetFixSuggDesc() const
{
    return "查UMDK/驱动日志；上报URMA团队（08手册:L300）。";
}

std::string KvcacheConnFault028_004::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L300, 10案例:L125）：匹配[URMA_RECREATE_JFS_FAILED]连续出现。";
}

std::string KvcacheConnFault028_004::GetId() const
{
    return "kvcache_conn_fault_028_004";
}
} // namespace diag
