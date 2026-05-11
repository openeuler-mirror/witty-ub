#include "kvcache_conn_fault_029.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault029> g_KvcacheConnFault029("kvcache_conn_fault_029");

KvcacheConnFault029::KvcacheConnFault029() noexcept
{
}

bool KvcacheConnFault029::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L550-L561
    // 来源: 03-fault-mode-library.md L64-L65
    // 来源: 03-fault-mode-library.md L95-L96
    // 验证方法: INFO log含Failed to urma write object或Failed to urma read object
    // 匹配逻辑: grep `Failed to urma write object`或`Failed to urma read object` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Failed to urma write object|Failed to urma read object' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault029::GetName() const
{
    return "URMA数据面读写失败";
}

std::string KvcacheConnFault029::GetRootCauseDesc() const
{
    return "读写到对端UB失败";
}

RootCause KvcacheConnFault029::AnalyzeRootCause()
{
    return RootCause(true, "读写到对端UB失败");
}

std::string KvcacheConnFault029::GetFixSuggDesc() const
{
    return "UB/URMA运维排查";
}

std::string KvcacheConnFault029::GetValidationMethodDesc() const
{
    return "INFO log含Failed to urma write object或Failed to urma read object";
}

std::string KvcacheConnFault029::GetId() const
{
    return "kvcache_conn_fault_029";
}

} // namespace diag