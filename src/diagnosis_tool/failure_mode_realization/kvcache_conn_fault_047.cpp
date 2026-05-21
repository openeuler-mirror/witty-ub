#include "kvcache_conn_fault_047.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault047> g_KvcacheConnFault047("kvcache_conn_fault_047");

KvcacheConnFault047::KvcacheConnFault047() noexcept
{
}

bool KvcacheConnFault047::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L810-L826
    // 来源: 10-customer-fault-scenarios.md L694-L699
    // Case 1: Worker进程不存在
    // 来源: references/kvcache_conn_fault_mode.md L810-L826
    std::string cmdOutput0 = kvcache_conn_utils::RunCommand(
        R"(pgrep -af datasystem_worker 2>/dev/null)");
    bool case0_matched = cmdOutput0.empty();
    // Case 2: dmesg含OOM killer
    // 来源: references/kvcache_conn_fault_mode.md L810-L826
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(dmesg | grep 'OOM killer' 2>/dev/null)");
    bool case1_matched = !cmdOutput1.empty();
    // Case 3: dmesg含datasystem_worker
    // 来源: references/kvcache_conn_fault_mode.md L810-L826
    std::string cmdOutput2 = kvcache_conn_utils::RunCommand(
        R"(dmesg | grep datasystem_worker 2>/dev/null)");
    bool case2_matched = !cmdOutput2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault047::GetName() const
{
    return "Worker进程被OOM Killer杀掉";
}

std::string KvcacheConnFault047::GetRootCauseDesc() const
{
    return "主机OOM";
}

RootCause KvcacheConnFault047::AnalyzeRootCause()
{
    return RootCause(true, "主机OOM");
}

std::string KvcacheConnFault047::GetFixSuggDesc() const
{
    return "扩内存/调cgroup；补内存后编排拉起";
}

std::string KvcacheConnFault047::GetValidationMethodDesc() const
{
    return "dmesg含OOM killer杀掉datasystem_worker";
}

std::string KvcacheConnFault047::GetId() const
{
    return "kvcache_conn_fault_047";
}

} // namespace diag