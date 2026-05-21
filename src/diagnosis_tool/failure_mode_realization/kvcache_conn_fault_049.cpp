#include "kvcache_conn_fault_049.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault049> g_KvcacheConnFault049("kvcache_conn_fault_049");

KvcacheConnFault049::KvcacheConnFault049() noexcept
{
}

bool KvcacheConnFault049::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L846-L857
    // 来源: 10-customer-fault-scenarios.md L698-L699
    // Case 1: Worker进程存在
    // 来源: references/kvcache_conn_fault_mode.md L846-L857
    std::string cmdOutput0 = kvcache_conn_utils::RunCommand(
        R"(pgrep -af datasystem_worker 2>/dev/null)");
    bool case0_matched = !cmdOutput0.empty();
    // Case 2: 端口未LISTEN
    // 来源: references/kvcache_conn_fault_mode.md L846-L857
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(ss -tnlp | grep 31402 2>/dev/null)");
    bool case1_matched = cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault049::GetName() const
{
    return "Worker进程在但端口不LISTEN";
}

std::string KvcacheConnFault049::GetRootCauseDesc() const
{
    return "DataSystem问题";
}

RootCause KvcacheConnFault049::AnalyzeRootCause()
{
    return RootCause(true, "DataSystem问题");
}

std::string KvcacheConnFault049::GetFixSuggDesc() const
{
    return "上报华为DS支持";
}

std::string KvcacheConnFault049::GetValidationMethodDesc() const
{
    return "Worker进程在但ss -tnlp无端口LISTEN";
}

std::string KvcacheConnFault049::GetId() const
{
    return "kvcache_conn_fault_049";
}

} // namespace diag