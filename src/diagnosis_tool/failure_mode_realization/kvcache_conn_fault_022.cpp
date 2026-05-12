#include "kvcache_conn_fault_022.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault022> g_KvcacheConnFault022("kvcache_conn_fault_022");

KvcacheConnFault022::KvcacheConnFault022() noexcept
{
}

bool KvcacheConnFault022::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L420-L429
    // 来源: 08-fault-triage-consolidated.md L73-L74
    // 来源: 10-customer-fault-scenarios.md L78-L80
    // 验证方法: KVCache错误码为1004/1006/1008/1009/1010
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有1004, 1006, 1008, 1009, 1010
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {1004, 1006, 1008, 1009, 1010});
}

std::string KvcacheConnFault022::GetName() const
{
    return "URMA错误";
}

std::string KvcacheConnFault022::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault022::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault022::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault022::GetValidationMethodDesc() const
{
    return "KVCache错误码为1004/1006/1008/1009/1010";
}

std::string KvcacheConnFault022::GetId() const
{
    return "kvcache_conn_fault_022";
}

} // namespace diag