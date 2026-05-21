#include "kvcache_conn_fault_020.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198)
static AutoRegister<KvcacheConnFault020> g_kvcacheconnfault020("kvcache_conn_fault_020");

bool KvcacheConnFault020::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -E '1001|1002'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    return "错误码1001 K_RPC_DEADLINE_EXCEEDED / 1002 K_RPC_UNAVAILABLE（桶码）";
}

std::string KvcacheConnFault020::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    return "向下级匹配，必须按日志前缀分流定界。（来源：08手册:L202-234）";
}

RootCause KvcacheConnFault020::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault020::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    return "向下级匹配。";
}

std::string KvcacheConnFault020::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L611, L613-615, L137, L198
    return "通过access log识别（来源：08手册:L137, L198）：access log中status_code（第8列）为1001或1002，须按日志前缀分流定界。（来源：08手册:L137, L140, L202）";
}

std::string KvcacheConnFault020::GetId() const
{
    return "kvcache_conn_fault_020";
}

} // namespace diag
