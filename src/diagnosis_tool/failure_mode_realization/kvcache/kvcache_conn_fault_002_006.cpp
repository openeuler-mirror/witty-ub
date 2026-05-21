#include "kvcache_conn_fault_002_006.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_006 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130)
static AutoRegister<KvcacheConnFault002_006> g_kvcacheconnfault002_006("kvcache_conn_fault_002_006");

bool KvcacheConnFault002_006::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -w 2");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_006::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    return "错误码2 K_INVALID";
}

std::string KvcacheConnFault002_006::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    return "K_INVALID表示业务参数非法，属于用户侧问题。（来源：08手册:L130）";
}

RootCause KvcacheConnFault002_006::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_006::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    return "业务方校验调用参数。（来源：08手册:L130, L247）";
}

std::string KvcacheConnFault002_006::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L227, L229, L130
    return "通过access log识别（来源：08手册:L130, L189）：access log中status_code（第8列）为2。（来源：08手册:L130）";
}

std::string KvcacheConnFault002_006::GetId() const
{
    return "kvcache_conn_fault_002_006";
}

} // namespace diag
