#include "kvcache_conn_fault_030.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault030> g_KvcacheConnFault030("kvcache_conn_fault_030");

KvcacheConnFault030::KvcacheConnFault030() noexcept
{
}

bool KvcacheConnFault030::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L497-L498（从1.5.4上下文推断）
    // 来源: 08-fault-triage-consolidated.md L228-L229
    // Case 1: 返回错误码中有1010
    // 来源: references/kvcache_conn_fault_mode.md L497-L498（从1.5.4上下文推断）
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {1010});
    // Case 2: [URMA_WAIT_TIMEOUT]
    // 来源: references/kvcache_conn_fault_mode.md L497-L498（从1.5.4上下文推断）
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep '\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault030::GetName() const
{
    return "URMA超时";
}

std::string KvcacheConnFault030::GetRootCauseDesc() const
{
    return "URMA等待CQE超时";
}

RootCause KvcacheConnFault030::AnalyzeRootCause()
{
    return RootCause(true, "URMA等待CQE超时");
}

std::string KvcacheConnFault030::GetFixSuggDesc() const
{
    return "SDK重试白名单自愈；持续出现查UB链路";
}

std::string KvcacheConnFault030::GetValidationMethodDesc() const
{
    return "KVCache错误码为1010或INFO log含[URMA_WAIT_TIMEOUT]";
}

std::string KvcacheConnFault030::GetId() const
{
    return "kvcache_conn_fault_030";
}

} // namespace diag