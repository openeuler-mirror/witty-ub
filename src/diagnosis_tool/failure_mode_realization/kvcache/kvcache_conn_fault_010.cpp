#include "kvcache_conn_fault_010.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_010 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132)
static AutoRegister<KvcacheConnFault010> g_kvcacheconnfault010("kvcache_conn_fault_010");

bool KvcacheConnFault010::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -w 18");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault010::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    return "错误码18 K_FILE_LIMIT_REACHED (OS)";
}

std::string KvcacheConnFault010::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    return "文件描述符耗尽，属于OS层问题。（来源：08手册:L132）";
}

RootCause KvcacheConnFault010::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault010::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    return "ls /proc/<pid>/fd | wc -l 对比 ulimit -n；调大ulimit -n。（来源：08手册:L333）";
}

std::string KvcacheConnFault010::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L433, L435, L132
    return "通过access log识别（来源：08手册:L132, L196）：access log中status_code（第8列）为18。（来源：08手册:L132）";
}

std::string KvcacheConnFault010::GetId() const
{
    return "kvcache_conn_fault_010";
}

} // namespace diag
