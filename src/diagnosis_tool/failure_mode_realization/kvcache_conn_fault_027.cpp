#include "kvcache_conn_fault_027.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault027> g_KvcacheConnFault027("kvcache_conn_fault_027");

KvcacheConnFault027::KvcacheConnFault027() noexcept
{
}

bool KvcacheConnFault027::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L522-L534
    // 来源: 03-fault-mode-library.md L56-L57
    // 来源: 10-customer-fault-scenarios.md L148-L149
    // 验证方法: INFO log含Failed to urma init或Failed to urma get device by name或Failed to urma get eid list或Failed to urma create context或Failed to initialize URMA dlopen loader
    // 匹配逻辑: grep `Failed to urma init`或`Failed to urma get device by name`或`Failed to urma get eid list`或`Failed to urma create context`或`Failed to initialize URMA dlopen loader` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Failed to urma init|Failed to urma get device by name|Failed to urma get eid list|Failed to urma create context|Failed to initialize URMA dlopen loader' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault027::GetName() const
{
    return "URMA初始化失败";
}

std::string KvcacheConnFault027::GetRootCauseDesc() const
{
    return "UB初始化失败（UMDK设备/context/jfc等）";
}

RootCause KvcacheConnFault027::AnalyzeRootCause()
{
    return RootCause(true, "UB初始化失败（UMDK设备/context/jfc等）");
}

std::string KvcacheConnFault027::GetFixSuggDesc() const
{
    return "UB/URMA运维排查";
}

std::string KvcacheConnFault027::GetValidationMethodDesc() const
{
    return "INFO log含Failed to urma init或Failed to urma get device by name或Failed to urma get eid list或Failed to urma create context或Failed to initialize URMA dlopen loader";
}

std::string KvcacheConnFault027::GetId() const
{
    return "kvcache_conn_fault_027";
}

} // namespace diag