#include "kvcache_conn_fault_007.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_007 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132)
static AutoRegister<KvcacheConnFault007> g_kvcacheconnfault007("kvcache_conn_fault_007");

bool KvcacheConnFault007::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -w 6");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault007::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    return "错误码6 K_OUT_OF_MEMORY (OS)";
}

std::string KvcacheConnFault007::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    return "内存不足（OOM），属于OS层问题。（来源：08手册:L132）";
}

RootCause KvcacheConnFault007::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault007::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    return "dmesg | grep -i 'Out of memory'；free -h；扩内存或调整cgroup限制。（来源：08手册:L330）";
}

std::string KvcacheConnFault007::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L362, L364, L132
    return "通过access log识别（来源：08手册:L132, L196）：access log中status_code（第8列）为6；或dmesg中Out of memory。（来源：08手册:L132, L330）";
}

std::string KvcacheConnFault007::GetId() const
{
    return "kvcache_conn_fault_007";
}

} // namespace diag
