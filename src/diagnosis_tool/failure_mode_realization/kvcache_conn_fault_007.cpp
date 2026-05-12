#include "kvcache_conn_fault_007.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault007> g_KvcacheConnFault007("kvcache_conn_fault_007");

KvcacheConnFault007::KvcacheConnFault007() noexcept
{
}

bool KvcacheConnFault007::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L162-L183
    // 来源: 08-fault-triage-consolidated.md L180
    // 来源: 10-customer-fault-scenarios.md L273-L280
    // Case 1: INFO log含K_NOT_FOUND或Can't find object
    // 来源: references/kvcache_conn_fault_mode.md L162-L183
    std::string grepOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep -E 'K_NOT_FOUND|Can.?t find object' $LOG/ds_client_*.INFO.log 2>/dev/null)");
    bool case0_matched = !grepOutput0.empty();
    // Case 2: access log中code=0但respMsg含NOT_FOUND或Can't find object
    // 来源: references/kvcache_conn_fault_mode.md L162-L183
    std::string accessOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log 2>/dev/null)");
    bool case1_matched = kvcache_conn_utils::HasCodeZeroWithNotFound(accessOutput1);
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault007::GetName() const
{
    return "对象不存在";
}

std::string KvcacheConnFault007::GetRootCauseDesc() const
{
    return "对象不存在";
}

RootCause KvcacheConnFault007::AnalyzeRootCause()
{
    return RootCause(true, "对象不存在");
}

std::string KvcacheConnFault007::GetFixSuggDesc() const
{
    return "业务自查key；检查业务是否先Put再Get、key生成逻辑、TTL是否提前过期";
}

std::string KvcacheConnFault007::GetValidationMethodDesc() const
{
    return "INFO log含K_NOT_FOUND或Can't find object，或access log code=0但respMsg含NOT_FOUND";
}

std::string KvcacheConnFault007::GetId() const
{
    return "kvcache_conn_fault_007";
}

} // namespace diag