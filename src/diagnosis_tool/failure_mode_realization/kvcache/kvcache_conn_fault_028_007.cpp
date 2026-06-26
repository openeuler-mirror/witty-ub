#include "kvcache_conn_fault_028_007.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_007> g_kvcacheconnfault("kvcache_conn_fault_028_007");

bool KvcacheConnFault028_007::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[URMA_WAIT_TIMEOUT]") != std::string::npos);
}

std::string KvcacheConnFault028_007::GetName() const
{
    return "URMA_WAIT_TIMEOUT（等待CQE超时, code=1010）。";
}

std::string KvcacheConnFault028_007::GetRootCauseDesc() const
{
    return "CQE等待超时，可能是链路抖动或对端重启触发；单独出现则由SDK白名单重试自愈（08手册:L303）。";
}

RootCause KvcacheConnFault028_007::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_007::GetFixSuggDesc() const
{
    return "若伴instanceId变化则按kvcache_conn_fault_028_001处理；若单独出现则由SDK白名单重试自愈（08手册:L303）。";
}

std::string KvcacheConnFault028_007::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L303）：匹配[URMA_WAIT_TIMEOUT]。";
}

std::string KvcacheConnFault028_007::GetId() const
{
    return "kvcache_conn_fault_028_007";
}
} // namespace diag
