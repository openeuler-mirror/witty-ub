#include "kvcache_conn_fault_020_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208)
static AutoRegister<KvcacheConnFault020_001> g_kvcacheconnfault020_001("kvcache_conn_fault_020_001");

bool KvcacheConnFault020_001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[TCP_CONNECT_FAILED\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    return "1001/1002 → OS侧TCP连接失败（对端活）";
}

std::string KvcacheConnFault020_001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    return "端口不通/iptables/路由问题，属于OS层。（来源：08手册:L208）";
}

RootCause KvcacheConnFault020_001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    return "ss -tnlp确认端口LISTEN；iptables -L -n检查规则；开端口/删规则。（来源：08手册:L336）";
}

std::string KvcacheConnFault020_001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L629, L631, L208
    return "通过日志关键字识别（来源：08手册:L208, L336）：匹配[TCP_CONNECT_FAILED]且对端Worker活。（来源：08手册:L208）";
}

std::string KvcacheConnFault020_001::GetId() const
{
    return "kvcache_conn_fault_020_001";
}

} // namespace diag
