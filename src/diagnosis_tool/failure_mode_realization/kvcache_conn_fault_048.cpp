#include "kvcache_conn_fault_048.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault048> g_KvcacheConnFault048("kvcache_conn_fault_048");

KvcacheConnFault048::KvcacheConnFault048() noexcept
{
}

bool KvcacheConnFault048::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L828-L844
    // 来源: 10-customer-fault-scenarios.md L694-L699
    // Case 1: Worker进程不存在
    // 来源: references/kvcache_conn_fault_mode.md L828-L844
    std::string cmdOutput0 = kvcache_conn_utils::RunCommand(
        R"(pgrep -af datasystem_worker 2>/dev/null)");
    bool case0_matched = cmdOutput0.empty();
    // Case 2: dmesg无OOM记录
    // 来源: references/kvcache_conn_fault_mode.md L828-L844
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(dmesg | grep 'OOM killer' 2>/dev/null)");
    bool case1_matched = cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault048::GetName() const
{
    return "Worker进程crash（非OOM）";
}

std::string KvcacheConnFault048::GetRootCauseDesc() const
{
    return "DataSystem进程crash";
}

RootCause KvcacheConnFault048::AnalyzeRootCause()
{
    return RootCause(true, "DataSystem进程crash");
}

std::string KvcacheConnFault048::GetFixSuggDesc() const
{
    return "上报华为+附journalctl/core dump";
}

std::string KvcacheConnFault048::GetValidationMethodDesc() const
{
    return "Worker进程不存在且dmesg无OOM记录";
}

std::string KvcacheConnFault048::GetId() const
{
    return "kvcache_conn_fault_048";
}

} // namespace diag