#include "kvcache_conn_fault_040.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault040> g_KvcacheConnFault040("kvcache_conn_fault_040");

KvcacheConnFault040::KvcacheConnFault040() noexcept
{
}

bool KvcacheConnFault040::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L732-L743
    // 来源: 10-customer-fault-scenarios.md L513-L514
    // Case 1: Worker进程存在
    // 来源: references/kvcache_conn_fault_mode.md L732-L743
    bool case0_matched = kvcache_conn_utils::ProcessExists("datasystem_worker");
    // Case 2: 端口未LISTEN
    // 来源: references/kvcache_conn_fault_mode.md L732-L743
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(ss -tnlp | grep 31402 2>/dev/null)");
    bool case1_matched = cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault040::GetName() const
{
    return "Worker端口未LISTEN";
}

std::string KvcacheConnFault040::GetRootCauseDesc() const
{
    return "DataSystem问题";
}

RootCause KvcacheConnFault040::AnalyzeRootCause()
{
    return RootCause(true, "DataSystem问题");
}

std::string KvcacheConnFault040::GetFixSuggDesc() const
{
    return "上报华为DS支持";
}

std::string KvcacheConnFault040::GetValidationMethodDesc() const
{
    return "ss -tnlp | grep <worker_port>无结果但Worker进程在";
}

std::string KvcacheConnFault040::GetId() const
{
    return "kvcache_conn_fault_040";
}

} // namespace diag