#include "kvcache_conn_fault_014.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault014> g_KvcacheConnFault014("kvcache_conn_fault_014");

KvcacheConnFault014::KvcacheConnFault014() noexcept
{
}

bool KvcacheConnFault014::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L287-L300
    // 来源: 08-fault-triage-consolidated.md L73-L76
    // 来源: 10-customer-fault-scenarios.md L78-L83
    // 验证方法: KVCache错误码为1001(K_RPC_DEADLINE_EXCEEDED)或1002(K_RPC_UNAVAILABLE)，需看日志前缀确定边界
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有1001, 1002
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {1001, 1002});
}

std::string KvcacheConnFault014::GetName() const
{
    return "桶码错误";
}

std::string KvcacheConnFault014::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault014::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault014::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault014::GetValidationMethodDesc() const
{
    return "KVCache错误码为1001(K_RPC_DEADLINE_EXCEEDED)或1002(K_RPC_UNAVAILABLE)，需看日志前缀确定边界";
}

std::string KvcacheConnFault014::GetId() const
{
    return "kvcache_conn_fault_014";
}

} // namespace diag