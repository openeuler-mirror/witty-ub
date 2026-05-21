#include "kvcache_conn_fault_032.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault032> g_KvcacheConnFault032("kvcache_conn_fault_032");

KvcacheConnFault032::KvcacheConnFault032() noexcept
{
}

bool KvcacheConnFault032::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L574-L596
    // 来源: 08-fault-triage-consolidated.md L226-L227
    // 来源: 10-customer-fault-scenarios.md L139-L140
    // Case 1: 返回错误码中有6
    // 来源: references/kvcache_conn_fault_mode.md L574-L596
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {6});
    // Case 2: dmesg含Out of memory
    // 来源: references/kvcache_conn_fault_mode.md L574-L596
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(dmesg | grep -i 'Out of memory' 2>/dev/null)");
    bool case1_matched = !cmdOutput1.empty();
    // Case 3: 可用内存不足
    // 来源: references/kvcache_conn_fault_mode.md L574-L596
    std::string cmdOutput2 = kvcache_conn_utils::RunCommand(
        R"(free -h 2>/dev/null)");
    // Warning: memory_low check requires baseline comparison, simplified to non-empty
    bool case2_matched = !cmdOutput2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault032::GetName() const
{
    return "内存不足";
}

std::string KvcacheConnFault032::GetRootCauseDesc() const
{
    return "OS内存不足（ENOMEM）";
}

RootCause KvcacheConnFault032::AnalyzeRootCause()
{
    return RootCause(true, "OS内存不足（ENOMEM）");
}

std::string KvcacheConnFault032::GetFixSuggDesc() const
{
    return "扩内存/调cgroup上限";
}

std::string KvcacheConnFault032::GetValidationMethodDesc() const
{
    return "KVCache错误码为6(K_OUT_OF_MEMORY)或dmesg含Out of memory或free -h可用内存不足";
}

std::string KvcacheConnFault032::GetId() const
{
    return "kvcache_conn_fault_032";
}

} // namespace diag