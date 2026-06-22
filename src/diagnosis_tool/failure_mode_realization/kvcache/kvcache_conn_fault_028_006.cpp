#include "kvcache_conn_fault_028_006.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_006> g_kvcacheconnfault("kvcache_conn_fault_028_006");

bool KvcacheConnFault028_006::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[URMA_POLL_ERROR]") != std::string::npos);
}

std::string KvcacheConnFault028_006::GetName() const
{
    return "URMA_POLL_ERROR（驱动/硬件）。";
}

std::string KvcacheConnFault028_006::GetRootCauseDesc() const
{
    return "UB驱动/硬件报告Poll错误，属于URMA责任（08手册:L302）。";
}

RootCause KvcacheConnFault028_006::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_006::GetFixSuggDesc() const
{
    return "grep UMDK日志；检查dmesg中UB相关错误（08手册:L302）。";
}

std::string KvcacheConnFault028_006::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L302, 10案例:L128）：匹配[URMA_POLL_ERROR]。";
}

std::string KvcacheConnFault028_006::GetId() const
{
    return "kvcache_conn_fault_028_006";
}
} // namespace diag
