#include "kvcache_conn_fault_028_006.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_006 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128)
static AutoRegister<KvcacheConnFault028_006> g_kvcacheconnfault028_006("kvcache_conn_fault_028_006");

bool KvcacheConnFault028_006::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[URMA_POLL_ERROR\\]' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_006::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    return "URMA_POLL_ERROR（驱动/硬件）";
}

std::string KvcacheConnFault028_006::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    return "UB驱动/硬件报告Poll错误，属于URMA责任。（来源：08手册:L302）";
}

RootCause KvcacheConnFault028_006::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_006::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    return "grep UMDK日志；检查dmesg中UB相关错误。（来源：08手册:L302）";
}

std::string KvcacheConnFault028_006::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L992, L994, L302, L128
    return "通过日志关键字识别（来源：08手册:L302, 10案例:L128）：匹配[URMA_POLL_ERROR]。（来源：08手册:L302）";
}

std::string KvcacheConnFault028_006::GetId() const
{
    return "kvcache_conn_fault_028_006";
}

} // namespace diag
