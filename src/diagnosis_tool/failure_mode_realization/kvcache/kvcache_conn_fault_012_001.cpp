#include "kvcache_conn_fault_012_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_012_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225)
static AutoRegister<KvcacheConnFault012_001> g_kvcacheconnfault012_001("kvcache_conn_fault_012_001");

bool KvcacheConnFault012_001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E '\\[RPC_RECV_TIMEOUT\\]|\\[RPC_SERVICE_UNAVAILABLE\\]' $WITTY_UB_CLIENT_INFO_LOG $WITTY_UB_WORKER_INFO_LOG 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault012_001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    return "对端处理慢/拒绝（RPC超时/服务不可用）";
}

std::string KvcacheConnFault012_001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    return "Worker对端处理慢或线程池打满导致RPC超时，属于yuanrong-datasystem进程内问题。（来源：08手册:L271）";
}

RootCause KvcacheConnFault012_001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    return "查Worker CPU使用率、锁争用情况；扩oc_rpc_thread_num线程数。（来源：08手册:L271）";
}

std::string KvcacheConnFault012_001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L512, L515-516, L271, L224-225
    return "通过日志关键字识别（来源：08手册:L271）：匹配[RPC_RECV_TIMEOUT]或[RPC_SERVICE_UNAVAILABLE]；配合resource.log中WAITING_TASK_NUM堆积。（来源：08手册:L271, L224-225）";
}

std::string KvcacheConnFault012_001::GetId() const
{
    return "kvcache_conn_fault_012_001";
}

} // namespace diag
