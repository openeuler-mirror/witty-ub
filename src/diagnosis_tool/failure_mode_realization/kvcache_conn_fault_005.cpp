#include "kvcache_conn_fault_005.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault005> g_KvcacheConnFault005("kvcache_conn_fault_005");

KvcacheConnFault005::KvcacheConnFault005() noexcept
{
}

bool KvcacheConnFault005::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L140-L149
    // 来源: 08-fault-triage-consolidated.md L178
    // 来源: 10-customer-fault-scenarios.md L133-L134
    // 验证方法: INFO log含Client object is already sealed
    // 匹配逻辑: grep `Client object is already sealed` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Client object is already sealed' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault005::GetName() const
{
    return "buffer重复Publish";
}

std::string KvcacheConnFault005::GetRootCauseDesc() const
{
    return "buffer重复Publish";
}

RootCause KvcacheConnFault005::AnalyzeRootCause()
{
    return RootCause(true, "buffer重复Publish");
}

std::string KvcacheConnFault005::GetFixSuggDesc() const
{
    return "检查业务逻辑";
}

std::string KvcacheConnFault005::GetValidationMethodDesc() const
{
    return "INFO log含Client object is already sealed";
}

std::string KvcacheConnFault005::GetId() const
{
    return "kvcache_conn_fault_005";
}

} // namespace diag