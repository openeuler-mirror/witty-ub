#include "kvcache_conn_fault_020_010.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_010 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605)
static AutoRegister<KvcacheConnFault020_010> g_kvcacheconnfault020_010("kvcache_conn_fault_020_010");

bool KvcacheConnFault020_010::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[SOCK_CONN_WAIT_TIMEOUT\\]|\\[REMOTE_SERVICE_WAIT_TIMEOUT\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_010::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    return "1001/1002 → 需进一步验证：SOCK/REMOTE握手超时";
}

std::string KvcacheConnFault020_010::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    return "握手延迟超时，需根据对端Worker存活状态区分是OS网络慢还是yuanrong-datasystem问题。（来源：08手册:L232）";
}

RootCause KvcacheConnFault020_010::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_010::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    return "根据对端存活状态定界后按对应边界处置。（来源：08手册:L232）";
}

std::string KvcacheConnFault020_010::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L829, L832-833, L232, L605
    return "通过日志关键字识别（来源：08手册:L232）：匹配[SOCK_CONN_WAIT_TIMEOUT]或[REMOTE_SERVICE_WAIT_TIMEOUT]。（来源：08手册:L232, L605）";
}

std::string KvcacheConnFault020_010::GetId() const
{
    return "kvcache_conn_fault_020_010";
}

} // namespace diag
