#include "kvcache_conn_fault_023.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault023> g_KvcacheConnFault023("kvcache_conn_fault_023");

KvcacheConnFault023::KvcacheConnFault023() noexcept
{
}

bool KvcacheConnFault023::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L431-L455
    // 来源: 08-fault-triage-consolidated.md L214-L217
    // 来源: 10-customer-fault-scenarios.md L148-L156
    // Case 1: [URMA_NEED_CONNECT]
    // 来源: references/kvcache_conn_fault_mode.md L431-L455
    std::string grepOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = !grepOutput0.empty();
    return case0_matched;
}

std::string KvcacheConnFault023::GetName() const
{
    return "URMA会话重连";
}

std::string KvcacheConnFault023::GetRootCauseDesc() const
{
    return "对端Worker重启（instanceId变化）或UB链路不稳（instanceId不变）";
}

RootCause KvcacheConnFault023::AnalyzeRootCause()
{
    return RootCause(true, "对端Worker重启（instanceId变化）或UB链路不稳（instanceId不变）");
}

std::string KvcacheConnFault023::GetFixSuggDesc() const
{
    return "对端重启→等SDK自重连稳定；UB链路不稳→查UB硬件/驱动/端口/交换机抖动";
}

std::string KvcacheConnFault023::GetValidationMethodDesc() const
{
    return "INFO log含[URMA_NEED_CONNECT]或[URMA_RECREATE_JFS]";
}

std::string KvcacheConnFault023::GetId() const
{
    return "kvcache_conn_fault_023";
}

} // namespace diag