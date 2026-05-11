#include "kvcache_conn_fault_001.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault001> g_KvcacheConnFault001("kvcache_conn_fault_001");

KvcacheConnFault001::KvcacheConnFault001() noexcept
{
}

bool KvcacheConnFault001::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L82-L97
    // 来源: 08-fault-triage-consolidated.md L12-L14
    // 来源: 10-customer-fault-scenarios.md L40-L42
    // Case 1: 在uniq -c输出中，第二列(code)有非0值
    // 来源: references/kvcache_conn_fault_mode.md L82-L97
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasNonZeroCode(uniqOutput0);
    // Case 2: code=0但respMsg含NOT_FOUND或Can't find object
    // 来源: references/kvcache_conn_fault_mode.md L82-L97
    std::string accessOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log 2>/dev/null)");
    bool case1_matched = kvcache_conn_utils::HasCodeZeroWithNotFound(accessOutput1);
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault001::GetName() const
{
    return "KVCache通断异常";
}

std::string KvcacheConnFault001::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault001::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault001::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault001::GetValidationMethodDesc() const
{
    return "查询KVCache错误码非0或code=0但respMsg含NOT_FOUND";
}

std::string KvcacheConnFault001::GetId() const
{
    return "kvcache_conn_fault_001";
}

} // namespace diag