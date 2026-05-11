#include "kvcache_conn_fault_038.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault038> g_KvcacheConnFault038("kvcache_conn_fault_038");

KvcacheConnFault038::KvcacheConnFault038() noexcept
{
}

bool KvcacheConnFault038::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L705-L720
    // 来源: 10-customer-fault-scenarios.md L539-L540
    // 来源: 10-customer-fault-scenarios.md L548-L549
    // 验证方法: INFO log含[TCP_CONNECT_FAILED]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或ConnectOptions was not configured
    // 匹配逻辑: grep `\[(TCP`或`UDS`或`SHM_FD)_`或`ConnectOptions was not configured` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"cmd(grep -E '\[(TCP|UDS|SHM_FD)_|ConnectOptions was not configured' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)cmd");
    return !grepOutput.empty();
}

std::string KvcacheConnFault038::GetName() const
{
    return "Client Init/连接Worker失败";
}

std::string KvcacheConnFault038::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault038::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault038::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault038::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_FAILED]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或ConnectOptions was not configured";
}

std::string KvcacheConnFault038::GetId() const
{
    return "kvcache_conn_fault_038";
}

} // namespace diag