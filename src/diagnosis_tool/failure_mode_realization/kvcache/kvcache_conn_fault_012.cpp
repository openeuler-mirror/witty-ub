#include "kvcache_conn_fault_012.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_012 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136)
static AutoRegister<KvcacheConnFault012> g_kvcacheconnfault012("kvcache_conn_fault_012");

bool KvcacheConnFault012::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault012::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    return "yuanrong-datasystem进程内故障（19/23/29/31/32）";
}

std::string KvcacheConnFault012::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    return "向下级匹配，需要根据证据进一步定界。（来源：08手册:L256-278）";
}

RootCause KvcacheConnFault012::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault012::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    return "向下级匹配。（来源：08手册:L256-278）";
}

std::string KvcacheConnFault012::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L490, L493-497, L133-136
    return "通过access log识别（来源：08手册:L133-136, L197）：access log中status_code（第8列）为19/23/29/31/32。（来源：08手册:L133-136）";
}

std::string KvcacheConnFault012::GetId() const
{
    return "kvcache_conn_fault_012";
}

} // namespace diag
