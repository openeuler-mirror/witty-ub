#include "kvcache_conn_fault_020_002.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337)
static AutoRegister<KvcacheConnFault020_002> g_kvcacheconnfault020_002("kvcache_conn_fault_020_002");

bool KvcacheConnFault020_002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[TCP_CONNECT_RESET\\]|\\[TCP_NETWORK_UNREACHABLE\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    return "1001/1002 → OS侧TCP连接重置/网络不可达";
}

std::string KvcacheConnFault020_002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    return "网络闪断或路由不可达，属于OS层。（来源：08手册:L209）";
}

RootCause KvcacheConnFault020_002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    return "dmesg查看系统日志；netstat -s | grep reset查看重置统计。（来源：08手册:L337）";
}

std::string KvcacheConnFault020_002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L654, L657-658, L209, L337
    return "通过日志关键字识别（来源：08手册:L209, L337）：匹配[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]。（来源：08手册:L209, L337）";
}

std::string KvcacheConnFault020_002::GetId() const
{
    return "kvcache_conn_fault_020_002";
}

} // namespace diag
