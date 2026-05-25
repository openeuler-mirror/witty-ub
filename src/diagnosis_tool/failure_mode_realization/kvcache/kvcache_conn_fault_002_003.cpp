#include "kvcache_conn_fault_002_003.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_003 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249)
static AutoRegister<KvcacheConnFault002_003> g_kvcacheconnfault002_003("kvcache_conn_fault_002_003");

bool KvcacheConnFault002_003::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep 'Client object is already sealed' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_CLIENT_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_003::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    return "respMsg重复Publish故障";
}

std::string KvcacheConnFault002_003::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    return "buffer重复Publish，属于用户业务逻辑问题。（来源：08手册:L249）";
}

RootCause KvcacheConnFault002_003::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_003::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    return "检查业务逻辑，确认是否对同一对象重复调用Publish。（来源：08手册:L249）";
}

std::string KvcacheConnFault002_003::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L170, L172, L249
    return "通过日志关键字识别（来源：08手册:L249）：匹配Client object is already sealed。（来源：08手册:L249）";
}

std::string KvcacheConnFault002_003::GetId() const
{
    return "kvcache_conn_fault_002_003";
}

} // namespace diag
