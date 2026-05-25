#include "kvcache_conn_fault_020_006.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_006 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223)
static AutoRegister<KvcacheConnFault020_006> g_kvcacheconnfault020_006("kvcache_conn_fault_020_006");

bool KvcacheConnFault020_006::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[TCP_CONNECT_FAILED\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_006::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    return "1001/1002 → yuanrong-datasystem进程内：对端Worker不在";
}

std::string KvcacheConnFault020_006::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    return "Worker crash/未拉起/机器故障，属于yuanrong-datasystem进程内问题。（来源：08手册:L223）";
}

RootCause KvcacheConnFault020_006::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_006::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    return "检查Worker进程状态（pgrep -af datasystem_worker）；若无进程则由编排拉起；若反复crash则查Worker crash dump。（来源：08手册:L223）";
}

std::string KvcacheConnFault020_006::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L749, L751-752, L223
    return "通过日志关键字识别（来源：08手册:L223）：匹配[TCP_CONNECT_FAILED]且对端Worker不在。（来源：08手册:L223）";
}

std::string KvcacheConnFault020_006::GetId() const
{
    return "kvcache_conn_fault_020_006";
}

} // namespace diag
