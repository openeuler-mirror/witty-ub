#include "kvcache_conn_fault_043.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault043> g_KvcacheConnFault043("kvcache_conn_fault_043");

KvcacheConnFault043::KvcacheConnFault043() noexcept
{
}

bool KvcacheConnFault043::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L770-L775（从1.4.1.3上下文推断）
    // 来源: 10-customer-fault-scenarios.md L539-L540
    // 验证方法: INFO log含[SHM_FD_TRANSFER_FAILED]
    // 匹配逻辑: grep `\[SHM_FD_TRANSFER_FAILED\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[SHM_FD_TRANSFER_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault043::GetName() const
{
    return "SHM传fd失败";
}

std::string KvcacheConnFault043::GetRootCauseDesc() const
{
    return "同机SHM fd传输失败，fd耗尽或权限问题";
}

RootCause KvcacheConnFault043::AnalyzeRootCause()
{
    return RootCause(true, "同机SHM fd传输失败，fd耗尽或权限问题");
}

std::string KvcacheConnFault043::GetFixSuggDesc() const
{
    return "检查ulimit -n；SELinux/AppArmor；/proc/sys/fs/file-max";
}

std::string KvcacheConnFault043::GetValidationMethodDesc() const
{
    return "INFO log含[SHM_FD_TRANSFER_FAILED]";
}

std::string KvcacheConnFault043::GetId() const
{
    return "kvcache_conn_fault_043";
}

} // namespace diag