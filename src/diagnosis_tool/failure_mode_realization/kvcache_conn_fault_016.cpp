#include "kvcache_conn_fault_016.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault016> g_KvcacheConnFault016("kvcache_conn_fault_016");

KvcacheConnFault016::KvcacheConnFault016() noexcept
{
}

bool KvcacheConnFault016::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L318-L332
    // 来源: 08-fault-triage-consolidated.md L103-L104
    // 来源: 10-customer-fault-scenarios.md L169-L170
    // Case 1: [TCP_CONNECT_FAILED]
    // 来源: references/kvcache_conn_fault_mode.md L318-L332
    std::string grepOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = !grepOutput0.empty();
    // Case 2: 对端Worker仍活
    // 来源: references/kvcache_conn_fault_mode.md L318-L332
    bool case1_matched = kvcache_conn_utils::ProcessExists("datasystem_worker");
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault016::GetName() const
{
    return "TCP建连失败（对端Worker活）";
}

std::string KvcacheConnFault016::GetRootCauseDesc() const
{
    return "端口不通/iptables/路由";
}

RootCause KvcacheConnFault016::AnalyzeRootCause()
{
    return RootCause(true, "端口不通/iptables/路由");
}

std::string KvcacheConnFault016::GetFixSuggDesc() const
{
    return "ss -tnlp；iptables -L -n；开端口/删规则";
}

std::string KvcacheConnFault016::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_FAILED]且对端Worker进程仍存活";
}

std::string KvcacheConnFault016::GetId() const
{
    return "kvcache_conn_fault_016";
}

} // namespace diag