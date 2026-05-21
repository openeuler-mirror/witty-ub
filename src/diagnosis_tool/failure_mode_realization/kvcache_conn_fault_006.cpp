#include "kvcache_conn_fault_006.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault006> g_KvcacheConnFault006("kvcache_conn_fault_006");

KvcacheConnFault006::KvcacheConnFault006() noexcept
{
}

bool KvcacheConnFault006::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L151-L160
    // 来源: 08-fault-triage-consolidated.md L179
    // 来源: 10-customer-fault-scenarios.md L135-L136
    // 验证方法: access log含OBJECT_KEYS_MAX_SIZE_LIMIT
    // 匹配逻辑: grep `OBJECT_KEYS_MAX_SIZE_LIMIT` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'OBJECT_KEYS_MAX_SIZE_LIMIT' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault006::GetName() const
{
    return "批次超限";
}

std::string KvcacheConnFault006::GetRootCauseDesc() const
{
    return "批次超限";
}

RootCause KvcacheConnFault006::AnalyzeRootCause()
{
    return RootCause(true, "批次超限");
}

std::string KvcacheConnFault006::GetFixSuggDesc() const
{
    return "拆batch";
}

std::string KvcacheConnFault006::GetValidationMethodDesc() const
{
    return "access log含OBJECT_KEYS_MAX_SIZE_LIMIT";
}

std::string KvcacheConnFault006::GetId() const
{
    return "kvcache_conn_fault_006";
}

} // namespace diag