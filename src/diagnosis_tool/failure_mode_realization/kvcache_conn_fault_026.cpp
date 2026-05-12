#include "kvcache_conn_fault_026.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault026> g_KvcacheConnFault026("kvcache_conn_fault_026");

KvcacheConnFault026::KvcacheConnFault026() noexcept
{
}

bool KvcacheConnFault026::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L497-L520
    // 来源: 08-fault-triage-consolidated.md L230-L231
    // 来源: 10-customer-fault-scenarios.md L148-L149
    // Case 1: 返回错误码中有1009
    // 来源: references/kvcache_conn_fault_mode.md L497-L520
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {1009});
    // Case 2: UB端口down
    // 来源: references/kvcache_conn_fault_mode.md L497-L520
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(ifconfig ub0 2>/dev/null 2>/dev/null)");
    bool case1_matched = cmdOutput1.find("DOWN") != std::string::npos;
    // Case 3: UB设备节点缺失
    // 来源: references/kvcache_conn_fault_mode.md L497-L520
    std::string cmdOutput2 = kvcache_conn_utils::RunCommand(
        R"(ls /dev/ub* 2>/dev/null 2>/dev/null)");
    bool case2_matched = cmdOutput2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault026::GetName() const
{
    return "URMA建连失败";
}

std::string KvcacheConnFault026::GetRootCauseDesc() const
{
    return "URMA建连失败，UB端口down或设备节点缺失";
}

RootCause KvcacheConnFault026::AnalyzeRootCause()
{
    return RootCause(true, "URMA建连失败，UB端口down或设备节点缺失");
}

std::string KvcacheConnFault026::GetFixSuggDesc() const
{
    return "ifconfig ub0 up；检查UB设备节点";
}

std::string KvcacheConnFault026::GetValidationMethodDesc() const
{
    return "KVCache错误码为1009或INFO log含[URMA_CONNECT_FAILED]";
}

std::string KvcacheConnFault026::GetId() const
{
    return "kvcache_conn_fault_026";
}

} // namespace diag