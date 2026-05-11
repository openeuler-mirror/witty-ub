#include "kvcache_conn_fault_009.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault009> g_KvcacheConnFault009("kvcache_conn_fault_009");

KvcacheConnFault009::KvcacheConnFault009() noexcept
{
}

bool KvcacheConnFault009::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L196-L213
    // 来源: 08-fault-triage-consolidated.md L120-L121
    // 来源: 10-customer-fault-scenarios.md L172-L173
    // Case 1: [RPC_RECV_TIMEOUT]且ZMQ fault=0
    // 来源: references/kvcache_conn_fault_mode.md L196-L213
    std::string grepOut0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[RPC_RECV_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = !grepOut0.empty();
    // Warning: ZMQ fault=0 check requires parsing Metrics Summary section
    // Case 2: [RPC_SERVICE_UNAVAILABLE]
    // 来源: references/kvcache_conn_fault_mode.md L196-L213
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep '\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault009::GetName() const
{
    return "对端处理慢/拒绝";
}

std::string KvcacheConnFault009::GetRootCauseDesc() const
{
    return "对端Worker处理慢或主动拒绝，线程池打满";
}

RootCause KvcacheConnFault009::AnalyzeRootCause()
{
    return RootCause(true, "对端Worker处理慢或主动拒绝，线程池打满");
}

std::string KvcacheConnFault009::GetFixSuggDesc() const
{
    return "查Worker CPU/锁；扩oc_rpc_thread_num";
}

std::string KvcacheConnFault009::GetValidationMethodDesc() const
{
    return "INFO log含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]";
}

std::string KvcacheConnFault009::GetId() const
{
    return "kvcache_conn_fault_009";
}

} // namespace diag