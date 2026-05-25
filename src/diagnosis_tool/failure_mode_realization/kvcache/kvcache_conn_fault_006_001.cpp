#include "kvcache_conn_fault_006_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_006_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334)
static AutoRegister<KvcacheConnFault006_001> g_kvcacheconnfault006_001("kvcache_conn_fault_006_001");

bool KvcacheConnFault006_001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E 'Get mmap entry failed' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault006_001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    return "code=5 + Get mmap entry failed (OS)";
}

std::string KvcacheConnFault006_001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    return "K_RUNTIME_ERROR(5)配合Get mmap entry failed，属于OS层mlock内存限制问题。（来源：08手册:L334）";
}

RootCause KvcacheConnFault006_001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    return "ulimit -l unlimited；或查看/proc/<pid>/limits确认mlock上限。（来源：08手册:L334）";
}

std::string KvcacheConnFault006_001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L309, L311, L192, L334
    return "通过日志关键字识别（来源：08手册:L192, L334）：匹配Get mmap entry failed。（来源：08手册:L192, L334）";
}

std::string KvcacheConnFault006_001::GetId() const
{
    return "kvcache_conn_fault_006_001";
}

} // namespace diag
