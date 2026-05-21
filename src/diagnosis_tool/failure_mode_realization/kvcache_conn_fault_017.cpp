#include "kvcache_conn_fault_017.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault017> g_KvcacheConnFault017("kvcache_conn_fault_017");

KvcacheConnFault017::KvcacheConnFault017() noexcept
{
}

bool KvcacheConnFault017::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L334-L344
    // 来源: 08-fault-triage-consolidated.md L105-L106
    // 来源: 10-customer-fault-scenarios.md L171-L172
    // 验证方法: INFO log含[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]
    // 匹配逻辑: grep `\[TCP_CONNECT_RESET\]`或`\[TCP_NETWORK_UNREACHABLE\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[TCP_CONNECT_RESET\]|\[TCP_NETWORK_UNREACHABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault017::GetName() const
{
    return "TCP连接重置/网络不可达";
}

std::string KvcacheConnFault017::GetRootCauseDesc() const
{
    return "网络闪断（除非同窗Worker重启）";
}

RootCause KvcacheConnFault017::AnalyzeRootCause()
{
    return RootCause(true, "网络闪断（除非同窗Worker重启）");
}

std::string KvcacheConnFault017::GetFixSuggDesc() const
{
    return "dmesg；netstat -s | grep reset";
}

std::string KvcacheConnFault017::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]";
}

std::string KvcacheConnFault017::GetId() const
{
    return "kvcache_conn_fault_017";
}

} // namespace diag