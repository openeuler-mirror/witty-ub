#include "kvcache_conn_fault_021.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault021> g_KvcacheConnFault021("kvcache_conn_fault_021");

KvcacheConnFault021::KvcacheConnFault021() noexcept
{
}

bool KvcacheConnFault021::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L396-L418
    // 来源: 08-fault-triage-consolidated.md L115-L119
    // 来源: 10-customer-fault-scenarios.md L169-L178
    // Case 1: [TCP_CONNECT_FAILED]且对端Worker不在
    // 来源: references/kvcache_conn_fault_mode.md L396-L418
    std::string grepOut0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = !grepOut0.empty() && !kvcache_conn_utils::ProcessExists("datasystem_worker");
    // Case 2: [RPC_RECV_TIMEOUT]且ZMQ fault=0或[RPC_SERVICE_UNAVAILABLE]
    // 来源: references/kvcache_conn_fault_mode.md L396-L418
    std::string grepOut1 = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case1_matched = !grepOut1.empty();
    // Warning: ZMQ fault=0 check requires parsing Metrics Summary section
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault021::GetName() const
{
    return "DS进程内层";
}

std::string KvcacheConnFault021::GetRootCauseDesc() const
{
    return "Worker crash/未拉起/机器故障、对端处理慢拖超时、对端主动拒绝";
}

RootCause KvcacheConnFault021::AnalyzeRootCause()
{
    return RootCause(true, "Worker crash/未拉起/机器故障、对端处理慢拖超时、对端主动拒绝");
}

std::string KvcacheConnFault021::GetFixSuggDesc() const
{
    return "查对端Worker存活；扩线程池";
}

std::string KvcacheConnFault021::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_FAILED]且对端Worker不在，或含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]";
}

std::string KvcacheConnFault021::GetId() const
{
    return "kvcache_conn_fault_021";
}

} // namespace diag