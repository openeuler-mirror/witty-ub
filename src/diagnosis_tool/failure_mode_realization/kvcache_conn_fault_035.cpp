#include "kvcache_conn_fault_035.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault035> g_KvcacheConnFault035("kvcache_conn_fault_035");

KvcacheConnFault035::KvcacheConnFault035() noexcept
{
}

bool KvcacheConnFault035::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L644-L666
    // 来源: 08-fault-triage-consolidated.md L226-L227
    // 来源: 10-customer-fault-scenarios.md L139-L140
    // Case 1: 返回错误码中有18
    // 来源: references/kvcache_conn_fault_mode.md L644-L666
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {18});
    // Case 2: fd数量接近ulimit -n的值
    // 来源: references/kvcache_conn_fault_mode.md L644-L666
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"cmd(ls /proc/$(pgrep -f datasystem_worker | head -1)/fd 2>/dev/null | wc -l 2>/dev/null)cmd");
    // Warning: fd_near_limit requires comparing fd count with ulimit -n
    bool case1_matched = !cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault035::GetName() const
{
    return "文件描述符耗尽";
}

std::string KvcacheConnFault035::GetRootCauseDesc() const
{
    return "文件描述符耗尽（EMFILE/ENFILE）";
}

RootCause KvcacheConnFault035::AnalyzeRootCause()
{
    return RootCause(true, "文件描述符耗尽（EMFILE/ENFILE）");
}

std::string KvcacheConnFault035::GetFixSuggDesc() const
{
    return "ulimit -n 65535（永久改/etc/security/limits.conf）";
}

std::string KvcacheConnFault035::GetValidationMethodDesc() const
{
    return "KVCache错误码为18(K_FILE_LIMIT_REACHED)或fd数量接近ulimit -n的值";
}

std::string KvcacheConnFault035::GetId() const
{
    return "kvcache_conn_fault_035";
}

} // namespace diag