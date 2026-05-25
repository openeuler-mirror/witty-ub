#include "kvcache_conn_fault_028_002.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124)
static AutoRegister<KvcacheConnFault028_002> g_kvcacheconnfault028_002("kvcache_conn_fault_028_002");

bool KvcacheConnFault028_002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[URMA_NEED_CONNECT\\]' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    return "URMA_NEED_CONNECT持续 + instanceId不变（UB链路不稳）";
}

std::string KvcacheConnFault028_002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    return "UB链路不稳，需区分是硬件/驱动问题还是端口/交换机抖动。（来源：08手册:L298）";
}

RootCause KvcacheConnFault028_002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    return "检查UB端口状态和交换机；若伴POLL_ERROR/RECREATE_JFS则需联系URMA/UB运维。（来源：08手册:L298）";
}

std::string KvcacheConnFault028_002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L907, L909, L298, L124
    return "通过日志关键字识别（来源：08手册:L298, 10案例:L124）：匹配[URMA_NEED_CONNECT]持续出现且instanceId不变。（来源：08手册:L298）";
}

std::string KvcacheConnFault028_002::GetId() const
{
    return "kvcache_conn_fault_028_002";
}

} // namespace diag
