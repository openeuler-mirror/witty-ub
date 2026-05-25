#include "kvcache_conn_fault_028_005.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_005 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624)
static AutoRegister<KvcacheConnFault028_005> g_kvcacheconnfault028_005("kvcache_conn_fault_028_005");

bool KvcacheConnFault028_005::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E 'fallback to TCP/IP payload' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_005::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    return "fallback to TCP/IP payload（URMA降级TCP）";
}

std::string KvcacheConnFault028_005::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    return "URMA已降级到TCP（功能正常但性能退化），属于URMA问题引起的时延/性能降级。（来源：08手册:L306）";
}

RootCause KvcacheConnFault028_005::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_005::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    return "检查UB端口状态（ifconfig ub0 up）；修UMDK。（来源：08手册:L587）";
}

std::string KvcacheConnFault028_005::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L967, L969, L301, L624
    return "通过日志关键字识别（来源：08手册:L301, L624）：匹配fallback to TCP/IP payload。（来源：08手册:L301, L624）";
}

std::string KvcacheConnFault028_005::GetId() const
{
    return "kvcache_conn_fault_028_005";
}

} // namespace diag
