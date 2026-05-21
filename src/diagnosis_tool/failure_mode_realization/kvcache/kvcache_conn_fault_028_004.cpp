#include "kvcache_conn_fault_028_004.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_004 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125)
static AutoRegister<KvcacheConnFault028_004> g_kvcacheconnfault028_004("kvcache_conn_fault_028_004");

bool KvcacheConnFault028_004::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[URMA_RECREATE_JFS_FAILED\\]' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_004::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    return "URMA_RECREATE_JFS_FAILED连续（JFS重建失败）";
}

std::string KvcacheConnFault028_004::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    return "JFS重建连续失败，可能为UMDK/驱动异常，属于URMA责任。（来源：08手册:L300）";
}

RootCause KvcacheConnFault028_004::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault028_004::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    return "查UMDK/驱动日志；上报URMA团队。（来源：08手册:L300）";
}

std::string KvcacheConnFault028_004::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L945, L947, L300, L125
    return "通过日志关键字识别（来源：08手册:L300, 10案例:L125）：匹配[URMA_RECREATE_JFS_FAILED]连续出现。（来源：08手册:L300）";
}

std::string KvcacheConnFault028_004::GetId() const
{
    return "kvcache_conn_fault_028_004";
}

} // namespace diag
