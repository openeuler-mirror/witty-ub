#include "kvcache_conn_fault_025.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault025> g_KvcacheConnFault025("kvcache_conn_fault_025");

KvcacheConnFault025::KvcacheConnFault025() noexcept
{
}

bool KvcacheConnFault025::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L477-L495
    // 来源: 08-fault-triage-consolidated.md L226-L229
    // 来源: 10-customer-fault-scenarios.md L148-L158
    // 验证方法: INFO log含URMA CQ error或URMA driver error
    // 匹配逻辑: grep `\[URMA_POLL_ERROR\]`或`\[URMA_WAIT_TIMEOUT\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[URMA_POLL_ERROR\]|\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault025::GetName() const
{
    return "URMA驱动/CQ错误";
}

std::string KvcacheConnFault025::GetRootCauseDesc() const
{
    return "PollJfcWait报错（驱动/硬件）或等待CQE超时";
}

RootCause KvcacheConnFault025::AnalyzeRootCause()
{
    return RootCause(true, "PollJfcWait报错（驱动/硬件）或等待CQE超时");
}

std::string KvcacheConnFault025::GetFixSuggDesc() const
{
    return "grep UMDK日志/dmesg；SDK重试白名单自愈";
}

std::string KvcacheConnFault025::GetValidationMethodDesc() const
{
    return "INFO log含URMA CQ error或URMA driver error";
}

std::string KvcacheConnFault025::GetId() const
{
    return "kvcache_conn_fault_025";
}

} // namespace diag