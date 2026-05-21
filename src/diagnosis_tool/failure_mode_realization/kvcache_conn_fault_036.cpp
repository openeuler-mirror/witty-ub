#include "kvcache_conn_fault_036.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault036> g_KvcacheConnFault036("kvcache_conn_fault_036");

KvcacheConnFault036::KvcacheConnFault036() noexcept
{
}

bool KvcacheConnFault036::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L668-L688
    // 来源: 08-fault-triage-consolidated.md L86-L87
    // 来源: 08-fault-triage-consolidated.md L233-L234
    // Case 1: 返回错误码中有5
    // 来源: references/kvcache_conn_fault_mode.md L668-L688
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {5});
    // Case 2: INFO log含Get mmap entry failed
    // 来源: references/kvcache_conn_fault_mode.md L668-L688
    std::string grepOutput1 = kvcache_conn_utils::RunCommand(
        R"(grep 'Get mmap entry failed' $LOG/datasystem_worker.INFO.log | tail -50 2>/dev/null)");
    bool case1_matched = !grepOutput1.empty();
    // Case 3: mlock限制值
    // 来源: references/kvcache_conn_fault_mode.md L668-L688
    std::string cmdOutput2 = kvcache_conn_utils::RunCommand(
        R"(ulimit -l 2>/dev/null)");
    bool case2_matched = cmdOutput2.find("unlimited") == std::string::npos;
    return case0_matched || case1_matched || case2_matched;
}

std::string KvcacheConnFault036::GetName() const
{
    return "mmap失败";
}

std::string KvcacheConnFault036::GetRootCauseDesc() const
{
    return "mlock限制导致mmap失败（ENOMEM）";
}

RootCause KvcacheConnFault036::AnalyzeRootCause()
{
    return RootCause(true, "mlock限制导致mmap失败（ENOMEM）");
}

std::string KvcacheConnFault036::GetFixSuggDesc() const
{
    return "ulimit -l unlimited";
}

std::string KvcacheConnFault036::GetValidationMethodDesc() const
{
    return "KVCache错误码为5(K_RUNTIME_ERROR)且INFO log含Get mmap entry failed";
}

std::string KvcacheConnFault036::GetId() const
{
    return "kvcache_conn_fault_036";
}

} // namespace diag