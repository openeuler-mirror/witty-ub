#include "kvcache_conn_fault_002.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault002> g_KvcacheConnFault002("kvcache_conn_fault_002");

KvcacheConnFault002::KvcacheConnFault002() noexcept
{
}

bool KvcacheConnFault002::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L99-L108
    // 来源: 08-fault-triage-consolidated.md L73-L74
    // 来源: 10-customer-fault-scenarios.md L78-L80
    // 验证方法: KVCache错误码为2(K_INVALID)、3(K_NOT_FOUND)或8(K_NOT_READY)
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有2, 3, 8
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {2, 3, 8});
}

std::string KvcacheConnFault002::GetName() const
{
    return "用户侧错误";
}

std::string KvcacheConnFault002::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault002::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault002::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault002::GetValidationMethodDesc() const
{
    return "KVCache错误码为2(K_INVALID)、3(K_NOT_FOUND)或8(K_NOT_READY)";
}

std::string KvcacheConnFault002::GetId() const
{
    return "kvcache_conn_fault_002";
}

} // namespace diag