#include "kvcache_conn_fault_006.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_006 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131)
static AutoRegister<KvcacheConnFault006> g_kvcacheconnfault006("kvcache_conn_fault_006");

bool KvcacheConnFault006::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG | sort | uniq -c | grep -w 5");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=5的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"5\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault006::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    return "错误码5 K_RUNTIME_ERROR";
}

std::string KvcacheConnFault006::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    return "向下级匹配。";
}

RootCause KvcacheConnFault006::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault006::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    return "向下级匹配。";
}

std::string KvcacheConnFault006::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L284, L286, L131
    return "通过access log识别（来源：08手册:L131, L191-195）：access log中status_code（第8列）为5；并通过Worker INFO log按日志串细分。（来源：08手册:L131, L191-195）";
}

std::string KvcacheConnFault006::GetId() const
{
    return "kvcache_conn_fault_006";
}

} // namespace diag
