#include "kvcache_conn_fault_002_005.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_005 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251)
static AutoRegister<KvcacheConnFault002_005> g_kvcacheconnfault002_005("kvcache_conn_fault_002_005");

bool KvcacheConnFault002_005::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && grep -E 'Can.?t find object' $WITTY_UB_CLIENT_INFO_LOG $WITTY_UB_WORKER_INFO_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_005::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "respMsg对象不存在故障";
}

std::string KvcacheConnFault002_005::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "对象不存在，属于用户侧问题。可能原因：业务未Put直接Get、对象已过期（TTL）、key拼写错误。（来源：08手册:L251）";
}

RootCause KvcacheConnFault002_005::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_005::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "业务方自查Put/Get顺序、key正确性、TTL设置。（来源：08手册:L251）";
}

std::string KvcacheConnFault002_005::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L200, L203-204, L251
    return "通过日志关键字识别（来源：08手册:L251）：在ds_client_*.INFO.log中匹配Can't find object或K_NOT_FOUND。（来源：08手册:L251）";
}

std::string KvcacheConnFault002_005::GetId() const
{
    return "kvcache_conn_fault_002_005";
}

} // namespace diag
