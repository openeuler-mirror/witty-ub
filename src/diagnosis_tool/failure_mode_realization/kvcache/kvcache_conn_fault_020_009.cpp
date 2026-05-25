#include "kvcache_conn_fault_020_009.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_009 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226)
static AutoRegister<KvcacheConnFault020_009> g_kvcacheconnfault020_009("kvcache_conn_fault_020_009");

bool KvcacheConnFault020_009::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E 'zmq_event_handshake_failure_total' $WITTY_UB_WORKER_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_009::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    return "1001/1002 → yuanrong-datasystem进程内：TLS/认证配置（握手失败）";
}

std::string KvcacheConnFault020_009::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    return "TLS/认证配置问题，属于yuanrong-datasystem进程内配置问题。（来源：08手册:L226）";
}

RootCause KvcacheConnFault020_009::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_009::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    return "检查TLS证书配置、认证参数是否正确。（来源：08手册:L226）";
}

std::string KvcacheConnFault020_009::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L807, L810, L226
    return "通过日志关键字识别（来源：08手册:L226）：匹配zmq_event_handshake_failure_total增多。（来源：08手册:L226）";
}

std::string KvcacheConnFault020_009::GetId() const
{
    return "kvcache_conn_fault_020_009";
}

} // namespace diag
