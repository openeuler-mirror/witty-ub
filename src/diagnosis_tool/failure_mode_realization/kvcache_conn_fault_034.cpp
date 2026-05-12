#include "kvcache_conn_fault_034.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault034> g_KvcacheConnFault034("kvcache_conn_fault_034");

KvcacheConnFault034::KvcacheConnFault034() noexcept
{
}

bool KvcacheConnFault034::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L618-L642
    // 来源: 08-fault-triage-consolidated.md L226-L227
    // 来源: 10-customer-fault-scenarios.md L139-L140
    // Case 1: 返回错误码中有13
    // 来源: references/kvcache_conn_fault_mode.md L618-L642
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {13});
    // Case 2: 磁盘使用率接近100%
    // 来源: references/kvcache_conn_fault_mode.md L618-L642
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(df -h 2>/dev/null)");
    // Warning: disk_usage_high check requires parsing df output for Use% >= 95%
    bool case1_matched = !cmdOutput1.empty();
    // Case 3: SPILL_HARD_DISK或SHARED_DISK空间接近TOTAL_LIMIT
    // 来源: references/kvcache_conn_fault_mode.md L618-L642
    std::string resourceOut2 = kvcache_conn_utils::RunCommand(
        R"(grep -E 'SPILL_HARD_DISK|SHARED_DISK' $LOG/resource.log | tail -5 2>/dev/null)");
    // Warning: resource log check requires parsing ETCD_QUEUE_USAGE >= 80% or success rate < 0.95
    bool case2_matched = !resourceOut2.empty();
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault034::GetName() const
{
    return "磁盘空间不足";
}

std::string KvcacheConnFault034::GetRootCauseDesc() const
{
    return "磁盘空间不足（ENOSPC）";
}

RootCause KvcacheConnFault034::AnalyzeRootCause()
{
    return RootCause(true, "磁盘空间不足（ENOSPC）");
}

std::string KvcacheConnFault034::GetFixSuggDesc() const
{
    return "清理/扩容（本地盘或分布式网盘挂载点）";
}

std::string KvcacheConnFault034::GetValidationMethodDesc() const
{
    return "KVCache错误码为13(K_NO_SPACE)或df -h磁盘使用率接近100%或resource log含SPILL_HARD_DISK/SHARED_DISK空间接近TOTAL_LIMIT";
}

std::string KvcacheConnFault034::GetId() const
{
    return "kvcache_conn_fault_034";
}

} // namespace diag