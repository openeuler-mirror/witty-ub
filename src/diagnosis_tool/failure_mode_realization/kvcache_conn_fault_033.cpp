#include "kvcache_conn_fault_033.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault033> g_KvcacheConnFault033("kvcache_conn_fault_033");

KvcacheConnFault033::KvcacheConnFault033() noexcept
{
}

bool KvcacheConnFault033::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L598-L616
    // 来源: 08-fault-triage-consolidated.md L226-L227
    // 来源: 10-customer-fault-scenarios.md L139-L140
    // Case 1: 返回错误码中有7
    // 来源: references/kvcache_conn_fault_mode.md L598-L616
    std::string uniqOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    bool case0_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput0, {7});
    // Case 2: dmesg含I/O error
    // 来源: references/kvcache_conn_fault_mode.md L598-L616
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(dmesg | grep 'I/O error' 2>/dev/null)");
    bool case1_matched = !cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault033::GetName() const
{
    return "IO错误";
}

std::string KvcacheConnFault033::GetRootCauseDesc() const
{
    return "块设备/文件系统IO错误（EIO）";
}

RootCause KvcacheConnFault033::AnalyzeRootCause()
{
    return RootCause(true, "块设备/文件系统IO错误（EIO）");
}

std::string KvcacheConnFault033::GetFixSuggDesc() const
{
    return "修文件系统/挂载；分布式网盘故障联系存储运维";
}

std::string KvcacheConnFault033::GetValidationMethodDesc() const
{
    return "KVCache错误码为7(K_IO_ERROR)或dmesg含块设备/文件系统错误";
}

std::string KvcacheConnFault033::GetId() const
{
    return "kvcache_conn_fault_033";
}

} // namespace diag