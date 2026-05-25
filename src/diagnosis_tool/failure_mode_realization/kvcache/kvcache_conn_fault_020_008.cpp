#include "kvcache_conn_fault_020_008.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_008 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225)
static AutoRegister<KvcacheConnFault020_008> g_kvcacheconnfault020_008("kvcache_conn_fault_020_008");

bool KvcacheConnFault020_008::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[RPC_SERVICE_UNAVAILABLE\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_008::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    return "1001/1002 → yuanrong-datasystem进程内：RPC服务不可用（对端主动拒绝）";
}

std::string KvcacheConnFault020_008::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    return "对端Worker正在shutting down或状态异常，属于yuanrong-datasystem进程内问题。（来源：08手册:L225）";
}

RootCause KvcacheConnFault020_008::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_008::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    return "检查对端Worker状态，确认是否在正常退出/扩缩容流程中；若非预期退出，检查Worker日志中的[HealthCheck]相关条目。（来源：08手册:L225, L274）";
}

std::string KvcacheConnFault020_008::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L791, L794-795, L225
    return "通过日志关键字识别（来源：08手册:L225）：匹配[RPC_SERVICE_UNAVAILABLE]。（来源：08手册:L225）";
}

std::string KvcacheConnFault020_008::GetId() const
{
    return "kvcache_conn_fault_020_008";
}

} // namespace diag
