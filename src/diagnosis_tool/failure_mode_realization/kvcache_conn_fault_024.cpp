#include "kvcache_conn_fault_024.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault024> g_KvcacheConnFault024("kvcache_conn_fault_024");

KvcacheConnFault024::KvcacheConnFault024() noexcept
{
}

bool KvcacheConnFault024::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L457-L475
    // 来源: 08-fault-triage-consolidated.md L218-L221
    // Case 1: [URMA_RECREATE_JFS]
    // 来源: references/kvcache_conn_fault_mode.md L457-L475
    std::string grepOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[URMA_RECREATE_JFS\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case0_matched = !grepOutput0.empty();
    // Case 2: [URMA_RECREATE_JFS_FAILED]
    // 来源: references/kvcache_conn_fault_mode.md L457-L475
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep '\[URMA_RECREATE_JFS_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault024::GetName() const
{
    return "URMA JFS异常";
}

std::string KvcacheConnFault024::GetRootCauseDesc() const
{
    return "JFS异常自动重建（cqeStatus=9 ACK TIMEOUT）；JFS重建失败";
}

RootCause KvcacheConnFault024::AnalyzeRootCause()
{
    return RootCause(true, "JFS异常自动重建（cqeStatus=9 ACK TIMEOUT）；JFS重建失败");
}

std::string KvcacheConnFault024::GetFixSuggDesc() const
{
    return "无[URMA_RECREATE_JFS_FAILED]→自愈成功；有且连续→查UMDK/驱动日志并上报URMA团队";
}

std::string KvcacheConnFault024::GetValidationMethodDesc() const
{
    return "INFO log含Failed to import jfr或advise jfr";
}

std::string KvcacheConnFault024::GetId() const
{
    return "kvcache_conn_fault_024";
}

} // namespace diag