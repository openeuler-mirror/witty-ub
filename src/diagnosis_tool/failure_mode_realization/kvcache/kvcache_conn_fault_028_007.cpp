#include "kvcache_conn_fault_028_007.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_007 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303)
static AutoRegister<KvcacheConnFault028_007> g_kvcacheconnfault028_007("kvcache_conn_fault_028_007");

bool KvcacheConnFault028_007::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[URMA_WAIT_TIMEOUT\\]' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_007::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    return "URMA_WAIT_TIMEOUT（等待CQE超时, code=1010）";
}

std::string KvcacheConnFault028_007::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    return "CQE等待超时，可能是链路抖动或对端重启触发；单独出现则由SDK白名单重试自愈。（来源：08手册:L303）";
}

RootCause KvcacheConnFault028_007::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_007::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    return "若伴instanceId变化则按kvcache_conn_fault_028_001处理；若单独出现则由SDK白名单重试自愈。（来源：08手册:L303）";
}

std::string KvcacheConnFault028_007::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1015, L1017, L303
    return "通过日志关键字识别（来源：08手册:L303）：匹配[URMA_WAIT_TIMEOUT]。（来源：08手册:L303）";
}

std::string KvcacheConnFault028_007::GetId() const
{
    return "kvcache_conn_fault_028_007";
}

} // namespace diag
