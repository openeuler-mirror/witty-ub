#include "kvcache_conn_fault_028.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault028> g_KvcacheConnFault028("kvcache_conn_fault_028");

KvcacheConnFault028::KvcacheConnFault028() noexcept
{
}

bool KvcacheConnFault028::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L536-L548
    // 来源: 03-fault-mode-library.md L60-L61
    // 来源: 03-fault-mode-library.md L95-L96
    // 验证方法: INFO log含Fast transport handshake failed或Failed to import jfr或advise jfr
    // 匹配逻辑: grep `Fast transport handshake failed`或`Failed to import jfr`或`advise jfr` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Fast transport handshake failed|Failed to import jfr|advise jfr' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault028::GetName() const
{
    return "FastTransport/握手失败";
}

std::string KvcacheConnFault028::GetRootCauseDesc() const
{
    return "UB握手失败、回退";
}

RootCause KvcacheConnFault028::AnalyzeRootCause()
{
    return RootCause(true, "UB握手失败、回退");
}

std::string KvcacheConnFault028::GetFixSuggDesc() const
{
    return "UB/URMA运维排查";
}

std::string KvcacheConnFault028::GetValidationMethodDesc() const
{
    return "INFO log含Fast transport handshake failed或Failed to import jfr或advise jfr";
}

std::string KvcacheConnFault028::GetId() const
{
    return "kvcache_conn_fault_028";
}

} // namespace diag