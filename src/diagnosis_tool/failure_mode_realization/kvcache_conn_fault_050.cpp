#include "kvcache_conn_fault_050.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault050> g_KvcacheConnFault050("kvcache_conn_fault_050");

KvcacheConnFault050::KvcacheConnFault050() noexcept
{
}

bool KvcacheConnFault050::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L859-L873
    // 来源: 10-customer-fault-scenarios.md L698-L699
    // Case 1: Worker进程存在
    // 来源: references/kvcache_conn_fault_mode.md L859-L873
    std::string cmdOutput0 = kvcache_conn_utils::RunCommand(
        R"(pgrep -af datasystem_worker 2>/dev/null)");
    bool case0_matched = !cmdOutput0.empty();
    // Case 2: 端口LISTEN
    // 来源: references/kvcache_conn_fault_mode.md L859-L873
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(ss -tnlp | grep 31402 2>/dev/null)");
    bool case1_matched = !cmdOutput1.empty();
    // Case 3: 心跳断
    // 来源: references/kvcache_conn_fault_mode.md L859-L873
    std::string grepOutput2 = kvcache_conn_utils::RunCommand(
        R"(grep 'Cannot receive heartbeat from worker' $LOG/datasystem_worker.INFO.log | tail -50 2>/dev/null)");
    bool case2_matched = !grepOutput2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault050::GetName() const
{
    return "Worker进程在、端口LISTEN但心跳断";
}

std::string KvcacheConnFault050::GetRootCauseDesc() const
{
    return "主机/网络（中间网络路径）";
}

RootCause KvcacheConnFault050::AnalyzeRootCause()
{
    return RootCause(true, "主机/网络（中间网络路径）");
}

std::string KvcacheConnFault050::GetFixSuggDesc() const
{
    return "查iptables/路由/MTU";
}

std::string KvcacheConnFault050::GetValidationMethodDesc() const
{
    return "Worker进程在、端口LISTEN但业务心跳断";
}

std::string KvcacheConnFault050::GetId() const
{
    return "kvcache_conn_fault_050";
}

} // namespace diag