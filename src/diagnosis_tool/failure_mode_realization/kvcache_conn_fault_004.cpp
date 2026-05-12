#include "kvcache_conn_fault_004.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault004> g_KvcacheConnFault004("kvcache_conn_fault_004");

KvcacheConnFault004::KvcacheConnFault004() noexcept
{
}

bool KvcacheConnFault004::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L129-L138
    // 来源: 08-fault-triage-consolidated.md L177
    // 来源: 10-customer-fault-scenarios.md L131-L132
    // 验证方法: INFO log含ConnectOptions was not configured
    // 匹配逻辑: grep `ConnectOptions was not configured` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'ConnectOptions was not configured' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault004::GetName() const
{
    return "未配置Init";
}

std::string KvcacheConnFault004::GetRootCauseDesc() const
{
    return "未配置Init";
}

RootCause KvcacheConnFault004::AnalyzeRootCause()
{
    return RootCause(true, "未配置Init");
}

std::string KvcacheConnFault004::GetFixSuggDesc() const
{
    return "检查Init";
}

std::string KvcacheConnFault004::GetValidationMethodDesc() const
{
    return "INFO log含ConnectOptions was not configured";
}

std::string KvcacheConnFault004::GetId() const
{
    return "kvcache_conn_fault_004";
}

} // namespace diag