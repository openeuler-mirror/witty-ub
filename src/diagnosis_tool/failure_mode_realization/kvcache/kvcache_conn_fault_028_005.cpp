#include "kvcache_conn_fault_028_005.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_005> g_kvcacheconnfault("kvcache_conn_fault_028_005");

bool KvcacheConnFault028_005::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("fallback to TCP payload") != std::string::npos);
}

std::string KvcacheConnFault028_005::GetName() const
{
    return "fallback to TCP payload（URMA降级TCP）。";
}

std::string KvcacheConnFault028_005::GetRootCauseDesc() const
{
    return "URMA已降级到TCP（功能正常但性能退化），属于URMA问题引起的时延/"
           "性能降级（08手册:L306）。";
}

RootCause KvcacheConnFault028_005::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_005::GetFixSuggDesc() const
{
    return "检查UB端口状态（ifconfig ub0 up）；修UMDK（08手册:L587）。";
}

std::string KvcacheConnFault028_005::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L301, L624）：匹配fallback "
           "to TCP payload。";
}

std::string KvcacheConnFault028_005::GetId() const
{
    return "kvcache_conn_fault_028_005";
}
} // namespace diag
