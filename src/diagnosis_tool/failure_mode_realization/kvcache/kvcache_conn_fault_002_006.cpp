#include "kvcache_conn_fault_002_006.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_006 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251)
static AutoRegister<KvcacheConnFault002_006> g_kvcacheconnfault002_005("kvcache_conn_fault_002_006");

bool KvcacheConnFault002_006::IsValid()
{
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG | sort | uniq -c | grep -w 2");
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"2\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_006::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "错误码2 K_INVALID";
}

std::string KvcacheConnFault002_006::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "K_INVALID表示业务参数非法，属于用户侧问题（08手册:L130）";
}

RootCause KvcacheConnFault002_006::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_006::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "业务方校验调用参数（08手册:L130, L247）";
}

std::string KvcacheConnFault002_006::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L130, L189）：access log中status_code（第8列）为2";
}

std::string KvcacheConnFault002_006::GetId() const
{
    return "kvcache_conn_fault_002_006";
}

} // namespace diag
