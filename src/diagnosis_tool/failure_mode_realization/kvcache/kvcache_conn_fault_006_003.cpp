#include "kvcache_conn_fault_006_003.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_006_003 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194)
static AutoRegister<KvcacheConnFault006_003> g_kvcacheconnfault006_003("kvcache_conn_fault_006_003");

bool KvcacheConnFault006_003::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E 'urma.*payload|Failed to urma' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault006_003::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    return "code=5 + urma ... payload ... (URMA)";
}

std::string KvcacheConnFault006_003::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    return "URMA数据面payload问题，属于URMA责任。（来源：08手册:L194）";
}

RootCause KvcacheConnFault006_003::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_003::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    return "向下级匹配URMA故障（见kvcache_conn_fault_028节）。（来源：08手册:L281-308）";
}

std::string KvcacheConnFault006_003::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L346, L348, L194
    return "通过日志关键字识别（来源：08手册:L194）：匹配urma.*payload或Failed to urma。（来源：08手册:L194）";
}

std::string KvcacheConnFault006_003::GetId() const
{
    return "kvcache_conn_fault_006_003";
}

} // namespace diag
