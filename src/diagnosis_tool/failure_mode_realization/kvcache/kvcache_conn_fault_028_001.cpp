#include "kvcache_conn_fault_028_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123)
static AutoRegister<KvcacheConnFault028_001> g_kvcacheconnfault028_001("kvcache_conn_fault_028_001");

bool KvcacheConnFault028_001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E '\\[URMA_NEED_CONNECT\\]' $WITTY_UB_WORKER_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    return "URMA_NEED_CONNECT + remoteInstanceId变化（对端Worker重启）";
}

std::string KvcacheConnFault028_001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    return "对端Worker重启导致URMA连接失效，属于预期行为，等待SDK自重连稳定。（来源：08手册:L297）";
}

RootCause KvcacheConnFault028_001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    return "确认对端Worker确实重启后，等待SDK自重连稳定；若重启由编排触发则属正常。（来源：08手册:L297）";
}

std::string KvcacheConnFault028_001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L885, L887-888, L297, L123
    return "通过日志关键字识别（来源：08手册:L297）：匹配[URMA_NEED_CONNECT]且remoteInstanceId变化。（来源：08手册:L297, 10案例:L123）";
}

std::string KvcacheConnFault028_001::GetId() const
{
    return "kvcache_conn_fault_028_001";
}

} // namespace diag
