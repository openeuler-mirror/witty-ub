#include "kvcache_conn_fault_020_007.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_007 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224)
static AutoRegister<KvcacheConnFault020_007> g_kvcacheconnfault020_007("kvcache_conn_fault_020_007");

bool KvcacheConnFault020_007::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E '\\[RPC_RECV_TIMEOUT\\]' $WITTY_UB_CLIENT_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_007::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    return "1001/1002 → yuanrong-datasystem进程内：RPC接收超时（对端处理慢）";
}

std::string KvcacheConnFault020_007::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    return "对端处理慢导致超时，属于yuanrong-datasystem进程内问题。（来源：08手册:L224）";
}

RootCause KvcacheConnFault020_007::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_007::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    return "查Worker CPU使用率、锁争用情况；扩oc_rpc_thread_num线程数。（来源：08手册:L271）";
}

std::string KvcacheConnFault020_007::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L769, L771-772, L224
    return "通过日志关键字识别（来源：08手册:L224）：匹配[RPC_RECV_TIMEOUT]且ZMQ fault=0。（来源：08手册:L224）";
}

std::string KvcacheConnFault020_007::GetId() const
{
    return "kvcache_conn_fault_020_007";
}

} // namespace diag
