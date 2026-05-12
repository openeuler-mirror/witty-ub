#include "kvcache_conn_fault_008.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault008> g_KvcacheConnFault008("kvcache_conn_fault_008");

KvcacheConnFault008::KvcacheConnFault008() noexcept
{
}

bool KvcacheConnFault008::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L185-L194
    // 来源: 08-fault-triage-consolidated.md L73-L74
    // 来源: 10-customer-fault-scenarios.md L78-L80
    // 验证方法: KVCache错误码为19(K_TRY_AGAIN)、23(K_CLIENT_WORKER_DISCONNECT)、29(K_SERVER_FD_CLOSED)、31(K_SCALE_DOWN)或32(K_SCALING)
    // 匹配逻辑: 在uniq -c输出中，第二列(code)有19, 23, 29, 31, 32
    std::string uniqOutput = kvcache_conn_utils::RunCommand(
        R"(grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c)");
    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {19, 23, 29, 31, 32});
}

std::string KvcacheConnFault008::GetName() const
{
    return "DS进程内错误";
}

std::string KvcacheConnFault008::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault008::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault008::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault008::GetValidationMethodDesc() const
{
    return "KVCache错误码为19(K_TRY_AGAIN)、23(K_CLIENT_WORKER_DISCONNECT)、29(K_SERVER_FD_CLOSED)、31(K_SCALE_DOWN)或32(K_SCALING)";
}

std::string KvcacheConnFault008::GetId() const
{
    return "kvcache_conn_fault_008";
}

} // namespace diag